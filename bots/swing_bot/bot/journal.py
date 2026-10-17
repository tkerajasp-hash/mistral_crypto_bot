"""Persistance : etat du bot (JSON) + journaux CSV (trades, equity)."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class BotState:
    in_position: bool = False
    entry_price: float = 0.0
    entry_time: Optional[str] = None
    qty: float = 0.0
    initial_stop: float = 0.0                          # stop au moment de l'entree (pour le R)
    entry_fee: float = 0.0
    stop: dict = field(default_factory=dict)          # StopManager.to_dict()
    last_bar_time: Optional[str] = None               # derniere bougie traitee
    cooldown_until_bar: int = 0                        # compteur de bougies
    last_exit_bar: int = -10**9                        # bougie de la derniere sortie (anti-whipsaw)
    bars_seen: int = 0
    day_key: Optional[str] = None                      # 'YYYY-MM-DD' UTC
    day_start_equity: float = 0.0
    peak_equity: float = 0.0
    halted: bool = False
    halt_reason: Optional[str] = None

    def to_json(self) -> str:
        return json.dumps(self.__dict__, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "BotState":
        p = Path(path)
        if not p.exists():
            return cls()
        return cls(**json.loads(p.read_text()))

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.to_json())


class CsvLog:
    def __init__(self, path: str | Path, header: list[str]):
        self.path = Path(path)
        self.header = header
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="") as f:
                csv.writer(f).writerow(header)

    def append(self, row: dict) -> None:
        with self.path.open("a", newline="") as f:
            csv.writer(f).writerow([row.get(h, "") for h in self.header])


TRADES_HEADER = [
    "time", "action", "side", "qty", "price", "fee", "liquidity",
    "equity", "pnl", "r_multiple", "reason",
]
EQUITY_HEADER = ["time", "bar_time", "equity", "cash", "position_qty", "mark", "in_position", "stop"]


class Journal:
    def __init__(self, trades_csv: str, equity_csv: str):
        self.trades = CsvLog(trades_csv, TRADES_HEADER)
        self.equity = CsvLog(equity_csv, EQUITY_HEADER)

    def record_trade(self, **row) -> None:
        row.setdefault("time", _now_iso())
        self.trades.append(row)

    def record_equity(self, **row) -> None:
        row.setdefault("time", _now_iso())
        self.equity.append(row)
