# -*- coding: utf-8 -*-
"""
趨勢狀態機與關鍵支撐壓力演算 (Trend Analyzer)
依據《技術分析全攻略》CH1 六字訣：
- 多頭：頭頭高、底底高 (上升趨勢)
- 空頭：頭頭低、底底低 (下跌趨勢)
- 盤整：高低未同向突破 (箱型或收斂)
- 趨勢轉變警戒：多頭破前低、空頭過前高
- 自動計算：壓力線、支撐線、目標價
"""

import pandas as pd
import numpy as np

def analyze_trend(df: pd.DataFrame, points: list):
    """
    分析當前趨勢狀態、支撐壓力與關鍵價位
    """
    if not points or len(points) < 4:
        return {
            "trend_status": "資料累積中",
            "trend_badge": "觀望",
            "trend_color": "gray",
            "higher_highs": False,
            "higher_lows": False,
            "lower_highs": False,
            "lower_lows": False,
            "support": None,
            "resistance": None,
            "target": None,
            "alerts": []
        }

    peaks = [p for p in points if p['type'] == 'PEAK']
    troughs = [p for p in points if p['type'] == 'TROUGH']

    if len(peaks) < 2 or len(troughs) < 2:
        return {
            "trend_status": "轉折不足",
            "trend_badge": "觀望",
            "trend_color": "gray",
            "support": None,
            "resistance": None,
            "target": None,
            "alerts": []
        }

    # 最近兩組頭與底
    curr_peak = peaks[-1]
    prev_peak = peaks[-2]
    curr_trough = troughs[-1]
    prev_trough = troughs[-2]

    # 頭頭高、底底高判斷
    hh = curr_peak['price'] > prev_peak['price']  # 頭頭高
    hl = curr_trough['price'] > prev_trough['price']  # 底底高
    lh = curr_peak['price'] < prev_peak['price']  # 頭頭低
    ll = curr_trough['price'] < prev_trough['price']  # 底底低

    latest_close = float(df['Close'].iloc[-1])

    alerts = []

    # 判斷多空與狀態
    if hh and hl:
        trend_status = "多頭趨勢 (頭頭高、底底高)"
        trend_badge = "多頭 🟢"
        trend_color = "#E03131"  # 台股紅代表漲
        # 支撐為最近的底，壓力為最近的頭
        support = curr_trough['price']
        resistance = curr_peak['price']
        # 目標價：N字波等距目標 (突破前高後 target = curr_peak + (curr_peak - curr_trough))
        target = round(curr_peak['price'] + (curr_peak['price'] - curr_trough['price']), 2)

        # 警戒檢測
        if latest_close < curr_trough['price']:
            alerts.append(f"⚠️ 警訊：今日收盤價 ({latest_close}) 跌破前低支撐 ({curr_trough['price']})，多頭架構遭到破壞！")
        elif latest_close >= curr_peak['price']:
            alerts.append(f"🔥 強勢：今日收盤價 ({latest_close}) 突破前波高點 ({curr_peak['price']})，多頭續創新高！")

    elif lh and ll:
        trend_status = "空頭趨勢 (頭頭低、底底低)"
        trend_badge = "空頭 🔴"
        trend_color = "#2F9E44"  # 台股綠代表跌
        # 壓力為最近的頭，支撐為最近的底
        resistance = curr_peak['price']
        support = curr_trough['price']
        # 目標價：倒N波等距目標
        target = round(curr_trough['price'] - (curr_peak['price'] - curr_trough['price']), 2)

        # 警戒檢測
        if latest_close > curr_peak['price']:
            alerts.append(f"⚠️ 警訊：今日收盤價 ({latest_close}) 突破前高壓力 ({curr_peak['price']})，空頭架構遭到破壞！")
        elif latest_close <= curr_trough['price']:
            alerts.append(f"❄️ 弱勢：今日收盤價 ({latest_close}) 跌破前波低點 ({curr_trough['price']})，空頭續創新低！")

    else:
        trend_status = "盤整整理 (高低未同向突破)"
        trend_badge = "盤整 🟡"
        trend_color = "#F59F00"
        resistance = max(curr_peak['price'], prev_peak['price'])
        support = min(curr_trough['price'], prev_trough['price'])
        target = resistance

        if latest_close > resistance:
            alerts.append(f"🚀 突破：今日收盤價 ({latest_close}) 放量突破盤整箱頂 ({resistance})，轉多訊號！")
        elif latest_close < support:
            alerts.append(f"⚡ 跌破：今日收盤價 ({latest_close}) 跌破盤整箱底 ({support})，轉空訊號！")

    return {
        "trend_status": trend_status,
        "trend_badge": trend_badge,
        "trend_color": trend_color,
        "higher_highs": hh,
        "higher_lows": hl,
        "lower_highs": lh,
        "lower_lows": ll,
        "curr_peak": curr_peak,
        "prev_peak": prev_peak,
        "curr_trough": curr_trough,
        "prev_trough": prev_trough,
        "support": support,
        "resistance": resistance,
        "target": target,
        "alerts": alerts
    }
