# -*- coding: utf-8 -*-
"""
選股池與鎖股池掃描引擎 (Screener Pro - 高效快取版)
1. 完整支援官方 App 全套策略：
   - 波段 8 大子策略 (頭高底高、回後準進場、底部起漲、高檔起漲、雙線黃金交叉、一字底、N字底、圓弧底)
   - 長抱
   - 一點鐘 (1:00 PM 尾盤選股)
   - 盤中強勢
   - 鎖股池 3 階段 (等突破、高檔等回檔、回檔等上漲)
2. 助教把關機制 (實戰安全評級 🟢/🟡/🔴)
3. 支援價格分級過濾 (低價 <30 / 中價 30~100 / 高價 100~300 / 超高 >300)
4. 附帶 25 天 K 線走勢微縮數據 (供卡片即時渲染 5/20MA 操盤縮圖)
5. 記憶體全市場快取機制：毫秒級多策略隨心切換
"""

import time
import pandas as pd
import numpy as np
from core.data_fetcher import load_stock_list, fetch_stock_kline
from core.wave_engine import calculate_turning_points
from core.trend_analyzer import analyze_trend
from core.signal_detector import detect_signals

BROKER_NAMES = ["台灣摩根", "凱基台北", "元大", "富邦", "國泰敦南", "美商高盛", "統一", "永豐金", "華南永昌"]

_ANALYZED_STOCKS_CACHE = None
_LAST_CACHE_TIME = 0

def get_all_analyzed_stocks(force_refresh=False):
    """
    載入並分析全市場股票清單，結果快取於記憶體中 (5分鐘內不重複解析磁碟)
    """
    global _ANALYZED_STOCKS_CACHE, _LAST_CACHE_TIME
    now = time.time()

    if not force_refresh and _ANALYZED_STOCKS_CACHE is not None and (now - _LAST_CACHE_TIME) < 300:
        return _ANALYZED_STOCKS_CACHE

    stock_list = load_stock_list()
    analyzed = []

    for item in stock_list:
        code = item['code']
        try:
            df, info = fetch_stock_kline(code, period="6mo")
            if df.empty or len(df) < 15:
                continue

            points, _, highest, lowest = calculate_turning_points(df, ma_period=5)
            trend = analyze_trend(df, points)
            signals_dict, signals_list = detect_signals(df, trend)

            close_price = info['close']
            stage = signals_dict.get('watchlist_stage', '觀察中')

            # 擷取最近 25 天 K 線縮圖資料
            sub_recent = df.iloc[-25:].copy()
            recent_data = []
            for _, r in sub_recent.iterrows():
                recent_data.append({
                    "date": r['Date'].strftime('%m/%d'),
                    "open": round(float(r['Open']), 2),
                    "high": round(float(r['High']), 2),
                    "low": round(float(r['Low']), 2),
                    "close": round(float(r['Close']), 2),
                    "sma5": round(float(r.get('SMA_5', r['Close'])), 2),
                    "sma20": round(float(r.get('SMA_20', r['Close'])), 2)
                })

            # 主力籌碼模擬
            broker_seed = int(code[:4]) if code[:4].isdigit() else 1234
            broker_name = BROKER_NAMES[broker_seed % len(BROKER_NAMES)]
            buyer_vol = int(info['volume'] * ((broker_seed % 25 + 15) / 1000.0))
            buyer_vol = max(25, buyer_vol)

            analyzed.append({
                "code": item['code'],
                "name": item['name'],
                "market": item.get('market', 'TW'),
                "industry": item.get('industry', '一般類股'),
                "has_futures": item.get('has_futures', False),
                "has_cb": item.get('has_cb', False),
                "close": close_price,
                "change": info['change'],
                "change_pct": info['change_pct'],
                "volume": info['volume'],
                "volume_str": f"{int(info['volume']/1000):,} 張" if info['volume'] >= 1000 else f"{info['volume']} 股",
                "trend_status": trend['trend_status'],
                "trend_badge": trend['trend_badge'],
                "trend_color": trend['trend_color'],
                "support": trend.get('support'),
                "resistance": trend.get('resistance'),
                "target": trend.get('target'),
                "signals": signals_list,
                "signals_dict": signals_dict,
                "watchlist_stage": stage,
                "safety_rating": signals_dict.get('safety_rating', '🟢 安全首選'),
                "safety_reasons": signals_dict.get('safety_reasons', []),
                "chili_count": signals_dict.get('chili_count', 1),
                "broker_info": f"{broker_name} {buyer_vol:,} 張 (均 {round(close_price*0.995, 2)})",
                "recent_bars": recent_data,
                "is_bull": trend.get('higher_highs', False) and trend.get('higher_lows', False),
                "is_bear": trend.get('lower_highs', False) and trend.get('lower_lows', False)
            })

        except Exception:
            continue

    _ANALYZED_STOCKS_CACHE = analyzed
    _LAST_CACHE_TIME = now
    return analyzed

def scan_stocks(strategy="全部", direction="多", price_filter="全部", watchlist_stage="全部", limit=50):
    """
    高效過濾篩選
    """
    all_stocks = get_all_analyzed_stocks()
    filtered = []

    for s in all_stocks:
        close_price = s['close']
        stage = s['watchlist_stage']
        signals_dict = s['signals_dict']

        # 1. 價格區間篩選
        if price_filter == "低價" and close_price >= 30:
            continue
        elif price_filter == "中價" and not (30 <= close_price < 100):
            continue
        elif price_filter == "高價" and not (100 <= close_price < 300):
            continue
        elif price_filter == "超高" and close_price < 300:
            continue

        # 2. 鎖股池階段篩選
        if watchlist_stage != "全部" and stage != watchlist_stage:
            continue

        # 3. 多空方向篩選
        if direction == "多" and s['is_bear'] and not signals_dict.get('bottom_breakout', False):
            continue
        elif direction == "空" and s['is_bull']:
            continue

        # 4. 策略精準過濾
        match = False
        if strategy == "全部":
            match = True
        elif strategy == "頭高底高" and (signals_dict.get('higher_highs_lows', False) or s['is_bull']):
            match = True
        elif strategy == "回後準進場" and signals_dict.get('pullback_buy', False):
            match = True
        elif strategy == "底部起漲" and signals_dict.get('bottom_breakout', False):
            match = True
        elif strategy == "高檔起漲" and signals_dict.get('high_breakout', False):
            match = True
        elif strategy == "雙線黃金交叉" and signals_dict.get('golden_cross_5_20', False):
            match = True
        elif strategy == "一字底" and signals_dict.get('flat_base_breakout', False):
            match = True
        elif strategy == "N字底" and signals_dict.get('n_pattern_bottom', False):
            match = True
        elif strategy == "圓弧底" and signals_dict.get('rounding_bottom', False):
            match = True
        elif strategy == "長抱" and signals_dict.get('long_hold', False):
            match = True
        elif strategy == "一點鐘" and signals_dict.get('one_pm_strategy', False):
            match = True
        elif strategy == "盤中強勢" and signals_dict.get('intraday_strong', False):
            match = True
        elif strategy == "等突破" and stage == "等突破":
            match = True
        elif strategy == "高檔等回檔" and stage == "高檔等回檔":
            match = True
        elif strategy == "回檔等上漲" and stage == "回檔等上漲":
            match = True

        if match:
            filtered.append(s)
            if len(filtered) >= limit:
                break

    return filtered
