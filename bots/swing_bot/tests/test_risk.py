from bot.config import RiskConfig
from bot.risk import StopManager, position_size


def _cfg(**kw):
    c = RiskConfig()
    for k, v in kw.items():
        setattr(c, k, v)
    return c


def test_initial_stop_uses_atr_then_hard_floor():
    sm = StopManager(entry_price=100, entry_atr=2, cfg=_cfg(initial_stop_atr=2.5, hard_max_loss_pct=0.06))
    # atr stop = 100 - 5 = 95 ; hard floor = 94 -> on garde le plus haut (95)
    assert sm.stop == 95.0

    sm2 = StopManager(entry_price=100, entry_atr=5, cfg=_cfg(initial_stop_atr=2.5, hard_max_loss_pct=0.06))
    # atr stop = 87.5 ; hard floor = 94 -> le plancher dur protege
    assert sm2.stop == 94.0


def test_trailing_stop_ratchets_up_only():
    sm = StopManager(entry_price=100, entry_atr=2, cfg=_cfg(trailing_atr=3.0, breakeven_at_r=99))
    start = sm.stop
    sm.update(bar_high=120, bar_close=118, current_atr=2)  # chandelier = 120 - 6 = 114
    assert sm.stop == 114.0
    sm.update(bar_high=110, bar_close=108, current_atr=2)  # ne doit PAS redescendre
    assert sm.stop == 114.0


def test_breakeven_moves_stop_after_1r():
    cfg = _cfg(initial_stop_atr=2.5, hard_max_loss_pct=0.5, breakeven_at_r=1.0, breakeven_offset_atr=0.25, trailing_atr=99)
    sm = StopManager(entry_price=100, entry_atr=2, cfg=cfg)   # stop 95, risque 5
    sm.update(bar_high=106, bar_close=105, current_atr=2)     # +1R exactement
    assert sm.stop >= 100.0
    assert sm.breakeven_done


def test_stop_hit_detection():
    sm = StopManager(entry_price=100, entry_atr=2, cfg=_cfg())
    assert not sm.hit(96)
    assert sm.hit(94.9)


def test_position_size_respects_risk_budget():
    qty = position_size(10_000, entry=100, stop=95,
                        risk_per_trade=0.01, max_position_pct=1.0, cash_available=1e9)
    # risque 1% de 10k = 100 ; risque/unite = 5 -> 20 unites
    assert abs(qty - 20) < 1e-6


def test_position_size_capped_by_cash():
    qty = position_size(10_000, entry=100, stop=95,
                        risk_per_trade=0.5, max_position_pct=1.0, cash_available=500)
    assert abs(qty - 5) < 1e-6
