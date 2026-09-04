import pytest

from trading_research.data.provider_policy import _call_tushare_api


def test_call_tushare_api_retries_transient_error(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = iter([TimeoutError("timed out"), "ok"])
    sleeps: list[int] = []
    monkeypatch.setattr("trading_research.data.provider_policy.time.sleep", sleeps.append)

    def call() -> str:
        value = next(attempts)
        if isinstance(value, Exception):
            raise value
        return value

    result = _call_tushare_api(call, retry_sleep=2)

    assert result == "ok"
    assert sleeps == [2]
