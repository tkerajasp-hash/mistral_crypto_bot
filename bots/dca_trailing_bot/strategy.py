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
    initial_cash: float = 10000.0  # Capital initial
    available_funds: float = 10000.0  # Fonds disponibles pour DCA
    
    # === NOUVEAUX CHAMPS POUR DCA AGRESSIF ===
    total_invested: float = 0.0  # Montant total investi
    current_exposure: float = 0.0  # Exposition actuelle (0-1)
    aggressive_dca_active: bool = False  # DCA agressif en cours
    aggressive_dca_step: int = 0  # Étape actuelle du DCA agressif
    last_aggressive_dca_bar: int = 0  # Dernière bougie DCA agressif
    
    def reset(self) -> None:
        """Réinitialise l'état DCA."""
        self.active = False
        self.entry_price = 0.0
        self.initial_stop = 0.0
        self.current_dca_level = 0
        self.last_dca_bar = 0
        self.highest_high = 0.0
        self.available_funds = self.initial_cash
        self.total_invested = 0.0
        self.current_exposure = 0.0
        self.aggressive_dca_active = False
        self.aggressive_dca_step = 0
        self.last_aggressive_dca_bar = 0
    
    def update_exposure(self, amount: float, price: float) -> None:
        """Met à jour l'exposition et les fonds investis."""
        self.total_invested += amount
        self.available_funds -= amount
        if self.initial_cash > 0:
            self.current_exposure = self.total_invested / self.initial_cash
    
    def get_remaining_exposure(self, target: float = 1.0) -> float:
        """Calcule l'exposition restante jusqu'à la cible."""
        return max(0.0, target - self.current_exposure)
    
    def on_enter(self, entry_price: float, initial_stop_pct: float = 15.0, is_dca: bool = False, dca_level: Optional[int] = None, amount: float = 0.0) -> None:
        """Appelé quand on entre en position."""
        if not self.active:
            self.active = True
            self.entry_price = entry_price
            self.initial_stop = entry_price * (1 - initial_stop_pct / 100)
            self.current_dca_level = 1
            self.highest_high = entry_price
            # Initialiser l'exposition avec la première entrée
            if amount > 0:
                self.update_exposure(amount, entry_price)
        else:
            # Entrée DCA
            self.current_dca_level = dca_level or self.current_dca_level + 1
            # Mettre à jour l'exposition
            if amount > 0:
                self.update_exposure(amount, entry_price)


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
        dca_use_atr_levels: bool = False,
        dca_pullback_atr_multipliers: list[float] = [1.5, 2.5, 3.5],
        trailing_stop_pct: float = 10.0,
        initial_stop_pct: float = 15.0,
        take_profit_r_multiple: float = 3.0,
        trend_ema: int = 200,
        trend_slope_lookback: int = 20,
        breakout_lookback: int = 20,
        adx_period: int = 14,
        adx_min: float = 20.0,
        use_trend_filter: bool = True,
        # NOUVELLES OPTIONS
        use_available_funds: bool = False,
        dca_available_funds_percentage: float = 0.50,
        use_dca_confirmation: bool = False,
        dca_confirmation_mode: str = "rsi_ema",
        use_enhanced_trend_filter: bool = False,
        trend_ema_fast: int = 50,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        confirm_ema_fast: int = 20,
        # === DCA AGRESSIF EN PHASE HAUSSIÈRE (NOUVEAU) ===
        aggressive_dca_enabled: bool = True,
        aggressive_dca_target_exposure: float = 1.0,
        aggressive_dca_investment_steps: int = 2,
        aggressive_dca_step_percentage: float = 0.50,
        aggressive_dca_step_delay_bars: int = 6,
        aggressive_dca_require_pullback: bool = True,
        aggressive_dca_pullback_levels: list[float] = [-3.0, -5.0],
        aggressive_dca_max_price_increase_pct: float = 8.0,
        aggressive_dca_consecutive_bars: int = 5,
    ):
        self.entry_mode = entry_mode
        self.initial_entry_condition = initial_entry_condition
        self.dca_levels = dca_levels
        self.dca_percentage = dca_percentage
        self.dca_delay_bars = dca_delay_bars
        self.dca_pullback_levels = dca_pullback_levels
        self.dca_use_atr_levels = dca_use_atr_levels
        self.dca_pullback_atr_multipliers = dca_pullback_atr_multipliers
        self.trailing_stop_pct = trailing_stop_pct
        self.initial_stop_pct = initial_stop_pct
        self.take_profit_r_multiple = take_profit_r_multiple
        self.trend_ema = trend_ema
        self.trend_slope_lookback = trend_slope_lookback
        self.breakout_lookback = breakout_lookback
        self.adx_period = adx_period
        self.adx_min = adx_min
        self.use_trend_filter = use_trend_filter
        
        # NOUVELLES CONFIGURATIONS
        self.use_available_funds = use_available_funds
        self.dca_available_funds_percentage = dca_available_funds_percentage
        self.use_dca_confirmation = use_dca_confirmation
        self.dca_confirmation_mode = dca_confirmation_mode
        self.use_enhanced_trend_filter = use_enhanced_trend_filter
        self.trend_ema_fast = trend_ema_fast
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.confirm_ema_fast = confirm_ema_fast
        
        # === DCA AGRESSIF EN PHASE HAUSSIÈRE ===
        self.aggressive_dca_enabled = aggressive_dca_enabled
        self.aggressive_dca_target_exposure = aggressive_dca_target_exposure
        self.aggressive_dca_investment_steps = aggressive_dca_investment_steps
        self.aggressive_dca_step_percentage = aggressive_dca_step_percentage
        self.aggressive_dca_step_delay_bars = aggressive_dca_step_delay_bars
        self.aggressive_dca_require_pullback = aggressive_dca_require_pullback
        self.aggressive_dca_pullback_levels = aggressive_dca_pullback_levels
        self.aggressive_dca_max_price_increase_pct = aggressive_dca_max_price_increase_pct
        self.aggressive_dca_consecutive_bars = aggressive_dca_consecutive_bars
        
        # Validation
        assert dca_levels == len(dca_pullback_levels), "dca_levels must match dca_pullback_levels"
        assert all(p < 0 for p in dca_pullback_levels), "Pullback levels must be negative"
        if not dca_use_atr_levels:
            assert sum([dca_percentage] * dca_levels) <= 1.0, "Total DCA allocation exceeds 100%"
        assert dca_confirmation_mode in ["rsi_ema", "ema_cross", "slope_positive"], "Invalid dca_confirmation_mode"
        
        # Validation DCA agressif
        if self.aggressive_dca_enabled:
            assert 0 < self.aggressive_dca_target_exposure <= 1.0, "Target exposure must be between 0 and 1"
            assert self.aggressive_dca_investment_steps > 0, "Investment steps must be > 0"
            assert 0 < self.aggressive_dca_step_percentage <= 1.0, "Step percentage must be between 0 and 1"

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
        
        # NOUVEAU: EMA rapide pour double confirmation (si use_enhanced_trend_filter)
        if self.use_enhanced_trend_filter:
            out["ema_fast"] = self._ema(out["close"], self.trend_ema_fast)
        
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
    def _check_uptrend_confirmed(self, data: pd.DataFrame) -> bool:
        """Vérifie si nous sommes en phase haussière avérée.
        
        Conditions pour une phase haussière confirmée:
        1. Prix > EMA200
        2. Pente EMA200 > 0 (tendance haussière)
        3. ADX > adx_min (tendance forte, pas un range)
        4. N bougies consécutives en hausse
        """
        if not self.aggressive_dca_enabled:
            return False
        
        if len(data) < max(self.trend_ema, self.trend_slope_lookback, self.adx_period, 2):
            return False
        
        row = data.iloc[-1]
        
        # 1. Prix > EMA200
        ema200 = data["ema_trend"].iloc[-1]
        price = float(row["close"])
        if pd.isna(ema200) or price <= ema200:
            return False
        
        # 2. Pente EMA200 > 0
        slope = data["ema_trend_slope"].iloc[-1]
        if pd.isna(slope) or slope <= 0:
            return False
        
        # 3. ADX > adx_min
        adx_val = float(row.get("adx", 0))
        if pd.isna(adx_val) or adx_val < self.adx_min:
            return False
        
        # 4. N bougies consécutives en hausse
        consecutive_up = 0
        for i in range(-1, -min(20, len(data)), -1):
            if i == -1:
                continue
            if float(data["close"].iloc[i]) > float(data["close"].iloc[i-1]):
                consecutive_up += 1
            else:
                break
        
        if consecutive_up < self.aggressive_dca_consecutive_bars:
            return False
        
        return True

    # ------------------------------------------------------------------
    def _rsi(self, close: pd.Series, period: int = 14) -> float:
        """Calcule le RSI (Relative Strength Index)."""
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    # ------------------------------------------------------------------
    def _rsi_ok(self, row: pd.Series, data: pd.DataFrame) -> bool:
        """RSI montre une survente ?"""
        if not self.use_dca_confirmation or self.dca_confirmation_mode != "rsi_ema":
            return True  # Pas besoin de confirmation
        
        if len(data) < self.rsi_period + 1:
            return False
        
        close = data["close"]
        rsi = self._rsi(close, self.rsi_period)
        rsi_value = rsi.iloc[-1]
        
        if pd.isna(rsi_value):
            return False
        
        return float(rsi_value) <= self.rsi_oversold

    # ------------------------------------------------------------------
    def _ema_cross_ok(self, row: pd.Series, data: pd.DataFrame) -> bool:
        """EMA rapide a croisé EMA lente à la hausse ?"""
        if not self.use_dca_confirmation or self.dca_confirmation_mode != "ema_cross":
            return True
        
        if len(data) < max(self.confirm_ema_fast, self.trend_ema) + 2:
            return False
        
        ema_fast = self._ema(data["close"], self.confirm_ema_fast)
        ema_slow = self._ema(data["close"], self.trend_ema)
        
        if len(ema_fast) < 2 or len(ema_slow) < 2:
            return False
        
        # Vérifier croisement haussier: EMA rapide > EMA lente
        fast_prev = ema_fast.iloc[-2]
        fast_curr = ema_fast.iloc[-1]
        slow_prev = ema_slow.iloc[-2]
        slow_curr = ema_slow.iloc[-1]
        
        # Croisement: fast_prev <= slow_prev et fast_curr > slow_curr
        return fast_prev <= slow_prev and fast_curr > slow_curr

    # ------------------------------------------------------------------
    def _slope_positive_ok(self, row: pd.Series, data: pd.DataFrame) -> bool:
        """La pente EMA est devenue positive ?"""
        if not self.use_dca_confirmation or self.dca_confirmation_mode != "slope_positive":
            return True
        
        if len(data) < self.trend_slope_lookback + 1:
            return False
        
        slope = data["ema_trend_slope"].iloc[-1]
        prev_slope = data["ema_trend_slope"].iloc[-2]
        
        if pd.isna(slope) or pd.isna(prev_slope):
            return False
        
        # Pente était négative ou nulle, devient positive
        return prev_slope <= 0 and slope > 0

    # ------------------------------------------------------------------
    def _dca_confirmation_ok(self, row: pd.Series, data: pd.DataFrame) -> bool:
        """Vérifie la confirmation pour le DCA.
        
        Selon dca_confirmation_mode:
        - rsi_ema: RSI < rsi_oversold ET prix > EMA(confirm_ema_fast)
        - ema_cross: EMA rapide a croisé EMA lente à la hausse
        - slope_positive: Pente EMA est devenue positive
        """
        if not self.use_dca_confirmation:
            return True
        
        if self.dca_confirmation_mode == "rsi_ema":
            # RSI < oversold ET prix > EMA rapide
            rsi_ok = self._rsi_ok(row, data)
            if not rsi_ok:
                return False
            
            # Prix > EMA rapide
            if len(data) < self.confirm_ema_fast + 1:
                return False
            ema_fast = self._ema(data["close"], self.confirm_ema_fast).iloc[-1]
            price = float(row["close"])
            return price > ema_fast
        
        elif self.dca_confirmation_mode == "ema_cross":
            return self._ema_cross_ok(row, data)
        
        elif self.dca_confirmation_mode == "slope_positive":
            return self._slope_positive_ok(row, data)
        
        return True

    # ------------------------------------------------------------------
    @staticmethod
    def _ema(close: pd.Series, period: int) -> pd.Series:
        """Calcule EMA."""
        return close.ewm(span=period, adjust=False).mean()

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
                row, price, atr_v, dca_state, current_bar, regime_ok, data
            )
        
        # --- En position simple (sans DCA) ---
        if in_position:
            return self._evaluate_position_exit(
                row, price, atr_v, dca_state, regime_ok, data
            )
        
        # === DCA AGRESSIF EN PHASE HAUSSIÈRE (NOUVEAU) ===
        # Vérifier si on peut déclencher un DCA agressif
        if (self.aggressive_dca_enabled and 
            dca_state.active and 
            dca_state.current_dca_level >= self.dca_levels):
            
            aggressive_signal = self._evaluate_aggressive_dca(
                row, price, atr_v, dca_state, current_bar, regime_ok, data
            )
            if aggressive_signal.action != HOLD:
                return aggressive_signal
        
        return Signal(HOLD, price, "Pas de signal", adx=adx_v, atr=atr_v)

    # ------------------------------------------------------------------
    def _evaluate_aggressive_dca(
        self,
        row: pd.Series,
        price: float,
        atr_v: float,
        dca_state: DCAState,
        current_bar: int,
        regime_ok: bool,
        data: pd.DataFrame,
    ) -> Signal:
        """Évalue et déclenche le DCA agressif en phase haussière.
        
        Logique:
        1. Vérifier qu'on est en phase haussière avérée
        2. Vérifier qu'on a pas déjà atteint l'exposition cible
        3. Vérifier qu'on a attendu le délai depuis la dernière entrée
        4. Vérifier qu'on est en pullback (si requis)
        5. Investir une partie du cash restant
        
        Returns:
            Signal DCA_ENTER si conditions remplies, HOLD sinon
        """
        # 1. Vérifier phase haussière avérée
        if not self._check_uptrend_confirmed(data):
            return Signal(HOLD, price, "Attente phase haussière pour DCA agressif", adx=0, atr=atr_v)
        
        # 2. Vérifier exposition actuelle
        remaining_exposure = dca_state.get_remaining_exposure(self.aggressive_dca_target_exposure)
        if remaining_exposure <= 0.01:  # 1% de marge
            return Signal(HOLD, price, f"Exposition cible atteinte ({dca_state.current_exposure:.0%})", adx=0, atr=atr_v)
        
        # 3. Vérifier délai depuis dernière entrée DCA (agressive ou classique)
        last_dca_bar = max(dca_state.last_dca_bar, dca_state.last_aggressive_dca_bar)
        if current_bar - last_dca_bar < self.aggressive_dca_step_delay_bars:
            return Signal(
                HOLD, price,
                f"Attente délai DCA agressif ({current_bar - last_dca_bar}/{self.aggressive_dca_step_delay_bars} bars)",
                adx=0, atr=atr_v
            )
        
        # 4. Vérifier pullback si requis
        if self.aggressive_dca_require_pullback:
            pullback_from_high_pct = (price / dca_state.highest_high - 1) * 100
            
            # Vérifier si on est dans un pullback acceptable
            pullback_ok = any(
                pullback_from_high_pct <= level
                for level in self.aggressive_dca_pullback_levels
            )
            
            if not pullback_ok:
                return Signal(
                    HOLD, price,
                    f"Attente pullback pour DCA agressif (actuel: {pullback_from_high_pct:.1f}%)",
                    adx=0, atr=atr_v
                )
            
            # Vérifier que le prix n'a pas trop monté depuis la dernière entrée
            if dca_state.highest_high > 0:
                price_increase_pct = (price / dca_state.highest_high - 1) * 100
                if price_increase_pct > self.aggressive_dca_max_price_increase_pct:
                    return Signal(
                        HOLD, price,
                        f"Prix trop élevé pour DCA agressif (+{price_increase_pct:.1f}% > {self.aggressive_dca_max_price_increase_pct}%)",
                        adx=0, atr=atr_v
                    )
        
        # 5. Calculer le montant à investir
        # Investir un pourcentage des fonds DISPONIBLES
        step_amount = dca_state.available_funds * self.aggressive_dca_step_percentage
        
        # Ne pas investir plus que nécessaire pour atteindre la cible
        amount_needed = remaining_exposure * dca_state.initial_cash
        step_amount = min(step_amount, amount_needed)
        
        if step_amount <= 10:  # Montant minimal
            return Signal(HOLD, price, "Montant DCA agressif trop faible", adx=0, atr=atr_v)
        
        # Incrémenter l'étape
        dca_state.aggressive_dca_step += 1
        dca_state.last_aggressive_dca_bar = current_bar
        
        # Retourner le signal DCA agressif
        return Signal(
            DCA_ENTER, price,
            f"⚡ DCA AGRESSIF Étape {dca_state.aggressive_dca_step} : "
            f"Investissement ${step_amount:.2f} | "
            f"Exposition: {dca_state.current_exposure:.0%} → {(dca_state.current_exposure + step_amount/dca_state.initial_cash):.0%} | "
            f"Phase haussière confirmée",
            dca_level=dca_state.aggressive_dca_step,
            adx=0, atr=atr_v
        )

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
            # NOUVEAU: Filtre de tendance renforcé si activé
            if self.use_trend_filter or self.use_enhanced_trend_filter:
                ema_trend = row.get("ema_trend")
                slope = row.get("ema_trend_slope")
                
                if pd.notna(ema_trend) and pd.notna(slope):
                    # Filtre standard: price > ema_trend OU slope > 0
                    if not (price > ema_trend or slope > 0):
                        return Signal(
                            HOLD, price, f"Tendance faiblarde (prix:{price:.2f} vs EMA:{ema_trend:.2f}, pente:{slope:.2f})",
                            atr=atr_v, adx=0.0
                        )
                    
                    # NOUVEAU: Double filtre si use_enhanced_trend_filter
                    if self.use_enhanced_trend_filter:
                        # Calculer EMA50 pour confirmation
                        if len(data) >= self.trend_ema_fast + 1:
                            ema_fast = self._ema(data["close"], self.trend_ema_fast).iloc[-1]
                            if pd.notna(ema_fast):
                                # Vérifier que prix > EMA50 (tendance courte terme haussière)
                                if price <= ema_fast:
                                    return Signal(
                                        HOLD, price,
                                        f"Double filtre échoué: prix {price:.2f} <= EMA{self.trend_ema_fast} {ema_fast:.2f}",
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
        data: pd.DataFrame,
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
            # current_dca_level commence à 1 après l'entrée initiale
            # dca_pullback_levels[0] est le premier niveau DCA
            required_pullback = self.dca_pullback_levels[dca_state.current_dca_level - 1]
            
            # VÉRIFIER LE NIVEAU DE PULLBACK
            if pullback_from_high_pct <= required_pullback:
                # VÉRIFIER CONFIRMATION (NOUVEAU: pas de DCA sans confirmation)
                if self.use_dca_confirmation and not self._dca_confirmation_ok(row, data):
                    return Signal(
                        HOLD, price,
                        f"Pullback {pullback_from_high_pct:.1f}% atteint mais CONFIRMATION manquante | wait confirmation",
                        adx=0, atr=atr_v
                    )
                
                # VÉRIFIER FONDS DISPONIBLES (NOUVEAU)
                next_level = dca_state.current_dca_level + 1
                if self.use_available_funds:
                    # Calculer le montant DCA basé sur les fonds DISPONIBLES
                    dca_amount = dca_state.available_funds * self.dca_available_funds_percentage
                    new_available = dca_state.available_funds - dca_amount
                    if dca_amount <= 0:
                        return Signal(
                            HOLD, price,
                            f"Pas assez de fonds pour DCA niveau {next_level} (disponible: ${dca_state.available_funds:.2f})",
                            adx=0, atr=atr_v
                        )
                else:
                    # Ancien système: % du capital initial
                    dca_amount = dca_state.initial_cash * self.dca_percentage
                    new_available = dca_state.available_funds - dca_amount
                
                # Mettre à jour les fonds disponibles
                dca_state.available_funds = new_available
                
                return Signal(
                    DCA_ENTER, price,
                    f"DCA Niveau {next_level} : pullback {pullback_from_high_pct:.1f}% vs PLUS HAUT | "
                    f"Montant: ${dca_amount:.2f} | Fonds restants: ${new_available:.2f}",
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
        data: pd.DataFrame,
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
            dca_state.initial_cash = dca_state.available_funds  # Sauvegarder le capital initial
        else:
            # Entrée DCA
            dca_state.current_dca_level = dca_level or dca_state.current_dca_level + 1
        
        dca_state.last_dca_bar = 0  # Réinitialiser pour la prochaine entrée

    # ------------------------------------------------------------------
    def on_exit(self, dca_state: DCAState) -> None:
        """Appelé quand on sort de position."""
        dca_state.reset()
    
    # ------------------------------------------------------------------
    def create_dca_state(self, initial_cash: float = 10000.0) -> DCAState:
        """Crée un nouvel état DCA avec le capital initial."""
        state = DCAState()
        state.initial_cash = initial_cash
        state.available_funds = initial_cash
        return state
