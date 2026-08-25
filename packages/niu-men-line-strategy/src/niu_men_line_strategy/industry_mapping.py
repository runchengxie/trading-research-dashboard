"""Auditable SW2021 L3 to listed equity-fund proxy mapping rules.

The rules intentionally map only when the fund benchmark contains a named
industry or theme. Broad market, style, bond, overseas, and mixed benchmarks
are excluded. A mapping is a research proxy, not a claim that an ETF is a
perfect representation of an SW2021 industry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IndustryProxyRule:
    code: str
    name_cn: str
    benchmark_pattern: str
    sw_pattern: str
    rationale: str


# These exclusions prevent strings such as "银行活期存款" and broad index
# names from being treated as industry evidence.
BROAD_BENCHMARK_PATTERN = (
    r"沪深|中证(?:A股|A\d{2,4}|\d{2,4})(?:\D|$)|上证|深证|创业板|科创板|"
    r"红利|价值|成长|低波|质量|自由现金流|央企|国企|港股通|恒生|海外|全球|"
    r"纳斯达克|标普|MSCI|ESG|基本面|股息|高股息|债|存款|可转债|全债|综合债|"
    r"交易所|香港|港股|中小板|中小企业|偏股型基金"
)


# The order is deliberate. More specific themes are considered before broad
# names, for example automotive before generic electronics and utilities
# before generic equipment.
PROXY_RULES: tuple[IndustryProxyRule, ...] = (
    IndustryProxyRule("bank", "银行", r"中证银行(?:指数)?(?!AH)|银行指数", r"银行|农商行|城商行", "direct bank index"),
    IndustryProxyRule("broker", "证券", r"证券公司|证券行业|证券龙头", r"证券", "direct securities index"),
    IndustryProxyRule("medicine", "医药医疗", r"医药|医疗|制药|生物医药|疫苗|中药", r"医药|医疗|中药|血液制品|疫苗|诊断|医院|医美|保健品|原料药|药店|生物制品", "direct healthcare index"),
    IndustryProxyRule("semiconductor", "半导体芯片", r"半导体|芯片|集成电路", r"半导体|芯片|集成电路|分立器件", "direct semiconductor index"),
    IndustryProxyRule("automobile", "汽车", r"汽车", r"汽车|摩托车|商用载客车|商用载货车|乘用车|发动机|轮胎|车身附件", "direct automotive index"),
    IndustryProxyRule("military", "国防军工", r"军工|国防|航天航空|航空航天", r"军工|兵装|航天|航空装备|航天装备|航海装备|卫星", "direct defense and aerospace index"),
    IndustryProxyRule("electronics", "电子", r"电子(?:指数|50)|消费电子", r"电子|面板|元件|光学|LED|电路板", "direct electronics index"),
    IndustryProxyRule("communication", "通信", r"通信", r"通信|电信", "direct communication index"),
    IndustryProxyRule("computer", "计算机软件", r"计算机|软件|人工智能|云计算|大数据", r"计算机|软件|IT服务|金融信息|垂直应用", "direct software and computing index"),
    IndustryProxyRule("new_energy", "新能源", r"新能源|光伏|电池", r"新能源|光伏|电池|燃料电池|逆变器", "direct new-energy index"),
    IndustryProxyRule("nonferrous", "有色金属", r"有色|稀有金属|黄金", r"有色|铜|铝|锂|钴|镍|锌|钨|钼|稀土|黄金|白银|小金属|金属新材料|钛白粉|磁性材料", "direct nonferrous or gold index"),
    IndustryProxyRule("chemical", "化工", r"化工|化学|石化", r"化工|化学|树脂|硅|氨纶|粘胶|涤纶|锦纶|橡胶|塑料|氟|纯碱|氯碱|化肥|磷肥|钾肥|氮肥|石化|焦炭|炼油|涂料|炭黑|胶黏剂|膜材料|无机盐|聚氨酯", "direct chemical index"),
    IndustryProxyRule("coal", "煤炭", r"煤炭", r"煤|焦煤|动力煤", "direct coal index"),
    IndustryProxyRule("steel", "钢铁", r"钢铁|黑色金属", r"钢铁|铁矿|冶钢|长材|钢材", "direct steel index"),
    IndustryProxyRule("food_beverage", "食品饮料", r"食品|饮料|白酒", r"食品|饮料|白酒|乳品|酒类|零食|肉制品|餐饮|调味|烘焙|熟食|粮油|果蔬", "direct food and beverage index"),
    IndustryProxyRule("home_appliance", "家电家居", r"家电|家居", r"家电|家居|冰洗|空调|厨|卫浴|照明|彩电", "direct home-appliance index"),
    IndustryProxyRule("real_estate", "房地产", r"房地产|地产", r"地产|房地产|住宅开发|物业|房产|租赁", "direct real-estate index"),
    IndustryProxyRule("media", "传媒娱乐", r"传媒|游戏|动漫|影视|文娱", r"传媒|游戏|动漫|影视|媒体|出版|院线|广告", "direct media and entertainment index"),
    IndustryProxyRule("environment", "环保", r"环保|环境治理", r"环保|环境|固废|大气|水务", "direct environment index"),
    IndustryProxyRule("machinery", "机械设备", r"机械|机器人|机床", r"机械|设备|机器人|仪器|仪表|自动化|机床|工控|检测|电机|农用机械", "direct machinery index"),
    IndustryProxyRule("infrastructure", "基建建材", r"基建|建筑材料", r"基建|建筑|建材|工程|装修|水泥|玻璃|耐火|防水|钢结构|板材|管材|玻纤", "direct infrastructure or building-material index"),
    IndustryProxyRule("livestock", "畜牧养殖", r"畜牧|养殖", r"畜牧|养殖|生猪|肉鸡|畜禽|动物保健|饲料", "direct livestock index"),
    IndustryProxyRule("agriculture", "农业", r"农业|农牧|农产品|粮食", r"农业|农牧|农产品|种植|粮食|种子|农药|林业|果蔬|水产|捕捞|食用菌|复合肥", "direct agriculture index"),
    IndustryProxyRule("tourism", "旅游酒店", r"旅游", r"旅游|酒店|景区|会展", "direct tourism index"),
    IndustryProxyRule("logistics", "物流", r"物流", r"物流|快递|供应链|仓储", "direct logistics index"),
    IndustryProxyRule("transport", "交通运输", r"运输|交通", r"运输|港口|机场|公路|铁路|航运|公交|轨交", "direct transport index"),
    IndustryProxyRule("utilities", "公用事业", r"电力|公用事业|绿色电力", r"电力|发电|电网|燃气|热力|电能综合服务", "direct utilities index"),
    IndustryProxyRule("petroleum", "石油天然气", r"油气|石油", r"油气|石油|油田服务", "direct oil and gas index"),
)

_COMPILED_PROXY_RULES = tuple(
    (rule, re.compile(rule.benchmark_pattern), re.compile(rule.sw_pattern))
    for rule in PROXY_RULES
)
_BROAD_BENCHMARK_RE = re.compile(BROAD_BENCHMARK_PATTERN)


def classify_benchmark(benchmark: object, name: object = "") -> IndustryProxyRule | None:
    """Return the first direct proxy rule supported by a benchmark string."""

    text = "" if benchmark is None else str(benchmark)
    fund_name = "" if name is None else str(name)
    if not text or _BROAD_BENCHMARK_RE.search(text):
        return None
    # Only listed equity index funds/ETFs are used as proxies. ETF联接 and
    # structured share classes do not represent a directly tradable ETF.
    if not re.search(r"ETF|LOF", fund_name, flags=re.IGNORECASE):
        return None
    if re.search(r"联接|分级|债|货币|混合", fund_name):
        return None
    for rule, benchmark_re, _ in _COMPILED_PROXY_RULES:
        if benchmark_re.search(text):
            return rule
    return None


def classify_sw_industry(name: object) -> tuple[IndustryProxyRule | None, tuple[str, ...]]:
    """Classify an SW2021 L3 name and return all matching rule codes."""

    text = "" if name is None else str(name)
    matches = tuple(rule.code for rule, _, sw_re in _COMPILED_PROXY_RULES if sw_re.search(text))
    selected = next((rule for rule, _, sw_re in _COMPILED_PROXY_RULES if sw_re.search(text)), None)
    return selected, matches


def sw_mapping_confidence(name: object, matches: tuple[str, ...]) -> str:
    """Assign a conservative confidence label for the name-to-proxy link."""

    text = "" if name is None else str(name)
    if not matches:
        return "unmapped"
    if text.startswith("其他") or "综合" in text or text.endswith("Ⅲ") or len(matches) > 1:
        return "medium"
    return "high"


__all__ = [
    "BROAD_BENCHMARK_PATTERN",
    "PROXY_RULES",
    "IndustryProxyRule",
    "classify_benchmark",
    "classify_sw_industry",
    "sw_mapping_confidence",
]
