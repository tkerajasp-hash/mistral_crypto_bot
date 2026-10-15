"""Client Coinbase Advanced Trade pour le DCA Trailing Bot.

Ce module récupère les données de marché depuis Coinbase.
"""

from __future__ import annotations

import time
from typing import Optional

import pandas as pd
import requests


PUBLIC_BASE = "https://api.coinbase.com/api/v3/brokerage/market"
MAX_CANDLES_PER_REQ = 300


class MarketData:
    """Client pour récupérer les données de marché Coinbase."""
    
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "dca-trailing-bot/0.1"})
    
    def _get_json(self, url: str, params: dict) -> dict:
        """Effectue une requête GET avec retry."""
        for attempt in range(4):
            try:
                resp = self.session.get(url, params=params, timeout=15)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in (429, 500, 502, 503):
                    time.sleep(1.5 * (attempt + 1))
                    continue
                resp.raise_for_status()
            except requests.exceptions.RequestException:
                if attempt == 3:
                    raise
                time.sleep(2)
        
        return {}
    
    def get_candles(
        self,
        product_id: str,
        granularity: str,
        granularity_seconds: int,
        n_bars: int,
    ) -> pd.DataFrame:
        """Récupère les bougies OHLCV.
        
        Args:
            product_id: Identifiant du produit (ex: BTC-USDC)
            granularity: Granularité (ex: SIX_HOUR)
            granularity_seconds: Granularité en secondes
            n_bars: Nombre de bougies à récupérer
            
        Returns:
            DataFrame avec index datetime et colonnes ohlcv
        """
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
                    break
            
            cursor_end = start
            time.sleep(0.2)
        
        if not rows:
            raise RuntimeError(f"Aucune bougie renvoyée pour {product_id}")
        
        # Conversion en DataFrame
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
        
        return df.tail(n_bars)
    
    def spot_price(self, product_id: str) -> float:
        """Récupère le prix spot actuel."""
        data = self._get_json(f"{PUBLIC_BASE}/products/{product_id}", {})
        return float(data["price"])
    
    def get_ticker(self, product_id: str) -> dict:
        """Récupère le ticker 24h."""
        data = self._get_json(f"{PUBLIC_BASE}/products/{product_id}", {})
        return {
            "price": float(data.get("price", 0)),
            "price_percent_change_24h": float(data.get("price_percent_change_24h", 0)),
            "volume_24h": float(data.get("volume_24h", 0)),
        }
    
    def get_products(self) -> list[dict]:
        """Liste tous les produits disponibles."""
        data = self._get_json(f"{PUBLIC_BASE}/products", {})
        return data.get("products", [])
