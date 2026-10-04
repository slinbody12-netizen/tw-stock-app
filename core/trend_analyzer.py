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
    # 實戰平底/雙底容差：前後兩底若差距在 0.8% 以內，視為「平底/箱底有守」，不誤判為底底低破底
    trough_diff_pct = (curr_trough['price'] - prev_trough['price']) / (prev_trough['price'] + 1e-9)
    peak_diff_pct = (curr_peak['price'] - prev_peak['price']) / (prev_peak['price'] + 1e-9)

    hh = peak_diff_pct > 0.003  # 頭頭高 (過前高)
    lh = peak_diff_pct < -0.005  # 頭頭低
    is_flat_bottom = abs(trough_diff_pct) <= 0.008  # 平底/箱底支撐 (差 0.8% 以內視為平底有守)
    hl = (trough_diff_pct > 0.003) or (is_flat_bottom and hh)  # 底底高 (或平底箱底且過前高)
    ll = (trough_diff_pct < -0.008) and not is_flat_bottom  # 底底低 (實質跌破前低超過 0.8%)

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
    trend_change_date = None

    if hh and hl:
        # 多頭趨勢架構：檢查自最新高點以來，是否曾實質跌破前低支撐？
        bars_since_peak = df[df['Date'] >= curr_peak['date']] if not df.empty else pd.DataFrame()
        pullback_low = bars_since_peak['Low'].min() if not bars_since_peak.empty and 'Low' in bars_since_peak else latest_low
        tentative_troughs = [p for p in points if p['type'] == 'TROUGH' and p['date'] >= curr_peak['date']]
        if tentative_troughs:
            pullback_low = min(pullback_low, min(p['price'] for p in tentative_troughs))

        has_broken_low = pullback_low <= curr_trough['price'] * 0.998
        has_new_high = latest_close >= curr_peak['price'] * 1.003

        if has_broken_low and not has_new_high:
            trend_status = "趨勢改變為盤整 (多頭回檔破前低)"
            trend_badge = "盤整 🟡"
            trend_color = "#FFA94D"
            target = resistance
            alerts.append(f"⚠️ 警訊：股價自波段高點 ({curr_peak['price']}) 回檔最低至 ({pullback_low:.1f})，已跌破前低支撐 ({curr_trough['price']})，多頭架構遭到破壞，趨勢改變為盤整！")
            if not bars_since_peak.empty:
                break_bars = bars_since_peak[(bars_since_peak['Low'] <= curr_trough['price'] * 0.998) | (bars_since_peak['Close'] <= curr_trough['price'])]
                if not break_bars.empty:
                    trend_change_date = break_bars['Date'].iloc[0]
            if trend_change_date is None:
                trend_change_date = curr_peak['date']
        else:
            trend_status = "多頭趨勢 (頭頭高、底底高)"
            trend_badge = "多頭 🟢"
            trend_color = "#E03131"  # 台股紅代表漲
            target = round(resistance + (resistance - support), 2)
            if latest_close < support:
                alerts.append(f"⚠️ 警訊：今日收盤價 ({latest_close}) 跌破前低支撐 ({support})，多頭架構遭到破壞！")
            elif latest_close >= resistance:
                alerts.append(f"🔥 強勢：今日收盤價 ({latest_close}) 突破前波高點 ({resistance})，多頭續創新高！")
            bars_since_trough = df[df['Date'] >= curr_trough['date']] if not df.empty else pd.DataFrame()
            if not bars_since_trough.empty and prev_peak:
                break_bars = bars_since_trough[(bars_since_trough['High'] >= prev_peak['price']) | (bars_since_trough['Close'] >= prev_peak['price'])]
                if not break_bars.empty:
                    trend_change_date = break_bars['Date'].iloc[0]
            if trend_change_date is None:
                trend_change_date = curr_trough['date']

    elif lh and ll:
        # 空頭趨勢架構：檢查自最新低點以來，反彈波是否已實質超越前高壓力？
        bars_since_trough = df[df['Date'] >= curr_trough['date']] if not df.empty else pd.DataFrame()
        rebound_high = bars_since_trough['High'].max() if not bars_since_trough.empty and 'High' in bars_since_trough else latest_high
        tentative_peaks = [p for p in points if p['type'] == 'PEAK' and p['date'] >= curr_trough['date']]
        if tentative_peaks:
            rebound_high = max(rebound_high, max(p['price'] for p in tentative_peaks))

        has_passed_high = rebound_high >= curr_peak['price'] * 1.002
        has_new_low = latest_close <= curr_trough['price'] * 0.995

        if has_passed_high and not has_new_low:
            trend_status = "趨勢改變為盤整 (空頭反彈過前高)"
            trend_badge = "盤整 🟡"
            trend_color = "#FFA94D"
            target = resistance
            alerts.append(f"⚠️ 警訊：股價自波段低點 ({curr_trough['price']}) 反彈最高達 ({rebound_high:.1f})，已突破前高壓力 ({curr_peak['price']})，空頭架構遭到破壞，趨勢改變為盤整！")
            if not bars_since_trough.empty:
                break_bars = bars_since_trough[(bars_since_trough['High'] >= curr_peak['price'] * 1.002) | (bars_since_trough['Close'] >= curr_peak['price'])]
                if not break_bars.empty:
                    trend_change_date = break_bars['Date'].iloc[0]
            if trend_change_date is None:
                trend_change_date = curr_trough['date']
        else:
            trend_status = "空頭趨勢 (頭頭低、底底低)"
            trend_badge = "空頭 🔴"
            trend_color = "#2F9E44"  # 台股綠代表跌
            target = round(support - (resistance - support), 2)
            if latest_close <= support:
                alerts.append(f"❄️ 弱勢：今日收盤價 ({latest_close}) 跌破前波低點 ({support})，空頭續創新低！")
            bars_since_peak = df[df['Date'] >= curr_peak['date']] if not df.empty else pd.DataFrame()
            if not bars_since_peak.empty and prev_trough:
                break_bars = bars_since_peak[(bars_since_peak['Low'] <= prev_trough['price']) | (bars_since_peak['Close'] <= prev_trough['price'])]
                if not break_bars.empty:
                    trend_change_date = break_bars['Date'].iloc[0]
            if trend_change_date is None:
                trend_change_date = curr_peak['date']

    else:
        trend_status = "盤整整理 (高低未同向突破)"
        trend_badge = "盤整 🟡"
        trend_color = "#F59F00"
        target = resistance
        if latest_close > resistance:
            alerts.append(f"🚀 突破：今日收盤價 ({latest_close}) 放量突破盤整箱頂 ({resistance})，轉多訊號！")
        elif latest_close < support:
            alerts.append(f"⚡ 跌破：今日收盤價 ({latest_close}) 跌破盤整箱底 ({support})，轉空訊號！")
        trend_change_date = max(curr_peak['date'], curr_trough['date'])

    # 計算轉變天數與格式化日期
    days_since_change = 99
    trend_change_date_str = ""
    if trend_change_date is not None and not df.empty:
        t_dt = pd.to_datetime(trend_change_date)
        # 嚴密防護：台股週末休市，若出現週末日期自動對齊至最近之有效交易日(週五)
        if t_dt.weekday() == 5:
            t_dt = t_dt - pd.Timedelta(days=1)
        elif t_dt.weekday() == 6:
            t_dt = t_dt - pd.Timedelta(days=2)
        trend_change_date = t_dt
        trend_change_date_str = t_dt.strftime('%m/%d')
        days_since_change = len(df[df['Date'] >= trend_change_date])

    # -------------------------------------------------------------
    # 老朱戰法：檢測轉多頭前是否經歷超過 2 個月（>= 40 個交易日）之充分盤整洗盤
    # -------------------------------------------------------------
    # 老朱戰法：檢測轉多頭前是否經歷超過 2 個月（>= 40 個交易日）之充分盤整洗盤
    # 實戰心法：「橫有多長，豎有多高」，長盤超過 2 個月爆發之股票，波段漲幅往往驚人！
    # 精準計算：採用朱家泓標準箱型整理振幅上限 (<= 17%)，連續回溯，不穿透前波主升/主跌段
    # -------------------------------------------------------------
    cons_duration_bars = 0
    cons_duration_months = 0.0
    cons_start_date_str = ""
    cons_box_low = 0.0
    cons_box_high = 0.0
    cons_amp_pct = 0.0
    is_cons_over_2m = False

    if trend_status.startswith("多頭趨勢") and trend_change_date is not None and not df.empty:
        idx_list = df.index[df['Date'] <= trend_change_date].tolist()
        if idx_list:
            t_idx = idx_list[-1]
            max_amp = 0.18  # 精準標準箱型振幅上限 (18%)
            best_bars = 0
            t_dt = pd.to_datetime(trend_change_date)
            pts_at_or_before = [p for p in points if p['date'] <= t_dt]

            for lookback in range(5, min(140, t_idx)):
                slice_df = df.iloc[t_idx - lookback : t_idx + 1]
                h_max = float(slice_df['High'].max())
                l_min = float(slice_df['Low'].min())
                amp = (h_max - l_min) / (l_min + 1e-9)
                if amp > max_amp:
                    break

                cur_dt = df.iloc[t_idx - lookback]['Date']
                # 檢查 cur_dt 是否恰好越過了前一個推升段的頂峰
                # 若在 cur_dt 之前的轉折點是連續 2 個以上的底底高、頭頭高，且當前點是該推升段頂點
                pts_at = [p for p in pts_at_or_before if p['date'] <= cur_dt]
                if lookback >= 20 and len(pts_at) >= 3:
                    p_last = pts_at[-1]
                    if p_last['type'] == 'PEAK' and p_last['price'] == h_max:
                        p_prev_peaks = [p for p in pts_at[:-1] if p['type'] == 'PEAK']
                        p_prev_troughs = [p for p in pts_at[:-1] if p['type'] == 'TROUGH']
                        if len(p_prev_peaks) >= 2 and len(p_prev_troughs) >= 2:
                            if p_prev_peaks[-1]['price'] < p_last['price'] and p_prev_peaks[-2]['price'] < p_prev_peaks[-1]['price']:
                                if p_prev_troughs[-1]['price'] > p_prev_troughs[-2]['price']:
                                    best_bars = lookback
                                    break
                best_bars = lookback

            if best_bars >= 10:
                cons_duration_bars = best_bars
                cons_duration_months = round(cons_duration_bars / 20.0, 1)
                is_cons_over_2m = (cons_duration_bars >= 40)
                
                s_row = df.iloc[t_idx - cons_duration_bars]
                cons_start_date_str = s_row['Date'].strftime('%m/%d')
                
                slice_box = df.iloc[t_idx - cons_duration_bars : t_idx + 1]
                cons_box_high = round(float(slice_box['High'].max()), 2)
                cons_box_low = round(float(slice_box['Low'].min()), 2)
                cons_amp_pct = round(((cons_box_high - cons_box_low) / (cons_box_low + 1e-9)) * 100, 1)

                if is_cons_over_2m and days_since_change <= 5:
                    alerts.insert(0, f"🔥 【老朱戰法·橫有多長豎有多高】：本檔在突破前於 {cons_start_date_str}～{trend_change_date_str} 密集箱型整理（{cons_box_low}～{cons_box_high} 元，振幅 {cons_amp_pct}%）長達 {cons_duration_bars} 個交易日（約 {cons_duration_months} 個月），今日剛確立多頭趨勢！長盤沉澱後的初升第一根爆發力極強，常展開翻倍大波段行情！")

    return {
        "trend_status": trend_status,
        "trend_badge": trend_badge,
        "trend_color": trend_color,
        "trend_change_date": trend_change_date,
        "trend_change_date_str": trend_change_date_str,
        "days_since_change": days_since_change,
        "is_fresh_change": (days_since_change <= 4),
        "cons_duration_bars": cons_duration_bars,
        "cons_duration_months": cons_duration_months,
        "cons_start_date_str": cons_start_date_str,
        "cons_box_low": cons_box_low,
        "cons_box_high": cons_box_high,
        "cons_amp_pct": cons_amp_pct,
        "is_cons_over_2m": is_cons_over_2m,
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
