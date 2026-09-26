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
                核心心法：看 K 線三件事（趨勢、位置、成交量）· 第五元素 1/2 價
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 次級分頁直覺切換
    v_tab1, v_tab2, v_tab3, v_tab4, v_tab5 = st.tabs([
        "🧭 看K線三件事",
        "🕯️ 第五元素 1/2 價",
        "⚖️ 變盤線高低檔對照",
        "⚔️ 兩根K棒六組對句",
        "🌟 三根晨星與夜星"
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
