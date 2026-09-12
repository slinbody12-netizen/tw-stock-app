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
    if item.get('market') == 'TWO':
        badge_html += "<span style='background:#722ED1; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>櫃</span>"
    if item.get('has_futures'):
        badge_html += "<span style='background:#13C2C2; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>期</span>"
    if item.get('has_cb'):
        badge_html += "<span style='background:#1890FF; color:white; padding:1px 5px; border-radius:3px; font-size:0.75rem; margin-right:3px;'>CB</span>"

    chili_str = "🌶️" * item.get('chili_count', 1)
    safety = item.get('safety_rating', '🟢 安全首選')
    safety_color = "#52C41A" if "安全" in safety else ("#FAAD14" if "警訊" in safety else "#FF4D4F")
    
    st.markdown(f"""
    <div style="background:#1E202E; border:1px solid #33364D; border-radius:10px; padding:12px 14px; margin-bottom:8px;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start;">
            <div>
                <span style="font-size:1.15rem; font-weight:bold; color:white;">{item['name']}</span>
                <span style="color:#888; font-size:0.9rem; margin-left:4px;">{item['code']}</span>
                <span style="margin-left:6px;">{badge_html}</span>
            </div>
            <div style="text-align:right;">
                <span style="font-size:1.25rem; font-weight:bold; color:{c_color};">{item['close']:.2f}</span>
                <span style="font-size:0.85rem; font-weight:bold; color:{c_color}; margin-left:4px;">{sign}{item['change']:.2f} ({sign}{item['change_pct']:.2f}%)</span>
            </div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.82rem; color:#AAA; margin:4px 0;">
            <div>產業：<b>{item['industry']}</b> | 成交量：<b>{item['volume_str']}</b></div>
            <div>{chili_str}</div>
        </div>
        <div style="display:flex; justify-content:space-between; font-size:0.82rem; margin-bottom:4px;">
            <div style="color:#99A;">主力：{item.get('broker_info', '')}</div>
            <div style="color:{safety_color}; font-weight:bold;">{safety}</div>
        </div>
        <div style="font-size:0.8rem; color:#FFA94D; margin-bottom:4px;">
            支撐：<b>{item.get('support', 'N/A')}</b> | 壓力：<b>{item.get('resistance', 'N/A')}</b>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if item.get('safety_reasons'):
        for r in item['safety_reasons']:
            st.caption(f"⚠️ **助教把關提醒**：{r}")
            
    fig_mini = render_mini_kline(item.get('recent_bars', []))
    if fig_mini:
        st.plotly_chart(fig_mini, use_container_width=True, key=f"mini_{key_prefix}_{item['code']}")
        
    c_btn1, c_btn2 = st.columns([1, 1])
    with c_btn1:
        if st.button("📊 載入主圖", key=f"btn_load_{key_prefix}_{item['code']}", use_container_width=True):
            st.session_state.selected_stock = item['code']
            st.session_state.goto_chart = True
            st.rerun()
    with c_btn2:
        if st.button("👁️ 追蹤鎖股", key=f"btn_watch_{key_prefix}_{item['code']}", use_container_width=True):
            st.toast(f"已將 {item['name']} ({item['code']}) 加入即時追蹤鎖股池！")
    st.divider()

MENU_OPTIONS = [
    "📊 個股技術分析 (轉折波主圖)",
    "🎯 全攻略選股池 (多/空策略)",
    "👁️ 鎖股池分階段管理",
    "🧑‍🏫 AI 課程助教問答"
]

if 'selected_stock' not in st.session_state:
    st.session_state.selected_stock = "2330"

# 關鍵跳轉邏輯：若收到載入主圖請求，於導航元件渲染前強制切換導航至「個股技術分析」
if st.session_state.get('goto_chart', False):
    st.session_state.nav_menu_radio = MENU_OPTIONS[0]
    st.session_state.goto_chart = False

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

# ----------------------------------------------------
# 功能分頁 1：個股技術分析 (轉折波主圖)
# ----------------------------------------------------
if menu == "📊 個股技術分析 (轉折波主圖)":
    query = st.session_state.selected_stock

    c_ctrl1, c_ctrl2, c_ctrl3, c_ctrl4 = st.columns([2, 1.8, 1.8, 1.8])
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

        st.markdown(f"""
        <div class="main-header">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <h2 style="margin: 0; display: inline-block;">{info['name']} ({info['code']})</h2>
                    <span class="tag-badge" style="background: #3B5998; margin-left: 8px;">{info['industry']}</span>
                    <span class="tag-badge" style="background: {trend['trend_color']};">{trend['trend_badge']}</span>
                    <div style="margin-top: 6px;">
                        <span style="font-size: 2.2rem; font-weight: bold; color: {price_color};">{info['close']}</span>
                        <span style="font-size: 1.15rem; font-weight: bold; color: {price_color}; margin-left: 8px;">{sign}{info['change']} ({sign}{info['change_pct']}%)</span>
                    </div>
                </div>
                <div style="text-align: right; font-size: 0.92rem; color: #BBB;">
                    <div>最高：<b style="color: #FF4D4F;">{info['high']}</b> | 最低：<b style="color: #52C41A;">{info['low']}</b></div>
                    <div>開盤：{info['open']} | 昨收：{info['prev_close']}</div>
                    <div>成交量：<b>{info['volume_str']}</b> | 日期：{info['latest_date']}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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

        fig.update_layout(
            height=680,
            margin=dict(l=20, r=80, t=15, b=15),
            template="plotly_dark",
            annotations=annotations,
            shapes=shapes,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        fig.update_xaxes(
            rangeslider_visible=False,
            range=init_x_range
        )

        fig.update_yaxes(
            range=auto_y_range,
            row=1, col=1
        )

        st.plotly_chart(fig, use_container_width=True)

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

# ----------------------------------------------------
# 功能分頁 2：全攻略選股池 (Screener)
# ----------------------------------------------------
elif menu == "🎯 全攻略選股池 (多/空策略)":
    st.header("🎯 全攻略條件選股雷達 (1:1 復刻 App 專業版)")
    st.caption("完整收錄朱家泓 8 大波段子策略、長抱存股、盤中強勢、一點鐘尾盤進場與助教實戰安全評級")

    # 頂部控制列
    col_t1, col_t2 = st.columns([1.2, 3])
    with col_t1:
        direction = st.radio("操作方向", ["🔴 做多 (Long)", "🟢 做空 (Short)"], horizontal=True)
        dir_val = "多" if "做多" in direction else "空"
    with col_t2:
        main_mode = st.radio(
            "選股大類",
            ["📈 波段策略 (起漲關鍵)", "💎 長抱標的 (長期多排)", "⚡ 盤中強勢 (量價齊揚)", "⏰ 一點鐘 (尾盤進場)"],
            horizontal=True
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
                "⚔️ 雙線黃金交叉 (5MA上穿20MA)",
                "📦 一字底 (平躺橫盤突破)",
                "📐 N字底 (第二隻腳打樁有守)",
                "🔄 圓弧底 (U型弧底翻揚)",
                "👑 頭高底高 (六字訣多頭確認)"
            ],
            horizontal=True
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
        p_filter = st.radio("價格位階篩選", ["全部", "低價 (<30)", "中價 (30-100)", "高價 (100-300)", "超高 (>300)"], horizontal=True)
        price_val = p_filter.split()[0]
    with col_p2:
        st.write("")
        st.write("")
        refresh_btn = st.button("🔄 刷新快取行情")

    with st.spinner(f"正在全市場 186 檔標的中精確篩選【{target_strategy}】..."):
        results = scan_stocks(strategy=target_strategy, direction=dir_val, price_filter=price_val, limit=50)

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
        horizontal=True
    )
    
    current_stage = "回檔等上漲" if "回檔等上漲" in stage_tab else ("等突破" if "等突破" in stage_tab else "高檔等回檔")

    with st.spinner(f"正在載入【{current_stage}】名冊..."):
        stage_stocks = scan_stocks(strategy="全部", watchlist_stage=current_stage, limit=40)

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
