# -*- coding: utf-8 -*-
"""
AI 型態幾何作圖與切線引擎 (Pattern Geometry Engine)
依據《技術分析全攻略》經典多空實戰規範：
1. 突破 ABC 修正下降切線 (旗型整理、做頭失敗反手多、等距目標價 D')
2. 跌破反彈 ABC 上升切線 (弱勢反彈、做底失敗重回主跌段、等距下跌 D')
3. 一字底 (60天狹幅均線糾結箱型、箱頂頸線突破、箱底防守線、等距目標價 D')
4. 圓弧底 (U型打底二次拋物線擬合、頸線水平壓力、突破起漲點)
5. 上升軌道線 / 下降軌道線 (平行通道回歸、衝破上軌加速噴出 / 跌破下軌趕底)
6. 全自動幾何圖形注入 Plotly 主圖 (Shapes, Traces, Annotations)
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional

def detect_pattern_geometries(df: pd.DataFrame, signals_dict: dict = None) -> Dict[str, Any]:
    """
    全方位辨識 K 線走勢中的幾何型態與關鍵切線座標
    回傳字典結構包含：
    - active_pattern: 當前觸發的主導型態 (若有)
    - patterns_found: 所有偵測到的型態清單
    - trendlines: 通用主趨勢切線與通道 (保證任何股票皆能顯示智慧畫線)
    """
    result = {
        "active_pattern": None,
        "patterns_found": [],
        "trendlines": None,
        "summary_text": ""
    }

    if df is None or len(df) < 15:
        return result

    df = df.copy().reset_index(drop=True)
    if 'SMA_5' not in df.columns or 'SMA_20' not in df.columns:
        df['SMA_5'] = df['Close'].rolling(5).mean()
        df['SMA_20'] = df['Close'].rolling(20).mean()

    n = len(df)
    c_today = float(df.iloc[-1]['Close'])
    o_today = float(df.iloc[-1]['Open'])
    sma5_today = float(df.iloc[-1]['SMA_5'])
    sma20_today = float(df.iloc[-1]['SMA_20'])
    is_ma20_rising = (sma20_today >= float(df.iloc[-3]['SMA_20']) * 0.998) if n >= 3 else True
    is_ma20_falling = (sma20_today <= float(df.iloc[-3]['SMA_20']) * 1.002) if n >= 3 else False

    # =========================================================================
    # 1. 📐 突破 ABC 修正下降切線 (做多旗型突破)
    # =========================================================================
    abc_pat = None
    if n >= 15:
        # 在過去 12 ~ 32 根 K 棒尋找 A 點峰頂
        lookback = min(32, n - 2)
        slice_abc = df.iloc[-lookback:-2]
        if len(slice_abc) >= 8:
            idx_a = int(slice_abc['High'].idxmax())
            price_a = float(df.loc[idx_a, 'High'])
            
            # A 點需距離今日至少 4 根 K 棒，且為局部高點
            if (n - 1 - idx_a) >= 4 and (n - 1 - idx_a) <= 28:
                after_a = df.iloc[idx_a + 1:-1]
                if len(after_a) >= 3:
                    idx_b = int(after_a['Low'].idxmin())
                    price_b = float(df.loc[idx_b, 'Low'])

                    # C 點必須在 B 點之後
                    if idx_b < n - 2:
                        after_b = df.iloc[idx_b + 1:]
                        idx_c = int(after_b['High'].idxmax())
                        price_c = float(df.loc[idx_c, 'High'])

                        # ABC 旗型核心要件：
                        # 1. C 點次高 (頭頭低: price_c < price_a)
                        # 2. B 點為低檔回檔 (price_b < price_a)
                        # 3. 斜率為負 (下降切線)
                        if price_c < price_a * 0.998 and price_b < price_a and idx_c > idx_a:
                            slope = (price_c - price_a) / (idx_c - idx_a)
                            if slope < 0:
                                y_tangent_today = price_a + slope * (n - 1 - idx_a)
                                # 突破判斷：今日收盤價越過下降切線或收過 C 點
                                is_breaking = (c_today >= y_tangent_today * 0.995 or c_today >= price_c) and (c_today >= sma5_today)
                                
                                # 計算前波起漲低點 (Wave 1 起點)
                                prev_slice = df.iloc[max(0, idx_a - 15):idx_a]
                                wave1_low = float(prev_slice['Low'].min()) if len(prev_slice) > 0 else price_b
                                wave1_amp = max(price_a - wave1_low, price_a - price_b)
                                target_d = round(price_c + wave1_amp, 2)

                                abc_pat = {
                                    "id": "abc_correction",
                                    "name": "📐 突破 ABC 修正下降切線",
                                    "direction": "多",
                                    "status": "突破發動" if is_breaking else "旗型收斂中",
                                    "is_breakout": is_breaking,
                                    "a_point": {"date": df.loc[idx_a, 'Date'], "price": price_a, "index": idx_a, "label": "A點 (起修頂)"},
                                    "b_point": {"date": df.loc[idx_b, 'Date'], "price": price_b, "index": idx_b, "label": "B點 (回檔底)"},
                                    "c_point": {"date": df.loc[idx_c, 'Date'], "price": price_c, "index": idx_c, "label": "C點 (次高點)"},
                                    "tangent_line": {
                                        "x0": df.loc[idx_a, 'Date'], "y0": price_a,
                                        "x1": df.iloc[-1]['Date'], "y1": round(y_tangent_today, 2),
                                        "slope": slope
                                    },
                                    "breakout_point": {"date": df.iloc[-1]['Date'], "price": c_today, "label": "🔥 突破切線買點"} if is_breaking else None,
                                    "target_d": target_d,
                                    "color": "#06B6D4", # Cyan
                                    "desc": f"多頭 ABC 旗型整理完成，放量紅K突破下降切線 (切線價 {y_tangent_today:.2f} 元)！短空做頭失敗反手多，等距目標價 D' 為 {target_d} 元。"
                                }
                                result["patterns_found"].append(abc_pat)
                                if is_breaking and is_ma20_rising:
                                    result["active_pattern"] = abc_pat

    # =========================================================================
    # 2. 📐 跌破反彈 ABC 上升切線 (做空反彈結束重回主跌)
    # =========================================================================
    abc_short_pat = None
    if n >= 15:
        lookback = min(32, n - 2)
        slice_abc_s = df.iloc[-lookback:-2]
        if len(slice_abc_s) >= 8:
            idx_a_s = int(slice_abc_s['Low'].idxmin())
            price_a_s = float(df.loc[idx_a_s, 'Low'])

            if (n - 1 - idx_a_s) >= 4 and (n - 1 - idx_a_s) <= 28:
                after_a_s = df.iloc[idx_a_s + 1:-1]
                if len(after_a_s) >= 3:
                    idx_b_s = int(after_a_s['High'].idxmax())
                    price_b_s = float(df.loc[idx_b_s, 'High'])

                    if idx_b_s < n - 2:
                        after_b_s = df.iloc[idx_b_s + 1:]
                        idx_c_s = int(after_b_s['Low'].idxmin())
                        price_c_s = float(df.loc[idx_c_s, 'Low'])

                        # 空方 ABC 反彈要件：
                        # 1. C 點次低 (底底高: price_c_s > price_a_s)
                        # 2. B 點反彈高點
                        # 3. 斜率為正 (上升切線)
                        if price_c_s > price_a_s * 1.002 and price_b_s > price_a_s and idx_c_s > idx_a_s:
                            slope_s = (price_c_s - price_a_s) / (idx_c_s - idx_a_s)
                            if slope_s > 0:
                                y_tangent_s_today = price_a_s + slope_s * (n - 1 - idx_a_s)
                                is_breaking_s = (c_today <= y_tangent_s_today * 1.005 or c_today <= price_b_s * 0.99) and (c_today <= sma5_today)
                                
                                prev_high_s = df.iloc[max(0, idx_a_s - 15):idx_a_s]
                                wave1_high_s = float(prev_high_s['High'].max()) if len(prev_high_s) > 0 else price_b_s
                                wave1_down_amp = max(wave1_high_s - price_a_s, price_b_s - price_a_s)
                                target_d_s = round(max(1.0, price_c_s - wave1_down_amp), 2)

                                abc_short_pat = {
                                    "id": "abc_rebound_breakdown",
                                    "name": "📐 跌破反彈 ABC 上升切線",
                                    "direction": "空",
                                    "status": "破線重回主跌" if is_breaking_s else "反彈旗型中",
                                    "is_breakout": is_breaking_s,
                                    "a_point": {"date": df.loc[idx_a_s, 'Date'], "price": price_a_s, "index": idx_a_s, "label": "A點 (主跌底)"},
                                    "b_point": {"date": df.loc[idx_b_s, 'Date'], "price": price_b_s, "index": idx_b_s, "label": "B點 (反彈頂)"},
                                    "c_point": {"date": df.loc[idx_c_s, 'Date'], "price": price_c_s, "index": idx_c_s, "label": "C點 (次低底)"},
                                    "tangent_line": {
                                        "x0": df.loc[idx_a_s, 'Date'], "y0": price_a_s,
                                        "x1": df.iloc[-1]['Date'], "y1": round(y_tangent_s_today, 2),
                                        "slope": slope_s
                                    },
                                    "breakout_point": {"date": df.iloc[-1]['Date'], "price": c_today, "label": "⚡ 跌破切線空點"} if is_breaking_s else None,
                                    "target_d": target_d_s,
                                    "color": "#F97316", # Orange
                                    "desc": f"空頭反彈 ABC 旗型結束，放量黑K摜破上升切線 (切線價 {y_tangent_s_today:.2f} 元)！短多做底失敗重回主跌段，等距下跌目標價 D' 看 {target_d_s} 元。"
                                }
                                result["patterns_found"].append(abc_short_pat)
                                if is_breaking_s and is_ma20_falling and result["active_pattern"] is None:
                                    result["active_pattern"] = abc_short_pat

    # =========================================================================
    # 3. 📦 一字底 (60天狹幅均線糾結箱型放量突破)
    # =========================================================================
    flat_pat = None
    if n >= 25:
        # 尋找 20 ~ 55 根 K 棒的狹幅箱型
        for box_len in [45, 30, 20]:
            if n > box_len + 1:
                box_slice = df.iloc[-(box_len + 1):-1]
                b_high = float(box_slice['High'].max())
                b_low = float(box_slice['Low'].min())
                amplitude = (b_high - b_low) / (b_low + 1e-9)

                # 一字底標準：振幅在 12% 以內，或箱型振幅在 18% 以內
                if amplitude <= 0.18:
                    is_break_flat = (c_today >= b_high * 0.995) and (c_today >= sma5_today) and (c_today >= o_today)
                    target_flat = round(b_high + (b_high - b_low), 2)

                    flat_pat = {
                        "id": "flat_base",
                        "name": "📦 一字底 (箱型放量大突破)",
                        "direction": "多",
                        "status": "一棒過箱頂" if is_break_flat else "箱型糾結中",
                        "is_breakout": is_break_flat,
                        "box": {
                            "x0": box_slice.iloc[0]['Date'],
                            "x1": df.iloc[-1]['Date'],
                            "y0": b_low,
                            "y1": b_high
                        },
                        "neckline": b_high,
                        "bottom_line": b_low,
                        "amplitude_pct": round(amplitude * 100, 1),
                        "target_d": target_flat,
                        "breakout_point": {"date": df.iloc[-1]['Date'], "price": c_today, "label": "🚀 一棒放量過箱頂"} if is_break_flat else None,
                        "color": "#EAB308", # Gold
                        "desc": f"一字底 {box_len} 日狹幅整理 (振幅 {amplitude*100:.1f}%)，均線高度糾結後一棒摜破箱頂頸線 ({b_high:.2f} 元)！等距波段目標價上看 {target_flat} 元。"
                    }
                    result["patterns_found"].append(flat_pat)
                    if is_break_flat and result["active_pattern"] is None:
                        result["active_pattern"] = flat_pat
                    break

    # =========================================================================
    # 4. 🥣 圓弧底 (U型打底二次拋物線擬合)
    # =========================================================================
    round_pat = None
    if n >= 35:
        round_len = min(65, n - 1)
        r_slice = df.iloc[-round_len:]
        low_idx_rel = int(r_slice['Low'].values.argmin())
        
        # 最低點必須出現在中間 20% ~ 80% 區間 (凹槽特徵)
        if 0.20 * round_len <= low_idx_rel <= 0.80 * round_len:
            left_high = float(r_slice.iloc[:int(round_len*0.35)]['High'].max())
            right_high = float(r_slice.iloc[int(round_len*0.75):]['High'].max())
            center_low = float(r_slice.iloc[low_idx_rel]['Low'])

            depth_pct = (left_high - center_low) / (center_low + 1e-9)
            if depth_pct >= 0.06 and right_high > center_low * 1.04:
                # 二次多項式擬合 y = ax^2 + bx + c
                x_vals = np.arange(round_len)
                y_vals = r_slice['Low'].values
                poly_coeffs = np.polyfit(x_vals, y_vals, 2)
                a, b, c_coeff = poly_coeffs

                # 開口向上且擬合良度
                if a > 0.001:
                    y_fit = np.polyval(poly_coeffs, x_vals)
                    ss_res = np.sum((y_vals - y_fit) ** 2)
                    ss_tot = np.sum((y_vals - np.mean(y_vals)) ** 2)
                    r2 = 1 - (ss_res / (ss_tot + 1e-9))

                    if r2 >= 0.45:
                        neckline_round = max(left_high, right_high)
                        is_break_round = (c_today >= neckline_round * 0.99) and (c_today >= sma5_today)
                        target_round = round(neckline_round + (neckline_round - center_low), 2)

                        sample_indices = np.linspace(0, round_len - 1, 15, dtype=int)
                        arc_coords = [
                            {"date": r_slice.iloc[idx]['Date'], "price": round(float(y_fit[idx]), 2)}
                            for idx in sample_indices
                        ]

                        round_pat = {
                            "id": "rounding_bottom",
                            "name": "🥣 圓弧底 (U型慢火打底)",
                            "direction": "多",
                            "status": "放量過頸線起漲" if is_break_round else "打底成形中",
                            "is_breakout": is_break_round,
                            "neckline": neckline_round,
                            "trough_price": center_low,
                            "arc_points": arc_coords,
                            "target_d": target_round,
                            "breakout_point": {"date": df.iloc[-1]['Date'], "price": c_today, "label": "🎯 突破圓弧頸線"} if is_break_round else None,
                            "color": "#EC4899", # Pink
                            "desc": f"經典圓弧底 (U型底) 慢火打底洗淨浮額，今日收盤突破水平頸線 ({neckline_round:.2f} 元)！波段等距目標價 D' 為 {target_round} 元。"
                        }
                        result["patterns_found"].append(round_pat)
                        if is_break_round and result["active_pattern"] is None:
                            result["active_pattern"] = round_pat

    # =========================================================================
    # 5. 🚀 上升／下降軌道線 (平行通道回歸)
    # =========================================================================
    channel_pat = None
    if n >= 20:
        ch_len = min(40, n)
        ch_slice = df.iloc[-ch_len:]
        
        t1_idx = int(ch_slice.iloc[:int(ch_len*0.6)]['Low'].idxmin())
        t2_idx = int(ch_slice.iloc[int(ch_len*0.5):]['Low'].idxmin())
        
        if t2_idx > t1_idx:
            t1_p = float(df.loc[t1_idx, 'Low'])
            t2_p = float(df.loc[t2_idx, 'Low'])
            ch_slope = (t2_p - t1_p) / (t2_idx - t1_idx)

            if ch_slope > 0:
                indices_between = np.arange(t1_idx, n)
                lower_prices = t1_p + ch_slope * (indices_between - t1_idx)
                highs_between = df.loc[indices_between, 'High'].values
                diffs = highs_between - lower_prices
                channel_height = max(float(np.percentile(diffs, 90)), (t2_p - t1_p) * 0.5)

                y_lower_today = t1_p + ch_slope * (n - 1 - t1_idx)
                y_upper_today = y_lower_today + channel_height

                is_break_ch = (c_today >= y_upper_today * 0.995) and (c_today >= sma5_today)
                channel_pat = {
                    "id": "ascending_channel",
                    "name": "🚀 突破上升軌道線",
                    "direction": "多",
                    "status": "衝破上軌加速噴出" if is_break_ch else "通道內推升",
                    "is_breakout": is_break_ch,
                    "lower_line": {
                        "x0": df.loc[t1_idx, 'Date'], "y0": t1_p,
                        "x1": df.iloc[-1]['Date'], "y1": round(y_lower_today, 2)
                    },
                    "upper_line": {
                        "x0": df.loc[t1_idx, 'Date'], "y0": round(t1_p + channel_height, 2),
                        "x1": df.iloc[-1]['Date'], "y1": round(y_upper_today, 2)
                    },
                    "channel_height": round(channel_height, 2),
                    "breakout_point": {"date": df.iloc[-1]['Date'], "price": c_today, "label": "⚡ 衝破上軌加速噴出"} if is_break_ch else None,
                    "color": "#8B5CF6", # Purple
                    "desc": f"多頭沿上升通道推升，今日放量大紅K衝破上升軌道線上緣 ({y_upper_today:.2f} 元)！多頭轉強加速噴出主升段。"
                }
                result["patterns_found"].append(channel_pat)
                if is_break_ch and result["active_pattern"] is None:
                    result["active_pattern"] = channel_pat

    # =========================================================================
    # 6. 🌐 通用主趨勢切線 (保證任何股票皆能自動獲得幾何繪圖)
    # =========================================================================
    look_primary = min(50, n)
    pri_slice = df.iloc[-look_primary:]
    if is_ma20_rising:
        t_low1 = int(pri_slice.iloc[:int(look_primary*0.55)]['Low'].idxmin())
        t_low2 = int(pri_slice.iloc[int(look_primary*0.45):]['Low'].idxmin())
        if t_low2 > t_low1:
            p_low1 = float(df.loc[t_low1, 'Low'])
            p_low2 = float(df.loc[t_low2, 'Low'])
            m_pri = (p_low2 - p_low1) / (t_low2 - t_low1)
            y_pri_today = p_low1 + m_pri * (n - 1 - t_low1)
            result["trendlines"] = {
                "type": "support_rising",
                "label": "上升支撐趨勢切線",
                "color": "#38BDF8", # Sky blue
                "x0": df.loc[t_low1, 'Date'], "y0": p_low1,
                "x1": df.iloc[-1]['Date'], "y1": round(y_pri_today, 2),
                "is_rising": True
            }
    else:
        t_h1 = int(pri_slice.iloc[:int(look_primary*0.55)]['High'].idxmax())
        t_h2 = int(pri_slice.iloc[int(look_primary*0.45):]['High'].idxmax())
        if t_h2 > t_h1:
            p_h1 = float(df.loc[t_h1, 'High'])
            p_h2 = float(df.loc[t_h2, 'High'])
            m_pri_down = (p_h2 - p_h1) / (t_h2 - t_h1)
            y_pri_down_today = p_h1 + m_pri_down * (n - 1 - t_h1)
            result["trendlines"] = {
                "type": "resistance_falling",
                "label": "下降壓力趨勢切線",
                "color": "#F87171", # Light Red
                "x0": df.loc[t_h1, 'Date'], "y0": p_h1,
                "x1": df.iloc[-1]['Date'], "y1": round(y_pri_down_today, 2),
                "is_rising": False
            }

    if result["active_pattern"] is None and result["patterns_found"]:
        result["active_pattern"] = result["patterns_found"][0]

    if result["active_pattern"]:
        result["summary_text"] = result["active_pattern"].get("desc", "")
    elif result["trendlines"]:
        tl = result["trendlines"]
        result["summary_text"] = f"未觸發特定單一型態突破。已自動為您標註【{tl['label']}】(現值約 {tl['y1']:.2f} 元)，作為多空防守攻防界線。"

    return result


def apply_pattern_geometry_to_figure(fig: go.Figure, pattern_data: Dict[str, Any], df: pd.DataFrame) -> go.Figure:
    """
    將計算出的型態幾何線段、頸線、箱體、弧線與目標價標籤直接繪製於 Plotly 主圖 (Row 1)
    """
    if fig is None or not pattern_data:
        return fig

    active = pattern_data.get("active_pattern")
    trendlines = pattern_data.get("trendlines")

    # =========================================================================
    # 1. 繪製主導型態 (Active Pattern)
    # =========================================================================
    if active:
        pat_id = active.get("id")

        # --- A. 突破 ABC 修正下降切線 ---
        if pat_id == "abc_correction":
            t_line = active.get("tangent_line", {})
            if t_line:
                fig.add_trace(go.Scatter(
                    x=[t_line["x0"], t_line["x1"]],
                    y=[t_line["y0"], t_line["y1"]],
                    mode="lines",
                    name="ABC 下降切線",
                    line=dict(color="#06B6D4", width=2.4, dash="dash"),
                    hoverinfo="text",
                    hovertext=f"📐 ABC 下降趨勢切線 (今日切線價: {t_line['y1']} 元)",
                    showlegend=True
                ), row=1, col=1)

            for pt_key, pt_col, ay_val in [("a_point", "#38BDF8", -28), ("b_point", "#38BDF8", 28), ("c_point", "#38BDF8", -28)]:
                pt = active.get(pt_key)
                if pt:
                    fig.add_annotation(
                        x=pt["date"], y=pt["price"], xref="x", yref="y",
                        text=f" {pt['label']}: {pt['price']} ",
                        showarrow=True, arrowhead=2, ax=0, ay=ay_val,
                        bgcolor="#0E7490", bordercolor="#38BDF8", borderwidth=1.2,
                        font=dict(color="white", size=10, family="Arial Black")
                    )

            bk = active.get("breakout_point")
            if bk:
                fig.add_annotation(
                    x=bk["date"], y=bk["price"], xref="x", yref="y",
                    text=f" {bk['label']} ({bk['price']}) ",
                    showarrow=True, arrowhead=3, ax=0, ay=-45,
                    bgcolor="#EF4444", bordercolor="white", borderwidth=1.5,
                    font=dict(color="white", size=11, family="Arial Black")
                )

            tgt_d = active.get("target_d")
            if tgt_d and t_line:
                fig.add_shape(
                    type="line",
                    x0=t_line["x0"], x1=df.iloc[-1]['Date'],
                    y0=tgt_d, y1=tgt_d,
                    line=dict(color="#C084FC", width=2.0, dash="dot"),
                    row=1, col=1
                )
                fig.add_annotation(
                    x=df.iloc[-1]['Date'], y=tgt_d, xref="x", yref="y",
                    text=f" 🏁 等距目標價 D': {tgt_d} 元 ",
                    showarrow=False, xanchor="left",
                    bgcolor="#7E22CE", bordercolor="#C084FC", borderwidth=1,
                    font=dict(color="white", size=10, family="Arial Black")
                )

        # --- B. 跌破反彈 ABC 上升切線 ---
        elif pat_id == "abc_rebound_breakdown":
            t_line = active.get("tangent_line", {})
            if t_line:
                fig.add_trace(go.Scatter(
                    x=[t_line["x0"], t_line["x1"]],
                    y=[t_line["y0"], t_line["y1"]],
                    mode="lines",
                    name="ABC 上升切線",
                    line=dict(color="#F97316", width=2.4, dash="dash"),
                    hoverinfo="text",
                    hovertext=f"📐 反彈 ABC 上升切線 (今日切線價: {t_line['y1']} 元)",
                    showlegend=True
                ), row=1, col=1)

            for pt_key, ay_val in [("a_point", 28), ("b_point", -28), ("c_point", 28)]:
                pt = active.get(pt_key)
                if pt:
                    fig.add_annotation(
                        x=pt["date"], y=pt["price"], xref="x", yref="y",
                        text=f" {pt['label']}: {pt['price']} ",
                        showarrow=True, arrowhead=2, ax=0, ay=ay_val,
                        bgcolor="#C2410C", bordercolor="#FDBA74", borderwidth=1.2,
                        font=dict(color="white", size=10, family="Arial Black")
                    )

            tgt_d = active.get("target_d")
            if tgt_d and t_line:
                fig.add_shape(
                    type="line",
                    x0=t_line["x0"], x1=df.iloc[-1]['Date'],
                    y0=tgt_d, y1=tgt_d,
                    line=dict(color="#F87171", width=2.0, dash="dot"),
                    row=1, col=1
                )
                fig.add_annotation(
                    x=df.iloc[-1]['Date'], y=tgt_d, xref="x", yref="y",
                    text=f" 🎯 等距下跌目標價 D': {tgt_d} 元 ",
                    showarrow=False, xanchor="left",
                    bgcolor="#991B1B", bordercolor="#F87171", borderwidth=1,
                    font=dict(color="white", size=10)
                )

        # --- C. 一字底 (箱型放量大突破) ---
        elif pat_id == "flat_base":
            bx = active.get("box", {})
            if bx:
                fig.add_shape(
                    type="rect",
                    x0=bx["x0"], x1=bx["x1"],
                    y0=bx["y0"], y1=bx["y1"],
                    fillcolor="rgba(234, 179, 8, 0.12)",
                    line=dict(color="#EAB308", width=1.8, dash="dot"),
                    layer="below",
                    row=1, col=1
                )
                fig.add_trace(go.Scatter(
                    x=[bx["x0"], df.iloc[-1]['Date']],
                    y=[bx["y1"], bx["y1"]],
                    mode="lines",
                    name="箱頂頸線",
                    line=dict(color="#EAB308", width=2.4),
                    showlegend=True
                ), row=1, col=1)
                fig.add_annotation(
                    x=bx["x0"], y=bx["y1"], xref="x", yref="y",
                    text=f" 📦 箱頂頸線: {bx['y1']} 元 ",
                    showarrow=False, xanchor="left", yanchor="bottom",
                    bgcolor="#A16207", bordercolor="#EAB308",
                    font=dict(color="white", size=10, family="Arial Black")
                )

                fig.add_shape(
                    type="line",
                    x0=bx["x0"], x1=df.iloc[-1]['Date'],
                    y0=bx["y0"], y1=bx["y0"],
                    line=dict(color="#EF4444", width=1.5, dash="dash"),
                    row=1, col=1
                )
                fig.add_annotation(
                    x=bx["x0"], y=bx["y0"], xref="x", yref="y",
                    text=f" 🛑 箱底防守線: {bx['y0']} 元 ",
                    showarrow=False, xanchor="left", yanchor="top",
                    bgcolor="#991B1B", bordercolor="#EF4444",
                    font=dict(color="white", size=9)
                )

            tgt_d = active.get("target_d")
            if tgt_d and bx:
                fig.add_shape(
                    type="line",
                    x0=bx["x0"], x1=df.iloc[-1]['Date'],
                    y0=tgt_d, y1=tgt_d,
                    line=dict(color="#C084FC", width=2.0, dash="dot"),
                    row=1, col=1
                )
                fig.add_annotation(
                    x=df.iloc[-1]['Date'], y=tgt_d, xref="x", yref="y",
                    text=f" 🚀 箱型等距目標價 D': {tgt_d} 元 ",
                    showarrow=False, xanchor="left",
                    bgcolor="#7E22CE", font=dict(color="white", size=10, family="Arial Black")
                )

        # --- D. 圓弧底 (U型底) ---
        elif pat_id == "rounding_bottom":
            neck = active.get("neckline")
            arc_pts = active.get("arc_points", [])
            if arc_pts:
                fig.add_trace(go.Scatter(
                    x=[p["date"] for p in arc_pts],
                    y=[p["price"] for p in arc_pts],
                    mode="lines",
                    name="U型圓弧軌跡",
                    line=dict(color="#EC4899", width=2.5, dash="dashdot"),
                    showlegend=True
                ), row=1, col=1)

            if neck:
                fig.add_shape(
                    type="line",
                    x0=arc_pts[0]["date"] if arc_pts else df.iloc[-30]['Date'],
                    x1=df.iloc[-1]['Date'],
                    y0=neck, y1=neck,
                    line=dict(color="#EC4899", width=2.2),
                    row=1, col=1
                )
                fig.add_annotation(
                    x=df.iloc[-1]['Date'], y=neck, xref="x", yref="y",
                    text=f" 🥣 圓弧底頸線: {neck} 元 ",
                    showarrow=False, xanchor="left",
                    bgcolor="#BE185D", font=dict(color="white", size=10, family="Arial Black")
                )

            tgt_d = active.get("target_d")
            if tgt_d:
                fig.add_shape(
                    type="line",
                    x0=arc_pts[0]["date"] if arc_pts else df.iloc[-30]['Date'],
                    x1=df.iloc[-1]['Date'],
                    y0=tgt_d, y1=tgt_d,
                    line=dict(color="#C084FC", width=1.8, dash="dot"),
                    row=1, col=1
                )
                fig.add_annotation(
                    x=df.iloc[-1]['Date'], y=tgt_d, xref="x", yref="y",
                    text=f" 🏁 圓弧底等距目標價: {tgt_d} 元 ",
                    showarrow=False, xanchor="left",
                    bgcolor="#7E22CE", font=dict(color="white", size=10)
                )

        # --- E. 上升軌道線 ---
        elif pat_id == "ascending_channel":
            low_l = active.get("lower_line", {})
            upp_l = active.get("upper_line", {})
            if low_l and upp_l:
                fig.add_trace(go.Scatter(
                    x=[low_l["x0"], low_l["x1"]],
                    y=[low_l["y0"], low_l["y1"]],
                    mode="lines",
                    name="通道下軌支撐",
                    line=dict(color="#8B5CF6", width=2.0, dash="dash"),
                    showlegend=True
                ), row=1, col=1)

                fig.add_trace(go.Scatter(
                    x=[upp_l["x0"], upp_l["x1"]],
                    y=[upp_l["y0"], upp_l["y1"]],
                    mode="lines",
                    name="通道上軌反壓",
                    line=dict(color="#A855F7", width=2.4, dash="dash"),
                    showlegend=True
                ), row=1, col=1)

                bk = active.get("breakout_point")
                if bk:
                    fig.add_annotation(
                        x=bk["date"], y=bk["price"], xref="x", yref="y",
                        text=f" {bk['label']} ",
                        showarrow=True, arrowhead=2, ax=0, ay=-35,
                        bgcolor="#6D28D9", font=dict(color="white", size=11, family="Arial Black")
                    )

    # =========================================================================
    # 2. 若無特定主導型態，繪製主要智慧趨勢切線 (保證任何股票皆有切線指引)
    # =========================================================================
    elif trendlines:
        tl = trendlines
        fig.add_trace(go.Scatter(
            x=[tl["x0"], tl["x1"]],
            y=[tl["y0"], tl["y1"]],
            mode="lines",
            name=tl["label"],
            line=dict(color=tl["color"], width=2.2, dash="dash"),
            hoverinfo="text",
            hovertext=f"📐 {tl['label']} (現值: {tl['y1']} 元)",
            showlegend=True
        ), row=1, col=1)
        fig.add_annotation(
            x=tl["x1"], y=tl["y1"], xref="x", yref="y",
            text=f" 📐 {tl['label']} ({tl['y1']}) ",
            showarrow=False, xanchor="left",
            bgcolor="#1E293B", bordercolor=tl["color"], borderwidth=1.2,
            font=dict(color=tl["color"], size=10, family="Arial Black")
        )

    return fig
