# -*- coding: utf-8 -*-
"""
跳空缺口偵測與可視化引擎 (Gap Detector & Visualizer)
依據朱家泓技術分析與日本蠟燭圖經典形態學：
1. 自動識別歷史走勢中尚未被完全封閉的「向上跳空缺口 (多方支撐)」與「向下跳空缺口 (空方壓力)」
2. 計算部分回補狀態與剩餘真空反壓/防守區間
3. 即時預警股價是否正逼近重大套牢跳空缺口下緣
4. 在 Plotly 主圖上繪製半透明缺口陰影色帶與標註
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional

def detect_unfilled_gaps(df: pd.DataFrame, min_gap_pct: float = 0.8, lookback_bars: int = 120) -> Dict[str, Any]:
    """
    全方位檢測未回補跳空缺口
    """
    empty_res = {
        "bearish_gaps": [],
        "bullish_gaps": [],
        "nearest_overhead_gap": None,
        "nearest_underlying_gap": None,
        "is_approaching_overhead_gap": False,
        "warning_message": "",
        "summary_desc": ""
    }

    if df is None or len(df) < 5:
        return empty_res

    df = df.copy().reset_index(drop=True)
    n = len(df)
    c_today = float(df.iloc[-1]['Close'])
    latest_date = df.iloc[-1]['Date']

    start_idx = max(1, n - lookback_bars)
    
    bearish_gaps = []
    bullish_gaps = []

    for i in range(start_idx, n):
        prev_low = float(df.loc[i-1, 'Low'])
        prev_high = float(df.loc[i-1, 'High'])
        curr_low = float(df.loc[i, 'Low'])
        curr_high = float(df.loc[i, 'High'])
        gap_date = df.loc[i, 'Date']

        # ----------------------------------------------------
        # 1. 空方跳空缺口 (向下跳空：前一日低點 > 當日高點)
        # ----------------------------------------------------
        if prev_low > curr_high:
            gap_size = prev_low - curr_high
            gap_pct = (gap_size / prev_low) * 100.0

            if gap_pct >= min_gap_pct:
                # 檢驗該缺口後續是否被完全封閉或部分回補
                if i < n - 1:
                    sub_highs = df.loc[i+1:, 'High']
                    max_sub_high = float(sub_highs.max())
                else:
                    max_sub_high = 0.0

                # 若後續有任何一日的高點碰觸或超越前一日低點，則缺口已被完全回補
                if max_sub_high < prev_low:
                    # 未完全回補
                    is_partially = (max_sub_high > curr_high)
                    rem_bottom = max(curr_high, max_sub_high)
                    rem_top = prev_low
                    dist_pct = ((rem_bottom - c_today) / c_today) * 100.0

                    bearish_gaps.append({
                        "type": "bearish",
                        "date": gap_date,
                        "date_str": gap_date.strftime('%Y/%m/%d') if hasattr(gap_date, 'strftime') else str(gap_date)[:10],
                        "orig_bottom": round(curr_high, 2),
                        "orig_top": round(prev_low, 2),
                        "rem_bottom": round(rem_bottom, 2),
                        "rem_top": round(rem_top, 2),
                        "gap_size": round(rem_top - rem_bottom, 2),
                        "orig_gap_pct": round(gap_pct, 2),
                        "is_partially_filled": is_partially,
                        "distance_pct": round(dist_pct, 2),
                        "label": f"🕳️ 空方缺口反壓 ({rem_bottom:.1f}~{rem_top:.1f}元)"
                    })

        # ----------------------------------------------------
        # 2. 多方跳空缺口 (向上跳空：當日低點 > 前一日高點)
        # ----------------------------------------------------
        if curr_low > prev_high:
            gap_size = curr_low - prev_high
            gap_pct = (gap_size / prev_high) * 100.0

            if gap_pct >= min_gap_pct:
                # 檢驗該缺口後續是否被完全封閉或部分回補
                if i < n - 1:
                    sub_lows = df.loc[i+1:, 'Low']
                    min_sub_low = float(sub_lows.min())
                else:
                    min_sub_low = 999999.0

                if min_sub_low > prev_high:
                    # 未完全回補
                    is_partially = (min_sub_low < curr_low)
                    rem_top = min(curr_low, min_sub_low)
                    rem_bottom = prev_high
                    dist_pct = ((c_today - rem_top) / c_today) * 100.0

                    bullish_gaps.append({
                        "type": "bullish",
                        "date": gap_date,
                        "date_str": gap_date.strftime('%Y/%m/%d') if hasattr(gap_date, 'strftime') else str(gap_date)[:10],
                        "orig_bottom": round(prev_high, 2),
                        "orig_top": round(curr_low, 2),
                        "rem_bottom": round(rem_bottom, 2),
                        "rem_top": round(rem_top, 2),
                        "gap_size": round(rem_top - rem_bottom, 2),
                        "orig_gap_pct": round(gap_pct, 2),
                        "is_partially_filled": is_partially,
                        "distance_pct": round(dist_pct, 2),
                        "label": f"🛡️ 多方缺口支撐 ({rem_bottom:.1f}~{rem_top:.1f}元)"
                    })

    # 排序：空方缺口依下緣由低到高（最接近現價的在最前面）
    bearish_gaps.sort(key=lambda g: g['rem_bottom'])
    # 多方缺口依上緣由高到低（最接近現價的在最前面）
    bullish_gaps.sort(key=lambda g: g['rem_top'], reverse=True)

    # 尋找現價正上方的最近空方缺口
    overhead_candidates = [g for g in bearish_gaps if g['rem_bottom'] >= c_today * 0.99]
    nearest_overhead = overhead_candidates[0] if overhead_candidates else None

    # 尋找現價正下方的最近多方缺口
    underlying_candidates = [g for g in bullish_gaps if g['rem_top'] <= c_today * 1.01]
    nearest_underlying = underlying_candidates[0] if underlying_candidates else None

    is_approaching = False
    warning_msg = ""
    summary_parts = []

    if nearest_overhead:
        dist = nearest_overhead['distance_pct']
        if 0 <= dist <= 3.0:
            is_approaching = True
            warning_msg = (
                f"🚨 做多大忌警訊：股價現價 ({c_today:.2f}元) 正逼近 {nearest_overhead['date_str']} "
                f"重大空方跳空缺口下緣 ({nearest_overhead['rem_bottom']:.2f} 元，差距僅 +{dist:.1f}%)！"
                f"缺口區間為 {nearest_overhead['rem_bottom']:.2f}~{nearest_overhead['rem_top']:.2f} 元，上方解套賣壓沈重，嚴防逢高摜回！"
            )
            summary_parts.append(f"上方重大空方缺口反壓 ({nearest_overhead['rem_bottom']:.1f}~{nearest_overhead['rem_top']:.1f}元)")
        else:
            summary_parts.append(f"上方空方缺口壓力: {nearest_overhead['rem_bottom']:.1f}元 (距 +{dist:.1f}%)")

    if nearest_underlying:
        dist_u = nearest_underlying['distance_pct']
        summary_parts.append(f"下方多方缺口支撐: {nearest_underlying['rem_top']:.1f}元 (距 -{dist_u:.1f}%)")

    summary_desc = " | ".join(summary_parts) if summary_parts else "近期無重大未補跳空缺口"

    return {
        "bearish_gaps": bearish_gaps,
        "bullish_gaps": bullish_gaps,
        "nearest_overhead_gap": nearest_overhead,
        "nearest_underlying_gap": nearest_underlying,
        "is_approaching_overhead_gap": is_approaching,
        "warning_message": warning_msg,
        "summary_desc": summary_desc
    }

def apply_gaps_to_figure(fig: go.Figure, gaps_data: Dict[str, Any], df: pd.DataFrame, max_draw: int = 4) -> go.Figure:
    """
    在 Plotly 主圖上以半透明陰影色帶 (Shaded Region) 繪製未回補跳空缺口
    """
    if not gaps_data or not fig or df is None or df.empty:
        return fig

    last_dt = df.iloc[-1]['Date']
    
    # 限制繪製數量，避免歷史缺口過多造成視覺混亂
    bearish_to_draw = gaps_data.get("bearish_gaps", [])[:max_draw]
    bullish_to_draw = gaps_data.get("bullish_gaps", [])[:max_draw]

    # 1. 繪製空方缺口 (紫色/橘紅半透明帶，代表強大阻力天花板)
    for g in bearish_to_draw:
        y0 = g['rem_bottom']
        y1 = g['rem_top']
        x0 = g['date']
        x1 = last_dt
        
        # 陰影矩形色帶
        fig.add_shape(
            type="rect",
            x0=x0, y0=y0,
            x1=x1, y1=y1,
            fillcolor="rgba(168, 85, 247, 0.15)", # 半透明紫色
            line=dict(color="rgba(168, 85, 247, 0.65)", width=1.2, dash="dash"),
            xref="x", yref="y",
            row=1, col=1
        )
        
        # 右側標註徽章
        fig.add_annotation(
            x=x1,
            y=(y0 + y1) / 2.0,
            text=f"🕳️ 空方缺口反壓 {y0:.1f}~{y1:.1f}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.2,
            arrowcolor="#A855F7",
            ax=45,
            ay=0,
            font=dict(size=10, color="#FFFFFF", family="Arial Black"),
            bgcolor="rgba(147, 51, 234, 0.88)",
            bordercolor="#C084FC",
            borderwidth=1.2,
            borderpad=3,
            xref="x", yref="y",
            row=1, col=1
        )

    # 2. 繪製多方缺口 (翠綠色半透明帶，代表強大支撐地板)
    for g in bullish_to_draw:
        y0 = g['rem_bottom']
        y1 = g['rem_top']
        x0 = g['date']
        x1 = last_dt
        
        fig.add_shape(
            type="rect",
            x0=x0, y0=y0,
            x1=x1, y1=y1,
            fillcolor="rgba(16, 185, 129, 0.14)", # 半透明翠綠
            line=dict(color="rgba(16, 185, 129, 0.65)", width=1.2, dash="dash"),
            xref="x", yref="y",
            row=1, col=1
        )
        
        fig.add_annotation(
            x=x1,
            y=(y0 + y1) / 2.0,
            text=f"🛡️ 多方缺口支撐 {y0:.1f}~{y1:.1f}",
            showarrow=True,
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1.2,
            arrowcolor="#10B981",
            ax=45,
            ay=0,
            font=dict(size=10, color="#FFFFFF", family="Arial Black"),
            bgcolor="rgba(5, 150, 105, 0.88)",
            bordercolor="#34D399",
            borderwidth=1.2,
            borderpad=3,
            xref="x", yref="y",
            row=1, col=1
        )

    return fig
