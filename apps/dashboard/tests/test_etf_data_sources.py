# -*- coding: utf-8 -*-
"""ETF 数据接入的离线测试。"""

from __future__ import annotations

import sys

import pandas as pd
import pytest

from trading_research.data import data_sources as ds


def _fake_etf_daily() -> pd.DataFrame:
    return pd.DataFrame({
        '日期': ['2024-01-02', '2024-01-03'],
        '开盘': [2.50, 2.51],
        '收盘': [2.51, 2.52],
        '最高': [2.52, 2.53],
        '最低': [2.49, 2.50],
        '成交量': [1000, 1100],
    })


def _fake_etf_minute() -> pd.DataFrame:
    return pd.DataFrame({
        '时间': ['2024-01-03 09:31:00', '2024-01-03 09:32:00'],
        '开盘': [2.50, 2.51],
        '收盘': [2.51, 2.52],
        '最高': [2.52, 2.53],
        '最低': [2.49, 2.50],
        '成交量': [1000, 1100],
    })


def test_to_ts_code_accepts_both_code_styles():
    assert ds.to_ts_code('sh600199') == '600199.SH'
    assert ds.to_ts_code('600199.SH') == '600199.SH'
    assert ds.to_ts_code('510050.SH') == '510050.SH'
    assert ds.to_ts_code('sz159915') == '159915.SZ'


def test_instrument_type_validation():
    assert ds.normalize_instrument_type(None) == 'stock'
    assert ds.normalize_instrument_type('ETF') == 'etf'
    with pytest.raises(ValueError, match='instrument_type'):
        ds.normalize_instrument_type('bond')


def test_etf_daily_uses_etf_akshare_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(tmp_path / 'cache'))
    calls = []

    def fake_fund_etf_hist_em(**kwargs):
        calls.append(kwargs)
        return _fake_etf_daily()

    monkeypatch.setattr(ds.ak, 'fund_etf_hist_em', fake_fund_etf_hist_em)
    monkeypatch.setattr(
        ds.ak,
        'stock_zh_a_hist',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError('ETF 不应调用股票日线接口')),
    )

    frame = ds.fetch_daily(
        '510050.SH', '20240101', '20240103', instrument_type='etf'
    )

    assert frame.columns.tolist() == ['date', 'open', 'close', 'high', 'low', 'volume']
    assert frame['close'].tolist() == [2.51, 2.52]
    assert calls == [{
        'symbol': '510050',
        'period': 'daily',
        'start_date': '20240101',
        'end_date': '20240103',
        'adjust': 'qfq',
    }]


def test_etf_intraday_prefers_local_parquet(monkeypatch, tmp_path):
    root = tmp_path / 'minute'
    part_dir = root / '510050.SH' / 'trade_date=20240103'
    part_dir.mkdir(parents=True)
    pd.DataFrame({
        'ts_code': ['510050.SH', '510050.SH'],
        'trade_time': pd.to_datetime([
            '2024-01-03 09:31:00',
            '2024-01-03 09:32:00',
        ]),
        'open': [2.50, 2.51],
        'high': [2.52, 2.53],
        'low': [2.49, 2.50],
        'close': [2.51, 2.52],
        'vol': [1000, 1100],
        'amount': [2500.0, 2770.0],
    }).to_parquet(part_dir / 'part.parquet', index=False)

    monkeypatch.setenv(ds.ETF_MINUTE_DATA_ROOT_ENV, str(root))
    monkeypatch.setattr(
        ds.ak,
        'fund_etf_hist_min_em',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError('本地命中后不应请求网络')),
    )

    frame = ds.fetch_intraday('510050.SH', '2024-01-03', instrument_type='etf')

    assert frame.columns.tolist() == ['time', 'price', 'volume']
    assert frame['time'].tolist() == ['09:31:00', '09:32:00']
    assert frame['price'].tolist() == [2.51, 2.52]
    assert frame['volume'].tolist() == [1000, 1100]


def test_etf_intraday_falls_back_to_akshare_when_local_missing(monkeypatch, tmp_path):
    cache_root = tmp_path / 'cache'
    monkeypatch.setattr(ds, 'DATA_RAW_DIR', str(cache_root))
    monkeypatch.setenv(ds.ETF_MINUTE_DATA_ROOT_ENV, str(tmp_path / 'missing-minute-root'))
    calls = []

    def fake_fund_etf_hist_min_em(**kwargs):
        calls.append(kwargs)
        return _fake_etf_minute()

    monkeypatch.setattr(ds.ak, 'fund_etf_hist_min_em', fake_fund_etf_hist_min_em)

    frame = ds.fetch_intraday('510050.SH', '2024-01-03', instrument_type='etf')

    assert frame['time'].tolist() == ['09:31:00', '09:32:00']
    assert frame['price'].tolist() == [2.51, 2.52]
    assert calls == [{
        'symbol': '510050',
        'period': '1',
        'start_date': '2024-01-03 09:30:00',
        'end_date': '2024-01-03 15:00:00',
        'adjust': '',
    }]
    assert (cache_root / 'intraday' / '510050.SH' / '20240103.csv').is_file()


def test_etf_intraday_rejects_malformed_local_partition(monkeypatch, tmp_path):
    root = tmp_path / 'minute'
    part_dir = root / '510050.SH' / 'trade_date=20240103'
    part_dir.mkdir(parents=True)
    pd.DataFrame({
        'trade_time': pd.to_datetime(['2024-01-03 09:31:00']),
        'close': [2.51],
    }).to_parquet(part_dir / 'part.parquet', index=False)

    monkeypatch.setenv(ds.ETF_MINUTE_DATA_ROOT_ENV, str(root))
    monkeypatch.setattr(
        ds.ak,
        'fund_etf_hist_min_em',
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError('network down')),
    )
    monkeypatch.setattr(ds, '_read_cache', lambda *args, **kwargs: pd.DataFrame())

    with pytest.raises(RuntimeError, match='ETF 分时抓取失败'):
        ds.fetch_intraday('510050.SH', '2024-01-03', instrument_type='etf')
