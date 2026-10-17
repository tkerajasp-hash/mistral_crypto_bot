"""Gestion du risque : dimensionnement de position et stop loss.

Le stop loss combine :
  - un stop INITIAL base sur l'ATR         (entree - initial_stop_atr * ATR_entree)
  - un plancher de perte dur               (entree * (1 - hard_max_loss_pct))
  - un passage au point mort a +breakeven_at_r
  - un stop SUIVEUR "chandelier"           (plus_haut_depuis_entree - trailing_atr * ATR)
Le stop ne redescend jamais (effet cliquet).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from .config import RiskConfig


def position_size(
    equity: float,
    entry: float,
    stop: float,
    *,
    risk_per_trade: float,
    max_position_pct: float,
    cash_available: float,
) -> float:
    """Quantite a acheter pour que (entry - stop) * qty ~= risk_per_trade * equity."""
    per_unit_risk = max(entry - stop, 1e-9)
    qty_by_risk = (equity * risk_per_trade) / per_unit_risk
    qty_by_cap = (equity * max_position_pct) / entry
    qty_by_cash = max(cash_available, 0.0) / entry
    return max(min(qty_by_risk, qty_by_cap, qty_by_cash), 0.0)


@dataclass
class StopManager:
    """Suit le stop d'UNE position longue ouverte."""

    entry_price: float
    entry_atr: float
    cfg: RiskConfig
    highest_high: float = 0.0
    stop: float = 0.0
    breakeven_done: bool = False

    def __post_init__(self):
        if self.highest_high <= 0:
            self.highest_high = self.entry_price
        if self.stop <= 0:
            atr_stop = self.entry_price - self.cfg.initial_stop_atr * self.entry_atr
            hard_stop = self.entry_price * (1.0 - self.cfg.hard_max_loss_pct)
            self.stop = max(atr_stop, hard_stop)

    # ------------------------------------------------------------------
    @property
    def initial_risk(self) -> float:
        return max(self.entry_price - self.stop, 1e-9)

    def update(self, bar_high: float, bar_close: float, current_atr: float) -> None:
        """A appeler une fois par bougie cloturee tant que la position est ouverte."""
        self.highest_high = max(self.highest_high, bar_high)

        # 1) point mort apres +1R (ou le multiple configure)
        if not self.breakeven_done:
            r_gain = (bar_close - self.entry_price) / self.initial_risk
            if r_gain >= self.cfg.breakeven_at_r:
                be = self.entry_price + self.cfg.breakeven_offset_atr * self.entry_atr
                self.stop = max(self.stop, be)
                self.breakeven_done = True

        # 2) stop suiveur chandelier
        atr_v = current_atr if current_atr > 0 else self.entry_atr
        chandelier = self.highest_high - self.cfg.trailing_atr * atr_v
        self.stop = max(self.stop, chandelier)  # cliquet : ne redescend jamais

    def hit(self, bar_low: float) -> bool:
        return bar_low <= self.stop

    # ------------------------------------------------------------------
    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("cfg", None)
        return d

    @classmethod
    def from_dict(cls, d: dict, cfg: RiskConfig) -> "StopManager":
        return cls(
            entry_price=d["entry_price"],
            entry_atr=d["entry_atr"],
            cfg=cfg,
            highest_high=d.get("highest_high", 0.0),
            stop=d.get("stop", 0.0),
            breakeven_done=d.get("breakeven_done", False),
        )
