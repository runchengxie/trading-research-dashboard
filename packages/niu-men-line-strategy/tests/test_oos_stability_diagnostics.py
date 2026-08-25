import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from niu_men_line_strategy.signals import StrategyConfig


def _load_runner():
    path = Path(__file__).resolve().parents[1] / "scripts" / "run_industry_context_oos.py"
    spec = importlib.util.spec_from_file_location("run_industry_context_oos", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


oos = _load_runner()


def test_parse_reset_bars_neighborhood_normalizes_positive_unique_values() -> None:
    assert oos._parse_reset_bars_neighborhood("3,5,7,3") == (3, 5, 7)
    assert oos._parse_reset_bars_neighborhood("") == ()


@pytest.mark.parametrize("raw", ["0", "-1", "3,nope"])
def test_parse_reset_bars_neighborhood_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(ValueError, match="reset bars"):
        oos._parse_reset_bars_neighborhood(raw)


def test_reset_neighborhood_adds_variants_without_replacing_baseline() -> None:
    variants = oos._strategy_variants((3, 5, 7))

    assert variants["nml_baseline"] == StrategyConfig()
    assert variants["nml_baseline"].reset_bars == 5
    assert variants["nml_reset_3"].reset_bars == 3
    assert variants["nml_reset_7"].reset_bars == 7
    assert "nml_reset_5" not in variants


def test_default_variant_set_stays_unchanged() -> None:
    assert list(oos._strategy_variants()) == [
        "nml_baseline",
        "nml_no_price_volume_filters",
        "simple_20_day_breakout",
        "nml_simple_trend_gate",
        "nml_sector_retreat",
    ]


def test_requested_symbols_come_from_full_pit_universe() -> None:
    universe = pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000002.SZ", "000001.SZ", pd.NA],
        }
    )

    assert oos._requested_symbols(universe) == ["000001.SZ", "000002.SZ"]


def test_skip_result_preserves_available_stage_counts() -> None:
    result = oos._skip_result(
        "000001.SZ",
        "no_pit_eligible_bars",
        raw_bars=1200,
        mapped_industry_bars=1100,
        pit_eligible_bars=0,
    )

    assert result == {
        "symbol": "000001.SZ",
        "status": "skipped",
        "skip_reason": "no_pit_eligible_bars",
        "raw_bars": 1200,
        "mapped_industry_bars": 1100,
        "pit_eligible_bars": 0,
    }
