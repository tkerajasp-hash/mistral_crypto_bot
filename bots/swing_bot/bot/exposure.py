"""Pilotage dynamique de l'exposition -- 4 briques, activees par `risk.exposure_control`.

Objectif : garder un gros sizing en tendance saine, mais le COUPER vite quand une
baisse brutale / un vrai bear market se dessine.  Toutes les briques ne font que
REDUIRE la taille (jamais l'augmenter au-dela du risk_per_trade de base si
vol_mult_cap = 1.0).

  1. Vol targeting     taille *= clip(vol_ref / ATR%_courant, floor, cap)
                       (un krach = un pic de vol -> la taille tombe toute seule)
  2. Frein de krach    chute brutale (rendement N bougies < -k*ATR%, ou close tres
                       en dessous de l'EMA rapide) -> exposition 0 pendant M bougies
                       (sortie forcee si en position)
  3. Throttle drawdown  au-dela de -X% du pic d'equity, taille reduite lineairement
  4. Anti-whipsaw      taille reduite pendant K bougies apres chaque sortie
                       (evite de re-rentrer a fond dans un faux rebond)

Briques 1 et 2 ne dependent que du marche -> precalculees en colonnes par
`attach_market_signals`.  Briques 3 et 4 dependent de l'etat du portefeuille ->
evaluees barre par barre via `entry_multiplier`.

Litterature : Moreira & Muir 2017 (volatility-managed portfolios), Harvey et al.
2018 (impact of volatility targeting), Faber 2007 (MA rule), Perold & Sharpe 1988
(CPPI / drawdown control).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import RiskConfig


@dataclass
class ExposureState:
    """Entrees "cote portefeuille" du multiplicateur d'exposition."""
    equity: float
    peak_equity: float
    bars_since_exit: int    # tres grand si aucune sortie encore


# ---------------------------------------------------------------------------
# Briques 1 & 2 : signaux de marche (precalcul vectorise sur tout le df)
# ---------------------------------------------------------------------------
def attach_market_signals(df: pd.DataFrame, r: RiskConfig) -> pd.DataFrame:
    """Ajoute `exp_vol_mult` (float) et `exp_crash_brake` (bool). `df` doit deja
    contenir les colonnes `atr`, `close`, `ema_fast` (fournies par TrendStrategy.compute)."""
    out = df.copy()
    atr_pct = (out["atr"] / out["close"]).replace([np.inf, -np.inf], np.nan)

    if r.vol_target_pct and r.vol_target_pct > 0:
        vol_ref = pd.Series(r.vol_target_pct, index=out.index)
    else:
        win = max(int(r.vol_target_lookback), 20)
        vol_ref = atr_pct.rolling(win, min_periods=max(win // 4, 10)).median()
        vol_ref = vol_ref.bfill()   # amorçage : avant d'avoir la fenetre, on prend la 1re valeur connue

    mult = (vol_ref / atr_pct).clip(lower=r.vol_mult_floor, upper=r.vol_mult_cap)
    out["exp_vol_mult"] = mult.fillna(1.0)

    ret_n = out["close"].pct_change(max(int(r.crash_return_bars), 1))
    crash_by_ret = ret_n < -(r.crash_return_atr * atr_pct)
    crash_by_ema = out["close"] < (out["ema_fast"] - r.crash_ema_atr * out["atr"])
    trig = (crash_by_ret.fillna(False) | crash_by_ema.fillna(False))
    # le frein reste arme `crash_brake_bars` bougies apres le dernier declenchement
    hold = max(int(r.crash_brake_bars), 1)
    out["exp_crash_brake"] = trig.rolling(hold, min_periods=1).max().fillna(0).astype(bool)
    return out


# ---------------------------------------------------------------------------
# Briques 3 & 4 : etat portefeuille
# ---------------------------------------------------------------------------
def dd_throttle(equity: float, peak_equity: float, r: RiskConfig) -> float:
    if peak_equity <= 0:
        return 1.0
    dd = (peak_equity - equity) / peak_equity
    if dd <= r.dd_throttle_start:
        return 1.0
    span = max(r.dd_throttle_start, 1e-9)          # rampe lineaire de start -> 2*start
    frac = min((dd - r.dd_throttle_start) / span, 1.0)
    return max(1.0 - frac * (1.0 - r.dd_throttle_floor), r.dd_throttle_floor)


def whipsaw_mult(bars_since_exit: int, r: RiskConfig) -> float:
    return r.whipsaw_mult if bars_since_exit < max(int(r.whipsaw_bars), 0) else 1.0


# ---------------------------------------------------------------------------
# API utilisee par backtest.py et engine.py
# ---------------------------------------------------------------------------
def crash_active(row: pd.Series, r: RiskConfig) -> bool:
    return bool(r.exposure_control and bool(row.get("exp_crash_brake", False)))


def entry_multiplier(row: pd.Series, st: ExposureState, r: RiskConfig) -> tuple[float, str]:
    """Multiplicateur total a appliquer a `position_size` pour une entree a cette barre."""
    if not r.exposure_control:
        return 1.0, ""
    m_vol = row.get("exp_vol_mult", 1.0)
    m_vol = float(m_vol) if pd.notna(m_vol) else 1.0
    m_dd = dd_throttle(st.equity, st.peak_equity, r)
    m_ws = whipsaw_mult(st.bars_since_exit, r)
    mult = max(m_vol * m_dd * m_ws, 0.0)
    return mult, f"expo x{mult:.2f} (vol {m_vol:.2f} | dd {m_dd:.2f} | ws {m_ws:.2f})"
