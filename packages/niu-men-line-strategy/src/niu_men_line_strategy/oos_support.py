"""Shared point-in-time helpers for the OOS experiment entry points."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Literal

import pandas as pd


def dates(
    values: pd.Series,
    *,
    errors: Literal["raise", "coerce"] = "coerce",
) -> pd.Series:
    return pd.to_datetime(values.astype("string"), format="%Y%m%d", errors=errors)


def resolve_research_commit(explicit: str | None, *, repo_root: Path) -> str | None:
    if explicit is not None:
        value = explicit.strip()
        return value or None
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def parse_reset_bars_neighborhood(raw: str) -> tuple[int, ...]:
    text = raw.strip()
    if not text:
        return ()
    try:
        values = [int(item.strip()) for item in text.split(",")]
    except ValueError as exc:
        raise ValueError("reset bars neighborhood must contain integers") from exc
    if any(value <= 0 for value in values):
        raise ValueError("reset bars neighborhood values must be positive")
    return tuple(sorted(set(values)))


def requested_symbols(universe: pd.DataFrame) -> list[str]:
    return sorted(
        universe["symbol"].dropna().astype("string").dropna().astype(str).unique().tolist()
    )


def attach_pit_eligibility(data: pd.DataFrame, snapshots: pd.DataFrame) -> pd.Series:
    left = pd.DataFrame({"date": data.index})
    selected = (
        pd.merge_asof(
            left,
            snapshots[["trade_date", "selected"]].rename(columns={"trade_date": "snapshot_date"}),
            left_on="date",
            right_on="snapshot_date",
            direction="backward",
            allow_exact_matches=False,
        )["selected"]
        .fillna(0)
        .eq(1)
    )
    return pd.Series(selected.to_numpy(), index=data.index)


def attach_membership(data: pd.DataFrame, memberships: pd.DataFrame) -> pd.DataFrame:
    left = pd.DataFrame({"date": data.index})
    matched = pd.merge_asof(
        left,
        memberships[["effective_date", "end_date", "mapped_industry_code"]].sort_values(
            "effective_date"
        ),
        left_on="date",
        right_on="effective_date",
        direction="backward",
    )
    active = matched["end_date"].isna() | (matched["date"] <= matched["end_date"])
    result = data.copy()
    result["industry_code"] = matched["mapped_industry_code"].where(active).to_numpy()
    return result


def join_context(data: pd.DataFrame, context: pd.DataFrame) -> pd.DataFrame:
    left = data.reset_index(names="date")
    left["industry_code"] = left["industry_code"].astype("string")
    right = context.reset_index()
    result = left.merge(
        right,
        left_on=["date", "industry_code"],
        right_on=["trade_date", "industry_code"],
        how="left",
    )
    return result.drop(columns=["trade_date"], errors="ignore").set_index("date").sort_index()
