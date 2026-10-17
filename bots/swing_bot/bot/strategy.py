"""Strategie de suivi de tendance haussiere (long-only, spot).

Pipeline de decision, evalue uniquement sur bougies CLOTUREES :

  1. Filtre de regime      : close > EMA(trend_ema) ET pente(EMA) > 0
  2. Filtre unite sup.     : (optionnel) daily close > EMA(htf_ema) daily
  3. Force de tendance     : ADX(adx_period) >= adx_min      -> ecarte les ranges
  4. Declencheur d'entree  : selon entry_mode
       - donchian_breakout    : cassure du plus haut des breakout_lookback clotures
       - ema_cross            : croisement EMA(ema_fast) au-dessus de EMA(ema_slow)
       - pullback             : dans une tendance haussiere confirmee, on ACHETE LE REPLI :
                                le prix est revenu <= EMA(ema_fast) dans les pullback_lookback
                                dernieres bougies puis repasse au-dessus en remontant.
                                -> entre plus tot et plus souvent dans un bull run.
       - breakout_or_pullback : l'un OU l'autre (cassure franche + rachats de repli)
  5. Sortie tendance       : cassure Donchian(exit_lookback) vers le bas
                             (le stop loss ATR est gere separement dans risk.py)
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import StrategyConfig
from . import indicators as ind

HOLD = "hold"
ENTER_LONG = "enter_long"
EXIT = "exit"


@dataclass
class Signal:
    action: str          # hold | enter_long | exit
    price: float          # close de la derniere bougie cloturee
    atr: float
    reason: str
    regime_ok: bool = False
    adx: float = 0.0


class TrendStrategy:
    def __init__(self, cfg: StrategyConfig):
        self.cfg = cfg

    # ------------------------------------------------------------------
    def min_bars(self) -> int:
        c = self.cfg
        return max(c.trend_ema + c.trend_slope_lookback, c.breakout_lookback, c.ema_slow, c.adx_period) + 5

    # ------------------------------------------------------------------
    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajoute les colonnes d'indicateurs. `df` indexe par temps, colonnes ohlcv."""
        c = self.cfg
        out = df.copy()
        out["ema_trend"] = ind.ema(out["close"], c.trend_ema)
        out["ema_trend_slope"] = ind.slope(out["ema_trend"], c.trend_slope_lookback)
        out["ema_fast"] = ind.ema(out["close"], c.ema_fast)
        out["ema_slow"] = ind.ema(out["close"], c.ema_slow)
        out["adx"] = ind.adx(out["high"], out["low"], out["close"], c.adx_period)
        # cassure "en cloture" : on compare le close aux N closes precedents
        # (plus robuste que comparer aux meches, et coherent entree/sortie)
        out["breakout_high"] = ind.donchian_high(out["close"], c.breakout_lookback)
        out["exit_low"] = ind.donchian_low(out["close"], c.exit_lookback)
        out["atr"] = ind.atr(out["high"], out["low"], out["close"], c.adx_period)
        # repli recent sur l'EMA rapide : 1.0 si le close est passe <= EMA(ema_fast)
        # au moins une fois dans les `pullback_lookback` dernieres bougies (bougie courante incluse)
        below_fast = (out["close"] <= out["ema_fast"]).astype(float)
        out["dip_recent"] = below_fast.rolling(max(c.pullback_lookback, 1)).max()
        return out

    # ------------------------------------------------------------------
    def _htf_ok(self, htf_df: pd.DataFrame | None) -> bool:
        if not self.cfg.htf_filter:
            return True
        if htf_df is None or len(htf_df) < self.cfg.htf_ema + 2:
            return False  # prudence : pas de donnee -> pas de trade
        htf_ema = ind.ema(htf_df["close"], self.cfg.htf_ema)
        return bool(htf_df["close"].iloc[-1] > htf_ema.iloc[-1])

    # ------------------------------------------------------------------
    def evaluate(self, df: pd.DataFrame, in_position: bool, htf_df: pd.DataFrame | None = None) -> Signal:
        """Decision sur la derniere ligne de `df` (supposee CLOTUREE)."""
        data = self.compute(df)
        return self.signal_from_row(
            data.iloc[-1], data.iloc[-2], in_position=in_position, htf_ok=self._htf_ok(htf_df)
        )

    # ------------------------------------------------------------------
    def signal_from_row(self, row: pd.Series, prev: pd.Series, *, in_position: bool, htf_ok: bool) -> Signal:
        """Meme logique que `evaluate`, mais sur des lignes deja enrichies par `compute`.

        Utilise par le backtester pour eviter de recalculer les indicateurs a chaque barre.
        """
        price = float(row["close"])
        atr_v = float(row["atr"]) if pd.notna(row["atr"]) else 0.0
        adx_v = float(row["adx"]) if pd.notna(row["adx"]) else 0.0

        # --- Filtre de regime : "strict" (defaut) ou "fast" -------------------
        #   strict : prix > EMA(trend_ema)  ET  pente(EMA trend) > 0 sur N bougies
        #            -> confirme mais lent a valider un nouveau bull run
        #   fast   : prix > EMA(trend_ema)  ET  EMA(ema_fast) > EMA(ema_slow)
        #            -> remplace la pente lente par un croisement d'EMA rapides,
        #               qui se retourne quelques jours apres un creux au lieu de semaines
        above_trend = pd.notna(row["ema_trend"]) and price > row["ema_trend"]
        if self.cfg.regime_mode == "fast":
            regime_ok = bool(
                above_trend
                and pd.notna(row["ema_fast"]) and pd.notna(row["ema_slow"])
                and row["ema_fast"] > row["ema_slow"]
            )
        else:
            regime_ok = bool(
                above_trend
                and pd.notna(row["ema_trend_slope"])
                and row["ema_trend_slope"] > 0
            )

        # ---- Position ouverte : chercher une sortie "tendance" -----------
        if in_position:
            if pd.notna(row["exit_low"]) and price < row["exit_low"]:
                return Signal(EXIT, price, atr_v, "cassure Donchian basse (sortie tendance)", regime_ok, adx_v)
            if not regime_ok:
                return Signal(EXIT, price, atr_v, "regime repasse baissier (close < EMA trend)", regime_ok, adx_v)
            return Signal(HOLD, price, atr_v, "tendance toujours haussiere", regime_ok, adx_v)

        # ---- Flat : chercher une entree ---------------------------------
        if not regime_ok:
            return Signal(HOLD, price, atr_v, "regime non haussier", regime_ok, adx_v)
        if adx_v < self.cfg.adx_min:
            return Signal(HOLD, price, atr_v, f"ADX {adx_v:.1f} < {self.cfg.adx_min} (range)", regime_ok, adx_v)
        if not htf_ok:
            return Signal(HOLD, price, atr_v, "unite de temps superieure non haussiere", regime_ok, adx_v)
        if atr_v <= 0:
            return Signal(HOLD, price, atr_v, "ATR indisponible", regime_ok, adx_v)

        mode = self.cfg.entry_mode
        reasons: list[str] = []

        if mode in ("donchian_breakout", "breakout_or_pullback"):
            if pd.notna(row["breakout_high"]) and price > row["breakout_high"]:
                reasons.append(f"cassure du plus haut {self.cfg.breakout_lookback} bougies")

        if mode in ("pullback", "breakout_or_pullback"):
            # repli rachete : on a touche l'EMA rapide recemment, le prix repasse
            # au-dessus ET remonte (close > close precedent) -> on entre dans la tendance
            dipped = pd.notna(row.get("dip_recent")) and row["dip_recent"] == 1.0
            reclaim = pd.notna(row["ema_fast"]) and price > row["ema_fast"] and price > float(prev["close"])
            if dipped and reclaim:
                reasons.append(f"repli rachete sur EMA{self.cfg.ema_fast}")

        if mode == "ema_cross":
            if prev["ema_fast"] <= prev["ema_slow"] and row["ema_fast"] > row["ema_slow"]:
                reasons.append(f"croisement EMA{self.cfg.ema_fast}>{self.cfg.ema_slow}")

        if reasons:
            return Signal(ENTER_LONG, price, atr_v,
                          " + ".join(reasons) + f" | ADX {adx_v:.1f}", regime_ok, adx_v)
        return Signal(HOLD, price, atr_v, "pas de declencheur d'entree", regime_ok, adx_v)
