"""Methodo de validation "durcie" d'une strategie.

But : ne pas se contenter d'un seul chiffre de performance sur une seule fenetre.
On mesure separement les deux missions du bot :

  1. NE PAS SE FAIRE PIEGER  -> combien de la baisse buy & hold on evite en marche baissier
  2. PROFITER DES HAUSSES    -> combien de la hausse buy & hold on capture en marche haussier

Trois outils :

  * regime_report   : decoupe l'historique en phases haussieres / baissieres (drawdown BTC)
                      et compare strat vs buy & hold phase par phase.
  * walk_forward    : rejoue la MEME strategie sur des sous-periodes successives
                      -> la perf est-elle reguliere ou portee par une seule fenetre ?
  * param_sweep     : fait varier UN parametre -> la strategie est-elle robuste
                      ou calee au petit bonheur (surapprentissage) ?

  python -m bot analyze --strategy conservative_6h --days 3400
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .backtest import run_backtest
from .coinbase_client import MarketData
from .config import BotConfig, VALID_GRANULARITIES

_BARS_PER_YEAR_DAY = 365.25


# ---------------------------------------------------------------------------
# metriques de base sur une courbe d'equity (index temporel, valeurs)
# ---------------------------------------------------------------------------
def _ret(eq: pd.Series) -> float:
    return float(eq.iloc[-1] / eq.iloc[0] - 1) if len(eq) > 1 else 0.0


def _max_dd(eq: pd.Series) -> float:
    if len(eq) < 2:
        return 0.0
    roll = eq.cummax()
    return float(((eq - roll) / roll).min())


def _cagr(eq: pd.Series) -> float:
    if len(eq) < 2:
        return 0.0
    years = max((eq.index[-1] - eq.index[0]).total_seconds() / 86400 / _BARS_PER_YEAR_DAY, 1e-9)
    base = eq.iloc[-1] / eq.iloc[0]
    return float(base ** (1 / years) - 1) if base > 0 else -1.0


def _sharpe(eq: pd.Series, bars_per_year: float) -> float:
    r = eq.pct_change().dropna()
    return float(r.mean() / r.std() * np.sqrt(bars_per_year)) if r.std() > 0 else 0.0


def _sortino(eq: pd.Series, bars_per_year: float) -> float:
    r = eq.pct_change().dropna()
    downside = r[r < 0]
    dd = downside.std()
    return float(r.mean() / dd * np.sqrt(bars_per_year)) if dd and dd > 0 else 0.0


# ---------------------------------------------------------------------------
# 1. decoupage en regimes haussier / baissier (sur le close BTC journalier)
# ---------------------------------------------------------------------------
@dataclass
class Segment:
    kind: str            # "haussier" | "baissier"
    start: pd.Timestamp
    end: pd.Timestamp
    bh_return: float     # perf buy & hold sur le segment
    bh_max_dd: float
    strat_return: float
    strat_max_dd: float
    avg_exposure: float = 0.0   # part moyenne de l'equity investie sur le segment

    @property
    def days(self) -> float:
        return (self.end - self.start).total_seconds() / 86400

    @property
    def score(self) -> float:
        """Haussier -> taux de capture de la hausse.  Baissier -> taux de perte evitee."""
        if self.kind == "haussier":
            return self.strat_return / self.bh_return if self.bh_return > 1e-9 else 0.0
        # baissier : 1.0 = on a tout evite, 0.0 = on a pris toute la baisse
        return 1.0 - (self.strat_return / self.bh_return) if self.bh_return < -1e-9 else 1.0


def detect_regimes(close: pd.Series, dd_threshold: float = 0.20) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    """Marche baissier = repli >= dd_threshold sous le plus haut glissant ;
    retour en haussier quand on refait un nouveau plus haut.
    Renvoie une liste de (kind, start, end) contigus."""
    peak = close.iloc[0]
    kind = "haussier"
    runs: list[list] = [[kind, close.index[0], close.index[0]]]
    for ts, px in close.items():
        peak = max(peak, px)
        if kind == "haussier" and px <= peak * (1 - dd_threshold):
            kind = "baissier"
            runs.append([kind, ts, ts])
        elif kind == "baissier" and px >= peak:      # nouveau plus haut -> tendance repartie
            kind = "haussier"
            runs.append([kind, ts, ts])
        runs[-1][2] = ts
    return [(k, s, e) for k, s, e in runs]


def regime_report(cfg: BotConfig, *, days: int, dd_threshold: float = 0.20,
                  md: MarketData | None = None) -> tuple[list[Segment], dict]:
    md = md or MarketData(cache=True)
    res = run_backtest(cfg, days=days, save_dir=None, md=md)
    eq = res.equity_curve
    if len(eq) < 10:
        raise RuntimeError("courbe d'equity trop courte")

    exp = res.exposure_curve if res.exposure_curve is not None else pd.Series(dtype=float)

    span_days = (eq.index[-1] - eq.index[0]).days + cfg.strategy.trend_ema + 10
    daily = md.get_candles(cfg.market.product_id, "ONE_DAY", 86400, span_days + 50)
    close = daily["close"].loc[: eq.index[-1]]
    close = close.loc[close.index >= eq.index[0]]

    segments: list[Segment] = []
    for kind, s, e in detect_regimes(close, dd_threshold):
        eq_seg = eq.loc[(eq.index >= s) & (eq.index <= e)]
        px_seg = close.loc[(close.index >= s) & (close.index <= e)]
        if len(eq_seg) < 2 or len(px_seg) < 2:
            continue
        exp_seg = exp.loc[(exp.index >= s) & (exp.index <= e)] if len(exp) else pd.Series(dtype=float)
        segments.append(Segment(
            kind=kind, start=eq_seg.index[0], end=eq_seg.index[-1],
            bh_return=_ret(px_seg), bh_max_dd=_max_dd(px_seg),
            strat_return=_ret(eq_seg), strat_max_dd=_max_dd(eq_seg),
            avg_exposure=float(exp_seg.mean()) if len(exp_seg) else 0.0,
        ))

    bull = [g for g in segments if g.kind == "haussier"]
    bear = [g for g in segments if g.kind == "baissier"]

    def _agg_capture(segs):     # capture ponderee par l'amplitude buy & hold
        num = sum(g.strat_return for g in segs)
        den = sum(g.bh_return for g in segs)
        return num / den if abs(den) > 1e-9 else 0.0

    agg = {
        "n_bull": len(bull), "n_bear": len(bear),
        "bull_bh": sum(g.bh_return for g in bull),
        "bull_strat": sum(g.strat_return for g in bull),
        "bull_capture": _agg_capture(bull),
        "bear_bh": sum(g.bh_return for g in bear),
        "bear_strat": sum(g.strat_return for g in bear),
        "bear_protection": 1.0 - _agg_capture(bear) if bear else 1.0,
        "full_return": _ret(eq), "full_cagr": _cagr(eq), "full_max_dd": _max_dd(eq),
        "full_sharpe": _sharpe(eq, _BARS_PER_YEAR_DAY * 86400 / VALID_GRANULARITIES[cfg.market.granularity]),
        "full_sortino": _sortino(eq, _BARS_PER_YEAR_DAY * 86400 / VALID_GRANULARITIES[cfg.market.granularity]),
        "mar": (_cagr(eq) / abs(_max_dd(eq))) if _max_dd(eq) < 0 else float("inf"),
        "n_trades": len(res.trades),
        "avg_exposure": float(exp.mean()) if len(exp) else 0.0,
        "bull_exposure": float(np.mean([g.avg_exposure for g in bull])) if bull else 0.0,
    }
    return segments, agg


# ---------------------------------------------------------------------------
# 2. walk-forward : meme strategie, sous-periodes successives
# ---------------------------------------------------------------------------
def walk_forward(cfg: BotConfig, *, days: int, folds: int = 5,
                 md: MarketData | None = None) -> list[dict]:
    md = md or MarketData(cache=True)
    res = run_backtest(cfg, days=days, save_dir=None, md=md)
    eq = res.equity_curve
    bpy = _BARS_PER_YEAR_DAY * 86400 / VALID_GRANULARITIES[cfg.market.granularity]
    edges = pd.date_range(eq.index[0], eq.index[-1], periods=folds + 1)
    out = []
    for i in range(folds):
        s, e = edges[i], edges[i + 1]
        seg = eq.loc[(eq.index >= s) & (eq.index <= e)]
        if len(seg) < 3:
            continue
        tr = [t for t in res.trades if s <= t.entry_time <= e]
        wins = [t for t in tr if t.pnl > 0]
        gw = sum(t.pnl for t in wins)
        gl = -sum(t.pnl for t in tr if t.pnl <= 0)
        out.append({
            "fold": i + 1, "start": seg.index[0].date(), "end": seg.index[-1].date(),
            "return": _ret(seg), "max_dd": _max_dd(seg), "sharpe": _sharpe(seg, bpy),
            "n_trades": len(tr), "win_rate": (len(wins) / len(tr)) if tr else 0.0,
            "profit_factor": (gw / gl) if gl > 1e-9 else float("inf"),
        })
    return out


# ---------------------------------------------------------------------------
# 3. sensibilite a un parametre
# ---------------------------------------------------------------------------
_PARAM_GROUP = {
    "adx_min": "strategy", "breakout_lookback": "strategy", "exit_lookback": "strategy",
    "trend_slope_lookback": "strategy",
    "initial_stop_atr": "risk", "trailing_atr": "risk", "risk_per_trade": "risk",
    "bar_crash_stop_pct": "risk",
}


def param_sweep(cfg: BotConfig, param: str, values: list, *, days: int,
                md: MarketData | None = None) -> list[dict]:
    if param not in _PARAM_GROUP:
        raise ValueError(f"parametre non supporte: {param}. Choix: {', '.join(_PARAM_GROUP)}")
    md = md or MarketData(cache=True)
    group = _PARAM_GROUP[param]
    bpy = _BARS_PER_YEAR_DAY * 86400 / VALID_GRANULARITIES[cfg.market.granularity]
    rows = []
    for v in values:
        c = copy.deepcopy(cfg)
        setattr(getattr(c, group), param, v)
        res = run_backtest(c, days=days, save_dir=None, md=md)
        eq = res.equity_curve
        s = res.stats
        rows.append({
            "value": v, "return": _ret(eq), "cagr": _cagr(eq), "max_dd": _max_dd(eq),
            "sharpe": _sharpe(eq, bpy), "n_trades": s["n_trades"],
            "profit_factor": s["profit_factor"], "avg_r": s["avg_r"],
        })
    return rows


# ---------------------------------------------------------------------------
# rendu texte
# ---------------------------------------------------------------------------
def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def format_report(cfg: BotConfig, *, days: int, dd_threshold: float, folds: int,
                  md: MarketData | None = None) -> str:
    md = md or MarketData(cache=True)
    L: list[str] = []
    name = cfg.active_strategy or "(config.yaml)"
    L.append(f"══════ VALIDATION DURCIE — {name} · {cfg.market.product_id} · {cfg.market.granularity} ══════")

    segments, agg = regime_report(cfg, days=days, dd_threshold=dd_threshold, md=md)
    L.append("")
    L.append(f"Fenetre complete : {segments[0].start.date()} -> {segments[-1].end.date()}"
             f"   ({agg['n_trades']} trades)")
    L.append(f"  perf {_pct(agg['full_return'])}   CAGR {_pct(agg['full_cagr'])}   "
             f"maxDD {_pct(agg['full_max_dd'])}   Sharpe {agg['full_sharpe']:.2f}   "
             f"Sortino {agg['full_sortino']:.2f}   MAR {agg['mar']:.2f}")
    L.append(f"  exposition moyenne : {agg['avg_exposure'] * 100:.0f}% de l'equity "
             f"(en phase haussiere : {agg['bull_exposure'] * 100:.0f}%)")

    L.append("")
    L.append("── Phases de marche (regime BTC, seuil de bascule "
             f"{dd_threshold:.0%}) ─────────────────────────")
    L.append(f"{'phase':<10} {'debut':<11} {'fin':<11} {'jours':>6}  "
             f"{'B&H':>9} {'strat':>9}  {'B&H DD':>8} {'strat DD':>9}  {'expo':>5}  {'capt/prot':>10}")
    for g in segments:
        L.append(f"{g.kind:<10} {str(g.start.date()):<11} {str(g.end.date()):<11} {g.days:>6.0f}  "
                 f"{_pct(g.bh_return):>9} {_pct(g.strat_return):>9}  "
                 f"{_pct(g.bh_max_dd):>8} {_pct(g.strat_max_dd):>9}  {g.avg_exposure * 100:>4.0f}%  "
                 f"{g.score * 100:>9.0f}%")

    L.append("")
    L.append("── Synthese des deux missions ───────────────────────────────────────────────")
    L.append(f"  HAUSSES  ({agg['n_bull']} phases) : buy & hold {_pct(agg['bull_bh'])}   "
             f"strat {_pct(agg['bull_strat'])}   -> capture {agg['bull_capture'] * 100:.0f}% de la hausse")
    L.append(f"  BAISSES  ({agg['n_bear']} phases) : buy & hold {_pct(agg['bear_bh'])}   "
             f"strat {_pct(agg['bear_strat'])}   -> {agg['bear_protection'] * 100:.0f}% de la baisse evitee")

    L.append("")
    L.append(f"── Walk-forward ({folds} sous-periodes egales, meme strategie) ───────────────")
    L.append(f"{'#':<3} {'debut':<11} {'fin':<11} {'perf':>9} {'maxDD':>9} {'Sharpe':>7} "
             f"{'trades':>7} {'win%':>6} {'PF':>6}")
    wf = walk_forward(cfg, days=days, folds=folds, md=md)
    for r in wf:
        pf = "inf" if r["profit_factor"] == float("inf") else f"{r['profit_factor']:.2f}"
        L.append(f"{r['fold']:<3} {str(r['start']):<11} {str(r['end']):<11} "
                 f"{_pct(r['return']):>9} {_pct(r['max_dd']):>9} {r['sharpe']:>7.2f} "
                 f"{r['n_trades']:>7} {r['win_rate'] * 100:>5.0f}% {pf:>6}")
    pos = sum(1 for r in wf if r["return"] > 0)
    L.append(f"  -> {pos}/{len(wf)} sous-periodes positives")

    L.append("")
    L.append("── Sensibilite aux parametres (perf | maxDD | trades | PF) ──────────────────")
    sweeps = {
        "adx_min": sorted({max(5, cfg.strategy.adx_min + d) for d in (-8, -4, 0, 4, 8)}),
        "breakout_lookback": sorted({max(5, cfg.strategy.breakout_lookback + d) for d in (-10, -5, 0, 10, 20)}),
        "initial_stop_atr": [round(cfg.risk.initial_stop_atr + d, 1) for d in (-1.0, -0.5, 0, 0.5, 1.0)],
        "trailing_atr": [round(cfg.risk.trailing_atr + d, 1) for d in (-1.0, 0, 1.0, 2.0)],
    }
    if cfg.risk.bar_crash_stop_pct > 0:
        sweeps["bar_crash_stop_pct"] = [0.0, 0.04, 0.05, 0.06, 0.08, 0.10]
    for param, values in sweeps.items():
        L.append(f"  {param} (actuel {getattr(getattr(cfg, _PARAM_GROUP[param]), param)}):")
        for row in param_sweep(cfg, param, values, days=days, md=md):
            pf = "inf" if row["profit_factor"] == float("inf") else f"{row['profit_factor']:.2f}"
            L.append(f"      {str(row['value']):>6} : {_pct(row['return']):>9} | "
                     f"{_pct(row['max_dd']):>8} | {row['n_trades']:>4} trades | PF {pf}")
    L.append("")
    L.append("Lecture : une strategie robuste garde le meme signe de perf et un maxDD stable")
    L.append("quand on bouge un parametre de +/-20%, et reste positive sur la majorite des")
    L.append("sous-periodes walk-forward. Sinon = surapprentissage, ne pas passer en live.")
    return "\n".join(L)
