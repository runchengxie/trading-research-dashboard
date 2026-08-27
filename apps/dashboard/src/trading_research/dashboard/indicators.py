"""Indicator calculations used by the dashboard."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans


def calculate_atr(df: pd.DataFrame, period: int) -> float:
    """Compute ATR over the given period"""
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df['atr'].iloc[-1]


def calculate_vwap(df: pd.DataFrame) -> float:
    """Compute full-day VWAP"""
    if df['volume'].sum() == 0:
        return df['price'].mean()  # Fallback for no volume
    df['price_x_vol'] = df['price'] * df['volume']
    vwap = df['price_x_vol'].sum() / df['volume'].sum()
    return vwap


def get_opening_range(df: pd.DataFrame) -> tuple[float | None, float | None]:
    """Get opening range (09:30-09:45)"""
    # 确保索引是DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index('time')

    # 筛选09:30-09:45的时间段
    orb_df = df.between_time('09:30:00', '09:45:00')
    if orb_df.empty:
        return None, None
    orb_high = orb_df['price'].max()
    orb_low = orb_df['price'].min()
    return orb_high, orb_low


def calculate_support_resistance(
    df: pd.DataFrame, n_clusters: int = 5
) -> tuple[float, float, np.ndarray, float]:
    """Compute support/resistance via K-means clusters"""
    # Use close prices
    prices = df['close'].values.reshape(-1, 1)

    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(prices)
    centers = kmeans.cluster_centers_.flatten()
    centers.sort()

    # Support and resistance
    support = centers[0]
    resistance = centers[-1]

    # Nearest key level to latest close
    latest_close = df['close'].iloc[-1]
    nearest_key_level = centers[np.argmin(np.abs(centers - latest_close))]

    return support, resistance, centers, nearest_key_level


def determine_trading_style(df: pd.DataFrame) -> str:
    """Determine trading style based on history"""
    # Volatility: ATR20 relative to price
    atr_20 = calculate_atr(df.copy(), 20)
    price = df['close'].iloc[-1]
    volatility = atr_20 / price

    # Trend strength: |MA5-MA20| relative to price
    ma5 = df['close'].rolling(window=5).mean().iloc[-1]
    ma20 = df['close'].rolling(window=20).mean().iloc[-1]
    trend_strength = abs(ma5 - ma20) / price

    # Price position within recent range
    high_20 = df['high'].rolling(window=20).max().iloc[-1]
    low_20 = df['low'].rolling(window=20).min().iloc[-1]
    price_position = (price - low_20) / (high_20 - low_20)

    # Decide trading style
    if volatility > 0.03:  # high volatility
        if trend_strength > 0.05:  # strong trend
            style = "Trend-following + Breakout"
        else:
            if 0.3 < price_position < 0.7:
                style = "Mean reversion + VWAP"
            else:
                style = "Breakout + Momentum"
    else:  # low volatility
        if trend_strength > 0.03:  # some trend
            style = "Trend-following + Grid"
        else:
            style = "Mean reversion + Range"

    return style


def vwap_deviation_factor_for_style(style: str) -> float:
    """返回交易风格对应的 VWAP 偏离阈值系数。"""
    overrides = {
        "Mean reversion + VWAP": 0.4,
        "Trend-following + Breakout": 0.6,
    }
    return overrides.get(style, 0.5)


def _to_float(v: object) -> float | None:
    """将 numpy/pandas 标量或 None 转为可 JSON 序列化的 float；None 或空值返回 None。"""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None
