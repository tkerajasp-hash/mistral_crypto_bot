"""Indicateurs techniques (pandas/numpy uniquement, pas de dependance native)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).mean()


def _wilder(series: pd.Series, period: int) -> pd.Series:
    """Lissage de Wilder (equivalent RMA)."""
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    return _wilder(true_range(high, low, close), period)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index -- mesure la force (pas le sens) de la tendance."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

    tr = true_range(high, low, close)
    atr_ = _wilder(tr, period).replace(0, np.nan)
    plus_di = 100 * _wilder(plus_dm, period) / atr_
    minus_di = 100 * _wilder(minus_dm, period) / atr_

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _wilder(dx.fillna(0), period)


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = _wilder(gain, period)
    avg_loss = _wilder(loss, period).replace(0, np.nan)
    rs = avg_gain / avg_loss
    return (100 - 100 / (1 + rs)).fillna(50)


def donchian_high(high: pd.Series, window: int) -> pd.Series:
    """Plus haut des `window` bougies PRECEDENTES (exclut la bougie courante)."""
    return high.rolling(window).max().shift(1)


def donchian_low(low: pd.Series, window: int) -> pd.Series:
    return low.rolling(window).min().shift(1)


def slope(series: pd.Series, lookback: int) -> pd.Series:
    """Variation moyenne par bougie sur `lookback` (proxy simple de pente)."""
    return (series - series.shift(lookback)) / lookback
