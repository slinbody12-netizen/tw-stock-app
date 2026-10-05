# -*- coding: utf-8 -*-
"""
老朱三層進場階梯戰法量化核心 (Three-Tier Entry Hierarchy Engine)
依據朱家泓老師實戰體系：
- 第 1 買點 (B1)：底部轉折試單點 (打第二隻腳底底高 / 紅K過5MA / 建議倉位 20%~30%)
- 第 2 買點 (B2)：標準多頭確立買點 (帶量過前高頸線 / 頭頭高+底底高全成立 / 建議倉位 60%~70%)
- 第 3 買點 (B3)：波段加碼追價點 (帶量突破中長期大下降切線或大箱頂 / 順勢加碼或強勢追價)
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
    計算個股在老朱三層進場階梯戰法中的所屬階梯、關鍵價位、建議倉位與防守停損
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
    o = float(latest['Open'])
    h = float(latest['High'])
    l = float(latest['Low'])
    sma5 = float(latest.get('SMA_5', c))
    sma20 = float(latest.get('SMA_20', c))
    vol_ratio = float(signals_dict.get('vol_ratio', 1.0))
    up_days = int(signals_dict.get('up_days', 0))

    # 若未傳入 pattern_geo，嘗試自行呼叫
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
        "status": "WAITING",  # WAITING / ACTIVE / PASSED / INVALID
        "price": None,
        "stop_loss": None,
        "position": "20% ～ 30% (小部位試單)",
        "condition": "打第二隻腳不破前低，紅K站上5MA",
        "date": "",
        "desc": ""
    }

    b2_info = {
        "tier": 2,
        "name": "第 2 買點【標準多頭確立】",
        "status": "WAITING",  # WAITING / ACTIVE / PASSED
        "price": None,
        "stop_loss": None,
        "position": "60% ～ 70% (標準重倉進場)",
        "condition": "帶量突破前高頸線，頭頭高+底底高全成立",
        "date": "",
        "desc": ""
    }

    b3_info = {
        "tier": 3,
        "name": "第 3 買點【波段加碼追價】",
        "status": "WAITING",  # WAITING / ACTIVE / PASSED
        "price": None,
        "stop_loss": None,
        "position": "順勢加碼 / 強勢短線追價",
        "condition": "帶量突破大格局下降切線或大箱頂",
        "date": "",
        "desc": ""
    }

    # =========================================================================
    # 1. 計算 B1 (第二隻腳底底高)
    # =========================================================================
    has_b1 = False
    is_v_rebound = False

    if len(troughs) >= 2:
        leg1 = troughs[-2]
        leg2 = troughs[-1]
        # 兩腳比較：第二隻腳高於第一隻腳 (底底高，容差 0.8%)
        if leg2['price'] >= leg1['price'] * 0.992:
            has_b1 = True
            b1_stop = round(float(leg2['price']), 2)
            b1_date = leg2['date'].strftime('%m/%d') if hasattr(leg2['date'], 'strftime') else str(leg2['date'])[:10]
            
            # 尋找 leg2 之後收盤站上 5MA 的紅 K 作為試單買點
            leg2_idx = leg2.get('index', 0)
            b1_trigger_price = b1_stop
            for k in range(leg2_idx, len(df)):
                r = df.iloc[k]
                if r['Close'] >= r.get('SMA_5', r['Close']) and r['Close'] >= r['Open']:
                    b1_trigger_price = round(float(r['Close']), 2)
                    break

            b1_info['price'] = b1_trigger_price
            b1_info['stop_loss'] = b1_stop
            b1_info['date'] = b1_date
            b1_info['desc'] = f"守穩第二隻腳 {b1_stop} 元 (高於前低 {leg1['price']:.2f})，紅K站上5MA試單"

    # 特殊情況：若最近一底為最低底，但從該底一路紅K大彈超過 10% 或已過前高 (如 3013 V型反轉第一波)
    if not has_b1 and len(troughs) >= 1:
        last_trough = troughs[-1]
        t_idx = last_trough.get('index', 0)
        gain_from_trough = (c - last_trough['price']) / (last_trough['price'] + 1e-9)
        if gain_from_trough >= 0.08:
            is_v_rebound = True
            b1_info['price'] = round(float(last_trough['price'] * 1.02), 2)
            b1_info['stop_loss'] = round(float(last_trough['price']), 2)
            b1_info['date'] = last_trough['date'].strftime('%m/%d') if hasattr(last_trough['date'], 'strftime') else str(last_trough['date'])[:10]
            b1_info['desc'] = f"低點 {last_trough['price']:.2f} 元止跌V型推升（第一腳反彈中，尚未拉回打第二隻腳）"

    # =========================================================================
    # 2. 計算 B2 (過前高頸線)
    # =========================================================================
    has_b2 = False
    neckline_peak = None

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

    if neckline_peak:
        b2_price = round(float(neckline_peak['price']), 2)
        b2_date = neckline_peak['date'].strftime('%m/%d') if hasattr(neckline_peak['date'], 'strftime') else str(neckline_peak['date'])[:10]
        b2_info['price'] = b2_price
        b2_info['stop_loss'] = b2_price  # 突破後以頸線為防守
        b2_info['date'] = b2_date
        b2_info['desc'] = f"帶量突破前高頸線 {b2_price} 元，W底完成、頭頭高底底高正式確立"
        has_b2 = True

    # =========================================================================
    # 3. 計算 B3 (大格局切線 / 大箱頂突破)
    # =========================================================================
    b3_price = None
    b3_source = ""

    # A. 優先檢查 AI 幾何切線 (如 ABC 下降切線，如 8086 的 121.95)
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

    # B. 若無特定型態，尋找高於頸線之歷史波段大頭部
    if not b3_price:
        higher_peaks = [p for p in peaks if p['price'] > (b2_info['price'] or 0)]
        if higher_peaks:
            b3_price = round(float(max(p['price'] for p in higher_peaks)), 2)
            b3_source = "前波波段高點"
        elif trend_info.get('resistance') and (b2_info['price'] is None or trend_info['resistance'] > (b2_info['price'] or 0) * 1.01):
            b3_price = round(float(trend_info['resistance']), 2)
            b3_source = "關鍵壓力線"

    if b3_price:
        b3_info['price'] = b3_price
        b3_info['stop_loss'] = round(sma5, 2)
        b3_info['desc'] = f"帶量突破{b3_source} {b3_price} 元，主升段總攻加速衝刺"

    # =========================================================================
    # 4. 綜合判定當前所處階梯 (Current Stage)
    # =========================================================================
    current_stage = "NONE"
    stage_code = 0
    stage_name = "未達進場門檻"
    stage_verdict = ""
    badge_html = ""
    badge_text = ""

    b1_p = b1_info['price'] or 0
    b1_stop = b1_info['stop_loss'] or 0
    b2_p = b2_info['price'] or 999999
    b3_p = b3_info['price'] or 999999

    # 情況 A：仍在探底 (未打底、無第二隻腳、底底低)
    if not has_b1 and not is_v_rebound:
        current_stage = "BOTTOMING"
        stage_code = 0
        stage_name = "🛑 探底觀望期"
        stage_verdict = "目前尚未打出第二隻腳（仍處探底或底底低），未出現底底高轉折訊號，老朱戰法嚴禁盲目猜底！"
        badge_text = "🛑 探底觀望 (禁猜底)"
        badge_html = "<span style='background:#450A0A; border:1px solid #DC2626; color:#FCA5A5; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🛑 探底觀望 (禁猜底)</span>"
        b1_info['status'] = "WAITING"
        b2_info['status'] = "WAITING"
        b3_info['status'] = "WAITING"

    # 情況 B：V型急拉第一腳反彈中 (尚未打第二隻腳，如 3013)
    elif is_v_rebound and not has_b1:
        current_stage = "FIRST_LEG_RALLY"
        stage_code = 1
        stage_name = "🌱 第一腳反彈推升（等打第二腳）"
        gain_pct = ((c - b1_stop) / (b1_stop + 1e-9)) * 100
        stage_verdict = f"低點 {b1_stop:.2f} 元起漲為初升第一波推升（已漲 +{gain_pct:.1f}%），第一買點 ({b1_p:.2f}元) 已遠離！目前尚未拉回打第二隻腳，短線正乖離過大，現價切勿追價；手中有持股者安心續抱守 5MA，空手者耐心等待量縮拉回打出第二隻腳（底底高）再佈局！"
        badge_text = "🌱 第一腳反彈 (勿追高)"
        badge_html = "<span style='background:#1E293B; border:1px solid #64748B; color:#CBD5E1; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px;'>🌱 第一腳反彈 (勿追高)</span>"
        b1_info['status'] = "MISSED"
        b1_info['position'] = f"買點已過（已大漲 +{gain_pct:.1f}%，切勿追高）"
        b1_info['desc'] = f"當時 {b1_stop:.2f} 元止跌V型推升（第一腳反彈中，尚未拉回打第二隻腳）"
        b2_info['status'] = "WAITING"
        b2_info['desc'] = f"盤中越過前高 {b2_p:.2f} 元，但尚未拉回打第二隻腳，多頭未完備，等回測打腳"
        b3_info['status'] = "WAITING"

    # 情況 C：標準多頭階梯流程 (已有底底高 B1 基礎)
    else:
        # 1. 處在 B1 階梯 (股價在 B2 頸線之下，或剛守穩第二隻腳)
        if c < b2_p:
            b1_info['status'] = "ACTIVE"
            b2_info['status'] = "WAITING"
            b3_info['status'] = "WAITING"
            current_stage = "TIER_1"
            stage_code = 1
            stage_name = "🟢 處於第 1 買點【底部轉折試單】"
            stage_verdict = f"本檔已打出第二隻腳（支撐 {b1_stop} 元），目前在突破前高頸線 ({b2_p} 元) 前蓄勢。建議建立小部位 20%~30% 試單卡位，嚴守跌破 {b1_stop} 元停損！"
            badge_text = "🟢 第1買點 (試單20%)"
            badge_html = "<span style='background:#064E3B; border:1px solid #10B981; color:#A7F3D0; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px; box-shadow:0 0 6px rgba(16,185,129,0.3);'>🟢 第1買點 (試單20%)</span>"

        # 2. 處在 B2 階梯 (突破頸線，但尚未突破 B3 大切線)
        elif c >= b2_p and (b3_p is None or c < b3_p):
            b1_info['status'] = "PASSED"
            b2_info['status'] = "ACTIVE"
            b3_info['status'] = "WAITING"
            current_stage = "TIER_2"
            stage_code = 2
            stage_name = "🔥 處於第 2 買點【標準多頭確立】"
            stage_verdict = f"收盤已成功突破前高頸線 ({b2_p} 元)，『頭頭高＋底底高』100% 成立！此為老朱勝率最高之標準多頭進場點，建議建立標準部位 60%~70%，停損設守頸線 {b2_p} 元！"
            badge_text = "🔥 第2買點 (標準60%)"
            badge_html = "<span style='background:#78350F; border:1px solid #F59E0B; color:#FDE68A; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px; box-shadow:0 0 6px rgba(245,158,11,0.3);'>🔥 第2買點 (標準60%)</span>"

        # 3. 處在 B3 階梯 (突破大切線 / 大箱頂)
        else:
            b1_info['status'] = "PASSED"
            b2_info['status'] = "PASSED"
            b3_info['status'] = "ACTIVE"
            current_stage = "TIER_3"
            stage_code = 3
            stage_name = "🚀 處於第 3 買點【波段加碼／強勢追價】"
            stage_verdict = f"強勢放量突破大格局壓力切線/箱頂 ({b3_p} 元)，主升段衝刺啟動！已持股者可順勢加碼擴大戰果；空手者屬強勢追價，部位不宜過大，一律嚴守 5MA ({sma5:.2f}元) 移動停利！"
            badge_text = "🚀 第3買點 (加碼/追價)"
            badge_html = "<span style='background:#4C1D95; border:1px solid #8B5CF6; color:#DDD6FE; font-size:0.75rem; font-weight:bold; padding:2px 7px; border-radius:4px; box-shadow:0 0 6px rgba(139,92,246,0.3);'>🚀 第3買點 (加碼/追價)</span>"

        # 連漲 3 根以上風險提示
        if up_days >= 3 and current_stage in ["TIER_2", "TIER_3"]:
            stage_verdict += f"（⚠️ 提醒：已連續推升第 {up_days} 根，短線正乖離稍大，追價者手腳需敏捷，或耐心等量縮拉回守穩 5MA 時切入！）"

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
        "b3": b3_info
    }


def render_three_tier_entry_dashboard(tier_info: dict):
    """
    在 Streamlit 中渲染老朱三層進場階梯戰術導航看板 (Three-Tier Stepper Dashboard)
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
    else:
        theme_bg = "rgba(220, 38, 38, 0.12)"
        theme_bd = "#DC2626"
        theme_color = "#F87171"

    def format_card_status(b_item, default_active_name):
        st_val = b_item.get('status', 'WAITING')
        if st_val == 'ACTIVE':
            return (
                f"<span style='background:#10B981; color:#000; font-weight:bold; padding:2px 7px; border-radius:4px; font-size:0.75rem;'>{default_active_name}</span>",
                "border: 2px solid #10B981; background: rgba(16, 185, 129, 0.08); box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);"
            )
        elif st_val == 'MISSED':
            return (
                f"<span style='background:#2A1B0E; border:1px solid #D97706; color:#FCD34D; font-weight:bold; padding:2px 6px; border-radius:4px; font-size:0.72rem;'>⌛ 買點已過 (勿追)</span>",
                "border: 1px solid #78350F; background: #1A130B; opacity: 0.9;"
            )
        elif st_val == 'PASSED':
            return (
                f"<span style='background:#1E293B; border:1px solid #475569; color:#94A3B8; font-weight:bold; padding:2px 6px; border-radius:4px; font-size:0.72rem;'>✅ 已通過</span>",
                "border: 1px solid #334155; background: #0F172A; opacity: 0.85;"
            )
        else:
            return (
                f"<span style='background:#1E293B; border:1px solid #334155; color:#64748B; padding:2px 6px; border-radius:4px; font-size:0.72rem;'>⏳ 蓄勢中</span>",
                "border: 1px solid #1E293B; background: #0B0F19;"
            )

    b1_badge, b1_style = format_card_status(b1, "🟢 進行中 (試單區)")
    b2_badge, b2_style = format_card_status(b2, "🔥 進行中 (黃金買點)")
    b3_badge, b3_style = format_card_status(b3, "🚀 進行中 (衝刺加碼)")

    if b1.get('status') == 'MISSED':
        b1_price_str = f"當時 {b1['price']:.2f} 元 <span style='font-size:0.8rem; color:#94A3B8;'>(現價 {curr_c:.2f})</span>"
    else:
        b1_price_str = f"{b1['price']:.2f} 元" if b1.get('price') else "未成形"
    b1_stop_str = f"破 {b1['stop_loss']:.2f} 停損" if b1.get('stop_loss') else "未成形"

    b2_price_str = f"{b2['price']:.2f} 元" if b2.get('price') else "未成形"
    b2_stop_str = f"破 {b2['stop_loss']:.2f} 停損" if b2.get('stop_loss') else "守5MA"

    b3_price_str = f"{b3['price']:.2f} 元" if b3.get('price') else "上方壓力"
    b3_stop_str = f"破 5MA ({b3['stop_loss']:.2f}) 移動停利" if b3.get('stop_loss') else "沿5MA停利"

    dashboard_html = f"""
    <div style="background: linear-gradient(135deg, #131722 0%, #1A2030 100%); border: 1px solid {theme_bd}; border-radius: 10px; padding: 14px 16px; margin: 10px 0 14px 0; box-shadow: 0 4px 14px rgba(0,0,0,0.3);">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 10px; margin-bottom: 12px;">
            <div>
                <span style="font-size: 1.1rem; font-weight: bold; color: #FFFFFF;">🎯 老朱三層進場階梯戰術導航</span>
                <span style="font-size: 0.85rem; color: #94A3B8; margin-left: 8px;">(進場層次 · 倉位配比 · 風控停損 SOP)</span>
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

        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px;">
            <!-- 階梯 1 卡片 -->
            <div style="{b1_style} border-radius: 8px; padding: 10px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                    <span style="font-size:0.88rem; font-weight:bold; color:#A7F3D0;">🟢 階梯一 · 底部轉折試單 (B1)</span>
                    {b1_badge}
                </div>
                <div style="font-size:1.15rem; font-weight:bold; color:#FFFFFF; margin-bottom: 4px;">
                    {b1_price_str}
                </div>
                <div style="font-size:0.8rem; color:#94A3B8; margin-bottom: 2px;">
                    💰 建議部位：<b style="color:#FBBF24;">{b1.get('position', '20%~30%')}</b>
                </div>
                <div style="font-size:0.8rem; color:#94A3B8; margin-bottom: 4px;">
                    🛡️ 防守停損：<b style="color:#EF4444;">{b1_stop_str}</b>
                </div>
                <div style="font-size:0.75rem; color:#64748B; border-top:1px dashed #334155; padding-top:4px; margin-top:4px;">
                    型態：{b1.get('desc') or b1.get('condition', '')}
                </div>
            </div>

            <!-- 階梯 2 卡片 -->
            <div style="{b2_style} border-radius: 8px; padding: 10px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                    <span style="font-size:0.88rem; font-weight:bold; color:#FDE68A;">🔥 階梯二 · 標準多頭確立 (B2)</span>
                    {b2_badge}
                </div>
                <div style="font-size:1.15rem; font-weight:bold; color:#FFFFFF; margin-bottom: 4px;">
                    {b2_price_str}
                </div>
                <div style="font-size:0.8rem; color:#94A3B8; margin-bottom: 2px;">
                    💰 建議部位：<b style="color:#FBBF24;">{b2.get('position', '60%~70%')}</b>
                </div>
                <div style="font-size:0.8rem; color:#94A3B8; margin-bottom: 4px;">
                    🛡️ 防守停損：<b style="color:#EF4444;">{b2_stop_str}</b>
                </div>
                <div style="font-size:0.75rem; color:#64748B; border-top:1px dashed #334155; padding-top:4px; margin-top:4px;">
                    型態：{b2.get('desc') or b2.get('condition', '')}
                </div>
            </div>

            <!-- 階梯 3 卡片 -->
            <div style="{b3_style} border-radius: 8px; padding: 10px 12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 6px;">
                    <span style="font-size:0.88rem; font-weight:bold; color:#DDD6FE;">🚀 階梯三 · 波段加碼追價 (B3)</span>
                    {b3_badge}
                </div>
                <div style="font-size:1.15rem; font-weight:bold; color:#FFFFFF; margin-bottom: 4px;">
                    {b3_price_str}
                </div>
                <div style="font-size:0.8rem; color:#94A3B8; margin-bottom: 2px;">
                    💰 建議部位：<b style="color:#FBBF24;">{b3.get('position', '順勢加碼')}</b>
                </div>
                <div style="font-size:0.8rem; color:#94A3B8; margin-bottom: 4px;">
                    🛡️ 移動停利：<b style="color:#38BDF8;">{b3_stop_str}</b>
                </div>
                <div style="font-size:0.75rem; color:#64748B; border-top:1px dashed #334155; padding-top:4px; margin-top:4px;">
                    型態：{b3.get('desc') or b3.get('condition', '')}
                </div>
            </div>
        </div>
    </div>
    """

    clean_html = "".join([line.strip() for line in dashboard_html.splitlines() if line.strip() and not line.strip().startswith("<!--")])
    if hasattr(st, 'html'):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)

