"""Backtest de la strategie sur historique Coinbase (frais + slippage inclus)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from .config import VALID_GRANULARITIES, BotConfig
from .coinbase_client import MarketData
from . import exposure as expo
from .indicators import ema
from .risk import StopManager, position_size
from .strategy import ENTER_LONG, EXIT, TrendStrategy

log = logging.getLogger("bot.backtest")


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry: float
    exit_time: pd.Timestamp
    exit: float
    qty: float
    fees: float
    pnl: float
    r_multiple: float
    reason: str


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[Trade] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    exposure_curve: pd.Series | None = None   # part de l'equity investie, barre par barre

    def summary(self) -> str:
        s = self.stats
        lines = [
            "──────────  RESULTAT BACKTEST  ──────────",
            f"Periode              : {s['start']}  ->  {s['end']}  ({s['days']:.0f} j)",
            f"Capital initial      : {s['start_equity']:,.2f}",
            f"Capital final        : {s['end_equity']:,.2f}",
            f"Performance          : {s['total_return_pct']:+.2f} %",
            f"CAGR                 : {s['cagr_pct']:+.2f} %",
            f"Buy & Hold           : {s['buy_hold_pct']:+.2f} %",
            f"Max drawdown         : {s['max_drawdown_pct']:.2f} %",
            f"Sharpe (annualise)   : {s['sharpe']:.2f}",
            f"Trades               : {s['n_trades']}  (gagnants {s['win_rate_pct']:.1f} %)",
            f"Gain moyen / perte   : {s['avg_win']:+.2f} / {s['avg_loss']:+.2f}",
            f"R moyen              : {s['avg_r']:+.2f}   profit factor {s['profit_factor']:.2f}",
            f"Couts (frais+slip.)  : {s['total_fees']:,.2f}",
            f"Temps expose         : {s['time_in_market_pct']:.1f} %",
            "────────────────────────────────────────",
        ]
        return "\n".join(lines)


def _htf_ok_series(main_index: pd.DatetimeIndex, htf: pd.DataFrame, htf_ema: int) -> pd.Series:
    ok = (htf["close"] > ema(htf["close"], htf_ema)).astype(float)
    return ok.reindex(main_index, method="ffill").fillna(0.0).astype(bool)


def run_backtest(
    cfg: BotConfig,
    *,
    days: int = 365,
    save_dir: str | None = "data",
    md: MarketData | None = None,
) -> BacktestResult:
    m = cfg.market
    n_bars = int(days * 86400 / m.granularity_seconds) + cfg.strategy.trend_ema + 100
    md = md or MarketData()
    df = md.get_candles(m.product_id, m.granularity, m.granularity_seconds, n_bars)
    log.info("%d bougies chargees (%s -> %s)", len(df), df.index[0].date(), df.index[-1].date())

    strat = TrendStrategy(cfg.strategy)
    data = strat.compute(df)
    if cfg.risk.exposure_control:
        data = expo.attach_market_signals(data, cfg.risk)

    if cfg.strategy.htf_filter:
        secs = VALID_GRANULARITIES[cfg.strategy.htf_granularity]
        htf = md.get_candles(m.product_id, cfg.strategy.htf_granularity, secs,
                             int(days * 86400 / secs) + cfg.strategy.htf_ema + 200)
        htf_ok = _htf_ok_series(data.index, htf, cfg.strategy.htf_ema)
    else:
        htf_ok = pd.Series(True, index=data.index)

    fees = cfg.fees
    side_bps = fees.assumed_roundtrip_bps / 2 + fees.slippage_bps  # cout par cote, en bps

    cash = cfg.paper.starting_cash
    qty = 0.0
    entry_px = 0.0
    entry_fee = 0.0
    entry_time = None
    initial_stop = 0.0
    sm: StopManager | None = None
    cooldown_until = 0
    peak_equity = cfg.paper.starting_cash
    last_exit_i = -10**9

    equity_points: list[tuple[pd.Timestamp, float]] = []
    exposure_points: list[tuple[pd.Timestamp, float]] = []
    trades: list[Trade] = []
    total_fees = 0.0
    bars_in_market = 0

    start_i = strat.min_bars()
    for i in range(start_i, len(data)):
        row = data.iloc[i]
        prev = data.iloc[i - 1]
        px = float(row["close"])
        atr_v = float(row["atr"]) if pd.notna(row["atr"]) else 0.0
        equity = cash + qty * px
        equity_points.append((data.index[i], equity))
        exposure_points.append((data.index[i], (qty * px) / equity if equity > 1e-9 else 0.0))
        peak_equity = max(peak_equity, equity)

        if qty > 0 and sm is not None:
            bars_in_market += 1
            sm.update(float(row["high"]), px, atr_v)
            exit_px = None
            reason = ""
            bar_ret = px / float(prev["close"]) - 1.0
            if float(row["low"]) <= sm.stop:
                exit_px = min(sm.stop, float(row["open"]))  # stop touche : borne par l'open
                reason = f"stop loss @ {sm.stop:.2f}"
            elif cfg.risk.bar_crash_stop_pct > 0 and bar_ret <= -cfg.risk.bar_crash_stop_pct:
                exit_px = px
                reason = f"stop crash bougie ({bar_ret:+.1%})"
            elif expo.crash_active(row, cfg.risk):
                exit_px = px
                reason = "frein de krach (chute brutale / vol)"
            else:
                sig = strat.signal_from_row(row, prev, in_position=True, htf_ok=bool(htf_ok.iloc[i]))
                if sig.action == EXIT:
                    exit_px = px
                    reason = sig.reason
            if exit_px is not None:
                fill_px = exit_px * (1 - side_bps / 10_000)
                proceeds = qty * fill_px
                fee = proceeds * (fees.taker_bps if cfg.execution.stop_exit_is_market else fees.maker_bps) / 10_000
                cash += proceeds - fee
                total_fees += fee + qty * exit_px * side_bps / 10_000  # frais + slippage
                pnl = (fill_px - entry_px) * qty - entry_fee - fee
                r_mult = (fill_px - entry_px) / max(entry_px - initial_stop, 1e-9)
                trades.append(Trade(entry_time, entry_px, data.index[i], fill_px, qty,
                                    entry_fee + fee, pnl, r_mult, reason))
                qty = 0.0
                sm = None
                cooldown_until = i + cfg.execution.cooldown_bars
                last_exit_i = i
            continue

        if i < cooldown_until or atr_v <= 0:
            continue
        if expo.crash_active(row, cfg.risk):        # frein de krach : pas d'entree
            continue
        sig = strat.signal_from_row(row, prev, in_position=False, htf_ok=bool(htf_ok.iloc[i]))
        if sig.action != ENTER_LONG:
            continue

        probe = StopManager(entry_price=px, entry_atr=atr_v, cfg=cfg.risk)
        size = position_size(equity, px, probe.stop,
                             risk_per_trade=cfg.risk.risk_per_trade,
                             max_position_pct=cfg.risk.max_position_pct,
                             cash_available=cash)
        if cfg.risk.exposure_control:
            mult, _ = expo.entry_multiplier(
                row, expo.ExposureState(equity, peak_equity, i - last_exit_i), cfg.risk)
            size *= mult
        if size * px < 5.0:
            continue
        fill_px = px * (1 + side_bps / 10_000)
        cost = size * fill_px
        fee = cost * (fees.maker_bps if cfg.execution.prefer_maker else fees.taker_bps) / 10_000
        cash -= cost + fee
        total_fees += fee + size * px * side_bps / 10_000  # frais + slippage
        qty = size
        entry_px = fill_px
        entry_fee = fee
        entry_time = data.index[i]
        sm = StopManager(entry_price=fill_px, entry_atr=atr_v, cfg=cfg.risk)
        initial_stop = sm.stop

    # -- cloture forcee en fin de periode -----------------------------
    if qty > 0:
        px = float(data.iloc[-1]["close"])
        cash += qty * px
        trades.append(Trade(entry_time, entry_px, data.index[-1], px, qty, entry_fee,
                            (px - entry_px) * qty - entry_fee,
                            (px - entry_px) / max(entry_px - initial_stop, 1e-9), "fin de backtest"))
        qty = 0.0

    eq = pd.Series(dict(equity_points))
    exp = pd.Series(dict(exposure_points))
    result = BacktestResult(equity_curve=eq, trades=trades, exposure_curve=exp)
    result.stats = _compute_stats(eq, trades, data, total_fees, bars_in_market,
                                  cfg.paper.starting_cash, m.granularity_seconds)

    if save_dir:
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        pid = m.product_id
        eq.rename("equity").to_csv(Path(save_dir) / f"backtest_equity_{pid}.csv")
        pd.DataFrame([t.__dict__ for t in trades]).to_csv(
            Path(save_dir) / f"backtest_trades_{pid}.csv", index=False)
    return result


def _compute_stats(eq: pd.Series, trades, data, total_fees, bars_in_market,
                   start_equity, gran_seconds) -> dict:
    end_equity = float(eq.iloc[-1]) if len(eq) else start_equity
    days = (data.index[-1] - data.index[0]).total_seconds() / 86400
    years = max(days / 365.25, 1e-9)
    total_return = end_equity / start_equity - 1
    cagr = (end_equity / start_equity) ** (1 / years) - 1 if end_equity > 0 else -1

    roll_max = eq.cummax()
    max_dd = float(((eq - roll_max) / roll_max).min()) if len(eq) else 0.0

    rets = eq.pct_change().dropna()
    bars_per_year = 86400 * 365.25 / gran_seconds
    sharpe = float(rets.mean() / rets.std() * np.sqrt(bars_per_year)) if rets.std() > 0 else 0.0

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = -sum(t.pnl for t in losses)
    bh = float(data.iloc[-1]["close"] / data.iloc[data.index.get_indexer([eq.index[0]])[0]]["close"] - 1) if len(eq) else 0.0

    return {
        "start": str(data.index[0].date()), "end": str(data.index[-1].date()), "days": days,
        "start_equity": start_equity, "end_equity": end_equity,
        "total_return_pct": total_return * 100, "cagr_pct": cagr * 100,
        "buy_hold_pct": bh * 100,
        "max_drawdown_pct": max_dd * 100, "sharpe": sharpe,
        "n_trades": len(trades),
        "win_rate_pct": 100 * len(wins) / len(trades) if trades else 0.0,
        "avg_win": gross_win / len(wins) if wins else 0.0,
        "avg_loss": -gross_loss / len(losses) if losses else 0.0,
        "avg_r": float(np.mean([t.r_multiple for t in trades])) if trades else 0.0,
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else float("inf"),
        "total_fees": total_fees,
        "time_in_market_pct": 100 * bars_in_market / max(len(eq), 1),
    }
