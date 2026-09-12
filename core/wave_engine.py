# -*- coding: utf-8 -*-
"""
轉折波演算核心 (升級版：雜訊過濾與微波平滑)
依據《技術分析全攻略》CH1 講義規範，並提供波段雜訊平滑模式，
解決橫盤糾結時產生過多密集微小轉折導致畫面擁擠、遮擋K棒的問題。
"""

import pandas as pd
import numpy as np

def calculate_turning_points(df: pd.DataFrame, ma_period=5, filter_mode="standard"):
    """
    計算轉折波高點 (頭) 與低點 (底)
    參數:
      - ma_period: 基準均線 (5, 10, 20)
      - filter_mode: "standard" (過濾橫盤微小毛刺，畫面清爽，推薦) 或 "all" (完整原始細微轉折)
    """
    ma_col = f"SMA_{ma_period}"
    if ma_col not in df.columns:
        df[ma_col] = df['Close'].rolling(window=ma_period).mean()

    valid_df = df.dropna(subset=[ma_col]).copy().reset_index(drop=True)
    if len(valid_df) < 5:
        return [], [], None, None

    raw_points = []
    state = 1 if valid_df.loc[0, 'Close'] >= valid_df.loc[0, ma_col] else -1
    seg_start_idx = 0

    for i in range(1, len(valid_df)):
        c = valid_df.loc[i, 'Close']
        ma = valid_df.loc[i, ma_col]

        if state == 1:
            if c < ma:
                sub = valid_df.iloc[seg_start_idx:i + 1]
                max_high_idx = sub['High'].idxmax()
                peak_row = valid_df.loc[max_high_idx]
                
                point = {
                    "type": "PEAK",
                    "date": peak_row['Date'],
                    "price": round(float(peak_row['High']), 2),
                    "index": int(max_high_idx),
                    "label": "頭"
                }
                
                if raw_points and raw_points[-1]['type'] == 'PEAK':
                    if point['price'] > raw_points[-1]['price']:
                        raw_points[-1] = point
                else:
                    raw_points.append(point)

                state = -1
                seg_start_idx = max_high_idx

        elif state == -1:
            if c > ma:
                sub = valid_df.iloc[seg_start_idx:i + 1]
                min_low_idx = sub['Low'].idxmin()
                trough_row = valid_df.loc[min_low_idx]
                
                point = {
                    "type": "TROUGH",
                    "date": trough_row['Date'],
                    "price": round(float(trough_row['Low']), 2),
                    "index": int(min_low_idx),
                    "label": "底"
                }
                
                if raw_points and raw_points[-1]['type'] == 'TROUGH':
                    if point['price'] < raw_points[-1]['price']:
                        raw_points[-1] = point
                else:
                    raw_points.append(point)

                state = 1
                seg_start_idx = min_low_idx

    # 處理最後行進中波段
    if seg_start_idx < len(valid_df):
        sub = valid_df.iloc[seg_start_idx:]
        if state == 1:
            max_idx = sub['High'].idxmax()
            curr_peak = {
                "type": "PEAK",
                "date": valid_df.loc[max_idx, 'Date'],
                "price": round(float(valid_df.loc[max_idx, 'High']), 2),
                "index": int(max_idx),
                "label": "頭",
                "is_tentative": True
            }
            if not raw_points or raw_points[-1]['type'] != 'PEAK':
                raw_points.append(curr_peak)
            elif curr_peak['price'] > raw_points[-1]['price']:
                raw_points[-1] = curr_peak
        else:
            min_idx = sub['Low'].idxmin()
            curr_trough = {
                "type": "TROUGH",
                "date": valid_df.loc[min_idx, 'Date'],
                "price": round(float(valid_df.loc[min_idx, 'Low']), 2),
                "index": int(min_idx),
                "label": "底",
                "is_tentative": True
            }
            if not raw_points or raw_points[-1]['type'] != 'TROUGH':
                raw_points.append(curr_trough)
            elif curr_trough['price'] < raw_points[-1]['price']:
                raw_points[-1] = curr_trough

    # --- 雜訊過濾模式 ---
    if filter_mode == "standard" and len(raw_points) >= 3:
        # 動態計算合理過濾門檻 (約該股票平均每日振幅的 1.2 倍，通常在 1.5%~2.5%)
        daily_range_pct = ((valid_df['High'] - valid_df['Low']) / valid_df['Close']).mean() * 100
        min_swing_pct = max(1.6, min(3.0, daily_range_pct * 1.1))

        filtered = [raw_points[0]]
        for pt in raw_points[1:]:
            last_pt = filtered[-1]
            if pt['type'] == last_pt['type']:
                if pt['type'] == 'PEAK' and pt['price'] > last_pt['price']:
                    filtered[-1] = pt
                elif pt['type'] == 'TROUGH' and pt['price'] < last_pt['price']:
                    filtered[-1] = pt
            else:
                swing_pct = abs(pt['price'] - last_pt['price']) / (last_pt['price'] + 1e-9) * 100
                day_diff = abs(pt['index'] - last_pt['index'])
                # 波幅達到門檻，或天數間隔足夠，或是最後關鍵端點，予以保留
                if swing_pct >= min_swing_pct or day_diff >= 4 or pt == raw_points[-1]:
                    filtered.append(pt)
                else:
                    # 橫盤微小震盪毛刺，不開新波段
                    pass
        points = filtered
    else:
        points = raw_points

    # 確保嚴格高低交替
    cleaned = []
    for p in points:
        if not cleaned:
            cleaned.append(p)
        elif p['type'] == cleaned[-1]['type']:
            if p['type'] == 'PEAK' and p['price'] > cleaned[-1]['price']:
                cleaned[-1] = p
            elif p['type'] == 'TROUGH' and p['price'] < cleaned[-1]['price']:
                cleaned[-1] = p
        else:
            cleaned.append(p)
    points = cleaned

    # 整理折線座標
    wave_lines = []
    for j in range(len(points) - 1):
        wave_lines.append({
            "x0": points[j]['date'],
            "y0": points[j]['price'],
            "x1": points[j + 1]['date'],
            "y1": points[j + 1]['price'],
            "from_type": points[j]['type'],
            "to_type": points[j + 1]['type']
        })

    peaks = [p for p in points if p['type'] == 'PEAK']
    troughs = [p for p in points if p['type'] == 'TROUGH']

    highest_peak = max(peaks, key=lambda x: x['price']) if peaks else None
    lowest_trough = min(troughs, key=lambda x: x['price']) if troughs else None

    return points, wave_lines, highest_peak, lowest_trough
