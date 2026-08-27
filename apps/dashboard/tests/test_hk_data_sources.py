import pandas as pd

from trading_research.data import market_compat as ds


def _fake_hk_daily() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "日期": ["2026-08-25", "2026-08-26"],
            "开盘": [600.0, 605.0],
            "收盘": [604.0, 610.0],
            "最高": [608.0, 612.0],
            "最低": [598.0, 603.0],
            "成交量": [1_000, 1_100],
        }
    )


def _fake_hk_minute() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "时间": ["2026-08-26 09:31:00", "2026-08-26 09:32:00"],
            "开盘": [605.0, 606.0],
            "收盘": [606.0, 607.0],
            "最高": [606.5, 607.5],
            "最低": [604.5, 605.5],
            "成交量": [100, 110],
            "成交额": [60_600, 66_770],
            "最新价": [606.0, 607.0],
        }
    )


def test_cn_market_delegates_to_existing_data_layer(monkeypatch) -> None:
    sentinel = pd.DataFrame({"date": ["2026-08-26"]})
    calls = {}

    def fake_fetch(*args, **kwargs):
        calls["args"] = args
        calls["kwargs"] = kwargs
        return sentinel

    monkeypatch.setattr(ds.data_sources, "fetch_daily", fake_fetch)

    result = ds.fetch_daily("sz300246", "20260801", "20260826", market="CN")

    assert result is sentinel
    assert calls["args"] == ("sz300246", "20260801", "20260826")
    assert calls["kwargs"] == {"instrument_type": "stock"}


def test_fetch_daily_hk_uses_hk_hist_and_normalizes_schema(monkeypatch, tmp_path) -> None:
    calls = {}
    monkeypatch.setattr(ds.data_sources, "DATA_RAW_DIR", str(tmp_path / "data" / "raw"))

    def fake_hk_hist(**kwargs):
        calls.update(kwargs)
        return _fake_hk_daily()

    monkeypatch.setattr(ds.ak, "stock_hk_hist", fake_hk_hist)

    df = ds.fetch_daily("00700.HK", "20260801", "20260826", market="HK")

    assert calls == {
        "symbol": "00700",
        "period": "daily",
        "start_date": "20260801",
        "end_date": "20260826",
        "adjust": "qfq",
    }
    assert list(df.columns) == ["date", "open", "close", "high", "low", "volume"]
    assert df.iloc[-1]["close"] == 610.0


def test_fetch_intraday_hk_uses_delayed_hk_minute_adapter(monkeypatch, tmp_path) -> None:
    calls = {}
    monkeypatch.setattr(ds.data_sources, "DATA_RAW_DIR", str(tmp_path / "data" / "raw"))

    def fake_hk_minute(**kwargs):
        calls.update(kwargs)
        return _fake_hk_minute()

    monkeypatch.setattr(ds.ak, "stock_hk_hist_min_em", fake_hk_minute)

    df = ds.fetch_intraday("hk00700", "2026-08-26", market="HK")

    assert calls["symbol"] == "00700"
    assert calls["period"] == "1"
    assert calls["adjust"] == ""
    assert calls["start_date"] == "2026-08-26 09:30:00"
    assert calls["end_date"] == "2026-08-26 16:00:00"
    assert list(df.columns) == ["time", "price", "volume"]
    assert df["time"].tolist() == ["09:31:00", "09:32:00"]
    assert df["price"].tolist() == [606.0, 607.0]


def test_hk_live_failure_uses_existing_runtime_cache(monkeypatch, tmp_path) -> None:
    raw = tmp_path / "data" / "raw"
    monkeypatch.setattr(ds.data_sources, "DATA_RAW_DIR", str(raw))
    cached = pd.DataFrame(
        {
            "date": ["2026-08-25"],
            "open": [600.0],
            "close": [604.0],
            "high": [608.0],
            "low": [598.0],
            "volume": [1_000],
        }
    )
    cache_dir = raw / "daily"
    cache_dir.mkdir(parents=True)
    cached.to_csv(cache_dir / "00700.HK.csv", index=False)
    monkeypatch.setattr(
        ds.ak,
        "stock_hk_hist",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("hk provider down")),
    )

    df = ds.fetch_daily("00700.HK", "20260801", "20260826", market="HK")

    assert df.iloc[0]["close"] == 604.0


def test_market_profile_exposes_currency_timezone_and_live_capability() -> None:
    hk = ds.market_profile("HK")
    us = ds.market_profile("US")

    assert (hk.currency, hk.timezone, hk.live_provider) == ("HKD", "Asia/Hong_Kong", None)
    assert (us.currency, us.timezone, us.live_provider) == ("USD", "America/New_York", "alpaca")
