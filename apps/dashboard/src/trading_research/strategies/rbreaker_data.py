"""R-Breaker market data download and loading helpers."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

import akshare as ak
import pandas as pd


def download_stock_data_tushare(
    symbol, start_date, end_date, data_folder="data", token=None
):
    """使用 Tushare 下载分钟级别数据。token 从环境变量或参数读取。"""
    try:
        import tushare as ts
    except ImportError as exc:
        raise RuntimeError("未安装 tushare，请执行: pip install tushare") from exc
    if not os.path.exists(data_folder):
        os.makedirs(data_folder)
    ts_code = f"{symbol}.SH" if symbol.startswith("6") else f"{symbol}.SZ"
    start_time = datetime.strptime(start_date, "%Y%m%d").strftime("%Y-%m-%d 09:30:00")
    end_time = datetime.strptime(end_date, "%Y%m%d").strftime("%Y-%m-%d 15:00:00")
    token = token or os.environ.get("TUSHARE_TOKEN")
    if not token:
        raise RuntimeError("使用 tushare 数据源需要 token。请设置环境变量 TUSHARE_TOKEN 或传入 --tushare-token。")
    ts.set_token(token)
    data = ts.pro_api().stk_mins(
        ts_code=ts_code, freq="1min", start_date=start_time, end_date=end_time
    )
    if data.empty:
        raise RuntimeError("Tushare 在该时间段未返回数据。")
    data = data.rename(columns={
        "trade_time": "时间", "open": "开盘", "high": "最高",
        "low": "最低", "close": "收盘", "vol": "成交量",
    })[["时间", "开盘", "最高", "最低", "收盘", "成交量"]]
    data["时间"] = pd.to_datetime(data["时间"])
    data = data.sort_values("时间").reset_index(drop=True)
    data.to_csv(f"{data_folder}/{symbol}_{start_date}_{end_date}.csv", index=False, encoding="utf-8-sig")
    return True


def load_or_download_data(symbol, start_date, end_date, data_folder="data", token=None):
    """检查本地是否有数据文件，如果没有则调用 Tushare 下载。"""
    filename = f"{data_folder}/{symbol}_{start_date}_{end_date}.csv"
    if not os.path.exists(filename):
        download_stock_data_tushare(symbol, start_date, end_date, data_folder, token=token)
    try:
        data = pd.read_csv(filename, encoding="utf-8-sig")
        data["时间"] = pd.to_datetime(data["时间"])
        return data
    except (OSError, ValueError, KeyError):
        return pd.DataFrame()


def load_minute_data_akshare(symbol, start_date, end_date):
    """使用 Akshare 下载分钟数据。"""
    data = ak.stock_zh_a_hist_min_em(
        symbol=symbol, period="1", adjust="", start_date=start_date, end_date=end_date
    )
    if data is None or data.empty:
        raise RuntimeError("Akshare 未获取到分钟数据。")
    data["datetime"] = pd.to_datetime(data["时间"])
    return data.set_index("datetime")


def get_recent_trading_days_with_prev(symbol, n_days):
    """获取最近 n 个交易日及之前一个交易日的日线数据。"""
    start_date = (datetime.now() - timedelta(days=n_days + 30)).strftime("%Y%m%d")
    end_date = datetime.now().strftime("%Y%m%d")
    data = ak.stock_zh_a_hist(
        symbol=symbol, period="daily", adjust="qfq", start_date=start_date, end_date=end_date
    )
    data["日期"] = pd.to_datetime(data["日期"])
    data = data.sort_values("日期")
    if len(data) < n_days + 1:
        return pd.DataFrame()
    return data.tail(n_days + 1).reset_index(drop=True)
