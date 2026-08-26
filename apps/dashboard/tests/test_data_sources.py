# -*- coding: utf-8 -*-
"""data_sources 的离线测试：mock akshare / tushare，验证兜底顺序、列规范化与缓存。"""

import os
import sys

import pandas as pd
import pytest

from trading_research.data import data_sources as ds


def _fake_akshare_calendar():
    return pd.DataFrame({'trade_date': pd.to_datetime(['2024-01-02', '2024-01-03'])})


def _fake_akshare_daily():
    return pd.DataFrame({
        '日期': ['2024-01-02', '2024-01-03'],
        '开盘': [10.0, 10.5], '收盘': [10.3, 10.8],
        '最高': [10.5, 11.0], '最低': [9.8, 10.2], '成交量': [1000, 1100],
    })


def _fake_akshare_intraday():
    return pd.DataFrame({
        '时间': ['09:31', '09:32'],
        '成交价': [10.1, 10.2], '手数': [100, 110],
    })


def _fake_tushare_daily():
    return pd.DataFrame({
        'ts_code': ['600199.SH', '600199.SH'],
        'trade_date': ['2024-01-02', '2024-01-03'],
        'open': [10.0, 10.5], 'high': [10.5, 11.0], 'low': [9.8, 10.2],
        'close': [10.3, 10.8], 'vol': [1000, 1100], 'amount': [10000, 11000],
    })


def _fake_tushare_intraday():
    return pd.DataFrame({
        'ts_code': ['600199.SH', '600199.SH'],
        'trade_time': [pd.Timestamp('2024-01-03 09:31:00'), pd.Timestamp('2024-01-03 09:32:00')],
        'open': [10.0, 10.1], 'high': [10.2, 10.3], 'low': [9.9, 10.0],
        'close': [10.1, 10.2], 'vol': [100, 110], 'amount': [1010, 1020],
    })


class _FakePro:
    def trade_cal(self, exchange, start_date, end_date):
        return pd.DataFrame({
            'exchange': ['', ''],
            'cal_date': ['2024-01-02', '2024-01-03'],
            'is_open': ['1', '1'],
        })

    def daily(self, ts_code, start_date, end_date, adj=None):
        return _fake_tushare_daily()

    def stk_mins(self, ts_code, freq, start_date, end_date, fields, limit):
        return _fake_tushare_intraday()


def test_to_ts_code():
    assert ds.to_ts_code('sh600199') == '600199.SH'
    assert ds.to_ts_code('sz000001') == '000001.SZ'
    assert ds.to_ts_code('bj830799') == '830799.BJ'


def test_akshare_primary_daily(monkeypatch, tmp_path):
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(tmp_path / 'data' / 'raw'))
    monkeypatch.setattr(ds.ak, 'stock_zh_a_hist', lambda **k: _fake_akshare_daily())
    calls = []
    monkeypatch.setattr(ds, 'get_tushare_client', lambda **k: calls.append(k) or _FakePro())
    df = ds.fetch_daily('sh600199', '20240101', '20240103')
    assert list(df.columns) == ['date', 'open', 'close', 'high', 'low', 'volume']
    assert df['date'].iloc[0] == '2024-01-02'
    assert df['volume'].iloc[0] == 1000
    assert calls == []  # akshare 成功时不应调用 tushare
    assert os.path.exists(tmp_path / 'data' / 'raw' / 'daily' / 'sh600199.csv')


def test_tushare_fallback_daily(monkeypatch, tmp_path):
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(tmp_path / 'data' / 'raw'))
    monkeypatch.setattr(ds.ak, 'stock_zh_a_hist', lambda **k: (_ for _ in ()).throw(RuntimeError('akshare down')))
    monkeypatch.setattr(ds, 'get_tushare_client', lambda **k: _FakePro())
    df = ds.fetch_daily('sh600199', '20240101', '20240103')
    assert list(df.columns) == ['date', 'open', 'close', 'high', 'low', 'volume']
    assert df['date'].iloc[-1] == '2024-01-03'


def test_all_live_fail_uses_cache_daily(monkeypatch, tmp_path):
    raw = tmp_path / 'data' / 'raw'
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(raw))
    # 预置缓存
    cache_df = pd.DataFrame({
        'date': ['2024-01-02'], 'open': [9.0], 'close': [9.3],
        'high': [9.5], 'low': [8.8], 'volume': [900],
    })
    d = raw / 'daily'
    d.mkdir(parents=True)
    cache_df.to_csv(d / 'sh600199.csv', index=False)

    monkeypatch.setattr(ds.ak, 'stock_zh_a_hist', lambda **k: (_ for _ in ()).throw(RuntimeError('akshare down')))
    monkeypatch.setattr(ds, 'get_tushare_client', lambda **k: (_ for _ in ()).throw(RuntimeError('no token')))

    df = ds.fetch_daily('sh600199', '20240101', '20240103')
    assert not df.empty
    assert df['date'].iloc[0] == '2024-01-02'
    assert df['close'].iloc[0] == 9.3


def test_akshare_intraday_only_for_today(monkeypatch, tmp_path):
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(tmp_path / 'data' / 'raw'))
    monkeypatch.setattr(ds.ak, 'stock_intraday_em', lambda **k: _fake_akshare_intraday())
    monkeypatch.setattr(ds, 'get_tushare_client', lambda **k: _FakePro())
    # akshare 无日期参数、永远返回当天实时分时：仅当请求日期==今天才走 akshare
    today = ds._dt.datetime.now().strftime('%Y-%m-%d')
    df = ds.fetch_intraday('sh600199', today)
    assert list(df.columns) == ['time', 'price', 'volume']
    assert df['time'].iloc[0] == '09:31'  # akshare 原样时间
    # 历史交易日：akshare 跳过，直接走 tushare（时间规范为 HH:MM:SS）
    df2 = ds.fetch_intraday('sh600199', '2024-01-03')
    assert df2['time'].iloc[0] == '09:31:00'


def test_tushare_intraday_normalizes_time(monkeypatch, tmp_path):
    raw = tmp_path / 'data' / 'raw'
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(raw))
    monkeypatch.setattr(ds.ak, 'stock_intraday_em', lambda **k: (_ for _ in ()).throw(RuntimeError('akshare down')))
    monkeypatch.setattr(ds, 'get_tushare_client', lambda **k: _FakePro())
    df = ds.fetch_intraday('sh600199', '2024-01-03')
    assert list(df.columns) == ['time', 'price', 'volume']
    # tushare trade_time 应为无日期的时间字符串，供下游拼接日期
    assert df['time'].iloc[0] == '09:31:00'
    assert df['price'].iloc[0] == 10.1
    assert df['volume'].iloc[0] == 100
    assert (raw / 'intraday' / 'sh600199' / '20240103.csv').is_file()


def test_historical_intraday_does_not_reuse_undated_cache(monkeypatch, tmp_path):
    raw = tmp_path / 'data' / 'raw'
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(raw))
    old_cache = raw / 'intraday' / 'sh600199.csv'
    old_cache.parent.mkdir(parents=True)
    pd.DataFrame({
        'time': ['09:31:00'],
        'price': [8.88],
        'volume': [88],
    }).to_csv(old_cache, index=False)
    monkeypatch.setattr(
        ds,
        'get_tushare_client',
        lambda **k: (_ for _ in ()).throw(RuntimeError('no token')),
    )

    with pytest.raises(RuntimeError, match='分时抓取失败且无缓存'):
        ds.fetch_intraday('sh600199', '2024-01-03')


def test_calendar_akshare_primary(monkeypatch, tmp_path):
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(tmp_path / 'data' / 'raw'))
    monkeypatch.setattr(ds.ak, 'tool_trade_date_hist_sina', lambda: _fake_akshare_calendar())
    df = ds.fetch_trade_calendar()
    assert 'trade_date' in df.columns
    assert df['trade_date'].iloc[-1] == pd.Timestamp('2024-01-03')


def test_calendar_caps_to_today(monkeypatch, tmp_path):
    """akshare 返回含未来交易日的全年日历时，须截断到今天（含）。"""
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(tmp_path / 'data' / 'raw'))
    today = pd.Timestamp.now().normalize()
    future = today + pd.Timedelta(days=120)
    fake = pd.DataFrame({'trade_date': pd.to_datetime(['2024-01-02', today, future])})
    monkeypatch.setattr(ds.ak, 'tool_trade_date_hist_sina', lambda: fake)
    df = ds.fetch_trade_calendar()
    # 末行（即下游取的 last_trade_day_str）不得晚于今天
    assert df['trade_date'].iloc[-1] == today
    assert df['trade_date'].max() <= today
    # 缓存快照也不能包含未来日期，否则下次读取会复活问题
    cache = pd.read_csv(tmp_path / 'data' / 'raw' / 'calendar' / 'sina.csv')
    assert pd.to_datetime(cache['trade_date']).max() <= today


def test_quota_error_classification():
    assert ds._is_daily_quota_exhausted(RuntimeError('今日请求次数已达上限'))
    assert ds._is_quota_error(RuntimeError('访问频率已超速，增加等待几秒重试'))
    assert ds._is_retryable_provider_error(RuntimeError('RemoteDisconnected'))  # 海外 CI 偶发
    assert ds._is_retryable_provider_error(RuntimeError('Remote end closed connection without response'))
    assert not ds._is_retryable_provider_error(RuntimeError('今日请求次数已达上限'))


def test_resolve_api_url(monkeypatch):
    monkeypatch.delenv('TUSHARE_API_URL_2', raising=False)
    monkeypatch.delenv('TUSHARE_API_URL', raising=False)
    assert ds._resolve_tushare_api_url('TUSHARE_TOKEN') is None
    monkeypatch.setenv('TUSHARE_API_URL_2', 'http://proxy.example.com/')
    assert ds._resolve_tushare_api_url('TUSHARE_TOKEN_2') == 'http://proxy.example.com'
    monkeypatch.setenv('TUSHARE_API_URL', 'http://public.example.com')
    assert ds._resolve_tushare_api_url('TUSHARE_TOKEN') == 'http://public.example.com'
    # 专用 URL 优先于通用
    assert ds._resolve_tushare_api_url('TUSHARE_TOKEN_2') == 'http://proxy.example.com'


def test_get_tushare_client_sets_api_url(monkeypatch):
    class FakeClient:
        pass

    class FakeTs:
        @staticmethod
        def pro_api(token=None):
            return FakeClient()

    # 注入假的 tushare 模块，避免依赖真实包
    monkeypatch.setitem(sys.modules, 'tushare', FakeTs)
    monkeypatch.setenv('TUSHARE_API_URL_2', 'http://proxy.example.com/')
    monkeypatch.setenv('TUSHARE_TOKEN_2', 'dummy')
    client = ds.get_tushare_client(token_env='TUSHARE_TOKEN_2')
    assert client._DataApi__http_url == 'http://proxy.example.com'
