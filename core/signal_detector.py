# -*- coding: utf-8 -*-
"""
關鍵訊號與策略偵測核心 (Signal Detector Pro)
全面升級對標專業旗艦 App 全套策略：
1. 波段 8 大子策略：
   - 頭高底高 (Higher Highs & Higher Lows)
   - 回後準進場 (Pullback Ready for Entry)
   - 底部起漲 (Bottom Breakout)
   - 高檔起漲 (High-level Continuation Breakout)
   - 雙線黃金交叉 (5MA Cross Above 20MA)
   - 一字底 (Flat Base Breakout)
   - N字底 (N-pattern Bottom)
   - 圓弧底 (Rounding Bottom)
2. 長抱 (Long Hold / Buy & Hold)
3. 一點鐘 (1:00 PM Pre-Close Strategy)
4. 盤中強勢 (Intraday Strong)
5. 鎖股池 3 階段 (等突破、高檔等回檔、回檔等上漲)
6. 助教實戰安全評級 (安全首選 🟢 / 警訊注意 🟡 / 嚴禁追高 🔴)
"""

import pandas as pd
import numpy as np

def detect_signals(df: pd.DataFrame, trend_info: dict):
    """
    偵測所有關鍵技術分析訊號與官方 App 策略
    """
    signals = []
    signals_dict = {
        # 波段 8 大子策略
        "higher_highs_lows": False,   # 頭高底高
        "pullback_buy": False,        # 回後準進場
        "bottom_breakout": False,     # 底部起漲
        "high_breakout": False,       # 高檔起漲
        "golden_cross_5_20": False,   # 雙線黃金交叉
        "flat_base_breakout": False,  # 一字底
        "n_pattern_bottom": False,    # N字底
        "rounding_bottom": False,     # 圓弧底
        
        # 其他大類
        "long_hold": False,           # 長抱
        "one_pm_strategy": False,     # 一點鐘
        "intraday_strong": False,     # 盤中強勢
        
        # 鎖股池狀態
        "watchlist_stage": "觀察中",   # 等突破 / 高檔等回檔 / 回檔等上漲
        
        # 輔助技術分析
        "bullish_alignment": False,   # 均線多頭排列
        "safety_rating": "🟢 安全首選",# 實戰安全評級
        "safety_reasons": [],         # 評級原因說明
        "chili_count": 1,             # 動能辣椒數 (1~3)
        "deduction": {}               # 均線扣抵
    }

    if len(df) < 15:
        return signals_dict, signals

    last = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3] if len(df) > 2 else prev

    c = round(float(last['Close']), 2)
    o = round(float(last['Open']), 2)
    h = round(float(last['High']), 2)
    l = round(float(last['Low']), 2)
    v = float(last['Volume'])
    v_ma20 = float(last['Vol_MA20']) if not np.isnan(last['Vol_MA20']) else v

    prev_c = round(float(prev['Close']), 2)
    change_pct = ((c - prev_c) / prev_c) * 100 if prev_c > 0 else 0
    is_red = (c >= o)

    sma5 = round(float(last['SMA_5']), 2)
    sma10 = round(float(last['SMA_10']), 2) if 'SMA_10' in last and not np.isnan(last['SMA_10']) else sma5
    sma20 = round(float(last['SMA_20']), 2) if 'SMA_20' in last and not np.isnan(last['SMA_20']) else sma5
    sma60 = round(float(last.get('SMA_60', sma20)), 2)

    prev_sma5 = round(float(prev['SMA_5']), 2)
    prev_sma20 = round(float(prev['SMA_20']), 2) if 'SMA_20' in prev and not np.isnan(prev['SMA_20']) else prev_sma5

    # 1. 均線扣抵
    deduction = {}
    if len(df) >= 6:
        d5 = float(df.iloc[-5]['Close'])
        deduction['5MA'] = {"price": d5, "status": "扣低助漲 ↗" if c >= d5 else "扣高下彎 ↘"}
    if len(df) >= 21:
        d20 = float(df.iloc[-20]['Close'])
        deduction['20MA'] = {"price": d20, "status": "扣低助漲 ↗" if c >= d20 else "扣高下彎 ↘"}
    if len(df) >= 61:
        d60 = float(df.iloc[-60]['Close'])
        deduction['60MA'] = {"price": d60, "status": "扣低助漲 ↗" if c >= d60 else "扣高下彎 ↘"}
    signals_dict['deduction'] = deduction

    # 2. 均線多頭排列
    if sma5 > sma10 > sma20 > sma60:
        signals_dict['bullish_alignment'] = True

    # 3. 連漲天數
    up_days = 0
    for j in range(len(df) - 1, max(0, len(df) - 6), -1):
        if df.iloc[j]['Close'] > df.iloc[j - 1]['Close']:
            up_days += 1
        else:
            break

    # 4. 前方 30 天爆量長黑排查
    heavy_black_ks = []
    sub30 = df.iloc[-30:] if len(df) >= 30 else df
    for _, r in sub30.iterrows():
        vol = r['Volume']
        vma = r.get('Vol_MA20', 0)
        is_bk = (r['Close'] < r['Open']) or ((r['High'] - max(r['Open'], r['Close'])) > (r['High'] - r['Low']) * 0.4)
        if vma > 0 and vol >= vma * 1.6 and is_bk:
            heavy_black_ks.append({
                "date": r['Date'].strftime('%m/%d'),
                "high": round(float(r['High']), 2),
                "ratio": round(vol / vma, 1)
            })

    unresolved_blacks = [b for b in heavy_black_ks if b['high'] >= c]

    # 5. 辣椒動能指標 (1~3 根)
    chili = 1
    vol_ratio = v / v_ma20 if v_ma20 > 0 else 1.0
    if vol_ratio >= 2.0 or change_pct >= 5.0:
        chili = 3
    elif vol_ratio >= 1.3 or change_pct >= 2.5:
        chili = 2
    signals_dict['chili_count'] = chili

    # ----------------------------------------------------
    # 策略 A：頭高底高 (六字訣多頭確認)
    # 實戰心法：必須同時滿足「波段頭頭高」且「波段底底高」，方為多頭架構！
    # ----------------------------------------------------
    is_bull = bool(trend_info.get('higher_highs', False) and trend_info.get('higher_lows', False))
    if is_bull:
        signals_dict['higher_highs_lows'] = True
        signals.append("頭高底高 (多頭走勢確認)")

    # ----------------------------------------------------
    # 策略 B：雙線黃金交叉 (5MA 向上穿過 20MA)
    # 實戰心法鐵律：
    # 1. 5MA 操盤線必須「向上翻揚」(sma5 > prev_sma5)，嚴禁 5MA 向下彎！
    # 2. 必須由下往上實質穿越突破 (昨日 5MA <= 20MA，今日 5MA >= 20MA，或近 2 日剛完成金叉)
    # ----------------------------------------------------
    is_5ma_rising = (sma5 >= prev_sma5)
    is_cross_today = (sma5 >= sma20 and prev_sma5 <= prev_sma20 and is_5ma_rising)
    is_cross_recent = (sma5 >= sma20 and float(prev2['SMA_5']) <= float(prev2['SMA_20']) and is_5ma_rising) if len(df) > 2 else False
    if is_cross_today or is_cross_recent:
        signals_dict['golden_cross_5_20'] = True
        signals.append("剛出現雙線黃金交叉 (5MA 向上穿過 20MA)")

    # ----------------------------------------------------
    # 策略 C：回後準進場 (經典回後買上漲進場訊號)
    # 實戰心法鐵律：
    # 1. 前幾天拉回測均線 (5MA/20MA) 有守，支撐未破
    # 2. 今日收轉折紅K站回 5MA 操盤線之上 (c >= sma5)
    # 3. 5MA 操盤線必須「走平或向上翻揚」(is_5ma_rising)，若操盤線仍在下彎，代表短線助跌，嚴禁買進！
    # ----------------------------------------------------
    support = trend_info.get('support', 0) or (c * 0.93)
    resistance = trend_info.get('resistance', 0) or (c * 1.08)
    recent_lows = df.iloc[-4:-1]['Low'].min() if len(df) >= 4 else l
    tested_ma = (recent_lows <= sma20 * 1.03 or l <= sma5 * 1.015)
    not_broken_support = l >= support * 0.985
    stand_on_5ma = (c >= sma5)

    if (is_bull or signals_dict['golden_cross_5_20'] or sma5 >= sma20) and tested_ma and not_broken_support and is_red and stand_on_5ma and is_5ma_rising:
        signals_dict['pullback_buy'] = True
        signals.append("回後準進場 (拉回測線有守，轉折紅K站回5MA且操盤線翻揚)")

    # ----------------------------------------------------
    # 策略 D：底部起漲 (低檔整理首度帶量長紅突破)
    # ----------------------------------------------------
    past20_low = df.iloc[-25:-5]['Low'].min() if len(df) >= 25 else l
    is_near_bottom = (c <= past20_low * 1.15) or (sma20 <= sma60 * 1.02)
    is_breakout_today = (c >= sma5 and c >= sma20 and is_red and (change_pct >= 0.5 or vol_ratio >= 1.1) and is_5ma_rising)
    if is_near_bottom and is_breakout_today:
        signals_dict['bottom_breakout'] = True
        signals.append("底部起漲 (低檔放量突破均線)")

    # ----------------------------------------------------
    # 策略 E：高檔起漲 (強勢多頭高檔休息後再發動)
    # ----------------------------------------------------
    if c >= sma60 and sma5 > sma20 and change_pct >= 1.5 and is_red and (c >= df.iloc[-10:-1]['High'].max() * 0.99) and is_5ma_rising:
        signals_dict['high_breakout'] = True
        signals.append("高檔起漲 (多頭高檔突破再創高)")

    # ----------------------------------------------------
    # 策略 F：一字底 (60天狹幅橫盤平躺糾結 + 放量突破)
    # ----------------------------------------------------
    if len(df) >= 40:
        sub_period = df.iloc[-50:-1] if len(df) >= 50 else df.iloc[:-1]
        rng_max = sub_period['High'].max()
        rng_min = sub_period['Low'].min()
        amplitude = (rng_max - rng_min) / (rng_min + 1e-9)
        ma_squeeze = abs(sma5 - sma20) / (sma20 + 1e-9)
        if amplitude <= 0.22 and ma_squeeze <= 0.05 and c >= rng_max * 0.985 and is_red and is_5ma_rising:
            signals_dict['flat_base_breakout'] = True
            signals.append("一字底 (均線高度糾結放量突破)")

    # ----------------------------------------------------
    # 策略 G：N字底 (第二隻腳不破前低，向上推升)
    # ----------------------------------------------------
    if len(df) >= 20:
        sub = df.iloc[-25:]
        min_idx = sub['Low'].idxmin()
        if min_idx < sub.index[-5]:
            low1 = df.loc[min_idx, 'Low']
            after_low1 = sub.loc[min_idx:]
            if len(after_low1) >= 6:
                peak_idx = after_low1['High'].idxmax()
                if peak_idx > min_idx and peak_idx < sub.index[-2]:
                    peak1 = df.loc[peak_idx, 'High']
                    after_peak = after_low1.loc[peak_idx:]
                    low2 = after_peak['Low'].min()
                    if low2 > low1 and c >= sma5 and is_red and c < peak1 * 1.05 and is_5ma_rising:
                        signals_dict['n_pattern_bottom'] = True
                        signals.append("N字底 (第二隻腳打樁有守突破)")

    # ----------------------------------------------------
    # 策略 H：圓弧底 (U型底部走平翻揚)
    # ----------------------------------------------------
    if len(df) >= 25:
        ma20_diff_recent = sma20 - prev_sma20
        ma20_diff_old = float(df.iloc[-10]['SMA_20']) - float(df.iloc[-15]['SMA_20'])
        if ma20_diff_old <= 0 and ma20_diff_recent >= -0.05 and c >= sma5 and is_red:
            signals_dict['rounding_bottom'] = True
            signals.append("圓弧底 (U型圓弧打底完成翻揚)")

    # ----------------------------------------------------
    # 策略 I：長抱 (均線長期多排穩健上揚)
    # ----------------------------------------------------
    if len(df) >= 20:
        past20_above = (df.iloc[-20:]['Close'] >= df.iloc[-20:]['SMA_20'] * 0.97).sum()
        if past20_above >= 16 and sma5 >= sma20 and sma20 >= sma60:
            signals_dict['long_hold'] = True
            signals.append("長抱 (多頭長線穩健推升)")

    # ----------------------------------------------------
    # 策略 J：一點鐘 (1:00 PM 尾盤選股 - 1:1 對齊專業 App 官方規則)
    # ----------------------------------------------------
    if is_red and c >= sma5 and is_5ma_rising and change_pct >= 0.5:
        signals_dict['one_pm_strategy'] = True
        signals.append("一點鐘 (尾盤強勢收紅站上操盤線)")

    # ----------------------------------------------------
    # 策略 K：盤中強勢
    # ----------------------------------------------------
    if change_pct >= 1.5 and is_red and c >= sma5 and vol_ratio >= 1.1:
        signals_dict['intraday_strong'] = True
        signals.append("盤中強勢 (量價齊揚強勁攻擊)")

    # ----------------------------------------------------
    # 盤整狀態辨識與盤整末端即將突破預警 (教學手冊重點)
    # ----------------------------------------------------
    is_consolidation = False
    consolidation_breakout_imminent = False
    if len(df) >= 15:
        past12 = df.iloc[-12:]
        box_high = float(past12['High'].max())
        box_low = float(past12['Low'].min())
        box_amp = (box_high - box_low) / (box_low + 1e-9)
        ma_squeeze = abs(sma5 - sma20) / (sma20 + 1e-9)
        
        # 無明顯底底高/頭頭高，且振幅小於 7.5%，均線糾結
        if not is_bull and box_amp <= 0.08 and ma_squeeze <= 0.035:
            is_consolidation = True
            # 若量縮至均量 60% 以下 (極致窒息量) 且收在箱頂 2.5% 內
            if vol_ratio <= 0.65 and c >= box_high * 0.975:
                consolidation_breakout_imminent = True
                signals.append("⏳ 盤整末端即將表態 (量縮窒息，逼近箱頂等待放量突破)")
            else:
                signals.append("⏸️ 進入箱型盤整 (無頭頭高/底底高，暫勿躁進，等待方向)")

    signals_dict['is_consolidation'] = is_consolidation
    signals_dict['consolidation_breakout_imminent'] = consolidation_breakout_imminent

    # ----------------------------------------------------
    # 暴漲 2~3 倍高檔警示 (教學手冊重點：非起漲點，嚴禁長抱)
    # ----------------------------------------------------
    is_multi_bagger = False
    bagger_multiple = 1.0
    if len(df) >= 60:
        check_period = df.iloc[-120:] if len(df) >= 120 else df
        lowest_price = float(check_period['Low'].min())
        if lowest_price > 0:
            bagger_multiple = round(c / lowest_price, 2)
            if bagger_multiple >= 1.95:  # 漲幅達 100% (2倍) 以上
                is_multi_bagger = True

    signals_dict['is_multi_bagger'] = is_multi_bagger
    signals_dict['bagger_multiple'] = bagger_multiple

    # ----------------------------------------------------
    # 買兩張（長短配）實戰操盤指引 (經典配置)
    # ----------------------------------------------------
    signals_dict['two_tranches'] = {
        "long_defend": sma20,     # 長線防守 20MA
        "short_defend": sma5,     # 短線防守 5MA
        "advice": f"張數 1 (長線)：守 20MA ({sma20:.2f}元)，未跌破一路長抱大波段；張數 2 (短線/波段)：守 5MA ({sma5:.2f}元) 或雙線死亡交叉獲利出場。"
    }

    # ----------------------------------------------------
    # 支撐與壓力詳細分類標記
    # ----------------------------------------------------
    res_type = "頭壓 (波段前高)"
    res_price = round(resistance, 2)
    if unresolved_blacks:
        res_type = f"爆量黑K壓 ({unresolved_blacks[-1]['date']})"
        res_price = unresolved_blacks[-1]['high']
    elif is_consolidation:
        res_type = "箱型整理上緣壓"

    sup_type = "底撐 (波段前底)"
    sup_price = round(support, 2)
    if l <= sma20 * 1.02 and c >= sma20:
        sup_type = "趨勢線撐 (20MA)"
        sup_price = sma20

    signals_dict['support_detail'] = {"price": sup_price, "type": sup_type}
    signals_dict['resistance_detail'] = {"price": res_price, "type": res_type}

    # ----------------------------------------------------
    # 短線 3~5 天波段價差專屬操盤卡 (量身打造風報比與停損停利)
    # ----------------------------------------------------
    stop_loss = round(min(l, sup_price), 2)
    risk = max(0.01, c - stop_loss)
    reward = max(0.01, res_price - c)
    rr_ratio = round(reward / risk, 1)
    risk_pct = round((risk / c) * 100, 1)
    reward_pct = round((reward / c) * 100, 1)

    signals_dict['swing_3_5d'] = {
        "stop_loss": stop_loss,
        "ma5_defend": sma5,
        "target_res": res_price,
        "rr_ratio": rr_ratio,
        "risk_pct": risk_pct,
        "reward_pct": reward_pct
    }

    # ----------------------------------------------------
    # 鎖股池 3 階段管理 (等突破 / 高檔等回檔 / 回檔等上漲)
    # ----------------------------------------------------
    bias5 = float(last.get('BIAS_5', 0))
    bias20 = float(last.get('BIAS_20', 0))

    if up_days >= 3 or bias20 >= 8.0 or bias5 >= 6.0:
        signals_dict['watchlist_stage'] = "高檔等回檔"
    elif (is_bull or sma5 >= sma20) and not is_red and c <= sma5 * 1.01:
        signals_dict['watchlist_stage'] = "回檔等上漲"
    elif abs(sma5 - sma20) / (sma20 + 1e-9) <= 0.02 and abs(change_pct) < 1.5:
        signals_dict['watchlist_stage'] = "等突破"
    elif is_bull:
        signals_dict['watchlist_stage'] = "回檔等上漲"
    else:
        signals_dict['watchlist_stage'] = "等突破"

    # ----------------------------------------------------
    # 助教把關：實戰安全評級 (Safety Rating)
    # ----------------------------------------------------
    safety_reasons = []
    if is_multi_bagger:
        safety_reasons.append(f"波段已大漲 {bagger_multiple:.1f} 倍高檔警示！非底部起漲，長線空間已不大，嚴禁長抱，僅限極短線操作")
    if up_days >= 3:
        safety_reasons.append(f"連續上漲 {up_days} 天，短線追高易回檔")
    if unresolved_blacks:
        latest_bk = unresolved_blacks[-1]
        safety_reasons.append(f"前方 {latest_bk['date']} 有 {latest_bk['ratio']} 倍爆量黑K套牢賣壓 ({latest_bk['high']} 元)")
    if c < sma60 and sma20 < sma60:
        safety_reasons.append("季線 (60MA) 下彎壓制，屬空方反彈非主升")

    if is_multi_bagger or unresolved_blacks or (up_days >= 3 and bias20 >= 8.0):
        signals_dict['safety_rating'] = "🟡 警訊注意"
    elif up_days >= 4 or bias20 >= 12.0:
        signals_dict['safety_rating'] = "🔴 嚴禁追高"
    else:
        signals_dict['safety_rating'] = "🟢 安全首選"

    signals_dict['safety_reasons'] = safety_reasons

    return signals_dict, signals
