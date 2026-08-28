"""Tushare provider retry and quota classification helpers."""

from __future__ import annotations

import time
from collections.abc import Callable


def _err_text(error: Exception) -> str:
    return (str(error) or error.__class__.__name__).lower()


def _is_quota_error(error: Exception) -> bool:
    message = _err_text(error)
    return any(
        marker in message
        for marker in (
            "频率超限",
            "访问频率已超速",
            "超速",
            "冷却",
            "rate limit",
            "too many requests",
            "官方限速",
            "增加等待几秒重试",
            "请求过于频繁",
            "quota",
        )
    )


def _is_daily_quota_exhausted(error: Exception) -> bool:
    message = _err_text(error)
    return any(
        marker in message
        for marker in (
            "今日请求次数已达上限",
            "今日访问次数已达上限",
            "今日请求次数已用完",
            "单日请求次数已达上限",
            "单日总容量已达上限",
            "每日请求次数已耗尽",
            "每日请求次数已用完",
            "daily request limit exceeded",
            "daily request capacity exhausted",
            "daily quota exhausted",
        )
    )


def _is_retryable_provider_error(error: Exception) -> bool:
    if isinstance(error, OSError) and _err_text(error).strip().upper() == "ERROR.":
        return True
    if _is_daily_quota_exhausted(error):
        return False
    if _is_quota_error(error):
        return True
    message = _err_text(error)
    return any(
        marker in message
        for marker in (
            "timed out",
            "timeout",
            "proxyerror",
            "proxy error",
            "max retries exceeded",
            "response ended prematurely",
            "connection aborted",
            "connection reset",
            "remote disconnected",
            "remotedisconnected",
            "remote end closed",
            "temporarily unavailable",
            "temporary failure",
            "502",
            "503",
            "504",
        )
    )


def _call_tushare_api(
    call: Callable[[], object],
    *,
    attempts: int = 4,
    retry_sleep: int = 3,
    retry_max: int = 30,
) -> object:
    """Call Tushare with bounded retries for transient provider failures."""
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except Exception as exc:
            if _is_daily_quota_exhausted(exc) or _is_quota_error(exc):
                raise
            if attempt >= attempts or not _is_retryable_provider_error(exc):
                raise
            delay = min(retry_sleep * (2 ** (attempt - 1)), retry_max)
            if delay > 0:
                time.sleep(delay)
    raise RuntimeError("unreachable Tushare retry state")


def _redact(error: Exception) -> str:
    """Return a short error description without exposing credentials."""
    return f"{type(error).__name__}: {str(error)[:200]}"
