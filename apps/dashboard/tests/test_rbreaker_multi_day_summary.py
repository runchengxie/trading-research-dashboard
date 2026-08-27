from pathlib import Path

from trading_research.scripts.summarize_rbreaker_snapshots import summarize_snapshots


def _snapshot(data_date: str, trades: int, returns: float, drawdown: float) -> dict:
    return {
        "dataDate": data_date,
        "variants": [{"metrics": {
            "tradeCountMedian": trades,
            "annualizedReturnMedian": returns,
            "maxDrawdownMedian": drawdown,
            "winRateMedian": 0.5,
        }}],
    }


def test_summarize_snapshots_aggregates_days_trades_and_compounded_return(
    tmp_path: Path,
) -> None:
    paths = []
    for index, values in enumerate(((2, 0.1, 1.0), (3, -0.05, 2.0)), start=1):
        path = tmp_path / f"snapshot-{index}.json"
        path.write_text(
            __import__("json").dumps(_snapshot(f"2025-08-0{index}", *values)),
            encoding="utf-8",
        )
        paths.append(path)

    result = summarize_snapshots(paths)

    assert result["days"] == 2
    assert result["daysWithTrades"] == 2
    assert result["totalTrades"] == 5
    assert result["compoundedReturn"] == 0.045
    assert result["maxDrawdown"] == 2.0
