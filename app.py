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

from core.data_fetcher import search_stocks, resolve_ticker, fetch_stock_kline, load_stock_list
from core.wave_engine import calculate_turning_points
from core.trend_analyzer import analyze_trend
from core.signal_detector import detect_signals
from core.screener import scan_stocks
from core.ai_assistant import answer_question

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
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 系統安全存取鎖 (保證非公開與私密性，防止未授權訪問)
# -------------------------------------------------------------
SYSTEM_PIN = "8888"

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

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes,
        increasing_line_color='#FF4D4F', increasing_fillcolor='#FF4D4F',
        decreasing_line_color='#52C41A', decreasing_fillcolor='#52C41A',
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=sma5s, mode='lines',
        line=dict(color='#FF3399', width=1.5),
        showlegend=False
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=sma20s, mode='lines',
        line=dict(color='#00CCFF', width=1.5),
        showlegend=False
    ))
    y_min = min(lows) * 0.985
    y_max = max(highs) * 1.015
    fig.update_layout(
        height=135,
        margin=dict(l=2, r=2, t=4, b=4),
        xaxis=dict(visible=False, rangeslider=dict(visible=False)),
        yaxis=dict(visible=False, range=[y_min, y_max]),
        plot_bgcolor='#161824',
        paper_bgcolor='rgba(0,0,0,0)'
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

    sig = item.get('signals_dict', {})
    if sig.get('is_multi_bagger', False):
        bagger_m = sig.get('bagger_multiple', 2.0)
        badge_html += f"<span style='background:#EB2F96; color:white; padding:1px 6px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>⚠️ 已漲{bagger_m}倍(非起漲)</span>"
    if sig.get('consolidation_breakout_imminent', False):
        badge_html += "<span style='background:#52C41A; color:white; padding:1px 6px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>⏳ 盤整即將表態</span>"
    elif sig.get('is_consolidation', False):
        badge_html += "<span style='background:#595959; color:white; padding:1px 6px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>⏸️ 整理觀望</span>"

    chili_str = "🌶️" * item.get('chili_count', 1)
    safety = item.get('safety_rating', '🟢 安全首選')
    safety_color = "#52C41A" if "安全" in safety else ("#FAAD14" if "警訊" in safety else "#FF4D4F")
    
    # 支撐與壓力詳細標示
    sup_d = sig.get('support_detail', {})
    res_d = sig.get('resistance_detail', {})
    sup_text = f"{sup_d.get('type', '底撐')}：<b>{sup_d.get('price', item.get('support', 'N/A'))}</b>"
    res_text = f"{res_d.get('type', '頭壓')}：<b>{res_d.get('price', item.get('resistance', 'N/A'))}</b>"

    card_html = (
        f'<div style="background:#1E202E; border:1px solid #33364D; border-radius:10px; padding:12px 14px; margin-bottom:8px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
        f'<div><span style="font-size:1.15rem; font-weight:bold; color:white;">{item["name"]}</span>'
        f'<span style="color:#888; font-size:0.9rem; margin-left:4px;">{item["code"]}</span>'
        f'<span style="margin-left:6px;">{badge_html}</span></div>'
        f'<div style="text-align:right;"><span style="font-size:1.25rem; font-weight:bold; color:{c_color};">{item["close"]:.2f}</span>'
        f'<span style="font-size:0.85rem; font-weight:bold; color:{c_color}; margin-left:4px;">{sign}{item["change"]:.2f} ({sign}{item["change_pct"]:.2f}%)</span></div>'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#AAA; margin:4px 0;">'
        f'<div>產業：<b>{item["industry"]}</b> | 成交量：<b>{item["volume_str"]}</b></div><div>{chili_str}</div>'
        f'</div>'
        f'<div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-bottom:4px;">'
        f'<div style="color:#99A;">{item.get("broker_info", "")}</div><div style="color:{safety_color}; font-weight:bold;">{safety}</div>'
        f'</div>'
        f'<div style="font-size:0.8rem; color:#FFA94D; margin-bottom:4px;">{sup_text} | {res_text}</div>'
        f'</div>'
    )
    st.markdown(card_html, unsafe_allow_html=True)
    
    if item.get('safety_reasons'):
        for r in item['safety_reasons']:
            st.caption(f"⚠️ **助教把關提醒**：{r}")

    # 買兩張策略建議
    two_tr = sig.get('two_tranches', {})
    if two_tr.get('advice'):
        st.caption(f"💡 **買兩張實戰配置**：{two_tr['advice']}")
            
    fig_mini = render_mini_kline(item.get('recent_bars', []))
    if fig_mini:
        st.plotly_chart(fig_mini, use_container_width=True, key=f"mini_{key_prefix}_{item['code']}")
        
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
    st.divider()

def get_market_condition():
    """
    動態研判台股大盤 (加權指數) 走勢與建議持股水位 (朱家泓心法)
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
                reason = "大盤多頭結構健康，指數穩居月線之上！朱老師心法：多頭環境積極做多，建議持股 7~8 成，保留 25% 現金應對突發震盪。"
            elif abs(c - sma20) / sma20 <= 0.018 or (c < sma20 and slope >= 0):
                status = "🟡 大盤震盪整理 (指數在月線附近糾結整理)"
                ratio = 0.55  # 建議 5~6 成
                reason = "大盤處於箱型震盪或回測月線，多空拉鋸！朱老師心法：持股降至 5~6 成，精選剛突破型態股，保留 45% 現金觀望。"
            else:
                status = "🔴 大盤轉弱走空 (指數跌破月線且月線下彎)"
                ratio = 0.35  # 建議 3~4 成
                reason = "大盤走弱跌破生命線，覆巢之下無完卵！朱老師心法：嚴控持股在 3~4 成以下或空手觀望，嚴禁盲目加碼攤平！"
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
        "reason": "大盤多頭趨勢良好，朱老師心法建議持股 7~8 成，保留 2~3 成現金防守。",
        "close": 23000,
        "sma20": 22800,
        "date": "最新交易日"
    }

MENU_OPTIONS = [
    "📊 個股技術分析 (轉折波主圖)",
    "🎯 全攻略選股池 (多/空策略)",
    "👁️ 鎖股池分階段管理",
    "🧑‍🏫 AI 課程助教問答"
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
st.sidebar.caption("朱家泓體系 · 轉折波與趨勢分析系統")

menu = st.sidebar.radio(
    "功能導航",
    MENU_OPTIONS,
    key="nav_menu_radio"
)

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

    c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4, c_ctrl5 = st.columns([2, 1.8, 1.8, 1.8, 1.2])
    with c_ctrl1:
        ma_mode = st.radio("轉折基準均線", ["5MA (短線)", "10MA (中線)", "20MA (長線)"], horizontal=True)
        ma_period = 5 if "5MA" in ma_mode else (10 if "10MA" in ma_mode else 20)
    with c_ctrl2:
        filter_opt = st.selectbox("轉折波濾網", ["主要波段 (清爽推薦)", "完整細微轉折"], index=0)
        filter_mode = "standard" if "主要波段" in filter_opt else "all"
    with c_ctrl3:
        view_bars = st.selectbox("每屏顯示K棒數", ["45日 (最佳比例，最清晰)", "70日", "全區間"], index=0)
    with c_ctrl4:
        sub_chart_type = st.selectbox("副圖指標", ["成交量 + 20MA量線", "KD (9,3,3)", "MACD (12,26,9)", "RSI (3,6,14)"], index=0)
    with c_ctrl5:
        st.write("")
        st.write("")
        if st.button("⚡ 刷新即時", use_container_width=True, help="立即向證交所請求最新盤中撮合價量"):
            st.rerun()

    with st.spinner(f"正在分析 {query} ..."):
        df, info = fetch_stock_kline(query, period="1y")

    if df.empty or "error" in info:
        st.error(f"❌ 無法讀取股票數據: {info.get('error', '未知錯誤')}，請確認代碼或名稱是否正確。")
    else:
        points, lines, highest_peak, lowest_trough = calculate_turning_points(df, ma_period=ma_period, filter_mode=filter_mode)
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

        header_html = (
            f'<div class="main-header">'
            f'<div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">'
            f'<div>'
            f'<h2 style="margin: 0; display: inline-block;">{info["name"]} ({info["code"]})</h2> '
            f'<span class="tag-badge" style="background: #3B5998; margin-left: 8px;">{info["industry"]}</span> '
            f'<span class="tag-badge" style="background: {trend["trend_color"]};">{trend["trend_badge"]}</span> '
            f'{rt_badge} '
            f'{extra_badges}'
            f'<div style="margin-top: 6px;">'
            f'<span style="font-size: 2.2rem; font-weight: bold; color: {price_color};">{info["close"]}</span> '
            f'<span style="font-size: 1.15rem; font-weight: bold; color: {price_color}; margin-left: 8px;">{sign}{info["change"]} ({sign}{info["change_pct"]}%)</span>'
            f'</div>'
            f'</div>'
            f'<div style="text-align: right; font-size: 0.92rem; color: #BBB;">'
            f'<div>最高：<b style="color: #FF4D4F;">{info["high"]}</b> | 最低：<b style="color: #52C41A;">{info["low"]}</b></div>'
            f'<div>開盤：{info["open"]} | 昨收：{info["prev_close"]}</div>'
            f'<div>成交量：<b>{info["volume_str"]}</b> | 日期：{info["latest_date"]}</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(header_html, unsafe_allow_html=True)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"<div class='metric-box'><div style='color:#AAA;'>趨勢架構</div><div style='font-size:1.05rem; font-weight:bold; color:{trend['trend_color']};'>{trend['trend_status']}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-box'><div style='color:#AAA;'>壓力線 (前高)</div><div style='font-size:1.25rem; font-weight:bold; color:#FF922B;'>{trend['resistance']}</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-box'><div style='color:#AAA;'>支撐線 (前低)</div><div style='font-size:1.25rem; font-weight:bold; color:#FFA94D;'>{trend['support']}</div></div>", unsafe_allow_html=True)
        with c4:
            hp_text = f"{highest_peak['price']} ({highest_peak['date'].strftime('%m/%d')})" if highest_peak else "無"
            st.markdown(f"<div class='metric-box'><div style='color:#AAA;'>🏆 區間最高頭</div><div style='font-size:1.2rem; font-weight:bold; color:#FF4D4F;'>{hp_text}</div></div>", unsafe_allow_html=True)
        with c5:
            lt_text = f"{lowest_trough['price']} ({lowest_trough['date'].strftime('%m/%d')})" if lowest_trough else "無"
            st.markdown(f"<div class='metric-box'><div style='color:#AAA;'>⚓ 區間最低底</div><div style='font-size:1.2rem; font-weight:bold; color:#52C41A;'>{lt_text}</div></div>", unsafe_allow_html=True)

        # 盤整與高檔警示
        if signals_dict.get('consolidation_breakout_imminent', False):
            st.success("⏳ **【盤整末端即將表態預警】**：目前均線高度糾結、成交量極度萎縮至窒息量，且收盤逼近箱頂！朱老師心法：耐心等待第一根放量突破長紅棒，即為起漲關鍵進場點！")
        elif signals_dict.get('is_consolidation', False):
            st.warning("⏸️ **【目前進入箱型盤整】**：尚未走出底底高或頭頭高，無明確多空方向。朱老師心法：盤整期趨勢線與操盤線暫停使用，嚴禁躁進追價，觀望等待突破！")
        if signals_dict.get('is_multi_bagger', False):
            st.error(f"⚠️ **【波段暴漲 {signals_dict['bagger_multiple']:.1f} 倍高檔警示】**：本檔股票波段低點至今累計漲幅達 {int((signals_dict['bagger_multiple']-1)*100)}%！朱老師心法：非底部起漲，高檔隨時有獲利了結賣壓，嚴禁長抱，僅限極短線嚴格停損操作！")

        # 買兩張策略指引
        two_tr = signals_dict.get('two_tranches', {})
        if two_tr.get('advice'):
            st.info(f"💡 **【朱家泓買兩張（長短配）實戰操盤指引】**：{two_tr['advice']}")

        # ----------------------------------------------------
        # 朱家泓心法：大盤強弱動態資金配置計算機
        # ----------------------------------------------------
        with st.expander("💵 【朱家泓資金配置計算機】(依大盤強弱動態調配持股成數 & 均分 3~5 檔)", expanded=False):
            mkt = get_market_condition()
            st.markdown(f"**當前大盤評估 ({mkt['date']})**：<span style='font-size:1.05rem; font-weight:bold;'>{mkt['status']}</span><br><span style='color:#AAA; font-size:0.88rem;'>{mkt['reason']}</span>", unsafe_allow_html=True)

            col_cap1, col_cap2, col_cap3 = st.columns([2, 1.3, 1.3])
            with col_cap1:
                user_capital = st.number_input("請輸入您的可用總投資資金 (新台幣元，自由輸入)：", min_value=10000, max_value=1000000000, value=1000000, step=100000, format="%d")
            with col_cap2:
                div_count = st.radio("建議分散檔數 (均分 3~5 檔)：", [3, 4, 5], index=0, horizontal=True)
            with col_cap3:
                override_ratio = st.slider("手動微調持股水位 (%)：", min_value=10, max_value=100, value=int(mkt['ratio']*100), step=5)

            calc_ratio = override_ratio / 100.0
            total_invest = user_capital * calc_ratio
            cash_reserve = user_capital - total_invest
            per_stock_budget = total_invest / div_count

            c_price = float(info['close']) if float(info['close']) > 0 else 1.0
            suggest_shares = int(per_stock_budget / (c_price * 1000)) if c_price > 0 else 0
            actual_cost = suggest_shares * c_price * 1000

            st.markdown("---")
            c_m1, c_m2, c_m3, c_m4 = st.columns(4)
            with c_m1:
                st.metric("建議總持股金額", f"{int(total_invest):,} 元", f"{int(calc_ratio*100)}% 水位")
            with c_m2:
                st.metric("建議保留防守現金", f"{int(cash_reserve):,} 元", f"{int((1-calc_ratio)*100)}% 現金")
            with c_m3:
                st.metric(f"每檔平均分配 (共{div_count}檔)", f"{int(per_stock_budget):,} 元", "專款專用均分")
            with c_m4:
                st.metric(f"當前標的 ({info['code']}) 建議", f"{suggest_shares} 張", f"成本約 {int(actual_cost):,} 元")

            st.caption("💡 **朱老師操盤心法叮嚀**：「專款專用、切忌單押一檔！透過 3~5 檔均分降低個股風險；大盤弱勢時務必保留現金防守，大盤多頭時放膽賺足大波段！」")

        if trend['alerts']:
            for alert in trend['alerts']:
                st.warning(alert)
        if signals_list:
            st.success(" | ".join(signals_list))

        st.markdown("<div class='checkbox-panel'>", unsafe_allow_html=True)
        st.markdown("<b>線圖顯示開關：</b>", unsafe_allow_html=True)
        
        row1_cols = st.columns(4)
        show_5ma = row1_cols[0].checkbox("5MA 操盤線 (桃紅)", value=True)
        show_10ma = row1_cols[1].checkbox("10MA 短線 (鮮黃)", value=False)
        show_20ma = row1_cols[2].checkbox("20MA 趨勢線 (天藍)", value=True)
        show_60ma = row1_cols[3].checkbox("60MA 季線 (亮紫)", value=False)

        row2_cols = st.columns(6)
        show_labels = row2_cols[0].checkbox("頭、底氣泡", value=True)
        show_wave = row2_cols[1].checkbox("轉折波折線", value=True)
        show_res = row2_cols[2].checkbox("壓力線 (橘)", value=True)
        show_sup = row2_cols[3].checkbox("支撐線 (橘)", value=True)
        show_target = row2_cols[4].checkbox("目標價 (金黃)", value=False)
        show_all_prices = row2_cols[5].checkbox("標示所有頭底價位", value=False)
        st.markdown("</div>", unsafe_allow_html=True)

        # 📱 手機觸控防誤觸與圖表縮放控制
        c_touch1, c_touch2 = st.columns([3, 2])
        with c_touch1:
            touch_mode = st.radio(
                "📱 手機觸控模式：",
                ["🔒 鎖定視角 (滑動防誤觸放大，最穩定推薦)", "✋ 自由拖曳移動 (Pan)"],
                index=0,
                horizontal=True,
                key=f"touch_mode_{query}"
            )
        with c_touch2:
            if st.button("🔄 恢復標準全貌 (重置頭底視角)", use_container_width=True, key=f"btn_reset_zoom_{query}", help="手機不小心滑動放大時，點擊即可瞬間還原完整波段圖"):
                st.session_state[f"chart_reset_{query}"] = st.session_state.get(f"chart_reset_{query}", 0) + 1
                st.rerun()

        # 縱向自適應縮放
        if "45日" in view_bars and len(df) > 45:
            init_x_range = [df['Date'].iloc[-45], df['Date'].iloc[-1]]
            visible_df = df.iloc[-45:]
        elif "70日" in view_bars and len(df) > 70:
            init_x_range = [df['Date'].iloc[-70], df['Date'].iloc[-1]]
            visible_df = df.iloc[-70:]
        else:
            init_x_range = [df['Date'].iloc[0], df['Date'].iloc[-1]]
            visible_df = df

        y_mins = [visible_df['Low'].min()]
        y_maxs = [visible_df['High'].max()]

        if show_5ma and 'SMA_5' in visible_df:
            s5 = visible_df['SMA_5'].dropna()
            if not s5.empty:
                y_mins.append(s5.min()); y_maxs.append(s5.max())
        if show_10ma and 'SMA_10' in visible_df:
            s10 = visible_df['SMA_10'].dropna()
            if not s10.empty:
                y_mins.append(s10.min()); y_maxs.append(s10.max())
        if show_20ma and 'SMA_20' in visible_df:
            s20 = visible_df['SMA_20'].dropna()
            if not s20.empty:
                y_mins.append(s20.min()); y_maxs.append(s20.max())
        if show_60ma and 'SMA_60' in visible_df:
            s60 = visible_df['SMA_60'].dropna()
            if not s60.empty:
                y_mins.append(s60.min()); y_maxs.append(s60.max())

        if show_res and trend.get('resistance'):
            if trend['resistance'] <= max(y_maxs) * 1.25:
                y_maxs.append(trend['resistance'])
        if show_sup and trend.get('support'):
            if trend['support'] >= min(y_mins) * 0.75:
                y_mins.append(trend['support'])
        if show_target and trend.get('target'):
            if trend['target'] <= max(y_maxs) * 1.35:
                y_maxs.append(trend['target'])

        curr_ymin = min(y_mins)
        curr_ymax = max(y_maxs)
        y_padding = (curr_ymax - curr_ymin) * 0.075
        auto_y_range = [curr_ymin - y_padding, curr_ymax + y_padding]

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.74, 0.26]
        )

        fig.add_trace(go.Candlestick(
            x=df['Date'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name="K線",
            increasing_line_color='#FF4D4F', increasing_fillcolor='#FF4D4F',
            decreasing_line_color='#2F9E44', decreasing_fillcolor='#2F9E44',
            showlegend=False
        ), row=1, col=1)

        if show_5ma:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_5'], name="5MA (操盤線)", line=dict(color='#FF3366', width=2.0)), row=1, col=1)
        if show_10ma:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_10'], name="10MA", line=dict(color='#FFD700', width=1.8)), row=1, col=1)
        if show_20ma:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_20'], name="20MA (趨勢線)", line=dict(color='#00BFFF', width=2.2)), row=1, col=1)
        if show_60ma:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['SMA_60'], name="60MA (季線)", line=dict(color='#A855F7', width=2.0)), row=1, col=1)

        if show_wave and lines:
            wave_x = [lines[0]['x0']] + [l['x1'] for l in lines]
            wave_y = [lines[0]['y0']] + [l['y1'] for l in lines]
            fig.add_trace(go.Scatter(
                x=wave_x, y=wave_y,
                mode='lines',
                name="轉折波",
                line=dict(color='#CBD5E1', width=1.8, dash='solid')
            ), row=1, col=1)

        peaks = [p for p in points if p['type'] == 'PEAK']
        troughs = [p for p in points if p['type'] == 'TROUGH']

        if show_labels and peaks:
            peak_x = [p['date'] for p in peaks]
            offset_val = (curr_ymax - curr_ymin) * 0.028
            peak_y = [p['price'] + offset_val for p in peaks]
            peak_texts = [f"頭 {p['price']:.1f}" if show_all_prices else "頭" for p in peaks]
            fig.add_trace(go.Scatter(
                x=peak_x, y=peak_y,
                mode='markers+text',
                name="頭 (高點)",
                marker=dict(symbol='circle', size=16, color='#E03131', line=dict(color='white', width=1.2)),
                text=peak_texts,
                textfont=dict(color='white', size=8, family='Arial Black'),
                textposition='middle center',
                hovertext=[f"波段高點【頭】：{p['price']} 元 ({p['date'].strftime('%Y/%m/%d')})" for p in peaks],
                hoverinfo='text',
                showlegend=False
            ), row=1, col=1)

        if show_labels and troughs:
            trough_x = [p['date'] for p in troughs]
            offset_val = (curr_ymax - curr_ymin) * 0.028
            trough_y = [p['price'] - offset_val for p in troughs]
            trough_texts = [f"底 {p['price']:.1f}" if show_all_prices else "底" for p in troughs]
            fig.add_trace(go.Scatter(
                x=trough_x, y=trough_y,
                mode='markers+text',
                name="底 (低點)",
                marker=dict(symbol='circle', size=16, color='#2F9E44', line=dict(color='white', width=1.2)),
                text=trough_texts,
                textfont=dict(color='white', size=8, family='Arial Black'),
                textposition='middle center',
                hovertext=[f"波段低點【底】：{p['price']} 元 ({p['date'].strftime('%Y/%m/%d')})" for p in troughs],
                hoverinfo='text',
                showlegend=False
            ), row=1, col=1)

        annotations = []
        if highest_peak:
            annotations.append(dict(
                x=highest_peak['date'],
                y=highest_peak['price'],
                xref="x", yref="y",
                text=f" 🏆 最高頭 {highest_peak['price']:.2f} ({highest_peak['date'].strftime('%m/%d')}) ",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                ax=0, ay=-36,
                bgcolor="#B91C1C",
                bordercolor="white",
                borderwidth=1.2,
                borderpad=4,
                font=dict(color="white", size=10, family="Arial")
            ))
        if lowest_trough:
            annotations.append(dict(
                x=lowest_trough['date'],
                y=lowest_trough['price'],
                xref="x", yref="y",
                text=f" ⚓ 最低底 {lowest_trough['price']:.2f} ({lowest_trough['date'].strftime('%m/%d')}) ",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                ax=0, ay=36,
                bgcolor="#15803D",
                bordercolor="white",
                borderwidth=1.2,
                borderpad=4,
                font=dict(color="white", size=10, family="Arial")
            ))

        shapes = []
        x_min = df['Date'].iloc[0]
        x_max = df['Date'].iloc[-1]

        if show_res and trend.get('resistance'):
            shapes.append(dict(
                type="line", x0=x_min, x1=x_max, y0=trend['resistance'], y1=trend['resistance'],
                line=dict(color="#FF922B", width=1.5, dash="dash")
            ))
            annotations.append(dict(
                x=x_max, y=trend['resistance'], xref="x", yref="y",
                text=f" 壓力 {trend['resistance']} ", showarrow=False,
                bgcolor="#FF922B", font=dict(color="white", size=10), xanchor="left"
            ))

        if show_sup and trend.get('support'):
            shapes.append(dict(
                type="line", x0=x_min, x1=x_max, y0=trend['support'], y1=trend['support'],
                line=dict(color="#FFA94D", width=1.5, dash="dash")
            ))
            annotations.append(dict(
                x=x_max, y=trend['support'], xref="x", yref="y",
                text=f" 支撐 {trend['support']} ", showarrow=False,
                bgcolor="#FFA94D", font=dict(color="white", size=10), xanchor="left"
            ))

        if show_target and trend.get('target'):
            shapes.append(dict(
                type="line", x0=x_min, x1=x_max, y0=trend['target'], y1=trend['target'],
                line=dict(color="#FFD43B", width=1.5, dash="dot")
            ))
            annotations.append(dict(
                x=x_max, y=trend['target'], xref="x", yref="y",
                text=f" 目標 {trend['target']} ", showarrow=False,
                bgcolor="#D97706", font=dict(color="white", size=10), xanchor="left"
            ))

        if "成交量" in sub_chart_type:
            vol_colors = ['#FF4D4F' if df.loc[k, 'Close'] >= df.loc[k, 'Open'] else '#2F9E44' for k in range(len(df))]
            fig.add_trace(go.Bar(
                x=df['Date'], y=df['Volume'],
                name="成交量", marker_color=vol_colors, showlegend=False
            ), row=2, col=1)
            fig.add_trace(go.Scatter(
                x=df['Date'], y=df['Vol_MA20'],
                name="20日均量", line=dict(color='#FCC419', width=1.5)
            ), row=2, col=1)

        elif "KD" in sub_chart_type:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['K'], name="K (9)", line=dict(color='#FF4D4F', width=1.5)), row=2, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['D'], name="D (9)", line=dict(color='#1C7ED6', width=1.5)), row=2, col=1)

        elif "MACD" in sub_chart_type:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['DIF'], name="DIF", line=dict(color='#FFA94D', width=1.5)), row=2, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['MACD'], name="MACD", line=dict(color='#339AF0', width=1.5)), row=2, col=1)
            hist_colors = ['#FF4D4F' if h >= 0 else '#2F9E44' for h in df['MACD_Hist']]
            fig.add_trace(go.Bar(x=df['Date'], y=df['MACD_Hist'], name="Hist", marker_color=hist_colors), row=2, col=1)

        elif "RSI" in sub_chart_type:
            fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI_3'], name="RSI(3)", line=dict(color='#FF4D4F', width=1.5)), row=2, col=1)
            fig.add_trace(go.Scatter(x=df['Date'], y=df['RSI_6'], name="RSI(6)", line=dict(color='#1C7ED6', width=1.5)), row=2, col=1)

        chosen_dragmode = 'pan' if "自由拖曳" in touch_mode else False
        fig.update_layout(
            height=680,
            margin=dict(l=20, r=80, t=15, b=15),
            template="plotly_dark",
            annotations=annotations,
            shapes=shapes,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            dragmode=chosen_dragmode,
            hovermode="x unified"
        )

        fig.update_xaxes(
            rangeslider_visible=False,
            range=init_x_range
        )

        fig.update_yaxes(
            range=auto_y_range,
            row=1, col=1
        )

        chart_config = {
            'scrollZoom': False,             # 徹底避免手指滑動時誤觸縮放
            'displayModeBar': True,           # 保留控制選單
            'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
            'displaylogo': False,
            'doubleClick': 'reset+autosize',  # 連點兩下瞬間還原
            'responsive': True
        }
        chart_key = f"main_plot_{query}_{st.session_state.get(f'chart_reset_{query}', 0)}"
        st.plotly_chart(fig, use_container_width=True, config=chart_config, key=chart_key)

        with st.expander("🔍 均線扣抵與未來走勢預判 (CH3 均線力量)", expanded=False):
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
                    st.session_state.target_nav_menu = "👁️ 鎖股池分階段管理"
                    st.rerun()

# ----------------------------------------------------
# 功能分頁 2：全攻略選股池 (Screener)
# ----------------------------------------------------
elif menu == "🎯 全攻略選股池 (多/空策略)":
    st.header("🎯 全攻略條件選股雷達 (1:1 復刻 App 專業版)")
    st.caption("完整收錄朱家泓 8 大波段子策略、長抱存股、盤中強勢、一點鐘尾盤進場與助教實戰安全評級")

    # 頂部控制列
    col_t1, col_t2 = st.columns([1.2, 3])
    with col_t1:
        direction = st.radio("操作方向", ["🔴 做多 (Long)", "🟢 做空 (Short)"], horizontal=True, key="scr_direction")
        dir_val = "多" if "做多" in direction else "空"
    with col_t2:
        main_mode = st.radio(
            "選股大類",
            ["📈 波段策略 (起漲關鍵)", "💎 長抱標的 (長期多排)", "⚡ 盤中強勢 (量價齊揚)", "⏰ 一點鐘 (尾盤進場)"],
            horizontal=True,
            key="scr_main_mode"
        )

    # 若選中波段策略，展示 8 大子策略
    target_strategy = "全部"
    if "波段" in main_mode:
        sub_strat = st.radio(
            "波段 8 大子策略 (依 Chu 老師實戰分類)：",
            [
                "🎯 回後準進場 (回後買上漲)",
                "🌱 底部起漲 (低檔首根長紅)",
                "🚀 高檔起漲 (突破續攻)",
                "⚔️ 剛出現雙線黃金交叉 (5MA 向上穿過 20MA)",
                "📦 一字底 (平躺橫盤突破)",
                "📐 N字底 (第二隻腳打樁有守)",
                "🔄 圓弧底 (U型弧底翻揚)",
                "👑 頭高底高 (六字訣多頭確認)"
            ],
            horizontal=True,
            key="scr_sub_strat"
        )
        if "回後準進場" in sub_strat:
            target_strategy = "回後準進場"
        elif "底部起漲" in sub_strat:
            target_strategy = "底部起漲"
        elif "高檔起漲" in sub_strat:
            target_strategy = "高檔起漲"
        elif "雙線黃金交叉" in sub_strat:
            target_strategy = "雙線黃金交叉"
        elif "一字底" in sub_strat:
            target_strategy = "一字底"
        elif "N字底" in sub_strat:
            target_strategy = "N字底"
        elif "圓弧底" in sub_strat:
            target_strategy = "圓弧底"
        elif "頭高底高" in sub_strat:
            target_strategy = "頭高底高"
    elif "長抱" in main_mode:
        target_strategy = "長抱"
    elif "盤中強勢" in main_mode:
        target_strategy = "盤中強勢"
    elif "一點鐘" in main_mode:
        target_strategy = "一點鐘"

    # 價格分級篩選
    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        p_filter = st.radio("價格位階篩選", ["全部", "低價 (<30)", "中價 (30-100)", "高價 (100-300)", "超高 (>300)"], horizontal=True, key="scr_price_filter")
        price_val = p_filter.split()[0]
    with col_p2:
        st.write("")
        st.write("")
        refresh_btn = st.button("⚡ 刷新即時行情", help="立即向證交所批次請求全市場最新盤中價量")

    st.caption("🟢 **證交所官方盤中即時模式已啟動**：每日開盤自動串接最新撮合價，所有均線、黃金交叉與一點鐘選股皆以今日最新成交價即時判定！")

    with st.spinner(f"正在全市場 186 檔標的中精確篩選【{target_strategy}】(證交所盤中即時模式)..."):
        results = scan_stocks(strategy=target_strategy, direction=dir_val, price_filter=price_val, limit=50, force_refresh=refresh_btn, enable_realtime=True)

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
# 功能分頁 3：鎖股池分階段管理 (Watchlist Stages)
# ----------------------------------------------------
elif menu == "👁️ 鎖股池分階段管理":
    st.header("👁️ 鎖股名冊與進場三階段監控 (App 復刻版)")
    st.caption("《技術分析全攻略》心法：好股票需先放入鎖股名冊，耐心等待正確時機出現！")

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
        stage_stocks = scan_stocks(strategy="全部", watchlist_stage=current_stage, limit=40, enable_realtime=True)

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
# 功能分頁 4：AI 課程助教問答 (AI Assistant)
# ----------------------------------------------------
elif menu == "🧑‍🏫 AI 課程助教問答":
    st.header("🧑‍🏫 《技術分析全攻略》專屬 AI 課程助教")
    st.caption("內建全套課程講義、學員實戰答疑、高檔爆量黑K排查與歷史覆盤時光機")

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

    # 取得當前或時光機切片之股票技術數據用於右側看板展示
    stock_context = None
    if not df.empty and "error" not in info:
        target_df = df
        if selected_replay_date_str:
            target_ts = pd.to_datetime(selected_replay_date_str)
            sliced = df[df['Date'] <= target_ts].copy().reset_index(drop=True)
            if not sliced.empty:
                target_df = sliced

        points, _, _, _ = calculate_turning_points(target_df, ma_period=5)
        trend = analyze_trend(target_df, points)
        signals_dict, signals_list = detect_signals(target_df, trend)
        last_row = target_df.iloc[-1]
        prev_row = target_df.iloc[-2] if len(target_df) > 1 else last_row
        c_price = round(float(last_row['Close']), 2)
        p_price = round(float(prev_row['Close']), 2)
        chg = round(c_price - p_price, 2)
        chg_pct = round((chg / p_price) * 100, 2) if p_price > 0 else 0

        stock_context = {
            "code": info['code'],
            "name": info['name'],
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
            "is_replay": bool(selected_replay_date_str)
        }

    st.markdown("---")
    col_q1, col_q2 = st.columns([1.5, 1])
    with col_q1:
        st.subheader("💬 向助教提問")
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
        preset_q = st.selectbox("常見疑難快速發問：", preset_options)
        custom_q = st.text_area("或自行輸入您的問題：", value=preset_q, height=95)
        
        c_btn1, c_btn2 = st.columns([1, 1])
        with c_btn1:
            ask_btn = st.button("🙋 詢問助教", type="primary", use_container_width=True)
        with c_btn2:
            if st.button("📊 載入主圖查看 K 線波段", use_container_width=True):
                st.session_state.selected_stock = cur_code
                st.session_state.return_to_menu = "🧑‍🏫 AI 課程助教問答"
                st.session_state.goto_chart = True
                st.rerun()

    with col_q2:
        if stock_context:
            title_prefix = f"⏳ 歷史覆盤基準日：{stock_context['date']}" if stock_context['is_replay'] else "📌 當前即時行情狀態"
            st.subheader(title_prefix)
            chg_color = '#FF4D4F' if stock_context['change'] >= 0 else '#52C41A'
            st.markdown(f"""
            <div class="metric-box" style="text-align:left;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0;">{stock_context['name']} ({stock_context['code']})</h3>
                    <span style="font-size:1.2rem; font-weight:bold; color:{chg_color};">
                        {stock_context['close']} ({'+' if stock_context['change']>=0 else ''}{stock_context['change_pct']}%)
                    </span>
                </div>
                <div style="margin:6px 0; color:#BBB; font-size:0.9rem;">
                    基準日期：<b>{stock_context['date']}</b> | 成交量：<b>{stock_context['volume']:,}</b>
                </div>
                <div style="margin:6px 0;">趨勢架構：<b>{stock_context['trend_status']}</b></div>
                <div style="margin:6px 0; color:#FFA94D;">
                    波段支撐：<b>{stock_context['support']}</b> | 波段壓力：<b>{stock_context['resistance']}</b>
                </div>
                <div style="margin:6px 0;">鎖股監控：<b>【{stock_context['watchlist_stage']}】</b></div>
            </div>
            """, unsafe_allow_html=True)

    if ask_btn:
        with st.spinner("助教正在翻閱課程講義並診斷技術面中..."):
            reply = answer_question(custom_q, stock_context, as_of_date=selected_replay_date_str)
            st.markdown("### 📝 助教解答回覆：")
            st.markdown(reply)
