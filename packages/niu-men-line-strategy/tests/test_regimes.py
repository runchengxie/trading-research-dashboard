import math

import pandas as pd
import pytest

from niu_men_line_strategy.regimes import simple_return_regime


def test_simple_return_regime_uses_current_close_and_lagged_close() -> None:
    data = pd.DataFrame({"close": [100.0, 102.0, 99.0, 105.0]})

    score = simple_return_regime(data, lookback=2)

    assert math.isnan(score.iloc[0])
    assert math.isnan(score.iloc[1])
    assert score.iloc[2] == pytest.approx(-0.01)
    assert score.iloc[3] == pytest.approx(105.0 / 102.0 - 1.0)
    assert score.name == "price_regime"


def test_simple_return_regime_rejects_non_positive_lookback() -> None:
    data = pd.DataFrame({"close": [100.0, 101.0]})

    with pytest.raises(ValueError, match="lookback must be positive"):
        simple_return_regime(data, lookback=0)


def test_simple_return_regime_requires_close_column() -> None:
    data = pd.DataFrame({"price": [100.0, 101.0]})

    with pytest.raises(ValueError, match="close"):
        simple_return_regime(data)
