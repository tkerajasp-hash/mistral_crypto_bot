"""Abstraction courtier + implementation "paper" (simulation sur prix reels)."""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Optional

from .config import BotConfig

BUY = "BUY"
SELL = "SELL"


@dataclass
class Fill:
    side: str
    qty: float
    price: float          # prix moyen d'execution (slippage inclus)
    fee: float             # en devise de cotation
    liquidity: str         # "maker" | "taker"


@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.qty > 1e-12


class Broker(abc.ABC):
    """Interface minimale utilisee par le moteur."""

    @abc.abstractmethod
    def get_cash(self) -> float: ...

    @abc.abstractmethod
    def get_position(self) -> Position: ...

    @abc.abstractmethod
    def mark_price(self, price: float) -> None: ...

    @abc.abstractmethod
    def equity(self, mark: float) -> float: ...

    @abc.abstractmethod
    def buy(self, qty: float, ref_price: float, *, maker: bool) -> Fill: ...

    @abc.abstractmethod
    def sell(self, qty: float, ref_price: float, *, maker: bool) -> Fill: ...


class PaperBroker(Broker):
    """Simule les executions.

    Hypotheses de fill :
      - ordre maker (limit post-only) : rempli au `ref_price` sans slippage, frais maker_bps
      - ordre taker (market)          : rempli avec slippage_bps defavorable, frais taker_bps
    C'est volontairement conservateur cote taker et optimiste cote maker
    (un maker peut ne pas etre rempli en live -- le moteur gere ce cas).
    """

    def __init__(self, cfg: BotConfig):
        self.cfg = cfg
        self._cash = cfg.paper.starting_cash
        self._pos = Position()
        self._last_mark = 0.0

    # -- lecture ------------------------------------------------------
    def get_cash(self) -> float:
        return self._cash

    def get_position(self) -> Position:
        return Position(self._pos.qty, self._pos.avg_price)

    def mark_price(self, price: float) -> None:
        self._last_mark = price

    def equity(self, mark: float) -> float:
        return self._cash + self._pos.qty * mark

    # -- helpers ----------------------------------------------------
    def _fees_bps(self, maker: bool) -> tuple[float, float]:
        f = self.cfg.fees
        if maker:
            return f.maker_bps, 0.0
        return f.taker_bps, f.slippage_bps

    # -- ordres ---------------------------------------------------
    def buy(self, qty: float, ref_price: float, *, maker: bool) -> Fill:
        fee_bps, slip_bps = self._fees_bps(maker)
        price = ref_price * (1 + slip_bps / 10_000)
        notional = qty * price
        fee = notional * fee_bps / 10_000
        self._cash -= notional + fee
        new_qty = self._pos.qty + qty
        self._pos.avg_price = (
            (self._pos.avg_price * self._pos.qty + notional) / new_qty if new_qty else 0.0
        )
        self._pos.qty = new_qty
        return Fill(BUY, qty, price, fee, "maker" if maker else "taker")

    def sell(self, qty: float, ref_price: float, *, maker: bool) -> Fill:
        fee_bps, slip_bps = self._fees_bps(maker)
        qty = min(qty, self._pos.qty)
        price = ref_price * (1 - slip_bps / 10_000)
        notional = qty * price
        fee = notional * fee_bps / 10_000
        self._cash += notional - fee
        self._pos.qty -= qty
        if self._pos.qty <= 1e-12:
            self._pos = Position()
        return Fill(SELL, qty, price, fee, "maker" if maker else "taker")
