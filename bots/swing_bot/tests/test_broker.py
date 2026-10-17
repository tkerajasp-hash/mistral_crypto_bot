from bot.config import BotConfig
from bot.broker import PaperBroker


def _cfg(maker=0.0, taker=60.0, slip=5.0, cash=10_000.0):
    c = BotConfig()
    c.fees.maker_bps = maker
    c.fees.taker_bps = taker
    c.fees.slippage_bps = slip
    c.paper.starting_cash = cash
    return c


def test_maker_buy_no_slippage_no_fee():
    b = PaperBroker(_cfg())
    fill = b.buy(1.0, 100.0, maker=True)
    assert fill.price == 100.0
    assert fill.fee == 0.0
    assert b.get_cash() == 9_900.0
    assert b.get_position().qty == 1.0


def test_taker_buy_applies_slippage_and_fee():
    b = PaperBroker(_cfg(taker=60.0, slip=10.0))
    fill = b.buy(1.0, 100.0, maker=False)
    assert fill.price == 100.1                      # +10 bps de slippage
    assert round(fill.fee, 6) == round(100.1 * 0.006, 6)
    assert b.get_cash() < 9_900.0


def test_round_trip_pnl_is_negative_with_costs():
    b = PaperBroker(_cfg(taker=60.0, slip=10.0))
    b.buy(1.0, 100.0, maker=False)
    b.sell(1.0, 100.0, maker=False)
    assert b.get_position().qty == 0.0
    assert b.equity(100.0) < 10_000.0              # les frais ont coute de l'argent


def test_equity_tracks_mark_price():
    b = PaperBroker(_cfg())
    b.buy(2.0, 100.0, maker=True)
    assert b.equity(100.0) == 10_000.0
    assert b.equity(150.0) == 10_100.0             # +50 sur 2 unites
