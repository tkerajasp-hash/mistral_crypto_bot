import numpy as np
import pandas as pd

from bot import indicators as ind


def test_ema_matches_manual():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = ind.ema(s, 3)
    # ewm adjust=False : premier point = valeur, alpha = 2/(3+1) = 0.5
    assert out.iloc[0] == 1.0
    assert out.iloc[1] == 1.5
    assert out.iloc[2] == 2.25


def test_atr_positive_and_bounded(uptrend_df):
    a = ind.atr(uptrend_df["high"], uptrend_df["low"], uptrend_df["close"], 14)
    assert (a.dropna() > 0).all()
    assert a.iloc[-1] < uptrend_df["close"].iloc[-1]  # ATR << prix


def test_adx_higher_in_trend_than_range(uptrend_df, range_df):
    adx_trend = ind.adx(uptrend_df["high"], uptrend_df["low"], uptrend_df["close"], 14).iloc[50:-20].mean()
    adx_range = ind.adx(range_df["high"], range_df["low"], range_df["close"], 14).iloc[50:].mean()
    assert adx_trend > adx_range


def test_donchian_high_excludes_current_bar():
    high = pd.Series([1, 2, 3, 4, 5], dtype=float)
    dh = ind.donchian_high(high, 2)
    # a l'index 2, plus haut des index [0,1] = 2
    assert dh.iloc[2] == 2.0
    assert np.isnan(dh.iloc[0])


def test_rsi_range():
    s = pd.Series(np.cumsum(np.random.default_rng(0).normal(size=200)))
    r = ind.rsi(s, 14).dropna()
    assert r.between(0, 100).all()
