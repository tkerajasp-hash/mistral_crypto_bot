"""Stratégie DCA + Trailing Stop Intelligent.

Stratégie de trading :
1. Entrée initiale sur cassure Donchian (ou autre condition)
2. DCA sur pullbacks : 3 entrées à 33% du capital à -5%, -10%, -15%
3. Trailing stop fixe à 10% sous le plus haut atteint depuis l'entrée
4. Take profit à 3x le risque (ou valeur fixe)

Pipeline :
  - Filtre de tendance (EMA200 + pente) pour éviter les marchés baissiers
  - Confirmation ADX pour éviter les ranges
  - Entrée initiale sur cassure
  - DCA sur pullbacks avec délai
  - Trailing stop à 10% (ne redescend jamais)
  - Take profit optionnel
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Ajouter le dossier courant au path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd

from indicators import ema, slope, donchian_high, adx


# Actions
HOLD = "hold"
ENTER_LONG = "enter_long"
DCA_ENTER = "dca_enter"  # Entrée DCA
EXIT = "exit"
TAKE_PROFIT = "take_profit"


@dataclass
class Signal:
    """Signal de trading pour la stratégie DCA."""
    action: str          # hold, enter_long, dca_enter, exit, take_profit
    price: float         # Prix actuel
    reason: str          # Raison du signal
    atr: float = 0.0
    adx: float = 0.0
    dca_level: Optional[int] = None  # Niveau DCA (1, 2, 3)


@dataclass
class DCAState:
    """État de la stratégie DCA pour une position."""
    active: bool = False
    entry_price: float = 0.0
    initial_stop: float = 0.0
    current_dca_level: int = 0  # 0 = pas encore entré, 1, 2, 3 = niveaux DCA
    last_dca_bar: int = 0       # Dernière bougie où DCA a été déclenché
    highest_high: float = 0.0   # Plus haut depuis l'entrée (pour trailing stop)
    
    def reset(self) -> None:
        """Réinitialise l'état DCA."""
        self.active = False
        self.entry_price = 0.0
        self.initial_stop = 0.0
        self.current_dca_level = 0
        self.last_dca_bar = 0
        self.highest_high = 0.0
    
    def on_enter(self, entry_price: float, initial_stop_pct: float = 15.0, is_dca: bool = False, dca_level: Optional[int] = None) -> None:
        """Appelé quand on entre en position."""
        if not self.active:
            self.active = True
            self.entry_price = entry_price
            self.initial_stop = entry_price * (1 - initial_stop_pct / 100)
            self.current_dca_level = 1
            self.highest_high = entry_price
        else:
            # Entrée DCA
            self.current_dca_level = dca_level or self.current_dca_level + 1


class DCATrailingStrategy:
    """Stratégie DCA + Trailing Stop."""
    
    def __init__(
        self,
        entry_mode: str = "dca_on_pullback",
        initial_entry_condition: str = "donchian_breakout",
        dca_levels: int = 3,
        dca_percentage: float = 0.33,
        dca_delay_bars: int = 6,
        dca_pullback_levels: list[float] = [-5.0, -10.0, -15.0],
        trailing_stop_pct: float = 10.0,
        initial_stop_pct: float = 15.0,
        take_profit_r_multiple: float = 3.0,
        trend_ema: int = 200,
        trend_slope_lookback: int = 20,
        breakout_lookback: int = 20,
        adx_period: int = 14,
        adx_min: float = 20.0,
        use_trend_filter: bool = True,
    ):
        self.entry_mode = entry_mode
        self.initial_entry_condition = initial_entry_condition
        self.dca_levels = dca_levels
        self.dca_percentage = dca_percentage
        self.dca_delay_bars = dca_delay_bars
        self.dca_pullback_levels = dca_pullback_levels
        self.trailing_stop_pct = trailing_stop_pct
        self.initial_stop_pct = initial_stop_pct
        self.take_profit_r_multiple = take_profit_r_multiple
        self.trend_ema = trend_ema
        self.trend_slope_lookback = trend_slope_lookback
        self.breakout_lookback = breakout_lookback
        self.adx_period = adx_period
        self.adx_min = adx_min
        self.use_trend_filter = use_trend_filter
        
        # Validation
        assert dca_levels == len(dca_pullback_levels), "dca_levels must match dca_pullback_levels"
        assert all(p < 0 for p in dca_pullback_levels), "Pullback levels must be negative"
        assert sum([dca_percentage] * dca_levels) <= 1.0, "Total DCA allocation exceeds 100%"

    # ------------------------------------------------------------------
    def min_bars(self) -> int:
        """Nombre minimum de bougies requises."""
        return max(
            self.trend_ema + self.trend_slope_lookback,
            self.breakout_lookback,
            self.adx_period,
        ) + 10

    # ------------------------------------------------------------------
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcule tous les indicateurs nécessaires."""
        out = df.copy()
        
        # Indicateurs de tendance
        out["ema_trend"] = ema(out["close"], self.trend_ema)
        out["ema_trend_slope"] = slope(out["ema_trend"], self.trend_slope_lookback)
        
        # Cassure Donchian
        out["breakout_high"] = donchian_high(out["close"], self.breakout_lookback)
        
        # ADX
        out["adx"] = adx(out["high"], out["low"], out["close"], self.adx_period)
        
        # ATR (pour le backtest, même si on utilise % fixe)
        out["atr"] = self._atr(out["high"], out["low"], out["close"], self.adx_period)
        
        return out

    # ------------------------------------------------------------------
    @staticmethod
    def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
        """Average True Range."""
        import numpy as np
        
        prev_close = close.shift(1)
        ranges = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        
        # Wilder smoothing (like RMA)
        return ranges.ewm(alpha=1.0/period, adjust=False).mean()

    # ------------------------------------------------------------------
    def _regime_ok(self, row: pd.Series) -> bool:
        """Le régime est-il haussier ?
        
        Avec use_trend_filter=True, on vérifie que la pente de l'EMA est positive
        (tendance haussière). On n'exige pas price > ema_trend car en pullback,
        le prix peut être en dessous de l'EMA.
        """
        if not self.use_trend_filter:
            return True
        
        slope = row.get("ema_trend_slope")
        
        if pd.isna(slope):
            return False
            
        # Pente EMA positive = tendance haussière
        return slope > 0

    # ------------------------------------------------------------------
    def _adx_ok(self, row: pd.Series) -> bool:
        """ADX suffisamment élevé ?"""
        adx_v = row.get("adx")
        if pd.isna(adx_v):
            return False
        return float(adx_v) >= self.adx_min

    # ------------------------------------------------------------------
    def evaluate(
        self,
        df: pd.DataFrame,
        in_position: bool,
        dca_state: DCAState,
        current_bar: int,
    ) -> Signal:
        """Évalue le signal pour la dernière bougie.
        
        Args:
            df: DataFrame avec les données OHLCV
            in_position: Position actuellement ouverte
            dca_state: État de la stratégie DCA
            current_bar: Index de la bougie courante
            
        Returns:
            Signal avec l'action à effectuer
        """
        data = self.compute(df)
        row = data.iloc[-1]
        prev = data.iloc[-2] if len(data) > 1 else row
        
        price = float(row["close"])
        atr_v = float(row.get("atr", 0)) if pd.notna(row.get("atr")) else 0.0
        adx_v = float(row.get("adx", 0)) if pd.notna(row.get("adx")) else 0.0
        
        regime_ok = self._regime_ok(row)
        adx_ok = self._adx_ok(row)
        
        # --- Pas en position : chercher une entrée ---
        if not in_position and not dca_state.active:
            return self._evaluate_entry(row, price, atr_v, regime_ok, adx_ok, data)
        
        # --- En position (DCA active) ---
        if dca_state.active:
            return self._evaluate_dca_position(
                row, price, atr_v, dca_state, current_bar, regime_ok
            )
        
        # --- En position simple (sans DCA) ---
        if in_position:
            return self._evaluate_position_exit(
                row, price, atr_v, dca_state, regime_ok
            )
        
        return Signal(HOLD, price, "Pas de signal", adx=adx_v, atr=atr_v)

    # ------------------------------------------------------------------
    def _evaluate_entry(
        self,
        row: pd.Series,
        price: float,
        atr_v: float,
        regime_ok: bool,
        adx_ok: bool,
        data: pd.DataFrame = None,
    ) -> Signal:
        """Évalue une nouvelle entrée.
        
        Utilise initial_entry_condition pour la première entrée :
        - donchian_breakout : entre sur cassure (achat au plus haut) - DÉCONSEILLÉ
        - pullback : entre sur pullback (achat au plus bas) - RECOMMANDÉ
        - immediate : entre dès que régime et ADX sont OK
        """
        # Pour le mode pullback, on utilise un filtre plus léger :
        # - On exige price > ema_trend OU slope > 0 (pas les deux)
        # - Cela permet d'entrer sur un pullback même si la pente est légèrement négative
        if self.initial_entry_condition == "pullback":
            if self.use_trend_filter:
                ema_trend = row.get("ema_trend")
                slope = row.get("ema_trend_slope")
                if pd.notna(ema_trend) and pd.notna(slope):
                    # Accepter si price > ema_trend OU slope > 0 (pas forcément les deux)
                    if not (price > ema_trend or slope > 0):
                        return Signal(
                            HOLD, price, f"Tendance faiblarde (prix:{price:.2f} vs EMA:{ema_trend:.2f}, pente:{slope:.2f})",
                            atr=atr_v, adx=0.0
                        )
            
            if not adx_ok:
                return Signal(
                    HOLD, price, f"ADX trop bas ({row.get('adx', 0):.1f} < {self.adx_min})",
                    atr=atr_v, adx=float(row.get("adx", 0))
                )
        else:
            # Pour les autres modes, on exige regime_ok
            if not regime_ok:
                return Signal(
                    HOLD, price, "Régime non haussier (EMA200)",
                    atr=atr_v, adx=0.0
                )
            
            if not adx_ok:
                return Signal(
                    HOLD, price, f"ADX trop bas ({row.get('adx', 0):.1f} < {self.adx_min})",
                    atr=atr_v, adx=float(row.get("adx", 0))
                )
        
        # Mode immediate : entrer dès que régime et ADX sont OK
        if self.initial_entry_condition == "immediate":
            return Signal(
                ENTER_LONG, price,
                f"Entrée immédiate | ADX {row.get('adx', 0):.1f}",
                atr=atr_v, adx=float(row.get("adx", 0))
            )
        
        # Mode cassure : entrer sur breakout
        if self.initial_entry_condition == "donchian_breakout":
            breakout_high = row.get("breakout_high")
            if pd.notna(breakout_high) and price > breakout_high:
                return Signal(
                    ENTER_LONG, price,
                    f"Cassure Donchian ({self.breakout_lookback} bougies) | ADX {row.get('adx', 0):.1f}",
                    atr=atr_v, adx=float(row.get("adx", 0))
                )
        
        # Mode pullback : entrer sur pullback vers EMA (RECOMMANDÉ)
        if self.initial_entry_condition == "pullback":
            if data is not None and len(data) >= 2:
                ema_trend = data["ema_trend"].iloc[-1] if "ema_trend" in data.columns else None
                if pd.notna(ema_trend):
                    # Calculer pullback par rapport à EMA
                    pullback_from_ema = (price / ema_trend - 1) * 100
                    
                    # Vérifier que le prix est en pullback (0 à -5% sous EMA)
                    # et montre des signes de rebond (prix > prix précédent)
                    prev_price = float(data["close"].iloc[-2])
                    
                    # Entrer si :
                    # 1. Prix est entre -10% et +5% par rapport à EMA20 (plus large pour plus d'opportunités)
                    # 2. Prix montre des signes de rebond (prix actuel > prix précédent)
                    if -10.0 <= pullback_from_ema <= 5.0 and price > prev_price:
                        return Signal(
                            ENTER_LONG, price,
                            f"Pullback vers EMA200 ({pullback_from_ema:.1f}%) + rebond | ADX {row.get('adx', 0):.1f}",
                            atr=atr_v, adx=float(row.get("adx", 0))
                        )
        
        return Signal(HOLD, price, "Pas de signal d'entrée", atr=atr_v, adx=0.0)

    # ------------------------------------------------------------------
    def _evaluate_dca_position(
        self,
        row: pd.Series,
        price: float,
        atr_v: float,
        dca_state: DCAState,
        current_bar: int,
        regime_ok: bool,
    ) -> Signal:
        """Évalue une position avec DCA active.
        
        NOUVELLE LOGIQUE :
        - Phase 1 : Accumulation (DCA) - NE PAS SORTIR tant que DCA possible
        - Phase 2 : Trailing Stop - SORTIR uniquement si stop touché
        
        LES DCA SE DÉCLENCHENT PAR RAPPORT AU PLUS HAUT (highest_high),
        PAS PAR RAPPORT AU PRIX D'ENTRÉE INITIAL.
        
        Cela permet d'acheter sur les baisses par rapport au sommet,
        ce qui est la bonne stratégie pour battre le buy and hold.
        """
        # Mettre à jour le plus haut
        dca_state.highest_high = max(dca_state.highest_high, float(row["high"]))
        
        # PHASE 1 : ACCUMULATION - NE PAS SORTIR tant que DCA possible
        if dca_state.current_dca_level < self.dca_levels:
            # Vérifier délai depuis dernière DCA
            if current_bar - dca_state.last_dca_bar < self.dca_delay_bars:
                # Attendre le délai
                pullback_from_high = (price / dca_state.highest_high - 1) * 100
                return Signal(
                    HOLD, price,
                    f"Attente délai DCA (niveau {dca_state.current_dca_level + 1}) | pullback: {pullback_from_high:.1f}%",
                    adx=0, atr=atr_v
                )
            
            # CORRECTIF : Calculer pullback par rapport au PLUS HAUT (highest_high)
            # Cela permet d'acheter sur les baisses par rapport au sommet
            pullback_from_high_pct = (price / dca_state.highest_high - 1) * 100
            required_pullback = self.dca_pullback_levels[dca_state.current_dca_level]
            
            if pullback_from_high_pct <= required_pullback:
                next_level = dca_state.current_dca_level + 1
                return Signal(
                    DCA_ENTER, price,
                    f"DCA Niveau {next_level} : pullback {pullback_from_high_pct:.1f}% vs PLUS HAUT (seuil: {required_pullback}%)",
                    dca_level=next_level,
                    adx=0, atr=atr_v
                )
            
            # NE PAS VÉRIFIER LA SORTIE pendant la phase DCA
            return Signal(HOLD, price, f"Phase DCA : attente pullback (actuel: {pullback_from_high_pct:.1f}% vs plus haut)", adx=0, atr=atr_v)
        
        # PHASE 2 : TRAILING STOP - Toutes les DCA faites
        # Calculer le trailing stop
        trailing_stop = dca_state.highest_high * (1 - self.trailing_stop_pct / 100)
        initial_stop = dca_state.entry_price * (1 - self.initial_stop_pct / 100)
        effective_stop = max(trailing_stop, initial_stop)
        
        # Vérifier sortie par stop (UNIQUEMENT en phase 2)
        if float(row["low"]) <= effective_stop:
            return Signal(
                EXIT, price,
                f"STOP LOSS @ {effective_stop:.2f} (trailing: {trailing_stop:.2f}, initial: {initial_stop:.2f})",
                adx=0, atr=atr_v
            )
        
        return Signal(HOLD, price, "Phase 2 : position complète, trailing stop actif", adx=0, atr=atr_v)

    # ------------------------------------------------------------------
    def _evaluate_position_exit(
        self,
        row: pd.Series,
        price: float,
        atr_v: float,
        dca_state: DCAState,
        regime_ok: bool,
    ) -> Signal:
        """Évalue la sortie d'une position simple (sans DCA)."""
        # Mettre à jour le plus haut
        dca_state.highest_high = max(dca_state.highest_high, float(row["high"]))
        
        # Calculer le trailing stop
        trailing_stop = dca_state.highest_high * (1 - self.trailing_stop_pct / 100)
        initial_stop = dca_state.entry_price * (1 - self.initial_stop_pct / 100)
        effective_stop = max(trailing_stop, initial_stop)
        
        # Vérifier sortie par stop
        if float(row["low"]) <= effective_stop:
            return Signal(
                EXIT, price,
                f"STOP LOSS @ {effective_stop:.2f}",
                adx=0, atr=atr_v
            )
        
        # Vérifier take profit (UNIQUEMENT si activé)
        if self.take_profit_r_multiple is not None:
            risk_per_unit = dca_state.entry_price - effective_stop
            if risk_per_unit > 0:
                take_profit = dca_state.entry_price + (self.take_profit_r_multiple * risk_per_unit)
                if price >= take_profit:
                    return Signal(
                        TAKE_PROFIT, price,
                        f"TAKE PROFIT @ {take_profit:.2f} (R={self.take_profit_r_multiple:.1f})",
                        adx=0, atr=atr_v
                    )
        
        return Signal(HOLD, price, "Position en cours", adx=0, atr=atr_v)

    # ------------------------------------------------------------------
    def on_enter(
        self,
        entry_price: float,
        dca_state: DCAState,
        is_dca: bool = False,
        dca_level: Optional[int] = None,
    ) -> None:
        """Appelé quand on entre en position."""
        if not dca_state.active:
            dca_state.active = True
            dca_state.entry_price = entry_price
            dca_state.current_dca_level = 1
            dca_state.highest_high = entry_price
        else:
            # Entrée DCA
            dca_state.current_dca_level = dca_level or dca_state.current_dca_level + 1
        
        dca_state.last_dca_bar = 0  # Réinitialiser pour la prochaine entrée

    # ------------------------------------------------------------------
    def on_exit(self, dca_state: DCAState) -> None:
        """Appelé quand on sort de position."""
        dca_state.reset()
