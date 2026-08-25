# -*- coding: utf-8 -*-
"""ETF 从配置到 Dashboard payload 的整合测试。"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path('.').resolve()))

import astock_tech as dashboard


def _daily_frame() -> pd.DataFrame:
    dates = pd.date_range('2026-06-01', periods=40, freq='B')
    base = pd.Series(range(len(dates)), dtype='float64') * 0.01 + 2.0
    return pd.DataFrame({
        'date': dates,
        'open': base + 0.01,
        'close': base + 0.02,
        'high': base + 0.04,
        'low': base - 0.02,
        'volume': 1000 + pd.Series(range(len(dates))) * 10,
    })


def _intraday_frame() -> pd.DataFrame:
    return pd.DataFrame({
        'time': ['09:31:00', '09:40:00', '09:45:00', '10:00:00'],
        'price': [2.38, 2.39, 2.40, 2.41],
        'volume': [1000, 1200, 900, 1500],
    })


def test_dashboard_routes_etf_through_unified_data_layer(monkeypatch, tmp_path):
    today = pd.Timestamp.now().normalize()
    calendar = pd.DataFrame({
        'trade_date': [today - pd.Timedelta(days=2), today - pd.Timedelta(days=1), today]
    })
    calls = []

    monkeypatch.setattr(
        dashboard,
        'STOCK_CONFIG',
        {
            '510050.SH': {
                'name': '上证50ETF',
                'instrument_type': 'etf',
            }
        },
    )
    monkeypatch.setattr(dashboard.data_sources, 'fetch_trade_calendar', lambda: calendar.copy())

    def fake_daily(code, start_date, end_date, *, instrument_type='stock'):
        calls.append(('daily', code, instrument_type))
        return _daily_frame()

    def fake_intraday(code, trade_date, *, instrument_type='stock'):
        calls.append(('intraday', code, instrument_type))
        return _intraday_frame()

    monkeypatch.setattr(dashboard.data_sources, 'fetch_daily', fake_daily)
    monkeypatch.setattr(dashboard.data_sources, 'fetch_intraday', fake_intraday)

    json_path = tmp_path / 'data.json'
    results, payloads, _ = dashboard.main(
        output_root=str(tmp_path / 'out'),
        json_path=str(json_path),
    )

    assert results
    assert calls == [
        ('daily', '510050.SH', 'etf'),
        ('intraday', '510050.SH', 'etf'),
    ]
    assert len(payloads) == 1
    assert payloads[0]['code'] == '510050.SH'
    assert payloads[0]['instrumentType'] == 'etf'
    assert payloads[0]['intraday']

    saved = json.loads(json_path.read_text(encoding='utf-8'))
    assert saved['stocks'][0]['instrumentType'] == 'etf'
