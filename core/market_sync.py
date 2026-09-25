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

from core.data_fetcher import fetch_stock_kline
from core.screener import load_stock_list

_MKT_CACHE = {"df": None, "info": None, "timestamp": None}

def get_market_benchmark(period: str = "3mo") -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
    """獲取大盤加權指數 K 線與行情數據 (帶短期快取)"""
    global _MKT_CACHE
    now = pd.Timestamp.now()
    if _MKT_CACHE["df"] is not None and _MKT_CACHE["timestamp"] is not None:
        if (now - _MKT_CACHE["timestamp"]).total_seconds() < 300:
            return _MKT_CACHE["df"].copy(), _MKT_CACHE["info"]

    df_mkt, info_mkt = fetch_stock_kline("^TWII", period=period)
    if df_mkt is not None and not df_mkt.empty:
        _MKT_CACHE["df"] = df_mkt
        _MKT_CACHE["info"] = info_mkt
        _MKT_CACHE["timestamp"] = now
        return df_mkt.copy(), info_mkt
    return None, None

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

    return {
        "code": stock_info.get("code", ""),
        "name": stock_info.get("name", ""),
        "industry": stock_info.get("industry", ""),
        "close": last_c,
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
        "is_struct_safe": is_struct_safe
    }

def scan_market_sync_candidates(
    stock_list: Optional[List[Dict[str, Any]]] = None,
    filter_mode: str = "lagging_only", # 'lagging_only' / 'all_sync' / 'all'
    min_shape_corr: float = 65.0,
    top_n: int = 20
) -> List[Dict[str, Any]]:
    """
    掃描全市場或指定股池，比對與大盤同步之滯後補漲股
    """
    df_mkt, info_mkt = get_market_benchmark(period="3mo")
    if df_mkt is None or df_mkt.empty:
        return []

    if stock_list is None:
        stock_list = load_stock_list()

    candidates = []
    for s in stock_list:
        code = s['code']
        df_s, info_s = fetch_stock_kline(code, period="3mo")
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

    # 排序：強烈滯後優先，其次按綜合評分
    candidates.sort(key=lambda x: (x["priority"], -x["sync_score"], -x["lag_gap_5d"]))
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

    fig.update_layout(
        height=680,
        margin=dict(l=15, r=75, t=40, b=15),
        template="plotly_dark",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.01),
        hovermode="x unified"
    )
    fig.update_xaxes(rangeslider_visible=False)
    return fig
