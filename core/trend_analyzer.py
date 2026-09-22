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
    依據《技術分析全攻略》六字訣與正統量化技術分析原則：
    - 排除行進間尚未由 5MA 確認之「暫高」與「暫底」，僅以實質確認之「頭」與「底」作為關鍵依據。
    - 壓力線：若當前價位上方有前波已確認頭部，取上方最近之已確認壓力（若現價已突破最近前高，自動向上推移至上層壓力）。
    - 支撐線：尋找當前價位下方最近之已確認底部防守關卡。
    - 多頭：頭頭高、底底高 (上升趨勢)
    - 空頭：頭頭低、底底低 (下跌趨勢)
    - 盤整：高低未同向突破 (箱型或收斂)
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

    # 1. 僅保留已確認的頭部與底部（排除行進間尚未由 5MA 轉折確認之暫高與暫底）
    confirmed_peaks = [p for p in points if p['type'] == 'PEAK' and not p.get('is_tentative', False)]
    confirmed_troughs = [p for p in points if p['type'] == 'TROUGH' and not p.get('is_tentative', False)]

    # 若確認點數不足，降級採用全部點位（避免極短歷史資料或剛上市股票報錯）
    peaks = confirmed_peaks if len(confirmed_peaks) >= 2 else [p for p in points if p['type'] == 'PEAK']
    troughs = confirmed_troughs if len(confirmed_troughs) >= 2 else [p for p in points if p['type'] == 'TROUGH']

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

    # 最近兩組實質已確認頭與底
    curr_peak = peaks[-1]
    prev_peak = peaks[-2]
    curr_trough = troughs[-1]
    prev_trough = troughs[-2]

    # 頭頭高、底底高判斷 (基於已確認之實質頭底)
    hh = curr_peak['price'] > prev_peak['price']  # 頭頭高
    hl = curr_trough['price'] > prev_trough['price']  # 底底高
    lh = curr_peak['price'] < prev_peak['price']  # 頭頭低
    ll = curr_trough['price'] < prev_trough['price']  # 底底低

    latest_close = float(df['Close'].iloc[-1])
    latest_high = float(df['High'].iloc[-1]) if 'High' in df else latest_close
    latest_low = float(df['Low'].iloc[-1]) if 'Low' in df else latest_close

    alerts = []

    # -------------------------------------------------------------
    # 關鍵支撐與壓力計算（對齊正統量化技術分析邏輯）
    # -------------------------------------------------------------
    curr_ref_high = max(latest_close, latest_high)
    curr_ref_low = min(latest_close, latest_low)

    # 壓力判斷：優先尋找位於當前價位上方最近之已確認頭部
    overhead_peaks = [p for p in reversed(peaks) if p['price'] > curr_ref_high]
    if overhead_peaks:
        # 當前價格上方有已確認前高：取最近之實質壓力 (若今天突破了最近前高，自動向上對齊更上層壓力)
        resistance = overhead_peaks[0]['price']
    else:
        # 當前價格已突破所有近期確認頭部 (創波段新高)：以波段最高頭或最近頭為基準
        resistance = max(p['price'] for p in peaks)

    # 支撐判斷：尋找位於當前價位下方最近之已確認底部
    underneath_troughs = [p for p in reversed(troughs) if p['price'] < curr_ref_low]
    if underneath_troughs:
        # 取當前價格下方最近之已確認支撐 (回檔防守點)
        support = underneath_troughs[0]['price']
    else:
        # 當前價格已跌破近期所有確認低點：以波段最低底為基準
        support = min(p['price'] for p in troughs)

    # -------------------------------------------------------------
    # 趨勢狀態判定與目標價推估
    # -------------------------------------------------------------
    if hh and hl:
        trend_status = "多頭趨勢 (頭頭高、底底高)"
        trend_badge = "多頭 🟢"
        trend_color = "#E03131"  # 台股紅代表漲
        # 目標價：N字波等距目標 (突破前高後 target = resistance + (resistance - support))
        target = round(resistance + (resistance - support), 2)

        # 警戒檢測
        if latest_close < support:
            alerts.append(f"⚠️ 警訊：今日收盤價 ({latest_close}) 跌破前低支撐 ({support})，多頭架構遭到破壞！")
        elif latest_close >= resistance:
            alerts.append(f"🔥 強勢：今日收盤價 ({latest_close}) 突破前波高點 ({resistance})，多頭續創新高！")

    elif lh and ll:
        if latest_close > curr_peak['price']:
            trend_status = "空頭反彈過前高 (架構破壞)"
            trend_badge = "轉強 🟡"
            trend_color = "#F59F00"
            target = resistance
            alerts.append(f"⚠️ 警訊：今日收盤價 ({latest_close}) 突破前高壓力 ({curr_peak['price']})，空頭架構遭到破壞！")
        else:
            trend_status = "空頭趨勢 (頭頭低、底底低)"
            trend_badge = "空頭 🔴"
            trend_color = "#2F9E44"  # 台股綠代表跌
            # 目標價：倒N波等距目標
            target = round(support - (resistance - support), 2)
            if latest_close <= support:
                alerts.append(f"❄️ 弱勢：今日收盤價 ({latest_close}) 跌破前波低點 ({support})，空頭續創新低！")

    else:
        trend_status = "盤整整理 (高低未同向突破)"
        trend_badge = "盤整 🟡"
        trend_color = "#F59F00"
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
