import pandas as pd
import pytest

from niu_men_line_strategy.signals import StrategyConfig, build_signals


def _breakout_sample() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": [9.4, 9.5, 9.7, 9.6, 9.8, 10.9],
            "high": [10.0, 10.0, 10.0, 10.0, 11.0, 11.2],
            "low": [9.0, 9.2, 9.3, 9.4, 9.7, 10.5],
            "close": [9.5, 9.8, 9.6, 9.7, 10.8, 10.7],
            "volume": [100.0, 100.0, 100.0, 100.0, 100.0, 100.0],
        }
    )


def test_close_breakout_requires_prior_reset_bars() -> None:
    config = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        reset_bars=2,
        enable_red_three_soldiers=False,
        enable_long_upper_shadow=False,
    )
    signals = build_signals(_breakout_sample(), config)

    assert bool(signals.loc[4, "raw_entry_signal"])
    assert bool(signals.loc[4, "armed"])
    assert bool(signals.loc[4, "entry_signal"])


def test_long_upper_shadow_filter_blocks_candidate() -> None:
    data = _breakout_sample()
    data.loc[4, "open"] = 10.4
    data.loc[4, "close"] = 11.1
    data.loc[4, "high"] = 12.0
    data.loc[4, "low"] = 10.3
    data.loc[4, "volume"] = 250.0

    config = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        reset_bars=2,
        enable_red_three_soldiers=False,
        enable_long_upper_shadow=True,
        upper_shadow_fraction=0.4,
        volume_spike_ratio=1.5,
        volume_lookback=2,
    )
    signals = build_signals(data, config)

    assert bool(signals.loc[4, "raw_entry_signal"])
    assert bool(signals.loc[4, "filter_long_upper_shadow"])
    assert not bool(signals.loc[4, "entry_signal"])


def test_red_three_soldiers_filter_uses_three_prior_bars() -> None:
    data = pd.DataFrame(
        {
            "open": [8.5, 8.8, 9.1, 9.4, 9.7],
            "high": [9.0, 9.2, 9.5, 9.8, 11.0],
            "low": [8.0, 8.7, 9.0, 9.3, 9.6],
            "close": [8.8, 9.1, 9.4, 9.7, 10.8],
            "volume": [100.0] * 5,
        }
    )
    config = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        reset_bars=1,
        enable_red_three_soldiers=True,
        soldier_body_atr_fraction=0.3,
        enable_long_upper_shadow=False,
    )
    signals = build_signals(data, config)

    assert bool(signals.loc[4, "raw_entry_signal"])
    assert bool(signals.loc[4, "filter_red_three_soldiers"])
    assert not bool(signals.loc[4, "entry_signal"])


def test_sector_retreat_filter_is_quantified_when_context_exists() -> None:
    data = _breakout_sample()
    data["sector_close"] = [12.0, 11.5, 11.0, 10.5, 10.0, 9.5]
    config = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        reset_bars=2,
        enable_red_three_soldiers=False,
        enable_long_upper_shadow=False,
        enable_sector_retreat=True,
        sector_fast_period=2,
        sector_slow_period=3,
    )
    signals = build_signals(data, config)

    assert bool(signals.loc[4, "filter_sector_retreat"])
    assert not bool(signals.loc[4, "entry_signal"])


def test_market_volume_divergence_filter_is_quantified() -> None:
    data = _breakout_sample()
    data.loc[4, "volume"] = 200.0
    data["market_volume"] = [100.0, 100.0, 100.0, 100.0, 70.0, 100.0]
    config = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        reset_bars=2,
        enable_red_three_soldiers=False,
        enable_long_upper_shadow=False,
        enable_market_volume_divergence=True,
        market_volume_lookback=2,
        market_dry_ratio=0.8,
        asset_spike_ratio=1.5,
    )
    signals = build_signals(data, config)

    assert bool(signals.loc[4, "filter_market_volume_divergence"])
    assert not bool(signals.loc[4, "entry_signal"])


def test_context_filter_requires_context_column() -> None:
    config = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        enable_sector_retreat=True,
    )
    with pytest.raises(ValueError, match="sector_close"):
        build_signals(_breakout_sample(), config)


def test_regime_gate_blocks_non_positive_context() -> None:
    data = _breakout_sample()
    data["macro_regime"] = 1.0
    data["industry_regime"] = 1.0
    data.loc[4, "industry_regime"] = 0.0

    config = StrategyConfig(
        high_lookback=2,
        atr_period=2,
        smx_period=2,
        reset_bars=2,
        enable_red_three_soldiers=False,
        enable_long_upper_shadow=False,
        enable_regime_gate=True,
        minimum_regime_score=0.0,
    )
    signals = build_signals(data, config)

    assert bool(signals.loc[4, "filter_regime"])
    assert not bool(signals.loc[4, "entry_signal"])
