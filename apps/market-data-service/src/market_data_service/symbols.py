from __future__ import annotations

import re

_SYMBOL = re.compile(r"^(?P<market>sh|sz|bj)[.?](?P<code>\d{6})$|^(?P<plain>sh|sz|bj)\d{6}$", re.I)


def normalize_symbol(raw: str) -> str:
    value = raw.strip().lower()
    match = _SYMBOL.fullmatch(value)
    if not match:
        raise ValueError(f"invalid symbol: {raw!r}")
    if match.group("plain"):
        return value
    return f"{match.group('market')}{match.group('code')}"
