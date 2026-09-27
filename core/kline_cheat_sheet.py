"""
core/kline_cheat_sheet.py
56 個常見 K 線型態視覺化速查寶典 UI 模組
提供直觀精美、色彩分明之純向量 SVG 迷你 K 棒圖解、六組對稱對句圖鑑與三根晨夜星對比
"""

import streamlit as st

def get_candlestick_svg(candle_type: str, width: int = 120, height: int = 110) -> str:
    """產生單一或多根迷你 K 棒之向量 SVG 圖形"""
    svg_header = f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg" style="background:#151824; border-radius:8px; border:1px solid #2B3145;">'
    svg_footer = '</svg>'
    elements = []

    # 1. 第五元素 1/2 價 (跌破)
    if candle_type == "half_break":
        # Day 1: 長紅 (Open=75, Close=25, High=15, Low=85) -> 1/2 price = 50
        elements.append('<line x1="38" y1="15" x2="38" y2="85" stroke="#FF4D4F" stroke-width="2"/>')
        elements.append('<rect x="28" y="25" width="20" height="50" fill="#FF4D4F" rx="2"/>')
        elements.append('<text x="38" y="100" fill="#FF7875" font-size="10" text-anchor="middle">前日長紅</text>')
        # 1/2 價虛線
        elements.append('<line x1="15" y1="50" x2="105" y2="50" stroke="#F59E0B" stroke-dasharray="3,3" stroke-width="1.5"/>')
        elements.append('<text x="70" y="46" fill="#F59E0B" font-size="9" font-weight="bold">1/2 價</text>')
        # Day 2: 跌破長黑 (Open=45, Close=68, High=40, Low=75)
        elements.append('<line x1="82" y1="40" x2="82" y2="75" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="72" y="45" width="20" height="23" fill="#2F9E44" rx="2"/>')
        elements.append('<text x="82" y="100" fill="#52C41A" font-size="10" text-anchor="middle">跌破1/2</text>')
        # 箭頭向下
        elements.append('<path d="M 82 78 L 82 88 M 78 84 L 82 88 L 86 84" stroke="#FF4D4F" stroke-width="2" fill="none"/>')

    # 2. 第五元素 1/2 價 (突破)
    elif candle_type == "half_rebound":
        # Day 1: 長黑 (Open=25, Close=75, High=15, Low=85) -> 1/2 price = 50
        elements.append('<line x1="38" y1="15" x2="38" y2="85" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="28" y="25" width="20" height="50" fill="#2F9E44" rx="2"/>')
        elements.append('<text x="38" y="100" fill="#52C41A" font-size="10" text-anchor="middle">前日長黑</text>')
        # 1/2 價虛線
        elements.append('<line x1="15" y1="50" x2="105" y2="50" stroke="#F59E0B" stroke-dasharray="3,3" stroke-width="1.5"/>')
        elements.append('<text x="70" y="46" fill="#F59E0B" font-size="9" font-weight="bold">1/2 價</text>')
        # Day 2: 突破長紅 (Open=55, Close=32, High=25, Low=60)
        elements.append('<line x1="82" y1="25" x2="82" y2="60" stroke="#FF4D4F" stroke-width="2"/>')
        elements.append('<rect x="72" y="32" width="20" height="23" fill="#FF4D4F" rx="2"/>')
        elements.append('<text x="82" y="100" fill="#FF7875" font-size="10" text-anchor="middle">突破1/2</text>')
        # 箭頭向上
        elements.append('<path d="M 82 22 L 82 12 M 78 16 L 82 12 L 86 16" stroke="#52C41A" stroke-width="2" fill="none"/>')

    # 3. 倒T字 / 天劍線 (墓碑)
    elif candle_type == "tombstone":
        elements.append('<line x1="60" y1="15" x2="60" y2="70" stroke="#E2E8F0" stroke-width="2.5"/>')
        elements.append('<rect x="44" y="68" width="32" height="5" fill="#E2E8F0" rx="1"/>')
        elements.append('<text x="60" y="96" fill="#AAA" font-size="11" text-anchor="middle">倒T / 天劍線</text>')

    # 4. 長T字 / 探底線
    elif candle_type == "dragonfly":
        elements.append('<line x1="60" y1="25" x2="60" y2="80" stroke="#E2E8F0" stroke-width="2.5"/>')
        elements.append('<rect x="44" y="22" width="32" height="5" fill="#E2E8F0" rx="1"/>')
        elements.append('<text x="60" y="96" fill="#AAA" font-size="11" text-anchor="middle">長T / 探底線</text>')

    # 5. 十字線 (十字星)
    elif candle_type == "doji":
        elements.append('<line x1="60" y1="15" x2="60" y2="80" stroke="#E2E8F0" stroke-width="2.5"/>')
        elements.append('<line x1="42" y1="48" x2="78" y2="48" stroke="#E2E8F0" stroke-width="3"/>')
        elements.append('<text x="60" y="96" fill="#AAA" font-size="11" text-anchor="middle">十字變盤線</text>')

    # 6. 紡錘線
    elif candle_type == "spinning_top":
        elements.append('<line x1="60" y1="15" x2="60" y2="80" stroke="#E2E8F0" stroke-width="2"/>')
        elements.append('<rect x="48" y="42" width="24" height="15" fill="#E2E8F0" rx="2"/>')
        elements.append('<text x="60" y="96" fill="#AAA" font-size="11" text-anchor="middle">紡錘平衡線</text>')

    # 7. 反鎚線
    elif candle_type == "inverted_hammer":
        elements.append('<line x1="60" y1="15" x2="60" y2="60" stroke="#E2E8F0" stroke-width="2"/>')
        elements.append('<rect x="48" y="60" width="24" height="15" fill="#E2E8F0" rx="2"/>')
        elements.append('<line x1="60" y1="75" x2="60" y2="80" stroke="#E2E8F0" stroke-width="1.5"/>')
        elements.append('<text x="60" y="96" fill="#AAA" font-size="11" text-anchor="middle">反鎚線</text>')

    # 8. 鎚子線 / 吊人線
    elif candle_type == "hammer":
        elements.append('<line x1="60" y1="20" x2="60" y2="24" stroke="#E2E8F0" stroke-width="1.5"/>')
        elements.append('<rect x="48" y="24" width="24" height="15" fill="#E2E8F0" rx="2"/>')
        elements.append('<line x1="60" y1="39" x2="60" y2="82" stroke="#E2E8F0" stroke-width="2"/>')
        elements.append('<text x="60" y="96" fill="#AAA" font-size="11" text-anchor="middle">鎚子 / 吊人線</text>')

    # 9. 烏雲罩頂 (Dark Cloud Cover)
    elif candle_type == "dark_cloud":
        # Day 1: 長紅
        elements.append('<line x1="38" y1="20" x2="38" y2="80" stroke="#FF4D4F" stroke-width="2"/>')
        elements.append('<rect x="28" y="30" width="20" height="42" fill="#FF4D4F" rx="2"/>')
        # Day 2: 高開低走貫入 1/2 以下
        elements.append('<line x1="82" y1="15" x2="82" y2="75" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="72" y="22" width="20" height="42" fill="#2F9E44" rx="2"/>')
        # 1/2 標示
        elements.append('<line x1="20" y1="51" x2="100" y2="51" stroke="#F59E0B" stroke-dasharray="2,2" stroke-width="1"/>')
        elements.append('<text x="60" y="98" fill="#FF7875" font-size="10" text-anchor="middle">烏雲罩頂 (深入1/2)</text>')

    # 10. 旭日東昇 (Piercing Line)
    elif candle_type == "piercing":
        # Day 1: 長黑
        elements.append('<line x1="38" y1="20" x2="38" y2="80" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="28" y="28" width="20" height="42" fill="#2F9E44" rx="2"/>')
        # Day 2: 低開高走穿透 1/2 以上
        elements.append('<line x1="82" y1="25" x2="82" y2="85" stroke="#FF4D4F" stroke-width="2"/>')
        elements.append('<rect x="72" y="36" width="20" height="42" fill="#FF4D4F" rx="2"/>')
        # 1/2 標示
        elements.append('<line x1="20" y1="49" x2="100" y2="49" stroke="#F59E0B" stroke-dasharray="2,2" stroke-width="1"/>')
        elements.append('<text x="60" y="98" fill="#52C41A" font-size="10" text-anchor="middle">旭日東昇 (突破1/2)</text>')

    # 11. 長黑吞噬 (Bearish Engulfing)
    elif candle_type == "bearish_engulf":
        # Day 1: 小紅
        elements.append('<line x1="38" y1="35" x2="38" y2="70" stroke="#FF4D4F" stroke-width="1.8"/>')
        elements.append('<rect x="29" y="42" width="18" height="20" fill="#FF4D4F" rx="1.5"/>')
        # Day 2: 巨大長黑完全包覆
        elements.append('<line x1="82" y1="18" x2="82" y2="84" stroke="#2F9E44" stroke-width="2.5"/>')
        elements.append('<rect x="70" y="26" width="24" height="52" fill="#2F9E44" rx="2"/>')
        elements.append('<text x="60" y="98" fill="#FF7875" font-size="10" text-anchor="middle">長黑吞噬 (主力倒貨)</text>')

    # 12. 長紅吞噬 (Bullish Engulfing)
    elif candle_type == "bullish_engulf":
        # Day 1: 小黑
        elements.append('<line x1="38" y1="35" x2="38" y2="70" stroke="#2F9E44" stroke-width="1.8"/>')
        elements.append('<rect x="29" y="42" width="18" height="20" fill="#2F9E44" rx="1.5"/>')
        # Day 2: 巨大長紅完全包覆
        elements.append('<line x1="82" y1="18" x2="82" y2="84" stroke="#FF4D4F" stroke-width="2.5"/>')
        elements.append('<rect x="70" y="26" width="24" height="52" fill="#FF4D4F" rx="2"/>')
        elements.append('<text x="60" y="98" fill="#52C41A" font-size="10" text-anchor="middle">長紅吞噬 (主力進貨)</text>')

    # 13. 母子懷抱 (孕線)
    elif candle_type == "harami":
        # Day 1: 巨大長棒 (左)
        elements.append('<line x1="38" y1="18" x2="38" y2="84" stroke="#FF4D4F" stroke-width="2.5"/>')
        elements.append('<rect x="26" y="26" width="24" height="52" fill="#FF4D4F" rx="2"/>')
        # Day 2: 被完全包在肚子裡的小棒 (右)
        elements.append('<line x1="82" y1="40" x2="82" y2="68" stroke="#E2E8F0" stroke-width="1.8"/>')
        elements.append('<rect x="73" y="46" width="18" height="16" fill="#2F9E44" rx="1.5"/>')
        elements.append('<text x="60" y="98" fill="#F59E0B" font-size="10" text-anchor="middle">母子懷抱 (孕線變盤)</text>')

    # 14. 一日封口 (Equal Close)
    elif candle_type == "equal_close":
        # Day 1: 長紅
        elements.append('<line x1="38" y1="25" x2="38" y2="75" stroke="#FF4D4F" stroke-width="2"/>')
        elements.append('<rect x="28" y="32" width="20" height="38" fill="#FF4D4F" rx="2"/>')
        # Day 2: 長黑，收盤完全等平於 Day 1 開盤
        elements.append('<line x1="82" y1="20" x2="82" y2="78" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="72" y="26" width="20" height="44" fill="#2F9E44" rx="2"/>')
        # 等平水平線
        elements.append('<line x1="20" y1="70" x2="100" y2="70" stroke="#38BDF8" stroke-dasharray="2,2" stroke-width="1.5"/>')
        elements.append('<text x="60" y="98" fill="#38BDF8" font-size="10" text-anchor="middle">一日封口 (等平截斷)</text>')

    # 15. 孤島晨星 (Island Morning Star)
    elif candle_type == "island_morning":
        # K1: 長黑 (左)
        elements.append('<line x1="25" y1="18" x2="25" y2="62" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="17" y="24" width="16" height="32" fill="#2F9E44" rx="1.5"/>')
        # 缺口 1
        elements.append('<text x="40" y="68" fill="#F59E0B" font-size="8">缺口</text>')
        # K2: 孤島星線 (中下)
        elements.append('<line x1="60" y1="72" x2="60" y2="88" stroke="#E2E8F0" stroke-width="1.8"/>')
        elements.append('<line x1="52" y1="80" x2="68" y2="80" stroke="#E2E8F0" stroke-width="2.5"/>')
        # 缺口 2
        elements.append('<text x="73" y="68" fill="#F59E0B" font-size="8">缺口</text>')
        # K3: 長紅 (右)
        elements.append('<line x1="95" y1="22" x2="95" y2="66" stroke="#FF4D4F" stroke-width="2"/>')
        elements.append('<rect x="87" y="28" width="16" height="32" fill="#FF4D4F" rx="1.5"/>')
        elements.append('<text x="60" y="102" fill="#52C41A" font-size="10" font-weight="bold" text-anchor="middle">🏝️ 孤島晨星 (最強島轉)</text>')

    # 16. 孤島夜星 (Island Evening Star)
    elif candle_type == "island_evening":
        # K1: 長紅 (左)
        elements.append('<line x1="25" y1="38" x2="25" y2="82" stroke="#FF4D4F" stroke-width="2"/>')
        elements.append('<rect x="17" y="44" width="16" height="32" fill="#FF4D4F" rx="1.5"/>')
        # 缺口 1
        elements.append('<text x="40" y="38" fill="#F59E0B" font-size="8">缺口</text>')
        # K2: 孤島星線 (中上)
        elements.append('<line x1="60" y1="12" x2="60" y2="28" stroke="#E2E8F0" stroke-width="1.8"/>')
        elements.append('<line x1="52" y1="20" x2="68" y2="20" stroke="#E2E8F0" stroke-width="2.5"/>')
        # 缺口 2
        elements.append('<text x="73" y="38" fill="#F59E0B" font-size="8">缺口</text>')
        # K3: 長黑 (右)
        elements.append('<line x1="95" y1="34" x2="95" y2="78" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="87" y="40" width="16" height="32" fill="#2F9E44" rx="1.5"/>')
        elements.append('<text x="60" y="102" fill="#FF7875" font-size="10" font-weight="bold" text-anchor="middle">🏝️ 孤島夜星 (最強島轉)</text>')

    # 17. CH9-3 現象一：跌破高檔連續兩日大量低點
    elif candle_type == "reversal_2day_vol":
        # Day 1: 高檔紅K
        elements.append('<line x1="30" y1="18" x2="30" y2="52" stroke="#FF4D4F" stroke-width="1.8"/>')
        elements.append('<rect x="23" y="24" width="14" height="22" fill="#FF4D4F" rx="1.5"/>')
        # Day 2: 高檔小K (低點較高)
        elements.append('<line x1="56" y1="12" x2="56" y2="48" stroke="#FF4D4F" stroke-width="1.8"/>')
        elements.append('<rect x="49" y="18" width="14" height="24" fill="#FF4D4F" rx="1.5"/>')
        # 大量低點水平虛線 (min low = 48)
        elements.append('<line x1="16" y1="52" x2="104" y2="52" stroke="#F59E0B" stroke-dasharray="2,2" stroke-width="1.5"/>')
        elements.append('<text x="75" y="49" fill="#F59E0B" font-size="8">大量低點</text>')
        # Day 3: 長黑摜破 (Low=72, Close=68 < 52)
        elements.append('<line x1="86" y1="32" x2="86" y2="74" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="78" y="38" width="16" height="30" fill="#2F9E44" rx="1.5"/>')
        # 下方成交量量柱 (連兩日爆大量)
        elements.append('<rect x="25" y="80" width="10" height="18" fill="#FF4D4F" rx="1"/>')
        elements.append('<rect x="51" y="76" width="10" height="22" fill="#FF4D4F" rx="1"/>')
        elements.append('<rect x="81" y="78" width="10" height="20" fill="#2F9E44" rx="1"/>')
        elements.append('<text x="60" y="104" fill="#FF7875" font-size="9" font-weight="bold" text-anchor="middle">跌破兩日大量低點</text>')

    # 18. CH9-3 現象二：高檔爆量長黑 / 長黑吞噬
    elif candle_type == "reversal_heavy_black":
        # Day 1: 紅K
        elements.append('<line x1="40" y1="28" x2="40" y2="62" stroke="#FF4D4F" stroke-width="1.8"/>')
        elements.append('<rect x="33" y="34" width="14" height="22" fill="#FF4D4F" rx="1.5"/>')
        # Day 2: 爆巨量長黑吞噬
        elements.append('<line x1="78" y1="14" x2="78" y2="74" stroke="#2F9E44" stroke-width="2.5"/>')
        elements.append('<rect x="68" y="22" width="20" height="46" fill="#2F9E44" rx="2"/>')
        # 下方巨量柱
        elements.append('<rect x="35" y="84" width="10" height="14" fill="#FF4D4F" rx="1"/>')
        elements.append('<rect x="72" y="72" width="14" height="26" fill="#2F9E44" rx="1"/>')
        elements.append('<text x="60" y="104" fill="#FF7875" font-size="9" font-weight="bold" text-anchor="middle">爆量長黑 (吞噬全出)</text>')

    # 19. CH9-3 現象三：高檔爆量長上影線 (避雷針)
    elif candle_type == "reversal_shooting_star":
        # Day 1: 紅K
        elements.append('<line x1="40" y1="36" x2="40" y2="68" stroke="#FF4D4F" stroke-width="1.8"/>')
        elements.append('<rect x="33" y="42" width="14" height="20" fill="#FF4D4F" rx="1.5"/>')
        # Day 2: 避雷針 (超長上影線)
        elements.append('<line x1="80" y1="12" x2="80" y2="70" stroke="#E2E8F0" stroke-width="2"/>')
        elements.append('<rect x="72" y="52" width="16" height="14" fill="#2F9E44" rx="1.5"/>')
        # 下方爆大量柱
        elements.append('<rect x="35" y="84" width="10" height="14" fill="#FF4D4F" rx="1"/>')
        elements.append('<rect x="74" y="72" width="12" height="26" fill="#E2E8F0" rx="1"/>')
        elements.append('<text x="60" y="104" fill="#FF7875" font-size="9" font-weight="bold" text-anchor="middle">避雷針 (獲利>15%先出1/2)</text>')

    # 20. CH9-3 現象四：高檔爆量頭頭低盤整
    elif candle_type == "reversal_lower_highs":
        # 波峰 1 (最高)
        elements.append('<circle cx="32" cy="22" r="3" fill="#FF4D4F"/>')
        elements.append('<text x="32" y="18" fill="#FF7875" font-size="8" text-anchor="middle">頭1</text>')
        # 波谷
        elements.append('<circle cx="50" cy="52" r="2.5" fill="#F59E0B"/>')
        # 波峰 2 (頭頭低)
        elements.append('<circle cx="68" cy="30" r="3" fill="#FF7875"/>')
        elements.append('<text x="68" y="26" fill="#FF7875" font-size="8" text-anchor="middle">頭2</text>')
        # 折線
        elements.append('<polyline points="20,40 32,22 50,52 68,30 88,68" fill="none" stroke="#E2E8F0" stroke-width="1.8"/>')
        # 盤整頸線
        elements.append('<line x1="25" y1="52" x2="95" y2="52" stroke="#F59E0B" stroke-dasharray="2,2" stroke-width="1.2"/>')
        # 破頸線長黑
        elements.append('<line x1="88" y1="46" x2="88" y2="76" stroke="#2F9E44" stroke-width="2"/>')
        elements.append('<rect x="82" y="52" width="12" height="20" fill="#2F9E44" rx="1"/>')
        elements.append('<text x="60" y="104" fill="#FF7875" font-size="9" font-weight="bold" text-anchor="middle">頭頭低 (破箱底空頭確認)</text>')

    return svg_header + "".join(elements) + svg_footer


def render_kline_visual_cheat_sheet():
    """在 Streamlit 介面中渲染全視覺化的 56 個常見 K 線型態寶典"""
    st.markdown("""
    <div style="background:linear-gradient(135deg, #1A1F2C 0%, #11141F 100%); border:1px solid #30384F; border-radius:12px; padding:16px 20px; margin-bottom:16px;">
        <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px;">
            <div>
                <span style="font-size:1.25rem; font-weight:bold; color:#FFFFFF;">📘 56個常見 K 線型態全圖解速查寶典</span>
                <span style="background:#2563EB; color:#FFF; font-size:0.75rem; padding:2px 8px; border-radius:12px; margin-left:8px; font-weight:bold;">視覺圖解實戰版</span>
            </div>
            <div style="color:#94A3B8; font-size:0.85rem;">
                核心心法：看 K 線三件事 · 第五元素 1/2 價 · 高檔四大反轉 · 五大實戰解套 · 做多七不買禁忌 · 六年千萬計畫
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 次級分頁直覺切換
    v_tab1, v_tab2, v_tab3, v_tab4, v_tab5, v_tab6, v_tab7, v_tab8 = st.tabs([
        "🧭 看K線三件事",
        "🕯️ 第五元素 1/2 價",
        "⚖️ 變盤線高低檔對照",
        "⚔️ 兩根K棒六組對句",
        "🌟 三根晨星與夜星",
        "🛑 高檔四大反轉停利圖鑑",
        "🆘 五大實戰解套與贏家思維",
        "🛡️ 做多七不買與六年千萬"
    ])

    # -------------------------------------------------------------
    # TAB 1: 看 K 線三件事 (核心心法視覺卡)
    # -------------------------------------------------------------
    with v_tab1:
        st.caption("💡 操盤大師心法：K 線是末端訊號，絕不能單看一根紅黑就衝動下單！務必依照以下三步驟依序檢視：")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""
            <div style="background:#171C28; border:1px solid #2B344B; border-top:4px solid #3B82F6; border-radius:10px; padding:14px; min-height:220px;">
                <div style="font-size:1.05rem; font-weight:bold; color:#60A5FA; margin-bottom:6px;">① 趨勢（最重要）</div>
                <div style="font-size:0.85rem; color:#E2E8F0; line-height:1.6;">
                    • <b>多頭趨勢</b>：頭頭高、底底高。回檔拉回出紅K是<b>「起漲進場訊號」</b>！<br>
                    • <b>空頭趨勢</b>：頭頭低、底底低。破底時出現紅K往往只是<b>「跌深反彈」</b>，切勿盲目抄底！<br>
                    • <b>盤整走勢</b>：上下箱型洗盤，突破上緣才買、跌破下緣退場。
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown("""
            <div style="background:#171C28; border:1px solid #2B344B; border-top:4px solid #F59E0B; border-radius:10px; padding:14px; min-height:220px;">
                <div style="font-size:1.05rem; font-weight:bold; color:#FBBF24; margin-bottom:6px;">② 位置（定生死）</div>
                <div style="font-size:0.85rem; color:#E2E8F0; line-height:1.6;">
                    • <b>低檔位置</b>：剛完成打底或回測均線支撐，買進風險小、獲利波段大。<br>
                    • <b>高檔位置</b>：<b>連漲 3~4 天以上即為短線高檔！</b>此時再出長紅往往是主力最後誘多，追高極易現買現套！<br>
                    • <b>轉折確認</b>：位置決定形態意義，同樣一根變盤線，在頂部是凶兆、在底部是吉兆！
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown("""
            <div style="background:#171C28; border:1px solid #2B344B; border-top:4px solid #10B981; border-radius:10px; padding:14px; min-height:220px;">
                <div style="font-size:1.05rem; font-weight:bold; color:#34D399; margin-bottom:6px;">③ 成交量（印證真偽）</div>
                <div style="font-size:0.85rem; color:#E2E8F0; line-height:1.6;">
                    • <b>量增價漲</b>：主力大戶實單敲進，漲勢紮實具延續力。<br>
                    • <b>量縮價跌</b>：正常良性洗盤，主力並未倒貨，籌碼安定。<br>
                    • <b>高檔爆量長黑</b>：波段大漲後爆天量收黑，主力大量倒貨之確定性賣出訊號！
                </div>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 2: 第五元素 1/2 價量化圖解
    # -------------------------------------------------------------
    with v_tab2:
        st.caption("💡 《K線型態秘笈》核心量化指標：K 棒除了開高低收四元素外，最重要的就是 **「第五元素 1/2 成本價 = (最高價 + 最低價) / 2」**！")
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #EF4444; border-radius:10px; padding:14px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('half_break', 130, 115)}</div>
                    <div>
                        <div style="color:#FF7875; font-weight:bold; font-size:1.05rem; margin-bottom:4px;">⚠️ 跌破前日紅棒 1/2 價</div>
                        <div style="color:#CBD5E1; font-size:0.84rem; line-height:1.5;">
                            • <b>形態意義</b>：大紅K次日收盤若<b>跌破昨日紅K的 1/2 成本價</b>。<br>
                            • <b>主力心態</b>：昨日追價買盤全部陷入虧損，多方動能嚴重轉弱。<br>
                            • <b>操作對策</b>：強勢格局瓦解，提防短線拉回洗盤或波段做頭，持股應停利或減碼防守！
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_h2:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #22C55E; border-radius:10px; padding:14px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('half_rebound', 130, 115)}</div>
                    <div>
                        <div style="color:#52C41A; font-weight:bold; font-size:1.05rem; margin-bottom:4px;">🟢 站上突破前日黑棒 1/2 價</div>
                        <div style="color:#CBD5E1; font-size:0.84rem; line-height:1.5;">
                            • <b>形態意義</b>：大黑K次日收盤若<b>站上突破昨日黑K的 1/2 成本價</b>。<br>
                            • <b>主力心態</b>：空方摜壓全力遭到多方化解，下檔買盤強勁承接。<br>
                            • <b>操作對策</b>：空方力竭竭盡，極易展開跌深強彈或底部起漲，可伺機逢低分批布局！
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("""
        <div style="margin-top:12px; background:#1E2433; padding:10px 14px; border-radius:8px; font-size:0.85rem; color:#94A3B8;">
            📏 <b>K 棒長度量化標準</b>：<b>長紅/長黑</b>（漲跌幅 ≥ 6.5%，主力絕對表態）；<b>中紅/中黑</b>（3.5% ~ 6.5%，波段推進）；<b>小紅/小黑</b>（< 3.5%，常態整理）。連續 3 根以上 K 棒高低重疊即為<b>「K 線盤整」</b>。
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 3: 變盤線高低檔對照圖鑑
    # -------------------------------------------------------------
    with v_tab3:
        st.markdown("""
        <div style="background:#3C1F24; border-left:4px solid #FF4D4F; padding:8px 12px; border-radius:6px; margin-bottom:12px; font-size:0.88rem; color:#FFCCC7;">
            ⚖️ <b>操盤黃金鐵律</b>：<b>變盤線在「高檔」凶多吉少（空方變盤見頂）；在「低檔」逢凶化吉（多方起死回生）！</b>
        </div>
        """, unsafe_allow_html=True)

        r1_c1, r1_c2, r1_c3 = st.columns(3)
        with r1_c1:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center;">
                {get_candlestick_svg('tombstone', 120, 105)}
                <div style="text-align:left; margin-top:8px; font-size:0.8rem; line-height:1.5;">
                    <span style="color:#FF7875; font-weight:bold;">高檔（墓碑線/天劍）：</span>主力拉高倒貨，追高全套牢，轉折向下。<br>
                    <span style="color:#52C41A; font-weight:bold;">低檔（倒T字）：</span>主力向上試探賣壓，浮額洗淨即將起漲。
                </div>
            </div>
            """, unsafe_allow_html=True)
        with r1_c2:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center;">
                {get_candlestick_svg('dragonfly', 120, 105)}
                <div style="text-align:left; margin-top:8px; font-size:0.8rem; line-height:1.5;">
                    <span style="color:#FF7875; font-weight:bold;">高檔（長T線）：</span>主力尾盤刻意作價拉抬誘多，翌日開低轉弱。<br>
                    <span style="color:#52C41A; font-weight:bold;">低檔（探底線）：</span>低檔買盤強勁承接，黃金探底反轉吉兆。
                </div>
            </div>
            """, unsafe_allow_html=True)
        with r1_c3:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center;">
                {get_candlestick_svg('doji', 120, 105)}
                <div style="text-align:left; margin-top:8px; font-size:0.8rem; line-height:1.5;">
                    <span style="color:#FF7875; font-weight:bold;">高檔十字星：</span>多空交戰平手，推升動能竭盡，轉折拉回。<br>
                    <span style="color:#52C41A; font-weight:bold;">低檔十字星：</span>空方摜壓無力，多空即將轉折向上迎黎明。
                </div>
            </div>
            """, unsafe_allow_html=True)

        r2_c1, r2_c2, r2_c3 = st.columns(3)
        with r2_c1:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center; margin-top:10px;">
                {get_candlestick_svg('spinning_top', 120, 105)}
                <div style="text-align:left; margin-top:8px; font-size:0.8rem; line-height:1.5;">
                    <span style="color:#FF7875; font-weight:bold;">高檔紡錘線：</span>追價意願停滯，短線防變盤下彎。<br>
                    <span style="color:#52C41A; font-weight:bold;">低檔紡錘線：</span>空方賣壓逐步鈍化，多空平衡蓄勢向上。
                </div>
            </div>
            """, unsafe_allow_html=True)
        with r2_c2:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center; margin-top:10px;">
                {get_candlestick_svg('inverted_hammer', 120, 105)}
                <div style="text-align:left; margin-top:8px; font-size:0.8rem; line-height:1.5;">
                    <span style="color:#FF7875; font-weight:bold;">高檔反鎚線：</span>盤中衝高遭強大解套賣壓擊沉，凶兆。<br>
                    <span style="color:#52C41A; font-weight:bold;">低檔反鎚線：</span>低檔有特定買盤進場試單點火，轉折在即。
                </div>
            </div>
            """, unsafe_allow_html=True)
        with r2_c3:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center; margin-top:10px;">
                {get_candlestick_svg('hammer', 120, 105)}
                <div style="text-align:left; margin-top:8px; font-size:0.8rem; line-height:1.5;">
                    <span style="color:#FF7875; font-weight:bold;">高檔吊人線：</span>主力高檔作假支撐誘多，次日開低必殺！<br>
                    <span style="color:#52C41A; font-weight:bold;">低檔鎚子線：</span>下影線洗淨浮額，買盤強勢收腳，逢凶化吉！
                </div>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 4: 兩根 K 棒六組對稱對句
    # -------------------------------------------------------------
    with v_tab4:
        st.caption("💡 兩根 K 棒對稱口訣對句：次日開低確認頂部停利賣出；次日開高確認底部反轉買進！")
        p1_c1, p1_c2, p1_c3 = st.columns(3)
        with p1_c1:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center;">
                {get_candlestick_svg('dark_cloud', 120, 105)}
                <div style="color:#FF7875; font-weight:bold; font-size:0.95rem; margin-top:6px;">烏雲罩頂 (深入1/2)</div>
                <div style="font-size:0.8rem; color:#CBD5E1; text-align:left; margin-top:4px;">高開低走黑棒，實體深入前日長紅 1/2 以下，高檔轉折向下。</div>
            </div>
            """, unsafe_allow_html=True)
        with p1_c2:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center;">
                {get_candlestick_svg('piercing', 120, 105)}
                <div style="color:#52C41A; font-weight:bold; font-size:0.95rem; margin-top:6px;">旭日東昇 (穿透1/2)</div>
                <div style="font-size:0.8rem; color:#CBD5E1; text-align:left; margin-top:4px;">低開高走紅棒，實體反噬前日長黑 1/2 以上，低檔突破起漲。</div>
            </div>
            """, unsafe_allow_html=True)
        with p1_c3:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center;">
                {get_candlestick_svg('equal_close', 120, 105)}
                <div style="color:#38BDF8; font-weight:bold; font-size:0.95rem; margin-top:6px;">長黑/紅遭遇 一日封口</div>
                <div style="font-size:0.8rem; color:#CBD5E1; text-align:left; margin-top:4px;">次日收盤與前日開盤完全等平封口，漲勢或跌勢瞬間遭到截斷。</div>
            </div>
            """, unsafe_allow_html=True)

        p2_c1, p2_c2, p2_c3 = st.columns(3)
        with p2_c1:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center; margin-top:10px;">
                {get_candlestick_svg('bearish_engulf', 120, 105)}
                <div style="color:#FF7875; font-weight:bold; font-size:0.95rem; margin-top:6px;">長黑吞噬 主力出貨</div>
                <div style="font-size:0.8rem; color:#CBD5E1; text-align:left; margin-top:4px;">次日長黑完全吞噬前日紅棒實體，空方全面掌控盤勢。</div>
            </div>
            """, unsafe_allow_html=True)
        with p2_c2:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center; margin-top:10px;">
                {get_candlestick_svg('bullish_engulf', 120, 105)}
                <div style="color:#52C41A; font-weight:bold; font-size:0.95rem; margin-top:6px;">長紅吞噬 主力進貨</div>
                <div style="font-size:0.8rem; color:#CBD5E1; text-align:left; margin-top:4px;">次日長紅完全吞噬前日黑棒實體，多方強勢反攻主導。</div>
            </div>
            """, unsafe_allow_html=True)
        with p2_c3:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #2B344B; border-radius:10px; padding:12px; text-align:center; margin-top:10px;">
                {get_candlestick_svg('harami', 120, 105)}
                <div style="color:#F59E0B; font-weight:bold; font-size:0.95rem; margin-top:6px;">母子懷抱 (孕線)</div>
                <div style="font-size:0.8rem; color:#CBD5E1; text-align:left; margin-top:4px;">長棒懷中小K棒，動能驟降。高檔不懷好意(跌)；低檔光明在望(漲)。</div>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 5: 三根晨星與夜星 (島型反轉)
    # -------------------------------------------------------------
    with v_tab5:
        st.caption("💡 三根組合核心心法：中間星線越多，多空沉澱換手越久，變盤動能越大！兩側皆有跳空缺口者為爆發力最強之「孤島反轉」！")
        s_c1, s_c2 = st.columns(2)
        with s_c1:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #22C55E; border-radius:10px; padding:14px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('island_morning', 130, 115)}</div>
                    <div>
                        <div style="color:#52C41A; font-weight:bold; font-size:1.05rem; margin-bottom:4px;">🚀 孤島晨星（底部最強反轉）</div>
                        <div style="color:#CBD5E1; font-size:0.84rem; line-height:1.5;">
                            • <b>形態結構</b>：長黑 + 左右兩側雙跳空缺口 + 底部小星線落單 + 向上突破長紅。<br>
                            • <b>爆發力</b>：為島型反轉中最極致的買進訊號，底部所有空單瞬間全被軋空套牢！<br>
                            • <b>系列衍伸</b>：標準晨星、母子晨星、雙星晨星、雙肩晨星、群星晨星。
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with s_c2:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #EF4444; border-radius:10px; padding:14px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('island_evening', 130, 115)}</div>
                    <div>
                        <div style="color:#FF7875; font-weight:bold; font-size:1.05rem; margin-bottom:4px;">🛑 孤島夜星（頂部最強見頂）</div>
                        <div style="color:#CBD5E1; font-size:0.84rem; line-height:1.5;">
                            • <b>形態結構</b>：長紅 + 左右兩側雙跳空缺口 + 頂部小星線孤立 + 向下摜破長黑。<br>
                            • <b>破壞力</b>：主力高檔斷頭出脫籌碼，高點追價買盤全部淪為孤島套牢冤魂！<br>
                            • <b>系列衍伸</b>：標準夜星、母子夜星、雙星夜星、雙鴉夜星、群星夜星。
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 6: 高檔四大反轉停利圖鑑 (CH9 主力出貨與分批停利 SOP)
    # -------------------------------------------------------------
    with v_tab6:
        st.caption("💡 實戰停利鐵律：「會買股票是徒弟，會賣股票的才是師父」！股價大漲至高檔，出現以下四大反轉訊號，務必果斷停利獲利入袋！")
        tp_c1, tp_c2 = st.columns(2)
        with tp_c1:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #EF4444; border-radius:10px; padding:14px; margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('reversal_2day_vol', 130, 115)}</div>
                    <div>
                        <div style="color:#FF7875; font-weight:bold; font-size:1.02rem; margin-bottom:4px;">🚨 現象一：跌破連續兩日大量低點</div>
                        <div style="color:#CBD5E1; font-size:0.83rem; line-height:1.5;">
                            • <b>主力出貨特徵</b>：高檔連續 2 日爆巨量換手，第三日收盤摜破兩天最低點。<br>
                            • <b>一日反轉確立</b>：買盤瞬間潰散，主力大戶出貨完畢！<br>
                            • <b>停利動作</b>：<b>多單果斷全數停利退場！</b>絕不心存僥倖凹單。
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #F59E0B; border-radius:10px; padding:14px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('reversal_shooting_star', 130, 115)}</div>
                    <div>
                        <div style="color:#FBBF24; font-weight:bold; font-size:1.02rem; margin-bottom:4px;">⚠️ 現象三：爆量長上影線 (避雷針)</div>
                        <div style="color:#CBD5E1; font-size:0.83rem; line-height:1.5;">
                            • <b>主力出貨特徵</b>：高檔創高後遭空方重擊壓回，爆巨量留長上影線。<br>
                            • <b>15% 分批停利</b>：若未破前低但<b>獲利已逾 15%，先停利 1/2！</b><br>
                            • <b>次日破低確認</b>：次日若開低走低或破底，<b>剩餘 1/2 全數清倉！</b>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with tp_c2:
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #EF4444; border-radius:10px; padding:14px; margin-bottom:12px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('reversal_heavy_black', 130, 115)}</div>
                    <div>
                        <div style="color:#FF7875; font-weight:bold; font-size:1.02rem; margin-bottom:4px;">🛑 現象二：爆量長黑K / 長黑吞噬</div>
                        <div style="color:#CBD5E1; font-size:0.83rem; line-height:1.5;">
                            • <b>主力出貨特徵</b>：高檔爆大量長黑或長黑吞噬前日紅K實體。<br>
                            • <b>破前低</b>：形成長黑吞噬或貫穿，<b>多單果斷全數停利賣出！</b><br>
                            • <b>未破前低</b>：若波段<b>獲利已逾 15%，先停利 1/2！</b>次日續跌破大量低點則全出。
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            st.markdown(f"""
            <div style="background:#171C28; border:1px solid #A855F7; border-radius:10px; padding:14px;">
                <div style="display:flex; align-items:center; gap:16px;">
                    <div>{get_candlestick_svg('reversal_lower_highs', 130, 115)}</div>
                    <div>
                        <div style="color:#C084FC; font-weight:bold; font-size:1.02rem; margin-bottom:4px;">📉 現象四：高檔爆量頭頭低盤整</div>
                        <div style="color:#CBD5E1; font-size:0.83rem; line-height:1.5;">
                            • <b>主力出貨特徵</b>：高檔爆量後無法再過前高，形成「頭頭低」震盪。<br>
                            • <b>短線停利</b>：出現頭頭低盤整，<b>短線多單立即停利出場！</b><br>
                            • <b>長線停利</b>：後續跌破盤整區下緣低點（空頭確認），<b>長線多單全數停利清倉！</b>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 7: 五大實戰解套與散戶贏家思維 (CH10 實戰精華)
    # -------------------------------------------------------------
    with v_tab7:
        st.caption("💡 實戰解套鐵律：賠損超過 10% 仍持有稱為被套牢！絕不能有「不賣就不賠」的鴕鳥心態，依據跌幅位階果斷執行五大解套 SOP！")

        # 5大解套 SOP 卡片
        st.markdown("""
        <div style="background:#171C28; border:1px solid #30384F; border-radius:10px; padding:16px; margin-bottom:14px;">
            <div style="color:#FF7875; font-weight:bold; font-size:1.08rem; margin-bottom:8px;">🆘 股票套牢五大實戰解套 SOP 流程指引</div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:12px;">
                <div style="background:#1E2433; border-left:4px solid #52C41A; padding:10px; border-radius:6px;">
                    <div style="color:#52C41A; font-weight:bold; font-size:0.9rem;">SOP 1 · 虧損 &lt; 10% (進場防守期)</div>
                    <div style="color:#CBD5E1; font-size:0.82rem; margin-top:4px; line-height:1.5;">
                        以買進 K 線低點 (或 5MA) 為停損點，收盤跌破立刻執行停損認賠！每日跌逾 5% 列為警示股，絕不拖成大套牢。
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #F59E0B; padding:10px; border-radius:6px;">
                    <div style="color:#F59E0B; font-weight:bold; font-size:0.9rem;">SOP 2 · 套牢 10%~20% (反彈逃命期)</div>
                    <div style="color:#CBD5E1; font-size:0.82rem; margin-top:4px; line-height:1.5;">
                        股票反彈遇下彎均線 (20MA/5MA) 或前高壓力不漲時，斷然認賠出場！<b>嚴禁向下攤平加碼</b>弱勢空頭股！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#EF4444; font-weight:bold; font-size:0.9rem;">SOP 3 · 套牢 &gt; 20% (反手做空解套)</div>
                    <div style="color:#CBD5E1; font-size:0.82rem; margin-top:4px; line-height:1.5;">
                        空頭趨勢不變 (20MA下彎)：反彈賣出後<b>反手放空賺價差解套</b>！直到走勢出現「底底高」才停止放空回補！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #13C2C2; padding:10px; border-radius:6px;">
                    <div style="color:#13C2C2; font-weight:bold; font-size:0.9rem;">SOP 4 · 套牢 &gt; 20% (換股強勢多頭)</div>
                    <div style="color:#CBD5E1; font-size:0.82rem; margin-top:4px; line-height:1.5;">
                        反彈賣出後換其它多頭強勢股（頭高底高、站穩月線）操作，利用主流飆股主升段利潤迅速彌補虧損解套！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #A855F7; padding:10px; border-radius:6px;">
                    <div style="color:#C084FC; font-weight:bold; font-size:0.9rem;">SOP 5 · 套牢 &gt; 20% (大量打底完成)</div>
                    <div style="color:#CBD5E1; font-size:0.82rem; margin-top:4px; line-height:1.5;">
                        低檔已出現爆大量止跌，切勿急躁盲目攤平！耐心等待打底完成、多頭趨勢確立 (底底高、站上20MA) 再加碼！
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        qa_c1, qa_c2 = st.columns(2)
        with qa_c1:
            st.markdown("""
            <div style="background:#171C28; border:1px solid #3B82F6; border-radius:10px; padding:14px; margin-bottom:12px;">
                <div style="color:#60A5FA; font-weight:bold; font-size:1.02rem; margin-bottom:6px;">🚀 多頭創新高：為什麼不敢買？（勤誠/廣達實戰）</div>
                <div style="color:#CBD5E1; font-size:0.83rem; line-height:1.6;">
                    • <b>散戶心理死穴</b>：98% 的散戶認為太高不敢買，喪失主升段大飆股。<br>
                    • <b>贏家思維</b>：多頭趨勢不變的股票，股價會一直創新高！<br>
                    • <b>回後買上漲 SOP</b>：創高當天不追高；等量縮拉回守穩 5MA 或 20MA（月線）出轉折紅 K 站上 5MA 突破昨高時，毫不猶豫大膽買進！
                </div>
            </div>
            <div style="background:#171C28; border:1px solid #EF4444; border-radius:10px; padding:14px;">
                <div style="color:#FF7875; font-weight:bold; font-size:1.02rem; margin-bottom:6px;">❌ 為什麼嚴禁「向下攤平買進降低成本」？</div>
                <div style="color:#CBD5E1; font-size:0.83rem; line-height:1.6;">
                    • <b>散戶迷思</b>：以為成本攤低能提早解套，實質上是在加碼正在下跌的弱勢空頭股。<br>
                    • <b>卡死資金</b>：攤平往往導致更多資金套死在弱勢股，一旦再跌恐面臨斷頭腰斬。<br>
                    • <b>官方鐵律</b>：波段賺價差操作絕對嚴禁向下攤平！
                </div>
            </div>
            """, unsafe_allow_html=True)

        with qa_c2:
            st.markdown("""
            <div style="background:#171C28; border:1px solid #F59E0B; border-radius:10px; padding:14px; height:100%;">
                <div style="color:#FBBF24; font-weight:bold; font-size:1.02rem; margin-bottom:6px;">🏆 散戶 8 大錯誤行為 vs 贏家思維對照</div>
                <div style="color:#CBD5E1; font-size:0.82rem; line-height:1.6;">
                    1. <b>不願賠小錢</b> ➔ 贏家迅速停損認賠，絕不猶豫拖延。<br>
                    2. <b>向下攤平加碼</b> ➔ 嚴禁加碼下跌股票，只買強勢起漲股。<br>
                    3. <b>夢想一夜暴富</b> ➔ 做充分準備，嚴守 SOP 穩定累積資產。<br>
                    4. <b>聽信消息電視</b> ➔ 只看客觀走勢圖，消息多為出貨工具。<br>
                    5. <b>因低本益比買牛皮股</b> ➔ 賺差價要買當下有題材有趨勢強勢股。<br>
                    6. <b>賺一點就賣金雞母</b> ➔ 依技術訊號賣出，讓利潤奔馳不預設立場。<br>
                    7. <b>不敢買進創新高股</b> ➔ 多頭會一直創新高，掌握回後買上漲。<br>
                    8. <b>盤前沒策略盤中慌亂</b> ➔ 盤前定好策略，盤中冷靜執行，盤後客觀復盤！
                </div>
            </div>
            """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 8: 做多七不買與六年千萬計畫 (CH11 贏家策略)
    # -------------------------------------------------------------
    with v_tab8:
        st.caption("💡 操盤大師實戰精華：做多進場先排查七大禁忌位置；短線波段價差每月賺 5%，靠六年千萬複利藍圖改變人生！")

        # 一、做多 7 大禁忌位置 (做多七不買)
        st.markdown("""
        <div style="background:#171C28; border:1px solid #30384F; border-radius:10px; padding:16px; margin-bottom:14px;">
            <div style="color:#FF7875; font-weight:bold; font-size:1.08rem; margin-bottom:8px;">🛑 一、做多絕對不可進場的 7 大禁忌位置 (做多七不買)</div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap:10px;">
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#FF7875; font-weight:bold; font-size:0.88rem;">禁忌 1 · 盤底未反轉無三線多排</div>
                    <div style="color:#CBD5E1; font-size:0.80rem; margin-top:4px; line-height:1.5;">
                        打底還沒有完成，均線未呈現 5MA &gt; 10MA &gt; 20MA 多排。嚴禁盲目猜底摸底！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#FF7875; font-weight:bold; font-size:0.88rem;">禁忌 2 · 連漲第 3 根以上勿追</div>
                    <div style="color:#CBD5E1; font-size:0.80rem; margin-top:4px; line-height:1.5;">
                        股價連續推升 3 天以上短線正乖離過大，隨時獲利回吐，嚴禁追高，等量縮拉回再買！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#FF7875; font-weight:bold; font-size:0.88rem;">禁忌 3 · 重大壓力關卡前勿進</div>
                    <div style="color:#CBD5E1; font-size:0.80rem; margin-top:4px; line-height:1.5;">
                        週線/季線壓力、前高、向下缺口前若空間不足 3%，風報比極差，極易衝高解套回測！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#FF7875; font-weight:bold; font-size:0.88rem;">禁忌 4 · 跌破月線反彈未突破月線</div>
                    <div style="color:#CBD5E1; font-size:0.80rem; margin-top:4px; line-height:1.5;">
                        下彎 20MA 月線反壓沉重，屬空方反彈碰壁格局，月線未放量站回前嚴禁做多！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#FF7875; font-weight:bold; font-size:0.88rem;">禁忌 5 · 趨勢盤整或空頭勿做多</div>
                    <div style="color:#CBD5E1; font-size:0.80rem; margin-top:4px; line-height:1.5;">
                        做多只做「頭頭高、底底高」；盤整箱內常被雙巴，空頭走勢破底不斷，嚴禁逆勢做多！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#FF7875; font-weight:bold; font-size:0.88rem;">禁忌 6 · 連續急漲高檔爆量長紅</div>
                    <div style="color:#CBD5E1; font-size:0.80rem; margin-top:4px; line-height:1.5;">
                        波段大漲後在高檔爆出巨量長紅K，往往是主力末升段吸引散戶追高的誘多出貨棒！
                    </div>
                </div>
                <div style="background:#1E2433; border-left:4px solid #EF4444; padding:10px; border-radius:6px;">
                    <div style="color:#FF7875; font-weight:bold; font-size:0.88rem;">禁忌 7 · 多頭進場位是價漲黑K</div>
                    <div style="color:#CBD5E1; font-size:0.80rem; margin-top:4px; line-height:1.5;">
                        開高走低出貨黑K，缺乏實體長紅的多方攻擊力道，防範主力當沖隔日沖騙線！
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 二、贏家策略五大永遠原則 vs 集中火力 2~5 檔
        w_c1, w_c2 = st.columns(2)
        with w_c1:
            st.markdown("""
            <div style="background:#171C28; border:1px solid #3B82F6; border-radius:10px; padding:14px; height:100%;">
                <div style="color:#60A5FA; font-weight:bold; font-size:1.02rem; margin-bottom:6px;">🏆 贏家操盤五大「永遠」原則</div>
                <div style="color:#CBD5E1; font-size:0.82rem; line-height:1.65;">
                    1. <b>永遠控制風險，嚴格執行停損</b>：不讓小賠擴大為致命大賠。<br>
                    2. <b>永遠集中火力在 2 ~ 5 檔股票</b>：絕不分散買十幾檔，全神貫注追蹤掌握盤面節奏！<br>
                    3. <b>永遠汰弱換強</b>：手中只留強勢上漲主升股，弱勢不漲果斷剃除換股！<br>
                    4. <b>永遠只操作符合技術分析高勝率條件的股票</b>。<br>
                    5. <b>永遠相信技術分析，紀律操作</b>。
                </div>
            </div>
            """, unsafe_allow_html=True)
        with w_c2:
            st.markdown("""
            <div style="background:#171C28; border:1px solid #10B981; border-radius:10px; padding:14px; height:100%;">
                <div style="color:#34D399; font-weight:bold; font-size:1.02rem; margin-bottom:6px;">🛡️ 停損的正面思考五大金句</div>
                <div style="color:#CBD5E1; font-size:0.82rem; line-height:1.65;">
                    1. <b>停損是為了賺錢所設的</b>。<br>
                    2. <b>小賠容易快速反敗為勝</b>。<br>
                    3. <b>當下小賠賣出，避開快速暴跌崩盤風險</b>；若賣錯伺機買回也不遺憾。<br>
                    4. <b>當下小賠高價賣出，下跌止跌反轉再低價買回，何樂不為</b>！<br>
                    5. <b>留得青山在，不怕沒柴燒！</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 三、月獲利 5%、年獲利 60% 與六年千萬計畫 (複利滾動藍圖)
        st.markdown("""
        <div style="background:#171C28; border:1px solid #F59E0B; border-radius:10px; padding:16px; margin-top:14px; margin-bottom:14px;">
            <div style="color:#FBBF24; font-weight:bold; font-size:1.08rem; margin-bottom:6px;">💰 月獲利 5% 年獲利 60% 與六年千萬計畫 (複利滾動藍圖)</div>
            <div style="color:#CBD5E1; font-size:0.84rem; line-height:1.6; margin-bottom:12px;">
                • <b>核心哲學</b>：短線價差操作，積小勝為大勝！以 60 萬元為例，每月 22 個交易日獲利 5% = 30,000 元；拆解為每 2 週只要操作 1 次 2.5% = 15,000 元！<br>
                • <b>單利年化</b>：5% × 12 個月 = 年獲利 60%！每年獲利滾入本金複利前進：
            </div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:10px; text-align:center;">
                <div style="background:#1E2433; border:1px solid #3A3F58; border-radius:8px; padding:8px;">
                    <div style="color:#AAA; font-size:0.75rem;">第 1 年</div>
                    <div style="color:#FFF; font-weight:bold; font-size:1.05rem;">96 萬</div>
                    <div style="color:#52C41A; font-size:0.72rem;">年增 36 萬</div>
                </div>
                <div style="background:#1E2433; border:1px solid #3A3F58; border-radius:8px; padding:8px;">
                    <div style="color:#AAA; font-size:0.75rem;">第 2 年</div>
                    <div style="color:#FFF; font-weight:bold; font-size:1.05rem;">153.6 萬</div>
                    <div style="color:#52C41A; font-size:0.72rem;">年增 57.6 萬</div>
                </div>
                <div style="background:#1E2433; border:1px solid #3A3F58; border-radius:8px; padding:8px;">
                    <div style="color:#AAA; font-size:0.75rem;">第 3 年</div>
                    <div style="color:#FFF; font-weight:bold; font-size:1.05rem;">245.7 萬</div>
                    <div style="color:#52C41A; font-size:0.72rem;">年增 92.1 萬</div>
                </div>
                <div style="background:#1E2433; border:1px solid #3A3F58; border-radius:8px; padding:8px;">
                    <div style="color:#AAA; font-size:0.75rem;">第 4 年</div>
                    <div style="color:#FFF; font-weight:bold; font-size:1.05rem;">393.2 萬</div>
                    <div style="color:#52C41A; font-size:0.72rem;">年增 147.5 萬</div>
                </div>
                <div style="background:#1E2433; border:1px solid #3A3F58; border-radius:8px; padding:8px;">
                    <div style="color:#AAA; font-size:0.75rem;">第 5 年</div>
                    <div style="color:#FFF; font-weight:bold; font-size:1.05rem;">629.1 萬</div>
                    <div style="color:#52C41A; font-size:0.72rem;">年增 235.9 萬</div>
                </div>
                <div style="background:#2A2312; border:1px solid #F59E0B; border-radius:8px; padding:8px;">
                    <div style="color:#FBBF24; font-size:0.75rem;">🎉 第 6 年突破</div>
                    <div style="color:#FBBF24; font-weight:bold; font-size:1.15rem;">1,006 萬</div>
                    <div style="color:#FBBF24; font-size:0.72rem;">年增 377.5 萬</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 四、六大高勝率進場位置與進場 K 線 4 大要件
        st.markdown("""
        <div style="background:#171C28; border:1px solid #30384F; border-radius:10px; padding:16px;">
            <div style="color:#60A5FA; font-weight:bold; font-size:1.08rem; margin-bottom:8px;">🚀 四、六大高勝率進場位置與進場 K 線必備標準</div>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:12px;">
                <div style="background:#1E2433; padding:12px; border-radius:8px; border-left:4px solid #2563EB;">
                    <div style="color:#60A5FA; font-weight:bold; font-size:0.92rem; margin-bottom:6px;">📋 尾盤進場 K 線 4 大必備要件</div>
                    <div style="color:#CBD5E1; font-size:0.82rem; line-height:1.6;">
                        1. <b>價漲量增</b>：成交量 &gt; 20MA 均量 1.25 倍。<br>
                        2. <b>實體長紅</b>：當日漲幅 &gt; 2% 且實體大於影線。<br>
                        3. <b>收盤站穩 5MA</b>：站在 5 日操盤生命線之上。<br>
                        4. <b>突破昨日高點</b>：過昨高確認多方攻擊動能！
                    </div>
                </div>
                <div style="background:#1E2433; padding:12px; border-radius:8px; border-left:4px solid #10B981;">
                    <div style="color:#34D399; font-weight:bold; font-size:0.92rem; margin-bottom:6px;">🎯 六大高勝率進場型態位置</div>
                    <div style="color:#CBD5E1; font-size:0.82rem; line-height:1.6;">
                        1. <b>日線回後買上漲</b> (拉回守穩均線轉折買)<br>
                        2. <b>盤整放量突破</b> (箱型平台一棒過頂)<br>
                        3. <b>K 線橫盤放量突破</b> (以基準K線為母體突破)<br>
                        4. <b>回檔 ABC 修正突破原始下降切線</b><br>
                        5. <b>弱勢回檔大量黑 K 的突破</b> (放量長紅過黑K頂)<br>
                        6. <b>突破緩角度往上的上升軌道線</b> (加速起漲)
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_ma_direction_dashboard(df, close_price=None, visible_mas=None):
    """
    在圖表上方渲染全自動均線即時方向、數值與位階狀態儀錶盤
    支援 5MA (操盤線)、10MA (雙週線)、20MA (月線/趨勢線)、60MA (季線/生命線)
    """
    if df is None or len(df) < 2:
        return

    close = float(close_price if close_price is not None else df['Close'].iloc[-1])

    ma_defs = [
        {"col": "SMA_5", "name": "5MA", "alias": "操盤線", "color": "#FF3366"},
        {"col": "SMA_10", "name": "10MA", "alias": "雙週線", "color": "#FFD700"},
        {"col": "SMA_20", "name": "20MA", "alias": "趨勢線", "color": "#00BFFF"},
        {"col": "SMA_60", "name": "60MA", "alias": "生命線", "color": "#A855F7"},
    ]

    cards_html = []
    for m in ma_defs:
        col = m["col"]
        if col not in df.columns:
            continue
        if visible_mas is not None and col not in visible_mas:
            continue

        s = df[col].dropna()
        if len(s) < 2:
            continue

        cur = float(s.iloc[-1])
        prev = float(s.iloc[-2])
        diff = cur - prev
        dist = close - cur

        if diff > 0.005:
            dir_badge = "<span style='color:#FF7875; font-weight:bold;'>↗ 翻揚助漲</span>"
            dir_border = "#FF4D4F"
        elif diff < -0.005:
            dir_badge = "<span style='color:#52C41A; font-weight:bold;'>↘ 下彎助跌</span>"
            dir_border = "#2F9E44"
        else:
            dir_badge = "<span style='color:#FBBF24; font-weight:bold;'>➡️ 走平待變</span>"
            dir_border = "#F59E0B"

        if dist >= 0:
            pos_badge = f"<span style='color:#FF7875; background:rgba(239,68,68,0.18); padding:1px 6px; border-radius:4px; font-weight:bold;'>站上 +{dist:.2f}</span>"
        else:
            pos_badge = f"<span style='color:#52C41A; background:rgba(34,197,94,0.18); padding:1px 6px; border-radius:4px; font-weight:bold;'>跌破 {dist:.2f}</span>"

        diff_str = f"+{diff:.2f}" if diff >= 0 else f"{diff:.2f}"

        card = (
            f'<div style="flex:1; min-width:140px; background:#181D29; border:1px solid #2B3448; border-top:3px solid {m["color"]}; border-radius:8px; padding:7px 10px; margin:3px;">'
            f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">'
            f'<span style="color:{m["color"]}; font-weight:bold; font-size:0.88rem;">{m["name"]} <span style="font-size:0.75rem; color:#888;">({m["alias"]})</span></span>'
            f'<span style="font-weight:bold; font-size:0.92rem; color:#FFF;">{cur:.2f}</span>'
            f'</div>'
            f'<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.78rem;">'
            f'<div>{dir_badge} <span style="color:#888; font-size:0.72rem;">({diff_str})</span></div>'
            f'<div>{pos_badge}</div>'
            f'</div>'
            f'</div>'
        )
        cards_html.append(card)

    if not cards_html:
        return

    cards_str = "".join(cards_html)
    full_html = (
        '<div style="background:#111520; border:1px solid #232A3B; border-radius:10px; padding:6px 8px; margin-bottom:8px;">'
        '<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:4px; padding:0 4px;">'
        '<span style="font-size:0.82rem; font-weight:bold; color:#94A3B8;">🧭 均線即時方向與位階狀態儀錶盤</span>'
        '<span style="font-size:0.76rem; color:#64748B;">每日收盤自動計算斜率 (↗翻揚助漲 / ↘下彎助跌)</span>'
        '</div>'
        f'<div style="display:flex; flex-wrap:wrap; gap:4px;">{cards_str}</div>'
        '</div>'
    )
    st.markdown(full_html, unsafe_allow_html=True)

