"""Dashboard instrument and parameter configuration."""

from __future__ import annotations

from typing import Final

STOCK_CONFIG: Final = {
    "sz300246": {
        "name": "宝莱特",
        "instrument_type": "stock",
    },
    "AAPL.US": {
        "name": "Apple",
        "instrument_type": "stock",
        "market": "US",
    },
    "MSFT.US": {
        "name": "Microsoft",
        "instrument_type": "stock",
        "market": "US",
    },
    "NVDA.US": {
        "name": "NVIDIA",
        "instrument_type": "stock",
        "market": "US",
    },
    "TSLA.US": {
        "name": "Tesla",
        "instrument_type": "stock",
        "market": "US",
    },
}

USAGE_DICT: Final = {
    "自动交易风格": "根据历史波动率、趋势强度和价格位置自动确定的交易策略风格",
    "最新收盘价": "T+0交易的核心中轴，判断当日强弱的分水岭。",
    "20日ATR (日振幅)": "衡量股票的日均波动空间。用于设定VWAP_DEV触发阈值，以及预估日内盈利/止损范围。",
    "聚类支撑位": "通过K-means聚类算法计算出的关键支撑位",
    "聚类阻力位": "通过K-means聚类算法计算出的关键阻力位",
    "最近关键价格": "距离当前价格最近的聚类中心，可能是重要的反转或加速点",
    "关键支撑位 (昨低)": "日内价格回调至此区域若出现企稳迹象，是潜在的做多T+0买点。",
    "关键阻力位 (昨高)": "日内价格上涨至此区域若出现滞涨迹象，是潜在的做空T+0卖点。",
    "上一日VWAP": "重要的多空参考线。今日价格在其上方运行偏强，下方运行偏弱。也是均值回归策略的核心。",
    "收盘相对VWAP偏离": "衡量收盘价的乖离程度。绝对值越大，次日开盘均值回归的概率越高。",
    "VWAP_DEV触发阈值": "当实时价与当日VWAP的绝对差值超过此阈值时，触发均值回归交易信号。",
    "ORB突破上轨": "宝莱特专用，开盘后若价格放量突破此价位，执行追多操作。",
    "ORB突破下轨": "宝莱特专用，开盘后若价格放量跌穿此价位，执行追空操作。",
}

USAGE_DICT_MANUAL: Final = {
    "盘口不平衡": "做多时主动买量与主动卖量比值至少为 1.8，做空时不高于 0.55。需要 Level-2 行情支持。",
    "加速信号": "最近 3 根 1 分钟 K 线实体占全长 65% 以上且方向一致，与 VWAP_DEV 信号叠加确认，用于追单。",
    "滚动仓强制归零": "滚动仓必须在所属市场收盘前的风控时点平仓，防止隔夜风险。",
    "最大日损": "滚动仓亏损触及此线后立即止损，并停止当天交易。",
}
