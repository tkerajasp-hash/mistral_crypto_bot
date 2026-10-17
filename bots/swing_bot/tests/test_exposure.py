import numpy as np
import pandas as pd

from bot.config import RiskConfig
from bot import exposure as expo


def _df(close, atr, ema_fast):
    idx = pd.date_range("2024-01-01", periods=len(close), freq="6h", tz="UTC")
    return pd.DataFrame({"close": close, "atr": atr, "ema_fast": ema_fast}, index=idx)


def _rc(**kw):
    r = RiskConfig()
    r.exposure_control = True
    for k, v in kw.items():
        setattr(r, k, v)
    return r


def test_vol_targeting_cuts_size_when_vol_spikes():
    n = 400
    close = np.full(n, 100.0)
    atr = np.full(n, 2.0)          # ATR% = 2%
    atr[-1] = 8.0                  # pic de vol sur la derniere barre -> ATR% = 8%
    df = expo.attach_market_signals(_df(close, atr, close - 1), _rc(vol_target_lookback=100))
    assert df["exp_vol_mult"].iloc[-2] == 1.0          # regime calme : plein (cap 1.0)
    assert df["exp_vol_mult"].iloc[-1] < 0.35          # vol x4 -> taille ~ /4


def test_vol_mult_never_exceeds_cap():
    n = 200
    df = expo.attach_market_signals(
        _df(np.full(n, 100.0), np.full(n, 5.0), np.full(n, 99.0)),
        _rc(vol_target_lookback=50, vol_mult_cap=1.0),
    )
    assert (df["exp_vol_mult"] <= 1.0 + 1e-9).all()


def test_crash_brake_fires_on_brutal_drop_and_holds():
    n = 60
    close = np.full(n, 100.0)
    close[40:] = 80.0             # -20% d'un coup
    atr = np.full(n, 2.0)
    df = expo.attach_market_signals(_df(close, atr, close), _rc(crash_brake_bars=8))
    assert bool(df["exp_crash_brake"].iloc[41]) is True
    assert bool(df["exp_crash_brake"].iloc[45]) is True      # encore arme quelques barres apres
    assert bool(df["exp_crash_brake"].iloc[10]) is False


def test_crash_active_respects_master_switch():
    row = pd.Series({"exp_crash_brake": True})
    assert expo.crash_active(row, _rc()) is True
    r_off = RiskConfig()  # exposure_control = False par defaut
    assert expo.crash_active(row, r_off) is False


def test_dd_throttle_ramps_linearly():
    r = _rc(dd_throttle_start=0.10, dd_throttle_floor=0.30)
    assert expo.dd_throttle(100, 100, r) == 1.0            # pas de DD
    assert expo.dd_throttle(95, 100, r) == 1.0             # -5% : sous le seuil
    assert abs(expo.dd_throttle(90, 100, r) - 1.0) < 1e-9  # -10% : pile au seuil
    mid = expo.dd_throttle(85, 100, r)                     # -15% : a mi-rampe
    assert 0.60 < mid < 0.70
    assert abs(expo.dd_throttle(80, 100, r) - 0.30) < 1e-9  # -20% : plancher
    assert abs(expo.dd_throttle(50, 100, r) - 0.30) < 1e-9  # au-dela : reste au plancher


def test_whipsaw_halves_size_then_recovers():
    r = _rc(whipsaw_bars=12, whipsaw_mult=0.5)
    assert expo.whipsaw_mult(3, r) == 0.5
    assert expo.whipsaw_mult(11, r) == 0.5
    assert expo.whipsaw_mult(12, r) == 1.0
    assert expo.whipsaw_mult(10**9, r) == 1.0


def test_entry_multiplier_combines_bricks():
    r = _rc(dd_throttle_start=0.10, dd_throttle_floor=0.30, whipsaw_bars=12, whipsaw_mult=0.5)
    row = pd.Series({"exp_vol_mult": 0.8})
    st = expo.ExposureState(equity=85.0, peak_equity=100.0, bars_since_exit=3)  # -15% DD, whipsaw actif
    mult, why = expo.entry_multiplier(row, st, r)
    # 0.8 (vol) * ~0.65 (dd) * 0.5 (whipsaw)
    assert 0.24 < mult < 0.28
    assert "vol" in why and "dd" in why and "ws" in why


def test_disabled_by_default():
    r = RiskConfig()
    row = pd.Series({"exp_vol_mult": 0.2, "exp_crash_brake": True})
    mult, why = expo.entry_multiplier(row, expo.ExposureState(50, 100, 0), r)
    assert mult == 1.0 and why == ""


def test_bar_crash_stop_forces_exit_in_backtest():
    """Une bougie 6h qui cloture a -8% doit declencher le stop 'crash bougie'
    quand bar_crash_stop_pct=0.05 (les autres stops sont neutralises pour l'isoler)."""
    import numpy as np
    import pandas as pd
    from bot.config import load_config
    from bot.backtest import run_backtest

    n = 500
    close = np.linspace(100.0, 400.0, n)
    close[400] = close[399] * 0.92                       # -8% sur une bougie
    close[401:] = close[400] * np.linspace(1.0, 1.3, n - 401)
    op = np.r_[close[0], close[:-1]]
    idx = pd.date_range("2022-01-01", periods=n, freq="6h", tz="UTC")
    df = pd.DataFrame({"open": op, "high": np.maximum(op, close) + 1,
                       "low": np.minimum(op, close) - 1, "close": close, "volume": 1.0}, index=idx)

    class _MD:
        def get_candles(self, *a, **k):
            return df.copy()

    cfg = load_config(strategy_name="bull_rider_guarded_6h")
    cfg.strategy.htf_filter = False
    cfg.risk.initial_stop_atr = 100.0        # neutralise le stop ATR
    cfg.risk.trailing_atr = 100.0            # neutralise le trailing
    cfg.risk.hard_max_loss_pct = 0.99        # neutralise le plancher dur
    cfg.risk.daily_max_loss_pct = 0.99
    cfg.risk.max_drawdown_pct = 0.99

    res = run_backtest(cfg, days=120, save_dir=None, md=_MD())
    assert any("crash bougie" in t.reason for t in res.trades)

    cfg.risk.bar_crash_stop_pct = 0.0        # desactive -> plus aucune sortie "crash bougie"
    res2 = run_backtest(cfg, days=120, save_dir=None, md=_MD())
    assert not any("crash bougie" in t.reason for t in res2.trades)
