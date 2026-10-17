import numpy as np
import pandas as pd
import pytest


def _ohlc(close: np.ndarray, start="2024-01-01"):
    idx = pd.date_range(start, periods=len(close), freq="h", tz="UTC")
    spread = 1.5
    open_ = np.r_[close[0], close[:-1]]
    return pd.DataFrame(
        {
            "open": open_,
            "high": np.maximum(open_, close) + spread,
            "low": np.minimum(open_, close) - spread,
            "close": close,
            "volume": 1.0,
        },
        index=idx,
    )


@pytest.fixture
def uptrend_df():
    """200 barres de hausse douce, 60 de consolidation, 60 de forte cassure haussiere."""
    rng = np.random.default_rng(42)
    seg1 = np.linspace(100, 180, 200) + rng.normal(0, 1.0, 200)
    seg2 = 180 + rng.normal(0, 1.0, 60)
    seg3 = np.linspace(180, 320, 60) + rng.normal(0, 1.2, 60)
    return _ohlc(np.concatenate([seg1, seg2, seg3]))


@pytest.fixture
def range_df():
    """Chop serre autour de 200 (oscillation rapide, faible amplitude) -> pas de trade."""
    rng = np.random.default_rng(7)
    close = 200 + np.sin(np.linspace(0, 170, 400)) * 1.8 + rng.normal(0, 0.7, 400)
    return _ohlc(close)


@pytest.fixture
def crash_after_uptrend_df(uptrend_df):
    """Hausse puis effondrement brutal (test des sorties)."""
    close = uptrend_df["close"].to_numpy().copy()
    close[-20:] = close[-21] - np.linspace(0, 90, 20)
    return _ohlc(close)
