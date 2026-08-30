from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import fsum
from typing import Any

from research_core import validate_conditional_research, validate_contextual_snapshot

_DIMENSION_NAMES = (
    "instrument",
    "market",
    "session",
    "dayArchetype",
    "eventType",
    "referenceLevelKind",
    "strategyId",
    "variantId",
)


def _text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _date(value: Any) -> str | None:
    text = _text(value)
    if text is None:
        return None
    try:
        year, month, day = (int(part) for part in text[:10].split("-"))
    except (ValueError, TypeError):
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31 and year >= 1):
        return None
    return f"{year:04d}-{month:02d}-{day:02d}"


def _snapshot_date(snapshot: Mapping[str, Any]) -> str | None:
    return _date(snapshot.get("dataDate"))


def _context_index(snapshot: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    contexts = snapshot.get("contexts")
    if not isinstance(contexts, Sequence) or isinstance(contexts, (str, bytes)):
        return {}
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    snapshot_date = _snapshot_date(snapshot)
    if snapshot_date is None:
        return result
    for context in contexts:
        if not isinstance(context, Mapping):
            continue
        instrument = context.get("instrument")
        code = instrument.get("code") if isinstance(instrument, Mapping) else None
        if code:
            result[(str(code), snapshot_date)] = context
    return result


def _dimensions(
    *,
    instrument: Any = None,
    market: Any = None,
    session: Any = None,
    day_archetype: Any = None,
    event_type: Any = None,
    reference_level_kind: Any = None,
    strategy_id: Any = None,
    variant_id: Any = None,
) -> dict[str, str | None]:
    values = {
        "instrument": _text(instrument),
        "market": _text(market),
        "session": _text(session),
        "dayArchetype": _text(day_archetype),
        "eventType": _text(event_type),
        "referenceLevelKind": _text(reference_level_kind),
        "strategyId": _text(strategy_id),
        "variantId": _text(variant_id),
    }
    return {name: values[name] for name in _DIMENSION_NAMES}


def _dimension_key(dimensions: Mapping[str, str | None]) -> tuple[str | None, ...]:
    return tuple(dimensions.get(name) for name in _DIMENSION_NAMES)


def _empty_accumulator(dimensions: dict[str, str | None]) -> dict[str, Any]:
    return {
        "dimensions": dimensions,
        "returns": [],
        "mfe": [],
        "mae": [],
        "wins": [],
        "dates": set(),
        "instruments": set(),
    }


def _add_sample(
    accumulator: dict[str, Any],
    *,
    data_date: str | None,
    instrument: str | None,
    return_value: Any = None,
    mfe: Any = None,
    mae: Any = None,
    win: Any = None,
) -> None:
    accumulator["returns"].append(_number(return_value))
    accumulator["mfe"].append(_number(mfe))
    accumulator["mae"].append(_number(mae))
    return_number = _number(return_value)
    if isinstance(win, bool):
        accumulator["wins"].append(win)
    elif return_number is not None:
        accumulator["wins"].append(return_number > 0)
    if data_date is not None:
        accumulator["dates"].add(data_date)
    if instrument:
        accumulator["instruments"].add(instrument)


def _mean(values: list[float | None]) -> float | None:
    present = [value for value in values if value is not None]
    return None if not present else fsum(present) / len(present)


def _metrics(accumulator: Mapping[str, Any]) -> dict[str, Any]:
    returns = accumulator["returns"]
    wins = accumulator["wins"]
    sample_count = len(returns)
    return {
        "sampleCount": sample_count,
        "winRate": None if not wins else sum(wins) / len(wins),
        "expectancy": _mean(returns),
        "meanReturn": _mean(returns),
        "meanMfe": _mean(accumulator["mfe"]),
        "meanMae": _mean(accumulator["mae"]),
        "dateCount": len(accumulator["dates"]),
        "instrumentCount": len(accumulator["instruments"]),
    }


def _setup_dimensions(
    event: Mapping[str, Any],
    context: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    event_context = event.get("context")
    if not isinstance(event_context, Mapping):
        event_context = {}
    if not event_context and context is not None:
        event_context = context
    instrument = event.get("instrument")
    market = context.get("market") if context is not None else None
    archetype = event_context.get("dayArchetype")
    if isinstance(archetype, Mapping):
        archetype = archetype.get("id")
    elif archetype is None and context is not None:
        day_archetype = context.get("dayArchetype")
        archetype = day_archetype.get("id") if isinstance(day_archetype, Mapping) else None
    reference = event.get("referenceLevel")
    reference_kind = reference.get("kind") if isinstance(reference, Mapping) else None
    return _dimensions(
        instrument=instrument,
        market=market,
        session=event.get("session"),
        day_archetype=archetype,
        event_type=event.get("eventType"),
        reference_level_kind=reference_kind,
    )


def _strategy_dimensions(
    outcome: Mapping[str, Any],
    context: Mapping[str, Any] | None,
) -> dict[str, str | None]:
    archetype = outcome.get("dayArchetype")
    if archetype is None and context is not None:
        day_archetype = context.get("dayArchetype")
        archetype = day_archetype.get("id") if isinstance(day_archetype, Mapping) else None
    market = outcome.get("market")
    if market is None and context is not None:
        market = context.get("market")
    return _dimensions(
        instrument=outcome.get("instrument"),
        market=market,
        session=outcome.get("session"),
        day_archetype=archetype,
        event_type=outcome.get("eventType"),
        reference_level_kind=outcome.get("referenceLevelKind"),
        strategy_id=outcome.get("strategyId"),
        variant_id=outcome.get("variantId"),
    )


def aggregate_contextual_history(
    snapshots: Sequence[Mapping[str, Any]],
    *,
    strategy_outcomes: Sequence[Mapping[str, Any]] | None = None,
    generated_at: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    accumulators: dict[tuple[str | None, ...], dict[str, Any]] = {}
    valid_snapshots: list[Mapping[str, Any]] = []
    context_indexes: list[dict[tuple[str, str], Mapping[str, Any]]] = []

    for index, snapshot in enumerate(snapshots):
        if not isinstance(snapshot, Mapping):
            warnings.append(f"snapshot[{index}]: root must be an object")
            continue
        try:
            validate_contextual_snapshot(snapshot)
        except (TypeError, ValueError) as exc:
            warnings.append(f"snapshot[{index}]: {exc}")
            continue
        if _snapshot_date(snapshot) is None:
            warnings.append(f"snapshot[{index}]: dataDate is invalid")
            continue
        valid_snapshots.append(snapshot)
        context_indexes.append(_context_index(snapshot))

        events = snapshot.get("setupEvents", [])
        for event in events:
            if not isinstance(event, Mapping):
                continue
            instrument = _text(event.get("instrument"))
            date = _date(event.get("dataDate"))
            context = context_indexes[-1].get((instrument or "", date or ""))
            dimensions = _setup_dimensions(event, context)
            key = _dimension_key(dimensions)
            accumulator = accumulators.setdefault(key, _empty_accumulator(dimensions))
            outcome = event.get("outcome")
            outcome = outcome if isinstance(outcome, Mapping) else {}
            _add_sample(
                accumulator,
                data_date=date,
                instrument=instrument,
                return_value=outcome.get("return30m"),
                mfe=outcome.get("mfe30m"),
                mae=outcome.get("mae30m"),
            )

    accepted_strategy_samples = 0
    for index, outcome in enumerate(strategy_outcomes or ()):
        if not isinstance(outcome, Mapping):
            warnings.append(f"strategyOutcome[{index}]: root must be an object")
            continue
        strategy_id = _text(outcome.get("strategyId"))
        variant_id = _text(outcome.get("variantId"))
        instrument = _text(outcome.get("instrument"))
        date = _date(outcome.get("dataDate"))
        if not strategy_id or not variant_id or not instrument or not date:
            warnings.append(f"strategyOutcome[{index}]: strategyId, variantId, instrument and dataDate are required")
            continue
        context = next(
            (
                context_index.get((instrument, date))
                for context_index in context_indexes
                if (instrument, date) in context_index
            ),
            None,
        )
        dimensions = _strategy_dimensions(outcome, context)
        key = _dimension_key(dimensions)
        accumulator = accumulators.setdefault(key, _empty_accumulator(dimensions))
        _add_sample(
            accumulator,
            data_date=date,
            instrument=instrument,
            return_value=outcome.get("return"),
            mfe=outcome.get("mfe"),
            mae=outcome.get("mae"),
            win=outcome.get("win"),
        )
        accepted_strategy_samples += 1

    dates = sorted(
        date
        for snapshot in valid_snapshots
        if (date := _snapshot_date(snapshot)) is not None
    )
    generated_date = _date(generated_at) or (dates[-1] if dates else "1970-01-01")
    result = {
        "schemaVersion": "trading_research.conditional_research.v1",
        "generatedAt": generated_at,
        "dateRange": {
            "start": dates[0] if dates else generated_date,
            "end": dates[-1] if dates else generated_date,
        },
        "sourceSnapshots": len(valid_snapshots),
        "quality": {"status": "warning" if warnings else "pass", "warnings": warnings},
        "coverage": {
            "requestedSnapshots": len(snapshots),
            "evaluatedSnapshots": len(valid_snapshots),
            "skippedSnapshots": len(snapshots) - len(valid_snapshots),
            "setupSamples": sum(
                len(snapshot.get("setupEvents", []))
                for snapshot in valid_snapshots
                if isinstance(snapshot.get("setupEvents"), Sequence)
            ),
            "strategySamples": accepted_strategy_samples,
        },
        "groups": [
            {
                "dimensions": accumulator["dimensions"],
                "metrics": _metrics(accumulator),
            }
            for _, accumulator in sorted(
                accumulators.items(),
                key=lambda item: tuple(value or "" for value in item[0]),
            )
        ],
        "provenance": {
            "source": "contextual-history-summarizer",
            "definitionVersion": "conditional-research.v1",
        },
    }
    validate_conditional_research(result)
    return result
