# -*- coding: utf-8 -*-
"""
大盤同步與滯後補漲量化分析引擎 (Market Synchronization & Lagging Catch-Up Radar)
核心職責：
1. 抓取大盤基準指數 (^TWII 加權指數)，與台股主流熱門股進行多維度走勢比對。
2. 計算兩大核心指標：
   - 【走勢幾何相似度 (Shape Correlation)】：歸一化價格軌跡皮爾森相關性，確認個股型態是否與大盤同構。
   - 【報酬率同步率 (Return Correlation)】：近 20 日每日漲跌幅相關性。
3. 識別【領先-滯後差 (Lead-Lag Gap)】：
   - 篩選出「型態與大盤高度同步，但近期走勢落後於大盤 2%~15%」之潛在滯後補漲股。
   - 搭配技術結構健康濾網（守穩月線/前底、非空頭排列、無爆量長黑），排除「假補漲、真弱勢」標的。
4. 提供大盤 vs 個股歸一化走勢比對圖 (Plotly Figure) 與補漲目標價試算。
"""

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict, Any, Tuple, Optional

from core.data_fetcher import fetch_stock_kline, batch_fetch_realtime_quotes, get_tw_now, load_stock_list
from core.wave_engine import calculate_turning_points
from core.trend_analyzer import analyze_trend
from core.signal_detector import detect_signals

_MKT_CACHE = {}

def get_market_benchmark(period: str = "6mo", force_refresh: bool = False) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
    """獲取大盤加權指數 K 線與行情數據 (帶 60 秒盤中即時快取)"""
    global _MKT_CACHE
    now = get_tw_now()
    today_str = now.strftime('%Y-%m-%d')
    cached = _MKT_CACHE.get(period)

    if not force_refresh and cached is not None:
        c_time = cached.get("timestamp")
        c_info = cached.get("info")
        if c_time is not None and (now - c_time).total_seconds() < 60:
            is_weekday = now.weekday() < 5
            market_started = (now.hour > 9) or (now.hour == 9 and now.minute >= 0)
            if is_weekday and market_started:
                # 盤中開盤時間：確認快取資料日期為今天；若為舊日行情則強制重刷
                if c_info and c_info.get("latest_date") == today_str:
                    return cached["df"].copy(), cached["info"]
            else:
                return cached["df"].copy(), cached["info"]

    df_mkt, info_mkt = fetch_stock_kline("^TWII", period=period, force_refresh=force_refresh, enable_realtime=True)
    if df_mkt is not None and not df_mkt.empty:
        _MKT_CACHE[period] = {
            "df": df_mkt,
            "info": info_mkt,
            "timestamp": now
        }
        return df_mkt.copy(), info_mkt
    return None, None

def calculate_market_environment_guidance(df_mkt: pd.DataFrame, info_mkt: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    依據朱家泓老師最新實戰心法（理財達人秀節後攻勢篇）：
    計算大盤指數 (^TWII) 之環境診斷、止跌/上攻條件與建議持股資金水位。

    朱老師三大上攻條件：
    1. 攻擊量基本要回到均量或 8000 億以上 (出攻擊量)
    2. 突破前日黑K高點 (化解短線壓力)
    3. 站回月線 (20MA) 且月線走平翻揚

    朱老師操作資金紀律：
    - 🟢 多頭攻擊波：持股 60%~70% (做多強勢股，守5MA續抱)
    - 🟡 震盪量縮期：資金嚴格控制 40% 以下 (只做強勢多頭短線，嚴格風控)
    - 🔴 空頭破線期：資金 0%~20% (多看少做，保留大量現金因應變化)
    """
    if df_mkt is None or df_mkt.empty or len(df_mkt) < 20:
        return {
            "status_code": "UNKNOWN",
            "status_label": "⚪ 資料不足",
            "capital_advice": "資金水位 4 成以下 (風控為先)",
            "recommended_pct": 40,
            "badge_color": "#64748B",
            "action_strategy": "暫無法取得完整大盤數據，請保守觀望。",
            "conditions": []
        }

    c = float(df_mkt['Close'].iloc[-1])
    o = float(df_mkt['Open'].iloc[-1])
    v = float(df_mkt['Volume'].iloc[-1])
    
    # 均線計算
    sma5 = float(df_mkt['SMA_5'].iloc[-1]) if 'SMA_5' in df_mkt else float(df_mkt['Close'].rolling(5).mean().iloc[-1])
    prev_sma5 = float(df_mkt['SMA_5'].iloc[-2]) if 'SMA_5' in df_mkt else sma5
    sma20 = float(df_mkt['SMA_20'].iloc[-1]) if 'SMA_20' in df_mkt else float(df_mkt['Close'].rolling(20).mean().iloc[-1])
    prev_sma20 = float(df_mkt['SMA_20'].iloc[-2]) if 'SMA_20' in df_mkt else sma20
    
    # 量能均線
    vma5 = float(df_mkt['Volume'].rolling(5).mean().iloc[-1])
    vma20 = float(df_mkt['Volume'].rolling(20).mean().iloc[-1])
    vol_ratio_5 = v / (vma5 + 1e-9)
    vol_ratio_20 = v / (vma20 + 1e-9)

    # 前一根 K 棒
    prev_bar = df_mkt.iloc[-2]
    prev_h = float(prev_bar['High'])
    prev_c = float(prev_bar['Close'])
    prev_o = float(prev_bar['Open'])
    prev_is_black = (prev_c < prev_o)

    # 條件 1: 站回月線 (20MA) 且月線走平/向上
    cond_ma20 = (c >= sma20)
    cond_ma20_rising = (sma20 >= prev_sma20 * 0.999)
    ma20_ok = cond_ma20 and cond_ma20_rising

    # 條件 2: 站穩 5MA 操盤線且 5MA 翻揚
    cond_5ma = (c >= sma5) and (sma5 >= prev_sma5 * 0.999)

    # 條件 3: 攻擊量回升 (成交量放大至 5MA/20MA 均量之上)
    cond_attack_vol = (vol_ratio_5 >= 1.0 or vol_ratio_20 >= 1.0)
    
    # 條件 4: 突破昨日高點 (若昨日為黑K，過昨黑K高點更具意義)
    cond_over_prev_high = (c >= prev_h * 0.998)

    conditions = [
        {
            "name": "站回月線 (20MA)",
            "passed": ma20_ok,
            "desc": f"大盤現價 {c:,.0f} 點 {'✅ 站穩' if c >= sma20 else '❌ 跌破'} 月線 ({sma20:,.0f} 點)，月線 {'走平翻揚' if cond_ma20_rising else '下彎助跌'}"
        },
        {
            "name": "站上操盤線 (5MA)",
            "passed": cond_5ma,
            "desc": f"操盤線 5MA ({sma5:,.0f} 點) {'✅ 走升有守' if cond_5ma else '⚠️ 尚未站穩或下彎'}"
        },
        {
            "name": "具備攻擊量 (≥均量)",
            "passed": cond_attack_vol,
            "desc": f"今日成交量為 5日均量之 {vol_ratio_5*100:.0f}%，{'✅ 達攻擊量' if cond_attack_vol else '⚠️ 量縮震盪'}"
        },
        {
            "name": "過前日K線高點",
            "passed": cond_over_prev_high,
            "desc": f"{'✅ 突破昨高化解短線壓力' if cond_over_prev_high else '⚠️ 尚未過前一日高點 (' + f'{prev_h:,.0f} 點)'}"
        }
    ]

    passed_cnt = sum(1 for item in conditions if item['passed'])

    # 判定燈號與資金水位
    if ma20_ok and cond_5ma and (cond_attack_vol or cond_over_prev_high):
        status_code = "BULL_ATTACK"
        status_label = "🟢 多頭攻擊波"
        capital_advice = "持股水位 60% ～ 70% (標準波段)"
        recommended_pct = 70
        badge_color = "#10B981"
        action_strategy = (
            "【多頭攻擊確立】大盤站穩月線之上且操盤線 5MA 翻揚！"
            "操作策略：主流多頭股順勢做多，精選四線多排與回後買上漲標的，買進後嚴格守穩 5MA 移動停利！"
        )
    elif not cond_ma20 and not cond_ma20_rising and not cond_5ma:
        status_code = "BEAR_WEAK"
        status_label = "🔴 空頭破線期"
        capital_advice = "資金水位 0% ～ 20% (保留現金·防守)"
        recommended_pct = 20
        badge_color = "#EF4444"
        action_strategy = (
            "【空頭修正破線】大盤跌破月線且 20MA 下彎助跌，多頭架構破壞！"
            "操作策略：嚴格遵守朱老師紀律，保留 8 成以上現金因應盤勢變化，切勿盲目接刀摸底！空方避險或多看少做。"
        )
    else:
        status_code = "CHOPPY_DEFEND"
        status_label = "🟡 震盪整理期"
        capital_advice = "資金嚴格控制 40% 以下 (做短線)"
        recommended_pct = 40
        badge_color = "#F59E0B"
        action_strategy = (
            "【大盤量縮震盪】多空拉鋸、攻擊量尚未全面放大！"
            "操作策略：按照朱家泓老師實戰紀律，現在要將資金嚴格控制在 4 成以下！只做強勢多頭龍頭股、做短線，不長抱！"
        )

    return {
        "status_code": status_code,
        "status_label": status_label,
        "capital_advice": capital_advice,
        "recommended_pct": recommended_pct,
        "badge_color": badge_color,
        "action_strategy": action_strategy,
        "conditions": conditions,
        "passed_count": passed_cnt,
        "close": c,
        "sma5": sma5,
        "sma20": sma20,
        "vol_ratio_5": vol_ratio_5
    }

def analyze_market_sync_single(
    df_stock: pd.DataFrame,
    df_mkt: pd.DataFrame,
    stock_info: Dict[str, Any],
    lookback_bars: int = 40
) -> Optional[Dict[str, Any]]:
    """
    針對單檔個股比對與大盤的同步率、型態相似度與滯後程度
    """
    if df_stock is None or len(df_stock) < 25 or df_mkt is None or len(df_mkt) < 25:
        return None

    # 日期對齊
    merged = pd.merge(
        df_stock[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']],
        df_mkt[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']],
        on='Date',
        suffixes=('_stock', '_mkt')
    ).sort_values('Date').dropna().reset_index(drop=True)

    if len(merged) < 20:
        return None

    sub = merged.tail(lookback_bars).copy()
    if len(sub) < 15:
        return None

    # 1. 報酬率相關性 (同步率)
    ret_s = sub['Close_stock'].pct_change().dropna()
    ret_m = sub['Close_mkt'].pct_change().dropna()
    corr_return = float(ret_s.corr(ret_m)) if len(ret_s) >= 10 else 0.0
    corr_return = 0.0 if np.isnan(corr_return) else corr_return

    # 2. 幾何走勢形狀相似度 (歸一化價格波形皮爾森係數)
    s_min, s_max = sub['Close_stock'].min(), sub['Close_stock'].max()
    m_min, m_max = sub['Close_mkt'].min(), sub['Close_mkt'].max()
    s_norm = (sub['Close_stock'] - s_min) / (s_max - s_min + 1e-9)
    m_norm = (sub['Close_mkt'] - m_min) / (m_max - m_min + 1e-9)
    shape_corr = float(s_norm.corr(m_norm))
    shape_corr = 0.0 if np.isnan(shape_corr) else shape_corr

    # 3. 相對累積漲跌幅 (走勢滯後差距計算)
    # 以 5 日與 15 日為觀察窗口
    m_p_now = sub['Close_mkt'].iloc[-1]
    s_p_now = sub['Close_stock'].iloc[-1]

    idx_5 = max(0, len(sub) - 6)
    idx_15 = max(0, len(sub) - 16)

    mkt_5d = ((m_p_now - sub['Close_mkt'].iloc[idx_5]) / sub['Close_mkt'].iloc[idx_5]) * 100
    stk_5d = ((s_p_now - sub['Close_stock'].iloc[idx_5]) / sub['Close_stock'].iloc[idx_5]) * 100
    lag_gap_5d = mkt_5d - stk_5d

    mkt_15d = ((m_p_now - sub['Close_mkt'].iloc[idx_15]) / sub['Close_mkt'].iloc[idx_15]) * 100
    stk_15d = ((s_p_now - sub['Close_stock'].iloc[idx_15]) / sub['Close_stock'].iloc[idx_15]) * 100
    lag_gap_15d = mkt_15d - stk_15d

    # 4. 個股技術健康度檢核 (防止「假補漲、真破線弱勢股」)
    last_c = float(df_stock['Close'].iloc[-1])
    sma5 = float(df_stock['Close'].rolling(5).mean().iloc[-1]) if len(df_stock) >= 5 else last_c
    sma20 = float(df_stock['Close'].rolling(20).mean().iloc[-1]) if len(df_stock) >= 20 else last_c
    low_20 = float(df_stock['Low'].tail(20).min())

    diff_ma20 = ((last_c - sma20) / sma20) * 100
    diff_ma5 = ((last_c - sma5) / sma5) * 100

    # 健康多頭或打底條件：
    # (A) 股價未嚴重摜破月線 (收盤在 20MA -3.5% 之上)
    # (B) 未摜破 20 日最低點
    # (C) 形狀相似度 >= 0.65 或報酬相關性 >= 0.50
    is_struct_safe = (last_c >= sma20 * 0.965) and (last_c >= low_20 * 1.01)
    
    # 5. 補漲狀態與目標評定
    # 若大盤領先拉開差距，計算若個股補漲回到與大盤相同位階的目標價
    catchup_pct = max(0.0, lag_gap_5d)
    catchup_target = round(last_c * (1 + catchup_pct / 100), 2)
    
    # 防守停損設定
    stop_loss = round(max(low_20, last_c * 0.95), 2)
    if stop_loss >= last_c:
        stop_loss = round(last_c * 0.95, 2)
    risk_pct = round(((last_c - stop_loss) / last_c) * 100, 1)

    # 評定標籤
    if shape_corr >= 0.75 and lag_gap_5d >= 3.0 and is_struct_safe:
        status_badge = "🔥 強烈滯後補漲 (形狀同構·蓄勢待發)"
        status_color = "#FF4D4F"
        priority = 1
    elif shape_corr >= 0.70 and lag_gap_5d >= 1.0 and is_struct_safe:
        status_badge = "🟢 溫和滯後待發 (結構安全·位階偏低)"
        status_color = "#52C41A"
        priority = 2
    elif shape_corr >= 0.75 and lag_gap_5d < 1.0:
        status_badge = "⚡ 大盤高度同步 (同步推升中)"
        status_color = "#1890FF"
        priority = 3
    elif lag_gap_5d >= 5.0 and not is_struct_safe:
        status_badge = "⚠️ 弱勢落後警戒 (注意非補漲)"
        status_color = "#FAAD14"
        priority = 4
    else:
        status_badge = "常態走勢"
        status_color = "#8892B0"
        priority = 5

    # 綜合評分 (0 ~ 100)
    # 形狀相似度 (40%) + 相關性 (20%) + 適度滯後空間 (25%) + 均線健康度 (15%)
    lag_bonus = min(25.0, max(0.0, lag_gap_5d * 2.5))
    sync_score = round(
        max(0.0, shape_corr * 40) +
        max(0.0, corr_return * 20) +
        lag_bonus +
        (15.0 if last_c >= sma20 else (10.0 if is_struct_safe else 0.0)),
        1
    )

    # 6. 進階安全檢核、趨勢操盤線與動能指標 (無敵鐵金剛 / 5MA走勢 / 安全燈號 / 動能辣椒)
    last_r = df_stock.iloc[-1]
    prev_r = df_stock.iloc[-2] if len(df_stock) > 1 else last_r

    c_now = float(last_r['Close'])
    c_prev = float(prev_r['Close'])
    change = round(c_now - c_prev, 2)
    change_pct = round((change / c_prev) * 100, 2) if c_prev != 0 else 0.0
    is_up = change >= 0

    cur_sma5 = float(last_r.get('SMA_5', sma5))
    prev_sma5 = float(prev_r.get('SMA_5', cur_sma5))
    is_5ma_rising = cur_sma5 >= prev_sma5
    above_5ma = c_now >= cur_sma5

    try:
        points, _, _, _ = calculate_turning_points(df_stock, ma_period=5)
        trend = analyze_trend(df_stock, points)
        signals_dict, signals_list = detect_signals(df_stock, trend)
        safety_rating = signals_dict.get('safety_rating', '🟢 安全首選')
        safety_reasons = signals_dict.get('safety_reasons', [])
        chili_count = signals_dict.get('chili_count', 1)
        iron_man = bool(signals_dict.get('iron_man', False))
    except Exception:
        safety_rating = '🟢 安全首選' if is_struct_safe else '🟡 警訊注意'
        safety_reasons = [] if is_struct_safe else ["結構偏弱未達安全標準"]
        chili_count = 1
        iron_man = False
        signals_dict = {}

    return {
        "code": stock_info.get("code", ""),
        "name": stock_info.get("name", ""),
        "industry": stock_info.get("industry", ""),
        "close": last_c,
        "change": change,
        "change_pct": change_pct,
        "is_up": is_up,
        "sma5": round(sma5, 2),
        "sma20": round(sma20, 2),
        "shape_corr": round(shape_corr * 100, 1),
        "corr_return": round(corr_return * 100, 1),
        "mkt_5d": round(mkt_5d, 1),
        "stk_5d": round(stk_5d, 1),
        "lag_gap_5d": round(lag_gap_5d, 1),
        "mkt_15d": round(mkt_15d, 1),
        "stk_15d": round(stk_15d, 1),
        "lag_gap_15d": round(lag_gap_15d, 1),
        "diff_ma20": round(diff_ma20, 1),
        "diff_ma5": round(diff_ma5, 1),
        "catchup_target": catchup_target,
        "stop_loss": stop_loss,
        "risk_pct": risk_pct,
        "status_badge": status_badge,
        "status_color": status_color,
        "priority": priority,
        "sync_score": sync_score,
        "is_struct_safe": is_struct_safe,
        "safety_rating": safety_rating,
        "safety_reasons": safety_reasons,
        "chili_count": chili_count,
        "is_5ma_rising": is_5ma_rising,
        "above_5ma": above_5ma,
        "iron_man": iron_man,
        "signals_dict": signals_dict
    }

def scan_market_sync_candidates(
    stock_list: Optional[List[Dict[str, Any]]] = None,
    filter_mode: str = "lagging_only", # 'lagging_only' / 'all_sync' / 'all'
    min_shape_corr: float = 65.0,
    top_n: int = 25,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    掃描全市場或指定股池，比對與大盤同步之滯後補漲股 (全面支援盤中即時行情無縫對齊)
    """
    df_mkt, info_mkt = get_market_benchmark(period="3mo", force_refresh=force_refresh)
    if df_mkt is None or df_mkt.empty:
        return []

    if stock_list is None:
        stock_list = load_stock_list()

    # 盤中並行獲取全市場即時報價，確保所有候選個股皆為最新盤中撮合價
    realtime_map = {}
    try:
        realtime_map = batch_fetch_realtime_quotes(stock_list)
    except Exception:
        realtime_map = {}

    has_realtime = bool(realtime_map)
    candidates = []
    for s in stock_list:
        code = s['code']
        q_live = realtime_map.get(code)
        df_s, info_s = fetch_stock_kline(code, period="3mo", force_refresh=force_refresh, enable_realtime=has_realtime, realtime_quote=q_live)
        res = analyze_market_sync_single(df_s, df_mkt, s, lookback_bars=40)
        if not res:
            continue

        # 依條件篩選
        if filter_mode == "lagging_only":
            if res["shape_corr"] >= min_shape_corr and res["lag_gap_5d"] >= 1.5 and res["is_struct_safe"]:
                candidates.append(res)
        elif filter_mode == "all_sync":
            if res["shape_corr"] >= min_shape_corr and res["is_struct_safe"]:
                candidates.append(res)
        else:
            candidates.append(res)

    # 排序：策略優先級 -> 安全評級 (🟢安全首選最優先) -> 綜合評分 -> 滯後空間
    def _sort_key(x):
        p = x.get("priority", 5)
        safety = x.get("safety_rating", "")
        safety_rank = 0 if "安全首選" in safety else (1 if "警訊注意" in safety else 2)
        score = x.get("sync_score", 0)
        gap = x.get("lag_gap_5d", 0)
        return (p, safety_rank, -score, -gap)

    candidates.sort(key=_sort_key)
    return candidates[:top_n]

def create_market_sync_comparison_figure(
    df_stock: pd.DataFrame,
    df_mkt: Optional[pd.DataFrame] = None,
    stock_name: str = "",
    stock_code: str = "",
    sync_data: Optional[Dict[str, Any]] = None,
    df_market: Optional[pd.DataFrame] = None,
    **kwargs
) -> Optional[go.Figure]:
    """
    繪製大盤 vs 個股雙軸與累積報酬率對比圖 (一眼看出領先與滯後補漲空間)
    """
    if df_mkt is None and df_market is not None:
        df_mkt = df_market

    if df_stock is None or df_mkt is None or df_stock.empty or df_mkt.empty:
        return None

    # 對齊日期
    try:
        merged = pd.merge(
            df_stock[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']],
            df_mkt[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']],
            on='Date',
            suffixes=('_stock', '_mkt')
        ).sort_values('Date').dropna().reset_index(drop=True)
    except Exception:
        return None

    if len(merged) < 5:
        return None

    # 抓取最近 45 個交易日
    sub = merged.tail(45).copy().reset_index(drop=True)

    # 計算以區間第一天為基準的累積百分比漲跌幅 (0% Baseline)
    s_base = sub['Close_stock'].iloc[0]
    m_base = sub['Close_mkt'].iloc[0]
    sub['Stock_Pct'] = ((sub['Close_stock'] - s_base) / s_base) * 100
    sub['Market_Pct'] = ((sub['Close_mkt'] - m_base) / m_base) * 100

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=(
            f"📈 走勢同步對比 (累積報酬率 % · 金色:大盤加權指數 vs 青色:{stock_name})",
            f"🕯️ 【{stock_name} ({stock_code})】技術 K 線與 5MA / 20MA 操盤防守線"
        ),
        row_heights=[0.55, 0.45]
    )

    # ----------------- ROW 1: 累積漲跌幅百分比對比 -----------------
    # 大盤曲線 (金色)
    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Market_Pct'],
        name="大盤加權指數 (^TWII)",
        line=dict(color="#FFD700", width=2.8),
        hovertemplate="大盤累積: %{y:+.2f}%<extra></extra>"
    ), row=1, col=1)

    # 個股曲線 (青藍色)
    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Stock_Pct'],
        name=f"{stock_name} ({stock_code})",
        line=dict(color="#13C2C2", width=2.8),
        hovertemplate=f"{stock_name}累積: " + "%{y:+.2f}%<extra></extra>"
    ), row=1, col=1)

    # 填充相對差 (若大盤領先，填出補漲空間區域)
    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Market_Pct'],
        fill=None, mode='lines', line=dict(color='rgba(0,0,0,0)'),
        showlegend=False, hoverinfo='skip'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Stock_Pct'],
        fill='tonexty', mode='lines',
        fillcolor='rgba(255, 215, 0, 0.12)',
        line=dict(color='rgba(0,0,0,0)'),
        name="補漲潛在差距區",
        hoverinfo='skip'
    ), row=1, col=1)

    # ----------------- ROW 2: 個股 K 線 -----------------
    # 計算 5MA 與 20MA
    sub['SMA_5'] = sub['Close_stock'].rolling(5).mean()
    sub['SMA_20'] = sub['Close_stock'].rolling(20).mean()

    # K 棒
    fig.add_trace(go.Candlestick(
        x=sub['Date'],
        open=sub['Open_stock'], high=sub['High_stock'],
        low=sub['Low_stock'], close=sub['Close_stock'],
        name=f"{stock_name} K線",
        increasing_line_color='#FF4D4F', increasing_fillcolor='#FF4D4F',
        decreasing_line_color='#2F9E44', decreasing_fillcolor='#2F9E44',
        showlegend=False
    ), row=2, col=1)

    # 5MA 與 20MA
    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['SMA_5'],
        name="5MA 操盤線", line=dict(color="#1890FF", width=1.5)
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['SMA_20'],
        name="20MA 月線", line=dict(color="#E0A82E", width=1.5)
    ), row=2, col=1)

    # 調整標題位置與字體，避免與圖表邊界擠壓
    if len(fig.layout.annotations) > 0:
        fig.layout.annotations[0].update(y=1.05, font=dict(size=13, color="#E2E8F0"))
    if len(fig.layout.annotations) > 1:
        fig.layout.annotations[1].update(font=dict(size=13, color="#E2E8F0"))

    fig.update_layout(
        height=680,
        margin=dict(l=20, r=75, t=55, b=65),
        template="plotly_dark",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.09,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color="#94A3B8")
        ),
        hovermode="x unified"
    )
    fig.update_xaxes(rangeslider_visible=False)
    return fig


# ==============================================================================
# 族群龍頭外溢·看大哥買小弟量化比對模組 (Sector Leader Spillover & Laggard Catch-Up)
# ==============================================================================

SECTOR_FLEETS = [
    {
        "id": "plastics",
        "name": "塑膠石化與集團艦隊",
        "icon": "🛢️",
        "leader_anchor": "1303",  # 南亞
        "members": [
            {"code": "1303", "name": "南亞"},
            {"code": "1301", "name": "台塑"},
            {"code": "1309", "name": "台達化"},
            {"code": "1312", "name": "國喬"},
            {"code": "1709", "name": "和益"},
            {"code": "4714", "name": "永捷"}
        ]
    },
    {
        "id": "ai_server",
        "name": "AI 伺服器與代工艦隊",
        "icon": "🖥️",
        "leader_anchor": "2382",  # 廣達
        "members": [
            {"code": "2382", "name": "廣達"},
            {"code": "6669", "name": "緯穎"},
            {"code": "3231", "name": "緯創"},
            {"code": "2357", "name": "華碩"},
            {"code": "2317", "name": "鴻海"},
            {"code": "7711", "name": "永擎"}
        ]
    },
    {
        "id": "thermal",
        "name": "AI 散熱模組艦隊",
        "icon": "❄️",
        "leader_anchor": "3017",  # 奇鋐
        "members": [
            {"code": "3017", "name": "奇鋐"},
            {"code": "3324", "name": "雙鴻"},
            {"code": "2421", "name": "建準"},
            {"code": "3338", "name": "泰碩"},
            {"code": "3483", "name": "力致"}
        ]
    },
    {
        "id": "shipping",
        "name": "航運同盟 (貨櫃與散裝)",
        "icon": "🚢",
        "leader_anchor": "2603",  # 長榮
        "members": [
            {"code": "2603", "name": "長榮"},
            {"code": "2609", "name": "陽明"},
            {"code": "2615", "name": "萬海"},
            {"code": "2612", "name": "中航"},
            {"code": "2605", "name": "新興"},
            {"code": "2606", "name": "裕民"},
            {"code": "2637", "name": "慧洋-KY"}
        ]
    },
    {
        "id": "heavy_electric",
        "name": "重電與綠能電機艦隊",
        "icon": "⚡",
        "leader_anchor": "1609",  # 大亞
        "members": [
            {"code": "1609", "name": "大亞"},
            {"code": "1528", "name": "恩德"},
            {"code": "3628", "name": "盈正"},
            {"code": "1519", "name": "華城"},
            {"code": "1513", "name": "中興電"},
            {"code": "1503", "name": "士電"}
        ]
    },
    {
        "id": "cpo_optical",
        "name": "光通訊與 CPO 艦隊",
        "icon": "💡",
        "leader_anchor": "6442",  # 光聖
        "members": [
            {"code": "6442", "name": "光聖"},
            {"code": "3450", "name": "聯鈞"},
            {"code": "3081", "name": "聯亞"},
            {"code": "6426", "name": "統新"},
            {"code": "6530", "name": "創威"},
            {"code": "3234", "name": "光環"},
            {"code": "7717", "name": "萊德光電-KY"}
        ]
    },
    {
        "id": "probe_card_test",
        "name": "探針卡與先進測試艦隊",
        "icon": "📌",
        "leader_anchor": "6223",  # 旺矽
        "members": [
            {"code": "6223", "name": "旺矽"},
            {"code": "6515", "name": "穎崴"},
            {"code": "6510", "name": "精測"},
            {"code": "6683", "name": "雍智科技"},
            {"code": "6217", "name": "中探針"}
        ]
    },
    {
        "id": "semiconductor",
        "name": "半導體代工與封測艦隊",
        "icon": "🔬",
        "leader_anchor": "2330",  # 台積電
        "members": [
            {"code": "2330", "name": "台積電"},
            {"code": "2303", "name": "聯電"},
            {"code": "5347", "name": "世界"},
            {"code": "3711", "name": "日月光投控"},
            {"code": "2449", "name": "京元電子"},
            {"code": "2338", "name": "光罩"}
        ]
    },
    {
        "id": "ic_memory",
        "name": "IC 設計與記憶體艦隊",
        "icon": "💾",
        "leader_anchor": "3006",  # 晶豪科
        "members": [
            {"code": "3006", "name": "晶豪科"},
            {"code": "2454", "name": "聯發科"},
            {"code": "2408", "name": "南亞科"},
            {"code": "2344", "name": "華邦電"},
            {"code": "2363", "name": "矽統"},
            {"code": "3034", "name": "聯詠"}
        ]
    },
    {
        "id": "passive_components",
        "name": "被動元件與電阻艦隊",
        "icon": "🔋",
        "leader_anchor": "3624",  # 光頡
        "members": [
            {"code": "3624", "name": "光頡"},
            {"code": "6834", "name": "天二科技"},
            {"code": "6224", "name": "聚鼎"},
            {"code": "2327", "name": "國巨"},
            {"code": "2492", "name": "華新科"}
        ]
    },
    {
        "id": "finance",
        "name": "金控與銀行權值艦隊",
        "icon": "🏦",
        "leader_anchor": "2881",  # 富邦金
        "members": [
            {"code": "2881", "name": "富邦金"},
            {"code": "2882", "name": "國泰金"},
            {"code": "2885", "name": "元大金"},
            {"code": "2891", "name": "中信金"},
            {"code": "2884", "name": "玉山金"},
            {"code": "2880", "name": "華南金"},
            {"code": "2883", "name": "凱基金"},
            {"code": "2890", "name": "永豐金"},
            {"code": "2892", "name": "第一金"},
            {"code": "2887", "name": "台新金"},
            {"code": "2801", "name": "彰銀"}
        ]
    }
]

def scan_sector_spillover_candidates(
    fleets: Optional[List[Dict[str, Any]]] = None,
    min_corr: float = 60.0,
    force_refresh: bool = False
) -> List[Dict[str, Any]]:
    """
    掃描全市場核心族群艦隊，動態計算領頭大哥與接棒小弟的動能剪刀差與技術安全位階
    """
    if fleets is None:
        fleets = SECTOR_FLEETS

    # 盤中預先並行載入所有族群個股即時快取
    all_members = []
    for f in fleets:
        all_members.extend(f.get('members', []))
    rt_quotes = {}
    try:
        rt_quotes = batch_fetch_realtime_quotes(all_members)
    except Exception:
        pass

    results = []
    for fleet in fleets:
        f_id = fleet['id']
        f_name = fleet['name']
        f_icon = fleet['icon']
        anchor = fleet.get('leader_anchor', '')
        members = fleet['members']

        member_data = {}
        for m in members:
            code = m['code']
            df, _ = fetch_stock_kline(code, period="6mo", force_refresh=force_refresh, realtime_quote=rt_quotes.get(code))
            if df is not None and len(df) >= 20:
                last_c = float(df['Close'].iloc[-1])
                prev_c = float(df['Close'].iloc[-2]) if len(df) >= 2 else last_c
                chg = round(last_c - prev_c, 2)
                chg_pct = round((chg / prev_c) * 100, 2) if prev_c > 0 else 0.0

                idx_5 = max(0, len(df) - 6)
                c_5d_ago = float(df['Close'].iloc[idx_5])
                pct_5d = round(((last_c - c_5d_ago) / c_5d_ago) * 100, 2) if c_5d_ago > 0 else 0.0

                member_data[code] = {
                    "code": code,
                    "name": m['name'],
                    "df": df,
                    "close": last_c,
                    "change": chg,
                    "change_pct": chg_pct,
                    "pct_5d": pct_5d
                }

        if len(member_data) < 2:
            continue

        # 判定領頭大哥 (Leader)：優先考量今日漲幅顯著 (>1.0%) 且 5 日動能最強者，若皆微幅波動則以指定 anchor 優先
        sorted_by_today = sorted(member_data.values(), key=lambda x: (x['change_pct'], x['pct_5d']), reverse=True)
        top_today = sorted_by_today[0]

        if top_today['change_pct'] >= 1.0 or anchor not in member_data:
            leader = top_today
        else:
            leader = member_data[anchor]

        leader_code = leader['code']
        leader_df = leader['df']

        followers = []
        for code, m_info in member_data.items():
            if code == leader_code:
                continue

            f_df = m_info['df']
            # 動能剪刀差：大哥5日動能 - 小弟5日動能
            spillover_gap = round(leader['pct_5d'] - m_info['pct_5d'], 2)

            if spillover_gap < 1.0:
                continue

            # 計算與大哥的幾何走勢相關度 (最近 40 根 K 棒)
            merged = pd.merge(
                f_df[['Date', 'Close']],
                leader_df[['Date', 'Close']],
                on='Date',
                suffixes=('_fol', '_ldr')
            ).dropna().tail(40)

            if len(merged) < 15:
                continue

            corr_with_ldr = float(merged['Close_fol'].corr(merged['Close_ldr']))
            corr_with_ldr = 0.0 if np.isnan(corr_with_ldr) else round(corr_with_ldr * 100, 1)

            if corr_with_ldr < min_corr:
                continue

            last_c = m_info['close']
            sma5 = float(f_df['Close'].rolling(5).mean().iloc[-1])
            sma20 = float(f_df['Close'].rolling(20).mean().iloc[-1])
            low_20 = float(f_df['Low'].tail(20).min())

            is_struct_safe = (last_c >= sma20 * 0.965) and (last_c >= low_20 * 1.01)

            try:
                points, _, _, _ = calculate_turning_points(f_df, ma_period=5)
                trend = analyze_trend(f_df, points)
                signals_dict, _ = detect_signals(f_df, trend)
                safety_rating = signals_dict.get('safety_rating', '🟢 安全首選')
                safety_reasons = signals_dict.get('safety_reasons', [])
                chili_cnt = signals_dict.get('chili_count', 1)
                iron_man = bool(signals_dict.get('iron_man', False))
            except Exception:
                safety_rating = '🟢 安全首選' if is_struct_safe else '🟡 警訊注意'
                safety_reasons = [] if is_struct_safe else ["結構偏弱未達安全標準"]
                chili_cnt = 1
                iron_man = False
                signals_dict = {}

            cur_sma5 = float(f_df['Close'].rolling(5).mean().iloc[-1])
            prev_sma5 = float(f_df['Close'].rolling(5).mean().iloc[-2]) if len(f_df) > 1 else cur_sma5
            is_5ma_rising = cur_sma5 >= prev_sma5
            above_5ma = last_c >= cur_sma5

            # 族群接棒小弟安全評級精確分流：
            # 1. 致命空頭 (跌破前低底底低、嚴重空排破線)：嚴格判定 🔴 命中淘汰
            # 2. 結構安全 (守穩月線 20MA 且未破 20 日低點)：
            #    - 若已站上 5MA 或股價在月線之上：判定 🟢 安全接棒 (如台塑、廣達、聯電、元大金)
            #    - 若仍在均線下方測線震盪：判定 🟡 守線觀察
            raw_safety = signals_dict.get('safety_rating', '🟢 安全首選')
            if ("淘汰" in raw_safety or "嚴禁" in raw_safety) or not is_struct_safe:
                safety_rating = '🔴 命中淘汰'
            elif is_struct_safe:
                if above_5ma or last_c >= sma20 or "安全首選" in raw_safety:
                    safety_rating = '🟢 安全接棒'
                else:
                    safety_rating = '🟡 守線觀察'
            else:
                safety_rating = '🔴 命中淘汰'

            catchup_target = round(last_c * (1 + spillover_gap / 100), 2)
            stop_loss = round(max(low_20, last_c * 0.95), 2)
            if stop_loss >= last_c:
                stop_loss = round(last_c * 0.95, 2)
            risk_pct = round(((last_c - stop_loss) / last_c) * 100, 1)

            followers.append({
                "code": code,
                "name": m_info['name'],
                "close": last_c,
                "change": m_info['change'],
                "change_pct": m_info['change_pct'],
                "pct_5d": m_info['pct_5d'],
                "spillover_gap": spillover_gap,
                "corr_with_leader": corr_with_ldr,
                "sma5": round(sma5, 2),
                "sma20": round(sma20, 2),
                "catchup_target": catchup_target,
                "stop_loss": stop_loss,
                "risk_pct": risk_pct,
                "is_struct_safe": is_struct_safe,
                "safety_rating": safety_rating,
                "safety_reasons": safety_reasons,
                "chili_count": chili_cnt,
                "is_5ma_rising": is_5ma_rising,
                "above_5ma": above_5ma,
                "iron_man": iron_man,
                "signals_dict": signals_dict
            })

        if followers:
            followers.sort(key=lambda x: (
                0 if "安全首選" in x['safety_rating'] else (1 if "警訊" in x['safety_rating'] else 2),
                -x['spillover_gap']
            ))

            fleet_score = (leader['change_pct'] * 10) + (10 if "安全首選" in followers[0]['safety_rating'] else 0)

            results.append({
                "fleet_id": f_id,
                "fleet_name": f_name,
                "fleet_icon": f_icon,
                "leader": {
                    "code": leader['code'],
                    "name": leader['name'],
                    "close": leader['close'],
                    "change": leader['change'],
                    "change_pct": leader['change_pct'],
                    "pct_5d": leader['pct_5d'],
                    "is_active": leader['change_pct'] >= 1.0 or leader['pct_5d'] >= 2.0
                },
                "followers": followers,
                "fleet_score": fleet_score
            })

    results.sort(key=lambda x: x['fleet_score'], reverse=True)
    return results

def create_pair_sync_comparison_figure(
    df_follower: pd.DataFrame,
    df_leader: pd.DataFrame,
    follower_name: str,
    follower_code: str,
    leader_name: str,
    leader_code: str,
    follower_data: Dict[str, Any],
    lookback_bars: int = 50
) -> Optional[go.Figure]:
    """
    建立【小弟 vs 大哥】歸一化相對走勢與補漲剪刀差對照圖表
    """
    if df_follower is None or df_leader is None or len(df_follower) < 20 or len(df_leader) < 20:
        return None

    merged = pd.merge(
        df_follower[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']],
        df_leader[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']],
        on='Date',
        suffixes=('_fol', '_ldr')
    ).sort_values('Date').dropna().reset_index(drop=True)

    if len(merged) < 15:
        return None

    sub = merged.tail(lookback_bars).copy().reset_index(drop=True)

    # 歸一化累計漲跌幅 (%)
    f_base = sub['Close_fol'].iloc[0]
    l_base = sub['Close_ldr'].iloc[0]

    sub['Follower_Pct'] = ((sub['Close_fol'] - f_base) / f_base) * 100
    sub['Leader_Pct'] = ((sub['Close_ldr'] - l_base) / l_base) * 100

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.56, 0.44],
        subplot_titles=(
            f"📈 累積走勢對照 (👑 大哥: {leader_name} vs 🎯 小弟: {follower_name}) · 剪刀差 {follower_data.get('spillover_gap', 0):+}%",
            f"📊 {follower_name} ({follower_code}) 日 K 線與防守均線"
        )
    )

    # Row 1: 大哥曲線 (珊瑚紅) vs 小弟曲線 (青藍)
    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Leader_Pct'],
        name=f"👑 大哥 {leader_name} ({leader_code})",
        line=dict(color="#FF6B6B", width=2.8),
        hovertemplate=f"大哥 {leader_name}: " + "%{y:+.2f}%<extra></extra>"
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Follower_Pct'],
        name=f"🎯 小弟 {follower_name} ({follower_code})",
        line=dict(color="#13C2C2", width=2.8),
        hovertemplate=f"小弟 {follower_name}: " + "%{y:+.2f}%<extra></extra>"
    ), row=1, col=1)

    # 填充剪刀差區間
    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Leader_Pct'],
        fill=None, mode='lines', line=dict(color='rgba(0,0,0,0)'),
        showlegend=False, hoverinfo='skip'
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['Follower_Pct'],
        fill='tonexty', mode='lines',
        fillcolor='rgba(19, 194, 194, 0.15)',
        line=dict(color='rgba(0,0,0,0)'),
        name="外溢補漲剪刀差空間",
        hoverinfo='skip'
    ), row=1, col=1)

    # Row 2: 小弟 K 線與均線
    sub['SMA_5'] = sub['Close_fol'].rolling(5).mean()
    sub['SMA_20'] = sub['Close_fol'].rolling(20).mean()

    fig.add_trace(go.Candlestick(
        x=sub['Date'],
        open=sub['Open_fol'], high=sub['High_fol'],
        low=sub['Low_fol'], close=sub['Close_fol'],
        name=f"{follower_name} K線",
        increasing_line_color='#FF4D4F', increasing_fillcolor='#FF4D4F',
        decreasing_line_color='#2F9E44', decreasing_fillcolor='#2F9E44',
        showlegend=False
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['SMA_5'],
        name="5MA 操盤線", line=dict(color="#1890FF", width=1.5)
    ), row=2, col=1)

    fig.add_trace(go.Scatter(
        x=sub['Date'], y=sub['SMA_20'],
        name="20MA 月線", line=dict(color="#E0A82E", width=1.5)
    ), row=2, col=1)

    # 補漲目標價與防守價虛線
    target_val = follower_data.get('catchup_target')
    stop_val = follower_data.get('stop_loss')
    if target_val:
        fig.add_hline(
            y=target_val, line_dash="dash", line_color="#52C41A", line_width=1.2,
            annotation_text=f"補漲目標: {target_val}", annotation_position="top right",
            annotation_font_color="#52C41A", row=2, col=1
        )
    if stop_val:
        fig.add_hline(
            y=stop_val, line_dash="dash", line_color="#FF4D4F", line_width=1.2,
            annotation_text=f"防守停損: {stop_val}", annotation_position="bottom right",
            annotation_font_color="#FF4D4F", row=2, col=1
        )

    # 調整標題位置與字體，向上抬升避免與圖表邊界擠壓
    if len(fig.layout.annotations) > 0:
        fig.layout.annotations[0].update(y=1.05, font=dict(size=13, color="#E2E8F0"))
    if len(fig.layout.annotations) > 1:
        fig.layout.annotations[1].update(font=dict(size=13, color="#E2E8F0"))

    fig.update_layout(
        height=680,
        margin=dict(l=20, r=75, t=55, b=65),
        template="plotly_dark",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.09,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(0,0,0,0)",
            font=dict(size=12, color="#94A3B8")
        ),
        hovermode="x unified"
    )
    fig.update_xaxes(rangeslider_visible=False)
    return fig

