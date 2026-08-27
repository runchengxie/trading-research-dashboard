"""ETF 从配置到 Dashboard payload 的整合测试。"""

from __future__ import annotations

import json

import pandas as pd

from trading_research.dashboard import astock_tech as dashboard


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


def _calendar() -> pd.DataFrame:
    today = pd.Timestamp.now().normalize()
    return pd.DataFrame({
        'trade_date': [today - pd.Timedelta(days=2), today - pd.Timedelta(days=1), today]
    })


def _etf_config() -> dict[str, dict[str, str]]:
    return {
        '510050.SH': {
            'name': '上证50ETF',
            'instrument_type': 'etf',
        }
    }


def test_dashboard_routes_etf_through_unified_data_layer(monkeypatch, tmp_path):
    calls = []

    monkeypatch.setattr(dashboard, 'STOCK_CONFIG', _etf_config())
    monkeypatch.setattr(dashboard.data_sources, 'fetch_trade_calendar', _calendar)

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


def test_dashboard_marks_vwap_deviation_missing_without_intraday(monkeypatch, tmp_path):
    monkeypatch.setattr(dashboard, 'STOCK_CONFIG', _etf_config())
    monkeypatch.setattr(dashboard.data_sources, 'fetch_trade_calendar', _calendar)
    monkeypatch.setattr(
        dashboard.data_sources,
        'fetch_daily',
        lambda *args, **kwargs: _daily_frame(),
    )
    monkeypatch.setattr(
        dashboard.data_sources,
        'fetch_intraday',
        lambda *args, **kwargs: pd.DataFrame(),
    )

    _, payloads, _ = dashboard.main(output_root=str(tmp_path / 'out'))

    indicators = payloads[0]['indicators']
    assert indicators['vwap'] is None
    assert indicators['vwapDev'] is None
    assert indicators['vwapDevThreshold'] is not None


def test_dashboard_calendar_failure_falls_back_to_yesterday(monkeypatch, tmp_path):
    expected_day = (pd.Timestamp.now().normalize() - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
    intraday_calls: list[str] = []

    monkeypatch.setattr(dashboard, 'STOCK_CONFIG', _etf_config())
    monkeypatch.setattr(
        dashboard.data_sources,
        'fetch_trade_calendar',
        lambda: (_ for _ in ()).throw(RuntimeError('calendar down')),
    )
    monkeypatch.setattr(
        dashboard.data_sources,
        'fetch_daily',
        lambda *args, **kwargs: _daily_frame(),
    )

    def fake_intraday(code, trade_date, *, instrument_type='stock'):
        del code, instrument_type
        intraday_calls.append(trade_date)
        return _intraday_frame()

    monkeypatch.setattr(dashboard.data_sources, 'fetch_intraday', fake_intraday)

    results, payloads, last_trade_day = dashboard.main(output_root=str(tmp_path / 'out'))

    assert results
    assert payloads
    assert last_trade_day == expected_day
    assert intraday_calls == [expected_day]
