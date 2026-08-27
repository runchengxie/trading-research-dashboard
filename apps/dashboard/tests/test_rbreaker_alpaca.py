from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from trading_research.rbreaker_alpaca import (
    extract_previous_day_ohlc,
    normalize_regular_session_bars,
    validate_regular_session_bars,
    write_alpaca_artifact,
)
from trading_research.scripts.build_rbreaker_alpaca_artifact import (
    default_output_root,
    fetch_and_write_artifact,
)


def _bar(timestamp: str, price: float = 100.0) -> SimpleNamespace:
    return SimpleNamespace(
        timestamp=datetime.fromisoformat(timestamp),
        open=price,
        high=price + 1,
        low=price - 1,
        close=price + 0.5,
        volume=100,
    )


def test_normalize_bars_keeps_only_new_york_regular_session() -> None:
    bars = normalize_regular_session_bars(
        [
            _bar("2025-08-20T13:29:00+00:00"),
            _bar("2025-08-20T13:30:00+00:00", 101),
            _bar("2025-08-20T19:59:00+00:00", 102),
            _bar("2025-08-20T20:00:00+00:00"),
        ],
        session_date=date(2025, 8, 20),
    )

    assert list(bars.index) == [
        pd.Timestamp("2025-08-20 09:30", tz="America/New_York"),
        pd.Timestamp("2025-08-20 15:59", tz="America/New_York"),
    ]
    assert list(bars.columns) == ["open", "high", "low", "close", "volume"]


def test_validate_regular_session_bars_rejects_missing_minute() -> None:
    bars = normalize_regular_session_bars(
        [_bar("2025-08-20T13:30:00+00:00"), _bar("2025-08-20T13:32:00+00:00")],
        session_date=date(2025, 8, 20),
    )

    try:
        validate_regular_session_bars(bars, expected_bars=2)
    except ValueError as exc:
        assert "continuous" in str(exc)
    else:
        raise AssertionError("a missing minute must fail the completeness gate")


def test_expected_regular_session_bars_handles_us_early_close() -> None:
    from trading_research.rbreaker_alpaca import expected_regular_session_bars

    assert expected_regular_session_bars(date(2025, 7, 3)) == 210
    assert expected_regular_session_bars(date(2025, 7, 2)) == 390


def test_extract_previous_day_ohlc_uses_latest_prior_new_york_session() -> None:
    result = extract_previous_day_ohlc(
        [
            _bar("2025-08-18T04:00:00+00:00", 98),
            _bar("2025-08-19T04:00:00+00:00", 99),
            _bar("2025-08-20T04:00:00+00:00", 100),
        ],
        session_date=date(2025, 8, 20),
    )

    assert result == {"high": 100.0, "low": 98.0, "close": 99.5}


def test_write_alpaca_artifact_creates_hashed_manifest(tmp_path: Path) -> None:
    bars = normalize_regular_session_bars(
        [_bar("2025-08-20T13:30:00+00:00")],
        session_date=date(2025, 8, 20),
    )

    root = write_alpaca_artifact(
        tmp_path / "aapl-input",
        symbol="AAPL.US",
        bars=bars,
        previous_day={"high": 101.0, "low": 98.0, "close": 100.0},
        data_start="2025-08-20",
        data_end="2025-08-20",
        generated_at="2025-08-21T00:00:00Z",
        producer_commit="test-commit",
    )

    assert (root / "bars/aapl.us.parquet").is_file()
    assert (root / "manifest.json").is_file()


def test_fetch_and_write_artifact_requests_regular_session_and_previous_day(
    tmp_path: Path,
) -> None:
    class Response:
        def __init__(self, bars):
            self.bars = bars

        def __getitem__(self, symbol):
            return self.bars

    class Client:
        def __init__(self):
            self.requests = []

        def get_stock_bars(self, request):
            self.requests.append(request)
            if request.timeframe.unit == "Day":
                return Response([_bar("2025-08-19T04:00:00+00:00", 99)])
            return Response(
                [
                    _bar("2025-08-20T13:30:00+00:00", 101),
                    _bar("2025-08-20T20:00:00+00:00", 102),
                ]
            )

    class Request:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    client = Client()
    root = fetch_and_write_artifact(
        client,
        symbol="AAPL",
        session_date=date(2025, 8, 20),
        output_root=tmp_path / "aapl-input",
        producer_commit="test-commit",
        request_factory=Request,
        minute_timeframe=SimpleNamespace(unit="Minute"),
        daily_timeframe=SimpleNamespace(unit="Day"),
        require_complete=False,
    )

    assert root.joinpath("manifest.json").is_file()
    assert len(client.requests) == 2


def test_default_output_root_is_project_scoped_and_date_partitioned() -> None:
    root = default_output_root("aapl", date(2025, 8, 22))

    assert root.parts[-2:] == ("AAPL.US", "2025-08-22")
    assert root.as_posix().endswith(
        "data/trading-research-dashboard/rbreaker/alpaca/AAPL.US/2025-08-22"
    )
