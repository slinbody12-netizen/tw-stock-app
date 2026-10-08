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
        "accelerated_defense_line": None,
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
    # =========================================================================
    # 1. 📐 突破 ABC 修正下降切線 (做多旗型突破)
    # =========================================================================
    abc_pat = None
    if n >= 15:
        lookback_a = min(50, n - 4)
        slice_a_pool = df.iloc[-lookback_a:-6]
        if len(slice_a_pool) >= 3:
            a_cands = []
            for k in range(slice_a_pool.index[0] + 1, slice_a_pool.index[-1]):
                h = float(df.loc[k, 'High'])
                prev_h = float(df.loc[k-1, 'High'])
                next_h = float(df.loc[k+1, 'High'])
                if h >= prev_h and h >= next_h:
                    a_cands.append(k)
            max_h_idx = int(slice_a_pool['High'].idxmax())
            if max_h_idx not in a_cands:
                a_cands.append(max_h_idx)

            valid_combos = []
            for cand_a in a_cands:
                p_a = float(df.loc[cand_a, 'High'])
                for cand_c in range(cand_a + 4, n - 2):
                    p_c = float(df.loc[cand_c, 'High'])
                    if p_c >= p_a:
                        continue
                    sl = (p_c - p_a) / (cand_c - cand_a)
                    if sl >= 0:
                        continue

                    # 1. 上凸包檢驗：A 到 C 之間，所有中間 K 棒高點不得穿透切線 (容許 0.2% 影線雜訊)
                    pierced_ac = False
                    for mid_i in range(cand_a + 1, cand_c):
                        y_mid = p_a + sl * (mid_i - cand_a)
                        if float(df.loc[mid_i, 'High']) > y_mid * 1.002:
                            pierced_ac = True
                            break
                    if pierced_ac:
                        continue

                    # 2. C 到昨天 (n-2) 之間，檢驗穿透程度 (超過切線 0.3% 者計為穿身)
                    pierced_after = 0
                    for mid_i in range(cand_c + 1, n - 1):
                        y_mid = p_a + sl * (mid_i - cand_a)
                        if float(df.loc[mid_i, 'High']) > y_mid * 1.003:
                            pierced_after += 1
                    if pierced_after > 1:
                        continue

                    # 3. 檢查 C 是否為局部波峰
                    prev_h = float(df.loc[cand_c - 1, 'High'])
                    next_h = float(df.loc[cand_c + 1, 'High'])
                    is_peak_c = (p_c >= prev_h * 0.995) and (p_c >= next_h * 0.995)

                    # 4. 尋找 B 點 (A 與今天之間的最低低點)
                    slice_b = df.iloc[cand_a + 1:n - 1]
                    cand_b = int(slice_b['Low'].idxmin())
                    p_b = float(df.loc[cand_b, 'Low'])

                    # 修正深度 (從 A 到 B 至少回檔 3%)
                    depth_pct = (p_a - p_b) / (p_a + 1e-9)
                    if depth_pct < 0.03:
                        continue

                    y_line_today = p_a + sl * (n - 1 - cand_a)
                    is_break = (c_today >= y_line_today * 0.995) and (c_today >= sma5_today) and (c_today >= o_today)

                    # 幾何權重綜合評分
                    score = 100.0
                    if is_break:
                        score += 50.0
                    if is_peak_c:
                        score += 30.0
                    if pierced_after == 0:
                        score += 30.0
                    else:
                        score -= 30.0
                    if (n - 1 - cand_c) >= 5:
                        score += 15.0
                    span_ac = cand_c - cand_a
                    if 6 <= span_ac <= 25:
                        score += 15.0
                    score += depth_pct * 50.0
                    score += (p_a / float(df.loc[max_h_idx, 'High'])) * 20.0

                    valid_combos.append({
                        'idx_a': cand_a, 'price_a': p_a,
                        'idx_b': cand_b, 'price_b': p_b,
                        'idx_c': cand_c, 'price_c': p_c,
                        'slope': sl, 'y_tangent_today': y_line_today,
                        'is_breaking': is_break, 'score': score
                    })

            if valid_combos:
                valid_combos.sort(key=lambda x: x['score'], reverse=True)
                best_abc = valid_combos[0]

                idx_a = best_abc['idx_a']
                price_a = best_abc['price_a']
                idx_b = best_abc['idx_b']
                price_b = best_abc['price_b']
                idx_c = best_abc['idx_c']
                price_c = best_abc['price_c']
                slope = best_abc['slope']
                y_tangent_today = best_abc['y_tangent_today']
                is_breaking = best_abc['is_breaking']

                prev_slice = df.iloc[max(0, idx_a - 15):idx_a]
                wave1_low = float(prev_slice['Low'].min()) if len(prev_slice) > 0 else price_b
                wave1_amp = max(price_a - wave1_low, price_a - price_b, price_c * 0.05)
                target_d = round(price_c + wave1_amp, 2)

                if is_breaking:
                    status = "🔥 突破下降切線"
                    desc = f"多頭 ABC 旗型整理完成，今日放量突破下降切線 (切線價 {y_tangent_today:.2f} 元)！短空做頭失敗反手多，等距目標價 D' 為 {target_d} 元。"
                elif slope < 0:
                    status = "旗型收斂中 (未突破)"
                    desc = f"多頭 ABC 旗型整理收斂中，下降切線壓力現值約 {y_tangent_today:.2f} 元，前波高點 C 為 {price_c:.2f} 元。一旦放量長紅衝過切線，等距目標價 D' 上看 {target_d} 元。"
                else:
                    status = "整理觀察中"
                    desc = f"近期波段整理結構，前波高點 A 為 {price_a:.2f} 元、回檔低點 B 為 {price_b:.2f} 元。待明確轉折突破後，等距目標價 D' 上看 {target_d} 元。"

                abc_pat = {
                    "id": "abc_correction",
                    "name": "📐 突破 ABC 修正下降切線",
                    "direction": "多",
                    "status": status,
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
                    "desc": desc
                }

    # =========================================================================
    # 2. 📐 跌破反彈 ABC 上升切線 (做空反彈結束重回主跌)
    # =========================================================================
    abc_short_pat = None
    if n >= 15:
        lookback_s = min(50, n - 4)
        slice_s_pool = df.iloc[-lookback_s:-6]
        if len(slice_s_pool) >= 3:
            s_cands = []
            for k in range(slice_s_pool.index[0] + 1, slice_s_pool.index[-1]):
                l = float(df.loc[k, 'Low'])
                prev_l = float(df.loc[k-1, 'Low'])
                next_l = float(df.loc[k+1, 'Low'])
                if l <= prev_l and l <= next_l:
                    s_cands.append(k)
            min_l_idx = int(slice_s_pool['Low'].idxmin())
            if min_l_idx not in s_cands:
                s_cands.append(min_l_idx)

            valid_short_combos = []
            for cand_a_s in s_cands:
                p_a_s = float(df.loc[cand_a_s, 'Low'])
                for cand_c_s in range(cand_a_s + 4, n - 2):
                    p_c_s = float(df.loc[cand_c_s, 'Low'])
                    if p_c_s <= p_a_s:
                        continue
                    sl_s = (p_c_s - p_a_s) / (cand_c_s - cand_a_s)
                    if sl_s <= 0:
                        continue

                    # 下凸包檢驗：A 到 C 之間，所有中間 K 棒低點不得跌破切線 (容許 0.2% 誤差)
                    pierced_ac_s = False
                    for mid_i in range(cand_a_s + 1, cand_c_s):
                        y_mid = p_a_s + sl_s * (mid_i - cand_a_s)
                        if float(df.loc[mid_i, 'Low']) < y_mid * 0.998:
                            pierced_ac_s = True
                            break
                    if pierced_ac_s:
                        continue

                    pierced_after_s = 0
                    for mid_i in range(cand_c_s + 1, n - 1):
                        y_mid = p_a_s + sl_s * (mid_i - cand_a_s)
                        if float(df.loc[mid_i, 'Low']) < y_mid * 0.997:
                            pierced_after_s += 1
                    if pierced_after_s > 1:
                        continue

                    prev_l = float(df.loc[cand_c_s - 1, 'Low'])
                    next_l = float(df.loc[cand_c_s + 1, 'Low'])
                    is_trough_c = (p_c_s <= prev_l * 1.005) and (p_c_s <= next_l * 1.005)

                    slice_b_s = df.iloc[cand_a_s + 1:n - 1]
                    cand_b_s = int(slice_b_s['High'].idxmax())
                    p_b_s = float(df.loc[cand_b_s, 'High'])

                    rebound_pct = (p_b_s - p_a_s) / (p_a_s + 1e-9)
                    if rebound_pct < 0.03:
                        continue

                    y_line_s_today = p_a_s + sl_s * (n - 1 - cand_a_s)
                    is_breaking_s = (c_today <= y_line_s_today * 1.005) and (c_today <= sma5_today)

                    score_s = 100.0
                    if is_breaking_s:
                        score_s += 50.0
                    if is_trough_c:
                        score_s += 30.0
                    if pierced_after_s == 0:
                        score_s += 30.0
                    else:
                        score_s -= 30.0
                    if (n - 1 - cand_c_s) >= 5:
                        score_s += 15.0
                    span_ac_s = cand_c_s - cand_a_s
                    if 6 <= span_ac_s <= 25:
                        score_s += 15.0
                    score_s += rebound_pct * 50.0
                    score_s += (float(df.loc[min_l_idx, 'Low']) / (p_a_s + 1e-9)) * 20.0

                    valid_short_combos.append({
                        'idx_a': cand_a_s, 'price_a': p_a_s,
                        'idx_b': cand_b_s, 'price_b': p_b_s,
                        'idx_c': cand_c_s, 'price_c': p_c_s,
                        'slope': sl_s, 'y_tangent_today': y_line_s_today,
                        'is_breaking': is_breaking_s, 'score': score_s
                    })

            if valid_short_combos:
                valid_short_combos.sort(key=lambda x: x['score'], reverse=True)
                best_short = valid_short_combos[0]

                idx_a_s = best_short['idx_a']
                price_a_s = best_short['price_a']
                idx_b_s = best_short['idx_b']
                price_b_s = best_short['price_b']
                idx_c_s = best_short['idx_c']
                price_c_s = best_short['price_c']
                slope_s = best_short['slope']
                y_tangent_s_today = best_short['y_tangent_today']
                is_breaking_s = best_short['is_breaking']

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

    # =========================================================================
    # 3. 📦 一字底 (箱型狹幅糾結放量大突破)
    # =========================================================================
    flat_pat = None
    if n >= 20:
        found_box = False
        box_len_chosen = 30
        for b_len in [45, 30, 20]:
            if n > b_len:
                box_slice = df.iloc[-b_len:]
                b_high = float(box_slice['High'].max())
                b_low = float(box_slice['Low'].min())
                amplitude = (b_high - b_low) / (b_low + 1e-9)
                if amplitude <= 0.18:
                    found_box = True
                    box_len_chosen = b_len
                    break
        if not found_box:
            box_len_chosen = min(30, n - 1)
            box_slice = df.iloc[-box_len_chosen:]
            b_high = float(box_slice['High'].max())
            b_low = float(box_slice['Low'].min())
            amplitude = (b_high - b_low) / (b_low + 1e-9)

        is_break_flat = (c_today >= b_high * 0.995) and (c_today >= sma5_today) and (c_today >= o_today)
        target_flat = round(b_high + (b_high - b_low), 2)
        if is_break_flat:
            flat_status = "🔥 一棒過箱頂"
            flat_desc = f"一字底 {box_len_chosen} 日狹幅整理 (振幅 {amplitude*100:.1f}%)，均線高度糾結後一棒摜破箱頂頸線 ({b_high:.2f} 元)！等距波段目標價上看 {target_flat} 元。"
        else:
            flat_status = "箱型整理中 (未破箱頂)"
            flat_desc = f"箱型整理格局 (近 {box_len_chosen} 日振幅 {amplitude*100:.1f}%)，箱頂頸線為 {b_high:.2f} 元，箱底防守線為 {b_low:.2f} 元。靜待帶量長紅一棒過箱頂起漲，等距波段目標價上看 {target_flat} 元。"

        flat_pat = {
            "id": "flat_base",
            "name": "📦 一字底 (箱型放量大突破)",
            "direction": "多",
            "status": flat_status,
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
            "desc": flat_desc
        }

    # =========================================================================
    # 4. 🥣 圓弧底 (U型慢火打底二次拋物線擬合)
    # =========================================================================
    round_pat = None
    if n >= 25:
        round_len = min(65, n - 1)
        r_slice = df.iloc[-round_len:]
        y_lows = r_slice['Low'].values
        low_idx_rel = int(np.argmin(y_lows))
        
        # 凹槽低點平滑夾取，確保拋物線呈開口向上之 U 型
        trough_idx = low_idx_rel
        if trough_idx <= 2:
            trough_idx = max(3, round_len // 3)
        elif trough_idx >= round_len - 3:
            trough_idx = min(round_len - 4, 2 * round_len // 3)

        x1, x2, x3 = 0, trough_idx, round_len - 1
        y1 = float(r_slice.iloc[:max(2, trough_idx)]['High'].max())
        y2 = float(y_lows[trough_idx])
        y3 = float(r_slice.iloc[min(round_len - 1, trough_idx + 1):]['High'].max())
        if y2 >= min(y1, y3):
            y2 = min(y1, y3) * 0.95

        poly_coeffs = np.polyfit([x1, x2, x3], [y1, y2, y3], 2)
        sample_indices = np.linspace(0, round_len - 1, 25, dtype=int)
        y_fit = np.polyval(poly_coeffs, sample_indices)

        arc_coords = [
            {"date": r_slice.iloc[idx]['Date'], "price": round(float(y_fit[i]), 2)}
            for i, idx in enumerate(sample_indices)
        ]

        neckline_round = round(max(y1, y3), 2)
        depth_round = round(neckline_round - y2, 2)
        target_round = round(neckline_round + depth_round, 2)
        is_break_round = (c_today >= neckline_round * 0.995) and (c_today >= sma5_today) and (c_today >= o_today)

        if is_break_round:
            round_status = "🔥 放量過頸線起漲"
            round_desc = f"經典圓弧底 (U型底) 慢火打底洗淨浮額，今日收盤 ({c_today:.2f} 元) 突破水平頸線 ({neckline_round:.2f} 元)！波段等距目標價 D' 為 {target_round} 元。"
        else:
            pct_to_neck = ((neckline_round - c_today) / (c_today + 1e-9)) * 100
            round_status = "打底成形中 (未過頸線)"
            round_desc = f"經典圓弧底 (U型底) 慢火打底成形中，波段低點 {y2:.2f} 元、水平頸線反壓為 {neckline_round:.2f} 元 (距頸線約 {pct_to_neck:.1f}%)。一旦帶量長紅過頸線，等距目標價 D' 上看 {target_round} 元。"

        round_pat = {
            "id": "rounding_bottom",
            "name": "🥣 圓弧底 (U型慢火打底)",
            "direction": "多",
            "status": round_status,
            "is_breakout": is_break_round,
            "neckline": neckline_round,
            "trough_price": y2,
            "arc_points": arc_coords,
            "target_d": target_round,
            "breakout_point": {"date": df.iloc[-1]['Date'], "price": c_today, "label": "🎯 突破圓弧頸線"} if is_break_round else None,
            "color": "#EC4899", # Pink
            "desc": round_desc
        }

    # =========================================================================
    # 5. 🚀 上升／下降軌道線 (平行通道回歸)
    # =========================================================================
    channel_pat = None
    if n >= 20:
        ch_len = min(40, n)
        ch_slice = df.iloc[-ch_len:]
        
        t1_idx = int(ch_slice.iloc[:int(ch_len*0.6)]['Low'].idxmin())
        t2_idx = int(ch_slice.iloc[int(ch_len*0.5):]['Low'].idxmin())
        if t2_idx <= t1_idx:
            t1_idx = int(ch_slice.index[0])
            t2_idx = int(ch_slice.index[-1])

        t1_p = float(df.loc[t1_idx, 'Low'])
        t2_p = float(df.loc[t2_idx, 'Low'])
        span = max(1, t2_idx - t1_idx)
        ch_slope = (t2_p - t1_p) / span

        indices_between = np.arange(t1_idx, n)
        lower_prices = t1_p + ch_slope * (indices_between - t1_idx)
        highs_between = df.loc[indices_between, 'High'].values
        diffs = highs_between - lower_prices
        channel_height = max(float(np.percentile(diffs, 90)), (abs(t2_p - t1_p) + 1.0) * 0.5, c_today * 0.04)

        y_lower_today = t1_p + ch_slope * (n - 1 - t1_idx)
        y_upper_today = y_lower_today + channel_height

        # 檢驗上方是否緊鄰未回補重大空方跳空缺口 (嚴防訊號衝突)
        has_overhead_gap = False
        near_gap = None
        try:
            from core.gap_detector import detect_unfilled_gaps
            gaps_geo = detect_unfilled_gaps(df, lookback_bars=120)
            near_gap = gaps_geo.get("nearest_overhead_gap")
            has_overhead_gap = bool(near_gap and 0 <= near_gap.get('distance_pct', 99) <= 3.0)
        except Exception:
            pass

        is_red_k = (c_today >= o_today)
        is_touch_upper = (c_today >= y_upper_today * 0.995)
        # 若上方緊鄰重大空方缺口反壓，不得視為有效多頭加速突破
        is_break_ch = is_touch_upper and (c_today >= sma5_today) and is_red_k and (not has_overhead_gap)

        if ch_slope >= 0:
            ch_name = "🚀 突破上升軌道線" if is_break_ch else "📈 上升軌道線"
            if is_break_ch:
                ch_status = "衝破上軌加速噴出"
                ch_action = "今日放量大紅K衝破上升軌道線上緣！多頭轉強加速噴出主升段。"
            elif has_overhead_gap:
                ch_status = "逼近重大缺口反壓"
                ch_action = f"今日股價雖觸及上升軌道上緣，但上方緊鄰 {near_gap['date_str']} 重大空方跳空缺口反壓 ({near_gap['rem_bottom']:.2f}元，差距僅 +{near_gap['distance_pct']:.1f}%)！上方套牢解套賣壓沉重，嚴防逢高受阻假突破！"
            elif is_touch_upper and not is_red_k:
                ch_status = "觸頂開高走低收黑"
                ch_action = "今日盤中雖一度衝過上升軌道線上緣，但終場開高走低收黑K(綠K)遭逢獲利了結賣壓，需防高檔假突破或震盪拉回。"
            else:
                ch_status = "通道內推升"
                ch_action = "目前在上升軌道內震盪墊高，回踩下軌守穩為良性買點。"
            ch_desc = f"多頭沿上升通道推升 (下軌支撐約 {y_lower_today:.2f} 元，上軌反壓約 {y_upper_today:.2f} 元)。{ch_action}"
        else:
            ch_name = "🚀 突破下降軌道線" if is_break_ch else "📉 下降軌道線"
            if is_break_ch:
                ch_status = "衝破上軌扭轉空頭"
                ch_action = "今日強勢收紅衝破下降軌道線上緣！空頭趨勢扭轉反轉走多。"
            elif has_overhead_gap:
                ch_status = "逼近重大缺口反壓"
                ch_action = f"今日股價雖衝出下降軌道，但上方緊鄰 {near_gap['date_str']} 重大空方跳空缺口反壓 ({near_gap['rem_bottom']:.2f}元)！反彈面臨套牢牆，需待帶量完全封閉缺口始能確立反轉。"
            elif is_touch_upper and not is_red_k:
                ch_status = "衝高收黑留上影"
                ch_action = "今日盤中雖試圖衝破下降軌道上緣，但終場開高走低收黑，反轉尚未確認，需待帶量長紅實體站穩。"
            else:
                ch_status = "通道內尋底跌勢中"
                ch_action = "目前沿下降通道修正，需放量衝破上軌始能扭轉跌勢。"
            ch_desc = f"股價沿下降通道整理 (上軌壓力約 {y_upper_today:.2f} 元，下軌支撐約 {y_lower_today:.2f} 元)。{ch_action}"

        channel_pat = {
            "id": "ascending_channel",
            "name": ch_name,
            "direction": "多" if (is_break_ch or ch_slope >= 0) else "空",
            "status": ch_status,
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
            "breakout_point": {"date": df.iloc[-1]['Date'], "price": c_today, "label": "⚡ 衝破軌道加速噴出"} if is_break_ch else None,
            "color": "#8B5CF6", # Purple
            "desc": ch_desc
        }

    # =========================================================================
    # 6. 組織候選型態清單 (保證 4 大經典型態皆可切換，突破發動者置頂優先)
    # =========================================================================
    candidates = [p for p in [flat_pat, round_pat, abc_pat, channel_pat, abc_short_pat] if p is not None]
    breakouts = [p for p in candidates if p.get("is_breakout", False)]
    non_breakouts = [p for p in candidates if not p.get("is_breakout", False)]
    result["patterns_found"] = breakouts + non_breakouts

    # =========================================================================
    # 7. 🌐 通用主趨勢切線 (保證任何股票皆能自動獲得幾何繪圖)
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

    # =========================================================================
    # 8. ⚡ 近期短期加速防守線 (朱家泓/林穎老師角度修正·短線防守軌道，電光青藍色 #00F0FF)
    # =========================================================================
    acc_defense_line = None
    if n >= 15 and c_today >= sma20_today * 0.95:
        look_acc = min(30, n - 2)
        pool_acc = df.iloc[-look_acc:]
        
        troughs_acc = []
        for i_acc in range(1, len(pool_acc) - 1):
            idx_a = pool_acc.index[i_acc]
            l_a = float(df.loc[idx_a, 'Low'])
            prev_la = float(df.loc[pool_acc.index[i_acc - 1], 'Low'])
            next_la = float(df.loc[pool_acc.index[i_acc + 1], 'Low'])
            if l_a <= prev_la and l_a <= next_la:
                troughs_acc.append((idx_a, l_a))
        
        min_idx_a = pool_acc['Low'].idxmin()
        if not any(t[0] == min_idx_a for t in troughs_acc):
            troughs_acc.append((min_idx_a, float(df.loc[min_idx_a, 'Low'])))
        troughs_acc.sort(key=lambda x: x[0])
        
        best_acc_score = -1
        for i_t in range(len(troughs_acc)):
            t1_i, p1_v = troughs_acc[i_t]
            for j_t in range(i_t + 1, len(troughs_acc)):
                t2_i, p2_v = troughs_acc[j_t]
                span_t = t2_i - t1_i
                if span_t < 3 or span_t > 20:
                    continue
                if p2_v <= p1_v * 1.008:
                    continue
                
                sl_t = (p2_v - p1_v) / span_t
                if sl_t <= 0:
                    continue
                
                pierced_t = False
                for k_t in range(t1_i + 1, t2_i):
                    line_k = p1_v + sl_t * (k_t - t1_i)
                    if float(df.loc[k_t, 'Low']) < line_k * 0.992:
                        pierced_t = True
                        break
                if pierced_t:
                    continue
                
                y_acc_today = p1_v + sl_t * (n - 1 - t1_i)
                if y_acc_today > c_today * 1.20:
                    continue
                
                recency_s = (t2_i / (n - 1)) * 60.0
                span_s = (1.0 - abs(span_t - 8) / 20.0) * 20.0
                score_acc = 100.0 + recency_s + span_s + sl_t * 5.0
                
                if score_acc > best_acc_score:
                    best_acc_score = score_acc
                    is_broken_acc = (c_today < y_acc_today * 0.998) and (c_today <= sma5_today)
                    acc_defense_line = {
                        "t1_idx": t1_i, "t1_date": df.loc[t1_i, 'Date'], "p1": p1_v,
                        "t2_idx": t2_i, "t2_date": df.loc[t2_i, 'Date'], "p2": p2_v,
                        "slope": sl_t, "y_today": round(y_acc_today, 2),
                        "is_broken": is_broken_acc,
                        "color": "#00F0FF", # Electric Cyan
                        "label": f"近期加速防守線 ({round(y_acc_today, 2)}元)"
                    }
    result["accelerated_defense_line"] = acc_defense_line

    if result["patterns_found"]:
        result["active_pattern"] = result["patterns_found"][0]
        result["summary_text"] = result["active_pattern"].get("desc", "")
    elif result["trendlines"]:
        tl = result["trendlines"]
        result["summary_text"] = f"未觸發特定單一型態突破。已自動為您標註【{tl['label']}】(現值約 {tl['y1']:.2f} 元)，作為多空防守攻防界線。"

    return result


def _same_date(d1, d2) -> bool:
    try:
        return str(pd.to_datetime(d1).date()) == str(pd.to_datetime(d2).date())
    except Exception:
        return False


def _resolve_annotation_offset(fig: go.Figure, pt_date, default_ay: int, default_ax: int = 0):
    """
    智慧避讓碰撞演算法：
    檢查圖表中是否已存在同日期(x)與同方向(ay)的關鍵標註（例如「⚓ 最低底」或「🏆 最高頭」）。
    若存在碰撞，微調垂直高度避開，絕不橫向拉出跨越數根K線的混淆長箭頭，確保箭頭永遠直觀俐落。
    """
    final_ax = default_ax
    final_ay = default_ay

    pt_dt_str = str(pd.to_datetime(pt_date).date())
    existing_annos = list(fig.layout.annotations or [])

    is_colliding = False
    for a in existing_annos:
        if not hasattr(a, 'x') or a.x is None:
            continue
        try:
            a_dt_str = str(pd.to_datetime(a.x).date())
            if a_dt_str == pt_dt_str:
                a_ay = getattr(a, 'ay', 0) or 0
                a_ax = getattr(a, 'ax', 0) or 0
                # 若垂直位移方向一致 (同在下方 ay>0 或同在上方 ay<0) 且水平重疊
                if (default_ay > 0 and a_ay > 0) or (default_ay < 0 and a_ay < 0):
                    if abs(a_ax - default_ax) < 80 and abs(a_ay - default_ay) < 40:
                        is_colliding = True
                        break
        except Exception:
            continue

    if is_colliding:
        # 上下垂直錯開避讓，避免橫向拉出跨越數根K線的混淆長箭頭
        final_ay = default_ay - 22 if default_ay < 0 else default_ay + 22

    return final_ax, final_ay


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

            existing_annos = list(fig.layout.annotations or [])

            # 1. Ⓐ 起修頂 (檢查是否與 最高頭 重疊)
            pt_a = active.get("a_point")
            coincide_hp = False
            if pt_a:
                for a in existing_annos:
                    if hasattr(a, 'text') and a.text and "最高頭" in a.text and hasattr(a, 'x') and _same_date(a.x, pt_a["date"]):
                        coincide_hp = True
                        a.text = f" 🏆 最高頭 {pt_a['price']:.2f} · Ⓐ起修頂 "
                        a.arrowcolor = "#EF4444"
                        a.arrowwidth = 2.2
                        a.arrowsize = 1.2
                        break

            # 2. Ⓑ 回檔底 (檢查是否與 最低底 重疊)
            pt_b = active.get("b_point")
            coincide_lt = False
            if pt_b:
                for a in existing_annos:
                    if hasattr(a, 'text') and a.text and "最低底" in a.text and hasattr(a, 'x') and _same_date(a.x, pt_b["date"]):
                        coincide_lt = True
                        a.text = f" ⚓ 最低底 {pt_b['price']:.2f} · Ⓑ回檔底 "
                        a.arrowcolor = "#22C55E"
                        a.arrowwidth = 2.2
                        a.arrowhead = 2
                        a.arrowsize = 1.2
                        a.bordercolor = "#4ADE80"
                        a.borderwidth = 1.5
                        break

            # 更新可能已被修改的現有標註
            fig.layout.annotations = tuple(existing_annos)

            # 獨立標註 Ⓐ 起修頂：抬高 ay=-52，standoff=14 避開下方 K 線實體與「頭」圓圈，垂直青藍箭頭直指高點
            if pt_a and not coincide_hp:
                fig.add_annotation(
                    x=pt_a["date"], y=pt_a["price"], xref="x", yref="y",
                    text=f" Ⓐ 起修頂 {pt_a['price']} ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#06B6D4",
                    ax=0, ay=-52, standoff=14,
                    bgcolor="#0E7490", bordercolor="#38BDF8", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            # 獨立標註 Ⓑ 回檔底 (若未與最低底重合)：ay=46，standoff=16 避免箭頭遮擋綠色「底」圓圈
            if pt_b and not coincide_lt:
                fig.add_annotation(
                    x=pt_b["date"], y=pt_b["price"], xref="x", yref="y",
                    text=f" Ⓑ 回檔底 {pt_b['price']} ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#06B6D4",
                    ax=0, ay=46, standoff=16,
                    bgcolor="#0E7490", bordercolor="#38BDF8", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            # 3. Ⓒ 次高點：完全置於該日 K 線正上方 (ax=0, ay=-50, standoff=14)，青藍箭頭直指高點但不遮擋「頭」圓圈
            pt_c = active.get("c_point")
            if pt_c:
                fig.add_annotation(
                    x=pt_c["date"], y=pt_c["price"], xref="x", yref="y",
                    text=f" Ⓒ 次高 {pt_c['price']} ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#06B6D4",
                    ax=0, ay=-50, standoff=14,
                    bgcolor="#0E7490", bordercolor="#38BDF8", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            # 4. 🔥 突破切線買點：紅色箭頭垂直指向當日高點上方，避免遮擋行進間高點「暫高」或「頭」圓圈
            bk = active.get("breakout_point")
            if bk:
                target_y = bk["price"]
                for trace in fig.data:
                    if trace.name in ["暫高 (行進中)", "頭 (已確認)", "頭", "暫高"]:
                        if hasattr(trace, 'x') and trace.x is not None:
                            for x_val, y_val in zip(trace.x, trace.y):
                                if _same_date(x_val, bk["date"]):
                                    target_y = y_val
                                    break
                        if target_y != bk["price"]:
                            break

                if target_y == bk["price"]:
                    cand_high = df.loc[df['Date'] == bk['date'], 'High']
                    if len(cand_high) > 0:
                        target_y = float(cand_high.values[0])

                fig.add_annotation(
                    x=bk["date"], y=target_y, xref="x", yref="y",
                    text=f" 🔥 突破切線 {bk['price']} ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#EF4444",
                    ax=0, ay=-42, standoff=15,
                    bgcolor="#DC2626", bordercolor="white", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            # 5. 📐 切線當日點位標註 (例如 763.82 元)，指引今日切線壓力精準位置，不遮擋K線與移動停利等標籤
            t_line = active.get("tangent_line", {})
            if t_line:
                y_tan = t_line.get("y1")
                d_today = df.iloc[-1]['Date']
                if y_tan is not None:
                    # 徹底移除 mode="markers" 避免在 K 線實體上產生突兀圓點遮擋 K 線
                    fig.add_annotation(
                        x=d_today, y=y_tan, xref="x", yref="y",
                        text=f" 📐 切線 {y_tan:.2f} ",
                        showarrow=True, arrowhead=2, arrowsize=1.0, arrowwidth=1.5, arrowcolor="#06B6D4",
                        ax=52, ay=-22, standoff=6,
                        bgcolor="#083344", bordercolor="#06B6D4", borderwidth=1.2,
                        font=dict(color="#38BDF8", size=9.5, family="Arial Black")
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
                    showarrow=False, xanchor="left", xshift=22,
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

            existing_annos = list(fig.layout.annotations or [])

            # 1. Ⓐ 主跌底 (檢查是否與 最低底 重疊)
            pt_a = active.get("a_point")
            coincide_lt = False
            if pt_a:
                for a in existing_annos:
                    if hasattr(a, 'text') and a.text and "最低底" in a.text and hasattr(a, 'x') and _same_date(a.x, pt_a["date"]):
                        coincide_lt = True
                        a.text = f" ⚓ 最低底 {pt_a['price']:.2f} · Ⓐ主跌底 "
                        a.arrowcolor = "#22C55E"
                        a.arrowwidth = 2.2
                        a.arrowhead = 2
                        a.arrowsize = 1.2
                        a.bordercolor = "#4ADE80"
                        a.borderwidth = 1.5
                        break

            # 2. Ⓑ 反彈頂 (檢查是否與 最高頭 重疊)
            pt_b = active.get("b_point")
            coincide_hp = False
            if pt_b:
                for a in existing_annos:
                    if hasattr(a, 'text') and a.text and "最高頭" in a.text and hasattr(a, 'x') and _same_date(a.x, pt_b["date"]):
                        coincide_hp = True
                        a.text = f" 🏆 最高頭 {pt_b['price']:.2f} · Ⓑ反彈頂 "
                        a.arrowcolor = "#EF4444"
                        a.arrowwidth = 2.2
                        a.arrowsize = 1.2
                        break

            fig.layout.annotations = tuple(existing_annos)

            if pt_a and not coincide_lt:
                fig.add_annotation(
                    x=pt_a["date"], y=pt_a["price"], xref="x", yref="y",
                    text=f" Ⓐ 主跌底 {pt_a['price']} ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#F97316",
                    ax=0, ay=46, standoff=16,
                    bgcolor="#C2410C", bordercolor="#FDBA74", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            if pt_b and not coincide_hp:
                fig.add_annotation(
                    x=pt_b["date"], y=pt_b["price"], xref="x", yref="y",
                    text=f" Ⓑ 反彈頂 {pt_b['price']} ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#F97316",
                    ax=0, ay=-52, standoff=14,
                    bgcolor="#C2410C", bordercolor="#FDBA74", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            # 3. Ⓒ 次低點：完全置於該日 K 線正下方 (ax=0, ay=46, standoff=16)，橘色箭頭不遮擋「底」圓圈
            pt_c = active.get("c_point")
            if pt_c:
                fig.add_annotation(
                    x=pt_c["date"], y=pt_c["price"], xref="x", yref="y",
                    text=f" Ⓒ 次低 {pt_c['price']} ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#F97316",
                    ax=0, ay=46, standoff=16,
                    bgcolor="#C2410C", bordercolor="#FDBA74", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            # 4. ⚡ 跌破切線空點：紅色箭頭垂直指向當日低點下方，避免遮擋行進間「暫低」或「底」圓圈
            bk = active.get("breakout_point")
            if bk:
                target_y = bk["price"]
                for trace in fig.data:
                    if trace.name in ["底 (已確認)", "暫低 (行進中)", "底", "暫低"]:
                        if hasattr(trace, 'x') and trace.x is not None:
                            for x_val, y_val in zip(trace.x, trace.y):
                                if _same_date(x_val, bk["date"]):
                                    target_y = y_val
                                    break
                        if target_y != bk["price"]:
                            break

                if target_y == bk["price"]:
                    cand_low = df.loc[df['Date'] == bk['date'], 'Low']
                    if len(cand_low) > 0:
                        target_y = float(cand_low.values[0])

                t_line_bk = active.get("tangent_line", {})
                y_tan_bk = t_line_bk.get("y1")
                bk_disp = f"{y_tan_bk:.2f}元" if y_tan_bk is not None else f"{bk['price']}元"
                fig.add_annotation(
                    x=bk["date"], y=target_y, xref="x", yref="y",
                    text=f" ⚡ 跌破切線 ({bk_disp}) ",
                    showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#EF4444",
                    ax=0, ay=42, standoff=15,
                    bgcolor="#991B1B", bordercolor="white", borderwidth=1.2,
                    font=dict(color="white", size=10, family="Arial Black")
                )

            # 5. 📐 上升切線當日點位標註
            t_line = active.get("tangent_line", {})
            if t_line:
                y_tan = t_line.get("y1")
                d_today = df.iloc[-1]['Date']
                if y_tan is not None:
                    # 徹底移除 mode="markers" 避免在 K 線實體上產生突兀圓點遮擋 K 線
                    fig.add_annotation(
                        x=d_today, y=y_tan, xref="x", yref="y",
                        text=f" 📐 切線 {y_tan:.2f} ",
                        showarrow=True, arrowhead=2, arrowsize=1.0, arrowwidth=1.5, arrowcolor="#F97316",
                        ax=52, ay=22, standoff=6,
                        bgcolor="#431407", bordercolor="#F97316", borderwidth=1.2,
                        font=dict(color="#FDBA74", size=9.5, family="Arial Black")
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
                    showarrow=False, xanchor="left", xshift=22,
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
                    showarrow=False, xanchor="right", yanchor="top",
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
                    showarrow=False, xanchor="left", xshift=22,
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
                    showarrow=False, xanchor="left", xshift=22,
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
                    showarrow=False, xanchor="left", xshift=22,
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
            showarrow=False, xanchor="left", xshift=22,
            bgcolor="#1E293B", bordercolor=tl["color"], borderwidth=1.2,
            font=dict(color=tl["color"], size=10, family="Arial Black")
        )

    # =========================================================================
    # 3. ⚡ 疊加繪製近期短期加速防守線 (電光青藍色 #00F0FF，獨立於大波段切線)
    # =========================================================================
    acc_line = pattern_data.get("accelerated_defense_line")
    if acc_line:
        fig.add_trace(go.Scatter(
            x=[acc_line["t1_date"], acc_line["t2_date"], df.iloc[-1]['Date']],
            y=[acc_line["p1"], acc_line["p2"], acc_line["y_today"]],
            mode="lines",
            name="近期加速防守線",
            line=dict(color="#00F0FF", width=2.4, dash="solid"),
            hoverinfo="text",
            hovertext=f"📐 近期短期加速防守線 (今日切線價: {acc_line['y_today']} 元)",
            showlegend=True
        ), row=1, col=1)

        # 右側端點切線價標註 (電光青藍色框)
        fig.add_annotation(
            x=df.iloc[-1]['Date'], y=acc_line["y_today"], xref="x", yref="y",
            text=f" 📐 短線防守線 {acc_line['y_today']} ",
            showarrow=False, xanchor="left", xshift=20,
            bgcolor="#083344", bordercolor="#00F0FF", borderwidth=1.5,
            font=dict(color="#00F0FF", size=9.5, family="Arial Black")
        )

        # 若今日收盤跌破加速防守線，在當日 K 棒下方打出明確空方警示標籤
        if acc_line.get("is_broken", False):
            cand_low = float(df.iloc[-1]['Low'])
            fig.add_annotation(
                x=df.iloc[-1]['Date'], y=cand_low, xref="x", yref="y",
                text=f" ⚡ 跌破加速防守線 ({acc_line['y_today']}元) ",
                showarrow=True, arrowhead=2, arrowsize=1.1, arrowwidth=1.8, arrowcolor="#00F0FF",
                ax=0, ay=46, standoff=15,
                bgcolor="#0F172A", bordercolor="#00F0FF", borderwidth=1.5,
                font=dict(color="#00F0FF", size=10, family="Arial Black")
            )

    return fig
