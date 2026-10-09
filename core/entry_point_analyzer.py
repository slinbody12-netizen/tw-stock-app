# -*- coding: utf-8 -*-
"""
老朱三層進場階梯戰法量化核心 (Three-Tier Entry Hierarchy Engine)
依據朱家泓老師實戰體系：
- 第 1 買點 (B1)：底部轉折試單點 (打第二隻腳底底高 / 紅K過5MA / 建議倉位 20%~30%)
- 第 2 買點 (B2)：標準多頭確立買點 (帶量過前高頸線 / 頭頭高+底底高全成立 / 建議倉位 60%~70%)
- 第 3 買點 (B3)：波段加碼追價點 (帶量突破中長期大下降切線或大箱頂 / 順勢加碼或強勢追價)

升級特色：
1. 完整預算進場區間 (突破價 ~ +2.5%) 與禁追天花板 (+5.0%)。
2. 前瞻預測下一階：未達標前即提前推算進場價、出場停損價，並顯示即時價差與距買點距離。
3. 盤中即時狀態響應：根據最新撮合價即時判定「預備伏擊 / 黃金買點 / 輕度追價 / 買點已過勿追」。
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

def calculate_three_tier_entry(
    df: pd.DataFrame, 
    points: list, 
    trend_info: dict, 
    signals_dict: dict,
    pattern_geo: Optional[dict] = None
) -> Dict[str, Any]:
    """
    計算個股在老朱三層進場階梯戰法中的所屬階梯、關鍵價位、進場區間、禁追上限、建議倉位與防守停損
    """
    if df is None or df.empty or len(df) < 10:
        return {
            "current_stage": "NONE",
            "stage_code": 0,
            "stage_name": "資料不足",
            "stage_verdict": "歷史轉折資料不足，暫無法推算進場階梯",
            "badge_html": "",
            "badge_text": "",
            "b1": None,
            "b2": None,
            "b3": None
        }

    latest = df.iloc[-1]
    c = float(latest['Close'])
    sma5 = float(latest.get('SMA_5', c))
    up_days = int(signals_dict.get('up_days', 0))

    if pattern_geo is None:
        try:
            from core.pattern_geometry import detect_pattern_geometries
            pattern_geo = detect_pattern_geometries(df, signals_dict)
        except Exception:
            pattern_geo = {}

    confirmed_peaks = [p for p in points if p['type'] == 'PEAK' and not p.get('is_tentative', False)]
    confirmed_troughs = [p for p in points if p['type'] == 'TROUGH' and not p.get('is_tentative', False)]

    all_peaks = [p for p in points if p['type'] == 'PEAK']
    all_troughs = [p for p in points if p['type'] == 'TROUGH']

    peaks = confirmed_peaks if len(confirmed_peaks) >= 1 else all_peaks
    troughs = confirmed_troughs if len(confirmed_troughs) >= 2 else all_troughs

    # 基礎資訊容器
    b1_info = {
        "tier": 1,
        "name": "第 1 買點【底部轉折試單】",
        "status": "WAITING",  # WAITING / ACTIVE / CAUTION / MISSED
        "price": None,
        "entry_range_low": None,
        "entry_range_high": None,
        "chase_ceiling": None,
        "stop_loss": None,
        "position": "20% ～ 30% (小部位試單)",
        "condition": "打第二隻腳不破前低，紅K站上5MA",
        "date": "",
        "desc": "",
        "distance_price": 0.0,
        "distance_pct": 0.0,
        "status_text": "",
        "status_hint": ""
    }

    b2_info = {
        "tier": 2,
        "name": "第 2 買點【標準多頭確立】",
        "status": "WAITING",  # WAITING / ACTIVE / CAUTION / MISSED
        "price": None,
        "entry_range_low": None,
        "entry_range_high": None,
        "chase_ceiling": None,
        "stop_loss": None,
        "position": "60% ～ 70% (標準重倉進場)",
        "condition": "帶量突破前高頸線，頭頭高+底底高全成立",
        "date": "",
        "desc": "",
        "distance_price": 0.0,
        "distance_pct": 0.0,
        "status_text": "",
        "status_hint": ""
    }

    b3_info = {
        "tier": 3,
        "name": "第 3 買點【波段加碼追價】",
        "status": "WAITING",  # WAITING / ACTIVE / CAUTION / MISSED
        "price": None,
        "entry_range_low": None,
        "entry_range_high": None,
        "chase_ceiling": None,
        "stop_loss": None,
        "position": "順勢加碼 / 強勢短線追價",
        "condition": "帶量突破大格局下降切線或大箱頂",
        "date": "",
        "desc": "",
        "distance_price": 0.0,
        "distance_pct": 0.0,
        "status_text": "",
        "status_hint": ""
    }

    # =========================================================================
    # 1. 計算 B1 (第二隻腳底底高 / 或止跌打底試單點)
    # =========================================================================
    has_b1 = False
    is_v_rebound = False
    b1_trigger_idx = len(df) - 1
    b1_has_surged = False
    b1_surge_peak = 0.0

    if len(troughs) >= 2:
        leg1 = troughs[-2]
        leg2 = troughs[-1]
        if leg2['price'] >= leg1['price'] * 0.992:
            has_b1 = True
            b1_stop = round(float(leg2['price']), 2)
            b1_date = leg2['date'].strftime('%m/%d') if hasattr(leg2['date'], 'strftime') else str(leg2['date'])[:10]
            
            leg2_idx = leg2.get('index', 0)
            b1_trigger_price = b1_stop
            b1_trigger_idx = leg2_idx
            for k in range(leg2_idx, len(df)):
                r = df.iloc[k]
                if r['Close'] >= r.get('SMA_5', r['Close']) and r['Close'] >= r['Open']:
                    b1_trigger_price = round(float(r['Close']), 2)
                    b1_trigger_idx = k
                    break

            b1_info['price'] = b1_trigger_price
            b1_info['entry_range_low'] = b1_trigger_price
            b1_info['entry_range_high'] = round(b1_trigger_price * 1.025, 2)
            b1_info['chase_ceiling'] = round(b1_trigger_price * 1.050, 2)
            b1_info['stop_loss'] = b1_stop
            b1_info['date'] = b1_date
            b1_info['desc'] = f"守穩第二隻腳 {b1_stop} 元 (高於前低 {leg1['price']:.2f})，紅K站上5MA試單"

            # 檢查自發動以來，股價是否曾大漲衝破禁追天花板
            if b1_trigger_idx < len(df):
                sub_df = df.iloc[b1_trigger_idx:]
                b1_surge_peak = round(float(sub_df['High'].max()), 2)
                if b1_surge_peak > b1_info['chase_ceiling']:
                    b1_has_surged = True

    # 若最近一底為最低底，但從該底一路紅K大彈超過 8% 或已過前高 (如 3013 V型反轉第一波)
    if not has_b1 and len(troughs) >= 1:
        last_trough = troughs[-1]
        gain_from_trough = (c - last_trough['price']) / (last_trough['price'] + 1e-9)
        if gain_from_trough >= 0.08:
            is_v_rebound = True
            b1_trigger_price = round(float(last_trough['price'] * 1.02), 2)
            b1_stop = round(float(last_trough['price']), 2)
            b1_date = last_trough['date'].strftime('%m/%d') if hasattr(last_trough['date'], 'strftime') else str(last_trough['date'])[:10]
            b1_trigger_idx = last_trough.get('index', 0)
            
            b1_info['price'] = b1_trigger_price
            b1_info['entry_range_low'] = b1_trigger_price
            b1_info['entry_range_high'] = round(b1_trigger_price * 1.025, 2)
            b1_info['chase_ceiling'] = round(b1_trigger_price * 1.050, 2)
            b1_info['stop_loss'] = b1_stop
            b1_info['date'] = b1_date
            b1_info['desc'] = f"低點 {b1_stop:.2f} 元止跌V型推升（第一腳反彈中，尚未拉回打第二隻腳）"

            if b1_trigger_idx < len(df):
                sub_df = df.iloc[b1_trigger_idx:]
                b1_surge_peak = round(float(sub_df['High'].max()), 2)
                if b1_surge_peak > b1_info['chase_ceiling']:
                    b1_has_surged = True

    # =========================================================================
    # 2. 計算 B2 (過前高頸線)
    # =========================================================================
    neckline_peak = None
    has_broken_b2 = False
    b2_has_surged = False
    b2_surge_peak = 0.0

    if has_b1 and len(peaks) >= 1:
        leg2_idx = troughs[-1].get('index', 0)
        valid_peaks_before = [p for p in peaks if p.get('index', 0) <= leg2_idx]
        if valid_peaks_before:
            neckline_peak = valid_peaks_before[-1]
        else:
            neckline_peak = peaks[-1]
    elif is_v_rebound and len(peaks) >= 1:
        t_idx = troughs[-1].get('index', 0)
        valid_peaks_before = [p for p in peaks if p.get('index', 0) < t_idx]
        if valid_peaks_before:
            neckline_peak = valid_peaks_before[-1]
        else:
            neckline_peak = peaks[0]
    elif len(peaks) >= 1:
        neckline_peak = peaks[-1]

    if neckline_peak:
        b2_price = round(float(neckline_peak['price']), 2)
        b2_date = neckline_peak['date'].strftime('%m/%d') if hasattr(neckline_peak['date'], 'strftime') else str(neckline_peak['date'])[:10]
        b2_info['price'] = b2_price
        b2_info['entry_range_low'] = b2_price
        b2_info['entry_range_high'] = round(b2_price * 1.025, 2)
        b2_info['chase_ceiling'] = round(b2_price * 1.050, 2)
        b2_info['stop_loss'] = b2_price  # 突破後以頸線為防守
        b2_info['date'] = b2_date
        b2_info['desc'] = f"帶量突破前高頸線 {b2_price} 元，W底完成、頭頭高底底高正式確立"

        # 檢查自第二隻腳 (或 B1) 發動以來，股價是否曾突破前高頸線
        search_start = leg2_idx if has_b1 else (troughs[-1].get('index', 0) if troughs else 0)
        sub_since_neck = df.iloc[search_start:]
        b2_surge_peak = round(float(sub_since_neck['High'].max()), 2)
        if b2_surge_peak >= b2_price:
            has_broken_b2 = True
        if b2_surge_peak > b2_info['chase_ceiling']:
            b2_has_surged = True

    # =========================================================================
    # 3. 計算 B3 (大格局切線 / 大箱頂突破 / 波段高點)
    # =========================================================================
    b3_price = None
    b3_source = ""
    b3_has_surged = False
    b3_surge_peak = 0.0

    # A. 優先檢查 AI 幾何切線 (如 ABC 下降切線)
    patterns_found = pattern_geo.get("patterns_found", [])
    for p in patterns_found:
        if p.get("id") == "abc_correction" and "tangent_line" in p:
            cand_cut = p["tangent_line"].get("y1")
            if cand_cut and (b2_info['price'] is None or cand_cut > (b2_info['price'] or 0) * 1.01):
                b3_price = round(float(cand_cut), 2)
                b3_source = "下降壓力切線"
                break
        elif p.get("id") == "flat_base" and p.get("neckline"):
            cand_box = p["neckline"]
            if cand_box and (b2_info['price'] is None or cand_box > (b2_info['price'] or 0) * 1.01):
                b3_price = round(float(cand_box), 2)
                b3_source = "大箱型頂部"
                break

    # B. 若無特定型態，尋找高於頸線之歷史波段大頭部或近期最高點
    if not b3_price:
        higher_peaks = [p for p in peaks if p['price'] > (b2_info['price'] or 0)]
        if higher_peaks:
            b3_price = round(float(max(p['price'] for p in higher_peaks)), 2)
            b3_source = "前波波段高點"
        elif trend_info.get('resistance') and (b2_info['price'] is None or trend_info['resistance'] > (b2_info['price'] or 0) * 1.01):
            b3_price = round(float(trend_info['resistance']), 2)
            b3_source = "關鍵壓力線"

    # C. 若仍無更高峰，取近期高點或頸線上方 +6%~8% 作為衝刺加碼參考點
    if not b3_price and b2_info['price']:
        b3_price = round(float(b2_info['price'] * 1.08), 2)
        b3_source = "多頭波段續攻目標"

    if b3_price:
        b3_info['price'] = b3_price
        b3_info['entry_range_low'] = b3_price
        b3_info['entry_range_high'] = round(b3_price * 1.020, 2)
        b3_info['chase_ceiling'] = round(b3_price * 1.050, 2)
        b3_info['stop_loss'] = round(sma5, 2)
        b3_info['desc'] = f"帶量突破{b3_source} {b3_price} 元，主升段總攻加速衝刺"

        search_start = leg2_idx if has_b1 else 0
        b3_surge_peak = round(float(df.iloc[search_start:]['High'].max()), 2)
        if b3_surge_peak > b3_info['chase_ceiling']:
            b3_has_surged = True

    # =========================================================================
    # 4. 做多避開 7 位置：上方壓力臨頭檢測 (Overhead Resistance & Room Analysis)
    # =========================================================================
    res_candidates = []
    # A. 所有高於現價的已確認前高
    for p in peaks:
        if p['price'] > c * 1.002:
            res_candidates.append({'name': f"前高頸線 ({p['price']:.2f})", 'price': p['price'], 'type': 'PEAK'})

    # B. 下彎重大均線反壓 (月線 20MA / 季線 60MA)
    if 'SMA_20' in df and len(df) >= 5:
        sma20 = float(df['SMA_20'].iloc[-1])
        prev_sma20 = float(df['SMA_20'].iloc[-4])
        if sma20 > c * 1.002 and sma20 < prev_sma20:
            res_candidates.append({'name': f"下彎月線20MA ({sma20:.2f})", 'price': sma20, 'type': 'MA20'})

    if 'SMA_60' in df and len(df) >= 5:
        sma60 = float(df['SMA_60'].iloc[-1])
        prev_sma60 = float(df['SMA_60'].iloc[-4])
        if sma60 > c * 1.002 and sma60 < prev_sma60:
            res_candidates.append({'name': f"下彎季線60MA ({sma60:.2f})", 'price': sma60, 'type': 'MA60'})

    # C. 趨勢關鍵壓力線
    if trend_info.get('resistance') and float(trend_info['resistance']) > c * 1.002:
        res_candidates.append({'name': f"關鍵波段壓力 ({float(trend_info['resistance']):.2f})", 'price': float(trend_info['resistance']), 'type': 'TREND_RES'})

    closest_res = None
    room_pct = 999.0
    is_imminent = False
    is_ample = True
    overhead_status_badge = "✅ 空間充裕 (無前壓)"
    overhead_warning_desc = ""

    if res_candidates:
        res_candidates.sort(key=lambda x: x['price'])
        closest_res = res_candidates[0]
        room_pct = round(((closest_res['price'] - c) / c) * 100, 1)
        if 0 < room_pct <= 3.0:
            is_imminent = True
            is_ample = False
            overhead_status_badge = f"⚠️ 壓力臨頭 (僅距+{room_pct}%)"
            overhead_warning_desc = (
                f"上方僅距【{closest_res['name']}】約 {room_pct}%！"
                f"依朱家泓老師實戰鐵律『做多避開 7 位置：壓力前勿進』，此處進場極易遇壓被打回、盈虧比極差！"
                f"嚴禁在壓力前賭突破，寧等帶量長紅實質突破並站穩後再順勢進場！"
            )
        elif room_pct >= 8.0:
            is_imminent = False
            is_ample = True
            overhead_status_badge = f"✅ 空間充裕 (距前壓+{room_pct}%)"
            overhead_warning_desc = f"上方距最近壓力【{closest_res['name']}】有 +{room_pct}% 獲利空間，盈虧比良好。"
        else:
            is_imminent = False
            is_ample = False
            overhead_status_badge = f"🟡 正常空間 (距前壓+{room_pct}%)"
            overhead_warning_desc = f"上方距最近壓力【{closest_res['name']}】約 +{room_pct}%，按紀律操作。"

    overhead_analysis = {
        "closest_resistance": round(closest_res['price'], 2) if closest_res else None,
        "resistance_name": closest_res['name'] if closest_res else "",
        "room_pct": room_pct if closest_res else None,
        "is_imminent": is_imminent,
        "is_ample": is_ample,
        "status_badge": overhead_status_badge,
        "warning_desc": overhead_warning_desc
    }

    # =========================================================================
    # 5. 朱老師 10/07 贏家心法：預測失準 (時間停損) 換股診斷器
    # =========================================================================
    bars_since_trigger = 0
    trigger_ref_price = None
    target_tier_num = 1
    target_tier_name = "階梯一 (B1)"
    if has_b1 and b1_trigger_idx < len(df):
        bars_since_trigger = len(df) - 1 - b1_trigger_idx
        trigger_ref_price = b1_info['price']
        target_tier_num = 1
        target_tier_name = "階梯一 (B1)"
    elif has_broken_b2 and len(peaks) >= 1:
        bars_since_trigger = len(df) - 1 - int(peaks[-1].get('index', len(df)-1))
        trigger_ref_price = b2_info['price']
        target_tier_num = 2
        target_tier_name = "階梯二 (B2)"

    is_misprediction = False
    misprediction_chg = 0.0
    misprediction_warning = ""

    if 3 <= bars_since_trigger <= 6 and trigger_ref_price and trigger_ref_price > 0:
        misprediction_chg = round(((c - trigger_ref_price) / trigger_ref_price) * 100, 1)
        if -2.2 <= misprediction_chg <= 2.2:
            recent_vol = float(df['Volume'].iloc[-1])
            avg_vol = float(df['Volume'].rolling(20).mean().iloc[-1]) if len(df) >= 20 else recent_vol
            if recent_vol < avg_vol * 1.25:
                is_misprediction = True
                misprediction_warning = (
                    f"【{target_tier_name}】買點觸發已 T+{bars_since_trigger} 天，股價仍在成本區原地打轉 ({misprediction_chg:+.1f}%)、量能萎縮未放量發動！"
                    f"依朱家泓老師 10/07 線上 Q&A 贏家心法：『買進 3~5 天不衝即屬預測失準！沒壞但不漲也要出場！』"
                    f"資金的時間也是成本，切勿讓資金死守死魚盤！建議在平盤附近微損主動換股，落實『汰弱留強』，將資金轉向已放量起跑的強勢飆股！"
                )

    misprediction_diagnostic = {
        "is_misprediction": is_misprediction,
        "bars": bars_since_trigger,
        "pct_change": misprediction_chg,
        "badge": f"⏱️ 預測失準 (T+{bars_since_trigger} 沒壞不漲)" if is_misprediction else "",
        "warning": misprediction_warning,
        "target_tier": target_tier_num,
        "target_tier_name": target_tier_name
    }

    # =========================================================================
    # 6. 週線中長線雙重視角進場指引 (依朱老師 10/07 答覆)
    # =========================================================================
    weekly_guidance = {
        "title": "週線中長線進場 SOP (朱老師 10/07 規範)",
        "step1": "週五尾盤 (13:00~13:25) 確認週K收紅站上週 5MA / 突破週頸線，先建底倉 20%~30%",
        "step2": "下週一切回日線，等待日線拉回守穩、出現「日線回後買上漲」第一根紅K再加碼重倉",
        "tip": "長線一定要從獲利拉開 15%~20% 轉長線，切勿因套牢而自我安慰變長線！"
    }

    # =========================================================================
    # 7. 盤中即時狀態感知評估器 (Live State Evaluator for B1, B2, B3)
    # =========================================================================
    def evaluate_live_tier_state(t_item, cur_price, sma5_val, has_surged=False, surge_peak=0.0):
        p = t_item.get('price')
        if not p or p <= 0:
            t_item['status'] = 'WAITING'
            t_item['status_text'] = '⏳ 尚未成形'
            t_item['status_hint'] = '型態構築中，關鍵價位尚未成形'
            return

        low = t_item['entry_range_low']
        high = t_item['entry_range_high']
        ceil = t_item['chase_ceiling']
        t_tier = t_item['tier']

        t_item['distance_price'] = round(low - cur_price, 2)
        t_item['distance_pct'] = round(((low - cur_price) / cur_price) * 100, 1)

        # 情況 1: 該階梯在歷史上已經大漲噴出過 (曾衝破禁追天花板)
        if has_surged and surge_peak > ceil:
            over_pct = round(((surge_peak - low) / low) * 100, 1)
            t_item['status'] = 'MISSED'
            t_item['status_text'] = f"🚫 買點已過 (曾衝至{surge_peak:.2f}元)"
            t_item['status_hint'] = f"此階買點先前已發動並大漲 +{over_pct}% (最高達 {surge_peak:.2f} 元)！現價回落為波段拉回修正，切勿視為原始起漲黃金買點！"
            return

        # 情況 2: 現價尚未達到進場門檻 (低於 low)
        if cur_price < low:
            t_item['status'] = 'WAITING'
            diff_p = round(low - cur_price, 2)
            diff_pct = round(((low - cur_price) / cur_price) * 100, 1)
            t_item['status_text'] = f"🎯 距買點差 {diff_p:.2f}元 (-{diff_pct}%)"
            t_item['status_hint'] = f"蓄勢伏擊中，盤中帶量衝過 {low:.2f} 元即為啟動訊號"

        # 情況 3: 現價處於建議進場區間 [low, high]
        elif low <= cur_price <= high:
            if cur_price < sma5_val:
                t_item['status'] = 'WAITING'
                t_item['status_text'] = f"⏳ 跌破5MA拉回 (待站回{sma5_val:.2f}元)"
                t_item['status_hint'] = f"現價 {cur_price:.2f} 元雖落於進場區間，但收盤跌破 5MA ({sma5_val:.2f} 元) 整理中！老朱SOP嚴守『紅K站上5MA』才進場，切勿盲目接刀，靜待量縮止跌重返 5MA！"
            elif is_imminent:
                t_item['status'] = 'CAUTION'
                t_item['status_text'] = f"⚠️ 壓力臨頭 (僅距+{room_pct}%)"
                t_item['status_hint'] = f"現價雖在進場區，但頭頂正上方僅距【{closest_res['name']}】約 {room_pct}%！做多避開7位置（壓力前勿進），嚴禁賭突破，寧等帶量突破後再進！"
            else:
                t_item['status'] = 'ACTIVE'
                t_item['status_text'] = "🔥 黃金買點 (進行中)"
                t_item['status_hint'] = f"現價 {cur_price:.2f} 元正處黃金進場區 ({low:.2f} ~ {high:.2f} 元) 且站上 5MA，可按建議部位進場！"

        # 情況 4: 輕度追價區 (high < cur_price <= ceil)
        elif high < cur_price <= ceil:
            if cur_price < sma5_val:
                t_item['status'] = 'WAITING'
                t_item['status_text'] = f"⚠️ 破5MA整理 (待站回{sma5_val:.2f}元)"
                t_item['status_hint'] = f"現價稍離發動點但跌破 5MA ({sma5_val:.2f} 元)，短線轉弱，切勿追價，觀察守穩後能否重返 5MA！"
            elif is_imminent:
                t_item['status'] = 'CAUTION'
                t_item['status_text'] = f"⚠️ 壓力臨頭 (僅距+{room_pct}%)"
                t_item['status_hint'] = f"現價稍離發動點且接近上方【{closest_res['name']}】({closest_res['price']:.2f}元)，空間僅 {room_pct}%，壓力前切勿追價！"
            else:
                t_item['status'] = 'CAUTION'
                over_pct = round(((cur_price - low) / low) * 100, 1)
                t_item['status_text'] = f"⚠️ 輕度追價 (+{over_pct}%)"
                t_item['status_hint'] = f"現價稍離發動點 (+{over_pct}%)，接近禁追上限 ({ceil:.2f} 元)，建議部位減半！"

        # 情況 5: 超出禁追天花板 (cur_price > ceil)
        else:
            over_pct = round(((cur_price - low) / low) * 100, 1)
            t_item['status'] = 'MISSED'
            t_item['status_text'] = f"🚫 買點已過 (+{over_pct}%)"
            t_item['status_hint'] = f"現價已大漲 +{over_pct}%，超出禁追天花板 ({ceil:.2f} 元)！切勿追高，等待拉回測線或看下一階！"

    evaluate_live_tier_state(b1_info, c, sma5, has_surged=b1_has_surged, surge_peak=b1_surge_peak)
    evaluate_live_tier_state(b2_info, c, sma5, has_surged=b2_has_surged, surge_peak=b2_surge_peak)
    evaluate_live_tier_state(b3_info, c, sma5, has_surged=b3_has_surged, surge_peak=b3_surge_peak)

    # =========================================================================
    # 5. 綜合判定全檔所處階段 (Current Stage & Executive Verdict)
    # =========================================================================
    current_stage = "NONE"
    stage_code = 0
    stage_name = "未達進場門檻"
    stage_verdict = ""
    badge_html = ""
    badge_text = ""

    b1_p = b1_info['price'] or 0
    b2_p = b2_info['price'] or 999999
    b3_p = b3_info['price'] or 999999
    is_below_5ma = (c < sma5)

    # A. 仍在探底 (未打底、無第二隻腳、底底低)
    if not has_b1 and not is_v_rebound and c < b2_p:
        current_stage = "BOTTOMING"
        stage_code = 0
        stage_name = "🛑 探底觀望期"
        stage_verdict = "目前尚未打出第二隻腳（仍處探底或底底低），未出現底底高轉折訊號，老朱戰法嚴禁盲目猜底！"
        badge_text = "🛑 探底觀望 (禁猜底)"
        badge_html = "<span style='background:#450A0A; border:1px solid #DC2626; color:#FCA5A5; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🛑 探底觀望 (禁猜底)</span>"

    # B. V型急拉第一腳反彈中 (尚未打第二隻腳，且現價尚未突破 B2 頸線)
    elif is_v_rebound and not has_b1 and c < b2_p:
        current_stage = "FIRST_LEG_RALLY"
        stage_code = 1
        stage_name = "🌱 第一腳反彈推升（等打第二腳）"
        gain_pct = ((c - b1_info['stop_loss']) / (b1_info['stop_loss'] + 1e-9)) * 100
        stage_verdict = f"低點 {b1_info['stop_loss']:.2f} 元起漲為初升第一波推升（已漲 +{gain_pct:.1f}%），第一買點已遠離！目前尚未拉回打第二隻腳，短線正乖離過大，現價切勿追價；手中有持股者安心續抱守 5MA，空手者耐心等待量縮拉回打出第二隻腳（底底高）再佈局！"
        badge_text = "🌱 第一腳反彈 (勿追高)"
        badge_html = "<span style='background:#1E293B; border:1px solid #64748B; color:#CBD5E1; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🌱 第一腳反彈 (勿追高)</span>"

    # C. 特殊拉回型態：先前曾大漲衝高 (曾衝破 B1 禁追天花板或曾突破 B2 頸線)，目前自高檔拉回至頸線之下
    elif (b1_has_surged or has_broken_b2) and c < b2_p:
        current_stage = "PULLBACK_CORRECTION"
        stage_code = 0
        peak_val = max(b1_surge_peak, b2_surge_peak)

        broken_tags = []
        if is_below_5ma:
            broken_tags.append(f"5MA ({sma5:.2f}元)")
        if has_broken_b2:
            broken_tags.append(f"頸線 ({b2_p:.2f}元)")
        if pattern_geo:
            acc_def = pattern_geo.get("accelerated_defense_line")
            if acc_def and acc_def.get("is_broken"):
                broken_tags.append(f"加速防守線 ({acc_def.get('y_today', 0):.2f}元)")
            for p_item in pattern_geo.get("patterns_found", []):
                if p_item.get("id") == "abc_rebound_breakdown" and p_item.get("tangent_line"):
                    y_cut = p_item["tangent_line"].get("y1")
                    if y_cut:
                        broken_tags.append(f"上升切線 ({float(y_cut):.2f}元)")

        broken_desc = "、".join(broken_tags) if broken_tags else "關鍵防守線"

        if is_below_5ma:
            stage_name = "🛑 高檔拉回整理（破5MA防守中）"
            stage_verdict = (
                f"本檔先前自起漲點強勢推升，波段最高曾衝至 {peak_val:.2f} 元（已完成前波攻勢）！"
                f"目前自高檔拉回修正，今日收盤跌破 {broken_desc}，切勿盲目猜底接刀！"
                f"依老朱戰法紀律：持股者應依跌破 5MA 執行減碼停利防守；空手者耐心等待拉回守穩第二隻腳支撐 ({b1_info['stop_loss']:.2f} 元) 並出紅K重返 5MA，方為下一波布局良機！"
            )
            badge_text = "🛑 破5MA拉回 (禁接刀)"
            badge_html = "<span style='background:#450A0A; border:1px solid #DC2626; color:#FCA5A5; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🛑 破5MA拉回 (禁接刀)</span>"
        else:
            stage_name = "🔄 高檔拉回回測支撐（守穩5MA觀察）"
            stage_verdict = (
                f"本檔前波最高推升至 {peak_val:.2f} 元，目前自高檔拉回測試支撐，現價守穩 5MA ({sma5:.2f} 元) 之上！"
                f"空手者可觀察能否在此築出新的次級底底高，持股者以 5MA 移動防守續抱。"
            )
            badge_text = "🔄 拉回測支撐 (守5MA)"
            badge_html = "<span style='background:#1E293B; border:1px solid #3B82F6; color:#93C5FD; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🔄 拉回測支撐 (守5MA)</span>"

    # D. 標準多頭階梯流程
    else:
        # 1. 處在 B1 階梯 (股價在 B2 頸線之下，或剛守穩第二隻腳且尚未大漲過)
        if c < b2_p:
            current_stage = "TIER_1"
            stage_code = 1
            if b1_info['status'] == 'ACTIVE':
                stage_name = "🟢 處於第 1 買點【底部轉折試單】"
                stage_verdict = f"本檔已打出第二隻腳（支撐 {b1_info['stop_loss']} 元），現價正處於黃金進場區間 ({b1_info['entry_range_low']:.2f} ~ {b1_info['entry_range_high']:.2f} 元) 且站穩 5MA！建議建立小部位 20%~30% 試單卡位，嚴守跌破 {b1_info['stop_loss']} 元停損！"
                badge_text = "🟢 第1買點 (試單20%)"
                badge_html = "<span style='background:#064E3B; border:1px solid #10B981; color:#A7F3D0; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px; box-shadow:0 0 6px rgba(16,185,129,0.3);'>🟢 第1買點 (試單20%)</span>"
            elif is_below_5ma:
                stage_name = "⏳ 第 1 階築底整理（破5MA觀察中）"
                stage_verdict = f"本檔雖守在第二隻腳 ({b1_info['stop_loss']} 元) 之上，但今日收盤跌破 5MA ({sma5:.2f} 元) 整理中。老朱戰法嚴守『紅K站上5MA』才進場，切勿躁進猜底，待出紅K轉強再行試單！"
                badge_text = "⏳ 破5MA整理 (待轉強)"
                badge_html = "<span style='background:#1E293B; border:1px solid #64748B; color:#CBD5E1; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>⏳ 破5MA整理 (待轉強)</span>"
            else:
                if is_misprediction:
                    stage_name = f"⏱️ 第 1 階預測失準（T+{bars_since_trigger} 沒壞不漲·建議換股）"
                    stage_verdict = (
                        f"本檔自階梯一 (B1) 試單已 T+{bars_since_trigger} 天，股價在成本區原地打轉 ({misprediction_chg:+.1f}%) 且量能萎縮未發動！"
                        f"依朱家泓老師 10/07 贏家心法：『買進 3~5 天不衝即屬預測失準！沒壞但不漲也要出場！』"
                        f"既然第 1 階試單已預測失準，現階段絕不考慮第 2 階加碼；建議持股者於平盤附近微損主動換股，落實『汰弱留強』轉向強勢飆股！"
                    )
                    badge_text = f"⏱️ B1預測失準 (T+{bars_since_trigger}換股)"
                    badge_html = "<span style='background:#451A03; border:1px solid #D97706; color:#FDE68A; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>⏱️ B1預測失準 (換股)</span>"
                else:
                    stage_name = "🟢 第 1 買點已過（蓄勢挑戰第2買點）"
                    diff_b2 = round(b2_p - c, 2)
                    diff_b2_pct = round(((b2_p - c) / c) * 100, 1)
                    stage_verdict = f"第 1 買點試單區已過，目前股價向第 2 階頸線 ({b2_p:.2f} 元) 推升（僅差 {diff_b2:.2f} 元，-{diff_b2_pct}%）。持股者續抱守 5MA，空手者等待帶量放量突破 {b2_p:.2f} 元即刻啟動第 2 階重倉進場！"
                    badge_text = f"🎯 蓄勢突破B2 (差{diff_b2:.2f}元)"
                    badge_html = f"<span style='background:#1E293B; border:1px solid #F59E0B; color:#FDE68A; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🎯 蓄勢突破B2 (差{diff_b2:.2f}元)</span>"

        # 2. 處在 B2 階梯 (已突破 B2 頸線，但尚未突破 B3 大切線)
        elif c >= b2_p and (b3_p is None or c < b3_p):
            current_stage = "TIER_2"
            stage_code = 2
            diff_b3 = round(b3_p - c, 2)
            diff_b3_pct = round(((b3_p - c) / c) * 100, 1)

            if is_below_5ma:
                stage_name = "⚠️ 第 2 階高檔整理（跌破5MA防守中）"
                stage_verdict = f"本檔雖站於前高頸線 ({b2_p:.2f} 元) 之上，但今日收盤跌破 5MA ({sma5:.2f} 元)！多頭短線轉弱，嚴禁盲目追價；持股者緊盯 5MA 紀律執行停利防守，空手者待重新站回 5MA 再行觀察！"
                badge_text = "⚠️ 破5MA防守 (禁追價)"
                badge_html = "<span style='background:#451A03; border:1px solid #D97706; color:#FDE68A; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>⚠️ 破5MA防守 (禁追價)</span>"
            elif b2_info['status'] == 'ACTIVE':
                stage_name = "🔥 處於第 2 買點【標準多頭確立】"
                stage_verdict = f"收盤已成功突破前高頸線 ({b2_p:.2f} 元)，『頭頭高＋底底高』100% 成立！現價正處黃金進場區 ({b2_info['entry_range_low']:.2f} ~ {b2_info['entry_range_high']:.2f} 元) 且站穩 5MA，為老朱勝率最高之標準多頭進場點，建議建立標準部位 60%~70%，停損設守頸線 {b2_p:.2f} 元！"
                badge_text = "🔥 第2買點 (標準60%)"
                badge_html = "<span style='background:#78350F; border:1px solid #F59E0B; color:#FDE68A; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px; box-shadow:0 0 6px rgba(245,158,11,0.3);'>🔥 第2買點 (標準60%)</span>"
            elif b2_info['status'] == 'CAUTION':
                over_p = round(((c - b2_p) / b2_p) * 100, 1)
                stage_name = "⚠️ 第 2 買點【輕度追價區】"
                stage_verdict = f"股價突破頸線後已推升至 {c:.2f} 元 (+{over_p}%)，已高於黃金進場區，接近禁追天花板 ({b2_info['chase_ceiling']:.2f} 元)。此處若要進場建議部位減半 (30%)，防守緊貼 5MA！"
                badge_text = "⚠️ 第2買點 (輕度追價)"
                badge_html = "<span style='background:#451A03; border:1px solid #D97706; color:#FDE68A; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>⚠️ 第2買點 (輕度追價)</span>"
            else: # MISSED
                over_p = round(((c - b2_p) / b2_p) * 100, 1)
                stage_name = "🔥 第 2 買點已過（多頭確立·朝第3階推進）"
                stage_verdict = f"本檔已成功突破前高頸線 ({b2_p:.2f} 元) 多頭確立！現價 {c:.2f} 元已大漲超標 (+{over_p}%) 超過禁追天花板 ({b2_info['chase_ceiling']:.2f}元)，切勿在此追高！手中持股安心續抱守 5MA ({sma5:.2f}元)；距第 3 階加碼點 ({b3_p:.2f}元) 僅差 {diff_b3:.2f} 元 (-{diff_b3_pct}%)，待帶量突破時方可加碼！"
                badge_text = f"🔥 多頭推進中 (距B3差{diff_b3:.2f}元)"
                badge_html = f"<span style='background:#311005; border:1px solid #F97316; color:#FED7AA; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🔥 多頭推進 (距B3差{diff_b3:.2f}元)</span>"

        # 3. 處在 B3 階梯 (突破大切線 / 大箱頂)
        else:
            current_stage = "TIER_3"
            stage_code = 3
            if is_below_5ma:
                stage_name = "⚠️ 主升段高檔震盪（跌破5MA停利防守）"
                stage_verdict = f"本檔雖越過大格局壓力切線/箱頂 ({b3_p:.2f} 元)，但今日收盤跌破 5MA ({sma5:.2f} 元)！主升段短線拉回，嚴禁追價；持股者緊盯 5MA 紀律執行分批獲利了結！"
                badge_text = "⚠️ 破5MA防守 (緊盯停利)"
                badge_html = "<span style='background:#450A0A; border:1px solid #EF4444; color:#FCA5A5; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>⚠️ 破5MA防守 (緊盯停利)</span>"
            elif b3_info['status'] == 'ACTIVE':
                stage_name = "🚀 處於第 3 買點【波段加碼／強勢追價】"
                stage_verdict = f"強勢放量突破大格局壓力切線/箱頂 ({b3_p:.2f} 元)，主升段衝刺啟動！現價正處加碼區 ({b3_info['entry_range_low']:.2f} ~ {b3_info['entry_range_high']:.2f} 元) 且站穩 5MA，已持股者可順勢加碼擴大戰果；空手者屬強勢追價，部位不宜過大，一律嚴守 5MA ({sma5:.2f}元) 移動停利！"
                badge_text = "🚀 第3買點 (加碼/追價)"
                badge_html = "<span style='background:#4C1D95; border:1px solid #8B5CF6; color:#DDD6FE; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px; box-shadow:0 0 6px rgba(139,92,246,0.3);'>🚀 第3買點 (加碼/追價)</span>"
            elif b3_info['status'] == 'CAUTION':
                over_p = round(((c - b3_p) / b3_p) * 100, 1)
                stage_name = "🚀 第 3 買點【極致衝刺追價】"
                stage_verdict = f"已越過大箱頂/切線推升至 {c:.2f} 元 (+{over_p}%)，主升段加速奔馳中！追價空間有限，接近禁追上限 ({b3_info['chase_ceiling']:.2f}元)，一律以 5MA ({sma5:.2f}元) 為絕對防守線移動停利！"
                badge_text = "🚀 第3買點 (衝刺追價)"
                badge_html = "<span style='background:#2E1065; border:1px solid #A855F7; color:#E9D5FF; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🚀 第3買點 (衝刺追價)</span>"
            else: # MISSED
                over_p = round(((c - b3_p) / b3_p) * 100, 1)
                stage_name = "🚀 主升段高檔加速（嚴禁追高·守5MA停利）"
                stage_verdict = f"波段已自突破點大漲 +{over_p}%，已遠遠超出第 3 階禁追上限 ({b3_info['chase_ceiling']:.2f}元)！嚴禁任何新買單追高，手中持股緊盯 5MA ({sma5:.2f}元) 收盤破線即刻分批獲利了結！"
                badge_text = "🛑 主升段大漲 (嚴禁追高)"
                badge_html = "<span style='background:#450A0A; border:1px solid #EF4444; color:#FCA5A5; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🛑 主升段大漲 (嚴禁追高)</span>"

        # 連漲 3 根以上風險提示
        if up_days >= 3 and current_stage in ["TIER_2", "TIER_3"]:
            stage_verdict += f"（⚠️ 提醒：已連續推升第 {up_days} 根，短線正乖離稍大，追價者手腳需敏捷，或耐心等量縮拉回守穩 5MA 時切入！）"

    # 壓力臨頭警示全域追加於操盤定奪 (無論任何階段，只要上方空間不足 3% 一律警示做多避開 7 位置)
    if is_imminent and closest_res and "做多避開 7 位置" not in stage_verdict and "壓力臨頭" not in stage_verdict:
        ov_target_str = "階梯二前高" if (b2_p < 999999 and abs(closest_res['price'] - b2_p) <= max(b2_p * 0.05, 3.0)) else "上方"
        if is_misprediction:
            stage_verdict += f"（⚠️ 壓力臨頭：頭頂正上方僅距【{closest_res['name']}】約 {room_pct}%，空間不足 3% 風報比極差，正是壓制第 1 階攻勢熄火的主因，嚴禁加碼賭突破！）"
        else:
            stage_verdict += f"（⚠️ 做多避開 7 位置：{ov_target_str}【{closest_res['name']}】距今僅 {room_pct}%，壓力臨頭勿賭突破，靜待放量站上再順勢加碼！）"

    # 預測失準換股 SOP 全域追加於操盤定奪
    if is_misprediction and "預測失準" not in stage_verdict:
        stage_verdict += f"（⏱️ 朱老師 10/07 贏家心法：{target_tier_name}發動已 T+{bars_since_trigger} 天原地打轉量縮屬預測失準，沒壞但不漲亦建議平盤附近微損換股，汰弱留強！）"

    return {
        "current_stage": current_stage,
        "current_price": round(c, 2),
        "stage_code": stage_code,
        "stage_name": stage_name,
        "stage_verdict": stage_verdict,
        "badge_html": badge_html,
        "badge_text": badge_text,
        "b1": b1_info,
        "b2": b2_info,
        "b3": b3_info,
        "overhead_analysis": overhead_analysis,
        "misprediction_diagnostic": misprediction_diagnostic,
        "weekly_guidance": weekly_guidance
    }


def render_three_tier_entry_dashboard(tier_info: dict):
    """
    在 Streamlit 中渲染升級版老朱三層進場階梯戰術導航看板 (Three-Tier Stepper Dashboard)
    完整呈現：發動價、建議進場區間、禁追天花板、防守停損、以及盤中即時狀態響應
    """
    if not tier_info or tier_info.get('current_stage') == 'NONE':
        return

    import streamlit as st

    c_stage = tier_info.get('current_stage', '')
    curr_c = tier_info.get('current_price', 0.0)
    stage_name = tier_info.get('stage_name', '')
    stage_verdict = tier_info.get('stage_verdict', '')
    b1 = tier_info.get('b1') or {}
    b2 = tier_info.get('b2') or {}
    b3 = tier_info.get('b3') or {}

    # 頂部橫幅色彩依當前階梯動態配置
    if c_stage == 'TIER_1':
        theme_bg = "rgba(16, 185, 129, 0.12)"
        theme_bd = "#10B981"
        theme_color = "#34D399"
    elif c_stage == 'TIER_2':
        theme_bg = "rgba(245, 158, 11, 0.15)"
        theme_bd = "#F59E0B"
        theme_color = "#FBBF24"
    elif c_stage == 'TIER_3':
        theme_bg = "rgba(139, 92, 246, 0.15)"
        theme_bd = "#8B5CF6"
        theme_color = "#A78BFA"
    elif c_stage == 'FIRST_LEG_RALLY':
        theme_bg = "rgba(59, 130, 246, 0.12)"
        theme_bd = "#3B82F6"
        theme_color = "#60A5FA"
    elif c_stage == 'PULLBACK_CORRECTION':
        theme_bg = "rgba(220, 38, 38, 0.12)"
        theme_bd = "#DC2626"
        theme_color = "#F87171"
    elif c_stage == 'PULLBACK_SUPPORT':
        theme_bg = "rgba(59, 130, 246, 0.12)"
        theme_bd = "#3B82F6"
        theme_color = "#93C5FD"
    else:
        theme_bg = "rgba(220, 38, 38, 0.12)"
        theme_bd = "#DC2626"
        theme_color = "#F87171"

    def format_card_live_status(b_item):
        st_val = b_item.get('status', 'WAITING')
        st_txt = b_item.get('status_text', '')
        if st_val == 'ACTIVE':
            return (
                f"<span style='background:#059669; color:#FFF; font-weight:bold; padding:2px 7px; border-radius:4px; font-size:0.75rem; box-shadow:0 0 8px rgba(16,185,129,0.4);'>{st_txt or '🔥 黃金買點'}</span>",
                "border: 2px solid #10B981; background: rgba(16, 185, 129, 0.09); box-shadow: 0 0 14px rgba(16, 185, 129, 0.22);"
            )
        elif st_val == 'CAUTION':
            return (
                f"<span style='background:#D97706; color:#FFF; font-weight:bold; padding:2px 7px; border-radius:4px; font-size:0.73rem;'>{st_txt or '⚠️ 輕度追價'}</span>",
                "border: 1px solid #D97706; background: rgba(217, 119, 6, 0.10);"
            )
        elif st_val == 'MISSED':
            return (
                f"<span style='background:#2A1B0E; border:1px solid #B45309; color:#FCD34D; font-weight:bold; padding:2px 6px; border-radius:4px; font-size:0.72rem;'>{st_txt or '🚫 買點已過'}</span>",
                "border: 1px solid #78350F; background: #18120B; opacity: 0.92;"
            )
        else: # WAITING
            if "破5MA" in st_txt or "⚠️" in st_txt:
                return (
                    f"<span style='background:#3C1F24; border:1px solid #EF4444; color:#FCA5A5; font-weight:bold; padding:2px 6px; border-radius:4px; font-size:0.72rem;'>{st_txt}</span>",
                    "border: 1px solid #7F1D1D; background: rgba(127, 29, 29, 0.12);"
                )
            return (
                f"<span style='background:#1E293B; border:1px solid #475569; color:#94A3B8; font-weight:bold; padding:2px 6px; border-radius:4px; font-size:0.72rem;'>{st_txt or '⏳ 預備伏擊'}</span>",
                "border: 1px solid #1E293B; background: #0B0F19;"
            )

    b1_badge, b1_style = format_card_live_status(b1)
    b2_badge, b2_style = format_card_live_status(b2)
    b3_badge, b3_style = format_card_live_status(b3)

    overhead = tier_info.get('overhead_analysis') or {}
    mispred = tier_info.get('misprediction_diagnostic') or {}
    weekly_g = tier_info.get('weekly_guidance') or {}

    # 判斷臨壓屬於哪一個階梯門檻
    overhead_target_tier = 0
    if overhead.get('is_imminent') and overhead.get('closest_resistance'):
        res_p = overhead['closest_resistance']
        b1_p = b1.get('price') or 0
        b2_p = b2.get('price') or 999999
        b3_p = b3.get('price') or 999999
        if b3_p < 999999 and abs(res_p - b3_p) <= max(b3_p * 0.04, 2.0):
            overhead_target_tier = 3
        elif b2_p < 999999 and (abs(res_p - b2_p) <= max(b2_p * 0.05, 3.0) or (b1_p > 0 and res_p >= b1_p * 0.99)):
            overhead_target_tier = 2
        elif b1_p > 0 and res_p <= b1_p * 1.02:
            overhead_target_tier = 1
        else:
            overhead_target_tier = 2

    # 價格格式化
    def render_tier_card_content(b_item, default_name, is_b3=False, extra_alert_html=""):
        p = b_item.get('price')
        low = b_item.get('entry_range_low')
        high = b_item.get('entry_range_high')
        ceil = b_item.get('chase_ceiling')
        stop = b_item.get('stop_loss')
        hint = b_item.get('status_hint', '')

        if not p:
            return (
                f"<div style='font-size:1.1rem; color:#94A3B8; font-weight:bold; margin-bottom:4px;'>未成形</div>"
                f"<div style='font-size:0.8rem; color:#64748B;'>型態尚未構築完成</div>"
                f"{extra_alert_html}"
            )

        range_str = f"{low:.2f} ～ {high:.2f} 元" if (low and high) else f"{p:.2f} 元"
        ceil_str = f"超過 {ceil:.2f} 元 勿追" if ceil else "勿追"
        stop_label = "🛡️ 移動停利" if is_b3 else "🛡️ 防守停損"
        stop_val = f"破 5MA ({stop:.2f}) 停利" if (is_b3 and stop) else (f"破 {stop:.2f} 停損" if stop else "守5MA")

        return f"""
        <div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom: 4px;">
            <div>
                <span style="font-size:0.85rem; color:#94A3B8;">突破發動價：</span>
                <span style="font-size:1.25rem; font-weight:bold; color:#FFFFFF;">{p:.2f}</span>
                <span style="font-size:0.85rem; color:#94A3B8;"> 元</span>
            </div>
            <div style="font-size:0.78rem; color:#94A3B8;">
                現價: <b style="color:#FFF;">{curr_c:.2f}</b>
            </div>
        </div>
        <div style="background:rgba(255,255,255,0.03); border-radius:5px; padding:5px 8px; margin-bottom:5px;">
            <div style="font-size:0.82rem; color:#CBD5E1; margin-bottom:2px;">
                🎯 建議進場：<b style="color:#34D399;">{range_str}</b>
                <span style="font-size:0.72rem; color:#94A3B8;">(+0%~+2.5%)</span>
            </div>
            <div style="font-size:0.82rem; color:#CBD5E1;">
                🚫 禁追上限：<b style="color:#EF4444;">{ceil_str}</b>
                <span style="font-size:0.72rem; color:#94A3B8;">(+5.0%)</span>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.79rem; color:#94A3B8; margin-bottom:2px;">
            <div>💰 建議部位：<b style="color:#FBBF24;">{b_item.get('position', '依SOP')}</b></div>
            <div>{stop_label}：<b style="color:{'#38BDF8' if is_b3 else '#EF4444'};">{stop_val}</b></div>
        </div>
        <div style="font-size:0.74rem; color:#60A5FA; border-top:1px dashed #334155; padding-top:4px; margin-top:4px; line-height:1.4;">
            📌 <b>即時導航</b>：{hint}
        </div>
        {extra_alert_html}
        """

    # 卡片專屬警示標示 (直接標在對應卡片中，文字簡短清楚)
    c1_alerts = []
    if mispred.get('is_misprediction') and mispred.get('target_tier', 1) == 1:
        c1_alerts.append(
            f"<div style='background:rgba(245, 158, 11, 0.16); border-left:3px solid #F59E0B; border-radius:4px; padding:4px 7px; margin-top:5px; font-size:0.75rem; color:#FDE68A; line-height:1.45;'>"
            f"⏱️ <b>10/07心法 · 預測失準 (T+{mispred['bars']})</b>：發動後原地打轉量縮，建議平盤附近微損換股，汰弱留強！"
            f"</div>"
        )
    if overhead_target_tier == 1:
        c1_alerts.append(
            f"<div style='background:rgba(220, 38, 38, 0.16); border-left:3px solid #EF4444; border-radius:4px; padding:4px 7px; margin-top:5px; font-size:0.75rem; color:#FCA5A5; line-height:1.45;'>"
            f"⚠️ <b>臨壓防禦 (僅距+{overhead['room_pct']}%)</b>：距上方【{overhead['resistance_name']}】極近，壓力前勿急追！"
            f"</div>"
        )

    c2_alerts = []
    if mispred.get('is_misprediction') and mispred.get('target_tier') == 1:
        c2_alerts.append(
            f"<div style='background:rgba(75, 85, 99, 0.22); border-left:3px solid #94A3B8; border-radius:4px; padding:4px 7px; margin-top:5px; font-size:0.75rem; color:#CBD5E1; line-height:1.45;'>"
            f"🔒 <b>暫不考慮第 2 階</b>：階梯一試單已預測失準，且頭頂有壓 ({overhead.get('resistance_name')})，未見放量轉強前嚴禁預設加碼！"
            f"</div>"
        )
    elif overhead_target_tier == 2:
        c2_alerts.append(
            f"<div style='background:rgba(220, 38, 38, 0.16); border-left:3px solid #EF4444; border-radius:4px; padding:4px 7px; margin-top:5px; font-size:0.75rem; color:#FCA5A5; line-height:1.45;'>"
            f"⚠️ <b>臨壓防禦 (僅距+{overhead['room_pct']}%)</b>：距前高【{overhead['resistance_name']}】極近，壓力前勿賭突破，等放量站上再重倉！"
            f"</div>"
        )
    if mispred.get('is_misprediction') and mispred.get('target_tier') == 2:
        c2_alerts.append(
            f"<div style='background:rgba(245, 158, 11, 0.16); border-left:3px solid #F59E0B; border-radius:4px; padding:4px 7px; margin-top:5px; font-size:0.75rem; color:#FDE68A; line-height:1.45;'>"
            f"⏱️ <b>10/07心法 · 預測失準 (T+{mispred['bars']})</b>：突破後原地打轉量縮，建議平盤附近微損換股！"
            f"</div>"
        )

    c3_alerts = []
    if overhead_target_tier == 3:
        c3_alerts.append(
            f"<div style='background:rgba(220, 38, 38, 0.16); border-left:3px solid #EF4444; border-radius:4px; padding:4px 7px; margin-top:5px; font-size:0.75rem; color:#FCA5A5; line-height:1.45;'>"
            f"⚠️ <b>臨壓防禦 (僅距+{overhead['room_pct']}%)</b>：距波段重壓【{overhead['resistance_name']}】極近，守5MA停利！"
            f"</div>"
        )

    c1_html = render_tier_card_content(b1, "B1", extra_alert_html="".join(c1_alerts))
    c2_html = render_tier_card_content(b2, "B2", extra_alert_html="".join(c2_alerts))
    c3_html = render_tier_card_content(b3, "B3", is_b3=True, extra_alert_html="".join(c3_alerts))

    res_badge_color = "#FCA5A5" if overhead.get('is_imminent') else ("#86EFAC" if overhead.get('is_ample') else "#FDE68A")

    dashboard_html = f"""
    <div style="background: linear-gradient(135deg, #131722 0%, #1A2030 100%); border: 1px solid {theme_bd}; border-radius: 10px; padding: 14px 16px; margin: 10px 0 14px 0; box-shadow: 0 4px 14px rgba(0,0,0,0.3);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 12px;">
            <div>
                <span style="font-size: 1.1rem; font-weight: bold; color: #FFFFFF;">🎯 老朱三層進場階梯戰術導航</span>
                <span style="font-size: 0.85rem; color: #94A3B8; margin-left: 8px;">(進場區間 · 禁追天花板 · 盤中動態感知)</span>
            </div>
            <div>
                <span style="font-size: 0.95rem; font-weight: bold; color: {theme_color}; background: {theme_bg}; border: 1px solid {theme_bd}; padding: 3px 10px; border-radius: 6px;">
                    {stage_name}
                </span>
            </div>
        </div>

        <div style="background: {theme_bg}; border-left: 4px solid {theme_bd}; border-radius: 6px; padding: 9px 12px; margin-bottom: 12px; font-size: 0.86rem; line-height: 1.55; color: #F1F5F9;">
            <b>💡 實戰操盤定奪</b>：{stage_verdict}
        </div>

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px;">
            <!-- 階梯 1 卡片 -->
            <div style="{b1_style} border-radius: 8px; padding: 10px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                    <span style="font-size:0.88rem; font-weight:bold; color:#A7F3D0;">🟢 階梯一 · 底部轉折試單 (B1)</span>
                    {b1_badge}
                </div>
                {c1_html}
            </div>

            <!-- 階梯 2 卡片 -->
            <div style="{b2_style} border-radius: 8px; padding: 10px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                    <span style="font-size:0.88rem; font-weight:bold; color:#FDE68A;">🔥 階梯二 · 標準多頭確立 (B2)</span>
                    {b2_badge}
                </div>
                {c2_html}
            </div>

            <!-- 階梯 3 卡片 -->
            <div style="{b3_style} border-radius: 8px; padding: 10px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                    <span style="font-size:0.88rem; font-weight:bold; color:#DDD6FE;">🚀 階梯三 · 波段加碼追價 (B3)</span>
                    {b3_badge}
                </div>
                {c3_html}
            </div>
        </div>

        <!-- 底部實戰心法聯動條 -->
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); border-radius: 6px; padding: 7px 12px; margin-top: 12px; font-size: 0.77rem; color: #94A3B8;">
            <div>
                🧭 <b>週日聯動進場 SOP (朱老師 10/07 規範)</b>：週五尾盤 (13:00~13:25) 週K站上週5MA建底倉，下週一切回日線等「回後買上漲」再加碼！
            </div>
            <div style="font-weight: bold; color: {res_badge_color};">
                🛡️ 壓力空間：{overhead.get('status_badge', '空間適中')}
            </div>
        </div>
    </div>
    """

    clean_html = "".join([line.strip() for line in dashboard_html.splitlines() if line.strip() and not line.strip().startswith("<!--")])
    if hasattr(st, 'html'):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)
