# -*- coding: utf-8 -*-
# 1. Ensure required libraries are installed
# pip install akshare pandas openpyxl scikit-learn

import argparse
import json
import os
import socket
from datetime import datetime

import akshare as ak
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans

from trading_research.data import market_compat as data_sources

# ==============================================================================
# 2. Parameters
# ==============================================================================
# 证券配置。A 股兼容 sh600199 格式，ETF 推荐使用 510050.SH，港股支持 00700.HK / hk00700。
# instrument_type 可选 stock / etf，旧配置未填写时仍按 stock 处理。
# market 可选 CN / HK / US；省略时从带市场后缀/前缀的代码推断，历史 A 股配置默认 CN。
# vwap_dev_k 为可选字段，用于覆盖自动推导值（迁移自 wu-t0-trading-assitant 的 STOCK_CONFIG）
STOCK_CONFIG = {
    "sz300246": {
        "name": "宝莱特",
        "instrument_type": "stock",
        # "vwap_dev_k": 0.4,  # 可选：覆盖由交易风格自动推导的 ATR 系数
    },
}

# ATR period
ATR_PERIOD = 20
# Number of clusters
N_CLUSTERS = 5
# Output directories
OUTPUT_ROOT = "out"

# 指标/参数的使用说明（同时供 Excel 导出与前端 data.json 复用）。
# 注意：这些说明此前在 main() 内定义，现上提到模块级以便 build_stock_payload 在循环中引用。
USAGE_DICT = {
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
    "VWAP_DEV触发阈值": "【核心】当'实时价 - 当日VWAP'的绝对值 > 此阈值时，触发均值回归交易信号。",
    "ORB突破上轨": "【宝莱特专用】开盘后若价格放量突破此价位，执行追多操作。",
    "ORB突破下轨": "【宝莱特专用】开盘后若价格放量跌穿此价位，执行追空操作（融券卖出）。",
}

USAGE_DICT_MANUAL = {
    "盘口不平衡": "【做多】3分钟内主动买量/主动卖量 >= 1.8；【做空】<= 0.55。需Level-2行情支持。",
    "加速信号": "最近3根1分钟K线实体占全长65%以上且同向，与VWAP_DEV信号叠加确认，用于追单。",
    "滚动仓强制归零": "铁律！无论盈亏，滚动仓必须在所属市场配置的收盘前风控时点平仓，防止隔夜风险。",
    "最大日损": "风控底线！滚动仓亏损触及此线，立即止损并停止当天交易。",
}


# ==============================================================================
# 3. Calculation functions
# ==============================================================================
def calculate_atr(df: pd.DataFrame, period: int) -> float:
    """Compute ATR over the given period"""
    df['h-l'] = df['high'] - df['low']
    df['h-pc'] = abs(df['high'] - df['close'].shift(1))
    df['l-pc'] = abs(df['low'] - df['close'].shift(1))
    df['tr'] = df[['h-l', 'h-pc', 'l-pc']].max(axis=1)
    df['atr'] = df['tr'].rolling(window=period).mean()
    return df['atr'].iloc[-1]


def calculate_vwap(df: pd.DataFrame) -> float:
    """Compute full-day VWAP"""
    if df['volume'].sum() == 0:
        return df['price'].mean()  # Fallback for no volume
    df['price_x_vol'] = df['price'] * df['volume']
    vwap = df['price_x_vol'].sum() / df['volume'].sum()
    return vwap


def get_opening_range(df: pd.DataFrame) -> tuple:
    """Get opening range (09:30-09:45)"""
    # 确保索引是DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        df = df.set_index('time')

    # 筛选09:30-09:45的时间段
    orb_df = df.between_time('09:30:00', '09:45:00')
    if orb_df.empty:
        return None, None
    orb_high = orb_df['price'].max()
    orb_low = orb_df['price'].min()
    return orb_high, orb_low


def calculate_support_resistance(df: pd.DataFrame, n_clusters: int = 5) -> tuple:
    """Compute support/resistance via K-means clusters"""
    # Use close prices
    prices = df['close'].values.reshape(-1, 1)

    # K-means clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=0, n_init=10).fit(prices)
    centers = kmeans.cluster_centers_.flatten()
    centers.sort()

    # Support and resistance
    support = centers[0]
    resistance = centers[-1]

    # Nearest key level to latest close
    latest_close = df['close'].iloc[-1]
    nearest_key_level = centers[np.argmin(np.abs(centers - latest_close))]

    return support, resistance, centers, nearest_key_level


def determine_trading_style(df: pd.DataFrame) -> str:
    """Determine trading style based on history"""
    # Volatility: ATR20 relative to price
    atr_20 = calculate_atr(df.copy(), 20)
    price = df['close'].iloc[-1]
    volatility = atr_20 / price

    # Trend strength: |MA5-MA20| relative to price
    ma5 = df['close'].rolling(window=5).mean().iloc[-1]
    ma20 = df['close'].rolling(window=20).mean().iloc[-1]
    trend_strength = abs(ma5 - ma20) / price

    # Price position within recent range
    high_20 = df['high'].rolling(window=20).max().iloc[-1]
    low_20 = df['low'].rolling(window=20).min().iloc[-1]
    price_position = (price - low_20) / (high_20 - low_20)

    # Decide trading style
    if volatility > 0.03:  # high volatility
        if trend_strength > 0.05:  # strong trend
            style = "Trend-following + Breakout"
        else:
            if 0.3 < price_position < 0.7:
                style = "Mean reversion + VWAP"
            else:
                style = "Breakout + Momentum"
    else:  # low volatility
        if trend_strength > 0.03:  # some trend
            style = "Trend-following + Grid"
        else:
            style = "Mean reversion + Range"

    return style


def vwap_deviation_factor_for_style(style: str) -> float:
    """返回交易风格对应的 VWAP 偏离阈值系数。"""
    overrides = {
        "Mean reversion + VWAP": 0.4,
        "Trend-following + Breakout": 0.6,
    }
    return overrides.get(style, 0.5)


def _to_float(v):
    """将 numpy/pandas 标量或 None 转为可 JSON 序列化的 float；None 或空值返回 None。"""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def select_intraday_trade_day(
    market: str,
    daily_df: pd.DataFrame,
    cn_calendar_df: pd.DataFrame,
    *,
    now: pd.Timestamp | None = None,
) -> str:
    """为指定市场选择严格早于今天的最近交易日。

    CN 继续以现有 A 股交易日历为准；HK 等非 CN 市场从自身日线日期选择，避免
    A 股与港股节假日不一致时把错误日期交给分钟行情接口。
    """
    today = (now or pd.Timestamp.now()).normalize()
    market_key = data_sources.normalize_market(market)
    if market_key == "CN":
        dates = pd.to_datetime(cn_calendar_df['trade_date'], errors='coerce').dropna().sort_values()
    else:
        dates = pd.to_datetime(daily_df['date'], errors='coerce').dropna().sort_values()
    if dates.empty:
        raise ValueError(f"{market_key} 缺少可用于选择分时交易日的日期")
    previous = dates[dates < today]
    selected = previous.iloc[-1] if not previous.empty else dates.iloc[-1]
    return selected.strftime('%Y-%m-%d')


def build_stock_payload(code, name, instrument_type, trading_style, support, resistance, centers,
                        nearest_key_level, atr_20d, vwap, vwap_dev,
                        vwap_dev_threshold, orb_high, orb_low,
                        yesterday_close, yesterday_high, yesterday_low,
                        daily_df, intraday_df, intraday_day_str, usage_notes,
                        market="CN", currency="CNY", timezone="Asia/Shanghai"):
    """将单只股票或 ETF 的计算结果整理为前端 data.json 的 StockData 结构。

    - levels：每个聚类中心一条水平线，按位置赋予语义（support/resistance/key/center）。
    - daily：日线 OHLCV，日期为 'YYYY-MM-DD'。
    - intraday：上一交易日分时序列，无数据则为 None。
    - indicators：全部数值字段，缺失的分时用 None 表示（前端显示"—"）。
    - market/currency/timezone：新增可选市场元数据，前端对旧快照保持兼容。
    """
    # 水平线：每个聚类中心一条，位置决定语义，避免与 support/resistance/key 重复
    levels = []
    n = len(centers)
    nearest = float(nearest_key_level)
    for i, c in enumerate(centers):
        c = float(c)
        if i == 0:
            levels.append({"type": "support", "value": c, "label": "聚类支撑位"})
        elif i == n - 1:
            levels.append({"type": "resistance", "value": c, "label": "聚类阻力位"})
        elif abs(c - nearest) < 1e-9:
            levels.append({"type": "key", "value": c, "label": "最近关键价格"})
        else:
            levels.append({"type": "center", "value": c, "label": f"Cluster {i + 1}"})

    # 日线序列
    daily = []
    for _, row in daily_df.iterrows():
        daily.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "open": _to_float(row["open"]),
            "high": _to_float(row["high"]),
            "low": _to_float(row["low"]),
            "close": _to_float(row["close"]),
            "volume": int(row["volume"]) if not pd.isna(row["volume"]) else 0,
        })

    # 分时序列（无数据则为 None）
    intraday = None
    if intraday_df is not None and not intraday_df.empty:
        intraday = []
        for _, row in intraday_df.iterrows():
            intraday.append({
                "time": row["time"].strftime("%Y-%m-%d %H:%M:%S"),
                "price": _to_float(row["price"]),
                "volume": int(row["volume"]) if not pd.isna(row["volume"]) else 0,
            })

    indicators = {
        "lastClose": _to_float(yesterday_close),
        "atr20": _to_float(atr_20d),
        "support": _to_float(support),
        "resistance": _to_float(resistance),
        "nearestKeyLevel": _to_float(nearest_key_level),
        "yesterdayLow": _to_float(yesterday_low),
        "yesterdayHigh": _to_float(yesterday_high),
        "vwap": _to_float(vwap),
        "vwapDev": _to_float(vwap_dev),
        "vwapDevThreshold": _to_float(vwap_dev_threshold),
        "orbHigh": _to_float(orb_high),
        "orbLow": _to_float(orb_low),
    }

    return {
        "code": code,
        "name": name,
        "instrumentType": instrument_type,
        "market": market,
        "currency": currency,
        "timezone": timezone,
        "tradingStyle": trading_style,
        "lastTradeDay": intraday_day_str,
        "indicators": indicators,
        "levels": levels,
        "daily": daily,
        "intraday": intraday,
        "usageNotes": usage_notes,
    }


# ==============================================================================
# 4. Main flow: data fetching and computation
# ==============================================================================

def main(codes=None, output_root=None, json_path=None):
    """主流程，拉取数据、计算指标、生成 Excel 仪表盘与结构化 JSON（供前端 SPA 使用）。

    codes 为逗号分隔或列表形式的证券代码，可覆盖 STOCK_CONFIG 中的配置。
    output_root 覆盖默认输出根目录 out。
    json_path 指定时，额外将每只证券的计算结果写入该路径（结构化 data.json），
    用于替代旧的静态 HTML 报告，供前端 React SPA 渲染。
    返回 (results, payloads, last_trade_day_str)。
    """
    # 海外 runner 访问国内数据源时偶发连接挂死，只在真正运行任务时设置默认超时。
    socket.setdefaulttimeout(30)
    print(f"Akshare version: {ak.__version__}")
    print(f"Pandas version: {pd.__version__}")

    if isinstance(codes, str):
        codes = [c.strip() for c in codes.split(',') if c.strip()]

    indicator_output_dir = os.path.join(output_root or OUTPUT_ROOT, "indicators")

    # Today for data range
    today_str = datetime.now().strftime('%Y%m%d')
    try:
        last_trade_day_df = data_sources.fetch_trade_calendar()
        last_trade_day_str = last_trade_day_df['trade_date'].iloc[-1].strftime('%Y-%m-%d')
    except Exception as e:
        fallback_day = pd.Timestamp.now().normalize() - pd.Timedelta(days=1)
        print(f"无法获取交易日历，将使用昨天作为最近交易日。错误: {e}")
        last_trade_day_str = fallback_day.strftime('%Y-%m-%d')
        last_trade_day_df = pd.DataFrame({"trade_date": [fallback_day]})

    config_items = dict(STOCK_CONFIG)
    if codes:
        config_items = {c: config_items[c] for c in codes if c in config_items}

    results = []
    payloads = []

    for code, config in config_items.items():
        print(f"\nProcessing: {config['name']} ({code})...")
        try:
            instrument_type = data_sources.normalize_instrument_type(config.get('instrument_type'))
            market = data_sources.infer_market(code, config.get('market'))
            profile = data_sources.market_profile(market)
            currency_unit = {"CNY": "元", "HKD": "HKD", "USD": "USD"}[profile.currency]

            # --- Fetch daily data ---
            # market_compat 会从代码自动识别 HK/US；这里保留旧调用签名，让 CN/ETF 调用方和测试不受影响。
            stock_daily_df = data_sources.fetch_daily(
                code,
                "20240101",
                today_str,
                instrument_type=instrument_type,
            )
            # Ensure non-empty data
            if stock_daily_df is None or stock_daily_df.empty:
                print(f"  > 未能获取 {code} 的日线数据，跳过。")
                continue

            stock_daily_df['date'] = pd.to_datetime(stock_daily_df['date'])
            stock_daily_df.sort_values('date', inplace=True)

            # --- Determine trading style ---
            trading_style = determine_trading_style(stock_daily_df.copy())

            # --- Compute support/resistance via clusters ---
            support, resistance, centers, nearest_key_level = calculate_support_resistance(
                stock_daily_df.copy(), N_CLUSTERS)

            # --- Fetch intraday data ---
            # CN 继续用 A 股交易日历选上一交易日；HK 从自身日线日期选择，避免
            # 两地节假日不一致时把 A 股日期误用到港股分钟接口。
            intraday_day_str = select_intraday_trade_day(
                market,
                stock_daily_df,
                last_trade_day_df,
            )
            try:
                stock_intraday_df = data_sources.fetch_intraday(
                    code,
                    intraday_day_str,
                    instrument_type=instrument_type,
                )
            except Exception as e:
                print(f"  > 分时抓取失败，将基于日线输出：{e}")
                stock_intraday_df = pd.DataFrame()

            if stock_intraday_df is None or stock_intraday_df.empty:
                print(f"  > 未能获取 {code} 的分时数据，将基于日线输出结果。")
                # Without intraday, still compute daily-based indicators
                yesterday_close = stock_daily_df['close'].iloc[-1]
                yesterday_high = stock_daily_df['high'].iloc[-1]
                yesterday_low = stock_daily_df['low'].iloc[-1]
                vwap = None
            else:
                stock_intraday_df['time'] = pd.to_datetime(intraday_day_str + ' ' + stock_intraday_df['time'])

                # --- Indicator calculations ---
                yesterday_close = stock_daily_df['close'].iloc[-1]
                yesterday_high = stock_daily_df['high'].iloc[-1]
                yesterday_low = stock_daily_df['low'].iloc[-1]
                vwap = calculate_vwap(stock_intraday_df.copy())

            atr_20d = calculate_atr(stock_daily_df.copy(), ATR_PERIOD)

            # Parameters by trading style, can be overridden by per-stock config
            vwap_dev_k = vwap_deviation_factor_for_style(trading_style)

            # 按股票覆盖（迁移自 wu-t0-trading-assitant 的 STOCK_CONFIG）
            if config.get('vwap_dev_k') is not None:
                vwap_dev_k = config['vwap_dev_k']

            vwap_dev = yesterday_close - vwap if vwap is not None else None
            vwap_dev_threshold = vwap_dev_k * atr_20d

            orb_high, orb_low = (None, None)
            # ORB calculation
            if stock_intraday_df is not None and 'time' in stock_intraday_df.columns:
                orb_high, orb_low = get_opening_range(stock_intraday_df.copy())

            # --- Collect results（同时追踪本股票参数名，供前端使用说明映射）---
            stock_params = []

            def add_result(param, value):
                results.append({"股票代码": code, "股票名称": config['name'],
                                 "指标/参数": param, "计算值": value})
                stock_params.append(param)

            add_result("自动交易风格", trading_style)
            add_result("最新收盘价", f"{yesterday_close:.2f} {currency_unit}")
            add_result("20日ATR (日振幅)", f"{atr_20d:.2f} {currency_unit}")
            add_result("聚类支撑位", f"{support:.2f} {currency_unit}")
            add_result("聚类阻力位", f"{resistance:.2f} {currency_unit}")
            add_result("最近关键价格", f"{nearest_key_level:.2f} {currency_unit}")
            add_result("关键支撑位 (昨低)", f"{yesterday_low:.2f} {currency_unit}")
            add_result("关键阻力位 (昨高)", f"{yesterday_high:.2f} {currency_unit}")

            if vwap is not None:
                add_result("上一日VWAP", f"{vwap:.2f} {currency_unit}")
                add_result("收盘相对VWAP偏离", f"{vwap_dev:.2f} {currency_unit}")
                add_result("VWAP_DEV触发阈值", f"±{vwap_dev_threshold:.2f} {currency_unit}")

            if orb_high is not None and orb_low is not None:
                add_result("ORB突破上轨", f"{orb_high + 0.05:.2f} {currency_unit}")
                add_result("ORB突破下轨", f"{orb_low - 0.05:.2f} {currency_unit}")

            # --- 构建前端使用说明（计算指标说明 + 通用人工核查项）---
            usage_notes = [{"param": p, "note": USAGE_DICT[p]} for p in stock_params if p in USAGE_DICT]
            usage_notes += [{"param": p, "note": n} for p, n in USAGE_DICT_MANUAL.items()]

            # --- 构建结构化 payload（供 data.json / 前端 SPA）---
            payloads.append(build_stock_payload(
                code=code, name=config['name'], instrument_type=instrument_type,
                trading_style=trading_style,
                support=support, resistance=resistance, centers=centers,
                nearest_key_level=nearest_key_level, atr_20d=atr_20d,
                vwap=vwap, vwap_dev=vwap_dev, vwap_dev_threshold=vwap_dev_threshold,
                orb_high=orb_high, orb_low=orb_low,
                yesterday_close=yesterday_close, yesterday_high=yesterday_high,
                yesterday_low=yesterday_low,
                daily_df=stock_daily_df, intraday_df=stock_intraday_df,
                intraday_day_str=intraday_day_str, usage_notes=usage_notes,
                market=profile.market, currency=profile.currency, timezone=profile.timezone,
            ))
            print(f"  > 已整理结构化指标: {code}")

        except Exception as e:
            print(f"  > 处理 {code} 出错: {e}")
            import traceback

            traceback.print_exc()

    # ==============================================================================
    # 5. Generate Excel file
    # ==============================================================================
    if results:
        final_df = pd.DataFrame(results)

        manual_check_df = pd.DataFrame([
            {"股票代码": "通用", "股票名称": "所有", "指标/参数": "盘口不平衡", "计算值": "盘中实时观察"},
            {"股票代码": "通用", "股票名称": "所有", "指标/参数": "加速信号", "计算值": "盘中实时观察"},
            {"股票代码": "通用", "股票名称": "所有", "指标/参数": "滚动仓强制归零", "计算值": "按市场收盘前规则执行"},
            {"股票代码": "通用", "股票名称": "所有", "指标/参数": "最大日损", "计算值": "昨日收盘市值的1.2%"}
        ])

        final_df['使用说明'] = final_df['指标/参数'].map(USAGE_DICT)
        manual_check_df['使用说明'] = manual_check_df['指标/参数'].map(USAGE_DICT_MANUAL)

        output_df = pd.concat([final_df, manual_check_df], ignore_index=True)

        os.makedirs(indicator_output_dir, exist_ok=True)
        file_name = os.path.join(indicator_output_dir, f"T0交易指标_{last_trade_day_str}.xlsx")
        with pd.ExcelWriter(file_name, engine='openpyxl') as writer:
            output_df.to_excel(writer, sheet_name='T0_Trading_Dashboard', index=False,
                               columns=["股票代码", "股票名称", "指标/参数", "计算值", "使用说明"])

            worksheet = writer.sheets['T0_Trading_Dashboard']
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = length + 4

        print(f"\nExcel 文件已生成: {file_name}")

    else:
        print("\n未能成功处理任何股票，无法生成Excel文件。")
        results = []
        payloads = []

    if json_path:
        dashboard = {"generatedAt": last_trade_day_str, "stocks": payloads}
        parent = os.path.dirname(json_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(dashboard, f, ensure_ascii=False, indent=2)
        print(f"\n已生成结构化 JSON: {json_path}（{len(payloads)} 只股票）")

    return results, payloads, last_trade_day_str


def cli():
    parser = argparse.ArgumentParser(description="跨市场交易指标与图表生成")
    parser.add_argument("--codes", default=None,
                        help="逗号分隔的配置代码，例如 sz300246,00700.HK（默认使用 STOCK_CONFIG）")
    parser.add_argument("--output-root", default=None,
                        help="输出根目录（默认 out）")
    parser.add_argument("--json", dest="json_path", default=None,
                        help="输出结构化 JSON 到指定路径（替代旧的静态 HTML 报告，供前端 SPA 使用）")
    args = parser.parse_args()

    main(codes=args.codes, output_root=args.output_root, json_path=args.json_path)


if __name__ == '__main__':
    cli()
