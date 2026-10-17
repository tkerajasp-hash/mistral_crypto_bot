"""Rendu du dashboard : templating + SVG, sans reseau."""
import pytest

from bot.dashboard import _drawdown_points, _svg_multi_line, render_html


def _fake_result(name, perf, dd, bh, sharpe, n, color_idx):
    return {
        "name": name,
        "params": {"granularity": "SIX_HOUR", "entry_mode": "donchian_breakout",
                   "adx_min": 20, "breakout_lookback": 20, "risk_per_trade": 0.0075,
                   "initial_stop_atr": 2.5, "trailing_atr": 3.0},
        "stats": {
            "start": "2025-05-09", "end": "2026-08-27", "days": 475, "start_equity": 10000,
            "end_equity": 10000 * (1 + perf / 100), "total_return_pct": perf, "cagr_pct": perf * 0.8,
            "buy_hold_pct": bh, "max_drawdown_pct": dd, "sharpe": sharpe, "n_trades": n,
            "win_rate_pct": 44.0, "avg_win": 30.0, "avg_loss": -25.0, "avg_r": 0.1,
            "profit_factor": 1.2 if perf > 0 else 0.6, "total_fees": 50.0, "time_in_market_pct": 10.0,
        },
        "equity": [(1_700_000_000 + i * 21600, 10000 + i * perf) for i in range(30)],
        "trades": [{"entry_time": "2025-06-01T00:00", "entry": 100.0,
                    "exit_time": "2025-06-10T00:00", "exit": 110.0,
                    "pnl": 12.3, "r": 0.5, "reason": "stop loss @ 95"}],
        "live_signal": "enter_long" if perf > 0 else "hold",
        "live_reason": "cassure + ADX 25",
    }


@pytest.fixture
def results():
    return [
        _fake_result("breakout_6h", -0.6, -3.0, -26.0, -0.2, 17, 0),
        _fake_result("conservative_6h", 1.4, -1.4, -26.0, 0.7, 11, 1),
        _fake_result("aggressive_1h", -15.7, -17.0, -32.0, -1.3, 111, 2),
    ]


@pytest.fixture
def snapshots():
    return [{
        "granularity": "SIX_HOUR", "as_of": "2026-08-27T00:00:00+00:00", "trend_ema": 200,
        "price": 78897.3, "ema_trend": 67000.0, "dist_ema_pct": 17.2, "ema_slope_per_bar": 5.0,
        "ema_slope_up": True, "adx": 59.4, "adx_min": 20.0, "atr": 1325.0, "atr_pct": 1.68,
        "breakout_high": 80702.0, "dist_breakout_pct": 2.29, "exit_low": 78446.0, "rsi": 64.5,
        "htf_ok": True, "htf_label": "OK (ONE_DAY close vs EMA50)", "regime_ok": True,
        "implied_stop": 75584.0, "implied_stop_pct": -4.2, "signal": "hold",
        "signal_reason": "pas de declencheur d'entree",
    }]


def test_render_html_is_wellformed(snapshots, results):
    page = render_html("BTC-USDC", 400, "conservative_6h", snapshots, results)
    assert page.lstrip().startswith("<!doctype html>")
    assert "{" not in page.split("<style>")[0]          # aucun placeholder non resolu dans l'entete
    assert page.count('class="srow') == 3
    assert "conservative_6h" in page and "★" in page
    assert "python -m bot select conservative_6h" in page
    assert "<polyline" in page                           # les 2 graphes ont trace des series


def test_best_column_highlight(snapshots, results):
    page = render_html("BTC-USDC", 400, "conservative_6h", snapshots, results)
    # conservative_6h a le meilleur Sharpe -> au moins une cellule "best" sur sa ligne
    row = page.split('data-idx="1"')[1].split("</tr>")[0]
    assert "best" in row


def test_svg_handles_empty():
    assert "Pas de donnees" in _svg_multi_line([])


def test_drawdown_points_monotonic_peak():
    dd = _drawdown_points([(0, 100), (1, 120), (2, 90), (3, 130)])
    assert dd[0][1] == 0.0
    assert dd[1][1] == 0.0                # nouveau plus haut
    assert dd[2][1] == pytest.approx(-25.0)
    assert dd[3][1] == 0.0
