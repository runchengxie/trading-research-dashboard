"""股票与 ETF 的统一行情数据层。

股票继续使用 AKShare、Tushare 双 token 和 CSV 缓存兜底。ETF 日线使用 AKShare
专用接口，ETF 分钟线优先读取 etf-minute-fetcher 生成的本地 Parquet，缺失时再
请求 AKShare 近期 1 分钟数据，最后回退到 Dashboard 自己的 CSV 缓存。

对外接口保持兼容，只新增可选 instrument_type：
    fetch_trade_calendar() -> DataFrame(列 trade_date)
    fetch_daily(code, start_date, end_date, instrument_type="stock")
    fetch_intraday(code, trade_date, instrument_type="stock")

下游始终得到稳定 schema，避免指标层关心具体数据源。
"""

import datetime as _dt
import os
import re
from pathlib import Path

import akshare as ak
import pandas as pd

from trading_research.data.cache import cache_path, read_cache, write_cache
from trading_research.data.provider_policy import (
    _call_tushare_api,
    _err_text,  # noqa: F401
    _is_daily_quota_exhausted,  # noqa: F401
    _is_quota_error,  # noqa: F401
    _is_retryable_provider_error,  # noqa: F401
    _redact,
)  # noqa: F401

# 双 token 优先级：token2（xiaodefa 转发，15000 分）主力，token1（直连，5000 分）兜底。
# 顺序与 linux 主机默认相反，纯属本项目策略选择。
TUSHARE_TOKEN_ENVS = ("TUSHARE_TOKEN_2", "TUSHARE_TOKEN")

# 运行时缓存根目录。公开行情也不纳入版本库，避免把本地快照混入源码历史。
DATA_RAW_DIR = os.path.join("data", "raw")

VALID_INSTRUMENT_TYPES = {"stock", "etf"}
ETF_MINUTE_DATA_ROOT_ENV = "ETF_MINUTE_DATA_ROOT"
DEFAULT_ETF_MINUTE_DATA_ROOT = "~/data/etf-minute-fetcher/minute/fund_min_1m"


# ==============================================================================
# 工具函数
# ==============================================================================
def normalize_instrument_type(instrument_type: str | None) -> str:
    """规范证券类型，默认保持历史行为为 stock。"""
    normalized = (instrument_type or "stock").strip().lower()
    if normalized not in VALID_INSTRUMENT_TYPES:
        raise ValueError(
            f"不支持的 instrument_type={instrument_type!r}，"
            f"可选值：{sorted(VALID_INSTRUMENT_TYPES)}"
        )
    return normalized


def _split_security_code(code: str) -> tuple[str, str]:
    """把 sh600199 / 600199.SH 统一拆成六位代码和交易所后缀。"""
    raw = code.strip()
    prefixed = re.fullmatch(r"(?i)(sh|sz|bj)(\d{6})", raw)
    if prefixed:
        return prefixed.group(2), prefixed.group(1).upper()

    suffixed = re.fullmatch(r"(?i)(\d{6})\.(SH|SZ|BJ)", raw)
    if suffixed:
        return suffixed.group(1), suffixed.group(2).upper()

    raise ValueError(f"证券代码格式无效：{code!r}，应使用 sh600199 或 600199.SH")


def to_ts_code(code: str) -> str:
    """统一转换为 tushare / 本地数据目录使用的 600199.SH 格式。"""
    num, exchange = _split_security_code(code)
    return f"{num}.{exchange}"


def _code_digits(code: str) -> str:
    """返回 AKShare 接口使用的六位代码。"""
    return _split_security_code(code)[0]


def _normalize_trade_date(trade_date: str) -> tuple[str, str]:
    """返回 YYYYMMDD 和 YYYY-MM-DD 两种日期表示。"""
    value = pd.Timestamp(trade_date)
    if pd.isna(value):
        raise ValueError(f"交易日期格式无效：{trade_date!r}")
    return value.strftime("%Y%m%d"), value.strftime("%Y-%m-%d")


def get_etf_minute_data_root() -> Path:
    """返回 etf-minute-fetcher 1 分钟 Parquet 根目录。"""
    raw = os.environ.get(ETF_MINUTE_DATA_ROOT_ENV, DEFAULT_ETF_MINUTE_DATA_ROOT).strip()
    if not raw:
        raw = DEFAULT_ETF_MINUTE_DATA_ROOT
    return Path(raw).expanduser()


def _nonempty(df) -> bool:
    return df is not None and isinstance(df, pd.DataFrame) and not df.empty


def _cache_path(kind: str, code: str, *, trade_date: str | None = None) -> str:
    return cache_path(DATA_RAW_DIR, kind, code, trade_date=trade_date)


def _write_cache(
    kind: str,
    code: str,
    df: pd.DataFrame,
    *,
    trade_date: str | None = None,
) -> None:
    """写入运行时缓存，分时数据按交易日隔离。"""
    write_cache(DATA_RAW_DIR, kind, code, df, trade_date=trade_date)


def _read_cache(
    kind: str,
    code: str,
    *,
    trade_date: str | None = None,
) -> pd.DataFrame:
    """读取运行时缓存，分时数据只读取请求交易日对应文件。"""
    return read_cache(DATA_RAW_DIR, kind, code, trade_date=trade_date)


def _cap_calendar_to_today(df: pd.DataFrame) -> pd.DataFrame:
    """剔除交易日历中晚于今天的日期。

    akshare 的 tool_trade_date_hist_sina() 返回的是交易所公布的全年交易日历，
    含尚未到来的日期；若直接取末行会拿到未来日期，导致 tushare stk_mins 查空、
    报告标题显示未来日期。统一截断到今天（含）再返回/写缓存。
    """
    today = pd.Timestamp.now().normalize()
    df = df.copy()
    df['trade_date'] = pd.to_datetime(df['trade_date'])
    df = df[df['trade_date'] <= today].reset_index(drop=True)
    return df


# ==============================================================================
# 借鉴主机的重试 + 配额感知错误分类（精简版，无 quota ledger）
# ==============================================================================

def _resolve_tushare_api_url(token_env: str):
    """按 token env key 解析专用 API URL。

    TUSHARE_TOKEN_2 对应 TUSHARE_API_URL_2（如 xiaodefa 转发代理），
    其余回退到通用的 TUSHARE_API_URL。借鉴 linux 主机的 _api_url_env_candidates。
    """
    m = re.fullmatch(r"TUSHARE_TOKEN(_[A-Za-z0-9]+)?", token_env.strip())
    candidates = []
    if m and m.group(1):
        candidates.append(f"TUSHARE_API_URL{m.group(1)}")
    candidates.append("TUSHARE_API_URL")
    for key in candidates:
        url = os.environ.get(key, "").strip()
        if url:
            return url.rstrip("/")
    return None


def get_tushare_client(token_env: str = "TUSHARE_TOKEN"):
    """按单个 env key 构建 tushare pro 客户端；未安装或未设置则抛错（由上层捕获）。

    若该 token 配了专用 API URL（如 token2 走转发代理），则切换到对应端点。
    """
    try:
        import tushare as ts
    except ImportError as exc:
        raise RuntimeError("tushare 未安装，跳过 tushare 数据源") from exc
    token = os.environ.get(token_env, "").strip()
    if not token:
        raise RuntimeError(f"环境变量 {token_env} 未设置")
    client = ts.pro_api(token=token)
    api_url = _resolve_tushare_api_url(token_env)
    if api_url:
        client._DataApi__http_url = api_url
    return client


# ==============================================================================
# 各源的取数实现（返回已规范化的 DataFrame）
# ==============================================================================
def _fetch_calendar_akshare() -> pd.DataFrame:
    df = ak.tool_trade_date_hist_sina()
    if "trade_date" not in df.columns:
        raise RuntimeError("akshare 交易日历缺少 trade_date 列")
    return df


def _fetch_calendar_tushare(client, today_str: str) -> pd.DataFrame:
    raw = client.trade_cal(exchange="", start_date="20200101", end_date=today_str)
    if raw is None or raw.empty:
        raise RuntimeError("tushare trade_cal 返回空")
    open_dates = raw.loc[raw["is_open"].astype(str) == "1", "cal_date"].astype(str)
    if open_dates.empty:
        raise RuntimeError("tushare trade_cal 无开市日")
    return pd.DataFrame({"trade_date": pd.to_datetime(sorted(open_dates))})


def _normalize_akshare_daily(df: pd.DataFrame, code: str) -> pd.DataFrame:
    if df is None or df.empty:
        raise RuntimeError(f"akshare 日线为空：{code}")
    df = df.rename(columns={
        '日期': 'date', '开盘': 'open', '收盘': 'close',
        '最高': 'high', '最低': 'low', '成交量': 'volume',
    })
    required = ['date', 'open', 'close', 'high', 'low', 'volume']
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise RuntimeError(f"akshare 日线缺少字段：{code} {missing}")
    return df[required].copy()


def _fetch_daily_akshare(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    df = ak.stock_zh_a_hist(
        symbol=_code_digits(code), period="daily",
        start_date=start_date, end_date=end_date, adjust="qfq",
    )
    return _normalize_akshare_daily(df, code)


def _fetch_daily_etf_akshare(code: str, start_date: str, end_date: str) -> pd.DataFrame:
    """通过 AKShare 东方财富 ETF 日线接口获取前复权行情。"""
    df = ak.fund_etf_hist_em(
        symbol=_code_digits(code), period="daily",
        start_date=start_date, end_date=end_date, adjust="qfq",
    )
    return _normalize_akshare_daily(df, code)


def _fetch_daily_tushare(client, code: str, start_date: str, end_date: str) -> pd.DataFrame:
    raw = client.daily(ts_code=to_ts_code(code), start_date=start_date,
                       end_date=end_date, adj="qfq")
    if raw is None or raw.empty:
        raise RuntimeError(f"tushare daily 为空：{code}")
    df = raw.rename(columns={'trade_date': 'date', 'vol': 'volume'})
    df = df[['trade_date' if 'trade_date' in df.columns else 'date',
             'open', 'close', 'high', 'low', 'volume']]
    df.rename(columns={'trade_date': 'date'}, inplace=True)
    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    return df.sort_values('date').reset_index(drop=True)


def _fetch_intraday_akshare(code: str) -> pd.DataFrame:
    df = ak.stock_intraday_em(symbol=_code_digits(code))
    if df is None or df.empty:
        raise RuntimeError(f"akshare 分时为空：{code}")
    df = df.rename(columns={'时间': 'time', '成交价': 'price', '手数': 'volume'})
    return df[['time', 'price', 'volume']].copy()


def _fetch_intraday_etf_akshare(code: str, trade_date: str) -> pd.DataFrame:
    """通过 AKShare ETF 1 分钟接口获取指定交易日的分钟行情。"""
    compact_date, iso_date = _normalize_trade_date(trade_date)
    del compact_date
    raw = ak.fund_etf_hist_min_em(
        symbol=_code_digits(code),
        period="1",
        start_date=f"{iso_date} 09:30:00",
        end_date=f"{iso_date} 15:00:00",
        adjust="",
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"akshare ETF 分钟为空：{code} {trade_date}")
    required = {'时间', '收盘', '成交量'}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise RuntimeError(f"akshare ETF 分钟缺少字段：{code} {missing}")
    df = raw.rename(columns={'时间': 'time', '收盘': 'price', '成交量': 'volume'})
    times = pd.to_datetime(df['time'], errors='coerce')
    mask = times.notna() & (times.dt.strftime('%Y-%m-%d') == iso_date)
    df = df.loc[mask, ['time', 'price', 'volume']].copy()
    times = times.loc[mask]
    df['time'] = times.dt.strftime('%H:%M:%S').to_numpy()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df = df.dropna(subset=['time', 'price'])
    if df.empty:
        raise RuntimeError(f"akshare ETF 分钟没有目标交易日数据：{code} {trade_date}")
    return df.sort_values('time').reset_index(drop=True)


def _fetch_intraday_etf_local(code: str, trade_date: str) -> pd.DataFrame:
    """读取 etf-minute-fetcher 按 trade_date 分区保存的 1 分钟 Parquet。"""
    compact_date, _ = _normalize_trade_date(trade_date)
    ts_code = to_ts_code(code)
    path = get_etf_minute_data_root() / ts_code / f"trade_date={compact_date}" / "part.parquet"
    if not path.exists():
        raise FileNotFoundError(f"本地 ETF 分钟分区不存在：{path}")

    raw = pd.read_parquet(path)
    required = {'trade_time', 'close', 'vol'}
    missing = sorted(required.difference(raw.columns))
    if missing:
        raise RuntimeError(f"本地 ETF 分钟分区缺少字段：{path} {missing}")

    times = pd.to_datetime(raw['trade_time'], errors='coerce')
    mask = times.notna() & (times.dt.strftime('%Y%m%d') == compact_date)
    if not mask.any():
        raise RuntimeError(f"本地 ETF 分钟分区没有目标交易日数据：{path}")

    df = raw.loc[mask, ['trade_time', 'close', 'vol']].copy()
    selected_times = times.loc[mask]
    df = df.rename(columns={'close': 'price', 'vol': 'volume'})
    df['time'] = selected_times.dt.strftime('%H:%M:%S').to_numpy()
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    df = df.dropna(subset=['time', 'price']).drop_duplicates(subset=['time'], keep='last')
    return df[['time', 'price', 'volume']].sort_values('time').reset_index(drop=True)


def _fetch_intraday_tushare(client, code: str, trade_date: str) -> pd.DataFrame:
    raw = client.stk_mins(
        ts_code=to_ts_code(code), freq="1min",
        start_date=f"{trade_date} 09:30:00", end_date=f"{trade_date} 15:00:00",
        fields="ts_code,trade_time,open,close,high,low,vol,amount", limit=8000)
    if raw is None or raw.empty:
        raise RuntimeError(f"tushare stk_mins 为空：{code} {trade_date}")
    df = raw.rename(columns={'trade_time': 'time', 'vol': 'volume', 'close': 'price'})
    df = df[['time', 'price', 'volume']].copy()
    # 规范为时间字符串（无日期），与 akshare 分时格式一致，供下游拼接日期。
    df['time'] = pd.to_datetime(df['time']).dt.strftime('%H:%M:%S')
    return df.sort_values('time').reset_index(drop=True)


# ==============================================================================
# 统一接口：akshare -> tushare(token2) -> tushare(token1) -> 缓存
# ==============================================================================
def fetch_trade_calendar() -> pd.DataFrame:
    """返回含 trade_date(datetime) 列的 DataFrame；全部实时源失败则用缓存。"""
    today_str = __import__("datetime").datetime.now().strftime('%Y%m%d')
    errors = []

    try:
        df = _fetch_calendar_akshare()
        if _nonempty(df):
            df = _cap_calendar_to_today(df)
            if _nonempty(df):
                _write_cache("calendar", "sina", df)
                return df
    except Exception as e:
        errors.append(f"akshare: {_redact(e)}")

    for token_env in TUSHARE_TOKEN_ENVS:
        try:
            client = get_tushare_client(token_env=token_env)
        except Exception as e:
            errors.append(f"tushare {token_env} 初始化: {_redact(e)}")
            continue
        try:
            df = _call_tushare_api(
                lambda client=client: _fetch_calendar_tushare(client, today_str)
            )
            if _nonempty(df):
                df = _cap_calendar_to_today(df)
                if _nonempty(df):
                    _write_cache("calendar", "sina", df)
                    return df
        except Exception as e:
            errors.append(f"tushare {token_env}: {_redact(e)}")
            continue

    df = _read_cache("calendar", "sina")
    if _nonempty(df):
        print("  > 使用缓存快照（实时源均失败）：trade_calendar")
        df = _cap_calendar_to_today(df)
        if _nonempty(df):
            return df
    raise RuntimeError(f"交易日历抓取失败且无缓存；错误：{errors}")


def fetch_daily(
    code: str,
    start_date: str,
    end_date: str,
    *,
    instrument_type: str = "stock",
) -> pd.DataFrame:
    """获取股票或 ETF 日线，并统一成 date/open/close/high/low/volume。"""
    kind = normalize_instrument_type(instrument_type)
    errors = []

    try:
        if kind == "etf":
            df = _fetch_daily_etf_akshare(code, start_date, end_date)
        else:
            df = _fetch_daily_akshare(code, start_date, end_date)
        if _nonempty(df):
            _write_cache("daily", code, df)
            return df
    except Exception as e:
        errors.append(f"akshare {kind}: {_redact(e)}")

    # 现有 tushare daily 兜底继续只用于股票。ETF 先使用 AKShare 专用日线接口，
    # 避免把股票日线接口误当成基金行情接口。
    if kind == "stock":
        for token_env in TUSHARE_TOKEN_ENVS:
            try:
                client = get_tushare_client(token_env=token_env)
            except Exception as e:
                errors.append(f"tushare {token_env} 初始化: {_redact(e)}")
                continue
            try:
                df = _call_tushare_api(
                    lambda client=client: _fetch_daily_tushare(client, code, start_date, end_date)
                )
                if _nonempty(df):
                    _write_cache("daily", code, df)
                    return df
            except Exception as e:
                errors.append(f"tushare {token_env}: {_redact(e)}")
                continue

    df = _read_cache("daily", code)
    if _nonempty(df):
        print(f"  > 使用缓存快照（实时源均失败）：daily {code}")
        return df
    raise RuntimeError(f"日线抓取失败且无缓存：{code}；错误：{errors}")


def fetch_intraday(
    code: str,
    trade_date: str,
    *,
    instrument_type: str = "stock",
) -> pd.DataFrame:
    """获取股票或 ETF 分时，统一返回 time/price/volume。"""
    kind = normalize_instrument_type(instrument_type)
    errors = []

    if kind == "etf":
        try:
            df = _fetch_intraday_etf_local(code, trade_date)
            if _nonempty(df):
                return df
        except Exception as e:
            errors.append(f"local parquet: {_redact(e)}")

        try:
            df = _fetch_intraday_etf_akshare(code, trade_date)
            if _nonempty(df):
                _write_cache("intraday", code, df, trade_date=trade_date)
                return df
        except Exception as e:
            errors.append(f"akshare etf: {_redact(e)}")

        df = _read_cache("intraday", code, trade_date=trade_date)
        if _nonempty(df):
            print(f"  > 使用缓存快照（ETF 分钟源均失败）：intraday {code} {trade_date}")
            return df
        raise RuntimeError(f"ETF 分时抓取失败且无缓存：{code}；错误：{errors}")

    today_str = _dt.datetime.now().strftime('%Y-%m-%d')

    # akshare 的 stock_intraday_em 无日期参数，永远返回当天实时分时；
    # 仅当请求的 trade_date 就是今天时才尝试，历史交易日直接走 tushare，
    # 否则会把"今天"的数据错配到历史日期的时间戳上。
    if trade_date == today_str:
        try:
            df = _fetch_intraday_akshare(code)
            if _nonempty(df):
                _write_cache("intraday", code, df, trade_date=trade_date)
                return df
        except Exception as e:
            errors.append(f"akshare: {_redact(e)}")
    else:
        errors.append("akshare: 仅支持当天分时，历史日期跳过（走 tushare）")

    for token_env in TUSHARE_TOKEN_ENVS:
        try:
            client = get_tushare_client(token_env=token_env)
        except Exception as e:
            errors.append(f"tushare {token_env} 初始化: {_redact(e)}")
            continue
        try:
            df = _call_tushare_api(
                lambda client=client: _fetch_intraday_tushare(client, code, trade_date)
            )
            if _nonempty(df):
                _write_cache("intraday", code, df, trade_date=trade_date)
                return df
        except Exception as e:
            errors.append(f"tushare {token_env}: {_redact(e)}")
            continue

    df = _read_cache("intraday", code, trade_date=trade_date)
    if _nonempty(df):
        print(f"  > 使用缓存快照（实时源均失败）：intraday {code} {trade_date}")
        return df
    raise RuntimeError(f"分时抓取失败且无缓存：{code}；错误：{errors}")
