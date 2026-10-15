"""Indicateurs techniques pour le DCA Trailing Bot.

Indicateurs implémentés :
- EMA (Exponential Moving Average)
- SMA (Simple Moving Average)
- Slope (pente)
- Donchian Channel (plus haut/bas)
- ADX (Average Directional Index)
- ATR (Average True Range)
- RSI (Relative Strength Index)
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def ema(series: pd.Series, span: int) -> pd.Series:
    """Exponential Moving Average.
    
    Args:
        series: Série pandas
        span: Période
        
    Returns:
        Série avec EMA
    """
    return series.ewm(span=span, adjust=False).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple Moving Average.
    
    Args:
        series: Série pandas
        window: Fenêtre
        
    Returns:
        Série avec SMA
    """
    return series.rolling(window).mean()


def slope(series: pd.Series, lookback: int) -> pd.Series:
    """Pente moyenne sur lookback périodes.
    
    Args:
        series: Série pandas
        lookback: Nombre de périodes
        
    Returns:
        Série avec la pente
    """
    return (series - series.shift(lookback)) / lookback


def _wilder(series: pd.Series, period: int) -> pd.Series:
    """Lissage de Wilder (équivalent RMA).
    
    Args:
        series: Série pandas
        period: Période
        
    Returns:
        Série lissée
    """
    return series.ewm(alpha=1.0 / period, adjust=False).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """True Range.
    
    Args:
        high: Série des plus hauts
        low: Série des plus bas
        close: Série des clôtures
        
    Returns:
        Série True Range
    """
    prev_close = close.shift(1)
    ranges = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1)
    return ranges.max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range.
    
    Args:
        high: Série des plus hauts
        low: Série des plus bas
        close: Série des clôtures
        period: Période ATR
        
    Returns:
        Série ATR
    """
    return _wilder(true_range(high, low, close), period)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index.
    
    Mesure la force (pas le sens) de la tendance.
    
    Args:
        high: Série des plus hauts
        low: Série des plus bas
        close: Série des clôtures
        period: Période ADX
        
    Returns:
        Série ADX
    """
    up_move = high.diff()
    down_move = -low.diff()
    
    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=high.index
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=high.index
    )
    
    tr = true_range(high, low, close)
    atr_ = _wilder(tr, period).replace(0, np.nan)
    
    plus_di = 100 * _wilder(plus_dm, period) / atr_
    minus_di = 100 * _wilder(minus_dm, period) / atr_
    
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _wilder(dx.fillna(0), period)


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index.
    
    Args:
        series: Série pandas
        period: Période RSI
        
    Returns:
        Série RSI
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = _wilder(gain, period)
    avg_loss = _wilder(loss, period).replace(0, np.nan)
    
    rs = avg_gain / avg_loss
    return (100 - 100 / (1 + rs)).fillna(50)


def donchian_high(high: pd.Series, window: int) -> pd.Series:
    """Plus haut des `window` bougies PRÉCÉDENTES.
    
    Note: Exclut la bougie courante, utilise shift(1).
    
    Args:
        high: Série des plus hauts
        window: Fenêtre
        
    Returns:
        Série avec plus haut des N bougies précédentes
    """
    return high.rolling(window).max().shift(1)


def donchian_low(low: pd.Series, window: int) -> pd.Series:
    """Plus bas des `window` bougies PRÉCÉDENTES.
    
    Args:
        low: Série des plus bas
        window: Fenêtre
        
    Returns:
        Série avec plus bas des N bougies précédentes
    """
    return low.rolling(window).min().shift(1)


def bollinger_bands(
    close: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Bandes de Bollinger.
    
    Args:
        close: Série des clôtures
        period: Période
        std_dev: Écart-type (2.0 par défaut)
        
    Returns:
        Tuple (upper_band, middle_band, lower_band)
    """
    middle = sma(close, period)
    std = close.rolling(period).std()
    upper = middle + std * std_dev
    lower = middle - std * std_dev
    return upper, middle, lower


def macd(
    close: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD (Moving Average Convergence Divergence).
    
    Args:
        close: Série des clôtures
        fast: Période EMA rapide
        slow: Période EMA lente
        signal: Période signal
        
    Returns:
        Tuple (macd_line, signal_line, histogram)
    """
    ema_fast = ema(close, fast)
    ema_slow = ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram
