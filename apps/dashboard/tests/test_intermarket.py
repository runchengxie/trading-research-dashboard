import pandas as pd

from trading_research.dashboard.intermarket import build_intermarket_observations


def daily_stock(code, closes, *, final_high_break=False, final_low_break=False):
    dates = pd.date_range("2026-07-30", periods=len(closes), freq="D")
    rows = []
    for index, (date, close) in enumerate(zip(dates, closes, strict=True)):
        high = close + 0.5
        low = close - 0.5
        if index == len(closes) - 1 and final_high_break:
            high = max(closes[:-1]) + 5.0
        if index == len(closes) - 1 and final_low_break:
            low = min(closes[:-1]) - 5.0
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "open": close,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000,
            }
        )
    return {"code": code, "daily": rows}


def test_intermarket_selects_peer_and_detects_extreme_divergence():
    base = [100 + index for index in range(20)] + [118.5]
    peer = [50 + index * 0.5 for index in range(20)] + [59.25]
    left = daily_stock("LEFT.US", base, final_high_break=True)
    right = daily_stock("RIGHT.US", peer, final_high_break=False)
    result = build_intermarket_observations([left, right])
    observation = result["LEFT.US"][0]
    assert observation["peer"] == "RIGHT.US"
    assert observation["correlation20"] > 0.99
    assert observation["relativeExtremeDivergence"] is True
    assert observation["extremeConfirmation"] == "diverged"


def test_inverse_peer_confirms_high_with_peer_low():
    left_closes = [100 + index for index in range(20)] + [118.5]
    right_closes = [80 - index * 0.5 for index in range(20)] + [70.75]
    left = daily_stock("EQUITY.US", left_closes, final_high_break=True)
    right = daily_stock("DXY.US", right_closes, final_low_break=True)
    observation = build_intermarket_observations([left, right])["EQUITY.US"][0]
    assert observation["correlation20"] < -0.9
    assert observation["extremeConfirmation"] == "confirmed"
    assert observation["relativeExtremeDivergence"] is False


def test_intermarket_requires_twenty_return_observations():
    short = daily_stock("SHORT.US", [100 + index for index in range(10)])
    peer = daily_stock("PEER.US", [50 + index for index in range(10)])
    assert build_intermarket_observations([short, peer])["SHORT.US"] == []
