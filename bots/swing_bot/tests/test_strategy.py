import numpy as np
import pandas as pd

from bot.config import StrategyConfig
from bot.strategy import ENTER_LONG, EXIT, HOLD, TrendStrategy


def _strat(**kw):
    c = StrategyConfig()
    c.htf_filter = False           # on teste la logique mono-timeframe
    for k, v in kw.items():
        setattr(c, k, v)
    return TrendStrategy(c)


def _scan(strat, df, in_position=False, window=40):
    data = strat.compute(df)
    out = []
    for i in range(len(data) - window, len(data)):
        out.append(strat.signal_from_row(data.iloc[i], data.iloc[i - 1],
                                         in_position=in_position, htf_ok=True))
    return out


def _actions(sigs):
    return [s.action for s in sigs]


def test_enters_during_breakout_leg(uptrend_df):
    s = _strat(adx_min=15, breakout_lookback=20)
    assert ENTER_LONG in _actions(_scan(s, uptrend_df))


def test_no_entry_in_tight_range(range_df):
    s = _strat(adx_min=20)
    assert ENTER_LONG not in _actions(_scan(s, range_df, window=200))


def test_exit_when_regime_turns_down(crash_after_uptrend_df):
    s = _strat(adx_min=10)
    assert EXIT in _actions(_scan(s, crash_after_uptrend_df, in_position=True))


def test_adx_threshold_gates_the_same_bar(uptrend_df):
    """Sur la barre exacte d'une entree, relever adx_min au-dessus de l'ADX la bloque."""
    s = _strat(adx_min=15, breakout_lookback=20)
    data = s.compute(uptrend_df)
    for i in range(s.min_bars(), len(data)):
        sig = s.signal_from_row(data.iloc[i], data.iloc[i - 1], in_position=False, htf_ok=True)
        if sig.action == ENTER_LONG:
            gated = _strat(adx_min=sig.adx + 5, breakout_lookback=20)
            g = gated.signal_from_row(data.iloc[i], data.iloc[i - 1], in_position=False, htf_ok=True)
            assert g.action == HOLD and "ADX" in g.reason
            return
    raise AssertionError("aucune entree pour tester le filtre ADX")


def _ohlc(close, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(close), freq="h", tz="UTC")
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {"open": open_, "high": np.maximum(open_, close) + 1.0,
         "low": np.minimum(open_, close) - 1.0, "close": close, "volume": 1.0},
        index=idx,
    )


def test_pullback_enters_on_dip_reclaim_in_uptrend():
    """Tendance haussiere de fond + repli sur l'EMA20 puis rachat -> le mode pullback entre,
    et au moins une entree provient bien du chemin "repli rachete" (pas seulement d'une cassure)."""
    rng = np.random.default_rng(0)
    base = np.linspace(100, 260, 320) + rng.normal(0, 0.4, 320)   # hausse reguliere
    base[280:295] -= np.linspace(0, 16, 15)                        # repli qui ramene vers l'EMA20
    base[295:320] += np.linspace(0, 13, 25)                        # rachat / reprise
    df = _ohlc(base)

    s_pb = _strat(entry_mode="pullback", adx_min=10, ema_fast=20, pullback_lookback=6)
    sigs = _scan(s_pb, df, window=30)
    assert ENTER_LONG in _actions(sigs)
    assert any(s.action == ENTER_LONG and "repli" in s.reason for s in sigs)


def test_pullback_still_blocked_when_regime_not_bullish(range_df):
    """En range serre (ADX faible), aucune entree meme si le prix oscille autour de l'EMA20."""
    s = _strat(entry_mode="pullback", adx_min=20)
    assert ENTER_LONG not in _actions(_scan(s, range_df, window=200))


def test_htf_filter_blocks_when_not_ok(uptrend_df):
    s = _strat(adx_min=15, breakout_lookback=20)
    data = s.compute(uptrend_df)
    blocked = False
    for i in range(s.min_bars(), len(data)):
        s_ok = s.signal_from_row(data.iloc[i], data.iloc[i - 1], in_position=False, htf_ok=True)
        s_no = s.signal_from_row(data.iloc[i], data.iloc[i - 1], in_position=False, htf_ok=False)
        if s_ok.action == ENTER_LONG:
            assert s_no.action == HOLD
            blocked = True
    assert blocked
