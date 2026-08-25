from niu_men_line_strategy.industry_mapping import (
    classify_benchmark,
    classify_sw_industry,
    sw_mapping_confidence,
)


def test_benchmark_requires_direct_named_equity_fund_proxy() -> None:
    assert classify_benchmark("沪深300指数收益率×100%", "沪深300ETF") is None
    assert classify_benchmark(
        "活期存款利率(税后)×5%+中证银行指数×95%", "银行指数LOF-A"
    ) is None
    assert classify_benchmark("中证银行指数收益率×100%", "中证银行ETF").code == "bank"


def test_sw_specific_rules_take_priority_over_generic_matches() -> None:
    selected, matches = classify_sw_industry("军工电子Ⅲ")
    assert selected is not None
    assert selected.code == "military"
    assert matches == ("military", "electronics")


def test_sw_mapping_confidence_exposes_broad_and_ambiguous_names() -> None:
    selected, matches = classify_sw_industry("其他通信设备")
    assert selected is not None
    assert sw_mapping_confidence("其他通信设备", matches) == "medium"
    assert classify_sw_industry("综合Ⅲ")[0] is None
