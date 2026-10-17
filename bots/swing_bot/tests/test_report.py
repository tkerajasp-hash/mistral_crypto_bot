"""report.build_digest / equity_chart : robustes meme sans donnees."""
from pathlib import Path

import pandas as pd

from bot.config import load_config
from bot.report import build_digest, equity_chart


def _cfg(tmp_path, pid="BTC-USDC"):
    cfg = load_config("config.yaml")
    cfg.market.product_id = pid
    cfg.active_strategy = "test"
    cfg.logging.state_file = str(tmp_path / "state.json")
    cfg.logging.trades_csv = str(tmp_path / "trades.csv")
    cfg.logging.equity_csv = str(tmp_path / "equity.csv")
    return cfg


def test_digest_no_data(tmp_path):
    cfg = _cfg(tmp_path)
    txt = build_digest(cfg)
    assert "Rapport" in txt and "BTC-USDC" in txt
    assert "aucun tick" in txt


def _write_equity(path, values, start="2026-08-20"):
    idx = pd.date_range(start, periods=len(values), freq="6h", tz="UTC")
    pd.DataFrame({
        "time": idx.astype(str), "bar_time": idx.astype(str),
        "equity": values, "cash": values, "position_qty": 0.0,
        "mark": [60000] * len(values), "in_position": False, "stop": "",
    }).to_csv(path, index=False)


def test_digest_with_history(tmp_path):
    cfg = _cfg(tmp_path)
    _write_equity(cfg.logging.equity_csv, [10000, 10120, 9980, 10050])
    pd.DataFrame([
        {"time": "2026-08-20T06:00:00+00:00", "action": "ENTRY", "side": "BUY",
         "qty": 0.1, "price": 60000, "fee": 0, "liquidity": "maker",
         "equity": 10000, "pnl": "", "r_multiple": "", "reason": "cassure"},
        {"time": "2026-08-21T00:00:00+00:00", "action": "EXIT", "side": "SELL",
         "qty": 0.1, "price": 60500, "fee": 0, "liquidity": "maker",
         "equity": 10050, "pnl": 50.0, "r_multiple": 1.2, "reason": "trailing"},
    ]).to_csv(cfg.logging.trades_csv, index=False)

    txt = build_digest(cfg)
    assert "+0.50%" in txt                      # 10050 / 10000 - 1
    assert "1 clotures" in txt and "R cumule +1.20" in txt

    out = equity_chart(cfg, out_path=str(tmp_path / "eq.png"))
    assert out and Path(out).exists() and Path(out).stat().st_size > 0


def test_equity_chart_skips_when_too_short(tmp_path):
    cfg = _cfg(tmp_path)
    _write_equity(cfg.logging.equity_csv, [10000])
    assert equity_chart(cfg, out_path=str(tmp_path / "x.png")) is None
