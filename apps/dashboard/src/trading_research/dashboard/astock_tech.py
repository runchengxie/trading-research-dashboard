# 1. Ensure required libraries are installed
# pip install akshare pandas openpyxl scikit-learn

import argparse
import json
import os
import socket
from datetime import datetime
from pathlib import Path
from typing import cast

import akshare as ak
import pandas as pd

from trading_research.dashboard.config import (
    STOCK_CONFIG,
    USAGE_DICT,
    USAGE_DICT_MANUAL,
)
from trading_research.dashboard.indicators import (
    _to_float,
    calculate_atr,
    calculate_support_resistance,
    calculate_vwap,
    determine_trading_style,
    get_opening_range,
    vwap_deviation_factor_for_style,
)
from trading_research.data import market_compat as data_sources

# ==============================================================================
# 2. Parameters
# ==============================================================================
# ATR period
ATR_PERIOD = 20
# Number of clusters
N_CLUSTERS = 5
# Output directories
OUTPUT_ROOT = "out"


def _us_ticker_label(code: str) -> str:
    value = code.strip()
    if value.lower().startswith("us:"):
        return value[3:].upper()
    if value.upper().endswith(".US"):
        return value[:-3].upper()
    raise ValueError(f"美股代码格式无效：{code!r}")


def _resolve_config_items(codes: list[str] | None = None) -> dict[str, dict[str, object]]:
    """Resolve configured instruments and synthesize decorated US stock codes on demand."""
    configs = dict(STOCK_CONFIG)
    if not codes:
        return configs

    selected: dict[str, dict[str, object]] = {}
    for code in codes:
        if code in configs:
            selected[code] = configs[code]
            continue
        if data_sources.infer_market(code) == "US":
            selected[code] = {
                "name": _us_ticker_label(code),
                "instrument_type": "stock",
                "market": "US",
            }
    return selected


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

def main(
    codes: list[str] | None = None,
    output_root: str | Path | None = None,
    json_path: str | Path | None = None,
) -> tuple[list[dict[str, object]], list[dict[str, object]], str]:
    """主流程，拉取数据、计算指标、生成 Excel 仪表盘与结构化 JSON（供前端 SPA 使用）。

    codes 为逗号分隔或列表形式的证券代码，可覆盖 STOCK_CONFIG 中的配置；
    AAPL.US / us:AAPL 这类带 US 市场信息的未预配置代码会按美股 stock 自动补齐配置。
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

    config_items = _resolve_config_items(codes)

    results = []
    payloads = []

    for code, config in config_items.items():
        print(f"\nProcessing: {config['name']} ({code})...")
        try:
            instrument_type = data_sources.normalize_instrument_type(
                cast(str | None, config.get('instrument_type'))
            )
            market = data_sources.infer_market(code, cast(str | None, config.get('market')))
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
            # CN 继续用 A 股交易日历选上一交易日；HK/US 从自身日线日期选择，避免
            # 跨市场节假日不一致时把 A 股日期误用到海外分钟接口。
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
            configured_vwap_dev_k = config.get('vwap_dev_k')
            if configured_vwap_dev_k is not None:
                vwap_dev_k = float(cast(float | int, configured_vwap_dev_k))

            vwap_dev = yesterday_close - vwap if vwap is not None else None
            vwap_dev_threshold = vwap_dev_k * atr_20d

            orb_high, orb_low = (None, None)
            # ORB calculation
            if stock_intraday_df is not None and 'time' in stock_intraday_df.columns:
                orb_high, orb_low = get_opening_range(stock_intraday_df.copy())

            # --- Collect results（同时追踪本股票参数名，供前端使用说明映射）---
            stock_params = []

            def add_result(param, value, *, code=code, name=config['name'], stock_params=stock_params):
                results.append({"股票代码": code, "股票名称": name,
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
                        help="逗号分隔代码，例如 sz300246,00700.HK,AAPL.US,TSLA.US（默认使用 STOCK_CONFIG）")
    parser.add_argument("--output-root", default=None,
                        help="输出根目录（默认 out）")
    parser.add_argument("--json", dest="json_path", default=None,
                        help="输出结构化 JSON 到指定路径（替代旧的静态 HTML 报告，供前端 SPA 使用）")
    args = parser.parse_args()

    main(codes=args.codes, output_root=args.output_root, json_path=args.json_path)


if __name__ == '__main__':
    cli()
