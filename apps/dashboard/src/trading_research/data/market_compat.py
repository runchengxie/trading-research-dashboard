from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

from . import data_sources

ak = data_sources.ak
fetch_trade_calendar = data_sources.fetch_trade_calendar
normalize_instrument_type = data_sources.normalize_instrument_type


@dataclass(frozen=True, slots=True)
class MarketProfile:
    market: str
    currency: str
    timezone: str
    live_provider: str | None = None


_MARKET_PROFILES = {
    "CN": MarketProfile("CN", "CNY", "Asia/Shanghai"),
    "HK": MarketProfile("HK", "HKD", "Asia/Hong_Kong"),
    "US": MarketProfile("US", "USD", "America/New_York", "alpaca"),
}

_HK_PREFIX = re.compile(r"^hk[.:]?(?P<code>\d{5})$", re.I)
_HK_SUFFIX = re.compile(r"^(?P<code>\d{5})\.HK$", re.I)
_US_CANONICAL = re.compile(r"^us:[A-Z][A-Z0-9.-]{0,14}$", re.I)
_US_SUFFIX = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}\.US$", re.I)


def normalize_market(value: str | None) -> str:
    market = (value or "CN").strip().upper()
    if market not in _MARKET_PROFILES:
        raise ValueError(f"不支持的 market={value!r}，可选值：{sorted(_MARKET_PROFILES)}")
    return market


def _market_from_code(code: str) -> str:
    raw = code.strip()
    if _HK_PREFIX.fullmatch(raw) or _HK_SUFFIX.fullmatch(raw):
        return "HK"
    if _US_CANONICAL.fullmatch(raw) or _US_SUFFIX.fullmatch(raw):
        return "US"
    return "CN"


def infer_market(code: str, explicit_market: str | None = None) -> str:
    inferred = _market_from_code(code)
    if explicit_market is None:
        return inferred
    explicit = normalize_market(explicit_market)
    if explicit != inferred:
        raise ValueError(
            f"证券代码 {code!r} 推断市场为 {inferred}，与显式 market={explicit!r} 冲突"
        )
    return explicit


def market_profile(value: str | None) -> MarketProfile:
    return _MARKET_PROFILES[normalize_market(value)]


def _hk_code_digits(code: str) -> str:
    raw = code.strip()
    match = _HK_PREFIX.fullmatch(raw) or _HK_SUFFIX.fullmatch(raw)
    if not match:
        raise ValueError(f"港股代码格式无效：{code!r}，应使用 hk00700 或 00700.HK")
    return match.group("code")


def _fetch_daily_hk_akshare(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    raw = ak.stock_hk_hist(
        symbol=_hk_code_digits(code),
        period="daily",
        start_date=start_date,
        end_date=end_date,
        adjust="qfq",
    )
    return data_sources._normalize_akshare_daily(raw, code)


def _fetch_intraday_hk_akshare(code: str, trade_date: str) -> pd.DataFrame:
    _, iso_date = data_sources._normalize_trade_date(trade_date)
    raw = ak.stock_hk_hist_min_em(
        symbol=_hk_code_digits(code),
        period="1",
        adjust="",
        start_date=f"{iso_date} 09:30:00",
        end_date=f"{iso_date} 16:00:00",
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"akshare 港股分钟为空：{code} {trade_date}")
    required = {"时间", "收盘", "成交量"}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise RuntimeError(f"akshare 港股分钟缺少字段：{code} {missing}")

    df = raw.rename(columns={"时间": "time", "收盘": "price", "成交量": "volume"})
    times = pd.to_datetime(df["time"], errors="coerce")
    mask = times.notna() & (times.dt.strftime("%Y-%m-%d") == iso_date)
    df = df.loc[mask, ["time", "price", "volume"]].copy()
    selected_times = times.loc[mask]
    df["time"] = selected_times.dt.strftime("%H:%M:%S").to_numpy()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
    df = df.dropna(subset=["time", "price"])
    if df.empty:
        raise RuntimeError(f"akshare 港股分钟没有目标交易日数据：{code} {trade_date}")
    return df.sort_values("time").reset_index(drop=True)


def fetch_daily(
    code: str,
    start_date: str,
    end_date: str,
    *,
    instrument_type: str = "stock",
    market: str | None = None,
) -> pd.DataFrame:
    market_key = infer_market(code, market)
    kind = data_sources.normalize_instrument_type(instrument_type)
    if market_key == "CN":
        return data_sources.fetch_daily(
            code,
            start_date,
            end_date,
            instrument_type=kind,
        )
    if market_key == "US":
        raise ValueError("US 历史行情尚未接入；美股当前通过 market-data-service 的 Alpaca 实时层提供")
    if kind != "stock":
        raise ValueError("港股兼容层当前仅支持 stock")

    errors = []
    try:
        df = _fetch_daily_hk_akshare(code, start_date, end_date)
        if data_sources._nonempty(df):
            data_sources._write_cache("daily", code, df)
            return df
    except Exception as exc:
        errors.append(f"akshare hk: {data_sources._redact(exc)}")

    cached = data_sources._read_cache("daily", code)
    if data_sources._nonempty(cached):
        return cached
    raise RuntimeError(f"港股日线抓取失败且无缓存：{code}；错误：{errors}")


def fetch_intraday(
    code: str,
    trade_date: str,
    *,
    instrument_type: str = "stock",
    market: str | None = None,
) -> pd.DataFrame:
    market_key = infer_market(code, market)
    kind = data_sources.normalize_instrument_type(instrument_type)
    if market_key == "CN":
        return data_sources.fetch_intraday(code, trade_date, instrument_type=kind)
    if market_key == "US":
        raise ValueError("US 分时历史行情尚未接入；美股当前通过 market-data-service 的 Alpaca 实时层提供")
    if kind != "stock":
        raise ValueError("港股兼容层当前仅支持 stock")

    errors = []
    try:
        df = _fetch_intraday_hk_akshare(code, trade_date)
        if data_sources._nonempty(df):
            data_sources._write_cache("intraday", code, df, trade_date=trade_date)
            return df
    except Exception as exc:
        errors.append(f"akshare hk: {data_sources._redact(exc)}")

    cached = data_sources._read_cache("intraday", code, trade_date=trade_date)
    if data_sources._nonempty(cached):
        return cached
    raise RuntimeError(f"港股分时抓取失败且无缓存：{code} {trade_date}；错误：{errors}")
