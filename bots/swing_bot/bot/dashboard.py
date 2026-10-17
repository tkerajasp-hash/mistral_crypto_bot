"""Genere un dashboard HTML autonome :
  - snapshot des indicateurs marche (par unite de temps)
  - comparaison des backtests de chaque strategie (strategies.yaml)
  - courbes d'equity et de drawdown superposees
  - signal actuel de chaque strategie + commande pour l'activer

Usage : python -m bot dashboard --days 400
"""
from __future__ import annotations

import html
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .backtest import run_backtest
from .coinbase_client import MarketData
from .config import VALID_GRANULARITIES, BotConfig, list_strategies, load_config
from .indicators import atr, adx, donchian_high, donchian_low, ema, rsi, slope
from .strategy import ENTER_LONG, TrendStrategy

log = logging.getLogger("bot.dashboard")

PALETTE = ["#2563eb", "#dc2626", "#059669", "#d97706", "#7c3aed", "#0891b2", "#db2777"]


# ===========================================================================
# Donnees
# ===========================================================================
def _closed(md: MarketData, product: str, gran: str, n: int) -> pd.DataFrame:
    secs = VALID_GRANULARITIES[gran]
    df = md.get_candles(product, gran, secs, n)
    if df.index[-1].timestamp() + secs > datetime.now(timezone.utc).timestamp():
        df = df.iloc[:-1]
    return df


def market_snapshot(cfg: BotConfig, md: MarketData) -> dict:
    s = cfg.strategy
    need = max(s.trend_ema + s.trend_slope_lookback, s.breakout_lookback, s.adx_period) + 50
    df = _closed(md, cfg.market.product_id, cfg.market.granularity, need)
    close = df["close"]
    ema_t = ema(close, s.trend_ema)
    sl = slope(ema_t, s.trend_slope_lookback)
    adx_v = adx(df["high"], df["low"], close, s.adx_period)
    atr_v = atr(df["high"], df["low"], close, s.adx_period)
    bh = donchian_high(close, s.breakout_lookback)
    el = donchian_low(close, s.exit_lookback)
    rsi_v = rsi(close, 14)
    price = float(close.iloc[-1])

    htf_ok, htf_label = True, "désactivé"
    if s.htf_filter:
        hdf = _closed(md, cfg.market.product_id, s.htf_granularity, s.htf_ema + 200)
        he = ema(hdf["close"], s.htf_ema)
        htf_ok = bool(hdf["close"].iloc[-1] > he.iloc[-1])
        htf_label = f"{'OK' if htf_ok else 'KO'} ({s.htf_granularity} close vs EMA{s.htf_ema})"

    regime_ok = price > float(ema_t.iloc[-1]) and float(sl.iloc[-1]) > 0
    strat = TrendStrategy(s)
    hdf_full = None
    if s.htf_filter:
        hdf_full = _closed(md, cfg.market.product_id, s.htf_granularity, s.htf_ema + 200)
    sig = strat.evaluate(df, in_position=False, htf_df=hdf_full)

    a = float(atr_v.iloc[-1])
    implied_stop = price - cfg.risk.initial_stop_atr * a
    return {
        "granularity": cfg.market.granularity,
        "as_of": df.index[-1].isoformat(),
        "trend_ema": s.trend_ema,
        "price": price,
        "ema_trend": float(ema_t.iloc[-1]),
        "dist_ema_pct": (price / float(ema_t.iloc[-1]) - 1) * 100,
        "ema_slope_per_bar": float(sl.iloc[-1]),
        "ema_slope_up": float(sl.iloc[-1]) > 0,
        "adx": float(adx_v.iloc[-1]),
        "adx_min": s.adx_min,
        "atr": a,
        "atr_pct": a / price * 100,
        "breakout_high": float(bh.iloc[-1]),
        "dist_breakout_pct": (float(bh.iloc[-1]) / price - 1) * 100,
        "exit_low": float(el.iloc[-1]),
        "rsi": float(rsi_v.iloc[-1]),
        "htf_ok": htf_ok,
        "htf_label": htf_label,
        "regime_ok": regime_ok,
        "implied_stop": implied_stop,
        "implied_stop_pct": (implied_stop / price - 1) * 100,
        "signal": sig.action,
        "signal_reason": sig.reason,
    }


def _live_signal(cfg: BotConfig, md: MarketData) -> tuple[str, str]:
    s = cfg.strategy
    need = max(s.trend_ema + s.trend_slope_lookback, s.breakout_lookback, s.ema_slow, s.adx_period) + 30
    df = _closed(md, cfg.market.product_id, cfg.market.granularity, need)
    hdf = None
    if s.htf_filter:
        hdf = _closed(md, cfg.market.product_id, s.htf_granularity, s.htf_ema + 200)
    sig = TrendStrategy(s).evaluate(df, in_position=False, htf_df=hdf)
    return sig.action, sig.reason


def run_all(days: int, names: list[str], md: MarketData, *, cfgs: dict | None = None) -> list[dict]:
    results = []
    for name in names:
        cfg = (cfgs or {}).get(name) or load_config(strategy_name=name)
        log.info("Backtest strategie '%s' (%s %s)...", name, cfg.market.product_id, cfg.market.granularity)
        res = run_backtest(cfg, days=days, save_dir=None, md=md)
        action, reason = _live_signal(cfg, md)
        eq = [(int(ts.timestamp()), float(v)) for ts, v in res.equity_curve.items()]
        results.append({
            "name": name,
            "params": {
                "granularity": cfg.market.granularity,
                "entry_mode": cfg.strategy.entry_mode,
                "adx_min": cfg.strategy.adx_min,
                "breakout_lookback": cfg.strategy.breakout_lookback,
                "risk_per_trade": cfg.risk.risk_per_trade,
                "initial_stop_atr": cfg.risk.initial_stop_atr,
                "trailing_atr": cfg.risk.trailing_atr,
            },
            "stats": res.stats,
            "equity": eq,
            "trades": [
                {
                    "entry_time": t.entry_time.isoformat(), "entry": t.entry,
                    "exit_time": t.exit_time.isoformat(), "exit": t.exit,
                    "pnl": t.pnl, "r": t.r_multiple, "reason": t.reason,
                }
                for t in res.trades
            ],
            "live_signal": action,
            "live_reason": reason,
        })
    return results


# ===========================================================================
# Rendu SVG
# ===========================================================================
def _svg_multi_line(series: list[dict], *, width=920, height=320, ylabel="", zero_line=False) -> str:
    pad_l, pad_r, pad_t, pad_b = 56, 16, 14, 28
    xs = [p[0] for s in series for p in s["points"]]
    ys = [p[1] for s in series for p in s["points"]]
    if not xs:
        return "<p>Pas de donnees.</p>"
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if zero_line:
        ymax = max(ymax, 0.0)
        ymin = min(ymin, 0.0)
    span_y = (ymax - ymin) or 1.0
    ymin -= span_y * 0.06
    ymax += span_y * 0.06
    iw = width - pad_l - pad_r
    ih = height - pad_t - pad_b

    def px(x): return pad_l + (x - xmin) / ((xmax - xmin) or 1) * iw
    def py(y): return pad_t + (ymax - y) / ((ymax - ymin) or 1) * ih

    parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" class="chart">']
    # grille + ticks Y
    for i in range(5):
        yv = ymin + (ymax - ymin) * i / 4
        y = py(yv)
        parts.append(f'<line x1="{pad_l}" y1="{y:.1f}" x2="{width - pad_r}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{pad_l - 8}" y="{y + 3:.1f}" class="tick" text-anchor="end">{yv:,.0f}</text>')
    if zero_line:
        y0 = py(0.0)
        parts.append(f'<line x1="{pad_l}" y1="{y0:.1f}" x2="{width - pad_r}" y2="{y0:.1f}" class="zero"/>')
    # ticks X (dates)
    for i in range(5):
        xv = xmin + (xmax - xmin) * i / 4
        x = px(xv)
        d = datetime.fromtimestamp(xv, timezone.utc).strftime("%Y-%m-%d")
        parts.append(f'<text x="{x:.1f}" y="{height - 8}" class="tick" text-anchor="middle">{d}</text>')
    for s in series:
        pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in s["points"])
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{s["color"]}" stroke-width="1.7"/>')
    if ylabel:
        parts.append(f'<text x="14" y="{pad_t + ih / 2}" class="axis" transform="rotate(-90 14 {pad_t + ih / 2})" text-anchor="middle">{ylabel}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _drawdown_points(eq: list[tuple[int, float]]) -> list[tuple[int, float]]:
    peak = -1e18
    out = []
    for ts, v in eq:
        peak = max(peak, v)
        out.append((ts, (v / peak - 1) * 100))
    return out


# ===========================================================================
# Rendu HTML
# ===========================================================================
def _esc(x) -> str:
    return html.escape(str(x))


def _cell(value: str, *, best=False, cls="") -> str:
    c = " ".join(filter(None, [cls, "best" if best else ""]))
    return f'<td class="{c}">{value}</td>'


def render_html(product: str, days: int, active: str, snapshots: list[dict], results: list[dict]) -> str:
    gen = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for i, r in enumerate(results):
        r["color"] = PALETTE[i % len(PALETTE)]

    # ---- best-in-column ------------------------------------------------
    def best_name(key, *, maximize=True, path="stats"):
        vals = [(r["name"], r[path][key]) for r in results if r[path].get(key) is not None]
        if not vals:
            return None
        return (max if maximize else min)(vals, key=lambda kv: kv[1])[0]

    best = {
        "total_return_pct": best_name("total_return_pct"),
        "cagr_pct": best_name("cagr_pct"),
        "excess": None,
        "max_drawdown_pct": best_name("max_drawdown_pct", maximize=True),  # -2% > -10%
        "sharpe": best_name("sharpe"),
        "win_rate_pct": best_name("win_rate_pct"),
        "avg_r": best_name("avg_r"),
        "profit_factor": best_name("profit_factor"),
        "total_fees": best_name("total_fees", maximize=False),
    }
    excess = [(r["name"], r["stats"]["total_return_pct"] - r["stats"]["buy_hold_pct"]) for r in results]
    best["excess"] = max(excess, key=lambda kv: kv[1])[0] if excess else None

    # ---- snapshot cards --------------------------------------------
    snap_html = []
    for s in snapshots:
        regime = ('<span class="tag ok">HAUSSIER</span>' if s["regime_ok"]
                  else '<span class="tag ko">NON HAUSSIER</span>')
        adx_tag = ('<span class="tag ok">forte</span>' if s["adx"] >= s["adx_min"]
                   else '<span class="tag warn">faible</span>')
        htf_tag = ('<span class="tag mut">désactivé</span>' if "désactivé" in s["htf_label"]
                   else '<span class="tag ok">OK</span>' if s["htf_ok"]
                   else '<span class="tag ko">KO</span>')
        sig_tag = ('<span class="tag ok">ENTREE POSSIBLE</span>' if s["signal"] == ENTER_LONG
                   else f'<span class="tag mut">{_esc(s["signal"])}</span>')
        snap_html.append(f"""
        <div class="card">
          <div class="card-h">{_esc(s['granularity'])} <span class="muted">· clôture {_esc(s['as_of'][:16].replace('T',' '))}</span></div>
          <div class="verdict">{sig_tag} <span class="muted">{_esc(s['signal_reason'])}</span></div>
          <table class="kv">
            <tr><td>Prix</td><td>{s['price']:,.2f}</td></tr>
            <tr><td>Régime (EMA{s['trend_ema']})</td><td>{regime} &nbsp; {s['dist_ema_pct']:+.2f}% vs EMA, pente {'▲' if s['ema_slope_up'] else '▼'}</td></tr>
            <tr><td>ADX</td><td>{s['adx']:.1f} / min {s['adx_min']:.0f} &nbsp; {adx_tag}</td></tr>
            <tr><td>ATR</td><td>{s['atr']:,.2f} &nbsp; ({s['atr_pct']:.2f}% du prix)</td></tr>
            <tr><td>Cassure (Donchian haut)</td><td>{s['breakout_high']:,.2f} &nbsp; ({s['dist_breakout_pct']:+.2f}% vs prix)</td></tr>
            <tr><td>Sortie tendance (Donchian bas)</td><td>{s['exit_low']:,.2f}</td></tr>
            <tr><td>RSI(14)</td><td>{s['rsi']:.1f}</td></tr>
            <tr><td>Filtre unité sup.</td><td>{htf_tag} &nbsp; <span class="muted">{_esc(s['htf_label'])}</span></td></tr>
            <tr><td>Stop initial si entrée maintenant</td><td>{s['implied_stop']:,.2f} &nbsp; ({s['implied_stop_pct']:.2f}%)</td></tr>
          </table>
        </div>""")

    # ---- table strategies -----------------------------------------
    rows = []
    for idx, r in enumerate(results):
        st = r["stats"]
        p = r["params"]
        exc = st["total_return_pct"] - st["buy_hold_pct"]
        is_active = " active" if r["name"] == active else ""
        live = ('<span class="tag ok">ENTRÉE</span>' if r["live_signal"] == ENTER_LONG
                else '<span class="tag mut">attente</span>')
        rows.append(f"""
      <tr class="srow{is_active}" data-idx="{idx}">
        <td class="name"><span class="dot" style="background:{r['color']}"></span>{_esc(r['name'])}{' ★' if r['name']==active else ''}
            <div class="muted">{_esc(p['granularity'])} · {_esc(p['entry_mode'])} · ADX≥{p['adx_min']:.0f} · risk {p['risk_per_trade']*100:.2f}%
            · testé {_esc(r['stats']['start'])}→{_esc(r['stats']['end'])}</div></td>
        {_cell(f"{st['total_return_pct']:+.2f}%", best=r['name']==best['total_return_pct'], cls='num')}
        {_cell(f"{st['cagr_pct']:+.2f}%", best=r['name']==best['cagr_pct'], cls='num')}
        {_cell(f"{exc:+.2f}%", best=r['name']==best['excess'], cls='num')}
        {_cell(f"{st['max_drawdown_pct']:.2f}%", best=r['name']==best['max_drawdown_pct'], cls='num')}
        {_cell(f"{st['sharpe']:.2f}", best=r['name']==best['sharpe'], cls='num')}
        {_cell(str(st['n_trades']), cls='num')}
        {_cell(f"{st['win_rate_pct']:.0f}%", best=r['name']==best['win_rate_pct'], cls='num')}
        {_cell(f"{st['avg_r']:+.2f}", best=r['name']==best['avg_r'], cls='num')}
        {_cell(('∞' if st['profit_factor']==float('inf') else f"{st['profit_factor']:.2f}"), best=r['name']==best['profit_factor'], cls='num')}
        {_cell(f"{st['total_fees']:,.0f}", best=r['name']==best['total_fees'], cls='num')}
        {_cell(f"{st['time_in_market_pct']:.0f}%", cls='num')}
        <td>{live}</td>
      </tr>
      <tr class="detail" id="detail-{idx}"><td colspan="13">
        <div class="detail-box">
          <div class="cmd">Activer : <code>python -m bot select {_esc(r['name'])}</code> &nbsp;|&nbsp; tester : <code>python -m bot backtest --strategy {_esc(r['name'])} --days {days}</code></div>
          <div class="muted">{_esc(r['live_reason'])}</div>
          {_trades_table(r['trades'])}
        </div>
      </td></tr>""")

    eq_series = [{"color": r["color"], "points": r["equity"]} for r in results if r["equity"]]
    dd_series = [{"color": r["color"], "points": _drawdown_points(r["equity"])} for r in results if r["equity"]]
    legend = " ".join(
        f'<span class="lg"><span class="dot" style="background:{r["color"]}"></span>{_esc(r["name"])}</span>'
        for r in results
    )

    return _PAGE.format(
        product=_esc(product), days=days, gen=gen, active=_esc(active or "(aucune)"),
        snapshots="".join(snap_html),
        rows="".join(rows),
        legend=legend,
        eq_chart=_svg_multi_line(eq_series, ylabel="valeur du compte"),
        dd_chart=_svg_multi_line(dd_series, ylabel="drawdown %", zero_line=True),
    )


def _trades_table(trades: list[dict]) -> str:
    if not trades:
        return '<p class="muted">Aucun trade.</p>'
    body = "".join(
        f"<tr><td>{_esc(t['entry_time'][:16].replace('T',' '))}</td><td class='num'>{t['entry']:,.2f}</td>"
        f"<td>{_esc(t['exit_time'][:16].replace('T',' '))}</td><td class='num'>{t['exit']:,.2f}</td>"
        f"<td class='num {'pos' if t['pnl']>=0 else 'neg'}'>{t['pnl']:+,.2f}</td>"
        f"<td class='num {'pos' if t['r']>=0 else 'neg'}'>{t['r']:+.2f}R</td><td>{_esc(t['reason'])}</td></tr>"
        for t in trades
    )
    return (f'<table class="trades"><tr><th>Entrée</th><th>Prix</th><th>Sortie</th><th>Prix</th>'
            f'<th>PnL</th><th>R</th><th>Motif</th></tr>{body}</table>')


def build_dashboard(*, days: int = 400, out: str | None = None,
                    names: list[str] | None = None, product: str | None = None) -> str:
    active, presets = list_strategies()
    names = names or list(presets.keys())
    if not names:
        raise RuntimeError("Aucune strategie dans strategies.yaml")
    md = MarketData(cache=True)
    base = load_config(product=product)
    cfgs = {n: load_config(strategy_name=n, product=product) for n in names}
    pid = base.market.product_id
    out = out or f"dashboard_{pid}.html"

    log.info("Snapshot des indicateurs...")
    seen: set[str] = set()
    snapshots = []
    for n in names:
        g = cfgs[n].market.granularity
        if g in seen:
            continue
        seen.add(g)
        snapshots.append(market_snapshot(cfgs[n], md))

    results = run_all(days, names, md, cfgs=cfgs)

    Path("data").mkdir(exist_ok=True)
    Path(f"data/dashboard_data_{pid}.json").write_text(json.dumps(
        {"generated": datetime.now(timezone.utc).isoformat(), "days": days,
         "product": base.market.product_id, "active": active,
         "snapshots": snapshots, "results": results}, indent=2, default=str))

    page = render_html(base.market.product_id, days, active, snapshots, results)
    Path(out).write_text(page)
    log.info("Dashboard ecrit : %s", out)
    return out


# ===========================================================================
_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dashboard stratégies — {product}</title>
<style>
  :root {{
    --bg:#f7f8fa; --panel:#fff; --ink:#1a1d24; --muted:#6b7280; --line:#e5e7eb;
    --ok:#065f46; --okbg:#d1fae5; --ko:#991b1b; --kobg:#fee2e2; --warn:#92400e; --warnbg:#fef3c7;
    --best:#ecfdf5; --active:#eff6ff;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
    font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif; }}
  header {{ padding:20px 24px; background:var(--panel); border-bottom:1px solid var(--line); }}
  h1 {{ margin:0 0 4px; font-size:18px; }}
  h2 {{ font-size:15px; margin:28px 0 12px; }}
  .wrap {{ max-width:1180px; margin:0 auto; padding:0 24px 60px; }}
  .muted {{ color:var(--muted); font-size:12px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:14px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:14px; }}
  .card-h {{ font-weight:600; margin-bottom:8px; }}
  .verdict {{ margin-bottom:10px; }}
  table.kv {{ width:100%; border-collapse:collapse; }}
  table.kv td {{ padding:4px 0; border-bottom:1px dashed var(--line); vertical-align:top; }}
  table.kv td:first-child {{ color:var(--muted); width:46%; }}
  .tag {{ display:inline-block; padding:1px 7px; border-radius:999px; font-size:11px; font-weight:600; }}
  .tag.ok {{ background:var(--okbg); color:var(--ok); }}
  .tag.ko {{ background:var(--kobg); color:var(--ko); }}
  .tag.warn {{ background:var(--warnbg); color:var(--warn); }}
  .tag.mut, .tag.muted {{ background:#eef0f3; color:var(--muted); }}
  .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:16px; overflow-x:auto; }}
  table.cmp {{ width:100%; border-collapse:collapse; font-size:13px; }}
  table.cmp th, table.cmp td {{ padding:8px 10px; text-align:right; border-bottom:1px solid var(--line); white-space:nowrap; }}
  table.cmp th {{ cursor:pointer; user-select:none; font-size:11px; text-transform:uppercase; letter-spacing:.03em; color:var(--muted); }}
  table.cmp th:first-child, table.cmp td.name {{ text-align:left; }}
  td.num {{ font-variant-numeric:tabular-nums; }}
  td.best {{ background:var(--best); font-weight:600; }}
  tr.srow {{ cursor:pointer; }}
  tr.srow:hover td {{ background:#fafafa; }}
  tr.srow.active td {{ background:var(--active); }}
  tr.srow.active:hover td {{ background:var(--active); }}
  .dot {{ display:inline-block; width:9px; height:9px; border-radius:2px; margin-right:6px; vertical-align:middle; }}
  tr.detail {{ display:none; }}
  tr.detail.show {{ display:table-row; }}
  .detail-box {{ padding:10px 4px; }}
  .cmd {{ font-size:12px; margin-bottom:6px; }}
  code {{ background:#eef0f3; padding:1px 6px; border-radius:4px; font-size:12px; }}
  table.trades {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:12px; }}
  table.trades th, table.trades td {{ padding:4px 8px; border-bottom:1px solid var(--line); text-align:right; }}
  table.trades th:last-child, table.trades td:last-child,
  table.trades th:first-child, table.trades td:first-child {{ text-align:left; }}
  .pos {{ color:#065f46; }} .neg {{ color:#991b1b; }}
  .chart {{ width:100%; height:auto; background:var(--panel); }}
  .chart .grid {{ stroke:var(--line); stroke-width:1; }}
  .chart .zero {{ stroke:#9ca3af; stroke-width:1; stroke-dasharray:3 3; }}
  .chart .tick {{ fill:var(--muted); font-size:10px; }}
  .chart .axis {{ fill:var(--muted); font-size:11px; }}
  .legend {{ margin:8px 0 4px; }}
  .lg {{ font-size:12px; margin-right:14px; white-space:nowrap; }}
  .note {{ background:#fffbeb; border:1px solid var(--warnbg); border-radius:8px; padding:12px; font-size:13px; margin-top:18px; }}
</style></head>
<body>
<header>
  <h1>Dashboard stratégies — {product}</h1>
  <div class="muted">Généré {gen} · fenêtre backtest {days} j · stratégie active : <b>{active}</b></div>
</header>
<div class="wrap">

  <h2>1 · État du marché (indicateurs, par unité de temps)</h2>
  <div class="cards">{snapshots}</div>

  <h2>2 · Comparaison des stratégies (backtest)</h2>
  <div class="panel">
    <table class="cmp" id="cmp">
      <thead><tr>
        <th data-k="0" data-t="s">Stratégie</th>
        <th data-k="1">Perf</th><th data-k="2">CAGR</th><th data-k="3">vs Buy&amp;Hold</th>
        <th data-k="4">Max DD</th><th data-k="5">Sharpe</th><th data-k="6">Trades</th>
        <th data-k="7">Win</th><th data-k="8">R moyen</th><th data-k="9">Profit f.</th>
        <th data-k="10">Coûts</th><th data-k="11">Expo</th><th data-k="12" data-t="s">Signal</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <div class="muted" style="margin-top:8px">Clique une ligne pour le détail des trades et la commande d'activation. Clique un en-tête pour trier. Cellule verte = meilleure de la colonne. ★ = stratégie active.</div>
  </div>

  <h2>3 · Courbes d'equity</h2>
  <div class="panel"><div class="legend">{legend}</div>{eq_chart}
    <div class="muted" style="margin-top:6px">Attention : l'historique public Coinbase remonte plus loin en 6h/1j qu'en 1h — les courbes ne démarrent pas toutes à la même date. La colonne « vs Buy&amp;Hold » reste comparable (même fenêtre par ligne).</div>
  </div>

  <h2>4 · Drawdown</h2>
  <div class="panel"><div class="legend">{legend}</div>{dd_chart}</div>

  <div class="note">
    <b>Comment choisir.</b> Regarde d'abord le <b>Max DD</b> et le <b>Sharpe</b> (régularité), puis <b>vs Buy&amp;Hold</b>
    (valeur ajoutée réelle) et le <b>R moyen</b> (espérance par trade). Un backtest sur ~1 an de données
    (souvent baissier ici) favorise les stratégies défensives ; revalide sur une période haussière avant le live.
    Une fois décidé : <code>python -m bot select &lt;nom&gt;</code> puis <code>python -m bot paper</code>.
    <br>⚠️ Ceci n'est pas un conseil en investissement.
  </div>
</div>
<script>
(function () {{
  var tb = document.querySelector('#cmp tbody');
  document.querySelectorAll('#cmp thead th').forEach(function (th) {{
    th.addEventListener('click', function () {{
      var k = +th.dataset.k, txt = th.dataset.t === 's';
      var pairs = Array.from(tb.querySelectorAll('tr.srow'));
      var asc = th._asc = !th._asc;
      pairs.sort(function (ra, rb) {{
        var a = ra.children[k].innerText.replace(/[^0-9.\\-]/g, ''), b = rb.children[k].innerText.replace(/[^0-9.\\-]/g, '');
        if (txt) return asc ? ra.children[k].innerText.localeCompare(rb.children[k].innerText)
                            : rb.children[k].innerText.localeCompare(ra.children[k].innerText);
        return asc ? (parseFloat(a) - parseFloat(b)) : (parseFloat(b) - parseFloat(a));
      }});
      pairs.forEach(function (row) {{
        var det = document.getElementById('detail-' + row.dataset.idx);
        tb.appendChild(row); if (det) tb.appendChild(det);
      }});
    }});
  }});
  tb.querySelectorAll('tr.srow').forEach(function (row) {{
    row.addEventListener('click', function () {{
      var d = document.getElementById('detail-' + row.dataset.idx);
      if (d) d.classList.toggle('show');
    }});
  }});
}})();
</script>
</body></html>
"""
