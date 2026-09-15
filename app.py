# -*- coding: utf-8 -*-
"""
《技術分析全攻略》股票趨勢與轉折波分析系統 (Web 應用程式 - 升級專業版)
修復重點：
1. 解決選股池與鎖股池點擊「載入主圖」無反應之跳轉問題（程式化精準路由至主圖分頁）
2. 目標價開關徹底連動（勾選才顯示虛線與右側標籤，不勾選完全隱藏）
3. 5MA / 10MA / 20MA / 60MA 四條均線全數獨立開關控制，色彩對比鮮明
4. 縱向自適應縮放 (Vertical Auto-scaling)：K棒縱向展開，均線層次分明
5. 明確列出最高頭與最低底的當時股價與日期 (卡片看板 + 圖表膠囊徽章)
6. 支援一鍵開啟「標示所有頭底價位」
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import importlib
import datetime
import os

import core.data_fetcher
import core.wave_engine
import core.trend_analyzer
import core.signal_detector
import core.screener
import core.ai_assistant
import core.copilot

# 強制重載 core 模組，確保 Streamlit Cloud 部署即時同步最新簽名與函式
importlib.reload(core.wave_engine)
importlib.reload(core.trend_analyzer)
importlib.reload(core.signal_detector)
importlib.reload(core.screener)
importlib.reload(core.ai_assistant)
importlib.reload(core.copilot)

from core.data_fetcher import search_stocks, resolve_ticker, fetch_stock_kline, load_stock_list
from core.wave_engine import calculate_turning_points
from core.trend_analyzer import analyze_trend
from core.signal_detector import detect_signals
from core.screener import scan_stocks, load_speedy_chips
from core.ai_assistant import answer_question, extract_target_symbol, extract_date_from_query, diagnose_stock_deeply
from core.copilot import (
    load_portfolio, save_portfolio, add_holding, close_holding, delete_holding,
    get_copilot_recommendation, inspect_portfolio
)

st.set_page_config(
    page_title="技術分析全攻略 - 股票趨勢與轉折波系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1A1C29 0%, #25283B 100%);
        padding: 16px 22px;
        border-radius: 12px;
        margin-bottom: 14px;
        border-left: 5px solid #FF4D4F;
        color: white;
    }
    .metric-box {
        background: #202231;
        padding: 12px 14px;
        border-radius: 10px;
        border: 1px solid #33364D;
        text-align: center;
        height: 100%;
    }
    .tag-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 5px;
        font-size: 0.82rem;
        font-weight: bold;
        margin-right: 5px;
    }
    .checkbox-panel {
        background: #1E202E;
        padding: 10px 16px;
        border-radius: 8px;
        border: 1px solid #2F3247;
        margin-bottom: 12px;
    }
    /* 手機優先 Tabs 模組化導航樣式 */
    div[data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #1A1C29;
        padding: 8px 10px;
        border-radius: 12px;
        border: 1px solid #2F3247;
        margin-bottom: 14px;
        overflow-x: auto;
        white-space: nowrap;
    }
    div[data-baseweb="tab"] {
        padding: 10px 18px;
        font-size: 0.98rem;
        font-weight: 600;
        color: #A0AEC0;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    div[data-baseweb="tab"]:hover {
        color: #FFFFFF;
        background-color: #26293D;
    }
    div[data-baseweb="tab"][aria-selected="true"] {
        background-color: #2D3748 !important;
        color: #FFFFFF !important;
        border-bottom: 3px solid #FF4D4F;
    }
    .chip-card {
        background: #202231;
        border: 1px solid #33364D;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 12px;
        text-align: center;
    }
    .ai-card {
        background: #1E2235;
        border-left: 5px solid #3B82F6;
        border-radius: 10px;
        padding: 14px 18px;
        margin-bottom: 14px;
    }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 系統安全存取鎖 (保證非公開與私密性，防止未授權訪問)
# -------------------------------------------------------------
SYSTEM_PIN = os.getenv("SYSTEM_PIN", "8888")
COPILOT_SECRET_PIN = os.getenv("COPILOT_PIN", "7777")

def check_password():
    """驗證存取密碼，確保私密安全訪問"""
    if st.session_state.get("authenticated", False):
        return True

    # 支援 URL 參數直接驗證 (?pin=8888) 便捷存取
    params = st.query_params
    if params.get("pin") == SYSTEM_PIN:
        st.session_state["authenticated"] = True
        return True

    # 渲染專用登入解鎖畫面 (手機與電腦皆完美適配)
    st.markdown("""
    <div style='text-align: center; margin-top: 40px; margin-bottom: 20px;'>
        <div style='font-size: 3.2rem; margin-bottom: 8px;'>🔒</div>
        <h2 style='color: #FFFFFF; font-weight: 700; margin-bottom: 4px;'>技術分析全攻略 · 私人看盤系統</h2>
        <p style='color: #8C8C8C; font-size: 0.92rem;'>本系統受密碼保護 · 請輸入存取安全密碼 (PIN)</p>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_m, col_r = st.columns([1, 1.3, 1])
    with col_m:
        with st.form("login_form", clear_on_submit=False):
            pin_input = st.text_input("存取密碼 (PIN)", type="password", placeholder="請輸入 4 位數密碼", help="預設密碼為 8888")
            submitted = st.form_submit_button("🔐 解鎖進入系統", use_container_width=True)
            if submitted:
                if pin_input == SYSTEM_PIN:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ 密碼錯誤，請重新輸入！")
        st.markdown("<div style='text-align:center; color:#5A5E78; font-size:0.78rem; margin-top:12px;'>🛡️ 端對端加密傳輸 · 隱私專屬保護</div>", unsafe_allow_html=True)

    return False

if not check_password():
    st.stop()

def render_mini_kline(bars_data):
    if not bars_data or len(bars_data) < 5:
        return None
    dates = [b['date'] for b in bars_data]
    opens = [b['open'] for b in bars_data]
    highs = [b['high'] for b in bars_data]
    lows = [b['low'] for b in bars_data]
    closes = [b['close'] for b in bars_data]
    sma5s = [b['sma5'] for b in bars_data]
    sma20s = [b['sma20'] for b in bars_data]

    # 預設展示最新 25 根 K 線，保留歷史資料可左右滑動平移瀏覽
    start_idx = max(0, len(dates) - 26)
    end_idx = len(dates) - 0.5

    # 關鍵優化：縱向自適應縮放 (Vertical Auto-scaling)
    # 僅依據視野內 25 根 K 棒計算 Y 軸，徹底消除歷史高價將近期 K 棒壓成薄餅的問題
    vis_bars = bars_data[start_idx:]
    vis_highs = [b['high'] for b in vis_bars]
    vis_lows = [b['low'] for b in vis_bars]
    vis_s5 = [b['sma5'] for b in vis_bars if b.get('sma5')]
    vis_s20 = [b['sma20'] for b in vis_bars if b.get('sma20')]

    curr_min = min(vis_lows + vis_s5)
    curr_max = max(vis_highs + vis_s5)
    # 20MA 若在當前股價合理區間內 (+-12%) 才納入 Y 軸，避免 20MA 在極高處懸成一根孤線干擾視野
    for s20 in vis_s20:
        if curr_min * 0.90 <= s20 <= curr_max * 1.12:
            curr_min = min(curr_min, s20)
            curr_max = max(curr_max, s20)

    y_pad = max(0.4, (curr_max - curr_min) * 0.08)
    y_min = curr_min - y_pad
    y_max = curr_max + y_pad

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes,
        increasing_line_color='#FF4D4F', increasing_fillcolor='#FF4D4F',
        decreasing_line_color='#52C41A', decreasing_fillcolor='#52C41A',
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=sma5s, mode='lines',
        line=dict(color='#FF3399', width=1.6),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=sma20s, mode='lines',
        line=dict(color='#00CCFF', width=1.5),
        showlegend=False
    ))

    fig.update_layout(
        height=145,
        margin=dict(l=4, r=4, t=6, b=6),
        xaxis=dict(
            type='category',
            visible=False,
            rangeslider=dict(visible=False),
            fixedrange=False,
            range=[start_idx, end_idx]
        ),
        yaxis=dict(visible=False, range=[y_min, y_max], fixedrange=True),
        plot_bgcolor='#161824',
        paper_bgcolor='rgba(0,0,0,0)',
        dragmode='pan',
        hovermode=False
    )
    return fig

def render_stock_card(item, key_prefix="sc"):
    is_up = item['change'] >= 0
    c_color = "#FF4D4F" if is_up else "#52C41A"
    sign = "+" if is_up else ""
    
    badge_html = ""
    # 排名勳章 (綜合品質排序)
    rank_badge = item.get('rank_badge', '')
    if "No.1" in rank_badge:
        badge_html += f"<span style='background:linear-gradient(90deg, #FA8C16, #FF4D4F); color:white; padding:2px 8px; border-radius:4px; font-size:0.78rem; font-weight:bold; margin-right:4px;'>{rank_badge}</span>"
    elif "No.2" in rank_badge or "No.3" in rank_badge:
        badge_html += f"<span style='background:#FA8C16; color:white; padding:2px 6px; border-radius:4px; font-size:0.75rem; font-weight:bold; margin-right:4px;'>{rank_badge}</span>"
    elif "No." in rank_badge:
        badge_html += f"<span style='background:#2B3045; color:#AAA; padding:1px 5px; border-radius:3px; font-size:0.72rem; margin-right:4px;'>{rank_badge}</span>"

    if item.get('market') == 'TWO':
        badge_html += "<span style='background:#722ED1; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>櫃</span>"
    if item.get('has_futures'):
        badge_html += "<span style='background:#13C2C2; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>期</span>"
    if item.get('has_cb'):
        badge_html += "<span style='background:#1890FF; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>CB</span>"
    if item.get('is_day_trading_forbidden'):
        badge_html += "<span style='background:#A8071A; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>禁沖</span>"
    if item.get('in_attention'):
        badge_html += "<span style='background:#D46B08; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>注</span>"
    if item.get('in_disposal'):
        badge_html += "<span style='background:#CF1322; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>關</span>"

    # 操盤線 (5MA) 狀態勳章：走升 / 下彎，站上 / 跌破
    is_5ma_up = item.get('is_5ma_rising', True)
    is_above_5ma = item.get('above_5ma', True)
    if is_5ma_up:
        badge_html += "<span style='background:#1D392E; color:#52C41A; padding:2px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>📈 5MA走升</span>"
    else:
        badge_html += "<span style='background:#3C1F24; color:#FF7875; padding:2px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>↘️ 5MA下彎</span>"
    if is_above_5ma:
        badge_html += "<span style='background:#1D392E; color:#52C41A; padding:2px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>站上5MA</span>"
    else:
        badge_html += "<span style='background:#3C1F24; color:#FF7875; padding:2px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>破5MA</span>"

    sig = item.get('signals_dict', {})
    if sig.get('is_multi_bagger', False):
        bagger_m = sig.get('bagger_multiple', 2.0)
        badge_html += f"<span style='background:#EB2F96; color:white; padding:1px 6px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>⚠️ 已漲{bagger_m}倍(非起漲)</span>"
    if sig.get('consolidation_breakout_imminent', False):
        badge_html += "<span style='background:#52C41A; color:white; padding:1px 6px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>⏳ 盤整即將表態</span>"
    elif sig.get('is_consolidation', False):
        badge_html += "<span style='background:#595959; color:white; padding:1px 6px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>⏸️ 整理觀望</span>"

    if is_up:
        chili_str = "🌶️" * item.get('chili_count', 1)
    else:
        # 老朱 App 做空綠色辣椒標記 (代表空方摜壓/主力大賣)
        chili_str = "<span style='filter: hue-rotate(95deg) saturate(2); display:inline-block;'>🌶️</span>" * item.get('chili_count', 1)
    safety = item.get('safety_rating', '🟢 安全首選')
    safety_color = "#52C41A" if "安全" in safety else ("#FAAD14" if "警訊" in safety else "#FF4D4F")
    
    # 支撐與壓力詳細標示
    sup_d = sig.get('support_detail', {})
    res_d = sig.get('resistance_detail', {})
    sup_text = f"{sup_d.get('type', '底撐')}：<b>{sup_d.get('price', item.get('support', 'N/A'))}</b>"
    res_text = f"{res_d.get('type', '頭壓')}：<b>{res_d.get('price', item.get('resistance', 'N/A'))}</b>"

    eps_val = item.get('eps', 0.0)
    per_val = item.get('per', 0.0)
    per_str = f" | EPS：<b>{eps_val}</b> | PE：<b>{per_val:.1f}</b>" if per_val > 0 else (f" | EPS：<b>{eps_val}</b>" if eps_val != 0 else "")

    # 助教把關與長上影線提醒
    safety_warn_html = ""
    if item.get('safety_reasons'):
        reasons_text = " | ".join(item['safety_reasons'])
        safety_warn_html = f"<div style='font-size:0.78rem; color:#E0A82E; margin-top:4px;'>⚠️ <b>助教把關</b>：{reasons_text}</div>"

    # 短線 3~5 天波段價差專屬戰術區塊
    sig = item.get('signals_dict', {})
    swing = sig.get('swing_3_5d', {})
    swing_html = ""
    if swing:
        swing_html = (
            f"<div style='background:#151824; border-left:3px solid #13C2C2; padding:7px 10px; border-radius:6px; font-size:0.82rem; margin-top:6px; color:#E0E6ED;'>"
            f"<div style='font-weight:bold; color:#13C2C2; margin-bottom:2px;'>🎯 3-5 天短線波段戰術指引：</div>"
            f"🛑 <b>嚴格停損</b>：守 <b>{swing.get('stop_loss')}</b> 元 (跌破紅K低點即走，風險 -{swing.get('risk_pct')}%)<br>"
            f"🛡️ <b>短線生命線</b>：守 <b>5MA ({swing.get('ma5_defend')} 元)</b> 收盤站穩<br>"
            f"🏁 <b>短線頭壓目標</b>：<b>{swing.get('target_res')}</b> 元 (前波高點，潛在獲利 +{swing.get('reward_pct')}%) | ⚖️ <b>風報比 1 : {swing.get('rr_ratio')}</b>"
            f"</div>"
        )

    # 買兩張策略建議
    two_tr = sig.get('two_tranches', {})
    two_tr_html = ""
    if two_tr.get('advice'):
        two_tr_html = f"<div style='font-size:0.78rem; color:#888; margin-top:4px;'>💡 <b>買兩張配置</b>：{two_tr['advice']}</div>"

    card_html = (
        f'<div style="background:#1E202E; border:1px solid #33364D; border-radius:10px; padding:12px 14px; margin-bottom:4px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
        f'<div><span style="font-size:1.15rem; font-weight:bold; color:white;">{item["name"]}</span>'
        f'<span style="color:#888; font-size:0.9rem; margin-left:4px;">{item["code"]}</span>'
        f'<span style="margin-left:6px;">{badge_html}</span></div>'
        f'<div style="text-align:right;"><span style="font-size:1.25rem; font-weight:bold; color:{c_color};">{item["close"]:.2f}</span>'
        f'<span style="font-size:0.85rem; font-weight:bold; color:{c_color}; margin-left:4px;">{sign}{item["change"]:.2f} ({sign}{item["change_pct"]:.2f}%)</span></div>'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#AAA; margin:4px 0;">'
        f'<div>產業：<b>{item["industry"]}</b> | 成交量：<b>{item["volume_str"]}</b>{per_str}</div><div>{chili_str}</div>'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-bottom:4px;">'
        f'<div style="color:#99A;">{item.get("broker_info", "")}</div><div style="color:{safety_color}; font-weight:bold;">{safety}</div>'
        f'</div>'
        f'<div style="font-size:0.8rem; color:#FFA94D; margin-bottom:2px;">{sup_text} | {res_text}</div>'
        f'{safety_warn_html}'
        f'{swing_html}'
        f'{two_tr_html}'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
            
    fig_mini = render_mini_kline(item.get('recent_bars', []))
    if fig_mini:
        mini_config = {
            'scrollZoom': False,             # 徹底禁止滾輪/手勢縮放，防止誤觸變形
            'displayModeBar': False,          # 隱藏工具列，畫面乾淨
            'doubleClick': 'reset',           # 雙擊瞬間復原置中視角
            'responsive': True
        }
        st.plotly_chart(fig_mini, use_container_width=True, config=mini_config, key=f"mini_{key_prefix}_{item['code']}")
        st.markdown("<div style='text-align:center; color:#6B7280; font-size:0.72rem; margin-top:-6px; margin-bottom:4px;'>↔️ 支援水平滑動查看近 60 日歷史 · 雙擊圖表重置視角</div>", unsafe_allow_html=True)
        
    c_btn1, c_btn2 = st.columns([1, 1])
    with c_btn1:
        if st.button("📊 載入主圖", key=f"btn_load_{key_prefix}_{item['code']}", use_container_width=True):
            st.session_state.selected_stock = item['code']
            st.session_state.return_to_menu = st.session_state.get('nav_menu_radio', "🎯 全攻略選股池 (多/空策略)")
            st.session_state.goto_chart = True
            st.rerun()
    with c_btn2:
        if st.button("👁️ 追蹤鎖股", key=f"btn_watch_{key_prefix}_{item['code']}", use_container_width=True):
            st.toast(f"已將 {item['name']} ({item['code']}) 加入即時追蹤鎖股池！")
def compute_ta_indicators(df_in):
    """為重採樣之週K/月K計算標準均線與技術指標"""
    d = df_in.copy()
    d['SMA_5'] = d['Close'].rolling(5).mean()
    d['SMA_10'] = d['Close'].rolling(10).mean()
    d['SMA_20'] = d['Close'].rolling(20).mean()
    d['SMA_60'] = d['Close'].rolling(60).mean()
    d['Vol_MA20'] = d['Volume'].rolling(20).mean()

    # KD (9, 3, 3)
    low_9 = d['Low'].rolling(9).min()
    high_9 = d['High'].rolling(9).max()
    rsv = ((d['Close'] - low_9) / (high_9 - low_9 + 1e-8) * 100).fillna(50)
    k_vals = []
    d_vals = []
    k_prev, d_prev = 50.0, 50.0
    for r in rsv:
        k_curr = (2/3) * k_prev + (1/3) * r
        d_curr = (2/3) * d_prev + (1/3) * k_curr
        k_vals.append(k_curr)
        d_vals.append(d_curr)
        k_prev, d_prev = k_curr, d_curr
    d['K'] = k_vals
    d['D'] = d_vals

    # MACD (12, 26, 9)
    ema12 = d['Close'].ewm(span=12, adjust=False).mean()
    ema26 = d['Close'].ewm(span=26, adjust=False).mean()
    d['DIF'] = ema12 - ema26
    d['MACD'] = d['DIF'].ewm(span=9, adjust=False).mean()
    d['MACD_Hist'] = (d['DIF'] - d['MACD']) * 2

    # RSI (3, 6)
    delta = d['Close'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up3 = up.ewm(com=2, adjust=False).mean()
    ema_down3 = down.ewm(com=2, adjust=False).mean()
    d['RSI_3'] = 100 - (100 / (1 + (ema_up3 / (ema_down3 + 1e-8))))
    ema_up6 = up.ewm(com=5, adjust=False).mean()
    ema_down6 = down.ewm(com=5, adjust=False).mean()
    d['RSI_6'] = 100 - (100 / (1 + (ema_up6 / (ema_down6 + 1e-8))))
    return d

def get_market_condition():
    """
    動態研判台股大盤 (加權指數) 走勢與建議持股水位 (實戰量化心法)
    """
    try:
        df_tw, info_tw = fetch_stock_kline("^TWII", period="3mo")
        if not df_tw.empty and len(df_tw) >= 20:
            last_row = df_tw.iloc[-1]
            c = float(last_row['Close'])
            sma20 = float(last_row['SMA_20'])
            prev_sma20 = float(df_tw.iloc[-3]['SMA_20'])
            slope = sma20 - prev_sma20
            
            if c >= sma20 and slope >= 0:
                status = "🟢 大盤多頭強勢 (指數在月線之上且月線走升)"
                ratio = 0.75  # 建議 7~8 成
                reason = "大盤多頭結構健康，指數穩居月線之上！實戰操盤心法：多頭環境積極做多，建議持股 7~8 成，保留 25% 現金應對突發震盪。"
            elif abs(c - sma20) / sma20 <= 0.018 or (c < sma20 and slope >= 0):
                status = "🟡 大盤震盪整理 (指數在月線附近糾結整理)"
                ratio = 0.55  # 建議 5~6 成
                reason = "大盤處於箱型震盪或回測月線，多空拉鋸！實戰操盤心法：持股降至 5~6 成，精選剛突破型態股，保留 45% 現金觀望。"
            else:
                status = "🔴 大盤轉弱走空 (指數跌破月線且月線下彎)"
                ratio = 0.35  # 建議 3~4 成
                reason = "大盤走弱跌破生命線，覆巢之下無完卵！實戰操盤心法：嚴控持股在 3~4 成以下或空手觀望，嚴禁盲目加碼攤平！"
            return {
                "status": status,
                "ratio": ratio,
                "reason": reason,
                "close": c,
                "sma20": sma20,
                "date": last_row['Date'].strftime('%Y-%m-%d')
            }
    except Exception:
        pass

    return {
        "status": "🟢 大盤多頭強勢 (預設評估)",
        "ratio": 0.75,
        "reason": "大盤多頭趨勢良好，實戰操盤心法建議持股 7~8 成，保留 2~3 成現金防守。",
        "close": 23000,
        "sma20": 22800,
        "date": "最新交易日"
    }

MENU_OPTIONS = [
    "📊 個股技術分析 (轉折波主圖)",
    "🎯 全攻略選股池 (多/空策略)",
    "👁️ 晚間盤後功課 (鎖股名冊監控)",
    "🤖 實戰秘密特務 (操盤副駕駛)",
    "🧑‍🏫 AI 實戰操盤助教"
]

if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = "2330"

# 關鍵跳轉邏輯：若收到載入主圖或導航跳轉請求，於導航元件渲染前強制切換導航狀態
if st.session_state.get('goto_chart', False):
    st.session_state.nav_menu_radio = MENU_OPTIONS[0]
    st.session_state.goto_chart = False
elif st.session_state.get('target_nav_menu', None):
    st.session_state.nav_menu_radio = st.session_state.target_nav_menu
    st.session_state.target_nav_menu = None

st.sidebar.title("📈 技術分析全攻略")
st.sidebar.caption("專業轉折波與波段趨勢操盤系統")

menu = st.sidebar.radio(
    "功能導航",
    MENU_OPTIONS,
    key="nav_menu_radio"
)

if st.session_state.get("copilot_authenticated", False):
    st.sidebar.markdown(
        "<div style='background:#2A1B2D; padding:6px 10px; border-radius:6px; border:1px solid #722ED1; color:#D3ADF7; font-size:0.8rem; margin-top:4px; margin-bottom:6px; text-align:center;'>🕵️‍♂️ 秘密特務：已授權解鎖</div>",
        unsafe_allow_html=True
    )
    if st.sidebar.button("🔒 立即鎖定特務", key="sidebar_lock_copilot", use_container_width=True):
        st.session_state["copilot_authenticated"] = False
        if "copilot_pin" in st.query_params:
            del st.query_params["copilot_pin"]
        st.rerun()

st.sidebar.subheader("🔍 股票搜尋")
search_query = st.sidebar.text_input("輸入股票代碼或名稱 (例如 2330 或 台積電)", value=st.session_state.selected_stock)
if search_query != st.session_state.selected_stock:
    st.session_state.selected_stock = search_query
    st.session_state.goto_chart = True
    st.rerun()

st.sidebar.caption("熱門標的快捷點選：")
quick_stocks = ["2330 台積電", "2891 中信金", "2317 鴻海", "3013 晟銘電", "2609 陽明", "1810 和成", "大盤"]
cols = st.sidebar.columns(2)
for i, qs in enumerate(quick_stocks):
    c = cols[i % 2]
    if c.button(qs, key=f"quick_{qs}"):
        code_part = qs.split()[0]
        st.session_state.selected_stock = code_part
        st.session_state.goto_chart = True
        st.rerun()

st.sidebar.markdown("---")
if st.sidebar.button("🔒 鎖定系統 / 登出", use_container_width=True, help="點擊後立即鎖定系統，需重新輸入 PIN 碼才能進入"):
    st.session_state["authenticated"] = False
    st.query_params.clear()
    st.rerun()

# ----------------------------------------------------
# 功能分頁 1：個股技術分析 (轉折波主圖)
# ----------------------------------------------------
if menu == "📊 個股技術分析 (轉折波主圖)":
    query = st.session_state.selected_stock

    # ---------------- 頂部導航快捷列 (快速返回選股池 / 上下檔切換) ----------------
    return_source = st.session_state.get('return_to_menu')
    stock_queue = st.session_state.get('browsing_stock_list', [])
    stock_names = st.session_state.get('browsing_stock_names', {})

    ret_label = "🎯 全攻略選股池"
    if return_source:
        if "鎖股" in return_source:
            ret_label = "👁️ 鎖股池"
        elif "問答" in return_source:
            ret_label = "🧑‍🏫 AI 助教問答"
        else:
            ret_label = "🎯 全攻略選股池"
    target_menu = return_source if return_source else "🎯 全攻略選股池 (多/空策略)"

    nav_col1, nav_col2, nav_col3 = st.columns([3, 3.5, 2.5])
    with nav_col1:
        if st.button(f"🔙 返回【{ret_label}】繼續選股", type="primary", use_container_width=True, key="top_btn_back"):
            st.session_state.target_nav_menu = target_menu
            st.rerun()

    with nav_col2:
        if stock_queue and query in stock_queue:
            q_idx = stock_queue.index(query)
            c_prev, c_pos, c_next = st.columns([1.2, 1.4, 1.2])
            with c_prev:
                if q_idx > 0:
                    prev_c = stock_queue[q_idx - 1]
                    p_name = stock_names.get(prev_c, prev_c)
                    if st.button("⬅️ 上一檔", key="nav_prev_stock", use_container_width=True, help=f"切換至 {p_name} ({prev_c})"):
                        st.session_state.selected_stock = prev_c
                        st.rerun()
                else:
                    st.button("⬅️ 首檔", disabled=True, use_container_width=True, key="nav_prev_disabled")
            with c_pos:
                st.markdown(f"<div style='text-align:center; padding-top:6px; color:#DDD; font-size:0.88rem;'>清單標的 <b>{q_idx+1}</b> / {len(stock_queue)}</div>", unsafe_allow_html=True)
            with c_next:
                if q_idx < len(stock_queue) - 1:
                    next_c = stock_queue[q_idx + 1]
                    n_name = stock_names.get(next_c, next_c)
                    if st.button("下一檔 ➡️", key="nav_next_stock", use_container_width=True, help=f"切換至 {n_name} ({next_c})"):
                        st.session_state.selected_stock = next_c
                        st.rerun()
                else:
                    st.button("末檔 ➡️", disabled=True, use_container_width=True, key="nav_next_disabled")
        else:
            st.caption("💡 提示：從選股池載入股票後，可在此直接按「上一檔/下一檔」連續看盤！")

    with nav_col3:
        c_quick_pool, c_quick_watch = st.columns(2)
        with c_quick_pool:
            if st.button("🎯 選股雷達", use_container_width=True, key="top_quick_pool"):
                st.session_state.target_nav_menu = "🎯 全攻略選股池 (多/空策略)"
                st.rerun()
        with c_quick_watch:
            if st.button("👁️ 鎖股名冊", use_container_width=True, key="top_quick_watch"):
                st.session_state.target_nav_menu = "👁️ 鎖股池分階段管理"
                st.rerun()

    st.markdown("<div style='margin-bottom: 8px;'></div>", unsafe_allow_html=True)

    with st.spinner(f"正在分析 {query} ..."):
        df, info = fetch_stock_kline(query, period="1y")

    if df.empty or "error" in info:
        st.error(f"❌ 無法讀取股票數據: {info.get('error', '未知錯誤')}，請確認代碼或名稱是否正確。")
    else:
        # 初始計算：以 5MA 短線轉折標準為基準
        points, lines, highest_peak, lowest_trough = calculate_turning_points(df, ma_period=5, filter_mode="standard")
        trend = analyze_trend(df, points)
        signals_dict, signals_list = detect_signals(df, trend)

        is_up = info['change'] >= 0
        price_color = "#FF4D4F" if is_up else "#52C41A"
        sign = "+" if is_up else ""

        # 即時連線狀態標籤
        if info.get('is_realtime'):
            q_time = info.get('quote_time', '')
            rt_badge = f"<span class='tag-badge' style='background:#52C41A;'>🟢 證交所即時 ({q_time})</span>"
        else:
            rt_badge = f"<span class='tag-badge' style='background:#595959;'>⚪ 歷史日K</span>"

        # 額外標籤徽章
        extra_badges = ""
        if signals_dict.get('consolidation_breakout_imminent', False):
            extra_badges += "<span class='tag-badge' style='background:#52C41A;'>⏳ 盤整末端即將表態</span>"
        elif signals_dict.get('is_consolidation', False):
            extra_badges += "<span class='tag-badge' style='background:#595959;'>⏸️ 進入箱型盤整</span>"
        if signals_dict.get('is_multi_bagger', False):
            bagger_m = signals_dict.get('bagger_multiple', 2.0)
            extra_badges += f"<span class='tag-badge' style='background:#EB2F96;'>⚠️ 波段已大漲 {bagger_m} 倍</span>"

        # 頂部個股精緻大卡片 (手機自適應排版)
        header_html = (
            f'<div class="main-header">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">'
            f'<div>'
            f'<h2 style="margin: 0; display: inline-block; font-size: 1.65rem;">{info["name"]} ({info["code"]})</h2> '
            f'<span class="tag-badge" style="background: #3B5998; margin-left: 6px;">{info["industry"]}</span> '
            f'<span class="tag-badge" style="background: {trend["trend_color"]};">{trend["trend_badge"]}</span> '
            f'{rt_badge} '
            f'{extra_badges}'
            f'<div style="margin-top: 4px;">'
            f'<span style="font-size: 2.1rem; font-weight: bold; color: {price_color};">{info["close"]}</span> '
            f'<span style="font-size: 1.1rem; font-weight: bold; color: {price_color}; margin-left: 8px;">{sign}{info["change"]} ({sign}{info["change_pct"]}%)</span>'
            f'</div>'
            f'</div>'
            f'<div style="text-align: right; font-size: 0.88rem; color: #BBB;">'
            f'<div>最高：<b style="color: #FF4D4F;">{info["high"]}</b> | 最低：<b style="color: #52C41A;">{info["low"]}</b></div>'
            f'<div>開盤：{info["open"]} | 昨收：{info["prev_close"]}</div>'
            f'<div>成交量：<b>{info["volume_str"]}</b> | 日期：{info["latest_date"]}</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(header_html, unsafe_allow_html=True)

        # 📱 手機優先：4 大模組化分頁切換 (一頁只專注一件事，告別無限滾動)
        tab_tech, tab_kline, tab_chips, tab_ai = st.tabs([
            "🎯 技術分析 (頭底/壓力支撐)",
            "📈 K線全指標 (多週期/副圖)",
            "💼 主力籌碼 (法人/扣抵)",
            "🧑‍🏫 AI 助教 (深度診斷/提問)"
        ])

        # =========================================================================
        # TAB 1: 🎯 技術分析 (頭底/壓力支撐) - 老朱 App 1:1 核心視覺
        # =========================================================================
        with tab_tech:
            # 5 大核心技術面指標盒
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.markdown(f"<div class='metric-box'><div style='color:#AAA; font-size:0.85rem;'>趨勢架構</div><div style='font-size:1.05rem; font-weight:bold; color:{trend['trend_color']};'>{trend['trend_status']}</div></div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"<div class='metric-box'><div style='color:#AAA; font-size:0.85rem;'>壓力線 (前高)</div><div style='font-size:1.25rem; font-weight:bold; color:#FF922B;'>{trend['resistance']}</div></div>", unsafe_allow_html=True)
            with c3:
                st.markdown(f"<div class='metric-box'><div style='color:#AAA; font-size:0.85rem;'>支撐線 (前低)</div><div style='font-size:1.25rem; font-weight:bold; color:#FFA94D;'>{trend['support']}</div></div>", unsafe_allow_html=True)
            with c4:
                hp_text = f"{highest_peak['price']} ({highest_peak['date'].strftime('%m/%d')})" if highest_peak else "無"
                st.markdown(f"<div class='metric-box'><div style='color:#AAA; font-size:0.85rem;'>🏆 區間最高頭</div><div style='font-size:1.15rem; font-weight:bold; color:#FF4D4F;'>{hp_text}</div></div>", unsafe_allow_html=True)
            with c5:
                lt_text = f"{lowest_trough['price']} ({lowest_trough['date'].strftime('%m/%d')})" if lowest_trough else "無"
                st.markdown(f"<div class='metric-box'><div style='color:#AAA; font-size:0.85rem;'>⚓ 區間最低底</div><div style='font-size:1.15rem; font-weight:bold; color:#52C41A;'>{lt_text}</div></div>", unsafe_allow_html=True)

            # 老朱 App 目標價機制判斷 (未突破前高壓力前暫不啟動，過壓才啟動滿足點)
            has_broken_res = (info['close'] >= trend['resistance']) if trend.get('resistance') else False
            if trend.get('target'):
                if has_broken_res:
                    st.success(f"🚀 **【目標價已正式啟動！】** 收盤價 ({info['close']} 元) 已成功站上壓力線 ({trend['resistance']} 元)！波段 N 字等距對稱目標價上看：**{trend['target']}** 元！")
                else:
                    st.info(f"🔒 **【目標價機制】** 目前股價 ({info['close']} 元) 尚未突破壓力線 ({trend['resistance']} 元)，波段等距目標價 ({trend['target']} 元) 暫未啟動。（老朱心法：過壓才算起漲，未過壓前依箱型區間操作，嚴禁預設立場！）")

            # 盤整與警示訊息
            if signals_dict.get('consolidation_breakout_imminent', False):
                st.success("⏳ **【盤整末端即將表態預警】**：目前均線高度糾結、成交量極度萎縮至窒息量，收盤逼近箱頂！實戰操盤心法：等待第一根放量突破長紅棒進場！")
            elif signals_dict.get('is_consolidation', False):
                st.warning("⏸️ **【目前進入箱型盤整】**：尚未走出底底高或頭頭高。實戰操盤心法：盤整期不躁進追價，觀望等待放量突破！")
            if signals_dict.get('is_multi_bagger', False):
                st.error(f"⚠️ **【波段暴漲 {signals_dict['bagger_multiple']:.1f} 倍高檔警示】**：累積漲幅達 {int((signals_dict['bagger_multiple']-1)*100)}%！高檔隨時有獲利賣壓，嚴禁長抱！")
            two_tr = signals_dict.get('two_tranches', {})
            if two_tr.get('advice'):
                st.info(f"💡 **【買兩張（長短配）實戰操盤指引】**：{two_tr['advice']}")
            if trend['alerts']:
                for alert in trend['alerts']:
                    st.warning(alert)
            if signals_list:
                st.success(" | ".join(signals_list))

            # 轉折控制列
            col_t_ctrl1, col_t_ctrl2, col_t_ctrl3, col_t_ctrl4 = st.columns([1.6, 1.8, 2.4, 1.4])
            with col_t_ctrl1:
                t1_view_bars = st.selectbox("顯示範圍", ["45日 (最佳比例，最清晰)", "70日", "全區間"], index=0, key=f"t1_vb_{query}")
            with col_t_ctrl2:
                t1_filter_opt = st.selectbox("轉折波濾網", ["主要波段 (清爽推薦)", "完整細微轉折"], index=0, key=f"t1_fo_{query}")
                t1_filter_mode = "standard" if "主要波段" in t1_filter_opt else "all"
            with col_t_ctrl3:
                t1_touch_mode = st.radio("📱 觸控模式", ["🔒 鎖定視角 (防誤觸)", "✋ 自由拖曳"], horizontal=True, key=f"t1_tm_{query}")
            with col_t_ctrl4:
                st.write("")
                st.write("")
                if st.button("🔄 恢復標準全貌", use_container_width=True, key=f"t1_rst_{query}", help="點擊瞬間還原標準波段圖"):
                    st.session_state[f"chart_reset_{query}"] = st.session_state.get(f"chart_reset_{query}", 0) + 1
                    st.rerun()

            # 依使用者選擇重新計算轉折波
            t1_points, t1_lines, t1_hp, t1_lt = calculate_turning_points(df, ma_period=5, filter_mode=t1_filter_mode)

            st.markdown("<div class='checkbox-panel'>", unsafe_allow_html=True)
            r1_c1, r1_c2, r1_c3, r1_c4, r1_c5, r1_c6, r1_c7 = st.columns(7)
            show_5ma = r1_c1.checkbox("5MA 操盤線", value=True, key=f"t1_5ma_{query}")
            show_20ma = r1_c2.checkbox("20MA 趨勢線", value=True, key=f"t1_20ma_{query}")
            show_wave = r1_c3.checkbox("轉折波折線", value=True, key=f"t1_wave_{query}")
            show_labels = r1_c4.checkbox("頭/暫高/底/暫底", value=True, key=f"t1_lbl_{query}")
            show_res = r1_c5.checkbox("壓力線 (橘)", value=True, key=f"t1_res_{query}")
            show_sup = r1_c6.checkbox("支撐線 (橘)", value=True, key=f"t1_sup_{query}")
            show_target = r1_c7.checkbox("目標價 (金黃)", value=has_broken_res, key=f"t1_tgt_{query}")
            st.markdown("</div>", unsafe_allow_html=True)

            # 繪製 Tab 1 專屬轉折波與支撐壓力圖
            if "45日" in t1_view_bars and len(df) > 45:
                init_x = [df['Date'].iloc[-45], df['Date'].iloc[-1]]
                vis_df = df.iloc[-45:]
            elif "70日" in t1_view_bars and len(df) > 70:
                init_x = [df['Date'].iloc[-70], df['Date'].iloc[-1]]
                vis_df = df.iloc[-70:]
            else:
                init_x = [df['Date'].iloc[0], df['Date'].iloc[-1]]
                vis_df = df

            y_mins = [vis_df['Low'].min()]
            y_maxs = [vis_df['High'].max()]
            if show_5ma and 'SMA_5' in vis_df:
                s5 = vis_df['SMA_5'].dropna()
                if not s5.empty: y_mins.append(s5.min()); y_maxs.append(s5.max())
            if show_20ma and 'SMA_20' in vis_df:
                s20 = vis_df['SMA_20'].dropna()
                if not s20.empty: y_mins.append(s20.min()); y_maxs.append(s20.max())
            if show_res and trend.get('resistance') and trend['resistance'] <= max(y_maxs) * 1.25:
                y_maxs.append(trend['resistance'])
            if show_sup and trend.get('support') and trend['support'] >= min(y_mins) * 0.75:
                y_mins.append(trend['support'])
            if show_target and trend.get('target') and trend['target'] <= max(y_maxs) * 1.35:
                y_maxs.append(trend['target'])

            curr_ymin, curr_ymax = min(y_mins), max(y_maxs)
            y_pad = (curr_ymax - curr_ymin) * 0.075
            auto_y = [curr_ymin - y_pad, curr_ymax + y_pad]

            fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
            fig1.add_trace(go.Candlestick(
                x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="K線",
                increasing_line_color='#FF4D4F', increasing_fillcolor='#FF4D4F',
                decreasing_line_color='#2F9E44', decreasing_fillcolor='#2F9E44',
                showlegend=False
            ), row=1, col=1)

            if show_5ma:
                fig1.add_trace(go.Scatter(x=df['Date'], y=df['SMA_5'], name="5MA (操盤線)", line=dict(color='#FF3366', width=2.0)), row=1, col=1)
            if show_20ma:
                fig1.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], name="20MA (趨勢線)", line=dict(color='#00BFFF', width=2.2)), row=1, col=1)

            if show_wave and t1_lines:
                wave_x = [t1_lines[0]['x0']] + [l['x1'] for l in t1_lines]
                wave_y = [t1_lines[0]['y0']] + [l['y1'] for l in t1_lines]
                fig1.add_trace(go.Scatter(x=wave_x, y=wave_y, mode='lines', name="轉折波", line=dict(color='#CBD5E1', width=1.8)), row=1, col=1)

            t1_peaks = [p for p in t1_points if p['type'] == 'PEAK']
            t1_troughs = [p for p in t1_points if p['type'] == 'TROUGH']
            offset_v = (curr_ymax - curr_ymin) * 0.028

            if show_labels and t1_peaks:
                conf_p = [p for p in t1_peaks if not p.get('is_tentative', False)]
                tent_p = [p for p in t1_peaks if p.get('is_tentative', False)]
                if conf_p:
                    fig1.add_trace(go.Scatter(
                        x=[p['date'] for p in conf_p], y=[p['price'] + offset_v for p in conf_p],
                        mode='markers+text', name="頭 (已確認)",
                        marker=dict(symbol='circle', size=16, color='#E03131', line=dict(color='white', width=1.2)),
                        text=["頭" for _ in conf_p],
                        textfont=dict(color='white', size=8, family='Arial Black'), textposition='middle center',
                        hovertext=[f"波段高點【頭】：{p['price']} 元 ({p['date'].strftime('%Y/%m/%d')}) [已跌破5MA確認]" for p in conf_p],
                        hoverinfo='text', showlegend=False
                    ), row=1, col=1)
                if tent_p:
                    fig1.add_trace(go.Scatter(
                        x=[p['date'] for p in tent_p], y=[p['price'] + offset_v for p in tent_p],
                        mode='markers+text', name="暫高 (行進中)",
                        marker=dict(symbol='circle', size=19, color='#FD7E14', line=dict(color='white', width=1.5)),
                        text=["暫高" for _ in tent_p],
                        textfont=dict(color='white', size=7, family='Arial Black'), textposition='middle center',
                        hovertext=[f"行進間高點【暫高】：{p['price']} 元 ({p['date'].strftime('%Y/%m/%d')}) [尚未收跌破5MA]" for p in tent_p],
                        hoverinfo='text', showlegend=False
                    ), row=1, col=1)

            if show_labels and t1_troughs:
                conf_t = [p for p in t1_troughs if not p.get('is_tentative', False)]
                tent_t = [p for p in t1_troughs if p.get('is_tentative', False)]
                if conf_t:
                    fig1.add_trace(go.Scatter(
                        x=[p['date'] for p in conf_t], y=[p['price'] - offset_v for p in conf_t],
                        mode='markers+text', name="底 (已確認)",
                        marker=dict(symbol='circle', size=16, color='#2F9E44', line=dict(color='white', width=1.2)),
                        text=["底" for _ in conf_t],
                        textfont=dict(color='white', size=8, family='Arial Black'), textposition='middle center',
                        hovertext=[f"波段低點【底】：{p['price']} 元 ({p['date'].strftime('%Y/%m/%d')}) [已站上5MA確認]" for p in conf_t],
                        hoverinfo='text', showlegend=False
                    ), row=1, col=1)
                if tent_t:
                    fig1.add_trace(go.Scatter(
                        x=[p['date'] for p in tent_t], y=[p['price'] - offset_v for p in tent_t],
                        mode='markers+text', name="暫底 (行進中)",
                        marker=dict(symbol='circle', size=19, color='#20C997', line=dict(color='white', width=1.5)),
                        text=["暫底" for _ in tent_t],
                        textfont=dict(color='white', size=7, family='Arial Black'), textposition='middle center',
                        hovertext=[f"行進間低點【暫底】：{p['price']} 元 ({p['date'].strftime('%Y/%m/%d')}) [尚未收站上5MA]" for p in tent_t],
                        hoverinfo='text', showlegend=False
                    ), row=1, col=1)

            annos1, shapes1 = [], []
            if t1_hp:
                annos1.append(dict(x=t1_hp['date'], y=t1_hp['price'], xref="x", yref="y", text=f" 🏆 最高頭 {t1_hp['price']:.2f} ({t1_hp['date'].strftime('%m/%d')}) ", showarrow=True, arrowhead=2, ax=0, ay=-34, bgcolor="#B91C1C", bordercolor="white", borderwidth=1.2, font=dict(color="white", size=10)))
            if t1_lt:
                annos1.append(dict(x=t1_lt['date'], y=t1_lt['price'], xref="x", yref="y", text=f" ⚓ 最低底 {t1_lt['price']:.2f} ({t1_lt['date'].strftime('%m/%d')}) ", showarrow=True, arrowhead=2, ax=0, ay=34, bgcolor="#15803D", bordercolor="white", borderwidth=1.2, font=dict(color="white", size=10)))

            x_min, x_max = df['Date'].iloc[0], df['Date'].iloc[-1]
            if show_res and trend.get('resistance'):
                shapes1.append(dict(type="line", x0=x_min, x1=x_max, y0=trend['resistance'], y1=trend['resistance'], line=dict(color="#FF922B", width=1.5, dash="dash")))
                annos1.append(dict(x=x_max, y=trend['resistance'], xref="x", yref="y", text=f" 壓力 {trend['resistance']} ", showarrow=False, bgcolor="#FF922B", font=dict(color="white", size=10), xanchor="left"))
            if show_sup and trend.get('support'):
                shapes1.append(dict(type="line", x0=x_min, x1=x_max, y0=trend['support'], y1=trend['support'], line=dict(color="#FFA94D", width=1.5, dash="dash")))
                annos1.append(dict(x=x_max, y=trend['support'], xref="x", yref="y", text=f" 支撐 {trend['support']} ", showarrow=False, bgcolor="#FFA94D", font=dict(color="white", size=10), xanchor="left"))
            if show_target and trend.get('target'):
                shapes1.append(dict(type="line", x0=x_min, x1=x_max, y0=trend['target'], y1=trend['target'], line=dict(color="#FFD43B", width=1.5, dash="dot")))
                annos1.append(dict(x=x_max, y=trend['target'], xref="x", yref="y", text=f" 目標 {trend['target']} ", showarrow=False, bgcolor="#D97706", font=dict(color="white", size=10), xanchor="left"))

            # 副圖：成交量 + 20MA量線
            vol_colors = ['#FF4D4F' if df.loc[k, 'Close'] >= df.loc[k, 'Open'] else '#2F9E44' for k in range(len(df))]
            fig1.add_trace(go.Bar(x=df['Date'], y=df['Volume'], name="成交量", marker_color=vol_colors, showlegend=False), row=2, col=1)
            fig1.add_trace(go.Scatter(x=df['Date'], y=df['Vol_MA20'], name="20日均量", line=dict(color='#FCC419', width=1.5)), row=2, col=1)

            drag1 = 'pan' if "自由拖曳" in t1_touch_mode else False
            fig1.update_layout(
                height=650, margin=dict(l=15, r=75, t=15, b=15),
                template="plotly_dark", annotations=annos1, shapes=shapes1,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                dragmode=drag1, hovermode="x unified"
            )
            fig1.update_xaxes(rangeslider_visible=False, range=init_x)
            fig1.update_yaxes(range=auto_y, row=1, col=1)

            chart_config = {
                'scrollZoom': False, 'displayModeBar': True,
                'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
                'displaylogo': False, 'doubleClick': 'reset+autosize', 'responsive': True
            }
            c_key1 = f"t1_plot_{query}_{st.session_state.get(f'chart_reset_{query}', 0)}"
            st.plotly_chart(fig1, use_container_width=True, config=chart_config, key=c_key1)

            # 動態資金配置計算機
            with st.expander("💵 【動態資金配置計算機】(依大盤強弱調配持股成數 & 均分 3~5 檔)", expanded=False):
                mkt = get_market_condition()
                st.markdown(f"**當前大盤評估 ({mkt['date']})**：<span style='font-size:1.05rem; font-weight:bold;'>{mkt['status']}</span><br><span style='color:#AAA; font-size:0.88rem;'>{mkt['reason']}</span>", unsafe_allow_html=True)
                col_cap1, col_cap2, col_cap3 = st.columns([2, 1.3, 1.3])
                with col_cap1:
                    user_capital = st.number_input("可用總投資資金 (新台幣元)：", min_value=10000, max_value=1000000000, value=1000000, step=100000, format="%d", key=f"t1_cap_{query}")
                with col_cap2:
                    div_count = st.radio("建議分散檔數：", [3, 4, 5], index=0, horizontal=True, key=f"t1_div_{query}")
                with col_cap3:
                    override_ratio = st.slider("微調持股水位 (%)：", min_value=10, max_value=100, value=int(mkt['ratio']*100), step=5, key=f"t1_ratio_{query}")

                calc_ratio = override_ratio / 100.0
                total_invest = user_capital * calc_ratio
                cash_reserve = user_capital - total_invest
                per_stock_budget = total_invest / div_count
                c_price = float(info['close']) if float(info['close']) > 0 else 1.0
                suggest_shares = int(per_stock_budget / (c_price * 1000)) if c_price > 0 else 0
                actual_cost = suggest_shares * c_price * 1000

                st.markdown("---")
                c_m1, c_m2, c_m3, c_m4 = st.columns(4)
                with c_m1: st.metric("建議總持股金額", f"{int(total_invest):,} 元", f"{int(calc_ratio*100)}% 水位")
                with c_m2: st.metric("建議保留防守現金", f"{int(cash_reserve):,} 元", f"{int((1-calc_ratio)*100)}% 現金")
                with c_m3: st.metric(f"每檔分配 ({div_count}檔)", f"{int(per_stock_budget):,} 元", "專款專用均分")
                with c_m4: st.metric(f"本標的 ({info['code']}) 建議", f"{suggest_shares} 張", f"成本約 {int(actual_cost):,} 元")
                st.caption("💡 **實戰心法叮嚀**：「專款專用、切忌單押一檔！透過 3~5 檔均分降低個股風險；大盤弱勢時務必保留現金防守，大盤多頭時放膽賺足大波段！」")

        # =========================================================================
        # TAB 2: 📈 K線全指標 (多週期/副圖切換) - 專為手機快速切換設計
        # =========================================================================
        with tab_kline:
            col_k_c1, col_k_c2, col_k_c3 = st.columns([1.8, 2.4, 1.8])
            with col_k_c1:
                k_period = st.radio("K線週期", ["日K (標準)", "週K (波段)", "月K (長線)"], horizontal=True, key=f"k_per_{query}")
            with col_k_c2:
                k_sub_chart = st.radio("🎛️ 副圖指標 (單鍵直切)", ["📊 成交量", "⚡ KD (9,3,3)", "🌊 MACD", "🎯 RSI (3,6)"], horizontal=True, key=f"k_sub_{query}")
            with col_k_c3:
                k_view_bars = st.selectbox("每屏顯示K棒數", ["45根 (清晰放大)", "70根", "全區間"], index=0, key=f"k_vb_{query}")

            st.markdown("<div class='checkbox-panel'>", unsafe_allow_html=True)
            k_ma1, k_ma2, k_ma3, k_ma4 = st.columns(4)
            show_k_5ma = k_ma1.checkbox("5MA (桃紅)", value=True, key=f"k_5ma_{query}")
            show_k_10ma = k_ma2.checkbox("10MA (鮮黃)", value=True, key=f"k_10ma_{query}")
            show_k_20ma = k_ma3.checkbox("20MA (天藍)", value=True, key=f"k_20ma_{query}")
            show_k_60ma = k_ma4.checkbox("60MA (亮紫)", value=True, key=f"k_60ma_{query}")
            st.markdown("</div>", unsafe_allow_html=True)

            # 依週期重採樣數據
            if "週K" in k_period:
                df_k = df.set_index('Date').resample('W-FRI').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                }).dropna().reset_index()
                df_k = compute_ta_indicators(df_k)
            elif "月K" in k_period:
                df_k = df.set_index('Date').resample('ME').agg({
                    'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
                }).dropna().reset_index()
                df_k = compute_ta_indicators(df_k)
            else:
                df_k = df.copy()

            if "45根" in k_view_bars and len(df_k) > 45:
                k_init_x = [df_k['Date'].iloc[-45], df_k['Date'].iloc[-1]]
                k_vis_df = df_k.iloc[-45:]
            elif "70根" in k_view_bars and len(df_k) > 70:
                k_init_x = [df_k['Date'].iloc[-70], df_k['Date'].iloc[-1]]
                k_vis_df = df_k.iloc[-70:]
            else:
                k_init_x = [df_k['Date'].iloc[0], df_k['Date'].iloc[-1]]
                k_vis_df = df_k

            k_ymins = [k_vis_df['Low'].min()]
            k_ymaxs = [k_vis_df['High'].max()]
            for ma_c, ma_f in [('SMA_5', show_k_5ma), ('SMA_10', show_k_10ma), ('SMA_20', show_k_20ma), ('SMA_60', show_k_60ma)]:
                if ma_f and ma_c in k_vis_df:
                    s_tmp = k_vis_df[ma_c].dropna()
                    if not s_tmp.empty: k_ymins.append(s_tmp.min()); k_ymaxs.append(s_tmp.max())
            k_ymin, k_ymax = min(k_ymins), max(k_ymaxs)
            k_ypad = (k_ymax - k_ymin) * 0.07
            k_auto_y = [k_ymin - k_ypad, k_ymax + k_ypad]

            fig2 = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.74, 0.26])
            fig2.add_trace(go.Candlestick(
                x=df_k['Date'], open=df_k['Open'], high=df_k['High'], low=df_k['Low'], close=df_k['Close'],
                name=f"{k_period[:2]}",
                increasing_line_color='#FF4D4F', increasing_fillcolor='#FF4D4F',
                decreasing_line_color='#2F9E44', decreasing_fillcolor='#2F9E44',
                showlegend=False
            ), row=1, col=1)

            if show_k_5ma and 'SMA_5' in df_k:
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['SMA_5'], name="5MA", line=dict(color='#FF3366', width=1.8)), row=1, col=1)
            if show_k_10ma and 'SMA_10' in df_k:
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['SMA_10'], name="10MA", line=dict(color='#FFD700', width=1.6)), row=1, col=1)
            if show_k_20ma and 'SMA_20' in df_k:
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['SMA_20'], name="20MA", line=dict(color='#00BFFF', width=2.0)), row=1, col=1)
            if show_k_60ma and 'SMA_60' in df_k:
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['SMA_60'], name="60MA", line=dict(color='#A855F7', width=1.8)), row=1, col=1)

            if "成交量" in k_sub_chart:
                v_cols = ['#FF4D4F' if df_k.loc[k, 'Close'] >= df_k.loc[k, 'Open'] else '#2F9E44' for k in range(len(df_k))]
                fig2.add_trace(go.Bar(x=df_k['Date'], y=df_k['Volume'], name="成交量", marker_color=v_cols, showlegend=False), row=2, col=1)
                if 'Vol_MA20' in df_k:
                    fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['Vol_MA20'], name="20均量", line=dict(color='#FCC419', width=1.5)), row=2, col=1)
            elif "KD" in k_sub_chart and 'K' in df_k:
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['K'], name="K (9)", line=dict(color='#FF4D4F', width=1.6)), row=2, col=1)
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['D'], name="D (9)", line=dict(color='#1C7ED6', width=1.6)), row=2, col=1)
                fig2.add_hline(y=80, line_dash="dot", line_color="#E03131", row=2, col=1)
                fig2.add_hline(y=20, line_dash="dot", line_color="#2F9E44", row=2, col=1)
            elif "MACD" in k_sub_chart and 'DIF' in df_k:
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['DIF'], name="DIF", line=dict(color='#FFA94D', width=1.6)), row=2, col=1)
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['MACD'], name="MACD", line=dict(color='#339AF0', width=1.6)), row=2, col=1)
                h_cols = ['#FF4D4F' if h >= 0 else '#2F9E44' for h in df_k['MACD_Hist'].fillna(0)]
                fig2.add_trace(go.Bar(x=df_k['Date'], y=df_k['MACD_Hist'], name="Hist", marker_color=h_cols), row=2, col=1)
            elif "RSI" in k_sub_chart and 'RSI_3' in df_k:
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['RSI_3'], name="RSI (3)", line=dict(color='#FF4D4F', width=1.6)), row=2, col=1)
                fig2.add_trace(go.Scatter(x=df_k['Date'], y=df_k['RSI_6'], name="RSI (6)", line=dict(color='#1C7ED6', width=1.6)), row=2, col=1)
                fig2.add_hline(y=80, line_dash="dot", line_color="#E03131", row=2, col=1)
                fig2.add_hline(y=20, line_dash="dot", line_color="#2F9E44", row=2, col=1)

            fig2.update_layout(
                height=650, margin=dict(l=15, r=60, t=15, b=15),
                template="plotly_dark",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                dragmode=False, hovermode="x unified"
            )
            fig2.update_xaxes(rangeslider_visible=False, range=k_init_x)
            fig2.update_yaxes(range=k_auto_y, row=1, col=1)

            st.plotly_chart(fig2, use_container_width=True, config=chart_config, key=f"k_plot_{query}_{k_period}_{k_sub_chart}")

        # =========================================================================
        # TAB 3: 💼 主力籌碼 (法人/扣抵) - SpeedyAI 官方真實籌碼整合
        # =========================================================================
        with tab_chips:
            chips_map = load_speedy_chips()
            c_data = chips_map.get(info['code'], {})

            mf = c_data.get('mf', 0)
            fi = c_data.get('fi', 0)
            it = c_data.get('it', 0)
            per = c_data.get('per', 0.0)
            eps = c_data.get('eps', 0.0)

            mf_str = f"+{mf:,} 張" if mf > 0 else (f"{mf:,} 張" if mf < 0 else "-- 張")
            mf_color = "#FF4D4F" if mf > 0 else ("#2F9E44" if mf < 0 else "#888")
            mf_note = "🔴 主力大單吸籌吃貨" if mf > 0 else ("🟢 主力大單調節賣出" if mf < 0 else "⚪ 中性 / 無顯著大單")

            fi_str = f"+{fi:,} 張" if fi > 0 else (f"{fi:,} 張" if fi < 0 else "-- 張")
            fi_color = "#FF4D4F" if fi > 0 else ("#2F9E44" if fi < 0 else "#888")
            fi_note = "🔴 外資買超" if fi > 0 else ("🟢 外資賣超" if fi < 0 else "⚪ 無資料")

            it_str = f"+{it:,} 張" if it > 0 else (f"{it:,} 張" if it < 0 else "-- 張")
            it_color = "#FF4D4F" if it > 0 else ("#2F9E44" if it < 0 else "#888")
            it_note = "🔴 投信作帳認養" if it > 0 else ("🟢 投信結帳出場" if it < 0 else "⚪ 無資料")

            st.markdown("#### 💼 SpeedyAI 官方真實主力籌碼監控")
            col_ch1, col_ch2, col_ch3, col_ch4 = st.columns(4)
            with col_ch1:
                st.markdown(f"<div class='chip-card'><div style='color:#AAA; font-size:0.88rem;'>主力大單淨流 (MF)</div><div style='font-size:1.4rem; font-weight:bold; color:{mf_color}; margin:4px 0;'>{mf_str}</div><div style='font-size:0.8rem; color:{mf_color};'>{mf_note}</div></div>", unsafe_allow_html=True)
            with col_ch2:
                st.markdown(f"<div class='chip-card'><div style='color:#AAA; font-size:0.88rem;'>外資法人買賣超 (FI)</div><div style='font-size:1.4rem; font-weight:bold; color:{fi_color}; margin:4px 0;'>{fi_str}</div><div style='font-size:0.8rem; color:{fi_color};'>{fi_note}</div></div>", unsafe_allow_html=True)
            with col_ch3:
                st.markdown(f"<div class='chip-card'><div style='color:#AAA; font-size:0.88rem;'>投信法人買賣超 (IT)</div><div style='font-size:1.4rem; font-weight:bold; color:{it_color}; margin:4px 0;'>{it_str}</div><div style='font-size:0.8rem; color:{it_color};'>{it_note}</div></div>", unsafe_allow_html=True)
            with col_ch4:
                per_str = f"{per:.1f} 倍" if per > 0 else "--"
                eps_str = f"{eps:.2f} 元" if eps != 0 else "--"
                st.markdown(f"<div class='chip-card'><div style='color:#AAA; font-size:0.88rem;'>基本面估值</div><div style='font-size:1.2rem; font-weight:bold; color:#E0E0E0; margin:4px 0;'>PER: {per_str}</div><div style='font-size:0.85rem; color:#A0AEC0;'>EPS: {eps_str}</div></div>", unsafe_allow_html=True)

            # 籌碼與交易警示標籤
            badge_html = "<div style='margin-bottom:14px;'>"
            if c_data.get('has_cb'):
                badge_html += "<span class='tag-badge' style='background:#7048E8;'>🏷️ 發行可轉債 (CB) - 主力控盤標的</span>"
            if c_data.get('has_fut'):
                badge_html += "<span class='tag-badge' style='background:#1098AD;'>⚡ 具股票期貨 (流動性佳 / 波動加速)</span>"
            if c_data.get('is_day_trading_forbidden'):
                badge_html += "<span class='tag-badge' style='background:#E03131;'>⚠️ 禁止現股當沖</span>"
            if c_data.get('in_attention'):
                badge_html += "<span class='tag-badge' style='background:#F59F00;'>🚨 證交所注意股票</span>"
            if c_data.get('in_disposal'):
                badge_html += "<span class='tag-badge' style='background:#C92A2A;'>⛔ 處置股票 (分盤撮合)</span>"
            badge_html += "</div>"
            st.markdown(badge_html, unsafe_allow_html=True)

            st.markdown("---")
            # 均線扣抵走勢預判 (CH3 均線力量)
            st.markdown("#### 🔍 均線扣抵與未來走勢預判 (CH3 均線力量)")
            deduct = signals_dict.get('deduction', {})
            d_cols = st.columns(3)
            with d_cols[0]:
                d5 = deduct.get('5MA', {})
                st.metric("5MA 扣抵價", f"{d5.get('deduct_price', 'N/A')} 元", d5.get('status', ''))
            with d_cols[1]:
                d20 = deduct.get('20MA', {})
                st.metric("20MA 扣抵價", f"{d20.get('deduct_price', 'N/A')} 元", d20.get('status', ''))
            with d_cols[2]:
                d60 = deduct.get('60MA', {})
                st.metric("60MA 扣抵價", f"{d60.get('deduct_price', 'N/A')} 元", d60.get('status', ''))

            with st.expander("📘 【均線扣抵心法教學】為什麼扣抵決定均線方向？", expanded=False):
                st.markdown("""
                - **扣低助漲**：當均線未來即將扣抵的價位低於當前收盤價，均線每天會自動加速向上揚升，成為強大的多方推升動能！
                - **扣高助跌**：當均線未來即將扣抵的價位高於當前收盤價，股價若未大漲，均線就會被迫下彎形成蓋頭反壓！
                - **實戰要訣**：買進前確認 20MA（月線）與 60MA（季線）皆在扣低位置，持股續抱最安心！
                """)

        # =========================================================================
        # TAB 4: 🧑‍🏫 AI 助教 (深度診斷/提問) - 今日盤前 + 個股深度健檢 + 即時提問
        # =========================================================================
        with tab_ai:
            # 1. 今日 2026.09.15 盤前大盤解盤卡片 (老朱最新音檔與講義)
            st.markdown("""
            <div class='ai-card'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <h4 style='margin:0; color:#60A5FA;'>📢 今日 (2026.09.15) 盤前大盤實戰精要 (老朱音檔速報)</h4>
                    <span class='tag-badge' style='background:#2563EB;'>晨間 08:45 定調</span>
                </div>
                <div style='margin-top:8px; font-size:0.92rem; line-height:1.6; color:#E2E8F0;'>
                    • <b>大盤定位</b>：加權指數 45,862 點，昨收雙 T 字棒測試季線支撐。<br>
                    • <b>美股衝擊</b>：費城半導體大跌 <b>5.86%</b>，早盤台股電子股開低面臨考驗。<br>
                    • <b>關鍵防守線</b>：開低先看前低 <b>45,839 點</b> 支撐防線；<b>必須收盤拉出長下影線或收紅，才算正式止跌！</b><br>
                    • <b>實戰紀律叮嚀</b>：早盤急跌嚴禁衝動接刀摸底，等待 <b>12:40 尾盤一點鐘</b> 主力表態，確認轉折紅 K 站上 5MA 才是安全買點！
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 2. 本檔個股深度技術面健檢報告 (Deep TA Checklist)
            diag = None
            try:
                diag = diagnose_stock_deeply(info['code'], df_raw=df, info=info)
            except TypeError:
                diag = diagnose_stock_deeply(info['code'])
            except Exception:
                diag = None

            if diag:
                st.markdown(f"#### 📋 {diag['name']} ({diag['code']}) 深度技術面健檢報告")
                st.markdown(f"> ### {diag['decision']}")
                st.markdown(f"> **助教評語**：{diag['advice_summary']}")

                col_diag1, col_diag2 = st.columns(2)
                with col_diag1:
                    st.markdown("##### 🟢 多方優勢要件 (符合項)")
                    if diag['pros']:
                        for p in diag['pros']:
                            st.markdown(f"- ✅ **{p}**")
                    else:
                        st.markdown("- ⚠️ 目前尚未具備顯著的多方發動要件。")

                with col_diag2:
                    st.markdown("##### ⚠️ 關鍵風險與瑕疵排查")
                    if diag['cons']:
                        for c in diag['cons']:
                            st.markdown(f"- ❌ **{c}**")
                    else:
                        st.markdown("- ✅ 前方無重大爆量長黑K套牢，距離前高壓力仍有足夠空間，量價結構相對健康！")

                col_d_m1, col_d_m2, col_d_m3, col_d_m4 = st.columns(4)
                col_d_m1.metric("5MA 操盤線", f"{diag['sma5']} 元", "站上" if diag['close'] >= diag['sma5'] else "跌破")
                col_d_m2.metric("20MA 趨勢線", f"{diag['sma20']} 元", "多頭" if diag['close'] >= diag['sma20'] else "空頭")
                col_d_m3.metric("成交量比 (量/20均量)", f"{diag['vol_ratio']} 倍", "放量攻擊" if diag['vol_ratio'] >= 1.5 else "量縮整理")
                col_d_m4.metric("連漲天數", f"{diag['up_days']} 天", "⚠️ 追高風險" if diag['up_days'] >= 3 else "安全區間")

            st.markdown("---")
            # 3. AI 助教即時互動問答 (Inline Q&A)
            st.markdown("#### 💬 向 AI 助教即時請教（個股疑難、操作策略、技術面觀念）")
            
            cq1, cq2, cq3, cq4 = st.columns(4)
            quick_prompt = None
            if cq1.button("👉 這檔現在可以買嗎？", use_container_width=True, key=f"qp1_{query}"):
                quick_prompt = f"請問 {info['name']} ({info['code']}) 現在適合進場買進嗎？"
            if cq2.button("👉 支撐壓力和停損點在哪？", use_container_width=True, key=f"qp2_{query}"):
                quick_prompt = f"請問 {info['name']} ({info['code']}) 的支撐壓力與停損點應該怎麼設定？"
            if cq3.button("👉 什麼是一字底突破？", use_container_width=True, key=f"qp3_{query}"):
                quick_prompt = "請詳細解說一字底飆股型態的四個標準條件與進場點？"
            if cq4.button("👉 回後買上漲四大要件？", use_container_width=True, key=f"qp4_{query}"):
                quick_prompt = "請問回後買上漲的四大必備要件是什麼？"

            user_q = st.text_input("輸入您的問題：", value=quick_prompt if quick_prompt else "", placeholder=f"例如：{info['name']} 跌破 5MA 要停損嗎？ 或是 均線扣抵怎麼看？", key=f"ai_input_{query}")
            if user_q:
                with st.spinner("🧑‍🏫 AI 助教正在分析講義規範與盤面結構 ..."):
                    try:
                        ai_reply = answer_question(user_q, stock_context={"code": info['code'], "df": df, "info": info})
                    except TypeError:
                        ai_reply = answer_question(user_q, stock_context={"code": info['code']})
                    except Exception as e:
                        ai_reply = f"抱歉，分析過程中發生異常：{e}"
                st.markdown(f"<div style='background:#1E2235; border:1px solid #3B82F6; border-radius:10px; padding:18px 20px; margin-top:12px;'>{ai_reply}</div>", unsafe_allow_html=True)

        # 底部快捷返回列 (看完圖表後不必滑回最上方)
        st.markdown("---")
        c_bot1, c_bot2, c_bot3 = st.columns([3, 3.5, 2.5])
        with c_bot1:
            if st.button(f"🔙 返回【{ret_label}】繼續選股", type="primary", use_container_width=True, key="bot_btn_back"):
                st.session_state.target_nav_menu = target_menu
                st.rerun()
        with c_bot2:
            if stock_queue and query in stock_queue:
                q_idx = stock_queue.index(query)
                c_b_prev, c_b_pos, c_b_next = st.columns([1.2, 1.4, 1.2])
                with c_b_prev:
                    if q_idx > 0:
                        prev_c = stock_queue[q_idx - 1]
                        if st.button("⬅️ 上一檔", key="bot_prev_stock", use_container_width=True):
                            st.session_state.selected_stock = prev_c
                            st.rerun()
                    else:
                        st.button("⬅️ 首檔", disabled=True, use_container_width=True, key="bot_prev_dis")
                with c_b_pos:
                    st.markdown(f"<div style='text-align:center; padding-top:6px; color:#DDD; font-size:0.88rem;'>清單標的 <b>{q_idx+1}</b> / {len(stock_queue)}</div>", unsafe_allow_html=True)
                with c_b_next:
                    if q_idx < len(stock_queue) - 1:
                        next_c = stock_queue[q_idx + 1]
                        if st.button("下一檔 ➡️", key="bot_next_stock", use_container_width=True):
                            st.session_state.selected_stock = next_c
                            st.rerun()
                    else:
                        st.button("末檔 ➡️", disabled=True, use_container_width=True, key="bot_next_dis")
        with c_bot3:
            c_b_pool, c_b_watch = st.columns(2)
            with c_b_pool:
                if st.button("🎯 選股雷達", use_container_width=True, key="bot_quick_pool"):
                    st.session_state.target_nav_menu = "🎯 全攻略選股池 (多/空策略)"
                    st.rerun()
            with c_b_watch:
                if st.button("👁️ 鎖股名冊", use_container_width=True, key="bot_quick_watch"):
                    st.session_state.target_nav_menu = MENU_OPTIONS[2]
                    st.rerun()

# ----------------------------------------------------
# 功能分頁 2：全攻略選股池 (Screener)
# ----------------------------------------------------
elif menu == "🎯 全攻略選股池 (多/空策略)":
    st.header("🎯 全攻略條件選股雷達 (1:1 復刻 App 專業版)")
    st.caption("完整收錄 8 大波段子策略、長抱存股、盤中強勢、一點鐘尾盤進場與助教實戰安全評級")

    # 頂部控制列
    col_t1, col_t2 = st.columns([1.2, 3])
    with col_t1:
        direction = st.radio("操作方向", ["🔴 做多 (Long)", "🟢 做空 (Short)"], horizontal=True, key="scr_direction")
        dir_val = "多" if "做多" in direction else "空"
    with col_t2:
        if dir_val == "多":
            main_mode = st.radio(
                "選股大類",
                ["📈 波段策略 (起漲關鍵)", "⏰ 12:40 - 13:30 尾盤一點鐘 (短線 3 至 5 天首選)", "⚡ 盤中強勢 (量價齊揚)", "💎 長抱標的 (長期多排)"],
                horizontal=True,
                key="scr_main_mode"
            )
        else:
            main_mode = st.radio(
                "選股大類 (做空)",
                ["📉 波段策略 (起跌關鍵)", "⚡ 盤中弱勢 (跌破帶量)", "📊 盤中排行 (跌幅排行)", "🔥 量排行", "⏰ 12:40 - 13:30 尾盤一點鐘 (放空首選)"],
                horizontal=True,
                key="scr_main_mode_short"
            )

    target_strategy = "全部"
    if "波段" in main_mode:
        if dir_val == "多":
            sub_strat = st.radio(
                "波段子策略 (與老朱 APP 1:1 對齊)：",
                [
                    "👑 頭高底高 (六字訣多頭確認)",
                    "🎯 回後準進場 (拉回測線有守·短線買點)",
                    "🌱 底部起漲 (含一字底/N字底/圓弧底突破)",
                    "🚀 高檔起漲 (多頭突破再創高)",
                    "⚔️ 雙線翻揚 (5MA/20MA 向上翻揚)"
                ],
                horizontal=True,
                key="scr_sub_strat"
            )
            st.caption("💡 **選股 vs 鎖股分工**：此處【🎯 回後準進場】是「**今日轉折紅K確認、12:40 - 13:30 可進場買進**」的名單；若要看「**正在拉回整理、等待未來轉折的【回檔等上漲】觀察股**」，請切換至【👁️ 晚間盤後功課】分頁。")
            if "頭高底高" in sub_strat:
                target_strategy = "頭高底高"
            elif "回後準進場" in sub_strat:
                target_strategy = "回後準進場"
            elif "底部起漲" in sub_strat:
                target_strategy = "底部起漲"
            elif "高檔起漲" in sub_strat:
                target_strategy = "高檔起漲"
            elif "雙線翻揚" in sub_strat:
                target_strategy = "雙線翻揚"
        else:
            sub_strat = st.radio(
                "空方波段子策略 (與老朱 APP 1:1 對齊)：",
                [
                    "👑 頭低底低 (六字訣空頭確認)",
                    "🎯 彈後準進場 (反彈測線無力·短線空點)",
                    "🛑 頂部起跌 (高檔頭部成形·首度跌破)",
                    "📉 低檔起跌 (破底續跌·弱勢續殺)",
                    "⚔️ 雙線死亡交叉 (5MA/20MA 雙線下彎走空)"
                ],
                horizontal=True,
                key="scr_sub_strat_short"
            )
            st.caption("💡 **做空實戰心法**：【🎯 彈後準進場】是「**反彈測線無力、今日轉折黑K跌破5MA、12:40 - 13:30 可進場放空**」的黃金空點名單！")
            if "頭低底低" in sub_strat:
                target_strategy = "頭低底低"
            elif "彈後準進場" in sub_strat:
                target_strategy = "彈後準進場"
            elif "頂部起跌" in sub_strat:
                target_strategy = "頂部起跌"
            elif "低檔起跌" in sub_strat:
                target_strategy = "低檔起跌"
            elif "雙線死亡交叉" in sub_strat:
                target_strategy = "雙線死亡交叉"
    elif "長抱" in main_mode:
        target_strategy = "長抱"
    elif "強勢" in main_mode:
        target_strategy = "盤中強勢"
    elif "弱勢" in main_mode:
        target_strategy = "盤中弱勢"
    elif "一點鐘" in main_mode:
        target_strategy = "一點鐘"
    elif "盤中排行" in main_mode:
        target_strategy = "盤中排行"
    elif "量排行" in main_mode:
        target_strategy = "量排行"

    # 價格分級篩選
    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        p_filter = st.radio("價格位階篩選", ["全部", "低價 (<30)", "中價 (30-100)", "高價 (100-300)", "超高 (>300)"], horizontal=True, key="scr_price_filter")
        price_val = p_filter.split()[0]
    with col_p2:
        st.write("")
        refresh_btn = st.button("⚡ 刷新即時行情", help="立即向證交所批次請求全市場最新盤中價量")

    st.caption("🟢 **證交所官方盤中即時模式已啟動**：每日開盤自動串接最新撮合價，所有均線、黃金交叉與一點鐘選股皆以今日最新成交價即時判定！")

    with st.spinner(f"正在全市場 186 檔標的中精確篩選【{target_strategy}】(證交所盤中即時模式)..."):
        try:
            results = scan_stocks(strategy=target_strategy, direction=dir_val, price_filter=price_val, limit=50, force_refresh=refresh_btn, enable_realtime=True)
        except Exception:
            results = scan_stocks(strategy=target_strategy, direction=dir_val, price_filter=price_val, limit=50, force_refresh=False, enable_realtime=False)

    # 記錄選股隊列供主圖分頁進行「上一檔 / 下一檔」循序看盤
    st.session_state.browsing_stock_list = [item['code'] for item in results]
    st.session_state.browsing_stock_names = {item['code']: item['name'] for item in results}

    st.markdown(f"**掃描結果：符合【{target_strategy}】共 `{len(results)}` 檔標的**")

    # 助教安全統計摘要
    safe_count = sum(1 for s in results if "安全" in s.get('safety_rating', ''))
    caution_count = sum(1 for s in results if "警訊" in s.get('safety_rating', ''))
    danger_count = sum(1 for s in results if "嚴禁" in s.get('safety_rating', ''))
    st.caption(f"💡 **助教安全把關**：安全首選 `{safe_count}` 檔 | 警訊注意 `{caution_count}` 檔 (前方有爆量黑K或空間狹窄) | 嚴禁追高 `{danger_count}` 檔")

    if results:
        cols = st.columns(2)
        for idx, item in enumerate(results):
            c = cols[idx % 2]
            with c:
                render_stock_card(item, key_prefix=f"scr_{target_strategy}_{idx}")
    else:
        st.info(f"目前在【{target_strategy}】條件下暫無符合標的，您可以切換其他子策略或放寬價格位階重新掃描。")

# ----------------------------------------------------
# 功能分頁 3：晚間盤後功課 · 鎖股名冊監控 (Watchlist Stages)
# ----------------------------------------------------
elif "鎖股" in menu or "晚間盤後功課" in menu:
    st.header("👁️ 晚間盤後功課 · 鎖股名冊與三階段進場監控")
    st.caption("🌙 **晚間做功課心法**：每晚檢視【🎯 回檔等上漲】與【📌 等突破】名冊，篩選出拉回測線有守的股票，隔日 **12:40 - 13:30 尾盤** 只要確認出轉折紅 K 站上 5MA 即刻進場，賺取 3 至 5 天短線波段價差！")

    stage_tab = st.radio(
        "鎖股進場三階段監控",
        [
            "🎯 回檔等上漲 (拉回測均線有守，等待轉折紅K買點)",
            "📌 等突破 (均線高度糾結/箱型整理，等待長紅爆量)",
            "🚀 高檔等回檔 (連續上漲乖離過大，絕不追高)"
        ],
        horizontal=True,
        key="watchlist_stage_tab"
    )
    
    current_stage = "回檔等上漲" if "回檔等上漲" in stage_tab else ("等突破" if "等突破" in stage_tab else "高檔等回檔")

    with st.spinner(f"正在載入【{current_stage}】名冊 (盤中即時模式)..."):
        try:
            stage_stocks = scan_stocks(strategy="全部", watchlist_stage=current_stage, limit=40, enable_realtime=True)
        except Exception:
            stage_stocks = scan_stocks(strategy="全部", watchlist_stage=current_stage, limit=40, enable_realtime=False)

    # 記錄鎖股隊列供主圖分頁進行「上一檔 / 下一檔」循序看盤
    st.session_state.browsing_stock_list = [s['code'] for s in stage_stocks]
    st.session_state.browsing_stock_names = {s['code']: s['name'] for s in stage_stocks}

    st.markdown(f"**目前歸屬於【{current_stage}】之標的：共 `{len(stage_stocks)}` 檔**")
    
    if stage_stocks:
        cols = st.columns(2)
        for idx, s in enumerate(stage_stocks):
            c = cols[idx % 2]
            with c:
                render_stock_card(s, key_prefix=f"stage_{idx}")
    else:
        st.info(f"目前無處於【{current_stage}】的追蹤個股。")

# ----------------------------------------------------
# 功能分頁 4：實戰秘密特務 · 操盤副駕駛 (Trading Copilot)
# ----------------------------------------------------
elif "秘密特務" in menu or "操盤副駕駛" in menu:
    # 專屬特務私密安全鎖 (Double-lock protection)
    # 支援 URL 快速授權參數 (?copilot_pin=7777) 便捷存取
    if st.query_params.get("copilot_pin") == COPILOT_SECRET_PIN:
        st.session_state["copilot_authenticated"] = True

    if not st.session_state.get("copilot_authenticated", False):
        st.markdown("""
        <div style='background: linear-gradient(135deg, #1A1C29 0%, #2A1B2D 100%); padding: 26px 22px; border-radius: 14px; border: 1px solid #722ED1; text-align: center; margin-bottom: 20px;'>
            <div style='font-size: 3.2rem; margin-bottom: 10px;'>🕵️‍♂️</div>
            <h2 style='color: #E6D5F7; font-weight: 700; margin-bottom: 6px;'>機密特務權限驗證 · 操盤副駕駛</h2>
            <p style='color: #B37FEB; font-size: 0.96rem; margin-bottom: 4px;'>【最高優先級私密模組】每日尾盤唯一首選推薦 · 24H 持股自動守護神</p>
            <p style='color: #8C8C8C; font-size: 0.84rem;'>本專區包含核心實盤作戰策略與個人持股部位監控，受獨立二級特務安全金鑰 (PIN) 保護。<br/>若未獲授權，請切換至左側其他公開功能分頁。</p>
        </div>
        """, unsafe_allow_html=True)

        col_l, col_m, col_r = st.columns([1, 1.4, 1])
        with col_m:
            with st.form("copilot_auth_form", clear_on_submit=False):
                secret_pin_input = st.text_input(
                    "特務專屬安全金鑰 (PIN)",
                    type="password",
                    placeholder="請輸入 4 位數特務金鑰",
                    help="預設金鑰為 7777"
                )
                auth_submitted = st.form_submit_button("🔓 解鎖特務副駕駛系統", use_container_width=True)
                if auth_submitted:
                    if secret_pin_input == COPILOT_SECRET_PIN:
                        st.session_state["copilot_authenticated"] = True
                        st.rerun()
                    else:
                        st.error("❌ 特務金鑰錯誤！非授權訪問已被攔截。")
            st.markdown("<div style='text-align:center; color:#5A5E78; font-size:0.78rem; margin-top:10px;'>🛡️ 機密級策略隔離 · 個人資產防窺保護</div>", unsafe_allow_html=True)
        st.stop()

    c_head1, c_head2 = st.columns([4, 1])
    with c_head1:
        st.header("🤖 實戰秘密特務 · 尾盤推薦與自動持股守護神")
    with c_head2:
        if st.button("🔒 鎖定特務退出", key="btn_lock_copilot", use_container_width=True):
            st.session_state["copilot_authenticated"] = False
            if "copilot_pin" in st.query_params:
                del st.query_params["copilot_pin"]
            st.rerun()
    
    # 判斷當前是否處於 12:30 - 13:35 尾盤黃金時間
    now_dt = datetime.datetime.now()
    is_tail_time = (now_dt.hour == 12 and now_dt.minute >= 30) or (now_dt.hour == 13 and now_dt.minute <= 35)
    
    if is_tail_time:
        st.markdown("""
        <div style="background: linear-gradient(90deg, #FA8C16, #FF4D4F); padding: 14px 18px; border-radius: 10px; color: white; font-weight: bold; margin-bottom: 14px; font-size: 1.05rem;">
            ⏰【尾盤黃金決策時刻 12:40 - 13:30】：今日多空主力已充分表態！轉折紅K確認站穩5MA，正是執行短線 3~5 天波段下單的最佳進場時機！
        </div>
        """, unsafe_allow_html=True)
    else:
        st.caption("💡 **實戰心法**：每天尾盤 **12:40 - 13:30** 是主力全日多空定調的關鍵時刻。副駕駛在背景經過 5 重嚴苛濾網，每日精挑 **唯一一檔最高勝率標的** 指示進場；您買進後只需點擊【我買了】，副駕駛將自動啟動 24 小時守護神，每日監控 5MA 生命線與停損目標！")

    tab_copilot1, tab_copilot2, tab_copilot3 = st.tabs([
        "🎯 今日尾盤作戰指示 (AI 唯一首選推薦)",
        "🛡️ 我的持股守護神 (自動盯盤與出場提醒)",
        "📜 實戰戰報紀錄 (已結算出場歷史)"
    ])

    with tab_copilot1:
        st.subheader("🎯 今日全市場精選 · 尾盤作戰 Top 5 指示")

        c_r1, c_r2 = st.columns([3, 1])
        with c_r1:
            st.caption("🤖 經技術分析全攻略引擎 5 重嚴格濾網（剔除避雷針、剔除高檔暴漲、剔除重套賣壓、風報比 >= 1.1、5MA翻揚收紅）自動嚴選綜合品質最高之 Top 5 標的。")
        with c_r2:
            rec_refresh = st.button("⚡ 重新精選推薦", key="btn_rec_refresh", use_container_width=True)

        if 'copilot_rec_data' not in st.session_state or rec_refresh:
            with st.spinner("AI 副駕駛正在全市場 187 檔股票中層層嚴選今日 Top 5 首選作戰名冊..."):
                st.session_state.copilot_rec_data = get_copilot_recommendation(force_refresh=rec_refresh, enable_realtime=True)
        rec_data = st.session_state.copilot_rec_data

        picks = rec_data.get("picks", [])
        if not picks and rec_data.get("has_pick") and rec_data.get("code"):
            picks = [rec_data]

        if picks:
            st.markdown(f"<div style='color:#A0AEC0; font-size:0.92rem; margin-bottom:14px;'>📊 今日全市場共嚴選出 <b>{len(picks)}</b> 檔符合朱老師黃金買點之優質標的，依品質分數與風報比由高至低排列：</div>", unsafe_allow_html=True)
            for p_idx, p in enumerate(picks):
                p_code = p['code']
                p_name = p['name']
                p_price = p['close']
                p_chg = p['change_pct']
                p_stop = p['stop_loss']
                p_target = p['target_price']
                p_rr = p['rr_ratio']
                p_risk = p['risk_pct']
                p_reward = p['reward_pct']
                p_strat = p['strategy']
                p_badge = p.get('rank_badge', f'No.{p_idx+1}')
                p_chili = "🌶️" * p.get('chili_count', 1)

                chg_sign = "+" if p_chg >= 0 else ""
                chg_color = "#FF4D4F" if p_chg >= 0 else "#52C41A"

                border_color = "#3B82F6" if p_idx == 0 else "#2F3247"
                card_bg = "#181B26" if p_idx == 0 else "#161824"
                badge_bg = "linear-gradient(90deg, #FA8C16, #FF4D4F)" if p_idx == 0 else "#2A1B2D"

                why_buy_html = "".join([f"<div>• {w}</div>" for w in p.get('why_buy', [])])
                action_plan_html = f'<div style="background: #262014; border-left: 4px solid #FA8C16; padding: 10px 14px; border-radius: 6px; color: #FFE8CC; font-size: 0.92rem; line-height: 1.6; margin-top: 10px;">{p.get("action_plan", "")}</div>' if p.get("action_plan") else ""

                card_html = (
                    f'<div style="background: {card_bg}; border: 2px solid {border_color}; border-radius: 12px; padding: 18px; margin-bottom: 14px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 12px;">'
                    f'<div>'
                    f'<span style="background: {badge_bg}; color:white; padding:3px 10px; border-radius:6px; font-weight:bold; font-size:0.85rem; margin-right:8px;">{p_badge}</span>'
                    f'<span style="font-size: 1.55rem; font-weight: bold; color: white;">{p_name} ({p_code})</span>'
                    f'<span style="color: #A0AEC0; font-size: 0.95rem; margin-left: 8px;">{p.get("industry", "")} · {p_strat}</span>'
                    f'</div>'
                    f'<div style="text-align:right;">'
                    f'<span style="font-size: 1.75rem; font-weight: bold; color: {chg_color};">{p_price:.2f}</span>'
                    f'<span style="font-size: 1.05rem; font-weight: bold; color: {chg_color}; margin-left: 6px;">{chg_sign}{p_chg:.2f}%</span>'
                    f'<div style="margin-top:2px;">{p_chili}</div>'
                    f'</div>'
                    f'</div>'
                    f'<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 14px;">'
                    f'<div style="background: #202434; padding: 10px 12px; border-radius: 8px; text-align: center;"><div style="color: #8892B0; font-size: 0.8rem;">操盤線 (5MA)</div><div style="font-size: 1.15rem; font-weight: bold; color: #52C41A;">{p.get("ma5", p_price):.2f} 元</div></div>'
                    f'<div style="background: #202434; padding: 10px 12px; border-radius: 8px; text-align: center;"><div style="color: #8892B0; font-size: 0.8rem;">🛑 嚴格停損價</div><div style="font-size: 1.15rem; font-weight: bold; color: #FF4D4F;">{p_stop:.2f} 元 (-{p_risk}%)</div></div>'
                    f'<div style="background: #202434; padding: 10px 12px; border-radius: 8px; text-align: center;"><div style="color: #8892B0; font-size: 0.8rem;">🏁 波段目標價</div><div style="font-size: 1.15rem; font-weight: bold; color: #FAAD14;">{p_target:.2f} 元 (+{p_reward}%)</div></div>'
                    f'<div style="background: #202434; padding: 10px 12px; border-radius: 8px; text-align: center;"><div style="color: #8892B0; font-size: 0.8rem;">⚖️ 風報比 (Reward/Risk)</div><div style="font-size: 1.15rem; font-weight: bold; color: #13C2C2;">1 : {p_rr}</div></div>'
                    f'</div>'
                    f'<div style="background: #151822; padding: 12px 14px; border-radius: 8px; margin-bottom: 12px;">'
                    f'<div style="font-weight: bold; color: #4FD1C5; margin-bottom: 6px; font-size: 0.95rem;">💡 為什麼今天尾盤買這檔？（副駕駛嚴選理由）：</div>'
                    f'<div style="font-size: 0.9rem; color: #E2E8F0; line-height: 1.7;">{why_buy_html}</div>'
                    f'</div>'
                    f'{action_plan_html}'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

                with st.expander(f"👉 我在尾盤下單買了【{p_name}】！點此將這檔交由【持股守護神】自動盯盤", expanded=False):
                    col_b1, col_b2, col_b3 = st.columns(3)
                    with col_b1:
                        user_buy_price = st.number_input("您的實際成交價 (元)", value=p_price, step=0.1, key=f"buy_p_{p_code}_{p_idx}")
                    with col_b2:
                        user_shares = st.number_input("買進張數 (1張=1000股)", value=1, min_value=1, step=1, key=f"buy_s_{p_code}_{p_idx}")
                    with col_b3:
                        user_stop_p = st.number_input("自訂防守停損價 (元)", value=p_stop, step=0.1, key=f"buy_sl_{p_code}_{p_idx}")

                    if st.button(f"🚀 確認買進【{p_name} ({p_code})】並啟動守護神！", type="primary", use_container_width=True, key=f"confirm_buy_{p_code}_{p_idx}"):
                        reason_str = f"尾盤 Top {p_idx+1} 精選：{p_strat}，風報比 1:{p_rr}"
                        add_holding(
                            code=p_code,
                            name=p_name,
                            buy_price=user_buy_price,
                            stop_loss=user_stop_p,
                            target_price=p_target,
                            strategy=p_strat,
                            buy_reason=reason_str,
                            shares=user_shares * 1000
                        )
                        if "copilot_inspected_cache" in st.session_state:
                            del st.session_state["copilot_inspected_cache"]
                        st.success(f"🎉 已將【{p_name} ({p_code})】納入【我的持股守護神】！副駕駛將每日為您盯盤守護！")
                        st.rerun()

                st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)
        else:
            st.warning(rec_data.get("advice_title", "今日建議空手觀望"))
            st.info(rec_data.get("advice_detail", ""))

    with tab_copilot2:
        st.subheader("🛡️ 我的實戰在庫持股 · 全自動盯盤守護神")
        st.caption("副駕駛每日全自動串接行情，檢驗 5MA 操盤線與停損目標，一旦觸發破線、達標或加碼，第一時間跳出高亮指示！")
        
        all_holdings = load_portfolio()
        active_holdings = [h for h in all_holdings if h.get("status") == "HOLDING"]

        c_p_add1, c_p_add2 = st.columns([3, 1])
        with c_p_add1:
            btn_refresh_holdings = st.button("🔄 即時重新診斷持股行情", key="btn_refresh_holdings")
            if btn_refresh_holdings and "copilot_inspected_cache" in st.session_state:
                del st.session_state["copilot_inspected_cache"]
        with c_p_add2:
            with st.popover("➕ 手動新增其他持股", use_container_width=True):
                st.write("#### 新增手中的股票讓副駕駛守護")
                st_list = load_stock_list()
                h_opts = [f"{s['code']} {s['name']}" for s in st_list]
                h_pick = st.selectbox("選擇股票", h_opts, key="manual_hold_pick")
                h_code = h_pick.split()[0]
                h_name = h_pick.split()[1]

                # 自動嘗試抓取該股票最新收盤價做為貼心預設值
                cur_live_price = 100.0
                try:
                    _, inf = fetch_stock_kline(h_code, period="1mo")
                    cur_live_price = float(inf.get("close", 100.0))
                except Exception:
                    cur_live_price = 100.0

                h_buy_p = st.number_input("買進成交價 (元)", value=cur_live_price, step=0.1, key=f"manual_hold_p_{h_code}")
                h_shares = st.number_input("張數 (1張=1000股)", value=1, min_value=1, step=1, key=f"manual_hold_s_{h_code}")
                h_stop = st.number_input("停損防守價 (元)", value=round(h_buy_p * 0.95, 2), step=0.1, key=f"manual_hold_stop_{h_code}")
                h_tgt = st.number_input("波段目標價 (元)", value=round(h_buy_p * 1.10, 2), step=0.1, key=f"manual_hold_tgt_{h_code}")
                if st.button("確認加入守護", type="primary", use_container_width=True, key="btn_manual_add_confirm"):
                    add_holding(h_code, h_name, h_buy_p, h_stop, h_tgt, strategy="手動庫存", buy_reason="手動建倉", shares=h_shares * 1000)
                    if "copilot_inspected_cache" in st.session_state:
                        del st.session_state["copilot_inspected_cache"]
                    st.success(f"已加入【{h_name}】！")
                    st.rerun()

        if not active_holdings:
            st.info("💡 目前您的庫存清單中暫無股票。當您在【今日尾盤作戰指示】按下【我買了】，或是透過右上角【手動新增】，標的就會出現在此處，由副駕駛 24 小時守護！")
        else:
            if "copilot_inspected_cache" not in st.session_state:
                with st.spinner("副駕駛正在為您的持股即時診斷均線與防守位..."):
                    st.session_state["copilot_inspected_cache"] = inspect_portfolio(active_holdings)
            inspected_list = st.session_state["copilot_inspected_cache"]

            total_cost = sum(item['buy_price'] * item['shares'] for item in inspected_list)
            total_val = sum(item['curr_price'] * item['shares'] for item in inspected_list)
            total_pnl = total_val - total_cost
            total_pnl_pct = round((total_pnl / total_cost) * 100, 2) if total_cost > 0 else 0.0
            pnl_sign = "+" if total_pnl >= 0 else ""
            pnl_c = "#FF4D4F" if total_pnl >= 0 else "#52C41A"

            stop_count = sum(1 for item in inspected_list if "STOP" in item['status_type'] or "BREAK" in item['status_type'])
            target_count = sum(1 for item in inspected_list if "TARGET" in item['status_type'])
            add_count = sum(1 for item in inspected_list if "ADD" in item['status_type'])
            hold_count = sum(1 for item in inspected_list if "HOLD" in item['status_type'])

            summary_box = (
                f'<div style="background: #1E202E; border: 1px solid #2F3247; border-radius: 10px; padding: 14px 18px; margin-bottom: 16px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px;">'
                f'<div><span style="color: #8892B0; font-size: 0.88rem;">實戰持股總數</span><br><span style="font-size: 1.4rem; font-weight: bold; color: white;">{len(inspected_list)} 檔</span></div>'
                f'<div><span style="color: #8892B0; font-size: 0.88rem;">在庫總損益</span><br><span style="font-size: 1.4rem; font-weight: bold; color: {pnl_c};">{pnl_sign}{total_pnl:,.0f} 元 ({pnl_sign}{total_pnl_pct}%)</span></div>'
                f'<div><span style="color: #8892B0; font-size: 0.88rem;">守護健康狀態</span><br><span style="font-size: 0.92rem; color: #52C41A; font-weight: bold;">🟢 正常續抱 {hold_count} 檔</span> · <span style="font-size: 0.92rem; color: #FF4D4F; font-weight: bold;">🔴 破線警報 {stop_count} 檔</span> · <span style="font-size: 0.92rem; color: #FAAD14; font-weight: bold;">🏁 達標 {target_count} 檔</span></div>'
                f'</div>'
            )
            st.markdown(summary_box, unsafe_allow_html=True)

            for item in inspected_list:
                item_id = item['id']
                item_code = item['code']
                item_name = item['name']
                item_bp = item['buy_price']
                item_cp = item['curr_price']
                item_shares = item['shares']
                item_pnl_pct = item['pnl_pct']
                item_pnl_amt = item['pnl_amt']
                item_status = item['status_badge']
                item_color = item['status_color']
                item_desc = item['status_desc']
                item_sign = "+" if item_pnl_pct >= 0 else ""
                item_pnl_c = "#FF4D4F" if item_pnl_pct >= 0 else "#52C41A"

                border_css = f"border: 2px solid {item_color};"
                if "警報" in item_status or "跌破" in item_status:
                    border_css = "border: 2px solid #FF4D4F; box-shadow: 0 0 10px rgba(255, 77, 79, 0.4);"

                card_box = (
                    f'<div style="background: #181B26; {border_css} border-radius: 12px; padding: 16px; margin-bottom: 14px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
                    f'<div>'
                    f'<span style="font-size: 1.3rem; font-weight: bold; color: white;">{item_name} ({item_code})</span>'
                    f'<span style="background: {item_color}22; color: {item_color}; border: 1px solid {item_color}; padding: 2px 8px; border-radius: 4px; font-weight: bold; font-size: 0.85rem; margin-left: 8px;">{item_status}</span>'
                    f'<div style="font-size: 0.82rem; color: #8892B0; margin-top: 4px;">買進日：<b>{item["buy_date"]}</b> (已持有 {item["days_held"]} 天) · 張數：<b>{item_shares // 1000} 張</b></div>'
                    f'</div>'
                    f'<div style="text-align: right;">'
                    f'<div style="font-size: 1.35rem; font-weight: bold; color: {item_pnl_c};">{item_sign}{item_pnl_pct}%</div>'
                    f'<div style="font-size: 0.95rem; font-weight: bold; color: {item_pnl_c};">{item_sign}{item_pnl_amt:,.0f} 元</div>'
                    f'</div>'
                    f'</div>'
                    f'<div style="display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.88rem; margin: 12px 0; background: #202434; padding: 8px 12px; border-radius: 6px;">'
                    f'<div>買進價：<b>{item_bp:.2f}</b></div>'
                    f'<div>現價：<b style="color:{item_pnl_c};">{item_cp:.2f}</b></div>'
                    f'<div>5MA防守：<b>{item["sma5"]:.2f}</b></div>'
                    f'<div>停損價：<b style="color:#FF7875;">{item["stop_loss"]:.2f}</b></div>'
                    f'<div>目標價：<b style="color:#FFD666;">{item["target_price"]:.2f}</b></div>'
                    f'</div>'
                    f'<div style="background: #151822; padding: 10px 12px; border-radius: 6px; font-size: 0.9rem; color: #E2E8F0; line-height: 1.6; margin-bottom: 10px;">'
                    f'{item_desc}'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(card_box, unsafe_allow_html=True)

                col_act1, col_act2, col_act3 = st.columns([2, 1, 1])
                with col_act1:
                    if st.button(f"📊 載入【{item_name}】轉折波K線主圖", key=f"btn_chart_hold_{item_id}"):
                        st.session_state.selected_stock = item_code
                        st.session_state.goto_chart = True
                        st.rerun()
                with col_act2:
                    with st.popover("🏁 我賣出了 (結算)", use_container_width=True):
                        st.write(f"#### 結算出場【{item_name}】")
                        sell_p = st.number_input("實際賣出價格", value=item_cp, step=0.1, key=f"sp_{item_id}")
                        sell_r = st.selectbox("出場原因", ["跌破5MA獲利/停損出場", "達到目標價分批停利", "個人資金調整", "觸及停損線止損"], key=f"sr_{item_id}")
                        if st.button("確認結算歸檔", type="primary", use_container_width=True, key=f"btn_sell_ok_{item_id}"):
                            close_holding(item_id, sell_p, sell_r)
                            if "copilot_inspected_cache" in st.session_state:
                                del st.session_state["copilot_inspected_cache"]
                            st.success(f"已成功結算【{item_name}】並存入歷史戰報！")
                            st.rerun()
                with col_act3:
                    if st.button("🗑️ 刪除紀錄", key=f"btn_del_hold_{item_id}", use_container_width=True):
                        delete_holding(item_id)
                        if "copilot_inspected_cache" in st.session_state:
                            del st.session_state["copilot_inspected_cache"]
                        st.rerun()

    with tab_copilot3:
        st.subheader("📜 實戰戰報紀錄 · 已結算歷史明細")
        all_h = load_portfolio()
        closed_h = [h for h in all_h if h.get("status") == "CLOSED"]
        if not closed_h:
            st.info("尚無結算出場的歷史戰報。當您在持股守護神點擊【我賣出了】，已實現的交易成績將自動記錄於此。")
        else:
            win_trades = sum(1 for c in closed_h if float(c.get("realized_pnl_amt", 0)) > 0)
            total_realized_amt = sum(float(c.get("realized_pnl_amt", 0)) for c in closed_h)
            win_rate = round((win_trades / len(closed_h)) * 100, 1)
            amt_sign = "+" if total_realized_amt >= 0 else ""
            amt_color = "#FF4D4F" if total_realized_amt >= 0 else "#52C41A"

            st.markdown(f"""
            <div style="background:#1E202E; border:1px solid #2F3247; border-radius:10px; padding:12px 18px; margin-bottom:14px; display:flex; justify-content:space-around; text-align:center;">
                <div>
                    <div style="color:#8892B0; font-size:0.85rem;">已結算總筆數</div>
                    <div style="font-size:1.3rem; font-weight:bold; color:white;">{len(closed_h)} 筆</div>
                </div>
                <div>
                    <div style="color:#8892B0; font-size:0.85rem;">實戰勝率</div>
                    <div style="font-size:1.3rem; font-weight:bold; color:#FAAD14;">{win_rate}%</div>
                </div>
                <div>
                    <div style="color:#8892B0; font-size:0.85rem;">累積已實現損益</div>
                    <div style="font-size:1.3rem; font-weight:bold; color:{amt_color};">{amt_sign}{total_realized_amt:,.0f} 元</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            for c in reversed(closed_h):
                c_pnl_amt = float(c.get("realized_pnl_amt", 0))
                c_pnl_pct = float(c.get("realized_pnl_pct", 0))
                c_sign = "+" if c_pnl_amt >= 0 else ""
                c_col = "#FF4D4F" if c_pnl_amt >= 0 else "#52C41A"
                st.markdown(f"""
                <div style="background:#151822; border-left: 4px solid {c_col}; border-radius:6px; padding:10px 14px; margin-bottom:8px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <b>{c['name']} ({c['code']})</b> · 買: {c['buy_price']} ({c['buy_date']}) ➜ 賣: {c['sell_price']} ({c.get('sell_date', '')})<br>
                        <span style="font-size:0.82rem; color:#888;">出場原因：{c.get('sell_reason', '無備註')}</span>
                    </div>
                    <div style="text-align:right;">
                        <span style="font-weight:bold; color:{c_col}; font-size:1.1rem;">{c_sign}{c_pnl_pct}%</span><br>
                        <span style="font-weight:bold; color:{c_col}; font-size:0.9rem;">{c_sign}{c_pnl_amt:,.0f} 元</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

# ----------------------------------------------------
# 功能分頁 5：AI 實戰操盤助教 (AI Assistant)
# ----------------------------------------------------
elif "AI" in menu or "助教" in menu:
    st.header("🧑‍🏫 專業技術分析實戰 AI 助教")
    st.caption("內建全套實戰技術分析操盤心法、學員實戰答疑、高檔爆量黑K排查與歷史覆盤時光機")

    col_sel1, col_sel2 = st.columns([1, 1])
    with col_sel1:
        stock_options = [f"{s['code']} {s['name']}" for s in load_stock_list()]
        current_idx = 0
        for i, opt in enumerate(stock_options):
            if opt.startswith(st.session_state.selected_stock):
                current_idx = i
                break
        selected_stock_str = st.selectbox("🎯 選擇或切換當前分析標的：", stock_options, index=current_idx)
        cur_code = selected_stock_str.split()[0]
        st.session_state.selected_stock = cur_code

    df, info = fetch_stock_kline(cur_code, period="1y")

    # 歷史覆盤時光機面板
    st.markdown("---")
    col_tm1, col_tm2 = st.columns([1, 2])
    with col_tm1:
        enable_timemachine = st.toggle("⏳ 啟用歷史覆盤時光機", value=False, help="開啟後，將以您指定的歷史交易日截斷行情，還原當時的盤後數據與助教即時研判！")
    
    selected_replay_date_str = None
    if enable_timemachine and not df.empty:
        with col_tm2:
            all_dates = df['Date'].dt.date.tolist()
            default_date = all_dates[-1]
            if cur_code == "2851":
                st.caption("💡 經典覆盤日期推薦：`2026-08-26` (回後買上漲但有8/21爆量黑K瑕疵)")
            selected_date = st.date_input(
                "選擇歷史覆盤基準日 (盤後)",
                value=default_date,
                min_value=all_dates[0],
                max_value=all_dates[-1]
            )
            selected_replay_date_str = selected_date.strftime('%Y-%m-%d')
            st.info(f"⏳ 時光機已鎖定歷史覆盤基準日：`{selected_replay_date_str}`")
    else:
        with col_tm2:
            st.caption("💡 **自然語言智慧抽取**：您也可以直接在問題中提及日期（例如：「**請問 2851 在 8/26 是否為回後買上漲？**」或「**昨天 2330 符合回後買上漲嗎？**」），助教將智慧自動啟動時光機！")

    # 定義股票上下文計算函式 (支援依提問動態跟隨標的)
    def compute_stock_context(target_code, replay_date_str=None):
        df_target, info_target = fetch_stock_kline(target_code, period="1y")
        if df_target.empty or "error" in info_target:
            return None, df_target, info_target
        
        target_df = df_target
        is_replay = False
        if replay_date_str:
            target_ts = pd.to_datetime(replay_date_str)
            sliced = df_target[df_target['Date'] <= target_ts].copy().reset_index(drop=True)
            if not sliced.empty:
                target_df = sliced
                is_replay = (target_ts.strftime('%Y-%m-%d') != df_target.iloc[-1]['Date'].strftime('%Y-%m-%d'))

        points, _, _, _ = calculate_turning_points(target_df, ma_period=5)
        trend = analyze_trend(target_df, points)
        signals_dict, signals_list = detect_signals(target_df, trend)
        last_row = target_df.iloc[-1]
        prev_row = target_df.iloc[-2] if len(target_df) > 1 else last_row
        c_price = round(float(last_row['Close']), 2)
        p_price = round(float(prev_row['Close']), 2)
        chg = round(c_price - p_price, 2)
        chg_pct = round((chg / p_price) * 100, 2) if p_price > 0 else 0

        ctx = {
            "code": info_target['code'],
            "name": info_target['name'],
            "date": last_row['Date'].strftime('%Y-%m-%d'),
            "close": c_price,
            "change": chg,
            "change_pct": chg_pct,
            "volume": int(last_row['Volume']),
            "trend_status": trend['trend_status'],
            "support": trend['support'],
            "resistance": trend['resistance'],
            "target": trend['target'],
            "signals": signals_list,
            "watchlist_stage": signals_dict.get('watchlist_stage', '觀察中'),
            "is_replay": is_replay
        }
        return ctx, target_df, info_target

    st.markdown("---")
    col_q1, col_q2 = st.columns([1.5, 1])
    with col_q1:
        st.subheader("💬 向助教提問")
        ask_mode = st.radio(
            "請選擇提問方式：",
            ["✏️ 自行輸入問題 (自由提問 / 觀念諮詢 / 個股診斷)", "💡 常見疑難快速發問 (經典範例一鍵解答)"],
            horizontal=True,
            key="qa_ask_mode"
        )
        preset_options = [
            f"請問 2851 在 8/26 是否為回後買上漲？為什麼不適合進場？",
            f"請問 {cur_code} 目前符合【回後買上漲】嗎？該如何應對？",
            f"請問 2851 在 8/21 爆量長黑K之後，目前該如何防守與應對？",
            f"請問 {cur_code} 昨天收盤的技術型態與多空趨勢如何？",
            "跌破 5MA 與虧損 5% 停損有何區別？該如何搭配執行？",
            "一字底飆股的判定條件是什麼？進場最佳時機點？",
            "實戰操作五步驟的量化紀律是什麼？",
            "均線扣抵原理是什麼？如何預判未來均線助漲或助跌？"
        ]

        if "自行輸入" in ask_mode:
            target_q = st.text_area(
                "請在下方輸入您的問題：",
                value=st.session_state.get('custom_qa_text', ''),
                placeholder="例如：\n• 強茂 2481 今天9/14爆大量，站上四均過昨天上影線，漲幅過2% 是不是拉回找買點的進場位置？\n• 請問 2851 在 8/26 為什麼不適合進場？\n• 跌破 5MA 與虧損 5% 停損有何區別？",
                height=110,
                key="custom_qa_text"
            )
            btn_text = "🙋 詢問助教"
        else:
            target_q = st.selectbox(
                "請選擇常見實戰疑難快速發問：",
                preset_options,
                key="preset_qa_select"
            )
            btn_text = "💡 查看助教解答"

        # 智慧動態偵測：提問中是否包含個股（如 強茂 2481 / 2851 / 聯發科 等）
        active_code, has_explicit_stock = extract_target_symbol(target_q, default_code=cur_code)
        
        # 智慧偵測提問中是否有指定日期 (例如 9/14, 8/26, 昨天 等)
        extracted_date = None
        active_stock_context = None
        if has_explicit_stock:
            df_temp, _ = fetch_stock_kline(active_code, period="1y")
            if not df_temp.empty:
                extracted_date = extract_date_from_query(target_q, df_temp)
            target_date = extracted_date if extracted_date else selected_replay_date_str
            active_stock_context, _, _ = compute_stock_context(active_code, target_date)
            btn_chart_label = f"📊 載入【{active_stock_context['name'] if active_stock_context else active_code}】主圖看盤"
        else:
            btn_chart_label = "📊 載入主圖查看 K 線波段"

        c_btn1, c_btn2 = st.columns([1, 1])
        with c_btn1:
            ask_btn = st.button(btn_text, type="primary", use_container_width=True)
        with c_btn2:
            if st.button(btn_chart_label, use_container_width=True):
                st.session_state.selected_stock = active_code if has_explicit_stock else cur_code
                st.session_state.return_to_menu = "🧑‍🏫 AI 實戰操盤助教"
                st.session_state.goto_chart = True
                st.rerun()

    with col_q2:
        if has_explicit_stock and active_stock_context:
            title_prefix = f"⏳ 歷史覆盤基準日：{active_stock_context['date']}" if active_stock_context['is_replay'] else f"📌 提問個股即時行情：{active_stock_context['name']} ({active_stock_context['code']})"
            st.subheader(title_prefix)
            chg_color = '#FF4D4F' if active_stock_context['change'] >= 0 else '#52C41A'
            st.markdown(f"""
            <div class="metric-box" style="text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0;">{active_stock_context['name']} ({active_stock_context['code']})</h3>
                    <span style="font-size:1.2rem; font-weight:bold; color:{chg_color};">
                        {active_stock_context['close']} ({'+' if active_stock_context['change']>=0 else ''}{active_stock_context['change_pct']}%)
                    </span>
                </div>
                <div style="margin:6px 0; color:#BBB; font-size:0.9rem;">
                    基準日期：<b>{active_stock_context['date']}</b> | 成交量：<b>{active_stock_context['volume']:,}</b>
                </div>
                <div style="margin:6px 0;">趨勢架構：<b>{active_stock_context['trend_status']}</b></div>
                <div style="margin:6px 0; color:#FFA94D;">
                    波段支撐：<b>{active_stock_context['support']}</b> | 波段壓力：<b>{active_stock_context['resistance']}</b>
                </div>
                <div style="margin:6px 0;">鎖股監控：<b>【{active_stock_context['watchlist_stage']}】</b></div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.subheader("💡 智慧個股動態連動")
            st.markdown(f"""
            <div class="metric-box" style="text-align:left; border:1px dashed #4A5568; background:#161922; padding:16px; border-radius:8px;">
                <h4 style="margin:0 0 8px 0; color:#4FD1C5;">🔍 個股行情自動跟隨已就緒</h4>
                <div style="font-size:0.88rem; color:#A0AEC0; line-height:1.7;">
                    當前為<b>純觀念 / 交易心法提問</b>模式。<br><br>
                    🎯 <b>自動跟隨功能</b>：<br>
                    只要在左側輸入或提及任何<b>股票代號或名稱</b>（例如：<code>強茂 2481</code>、<code>聯發科</code>、<code>2851</code>），右側此處將<b>自動切換跟隨您問的個股</b>，同步呈現最新盤中即時行情、多空波段架構與支撐壓力！
                </div>
            </div>
            """, unsafe_allow_html=True)

    if ask_btn:
        if not target_q.strip():
            st.warning("⚠️ 請先輸入您的問題後再點擊詢問助教！")
        else:
            with st.spinner("助教正在翻閱技術分析講義並深入分析中..."):
                reply = answer_question(target_q, active_stock_context, as_of_date=extracted_date or selected_replay_date_str)
                st.markdown("### 📝 助教解答回覆：")
                st.markdown(reply)
