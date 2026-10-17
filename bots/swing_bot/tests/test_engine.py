"""Test d'integration du moteur avec un faux fournisseur de donnees (sans reseau)."""
import pandas as pd

from bot.broker import PaperBroker
from bot.config import load_config
from bot.engine import Bot
from bot.journal import BotState, Journal
from bot.strategy import TrendStrategy


class FakeMarket:
    def __init__(self, df):
        self._df = df

    def get_candles(self, product_id, granularity, granularity_seconds, n_bars):
        return self._df.tail(n_bars)

    def spot_price(self, product_id):
        return float(self._df["close"].iloc[-1])


def _cfg(tmp_path):
    cfg = load_config("config.yaml")
    cfg.strategy.htf_filter = False
    cfg.strategy.adx_min = 5
    cfg.execution.min_edge_atr = 0.0
    cfg.logging.state_file = str(tmp_path / "state.json")
    cfg.logging.trades_csv = str(tmp_path / "trades.csv")
    cfg.logging.equity_csv = str(tmp_path / "equity.csv")
    return cfg


def _first_entry_slice(cfg, df):
    """Trouve le plus petit prefixe de `df` sur lequel la strategie declenche une entree."""
    strat = TrendStrategy(cfg.strategy)
    data = strat.compute(df)
    for i in range(strat.min_bars(), len(data)):
        sig = strat.signal_from_row(data.iloc[i], data.iloc[i - 1], in_position=False, htf_ok=True)
        if sig.action == "enter_long":
            return df.iloc[: i + 1]
    raise AssertionError("aucune entree trouvee dans la fixture")


def test_tick_is_idempotent_per_bar(tmp_path, uptrend_df):
    cfg = _cfg(tmp_path)
    bot = Bot(cfg, FakeMarket(uptrend_df), PaperBroker(cfg),
              TrendStrategy(cfg.strategy), Journal(cfg.logging.trades_csv, cfg.logging.equity_csv))
    bot.tick()
    st1 = BotState.load(cfg.logging.state_file)
    bot.tick()  # meme derniere bougie -> ne doit rien changer
    st2 = BotState.load(cfg.logging.state_file)
    assert st1.bars_seen == st2.bars_seen == 1


def test_full_cycle_entry_then_stop_out(tmp_path, uptrend_df):
    cfg = _cfg(tmp_path)
    journal = Journal(cfg.logging.trades_csv, cfg.logging.equity_csv)
    broker = PaperBroker(cfg)

    entry_df = _first_entry_slice(cfg, uptrend_df)

    # 1) bougie de cassure -> entree
    bot = Bot(cfg, FakeMarket(entry_df), broker, TrendStrategy(cfg.strategy), journal)
    bot.tick()
    assert BotState.load(cfg.logging.state_file).in_position

    # 2) on injecte une bougie qui plonge sous le stop -> sortie
    crashed = uptrend_df.iloc[: len(entry_df) + 1].copy()
    crashed.iloc[-1, crashed.columns.get_loc("low")] = 1.0
    crashed.iloc[-1, crashed.columns.get_loc("close")] = 1.0
    bot2 = Bot(cfg, FakeMarket(crashed), broker, TrendStrategy(cfg.strategy), journal)
    bot2.tick()

    st = BotState.load(cfg.logging.state_file)
    assert not st.in_position
    assert st.cooldown_until_bar >= st.bars_seen
    trades = pd.read_csv(cfg.logging.trades_csv)
    assert list(trades["action"]) == ["ENTRY", "EXIT"]
