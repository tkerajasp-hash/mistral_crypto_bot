"""Digest periodique : resume texte de l'etat du bot + image de la courbe d'equity.

Utilise par la commande `python -m bot report` (a mettre en cron 1x/jour).
Lecture seule : ne touche ni a l'etat ni aux journaux.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from .config import BotConfig
from .journal import BotState

log = logging.getLogger("bot.report")


def _read_csv(path: str) -> pd.DataFrame:
    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:  # noqa: BLE001
        log.exception("lecture %s", path)
        return pd.DataFrame()


def _equity_series(cfg: BotConfig) -> pd.Series:
    df = _read_csv(cfg.logging.equity_csv)
    if df.empty or "equity" not in df:
        return pd.Series(dtype=float)
    t = pd.to_datetime(df["time"], utc=True, errors="coerce")
    s = pd.Series(pd.to_numeric(df["equity"], errors="coerce").values, index=t).dropna()
    return s[~s.index.isna()].sort_index()


def build_digest(cfg: BotConfig) -> str:
    """Resume texte (HTML Telegram) de l'etat courant."""
    pid = cfg.market.product_id
    quote = pid.split("-")[1]
    start_cash = cfg.paper.starting_cash
    st = BotState.load(cfg.logging.state_file)
    eq = _equity_series(cfg)
    trades = _read_csv(cfg.logging.trades_csv)

    now = datetime.now(timezone.utc)
    lines = [
        f"\U0001F4CA <b>Rapport</b> {pid} · {cfg.active_strategy or 'config.yaml'} · {cfg.mode}",
        f"<i>{now:%Y-%m-%d %H:%M} UTC</i>",
        "",
    ]

    if eq.empty:
        equity = start_cash
        lines.append(f"Equity     : {equity:,.2f} {quote}  (aucun tick enregistre)")
    else:
        equity = float(eq.iloc[-1])
        peak = float(eq.cummax().iloc[-1])
        dd = (equity - peak) / peak if peak > 0 else 0.0
        perf = equity / start_cash - 1 if start_cash > 0 else 0.0
        lines.append(f"Equity     : {equity:,.2f} {quote}  ({perf:+.2%} / depart {start_cash:,.0f})")
        lines.append(f"Pic        : {peak:,.2f}  ·  drawdown courant {dd:+.2%}")

        cutoff = now - timedelta(hours=24)
        e24 = eq[eq.index >= cutoff]
        if len(e24) >= 2:
            chg = float(e24.iloc[-1]) / float(e24.iloc[0]) - 1
            lines.append(f"24 h       : equity {chg:+.2%}  ·  {len(e24)} ticks")

    # -- position ouverte -------------------------------------------------
    if st.in_position and st.entry_price > 0:
        try:
            mark = float(pd.to_numeric(_read_csv(cfg.logging.equity_csv)["mark"], errors="coerce").dropna().iloc[-1])
        except Exception:  # noqa: BLE001
            mark = st.entry_price
        upnl = (mark - st.entry_price) * st.qty
        upct = mark / st.entry_price - 1 if st.entry_price else 0.0
        stop = st.stop.get("stop", 0.0)
        lines.append(
            f"Position   : ouverte — entree {st.entry_price:,.2f} x {st.qty:.8f}  |  "
            f"PnL latent {upnl:+,.2f} ({upct:+.2%})"
        )
        lines.append(f"             stop {stop:,.2f}  ·  stop initial {st.initial_stop:,.2f}")
    else:
        lines.append("Position   : aucune (en cash)")

    # -- trades clotures ------------------------------------------------
    if not trades.empty and "action" in trades:
        closed = trades[trades["action"] == "EXIT"].copy()
        n = len(closed)
        if n:
            pnl = pd.to_numeric(closed["pnl"], errors="coerce")
            r = pd.to_numeric(closed["r_multiple"], errors="coerce")
            wins = int((pnl > 0).sum())
            lines.append(
                f"Trades     : {n} clotures · {wins / n:.0%} gagnants · "
                f"R cumule {r.sum():+.2f} · PnL realise {pnl.sum():+,.2f} {quote}"
            )
        else:
            lines.append("Trades     : 0 cloture")

    lines.append(f"Halted     : {'OUI — ' + (st.halt_reason or '?') if st.halted else 'non'}")
    return "\n".join(lines)


def equity_chart(cfg: BotConfig, out_path: str | None = None) -> str | None:
    """Genere un PNG de la courbe d'equity (marqueurs entrees/sorties). Renvoie le chemin, ou None."""
    eq = _equity_series(cfg)
    if len(eq) < 2:
        log.info("Pas assez de points d'equity pour un graphe.")
        return None

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except Exception as exc:  # noqa: BLE001
        log.warning("matplotlib indisponible (%s) -> pas d'image.", exc)
        return None

    pid = cfg.market.product_id
    quote = pid.split("-")[1]
    start_cash = cfg.paper.starting_cash

    if out_path is None:
        out_path = str(Path("data") / f"report_equity_{pid}.png")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(9, 4.2), dpi=120)
    ax.plot(eq.index, eq.values, color="#2563eb", lw=1.6, label="equity")
    if start_cash > 0:
        ax.axhline(start_cash, color="#9ca3af", ls="--", lw=1, label=f"depart {start_cash:,.0f}")
    ax.fill_between(eq.index, eq.cummax().values, eq.values, color="#ef4444", alpha=0.10)

    trades = _read_csv(cfg.logging.trades_csv)
    if not trades.empty and "action" in trades:
        tt = trades.copy()
        tt["t"] = pd.to_datetime(tt["time"], utc=True, errors="coerce")
        tt = tt.dropna(subset=["t"])
        for action, marker, color in (("ENTRY", "^", "#16a34a"), ("EXIT", "v", "#dc2626")):
            sub = tt[tt["action"] == action]
            if sub.empty:
                continue
            pos = eq.index.get_indexer(sub["t"], method="nearest")
            ys = [float(eq.iloc[i]) for i in pos]
            ax.scatter(sub["t"], ys, marker=marker, s=42, color=color, zorder=5,
                       label="entree" if action == "ENTRY" else "sortie")

    ax.set_title(f"Equity — {pid} · {cfg.active_strategy or 'config'} ({cfg.mode})")
    ax.set_ylabel(quote)
    ax.grid(alpha=0.25)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)
    return out_path
