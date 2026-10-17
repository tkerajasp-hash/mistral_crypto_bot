"""Acces Coinbase : donnees de marche (public) + courtier live (SDK officiel)."""
from __future__ import annotations

import time
import uuid
from typing import Optional

import pandas as pd
import requests

from .broker import BUY, SELL, Broker, Fill, Position
from .config import BotConfig

PUBLIC_BASE = "https://api.coinbase.com/api/v3/brokerage/market"
MAX_CANDLES_PER_REQ = 300


class OrderNotFilled(RuntimeError):
    """Un ordre maker post-only n'a pas ete rempli dans le delai imparti."""


# ---------------------------------------------------------------------------
# Donnees de marche -- endpoint PUBLIC, aucune cle requise
# ---------------------------------------------------------------------------
class MarketData:
    def __init__(self, session: Optional[requests.Session] = None, *, cache: bool = False):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "swing-bot/0.1"})
        self._cache_enabled = cache
        self._cache: dict[tuple[str, str], pd.DataFrame] = {}

    def _get_json(self, url: str, params: dict) -> dict:
        for attempt in range(4):
            resp = self.session.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code in (429, 500, 502, 503):
                time.sleep(1.5 * (attempt + 1))
                continue
            resp.raise_for_status()
        resp.raise_for_status()
        return {}

    def get_candles(self, product_id: str, granularity: str, granularity_seconds: int, n_bars: int) -> pd.DataFrame:
        """Renvoie les `n_bars` dernieres bougies, index temporel UTC croissant.

        La derniere ligne peut etre une bougie EN COURS (non cloturee) -- l'appelant
        doit la retirer avant de decider.
        """
        if self._cache_enabled:
            cached = self._cache.get((product_id, granularity))
            if cached is not None and len(cached) >= n_bars:
                return cached.tail(n_bars).copy()

        rows: list[dict] = []
        remaining = n_bars
        cursor_end = int(time.time())
        empty_streak = 0
        max_calls = n_bars // MAX_CANDLES_PER_REQ + 5
        for _ in range(max_calls):
            if remaining <= 0:
                break
            span = min(remaining, MAX_CANDLES_PER_REQ)
            start = cursor_end - span * granularity_seconds
            data = self._get_json(
                f"{PUBLIC_BASE}/products/{product_id}/candles",
                {"start": str(start), "end": str(cursor_end), "granularity": granularity},
            )
            batch = data.get("candles", [])
            if batch:
                rows.extend(batch)
                remaining -= len(batch)
                empty_streak = 0
            else:
                empty_streak += 1
                if empty_streak >= 3:
                    break  # l'historique public s'arrete la
            cursor_end = start
            time.sleep(0.2)

        if not rows:
            raise RuntimeError(f"Aucune bougie renvoyee pour {product_id}")

        df = pd.DataFrame(rows)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["time"] = pd.to_datetime(pd.to_numeric(df["start"]), unit="s", utc=True)
        df = (
            df.drop(columns=["start"])
            .drop_duplicates(subset="time")
            .set_index("time")
            .sort_index()[["open", "high", "low", "close", "volume"]]
        )
        if self._cache_enabled:
            self._cache[(product_id, granularity)] = df
        return df.tail(n_bars)

    def spot_price(self, product_id: str) -> float:
        data = self._get_json(f"{PUBLIC_BASE}/products/{product_id}", {})
        return float(data["price"])


# ---------------------------------------------------------------------------
# Courtier LIVE -- necessite les cles API et le SDK coinbase-advanced-py
# ---------------------------------------------------------------------------
class LiveBroker(Broker):
    def __init__(self, cfg: BotConfig, market: MarketData):
        if not cfg.secrets.present:
            raise ValueError("LiveBroker: cles API absentes")
        try:
            from coinbase.rest import RESTClient  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "Installe le SDK : pip install coinbase-advanced-py"
            ) from exc

        self.cfg = cfg
        self.market = market
        self.product_id = cfg.market.product_id
        self.base_ccy, self.quote_ccy = self.product_id.split("-")
        self._client = RESTClient(api_key=cfg.secrets.api_key, api_secret=cfg.secrets.api_secret)
        p = self._client.get_product(self.product_id)
        self.base_increment = float(getattr(p, "base_increment", "0.00000001"))
        self.quote_increment = float(getattr(p, "quote_increment", "0.01"))

    # -- helpers d'arrondi -----------------------------------------
    @staticmethod
    def _round_step(value: float, step: float) -> float:
        return round(round(value / step) * step, 10)

    def _round_base(self, qty: float) -> float:
        return self._round_step(qty, self.base_increment)

    def _round_price(self, price: float) -> float:
        return self._round_step(price, self.quote_increment)

    # -- lecture des comptes -------------------------------------
    def _balances(self) -> dict[str, float]:
        out: dict[str, float] = {}
        resp = self._client.get_accounts()
        for acc in getattr(resp, "accounts", []):
            bal = getattr(acc, "available_balance", None)
            val = float(bal["value"]) if isinstance(bal, dict) else float(getattr(bal, "value", 0))
            out[getattr(acc, "currency", "?")] = val
        return out

    def balances(self) -> dict[str, float]:
        """Soldes disponibles par devise (lecture seule -- permission 'View')."""
        return self._balances()

    def get_cash(self) -> float:
        return self._balances().get(self.quote_ccy, 0.0)

    def get_position(self) -> Position:
        qty = self._balances().get(self.base_ccy, 0.0)
        return Position(qty=qty, avg_price=0.0)  # avg_price non suivi cote exchange

    def mark_price(self, price: float) -> None:  # no-op : le live lit le prix reel
        pass

    def equity(self, mark: float) -> float:
        b = self._balances()
        return b.get(self.quote_ccy, 0.0) + b.get(self.base_ccy, 0.0) * mark

    # -- passage d'ordres --------------------------------------
    def _poll_fill(self, order_id: str, timeout: float) -> tuple[float, float, float, str]:
        """Retourne (filled_qty, avg_price, fees, status) en sondant l'ordre."""
        deadline = time.time() + timeout
        last = (0.0, 0.0, 0.0, "UNKNOWN")
        while time.time() < deadline:
            o = self._client.get_order(order_id)
            od = getattr(o, "order", o)
            status = str(getattr(od, "status", "")).upper()
            filled = float(getattr(od, "filled_size", 0) or 0)
            avg = float(getattr(od, "average_filled_price", 0) or 0)
            fees = float(getattr(od, "total_fees", 0) or 0)
            last = (filled, avg, fees, status)
            if status in ("FILLED", "CANCELLED", "EXPIRED", "FAILED"):
                return last
            time.sleep(1.0)
        return last

    def _submit(self, side: str, qty: float, ref_price: float, *, maker: bool) -> Fill:
        coid = uuid.uuid4().hex
        qty = self._round_base(qty)
        if qty <= 0:
            return Fill(side, 0.0, ref_price, 0.0, "maker" if maker else "taker")

        if maker:
            off = self.cfg.execution.limit_offset_bps / 10_000
            # limit a l'interieur du spread pour maximiser la proba de fill maker
            limit_price = ref_price * (1 - off) if side == BUY else ref_price * (1 + off)
            limit_price = self._round_price(limit_price)
            fn = self._client.limit_order_gtc
            resp = fn(
                client_order_id=coid,
                product_id=self.product_id,
                side=side,
                base_size=str(qty),
                limit_price=str(limit_price),
                post_only=True,
            )
        else:
            if side == BUY:
                resp = self._client.market_order_buy(
                    client_order_id=coid,
                    product_id=self.product_id,
                    quote_size=str(self._round_price(qty * ref_price)),
                )
            else:
                resp = self._client.market_order_sell(
                    client_order_id=coid, product_id=self.product_id, base_size=str(qty)
                )

        success = getattr(resp, "success", True)
        order_id = None
        sr = getattr(resp, "success_response", None)
        if sr is not None:
            order_id = sr["order_id"] if isinstance(sr, dict) else getattr(sr, "order_id", None)
        order_id = order_id or getattr(resp, "order_id", None)
        if not success or not order_id:
            raise RuntimeError(f"Echec ordre {side}: {getattr(resp, 'error_response', resp)}")

        timeout = self.cfg.execution.order_timeout_sec if maker else 30
        filled, avg, fees, status = self._poll_fill(order_id, timeout)

        if maker and status != "FILLED" and filled <= 0:
            try:
                self._client.cancel_orders(order_ids=[order_id])
            except Exception:  # noqa: BLE001
                pass
            raise OrderNotFilled(f"{side} maker non rempli ({status})")

        avg = avg or ref_price
        return Fill(side, filled, avg, fees, "maker" if maker else "taker")

    def buy(self, qty: float, ref_price: float, *, maker: bool) -> Fill:
        return self._submit(BUY, qty, ref_price, maker=maker)

    def sell(self, qty: float, ref_price: float, *, maker: bool) -> Fill:
        return self._submit(SELL, qty, ref_price, maker=maker)
