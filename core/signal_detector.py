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

def check_14_elimination_rules(df: pd.DataFrame, trend_info: dict, last: pd.Series, prev: pd.Series, signals_dict: dict) -> dict:
    """
    14大實戰淘汰選股法 (負面剔除清單)：
    命中以下任何一條，即代表技術型態存在重大瑕疵或高檔倒貨風險，不得納入主升段追蹤！
    1. 未打底 (未出現第二隻腳、仍在探底或底底低)
    2. 區間整理方向不明 (量能極凍且均線糾結無表態)
    3. 無量 / 量能背離 (價漲量急縮背離，或長久窒息量無主力)
    4. 漲幅已達 1 倍 (100%) 以上高檔 (末升段，風險極大)
    5. 高檔爆量連三黑 (主力高檔連續倒貨三黑烏鴉)
    6. 前波爆量黑K重壓未化解 (上檔巨量套牢區阻擋)
    7. 高檔爆量長黑K (高檔出貨日大長黑)
    8. 回檔跌破月線且月線下彎 (20MA 下彎助跌，月線走空)
    9. 回檔跌破前低 (底底低，多頭架構被破壞)
    10. 漲 1 倍以上且趨勢頭頭低 (高檔轉弱走性格局)
    11. 指標 (KD) 高檔背離 (股價創高但KD未能過80且頭頭低)
    12. 法人高檔連續賣超 (三大法人於高檔連續倒貨)
    13. 線型雜亂 (連續上下長影線、走勢密集震盪無秩序)
    14. 有基本面但技術面走空 (頭頭低底底低空頭走勢，嚴禁逆勢做多)
    """
    reasons = []
    
    c = float(last['Close'])
    o = float(last['Open'])
    h = float(last['High'])
    l = float(last['Low'])
    prev_c = float(prev['Close'])
    sma5 = float(last.get('SMA_5', c))
    sma20 = float(last.get('SMA_20', c))
    prev_sma20 = float(prev.get('SMA_20', sma20))
    sma60 = float(last.get('SMA_60', sma20))
    vol_ratio = float(signals_dict.get('vol_ratio', 1.0))
    is_high = signals_dict.get('is_multi_bagger', False) or (c >= sma20 * 1.15)
    
    # 規則 1：未打底 (仍在探底或無底底高)
    if not trend_info.get('higher_lows', False) and (trend_info.get('lower_lows', False) or (c < sma60 and not (signals_dict.get('bottom_breakout', False) or signals_dict.get('box_range_breakout', False)))):
        reasons.append("【規則1·未打底】尚未走出第二隻腳打底完成訊號，仍在探底或底底低，不可盲目猜底")
        
    # 規則 2：區間整理方向不明
    if signals_dict.get('is_consolidation', False) and not signals_dict.get('consolidation_breakout_imminent', False) and vol_ratio < 0.85:
        reasons.append("【規則2·區間整理方向未明】箱型整理未放量表態，提前進場容易卡死資金")
        
    # 規則 3：無量 / 量能背離
    if signals_dict.get('is_volume_price_divergence', False):
        reasons.append("【規則3·量價背離】價漲量急縮背離或高檔滯漲，攻擊量能匱乏動能衰竭")
    elif vol_ratio <= 0.35 and not signals_dict.get('is_stop_fall_vol', False):
        reasons.append("【規則3·成交量極度窒息】量能大幅低於均量，缺乏主力資金與流動性")
        
    # 規則 4：漲幅已達 1 倍 (100%) 以上高檔
    # 助教教學核心（10/08指引）：若均線呈「四線多排」(5>10>20>60MA) 且處於整理後帶量突破或主升段發動 (c >= sma5 且收紅)，
    # 屬於「初升段整理完成，準備走主升段」，並非出貨末升段，豁免規則4淘汰！
    if signals_dict.get('is_multi_bagger', False):
        bagger_m = signals_dict.get('bagger_multiple', 1.0)
        # 助教 10/17 南亞指導：翻倍股維持多頭且今日站上5MA出紅K，依然能進場，策略轉為短線操作(守5MA)！
        # 僅在跌破5MA、收黑或高檔動能枯竭時才列為淘汰。
        is_bull_playable = (c >= sma5 and c >= o and (sma20 >= prev_sma20 * 0.999))
        if not is_bull_playable:
            reasons.append(f"【規則4·暴漲{bagger_m:.1f}倍高檔轉弱】波段漲幅已翻倍且跌破5MA/收黑，主力獲利豐厚隨時出貨，嚴禁做多")
        elif len(df) >= 5:
            recent_amp = (df.iloc[-3:]['High'].max() - df.iloc[-3:]['Low'].min()) / (df.iloc[-3:]['Low'].min() + 1e-9)
            vol_shrink = (df.iloc[-1]['Volume'] < df.iloc[-20:]['Volume'].mean() * 0.75)
            if recent_amp <= 0.035 and vol_shrink:
                reasons.append(f"【規則4·翻倍股高檔價平量縮】波段漲幅已大，高檔價平量縮動能耗盡，嚴防拉回")
        
    # 規則 5：高檔爆量連三黑
    if len(df) >= 3 and (is_high or signals_dict.get('is_multi_bagger', False)):
        last3 = df.iloc[-3:]
        all_black = (last3['Close'] <= last3['Open']).all()
        any_heavy = (last3['Volume'] >= last3.get('Vol_MA5', last3['Volume']) * 1.25).any()
        if all_black and any_heavy:
            reasons.append("【規則5·高檔爆量連三黑】高檔連續收黑倒貨，典型三黑烏鴉出貨訊號")
            
    # 規則 6：前波爆量黑K重壓未化解
    if signals_dict.get('unresolved_blacks'):
        latest_res = signals_dict['unresolved_blacks'][-1]
        ratio_note = ""
        if signals_dict.get('attack_vol_insufficient_for_res', False):
            ratio_note = f" (攻擊量僅達壓力量 {signals_dict.get('vol_vs_res_ratio', 0)*100:.0f}%，未達助教10/13指導之50%門檻)"
        reasons.append(f"【規則6·爆量黑K套牢重壓】前方有巨量黑K高點 ({latest_res['high']}元) 重壓未化解{ratio_note}")
        
    # 規則 7：高檔爆量長黑K
    if (is_high or signals_dict.get('is_multi_bagger', False)) and (c < o) and (vol_ratio >= 1.45):
        change_rate = (o - c) / o if o > 0 else 0
        if change_rate >= 0.02 or (c - prev_c) / prev_c <= -0.02:
            reasons.append("【規則7·高檔爆量長黑】高檔爆巨量收長黑K，主力帶頭倒貨大逃殺")
            
    # 規則 8：回檔跌破月線且月線下彎
    if signals_dict.get('ma20_death_break', False) or (c < sma20 and sma20 < prev_sma20 * 0.999):
        reasons.append("【規則8·跌破月線且20MA下彎】跌破月線且月線下彎助跌，空頭轉折嚴禁做多")
        
    # 規則 9：回檔跌破前低 (底底低)
    if trend_info.get('lower_lows', False) or (trend_info.get('support') and c < float(trend_info['support']) * 0.998):
        reasons.append("【規則9·跌破前低底底低】跌破前波支撐低點，破壞多頭底底高架構")
        
    # 規則 10：漲 1 倍以上且趨勢頭頭低
    # 豁免：若今日實體紅K突破前高頸線/箱型，或四線多排且今日收盤創近10日收盤新高，代表正在多頭攻擊突破，非做頭轉空！
    if signals_dict.get('is_multi_bagger', False) and trend_info.get('lower_highs', False):
        past10_c = df.iloc[-11:-1]['Close'].max() if len(df) >= 11 else prev_c
        is_breaking_out = (c > past10_c) or signals_dict.get('box_range_breakout', False) or (signals_dict.get('bullish_alignment', False) and c >= o and c >= sma5 and signals_dict.get('is_5ma_rising', True))
        if not is_breaking_out:
            reasons.append("【規則10·翻倍股頭頭低】倍數大漲後反彈不過前高，確認高檔做頭轉空")
        
    # 規則 11：指標 (KD) 高檔背離
    if len(df) >= 12 and 'K' in df.columns:
        recent_bars = df.iloc[-12:]
        if c >= float(recent_bars['Close'].max()) * 0.992:
            max_k = float(recent_bars['K'].max())
            cur_k = float(last.get('K', 50))
            is_strong_red_breakout = (c > o) and (c >= sma5) and (vol_ratio >= 1.1 or (c - prev_c) / prev_c >= 0.015)
            # 助教 10/08 核心心法：「KD 指標是輔助確認，飆股指標都會過熱」
            is_main_or_aligned = signals_dict.get('bullish_alignment', False) or signals_dict.get('main_wave_2nd', False)
            if not is_strong_red_breakout and not is_main_or_aligned:
                if cur_k < 78 and cur_k < max_k - 12:
                    reasons.append("【規則11·KD高檔背離】股價創新高但KD未能突破80且頭頭低，動能背離衰竭")
                
    # 規則 12：法人高檔連續賣超
    if 'Foreign_Buy' in df.columns and len(df) >= 3 and is_high:
        recent_f = df['Foreign_Buy'].tail(3).sum()
        if recent_f < -1000:
            reasons.append("【規則12·法人高檔連賣】外資等三大法人於高檔連續數日大幅調節賣超")
            
    # 規則 13：線型雜亂
    if len(df) >= 10:
        past10 = df.iloc[-10:]
        shadow_cnt = 0
        for _, row in past10.iterrows():
            bar_rng = max(0.01, float(row['High']) - float(row['Low']))
            u_shd = float(row['High']) - max(float(row['Open']), float(row['Close']))
            d_shd = min(float(row['Open']), float(row['Close'])) - float(row['Low'])
            if (u_shd / bar_rng >= 0.42) or (d_shd / bar_rng >= 0.42):
                shadow_cnt += 1
        is_clear_breakout = (c > o) and ((c - prev_c) / prev_c >= 0.02) and (c >= sma5) and signals_dict.get('bullish_alignment', False)
        if shadow_cnt >= 5 and not is_clear_breakout:
            reasons.append("【規則13·線型雜亂無序】連續頻繁出現長上下影線，主力控盤紊亂缺乏趨勢性")
            
    # 規則 14：有基本面但技術面走空
    if signals_dict.get('lower_highs_lows', False) or (trend_info.get('trend_status') == "空頭趨勢" and not signals_dict.get('bottom_breakout', False)):
        reasons.append("【規則14·技術面走空】頭頭低底底低空頭趨勢確立，技術面凌駕消息面，嚴禁逆勢買進")

    # 補充致命警訊：假突破誘多出貨
    if signals_dict.get('is_false_breakout_dump', False):
        reasons.append("【致命警訊·假突破誘多】突破長紅3天內長黑灌破低點，多頭誘多出貨必跑！")

    return {
        "is_eliminated": len(reasons) > 0,
        "eliminated_count": len(reasons),
        "reasons": reasons
    }


def check_do_not_buy_rules(df: pd.DataFrame, trend_info: dict, last: pd.Series, prev: pd.Series, signals_dict: dict) -> dict:
    """
    11-2 做多絕對不可進場的 7 大禁忌位置 (做多七不買)：
    1. 盤底還沒有反轉多頭，沒有三線多排勿進場
    2. 上漲第 3 根以上位置勿追高
    3. 重大壓力關卡前 (週線/季線壓力前、盤整區壓力前、大量下跌黑K或長上影線前) 勿進場
    4. 回檔跌破月線再上漲未突破月線勿進場 (下彎月線反彈碰壁)
    5. 趨勢盤整或空頭勿進場做多
    6. 連續急漲高檔的大量長紅K勿進場 (高檔爆量誘多防反轉)
    7. 多頭進場位置，是價漲的黑K勿進場 (開高走低出貨黑K)
    """
    violations = []

    c = float(last['Close'])
    o = float(last['Open'])
    prev_c = float(prev['Close'])
    sma5 = float(last.get('SMA_5', c))
    sma10 = float(last.get('SMA_10', c))
    sma20 = float(last.get('SMA_20', c))
    prev_sma20 = float(prev.get('SMA_20', sma20))
    vol_ratio = float(signals_dict.get('vol_ratio', 1.0))
    up_days = int(signals_dict.get('up_days', 0))

    # 禁忌 1：盤底還沒有反轉多頭，沒有三線多排
    is_three_ma_bull = (sma5 >= sma10 and sma10 >= sma20)
    if not is_three_ma_bull and not (signals_dict.get('bottom_breakout', False) or signals_dict.get('iron_man', False)):
        violations.append((1, "盤底未反轉無三線多排", "均線尚未形成 5MA > 10MA > 20MA 多頭排列，仍在打底或均線紊亂，不可盲目猜底進場"))

    # 禁忌 2：上漲第 3 根以上位置勿追高 (包含連漲天數與連續紅K棒數)
    consecutive_run = max(up_days, int(signals_dict.get('consecutive_red_days', 0)))
    if consecutive_run >= 3:
        violations.append((2, f"連續上漲/連紅第 {consecutive_run} 根位置勿追高", f"股價已連續推升/收紅 {consecutive_run} 天，短線正乖離過大，極易遭遇獲利調節回檔，應耐心等拉回再切入"))

    # 禁忌 3：重大壓力關卡前勿進場 (空間不足 3%，做多避開 7 位置鐵律)
    candidate_pressures = []
    # 1. 納入所有前高頸線與波峰
    if trend_info and 'peaks' in trend_info and trend_info['peaks']:
        for p in trend_info['peaks']:
            if p['price'] > c * 1.002:
                candidate_pressures.append(('前高頸線', float(p['price'])))
    elif trend_info.get('curr_peak') and trend_info['curr_peak']['price'] > c * 1.002:
        candidate_pressures.append(('前高頸線', float(trend_info['curr_peak']['price'])))

    # 2. 納入下彎月線與下彎季線反壓
    if sma20 > c * 1.002 and sma20 < prev_sma20:
        candidate_pressures.append(('下彎月線20MA', sma20))
    if 'SMA_60' in last and float(last['SMA_60']) > c * 1.002:
        sma60 = float(last['SMA_60'])
        if len(df) >= 5 and sma60 < float(df['SMA_60'].iloc[-4]):
            candidate_pressures.append(('下彎季線60MA', sma60))

    # 3. 納入原有形態壓力
    ch9_pressures = signals_dict.get('ch9_take_profit', {}).get('candidate_pressures', [])
    for p_item in ch9_pressures:
        candidate_pressures.append(p_item)

    if candidate_pressures:
        candidate_pressures.sort(key=lambda x: x[1])
        nearest_p_name, nearest_p_val = candidate_pressures[0]
        # 朱老師鐵律：重大壓力關卡前勿進場 (嚴禁賭突破，收盤未實質突破前距離 <= 2.5% 一律列為壓力臨頭禁忌)
        if nearest_p_val > c and (nearest_p_val - c) / c <= 0.025:
            room_p = ((nearest_p_val - c) / c) * 100
            violations.append((3, f"重大壓力關卡前 ({nearest_p_name} {nearest_p_val:.2f}元)", f"距離上方重壓僅剩 {room_p:.1f}% 空間，依朱老師 10/07 贏家鐵律『做多避開 7 位置：壓力前勿進』，風報比極差，嚴禁賭突破，寧等帶量突破站穩再進！"))

    # 禁忌 4：回檔跌破月線再上漲未突破月線
    if c < sma20 and (sma20 < prev_sma20 * 0.9995):
        violations.append((4, f"跌破月線反彈未突破月線 (20MA {sma20:.2f}元)", "股價仍在下彎月線之下，屬空方反彈碰壁格局，月線未站回前嚴禁做多"))

    # 禁忌 5：趨勢盤整或空頭勿進場做多
    trend_st = trend_info.get('trend_status', '盤整')
    if trend_st in ["空頭趨勢", "盤整趨勢"] and not (signals_dict.get('bottom_breakout', False) or signals_dict.get('box_range_breakout', False)):
        violations.append((5, f"趨勢為【{trend_st}】非確立多頭", "多頭做多只做『頭頭高、底底高』；盤整或空頭走勢嚴禁逆勢做多"))

    # 禁忌 6：連續急漲高檔大量長紅K
    is_high = (c >= sma20 * 1.15) or signals_dict.get('is_multi_bagger', False) or (signals_dict.get('swing_gain', 0) >= 18.0)
    if is_high and vol_ratio >= 2.2 and (c >= o * 1.035):
        violations.append((6, "高檔爆大量長紅K誘多出貨", "連續急漲後在高檔爆出巨量長紅K，往往是主力末升段吸引散戶追高的誘多出貨棒，嚴禁追價"))

    # 禁忌 7：進場位置收實體黑K (開高走低出貨或走弱，不符紅K表態標準)
    if c < o:
        if c >= prev_c:
            violations.append((7, "價平/價漲收實體黑K (開高走低逢高出貨)", "今日K線收實體黑K棒，代表盤中開高走低有主力逢高出貨或賣壓沉重，不符紅K進場標準！"))
        else:
            violations.append((7, "跌勢收實體黑K (空方摜壓未見止跌)", "今日K線收實體黑K下跌，代表空方佔據主導，尚未出現止跌或轉折紅K，嚴禁盲目進場！"))

    # 禁忌 8：收盤跌破 5MA 操盤線
    if c < sma5:
        violations.append((8, f"收盤跌破 5MA 操盤線 ({sma5:.2f}元)", f"股價收盤落在 5MA ({sma5:.2f}元) 之下，短期多頭動能不足，依朱老師紀律做多必須站穩 5MA！"))

    pass_all = (len(violations) == 0)
    return {
        "pass_all": pass_all,
        "violation_count": len(violations),
        "violations": violations,
        "status_badge": "🟢 完美避開做多七大禁忌" if pass_all else f"🛑 觸發 {len(violations)} 項做多禁忌",
        "advice": "全面通過進場安全檢核，可依技術 SOP 於 12:40~13:30 尾盤伺機進場！" if pass_all else "目前線型命中做多禁忌位置，嚴禁衝動追價，耐心等待拉回守穩再做！"
    }


def detect_signals(df: pd.DataFrame, trend_info: dict):
    """
    偵測所有關鍵技術分析訊號與官方 App 策略
    """
    signals = []
    signals_dict = {
        # 波段做多子策略
        "iron_man": False,            # 🏆 無敵鐵金剛 (三線合一頂級波段戰法)
        "higher_highs_lows": False,   # 頭高底高
        "pullback_buy": False,        # 回後準進場
        "main_wave_2nd": False,       # 🚀 主升段第二波 (鎖第一波做第二波)
        "is_turnover_success": False, # 🔥 換手量成功 (爆量黑K/變盤線3天內強勢過高)
        "is_false_breakout_dump": False, # 🚨 假突破誘多出貨 (突破長紅3天內破最低點)
        "bottom_breakout": False,     # 底部起漲
        "high_breakout": False,       # 高檔起漲
        "golden_cross_5_20": False,   # 雙線黃金交叉
        "ma_squeeze_breakout": False, # 🌀 均線糾結突破 (四線糾結起漲第一根)
        "ma_squeeze_bars": 0,         # 均線糾結天數
        "ma_squeeze_months": 0.0,     # 均線糾結月數
        "is_ma_squeeze_over_2m": False,# 均線糾結是否超過2個月 (>=40天)
        "box_range_breakout": False,  # 📦 箱型整理大突破 (一棒過頂·蓄勢噴發起漲第一根)
        "darvas_breakout": False,     # 📦 達瓦斯箱頂突破 (帶量衝破箱頂·開啟新箱子)
        "darvas_support_held": False, # 💎 達瓦斯回測有守 (箱頂變新地板·回後買上漲起漲)
        "darvas_false_breakout": False, # ⚠️ 達瓦斯假突破預警 (軟回箱體內·停損防守)
        "darvas_consolidating": False,# 📦 達瓦斯箱內整理 (等待方向)
        "darvas_info": {},            # 達瓦斯詳細指標 (box_top, box_bottom, target_d 等)
        "is_gap_breakout": False,     # ⚡ 盤整跳空缺口突破 (力道最強·CH6)
        "breakout_stage": "",         # 突破位階勝率 (初升段8成 / 第二波7成 / 高檔短線)
        "flat_base_breakout": False,  # 一字底 (2個月均線糾結10%區間內)
        "w_bottom": False,            # W底 (雙重底·兩腳落差小於4.5%)
        "is_w_pattern_consolidation": False, # W型態整理 (半山腰/高檔W整理，非底部型態·助教10/14陽明指引)
        "n_pattern_bottom": False,    # N字底 (第二隻腳顯著墊高·助教10/14華通指引)
        "pullback_without_5ma_dip": False,  # 回檔未跌破5MA直接漲 (非標準回後買上漲，不可追高·助教10/14南亞指引)
        "pullback_5ma_falling_warning": False, # 回後站回時5MA仍微幅下彎 (助教10/22南亞指引：回後買上漲無5均向上條件，僅作提示不阻擋)
        "deep_pullback_trend_change_warning": False, # ⚠️ 深回檔或長上影黑K易趨勢改變 (助教10/22川寶/TPK-KY指引)
        "breakout_heavy_vol_watch_next": False,      # ⚠️ 盤整突破爆量留上影注意後續走勢 (助教10/22晶碩指引)
        "abc_approaching_cutline": False,            # ⏳ 強勢紅K逼近ABC下降切線尚未破切 (助教10/22華新科指引：先鎖股等破切)
        "breakout_heavy_black_high_pos_warning": False, # ⚠️ 突破大量黑K符合但位置偏高 (助教10/22冠西電指引)
        "heavy_black_trend_intact_watch_next": False,   # 👀 爆量黑K但未破5均與前波底撐先看次日 (助教10/22德宏指引)
        "three_days_two_gaps_down_warning": False,      # 🚨 多頭回檔以三天二缺口方式疑似出貨 (助教10/23臻鼎-KY指引)
        "gap_up_then_gap_down_reversal": False,         # ⚠️ 向上跳空後又跳空回來防M頭/島狀出貨 (助教10/23臻鼎-KY指引)
        "rebound_short_near_support": False,            # ⚠️ 彈後空下跌離下方支撐較近注意止跌 (助教10/23京元電指引)
        "bearish_engulf_to_abc_watch": False,           # 💡 長黑吞噬破5均轉盤整但守月線上鎖多頭ABC (助教10/23南亞指引)
        "kline_consolidation_not_broken_no_short": False, # ⏸️ K線橫盤還沒跌破非彈後空進場點 (助教10/25旺宏指引)
        "rebound_short_ma20_still_rising_warning": False, # ⚠️ 位置彈後空下跌但月線仍向上未空排 (助教10/25華新科指引)
        "bear_confirm_at_ma60_support_wait_bounce": False,# ⚠️ 空頭確認剛碰季線/支撐宜短線或等彈後空更穩 (助教10/25金居&10/27指引)
        "left_red_right_black_watch_5ma": False,        # 👀 左長紅右長黑變盤徵兆注意次日是否破5均 (助教10/25寶僑PG指引)
        "left_red_right_black_low_pos_hold": False,     # 🛡️ 低位階左長紅右長黑缺口未補未破5均與停損續抱觀察 (助教10/25寶僑PG指引)
        "breakout_20ma_falling_stall_warning": False,   # ⏳ 長紅突破站上20MA但20MA向下防隔兩天不漲 (林穎老師10/25影片指引)
        "fake_high_intraday_pierce_only": False,        # ⚠️ 盤中過高收盤未過＝假的過高轉矩形盤整 (助教10/25台光電指引)
        "gain_over_10pct_take_profit_alert": False,     # 🎯 波段漲逾10%遇大量紅K覆蓋黑K看訊號準備停利 (助教10/29達航指引)
        "box_in_range_warning": False,                  # ⚠️ 箱型整理區間內震盪易遭雙巴建議等突破 (助教10/29群聯指引)
        "rebound_signal_not_entry_warning": False,      # ⚠️ 轉折是訊號非進場條件(月線下出晨星/變盤線防弱反彈) (助教10/29大盤指引)
        "breakout_next_day_shadow_pullback": False,     # 🛡️ 突破長紅次日黑K留長下影線屬回測支撐守原停損 (助教10/29旭隼指引)
        "two_peaks_resistance_alert": False,            # ⚠️ 遭遇二個頭壓未實質站穩過壓前不操作 (助教10/30華新科/頎邦指引)
        "low_vol_breakout_vs_pressure_alert": False,    # ⚠️ 突破量能小於前波套牢壓力量能防解套賣壓 (助教10/30百一指引)
        "bottom_volume_better_than_breakout": False,    # 💡 底部低點爆量過高優於過高當日爆量 (助教10/30佳世達指引)
        "breakout_next_day_black_warning": False,       # ⚠️ 進場次日收黑K不對需提高警覺 (助教11/02東捷指引)
        "near_long_term_support_no_short": False,       # ⚠️ 剛跌破長期支撐位置不可直接追空 (助教11/02國巨指引)
        "n_shape_bottom_breakout": False,               # 🚀 N字底型態確立帶量過前高第一根 (助教11/02光寶科指引)
        "wide_range_box_ignore_minor_turns": False,     # 📦 大區間震盪內部細部轉折不看抓高低點 (助教11/02榮科指引)
        "is_cavity_vol_valid": False,                   # 🕳️ 凹洞量嚴格成立(當日量<=昨日50%且止跌) (助教11/03大盤指引)
        "low_liquidity_risk_under_500": False,          # ⚠️ 成交量不足500張流動性風險防滑價 (助教11/03鼎固/華廣指引)
        "heavy_upper_shadows_enemy_ahead": False,       # ⚠️ 大敵當前多根上影線賣壓沉重可選不進場 (助教11/03協易機指引)
        "breakout_next_day_crash_anomaly": False,       # 🚨 突破次日大跌異常走勢嚴防誘多倒貨 (助教11/03華廣指引)
        "consecutive_3_black_rebound_risk": False,       # ⚠️ 下跌連三黑波段低檔防反彈追空風險 (助教11/04指引)
        "overhead_resistance_too_close_trap": False,     # ⚠️ 上方緊鄰前高壓力不可省略壓力自己找位子進場 (助教11/04指引)
        "target_met_awaiting_reversal": False,           # 🎯 滿足點到了不表示止跌須等止跌紅K確認 (助教11/04指引)
        "high_shadow_doubled_stock_risk": False,       # ⚠️ 起漲已翻倍+爆量長上影線未過前高出貨大忌 (助教11/06晉泰指引)
        "rebound_waiting_for_bounce_short": False,     # ⚠️ 低檔等反彈不可直接追空須等彈後空下跌 (助教11/06華城指引)
        "trend_turn_lower_high_confirmed": False,      # 🚨 黑K跌破確認頭頭低多頭瓦解 (助教11/06指引：紅K回後買黑K才確認頭頭低)
        "v_reversal_rebound_setup": False,              # ⚡ 搶V轉四大訊號(急跌+年線支撐+止跌量+紅K過高·助教11/10啟碁指引)
        "breakout_high_must_include_shadow": False,     # ⚠️ 突破前高必含上影線(未過前日最高價不符進場·助教11/10景碩/欣興指引)
        "bearish_indicator_rebound_trap": False,        # 🚨 空頭趨勢指標收斂非反轉(月線下彎空排絕不做多·助教11/10金山電指引)
        "stop_fall_vol_not_limited_to_red": False,      # 💡 止跌大量不限紅K以過大量高點為準 (助教11/10光聖指引)
        "bottom_breakout_no_higher_low_wait_leg2": False, # ⚠️ 突破季線但未成底底高(助教11/11晶宏指引：單腳急拉等第二隻腳)
        "flat_base_shadow_not_breakout": False,          # ⚠️ 一字底帶上影非真突破(助教11/11中電指引：需實體K且過大量高點)
        "bottom_heavy_red_three_supports": False,        # 💎 底部爆量長紅三大回測支撐(助教11/11虎航指引：均線未成防回測1/2價均線頸線)
        "short_near_quarterly_ma_support_risk": False,   # ⚠️ 遇季線與區間支撐有撐不追空(助教11/11金山電指引：做空勝率低)
        "v_rebound_ma20_overhead_resistance": False,     # ⚠️ V轉均線跟不上遇月線反壓(助教11/11指引：急拉受制下彎月線易不如預期)
        "abc_cutline_breakout_must_stand_5ma": False,    # 📐 ABC突破最好站上5均且需收紅K (助教11/12誠美材指引)
        "rebound_missed_best_timing_no_chase": False,    # ⚠️ 錯過搶反彈最佳時機不追等趨勢轉多 (助教11/12聯發科/群創指引)
        "bearish_wave_count_4ma_start": False,          # 📉 空頭波數完成四線空排起算 (助教11/12台汽電指引)
        "breakdown_vs_rebound_short_distinction": False, # 🚨 盤整破底為空頭確認非彈後空 (助教11/12仁寶/英業達指引)
        "bearish_halved_stock_late_stage_risk": False,   # ⚠️ 腰斬股末跌段做空防強彈洗盤 (助教11/12英業達指引)
        "fake_breakout_return_box_exit": False,          # 🛡️ 假突破跌回橫盤出場或守5% (助教11/12訊映指引)
        "rebound_stand_20ma_hold_guard_5ma": False,     # 🚀 反彈站上月線正式轉強守5MA (助教11/12奇鋐指引)
        # 11/13 助教最新專屬定錨指引
        "breakout_volume_divergence_warning": False,     # ⚠️ 挑戰前高價過量未過之價量背離 (助教11/13儒鴻指引)
        "bearish_rebound_drop_is_normal": False,         # 📉 空頭反彈遇阻下跌為常態非高檔出貨 (助教11/13富喬指引)
        "turning_point_5ma_strict_rule": False,          # 📐 轉折波向左追溯含當根且未破5均不可私設轉折 (助教11/13指引)
        "vol_color_misconception_filter": False,         # 📊 成交量紅綠純屬軟體設定無關買賣看實質數字與均量倍數 (助教11/13華城指引)
        # 11/17 助教最新專屬定錨指引
        "high_volume_black_k_pullback_no_buy": False,    # ⚠️ 前方有高檔爆量黑K主力出貨回後買上漲可不進場 (助教11/17廣豐指引)
        "second_leg_bottom_rebound_setup": False,        # 🦵 第二隻腳底底高型態(跌破5均後再站上5均且低點墊高·助教11/17台積電指引)
        "n_to_w_bottom_half_price_rule": False,          # 📐 先看N字底若跌破1/2價改看W底 (助教11/17台積電指引)
        "vol_amplified_not_just_high_vol": False,        # 🚀 特別報價看量放大股非單純量大股 (助教11/17選股指引)
        # 11/19 助教最新專屬定錨指引 (日盤 + 夜盤)
        "bullish_confirmed_not_buy_signal": False,       # ⚠️ 多頭確認不等於符合進場條件(均線未多排且季線反壓近·助教11/19宣德指引)
        "advance_black_k_rejection": False,              # ❌ 做多七不買：進場位收價漲黑K開高走低不買 (助教11/19聯發科指引)
        "topping_pattern_rebound_short_wait": False,     # 📉 圓弧頂/M頭破頸線確認後等回測壓力不過再放空 (助教11/19大盤指引)
        "volume_expansion_stopping_power": False,        # 📊 成交量零和·大跌量縮非止跌·量出有人接且不破低才止跌 (助教11/19指引)
        "margin_clean_washout_stage": False,             # 🧹 殺融資目的在於清洗浮額減輕未來上漲阻力 (助教11/19籌碼指引)
        "short_borrowing_bearish_warning": False,        # 🚨 趨勢偏空+借券餘額大增·防法人做空避險加速 (助教11/19籌碼指引)
        "weekly_m_top_measured_decline_alert": False,    # ⚠️ 週KM頭型態確認防對稱等幅下跌 (助教11/19華星光指引)
        "consolidation_counter_trend_no_buy": False,     # 🛑 空頭長紅漲停或低檔橫盤仍為盤整·等趨勢轉多 (助教11/19創新服務與祥碩指引)
        # 11/23 助教最新專屬定錨指引
        "pattern_retest_failure_invalidation": False,    # 🔄 頭部型態成立後回測壓力若無壓強彈轉多則原目標失敗 (助教11/23大盤圓弧頂指引)
        "gap_and_neckline_overlap_resistance": False,    # 🧱 空方跳空缺口與頭部頸線重疊構成雙重反壓 (助教11/23大盤指引)
        "rebound_depth_consolidation_rule": False,       # ⏳ 跌深整理時間拉長·彈高整理時間縮短法則 (助教11/23指引)
        "reverse_trial_buy_above_ma20_stop": False,      # 🎯 逆向過月線2成試單(不強制月線上揚)但回測破月線恐空頭續勢需全砍 (助教11/23指引)
        "kline_consolidation_3day_min_rule": False,      # 📊 K線橫盤自第1根起算滿3根即成立·第4天起任1天突破或跌破皆算 (助教11/23 6-10指引)
        "bearish_confirm_break_actual_low": False,       # 📉 空頭確認以收盤跌破前波轉折「最低點」為準非僅看收盤價 (助教11/23亞泥指引)
        # 11/25 助教最新專屬定錨指引 + 布林通道擴充
        "close_above_ma5_any_k_rule": False,             # 📊 收盤價高於5均即為站上(不限紅黑K)但黑K次日易跌 (助教11/25晶豪科指引)
        "bearish_rebound_pressure_alert": False,         # ⚠️ 空頭反彈「見撐不是撐，要看壓力重不重」(助教11/25無量漲停反彈指引)
        "megaphone_broadening_pattern_alert": False,     # 📢 喇叭擴散型態(頭頭高且底底低·觸及上軌易遇壓·助教11/25潤弘指引)
        "bollinger_squeeze_breakout": False,             # 🎯 布林通道收斂擠壓後帶量突破上軌起爆點 (11/25補充布林戰法·獨立隔離)
        "bollinger_upper_band_walk": False,              # 🚀 布林通道強勢貼上軌運行·抱單守中軌(20MA)移動停利 (11/25補充布林戰法·獨立隔離)
        "bollinger_lower_band_rebound": False,           # 🪃 布林通道跌破下軌後迅速收回下軌之左側反彈訊號 (11/25補充布林戰法·獨立隔離)
        "bollinger_info": {"available": False},          # 🫧 獨立布林通道輔助診斷資訊 (絕不混入正課主訊號列表)
        "rounding_bottom": False,     # 圓弧底
        "kline_consolidation_breakout": False, # 📊 6-3 K線橫盤突破 (3天橫盤放量突破·CH6)
        "abc_correction_breakout": False,      # 📐 6-5 突破ABC修正下降切線 (短空做頭失敗續噴·CH6)
        "ascending_channel_breakout": False,   # 🚀 6-6 突破上升軌道線 (多頭加速噴出·CH6)
        "breakout_heavy_black_high": False,    # ⚡ 6-7 突破飆股大量黑K最高點 (換手再轉強·CH6)
        "is_attack_vol": False,       # 攻擊量 (5MA量 1.25倍以上)
        "is_stop_fall_vol": False,    # 止跌量 (5MA量 50%以下急縮且不破低)
        "is_volume_price_divergence": False, # 量價背離 (價漲量縮 / 價平量增)
        "elimination_info": {"is_eliminated": False, "reasons": []}, # 14大淘汰檢核

        # 波段做空核心子策略
        "lower_highs_lows": False,    # 頭低底低 (六字訣空頭確認)
        "rebound_short": False,       # 彈後準進場 (反彈測線無力·短線空點)
        "is_parallel_red_warning": False, # ⚠️ 6-8 並列紅K (假下跌預警·嚴守停損·CH6)
        "kline_consolidation_breakdown": False, # 📊 6-10 K線橫盤跌破 (3天橫盤黑K摜破·CH6)
        "abc_rebound_breakdown": False,         # 📐 6-12 跌破反彈ABC切線 (短多做底失敗重回主跌·CH6)
        "descending_channel_breakdown": False,  # 📉 6-13 跌破下降軌道線 (空頭加速趕底·CH6)
        "breakdown_rebound_red_low": False,     # ⚡ 6-14 跌破大量紅K低點 (弱勢反彈破底·空頭再轉弱·CH6)
        "top_breakdown": False,       # 頂部起跌 (高檔頭部放量長黑破線)
        "low_breakdown": False,       # 低檔起跌 (破前低弱勢續殺)
        "death_cross_5_20": False,    # 雙線死亡交叉 / 雙線下彎
        "ma_squeeze_breakdown": False,# 🌀 均線糾結跌破 (四線空排崩跌初跌段)
        "bearish_alignment_4ma": False,# 均線四線空排 (5 < 10 < 20 < 60MA 全數下彎)
        "ma20_death_break": False,    # 🔴 跌破月線3天助漲未回且月線下彎 (多頭終結清倉)
        "flat_top_breakdown": False,  # 一字頭 (平躺橫盤跌破)
        "n_pattern_top": False,       # 倒N字底 (反彈不過前高再破低)
        "rounding_top": False,        # 圓弧頂 (頭部蓋頂)
        
        # 6-15 飆股操盤與智慧K線交易法
        "explosive_stock_status": "常態波動", # 飆股量價五燈號
        "smart_kline_safe": True,            # 智慧K線交易法：收盤未破前一日最低點
        "smart_kline_defend": 0.0,           # 前一日最低點 (智慧K線防守價)
        "smart_kline_exit_warning": False,   # 智慧K線退場警戒 (跌破前一日最低點)

        # 其他大類
        "long_hold": False,           # 長抱
        "one_pm_strategy": False,     # 一點鐘 (多)
        "one_pm_short": False,        # 一點鐘 (空)
        "intraday_strong": False,     # 盤中強勢
        "intraday_weak": False,       # 盤中弱勢
        
        # 鎖股池狀態
        "watchlist_stage": "觀察中",   # 等突破 / 高檔等回檔 / 回檔等上漲
        
        # 成交量位置研判 (起漲攻擊量 vs 高檔爆量)
        "volume_tag": "常態量",       # 起漲放量 / 高檔爆量 / 溫和放量 / 量縮整理 / 常態量
        "volume_status": "常態量",
        "vol_ratio": 1.0,

        # 輔助技術分析
        "bullish_alignment": False,   # 均線多頭排列
        "safety_rating": "🟢 安全首選",# 實戰安全評級
        "safety_reasons": [],         # 評級原因說明
        "chili_count": 1,             # 動能辣椒數 (1~3)
        "deduction": {},              # 均線扣抵

        # CH7 實戰停損與風控全攻略
        "ch7_stop_loss": {
            "kline_stop": 0.0,
            "ma5_stop": 0.0,
            "pattern_stop": 0.0,
            "fixed_5pct_stop": 0.0,
            "absolute_10pct_stop": 0.0,
            "recommended_stop": 0.0,
            "stop_type": "K線紅K低點",
            "stop_desc": "",
            "risk_pct": 0.0,
            "is_trailing_stop_active": False,
            "trailing_stop_price": 0.0,
            "swing_gain": 0.0,
            "is_drop_5pct_warning": False,
            "absolute_warnings": []
        }
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
    v_ma5 = float(last['Vol_MA5']) if 'Vol_MA5' in last and not np.isnan(last['Vol_MA5']) else (float(df['Volume'].tail(5).mean()) if len(df) >= 5 else v)
    v_ma20 = float(last['Vol_MA20']) if 'Vol_MA20' in last and not np.isnan(last['Vol_MA20']) else v
    vol_ratio_5 = round(v / v_ma5, 2) if v_ma5 > 0 else 1.0
    vol_ratio_20 = round(v / v_ma20, 2) if v_ma20 > 0 else 1.0
    vol_ratio = vol_ratio_5  # 標準：以 5MA 基本量為基準比率

    prev_c = round(float(prev['Close']), 2)
    prev_h = round(float(prev['High']), 2)
    prev_l = round(float(prev['Low']), 2)
    prev_v = float(prev['Volume'])
    change_pct = ((c - prev_c) / prev_c) * 100 if prev_c > 0 else 0
    is_red = (c >= o)

    # 實體與上影線分析 (用以精準識別與過濾「避雷針 / 衝高拉回」)
    body = abs(c - o)
    upper_shadow = max(0.0, h - max(o, c))
    total_range = max(0.01, h - l)
    upper_shadow_ratio = upper_shadow / total_range
    upper_shadow_pct = round((upper_shadow / c) * 100, 2) if c > 0 else 0.0

    # 長上影線（避雷針）判定：
    # 1. 上影線長度 >= 實體紅K長度，且上影線回吐幅度 >= 1.5% (經典衝高遇壓無力突破，如 4770 上品)
    # 2. 或上影線佔全日高低振幅 35% 以上，且相對於收盤價超過 1.2%
    # 3. 或上影線 >= 實體 1.25 倍，且上影線幅度 >= 1.0%
    has_long_upper_shadow = (
        (upper_shadow >= body * 1.0 and upper_shadow_pct >= 1.5) or
        (upper_shadow_ratio >= 0.35 and upper_shadow_pct >= 1.2) or
        (upper_shadow >= body * 1.25 and upper_shadow_pct >= 1.0)
    )
    # 實體飽滿收高 (無長上影線)：收在當日最高點 1.5% 內，且上影線小於實體紅K 0.6 倍
    is_solid_bull = ((h - c) <= (c * 0.015) or (upper_shadow <= body * 0.6)) and not has_long_upper_shadow

    signals_dict['has_long_upper_shadow'] = has_long_upper_shadow
    signals_dict['is_solid_bull'] = is_solid_bull
    signals_dict['upper_shadow_pct'] = upper_shadow_pct

    sma5 = round(float(last['SMA_5']), 2)
    sma10 = round(float(last['SMA_10']), 2) if 'SMA_10' in last and not np.isnan(last['SMA_10']) else sma5
    sma20 = round(float(last['SMA_20']), 2) if 'SMA_20' in last and not np.isnan(last['SMA_20']) else sma5
    sma60 = round(float(last.get('SMA_60', sma20)), 2)

    prev_sma5 = round(float(prev['SMA_5']), 2)
    prev_sma10 = round(float(prev['SMA_10']), 2) if 'SMA_10' in prev and not np.isnan(prev['SMA_10']) else prev_sma5
    prev_sma20 = round(float(prev['SMA_20']), 2) if 'SMA_20' in prev and not np.isnan(prev['SMA_20']) else prev_sma5
    prev_sma60 = round(float(prev.get('SMA_60', prev_sma20)), 2)

    # 1. 均線扣抵 (支援今日扣抵價、明日扣抵價、扣抵日、差價與走勢預判)
    deduction = {}
    if len(df) >= 5:
        idx5 = -5
        d5 = float(df.iloc[idx5]['Close'])
        d5_date = str(df.iloc[idx5].get('Date', ''))[:10]
        d5_diff = c - d5
        d5_next = float(df.iloc[-4]['Close']) if len(df) >= 5 else d5
        deduction['5MA'] = {
            "price": round(d5, 2),
            "deduct_price": round(d5, 2),
            "next_price": round(d5_next, 2),
            "diff": round(d5_diff, 2),
            "date": d5_date,
            "status": "扣低助漲 ↗" if c >= d5 else "扣高助跌 ↘",
            "next_status": "明日扣低助漲 ↗" if c >= d5_next else "明日扣高助跌 ↘"
        }
    if len(df) >= 20:
        idx20 = -20
        d20 = float(df.iloc[idx20]['Close'])
        d20_date = str(df.iloc[idx20].get('Date', ''))[:10]
        d20_diff = c - d20
        d20_next = float(df.iloc[-19]['Close']) if len(df) >= 20 else d20
        deduction['20MA'] = {
            "price": round(d20, 2),
            "deduct_price": round(d20, 2),
            "next_price": round(d20_next, 2),
            "diff": round(d20_diff, 2),
            "date": d20_date,
            "status": "扣低助漲 ↗" if c >= d20 else "扣高助跌 ↘",
            "next_status": "明日扣低助漲 ↗" if c >= d20_next else "明日扣高助跌 ↘"
        }
    if len(df) >= 60:
        idx60 = -60
        d60 = float(df.iloc[idx60]['Close'])
        d60_date = str(df.iloc[idx60].get('Date', ''))[:10]
        d60_diff = c - d60
        d60_next = float(df.iloc[-59]['Close']) if len(df) >= 60 else d60
        deduction['60MA'] = {
            "price": round(d60, 2),
            "deduct_price": round(d60, 2),
            "next_price": round(d60_next, 2),
            "diff": round(d60_diff, 2),
            "date": d60_date,
            "status": "扣低助漲 ↗" if c >= d60 else "扣高助跌 ↘",
            "next_status": "明日扣低助漲 ↗" if c >= d60_next else "明日扣高助跌 ↘"
        }
    signals_dict['deduction'] = deduction

    # 2. 均線多頭排列
    if sma5 > sma10 > sma20 > sma60:
        signals_dict['bullish_alignment'] = True

    # 3. 連漲天數與連續紅K棒數計算 (防追高核心指標)
    up_days = 0
    for j in range(len(df) - 1, max(0, len(df) - 15), -1):
        if df.iloc[j]['Close'] > df.iloc[j - 1]['Close']:
            up_days += 1
        else:
            break

    consecutive_red_days = 0
    for j in range(len(df) - 1, max(0, len(df) - 15), -1):
        if df.iloc[j]['Close'] >= df.iloc[j]['Open']:
            consecutive_red_days += 1
        else:
            break

    # 取連漲或連紅兩者之大者作為實際衝刺天數
    effective_run_days = max(up_days, consecutive_red_days)
    signals_dict['up_days'] = effective_run_days
    signals_dict['price_up_days'] = up_days
    signals_dict['consecutive_red_days'] = consecutive_red_days

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
                "ratio": round(vol / vma, 1),
                "volume": float(vol)
            })

    unresolved_blacks = [b for b in heavy_black_ks if b['high'] >= c]
    signals_dict['unresolved_blacks'] = unresolved_blacks
    signals_dict['has_unresolved_blacks'] = len(unresolved_blacks) > 0

    # 助教 10/13 華新指導：攻擊量與壓力量比對，不用大於，但至少要到一半 (>= 50%)
    if unresolved_blacks:
        latest_res_vol = unresolved_blacks[-1].get('volume', 0)
        signals_dict['res_black_vol'] = latest_res_vol
        if latest_res_vol > 0:
            vol_vs_res_ratio = round(v / latest_res_vol, 2)
            signals_dict['vol_vs_res_ratio'] = vol_vs_res_ratio
            if vol_vs_res_ratio < 0.5:
                signals_dict['attack_vol_insufficient_for_res'] = True
    chili = 1
    vol_ratio = v / v_ma20 if v_ma20 > 0 else 1.0
    if vol_ratio >= 2.0 or abs(change_pct) >= 5.0:
        chili = 3
    elif vol_ratio >= 1.3 or abs(change_pct) >= 2.5:
        chili = 2
    signals_dict['chili_count'] = chili

    # ----------------------------------------------------
    # 提前計算高低位階與暴漲倍數 (確保各策略與突破位階均能安全引用)
    # ----------------------------------------------------
    is_multi_bagger = False
    bagger_multiple = 1.0
    if len(df) >= 40:
        check_period = df.iloc[-120:] if len(df) >= 120 else df
        lowest_price = float(check_period['Low'].min())
        if lowest_price > 0:
            bagger_multiple = round(c / lowest_price, 2)
            if bagger_multiple >= 1.95:
                is_multi_bagger = True
    signals_dict['is_multi_bagger'] = is_multi_bagger
    signals_dict['bagger_multiple'] = bagger_multiple

    past20_low = df.iloc[-25:-5]['Low'].min() if len(df) >= 25 else l
    is_near_bottom = (c <= past20_low * 1.15) or (sma20 <= sma60 * 1.02)
    is_high_position = is_multi_bagger or (c >= sma20 * 1.15) or (len(df) >= 40 and c >= df.iloc[-40:]['Low'].min() * 1.35)
    is_low_position = is_near_bottom or (sma5 <= sma60 * 1.08) or (c <= sma20 * 1.06)
    signals_dict['is_high_position'] = is_high_position

    # ----------------------------------------------------
    # 56 個常見 K 線型態核心精華 (一根四元素與第五元素 1/2 價 · 變盤線 · 兩根六組對句 · 三根晨夜星)
    # ----------------------------------------------------
    half_price = round((h + l) / 2.0, 2)
    prev_o = round(float(prev['Open']), 2)
    prev_h = round(float(prev['High']), 2)
    prev_l = round(float(prev['Low']), 2)
    prev_half_price = round((prev_h + prev_l) / 2.0, 2)
    signals_dict['half_price'] = half_price
    signals_dict['prev_half_price'] = prev_half_price

    # 1. 第五元素 1/2 價突破與跌破判定
    is_prev_large_red = (prev_c > prev_o) and ((prev_c - prev_o) / (prev_o + 1e-9) >= 0.035)
    is_prev_large_black = (prev_c < prev_o) and ((prev_o - prev_c) / (prev_o + 1e-9) >= 0.035)

    if is_prev_large_red and c < prev_half_price:
        signals_dict['half_price_break'] = True
        signals.append(f"⚠️ 跌破前日長紅 1/2 成本價 ({prev_half_price:.2f}元)：多方氣勢轉弱")
    elif is_prev_large_black and c > prev_half_price:
        signals_dict['half_price_rebound'] = True
        signals.append(f"🟢 突破前日長黑 1/2 成本價 ({prev_half_price:.2f}元)：空方力道轉弱")

    # 2. 變盤線型態研判 (高檔凶多吉少 vs 低檔逢凶化吉)
    is_doji = (body <= total_range * 0.10)
    is_tombstone = (upper_shadow >= total_range * 0.65 and (min(o, c) - l) <= total_range * 0.12)
    is_dragonfly = ((min(o, c) - l) >= total_range * 0.65 and upper_shadow <= total_range * 0.12)
    is_hammer = ((min(o, c) - l) >= body * 1.8 and upper_shadow <= total_range * 0.18)
    is_inverted_hammer = (upper_shadow >= body * 1.8 and (min(o, c) - l) <= total_range * 0.18)

    reversal_candle = ""
    if is_high_position:
        if is_tombstone:
            reversal_candle = "高檔墓碑線 (倒T/天劍線，轉折下殺警示)"
        elif is_dragonfly:
            reversal_candle = "高檔長T線 (高檔洗盤，轉折向下警示)"
        elif is_doji:
            reversal_candle = "高檔十字線 (多空僵持，變盤向下警示)"
        elif is_hammer:
            reversal_candle = "高檔吊人線 (下影線誘多，轉折向下警示)"
        elif is_inverted_hammer:
            reversal_candle = "高檔反鎚線 (衝高拉回，轉折向下警示)"
        if reversal_candle:
            signals_dict['reversal_candle_warning'] = reversal_candle
            signals.append(f"⚠️ {reversal_candle}")
    elif is_low_position:
        if is_hammer:
            reversal_candle = "低檔鎚子線 (下影強撐，逢凶化吉起漲)"
        elif is_dragonfly:
            reversal_candle = "低檔長T線 (下檔買盤強勁，轉折向上)"
        elif is_tombstone:
            reversal_candle = "低檔墓碑線 (多方試盤，逢凶化吉轉折)"
        elif is_doji:
            reversal_candle = "低檔十字變盤線 (空方竭盡，止跌向上訊號)"
        elif is_inverted_hammer:
            reversal_candle = "低檔反鎚線 (主力試盤買盤進駐，轉折向上)"
        if reversal_candle:
            signals_dict['bottom_reversal_candle'] = reversal_candle
            signals.append(f"🔥 {reversal_candle}")

    # 3. 兩根 K 棒對稱組合 (六組對句)
    # (A) 烏雲罩頂 (長黑覆蓋) vs 旭日東昇 (長紅覆蓋)
    if is_prev_large_red and c < o and o >= prev_c and c < (prev_o + prev_c) / 2 and c > prev_o and is_high_position:
        signals_dict['dark_cloud_cover'] = True
        signals.append("⚠️ 烏雲罩頂 (長黑覆蓋·高檔次日開低確認止漲)")
    elif is_prev_large_black and c > o and o <= prev_c and c > (prev_o + prev_c) / 2 and c < prev_o and is_low_position:
        signals_dict['piercing_line'] = True
        signals.append("🔥 旭日東昇 (長紅覆蓋·低檔次日開高確認止跌)")

    # (B) 長黑吞噬 vs 長紅吞噬
    if prev_c > prev_o and c < o and o >= prev_c and c <= prev_o and is_high_position:
        signals_dict['bearish_engulfing'] = True
        signals.append("⚠️ 長黑吞噬 (主力出貨·次日開低確認止漲)")
    elif prev_c < prev_o and c > o and o <= prev_c and c >= prev_o and is_low_position:
        signals_dict['bullish_engulfing'] = True
        signals.append("🔥 長紅吞噬 (主力進貨·次日開高確認止跌)")

    # (C) 母子懷抱 (孕線)
    if is_prev_large_red and max(o, c) <= prev_c and min(o, c) >= prev_o and is_high_position:
        signals_dict['harami_top'] = True
        signals.append("⚠️ 母子懷抱 不懷好意 (長紅藏小K·變盤警示)")
    elif is_prev_large_black and max(o, c) <= prev_o and min(o, c) >= prev_c and is_low_position:
        signals_dict['harami_bottom'] = True
        signals.append("🔥 母子懷抱 光明在望 (長黑藏小K·止跌轉折)")

    # (D) 破底貫穿 vs 破高貫穿
    if prev_c > prev_o and c < o and c < prev_l and is_high_position:
        signals_dict['piercing_breakdown'] = True
        signals.append("⚠️ 破底貫穿 (黑K摜破前日最低點·一路向下)")
    elif prev_c < prev_o and c > o and c > prev_h and is_low_position:
        signals_dict['piercing_breakout'] = True
        signals.append("🔥 破高貫穿 (紅K穿透前日最高點·一路向上)")

    # 4. 三根 K 棒夜星 vs 晨星變盤組合
    if len(df) >= 3:
        prev2_o = round(float(prev2['Open']), 2)
        prev2_c = round(float(prev2['Close']), 2)
        prev2_h = round(float(prev2['High']), 2)
        prev2_l = round(float(prev2['Low']), 2)

        # 孤島夜星 (左右跳空最強轉折向下) vs 孤島晨星 (左右跳空最強轉折向上)
        is_island_evening = (prev2_c > prev2_o and min(prev_o, prev_c) > prev2_h and max(o, c) < prev_l and c < o and is_high_position)
        is_island_morning = (prev2_c < prev2_o and max(prev_o, prev_c) < prev2_l and min(o, c) > prev_h and c > o and is_low_position)

        if is_island_evening:
            signals_dict['island_evening_star'] = True
            signals.append("🛑 孤島夜星 (左右跳空孤島落單·轉折力道最強下殺)")
        elif is_island_morning:
            signals_dict['island_morning_star'] = True
            signals.append("🚀 孤島晨星 (左右跳空孤島落單·轉折力道最強起漲)")

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
    # 策略 🏆：無敵鐵金剛 / 三線合一 (官方 App 最高勝率 7~8 成旗艦波段戰法)
    # 實戰心法鐵律 (大師核心操盤心法)：
    # 1. 轉折波：多頭型態已確認 (底底高 + 頭頭高，即 is_bull)
    # 2. 雙線翻揚：5MA >= 20MA 且 5MA 走升 (is_5ma_rising)、20MA 走平或向上翻揚
    # 3. 今日 K 棒：當日收實體紅 K (c >= o) 且收盤價站穩 5MA 操盤線 (c >= sma5)
    # 操作紀律：買進後守穩 5MA 一路續抱，跌破 5MA 立即紀律停利出場！
    # ----------------------------------------------------
    is_20ma_rising = (sma20 >= prev_sma20 * 0.998)
    is_5ma_turning = is_5ma_rising or (c >= sma5 and sma5 >= prev_sma5 * 0.985) or (sma20 >= prev_sma20 and c >= sma5)
    if is_bull and sma5 >= sma20 and is_5ma_turning and is_20ma_rising and is_red and (c >= sma5):
        signals_dict['iron_man'] = True
        signals.append("🏆 無敵鐵金剛 (多頭確立+雙線翻揚+今日紅K站上5MA)")

    # ----------------------------------------------------
    # 策略 C：回後準進場 (經典回後買上漲進場訊號)
    # 實戰心法鐵律：
    # 1. 助教 10/14 鐵律 (華通 2313 & 南亞 1303)：
    #    回檔期間必須曾「跌破 5MA 再站回」才算！若未曾跌破 5 均直接漲，非教學進場點，不可追高！
    # 2. 今日收轉折紅K站回 5MA 操盤線之上 (c >= sma5)
    # 3. 5MA 操盤線必須「走平或向上翻揚」(is_5ma_rising)，若操盤線仍在下彎，代表短線助跌，嚴禁買進！
    # ----------------------------------------------------
    support = trend_info.get('support', 0) or (c * 0.93)
    resistance = trend_info.get('resistance', 0) or (c * 1.08)
    recent_lows = df.iloc[-4:-1]['Low'].min() if len(df) >= 4 else l
    tested_ma = (recent_lows <= sma20 * 1.03 or l <= sma5 * 1.015)
    not_broken_support = l >= support * 0.985
    stand_on_5ma = (c >= sma5)

    # 助教 10/14 華通/南亞檢核：拉回波段 (過去 1~5 日) 必須曾實質回測並跌破 5MA (Close < SMA_5 或 Low < SMA_5 * 0.998)
    has_dipped_5ma_in_pullback = False
    if len(df) >= 3:
        pullback_window = df.iloc[-5:-1] if len(df) >= 6 else df.iloc[:-1]
        has_dipped_5ma_in_pullback = ((pullback_window['Close'] < pullback_window['SMA_5']) | (pullback_window['Low'] < pullback_window['SMA_5'] * 0.998)).any()

    is_5ma_turning = is_5ma_rising or (c >= sma5 and sma5 >= df.iloc[-2]['SMA_5'] * 0.99) or (sma20 >= df.iloc[-2]['SMA_20'] and c >= sma5)
    is_5ma_falling = (sma5 < prev_sma5 * 0.996) and not is_5ma_rising

    # 助教 10/22 川寶(1595)/TPK-KY(3673) 檢核：回檔是否過深 (距近15日高點回撤逾11%或吃掉前波漲幅逾55%)
    recent15_high = float(df.iloc[-15:-1]['High'].max()) if len(df) >= 15 else h
    pullback_depth_pct = (recent15_high - min(recent_lows, l)) / (recent15_high + 1e-9)
    wave_span = max(0.01, recent15_high - support)
    wave_retrace_ratio = (recent15_high - min(recent_lows, l)) / wave_span
    is_deep_pullback = (pullback_depth_pct >= 0.11) or (wave_retrace_ratio >= 0.55)

    if (is_bull or signals_dict['golden_cross_5_20'] or sma5 >= sma20 or is_20ma_rising) and tested_ma and not_broken_support and stand_on_5ma:
        if has_dipped_5ma_in_pullback:
            if not is_red or has_long_upper_shadow:
                # 助教 10/22 TPK-KY (3673) 指引：雖然位置是回後買上漲，但回檔深或上漲是長上影線的黑K，要留意趨勢改變
                if c >= prev_c or stand_on_5ma:
                    signals_dict['deep_pullback_trend_change_warning'] = True
                    signals.append("⚠️ 位置回後買但收長上影/黑K (助教10/22 TPK-KY指引：雖位置是回後買上漲，但上漲是長上影黑K，留意趨勢改變)")
            else:
                # 助教 10/22 南亞 (1303) 官方定調：「回後買上漲沒有 5 均要向上的條件，除非是自己新增的進場條件。」
                signals_dict['pullback_buy'] = True
                if is_5ma_falling:
                    signals_dict['pullback_5ma_falling_warning'] = True
                    signals.append("回後準進場 (跌破5MA後紅K站回·助教10/22南亞指引：回後買上漲無5均向上條件)")
                else:
                    signals.append("回後準進場 (跌破5MA後轉折紅K強勢站回·標準進場點)")

                if is_deep_pullback or (resistance > c and (resistance - c) / (c + 1e-9) <= 0.045):
                    signals_dict['deep_pullback_trend_change_warning'] = True
                    signals.append("⚠️ 回檔深/逼近前高壓 (助教10/22川寶/TPK指引：可做多但容易趨勢改變，注意前高壓是否能過)")

                # 👑 創高無壓回後買上漲 (朱家泓老師 10/07 達人秀：日月光 3711、台達電 2308 歷史新高龍頭戰法)
                is_ath_candidate = False
                if len(df) >= 30 and not unresolved_blacks and not has_long_upper_shadow:
                    past_max = float(df.iloc[-120:]['High'].max()) if len(df) >= 120 else float(df['High'].max())
                    recent_high = float(df.iloc[-25:]['High'].max())
                    if recent_high >= past_max * 0.985 and c >= past_max * 0.94:
                        is_ath_candidate = True
                if is_ath_candidate:
                    signals_dict['ath_pullback_buy'] = True
                    signals.append("👑 創高無壓回後買 (歷史新高龍頭·上方無解套賣壓·必過前高首選)")

                # 助教 10/13 康舒指導：回後買上漲若季線(60MA)仍在上方且下彎，底部未完成，僅能短線操作，提防遇壓不漲
                if c < sma60 and sma60 < prev_sma60 * 0.999:
                    signals_dict['pullback_ma60_resistance'] = True
                    signals.append("⚠️ 季線下彎反壓 (回後買僅短線操作·底部未完成防遇壓不漲)")
        elif is_red:
            # 未曾跌破 5 均直接漲 (如南亞 1303 10/14)
            signals_dict['pullback_without_5ma_dip'] = True
            signals.append("⚠️ 回檔未破5MA直接漲 (助教10/14南亞指引：非回後買上漲進場點·切忌追高)")

    # ----------------------------------------------------
    # 策略 C-2：主升段第二波 (強勢飆股主升段：鎖第一波，做第二波)
    # 實戰心法鐵律：
    # 1. 過去 10~25 天曾出現強勢第一波 (累計漲幅 >= 15%，有連續急漲)
    # 2. 回檔跌破 5MA 降溫洗盤，但低點守穩在月線之上 (Low >= SMA_20 * 0.985) 且 20MA 向上
    # 3. 今日出攻擊量收實體長紅站上 5MA (過昨高)，為第二波主升段起漲點！
    # ----------------------------------------------------
    is_main_wave_2nd = False
    if len(df) >= 20 and is_red and (c >= sma5) and is_5ma_rising:
        prev_high = float(prev['High'])
        is_over_prev_high = (c > prev_high)
        is_supported_by_ma20 = (l >= sma20 * 0.985) and (c >= sma20) and (sma20 >= prev_sma20 * 0.998)
        prior_period = df.iloc[-25:-3] if len(df) >= 25 else df.iloc[:-3]
        prior_min = float(prior_period['Low'].min())
        prior_max = float(prior_period['High'].max())
        had_strong_wave1 = (prior_max - prior_min) / (prior_min + 1e-9) >= 0.14
        had_pullback = (df.iloc[-4:-1]['Close'] < df.iloc[-4:-1]['SMA_5']).any()
        has_volume = (vol_ratio_5 >= 1.15 or change_pct >= 1.0)
        if had_strong_wave1 and had_pullback and is_supported_by_ma20 and is_over_prev_high and has_volume:
            is_main_wave_2nd = True

    if is_main_wave_2nd:
        signals_dict['main_wave_2nd'] = True
        signals.append("🚀 主升段第二波 (鎖第一波做第二波·強勢飆股發動)")

    # ----------------------------------------------------
    # 高檔爆量換手成功 (高檔爆量黑K/變盤線後，3天內強勢突破最高點)
    # ----------------------------------------------------
    is_turnover_success = False
    if len(df) >= 5 and is_red and (c >= sma5):
        past4 = df.iloc[-5:-1]
        for _, bar in past4.iterrows():
            b_vol = float(bar['Volume'])
            b_vma5 = float(bar.get('Vol_MA5', b_vol))
            b_is_heavy = (b_vma5 > 0 and b_vol >= b_vma5 * 1.45)
            b_is_black_or_doji = (bar['Close'] <= bar['Open'] * 1.005) or (abs(bar['Close'] - bar['Open']) <= (bar['High'] - bar['Low']) * 0.25)
            if b_is_heavy and b_is_black_or_doji:
                if c > float(bar['High']):
                    is_turnover_success = True
                    break
    if is_turnover_success:
        signals_dict['is_turnover_success'] = True
        signals.append("🔥 換手量成功 (高檔爆量後強勢過高，籌碼換手完畢續噴)")

    # ----------------------------------------------------
    # 假突破誘多出貨 (突破長紅後3天內長黑跌破該長紅最低點)
    # ----------------------------------------------------
    is_false_breakout_dump = False
    if len(df) >= 5:
        past4 = df.iloc[-5:-1]
        for _, bar in past4.iterrows():
            b_vol = float(bar['Volume'])
            b_vma5 = float(bar.get('Vol_MA5', b_vol))
            b_is_red_long = (bar['Close'] > bar['Open']) and (bar['Close'] >= bar['Low'] * 1.02)
            b_is_vol_expand = (b_vma5 > 0 and b_vol >= b_vma5 * 1.2)
            if b_is_red_long and b_is_vol_expand:
                if c < float(bar['Low']) and not is_red:
                    is_false_breakout_dump = True
                    break
    if is_false_breakout_dump:
        signals_dict['is_false_breakout_dump'] = True
        signals.append("🚨 假突破誘多出貨 (突破長紅後3天內跌破最低點，必跑！)")

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
    # 策略 E：高檔起漲 (強勢多頭高檔休息後再發動，非低檔底部起漲)
    # ----------------------------------------------------
    if not signals_dict.get('bottom_breakout', False) and c >= sma60 and sma5 > sma20 and change_pct >= 1.5 and is_red and (c >= df.iloc[-10:-1]['High'].max() * 0.99) and is_5ma_rising:
        signals_dict['high_breakout'] = True
        signals.append("高檔起漲 (多頭高檔突破再創高)")


    # ----------------------------------------------------
    # 策略 F：均線糾結突破 (四線高度糾結放量突破起漲第一根)
    # ----------------------------------------------------
    if len(df) >= 30:
        sub_period = df.iloc[-50:-1] if len(df) >= 50 else df.iloc[:-1]
        rng_max = sub_period['High'].max()
        rng_min = sub_period['Low'].min()
        amplitude = (rng_max - rng_min) / (rng_min + 1e-9)

        # 計算四線糾結度 (5MA, 10MA, 20MA, 60MA)
        ma_list = [sma5, sma10, sma20, sma60] if len(df) >= 60 else [sma5, sma10, sma20]
        max_ma = max(ma_list)
        min_ma = min(ma_list)
        ma_dispersion = (max_ma - min_ma) / (min_ma + 1e-9)

        # 計算歷史均線糾結天數 (逐日回溯 5/10/20/60MA 離散度 <= 6.8%)
        c_series = df['Close']
        s5 = c_series.rolling(5).mean()
        s10 = c_series.rolling(10).mean()
        s20 = c_series.rolling(20).mean()
        s60 = c_series.rolling(60).mean() if len(df) >= 60 else s20
        ma_max_s = pd.concat([s5, s10, s20, s60], axis=1).max(axis=1)
        ma_min_s = pd.concat([s5, s10, s20, s60], axis=1).min(axis=1)
        disp_s = (ma_max_s - ma_min_s) / (ma_min_s + 1e-9)

        sq_bars = 0
        for i in range(len(df) - 2, max(0, len(df) - 150), -1):
            if disp_s.iloc[i] <= 0.068:
                sq_bars += 1
            elif disp_s.iloc[i] <= 0.082 and sq_bars >= 10:
                sq_bars += 1
            else:
                break

        signals_dict['ma_squeeze_bars'] = sq_bars
        signals_dict['ma_squeeze_months'] = round(sq_bars / 20.0, 1)
        signals_dict['is_ma_squeeze_over_2m'] = (sq_bars >= 40)

        # 四線離散在 5.5% 以內（四線高度靠攏平躺），且過去 30~50 天橫盤振幅小於 25% (低檔長期打底)
        is_ma_squeezed = (ma_dispersion <= 0.055) or (abs(sma5 - sma20) / (sma20 + 1e-9) <= 0.038 and abs(sma10 - sma20) / (sma20 + 1e-9) <= 0.038)
        # 一口氣站上/突破四線糾結
        is_standing_all_mas = (c >= sma5 and c >= sma10 and c >= sma20 and c >= (sma60 * 0.992))

        # 助教 10/13 大亞指導：一字底突破收盤必須實質過盤整最高點 (c >= rng_max * 0.995)，且上影線不可過長 (防假突破)
        has_long_upper = signals_dict.get('has_long_upper_shadow', False)
        is_breaking_high = (c >= rng_max * 0.995)
        if (amplitude <= 0.25 or sq_bars >= 30) and (is_ma_squeezed or sq_bars >= 30) and is_standing_all_mas and is_red and is_5ma_rising and is_breaking_high and not has_long_upper and (vol_ratio >= 1.05 or change_pct >= 0.8):
            signals_dict['ma_squeeze_breakout'] = True
            signals_dict['flat_base_breakout'] = True
            if signals_dict['is_ma_squeeze_over_2m']:
                signals.append(f"🌀 四線糾結逾2月突破 (糾結{signals_dict['ma_squeeze_months']}月·老朱翻倍飆股)")
            else:
                signals.append("均線糾結突破 (四線糾結起漲第一根)")

    # ----------------------------------------------------
    # 策略 📦：箱型整理大突破 / 一棒過頂 (經典箱型洗盤蓄勢噴發起漲第一根)
    # 實戰心法鐵律：
    # 1. 過去 12~35 天處於橫盤箱型區間整理 (收盤振幅 <= 20% 或高低振幅 <= 30%)
    # 2. 今日以實體長紅 K 棒 (c >= o 且 c >= sma5) 向上突破過去箱頂最高價 (c >= box_high * 0.995)
    # 3. 操盤線 5MA 走平或向上翻揚 (is_5ma_rising)
    # 4. 洗盤結束、籌碼換手完畢，一棒過頂，通常為波段主升段第一根起漲點！
    # ----------------------------------------------------
    is_box_breakout = False
    if len(df) >= 8:
        for lookback in [6, 8, 10, 12, 16, 20, 25, 30]:
            if len(df) > lookback:
                box_slice = df.iloc[-lookback-1:-1]
                b_max = float(box_slice['High'].max())
                b_min = float(box_slice['Low'].min())
                c_max = float(box_slice['Close'].max())
                c_min = float(box_slice['Close'].min())
                
                hl_amp = (b_max - b_min) / (b_min + 1e-9)
                c_amp = (c_max - c_min) / (c_min + 1e-9)
                
                is_valid_box = (c_amp <= 0.22) or (hl_amp <= 0.32)
                is_breaking = (c >= c_max * 0.998 or c >= b_max * 0.99) and is_red and (c >= sma5) and is_5ma_rising and (change_pct >= 1.0 or vol_ratio_5 >= 1.05 or c > float(prev['High']))
                
                if is_valid_box and is_breaking:
                    is_box_breakout = True
                    break

    if is_box_breakout:
        signals_dict['box_range_breakout'] = True
        signals.append("📦 箱型整理大突破 (一棒過頂·放量衝破箱頂壓力)")
        # 助教 10/22 晶碩 (6491) 指引：盤整突破若伴隨爆量(或留上影線)，要注意後續走勢
        if (vol_ratio_5 >= 1.8 or vol_ratio_20 >= 2.0) and (upper_shadow >= total_range * 0.20 or vol_ratio_5 >= 2.2):
            signals_dict['breakout_heavy_vol_watch_next'] = True
            signals.append("⚠️ 突破爆量留上影 (助教10/22晶碩指引：爆量突破要注意後續走勢，防短線拉回)")
        # CH6-1: 盤整突破是跳空上漲的缺口，力道最強
        if o > prev_h:
            signals_dict['is_gap_breakout'] = True
            signals.append("⚡ 跳空缺口突破 (缺口爆量突破力道最強)")
        # 突破位階勝率評定
        if signals_dict.get('bullish_alignment', False) and (is_main_wave_2nd or signals_dict.get('main_wave_2nd', False)):
            signals_dict['breakout_stage'] = "主升段箱型突破 (四線多排·波段加速)"
        elif is_near_bottom:
            signals_dict['breakout_stage'] = "初升段盤整突破 (勝率高達8成·4線多排)"
        elif is_main_wave_2nd:
            signals_dict['breakout_stage'] = "第二波盤整突破 (勝率高達7成)"
        elif is_high_position:
            signals_dict['breakout_stage'] = "高檔盤整突破 (防假突破/長紅騙線，僅限短線)"
        else:
            signals_dict['breakout_stage'] = "盤整突破 (價漲量增線實)"

    # ----------------------------------------------------
    # 策略 F-2：達瓦斯箱型理論 (Nicolas Darvas Box Theory - 突破開新箱、回測變地板、假突破預警)
    # ----------------------------------------------------
    if len(df) >= 15:
        v_sma5_val = float(df.iloc[-1]['VOL_SMA5']) if ('VOL_SMA5' in df.columns and float(df.iloc[-1]['VOL_SMA5']) > 0) else (float(df.iloc[-5:]['Volume'].mean()) if len(df) >= 5 else 1.0)
        vol_ratio_now = float(df.iloc[-1]['Volume']) / (v_sma5_val + 1e-9)

        found_d_break = False
        d_break_idx = 0
        d_top_f = 0.0
        d_bot_f = 0.0
        for off in range(1, min(9, len(df) - 12)):
            i_b = len(df) - off
            sl_b = df.iloc[max(0, i_b - 25):i_b]
            if len(sl_b) < 12:
                continue
            bt = float(sl_b['High'].max())
            bb = float(sl_b['Low'].min())
            bh = bt - bb
            b_amp = bh / (bb + 1e-9)
            if float(df.iloc[i_b]['Close']) >= bt * 0.998 and b_amp <= 0.32:
                found_d_break = True
                d_break_idx = i_b
                d_top_f = bt
                d_bot_f = bb
                break

        if found_d_break:
            d_box_top = d_top_f
            d_box_bot = d_bot_f
            d_box_h = d_box_top - d_box_bot
            d_box_amp = d_box_h / (d_box_bot + 1e-9)
            d_target_next = round(d_box_top + d_box_h, 2)

            if c < d_box_top * 0.99:
                signals_dict['darvas_false_breakout'] = True
                signals.append("⚠️ 達瓦斯假突破預警 (軟回箱體內·嚴守停損防守)")
                d_status = "⚠️ 跌回箱內假突破"
            elif c >= d_box_top * 0.995 and (l <= d_box_top * 1.025 or float(df.iloc[-2]['Low']) <= d_box_top * 1.025) and c <= d_box_top * 1.06:
                signals_dict['darvas_support_held'] = True
                signals.append("💎 達瓦斯回測有守 (箱頂變新地板·回後買上漲起漲·CH6)")
                d_status = "💎 回測箱頂有守 (新地板起漲)"
            else:
                signals_dict['darvas_breakout'] = True
                signals.append("📦 達瓦斯箱頂突破 (帶量衝破箱頂·開啟新箱子·CH6)")
                d_status = "🔥 帶量突破箱頂 (開新箱子)"
        else:
            lookback_d = min(25, len(df))
            sl_curr = df.iloc[-lookback_d:]
            d_box_top = float(sl_curr['High'].max())
            d_box_bot = float(sl_curr['Low'].min())
            d_box_h = d_box_top - d_box_bot
            d_box_amp = d_box_h / (d_box_bot + 1e-9)
            d_target_next = round(d_box_top + d_box_h, 2)

            if c >= d_box_top * 0.998 and (is_red or vol_ratio_now >= 1.2):
                signals_dict['darvas_breakout'] = True
                signals.append("📦 達瓦斯箱頂突破 (今日放量衝破箱頂·開新箱子·CH6)")
                d_status = "🔥 今日帶量突破箱頂"
            elif c < d_box_bot:
                d_status = "🛑 跌破箱底轉弱"
            else:
                signals_dict['darvas_consolidating'] = True
                d_status = "📦 箱內整理磨盤 (等待方向)"

        signals_dict['darvas_info'] = {
            "box_top": d_box_top,
            "box_bottom": d_box_bot,
            "box_height": round(d_box_h, 2),
            "amplitude_pct": round(d_box_amp * 100, 1),
            "target_d": d_target_next,
            "status": d_status
        }

    # ----------------------------------------------------
    # 策略 G：N字底 vs W底 (雙腳型態精確判定·助教10/14華通/陽明指引)
    # 1. 助教 10/14 華通指引：兩腳 (低點) 落差過大時，不能認定為 W 底，應認定為「N 字底」！
    # 2. 兩腳落差在 4.5% 以內且具雙底打樁：判定為「W底」
    # 3. 助教 10/14 陽明指引：W 底必須在波段低檔打底起漲；若在中高檔或半山腰，屬於「W型態整理」，非「底部型態」！
    # ----------------------------------------------------
    if len(df) >= 20:
        sub = df.iloc[-25:]
        min_idx = sub['Low'].idxmin()
        if min_idx < sub.index[-5]:
            low1 = float(df.loc[min_idx, 'Low'])
            after_low1 = sub.loc[min_idx:]
            if len(after_low1) >= 6:
                peak_idx = after_low1['High'].idxmax()
                if peak_idx > min_idx and peak_idx < sub.index[-2]:
                    peak1 = float(df.loc[peak_idx, 'High'])
                    after_peak = after_low1.loc[peak_idx:]
                    low2 = float(after_peak['Low'].min())
                    gap_pct = (low2 - low1) / (low1 + 1e-9)

                    if low2 >= low1 * 0.985 and c >= sma5 and is_red and c < peak1 * 1.08 and is_5ma_rising:
                        if gap_pct > 0.045:
                            # 助教 10/14 華通指引：二腳落差太大，非 W 底，N 字比較合適！
                            signals_dict['n_pattern_bottom'] = True
                            signals.append("N字底 (第二隻腳顯著墊高·不破前低推升·助教10/14華通指導)")
                        elif abs(gap_pct) <= 0.045:
                            # 兩腳落差在 4.5% 以內，符合正統 W 底 (雙底)
                            signals_dict['w_bottom'] = True
                            if is_near_bottom:
                                signals.append("W底 (雙底對稱有守·低檔底部起漲·助教10/14指導)")
                            else:
                                signals_dict['is_w_pattern_consolidation'] = True
                                signals.append("W型態整理 (半山腰W整理·非低檔底部·助教10/14陽明指引)")

    # ----------------------------------------------------
    # 策略 H：圓弧底 (U型慢火打底·過頸線或底部翻揚·CH6-4)
    # 實戰心法：
    # 1. 股價經過 25~60 天慢火打底洗淨浮額，凹槽最低點在中間，弧度開口向上。
    # 2. 突破頸線：帶量大紅K衝過左右水平頸線 (等距波段目標價 D' = 頸線 + 深度)
    # 3. 打底翻揚：右側回升脫離底部 >= 3%，站上 5MA 翻揚，雙線走平轉強。
    # ----------------------------------------------------
    if len(df) >= 25:
        round_w = min(60, len(df) - 1)
        r_slice = df.iloc[-round_w:]
        y_lows = r_slice['Low'].values
        low_idx_rel = int(np.argmin(y_lows))

        # 凹槽在中間非最近2天
        if 2 <= low_idx_rel <= round_w - 3:
            trough_low = float(y_lows[low_idx_rel])
            left_high = float(r_slice['High'].iloc[:low_idx_rel].max())
            right_high = float(r_slice['High'].iloc[low_idx_rel:].max())
            neckline = max(left_high, right_high)

            depth = (left_high - trough_low) / (trough_low + 1e-9)
            rebound = (c - trough_low) / (trough_low + 1e-9)

            poly = np.polyfit([0, low_idx_rel, round_w - 1], [left_high, trough_low, right_high], 2)
            if poly[0] > 0 and depth >= 0.05:
                # 型態一：放量過頸線起漲
                if c >= neckline * 0.99 and c >= sma5 and (is_red or change_pct >= 0.5):
                    signals_dict['rounding_bottom'] = True
                    signals_dict['rounding_bottom_breakout'] = True
                    signals.append("🥣 圓弧底放量突破 (突破水平頸線·等距對稱波)")
                # 型態二：慢火打底右側翻揚成形
                elif rebound >= 0.03 and c >= sma5 and sma5 >= prev_sma5 * 0.998 and sma20 >= prev_sma20 - 0.20:
                    signals_dict['rounding_bottom'] = True
                    signals_dict['rounding_bottom_breakout'] = False
                    signals.append("🥣 圓弧底慢火打底 (U型慢火打底右側翻揚)")

        # 備用均線平滑兼容
        if not signals_dict.get('rounding_bottom', False):
            ma20_diff_recent = sma20 - prev_sma20
            ma20_diff_old = float(df.iloc[-10]['SMA_20']) - float(df.iloc[-15]['SMA_20'])
            if ma20_diff_old <= 0 and ma20_diff_recent >= -0.05 and c >= sma5 and is_red:
                signals_dict['rounding_bottom'] = True
                signals.append("🥣 圓弧底慢火打底 (20MA平緩翻揚)")

    # ----------------------------------------------------
    # 策略 I：長抱 (均線長期多排穩健上揚)
    # ----------------------------------------------------
    if len(df) >= 20:
        past20_above = (df.iloc[-20:]['Close'] >= df.iloc[-20:]['SMA_20'] * 0.97).sum()
        if past20_above >= 16 and sma5 >= sma20 and sma20 >= sma60:
            signals_dict['long_hold'] = True
            signals.append("長抱 (多頭長線穩健推升)")

    # ----------------------------------------------------
    # 策略 J：一點鐘 (1:00 PM 尾盤選股規則)
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
    # 策略：K線橫盤的突破 (3天橫盤放量長紅突破)
    # 實戰心法鐵律：
    # 1. 過去 3 天收盤價未破第 1 天低點亦未過第 1 天高點 (K線橫盤整理)
    # 2. 今日放量紅K收盤突破前 3 天最高點 (c > max_h3)
    # 3. 站穩 5MA 且 5MA 翻揚 (c >= sma5 and is_5ma_rising)
    # ----------------------------------------------------
    if len(df) >= 4 and is_red and c >= sma5 and is_5ma_rising:
        past3 = df.iloc[-4:-1]
        h3 = float(past3['High'].max())
        l3 = float(past3['Low'].min())
        amp3 = (h3 - l3) / (l3 + 1e-9)
        if amp3 <= 0.065 and c > h3 and (vol_ratio_5 >= 1.05 or change_pct >= 1.0):
            signals_dict['kline_consolidation_breakout'] = True
            signals.append("📊 K線橫盤突破 (3天橫盤放量突破)")

    # ----------------------------------------------------
    # 策略：突破 ABC 修正下降切線 (短空做頭失敗反手多)
    # 實戰心法鐵律：
    # 1. 前波多頭推升後，出現 ABC 向下三波修正 (飄旗型態，時程在 20 天之內)
    # 2. 20MA 月線維持上揚 (sma20 >= prev_sma20 * 0.998)
    # 3. 今日大量中長紅 K 突破下降切線，短空做頭失敗，反手做多！
    # ----------------------------------------------------
    if len(df) >= 12 and is_red and c >= sma5 and is_5ma_rising and sma20 >= prev_sma20 * 0.998:
        sub_abc = df.iloc[-20:-1] if len(df) >= 20 else df.iloc[:-1]
        high_idx = sub_abc['High'].idxmax()
        if high_idx < sub_abc.index[-2]:
            after_h = sub_abc.loc[high_idx:]
            if len(after_h) >= 3:
                # 助教與老朱實戰心法：ABC 必須有「底底低轉短空」之回檔旗形特性
                # 若拉回期間低點未破 (底底平或底底高)，屬於水平箱型整理，不可誤判為 ABC 下降切線！
                after_lows = after_h['Low']
                mid_pt = max(1, len(after_lows) // 2)
                mid_low = float(after_lows.iloc[:mid_pt].min())
                late_low = float(after_lows.iloc[mid_pt:].min())
                has_descending_troughs = (late_low < mid_low * 0.992)

                b_peak = float(after_h.iloc[1:-1]['High'].max()) if len(after_h) > 2 else float(after_h['High'].mean())
                if has_descending_troughs and c > b_peak and (vol_ratio_5 >= 1.05 or change_pct >= 1.0):
                    signals_dict['abc_correction_breakout'] = True
                    signals.append("📐 突破ABC修正切線 (短空做頭失敗反手多)")

    # ----------------------------------------------------
    # 策略：突破上升軌道線 (多頭加速噴出)
    # 實戰心法鐵律：
    # 1. 多頭沿著上升軌道線緩步推升 (5MA > 20MA > 60MA)
    # 2. 今日大量中長紅 K 收盤突破上升軌道線頂部，多頭轉強加速噴出！
    # ----------------------------------------------------
    if len(df) >= 20 and is_bull and is_red and (c >= sma5) and is_5ma_rising and change_pct >= 2.0 and vol_ratio_5 >= 1.25:
        past15 = df.iloc[-16:-1]
        upper_bound = float(past15['High'].max())
        if c >= upper_bound * 1.005:
            signals_dict['ascending_channel_breakout'] = True
            signals.append("🚀 突破上升軌道線 (多頭加速噴出)")

    # ----------------------------------------------------
    # 策略：突破飆股大量黑K最高點 (洗盤換手突破起漲)
    # 實戰心法鐵律：
    # 1. 過去 1~3 天曾出現大量黑 K 或長避雷針回檔洗盤 (Volume >= Vol_MA5 * 1.25)
    # 2. 20MA 月線維持上揚 (sma20 >= prev_sma20 * 0.998)
    # 3. 今日大量中長紅 K 收盤突破該下跌黑 K 的最高點，多頭換手再轉強！
    # ----------------------------------------------------
    if len(df) >= 5 and is_red and (c >= sma5) and is_5ma_rising and sma20 >= prev_sma20 * 0.998:
        past3_bars = df.iloc[-4:-1]
        for _, b_row in past3_bars.iterrows():
            b_v = float(b_row['Volume'])
            b_vma = float(b_row.get('Vol_MA5', b_v))
            b_is_black = (float(b_row['Close']) < float(b_row['Open'])) or (float(b_row['High']) - float(b_row['Close']) >= (float(b_row['Close']) - float(b_row['Low'])) * 0.7)
            if b_vma > 0 and b_v >= b_vma * 1.2 and b_is_black:
                if c > float(b_row['High']):
                    signals_dict['breakout_heavy_black_high'] = True
                    if is_high_position or is_multi_bagger:
                        signals_dict['breakout_heavy_black_high_pos_warning'] = True
                        signals.append("⚡ 突破大量黑K高點 (助教10/22冠西電指引：符合進場點，但位置有點高要注意，採短線守5MA)")
                    else:
                        signals.append("⚡ 突破大量黑K高點 (飆股換手突破起漲)")
                    break

    # ----------------------------------------------------
    # 強勢連三紅 (朱家泓老師達人秀強勢股基因：反彈連三紅 或 突破上漲連三紅)
    # 實戰心法：
    # 1. 最近連續 3 根 K 棒收盤價大於等於開盤價 (收紅K)
    # 2. 收盤價重心逐日墊高 (c > prev_c > prev2_c)
    # 3. 站穩 5MA 操盤線且 5MA 翻揚助漲
    # ----------------------------------------------------
    is_consecutive_three_reds = False
    if len(df) >= 3:
        b0 = df.iloc[-1]
        b1 = df.iloc[-2]
        b2 = df.iloc[-3]
        all_red = (float(b0['Close']) >= float(b0['Open'])) and (float(b1['Close']) >= float(b1['Open'])) and (float(b2['Close']) >= float(b2['Open']))
        higher_closes = (float(b0['Close']) > float(b1['Close']) and float(b1['Close']) > float(b2['Close']))
        if all_red and higher_closes and (c >= sma5) and is_5ma_rising:
            is_consecutive_three_reds = True
    signals_dict['consecutive_three_reds'] = is_consecutive_three_reds
    if is_consecutive_three_reds:
        signals.append("🔥 強勢連三紅 (連續三紅K重心墊高·朱老師飆股基因)")

    # ----------------------------------------------------
    # 策略 🏆：底部反轉強勢多頭 (朱家泓老師《理財達人秀》標準 5 步驟 SOP)
    # SOP 條件：
    # 1. 底部大量反彈，走出底底高打底 (或過去 40 天有扎實低點支撐)
    # 2. 底部 1~2 個月 (20~45天) 橫盤打底整理，均線糾結或形成三線/四線多頭排列
    # 3. 突破盤底高點 (過整理區頸線)
    # 4. 反彈連三紅 或 突破上漲連三紅 (強勢股表現)
    # 5. 5MA 翻揚助漲且站穩 5MA 之上
    # 案例：穩懋 (3105)、中美晶 (5483)
    # ----------------------------------------------------
    is_bottom_reversal = False
    if len(df) >= 20 and c >= sma5 and is_5ma_rising:
        sub_base = df.iloc[-50:-1] if len(df) >= 50 else df.iloc[:-1]
        base_low = float(sub_base['Low'].min())
        base_high = float(sub_base['High'].max())
        
        # 低檔判定：現價距離基期低點不超過 32%，或均線在低檔
        is_at_base = (c <= base_low * 1.32) or (sma20 <= sma60 * 1.05) or signals_dict.get('is_cons_over_2m', False) or (signals_dict.get('ma_squeeze_bars', 0) >= 15)

        # 均線形態：三線或四線多排 (sma5 >= sma20 且 20MA 走平翻揚)
        has_3ma_aligned = (sma5 >= sma20 and sma20 >= prev_sma20 * 0.998)
        if 'SMA_10' in df:
            has_3ma_aligned = has_3ma_aligned and (sma5 >= float(df.iloc[-1]['SMA_10']))

        # 突破盤底高點：突破過去 15~40 天的收盤高點或最高點 99%
        recent_box = df.iloc[-35:-1] if len(df) >= 35 else df.iloc[:-1]
        neckline_high = float(recent_box['Close'].max())
        is_breaking_neckline = (c >= neckline_high * 0.995) or signals_dict.get('box_range_breakout', False) or signals_dict.get('bottom_breakout', False)

        # 連三紅 或 突破攻擊長紅
        is_three_reds_or_attack = is_consecutive_three_reds or (is_red and (change_pct >= 1.2 or vol_ratio_5 >= 1.2))

        # 底底高打底
        has_higher_low_base = trend_info.get('higher_lows', False) or (float(df.iloc[-5:]['Low'].min()) >= base_low * 1.01)

        if is_at_base and has_3ma_aligned and is_breaking_neckline and is_three_reds_or_attack and has_higher_low_base:
            is_bottom_reversal = True

    signals_dict['bottom_reversal_strong_bull'] = is_bottom_reversal
    if is_bottom_reversal:
        signals.append("🔥 底部反轉強勢多頭 (1~2月打底·連三紅突破·朱老師SOP)")

    # ----------------------------------------------------
    # 警示：四線尚未做好 / 均線未理順 (朱家泓老師達人秀盲點警示：東台 4526、漢磊 3707 案例)
    # 盲點特徵：
    # 1. 低檔出現反彈或帶量長紅突破，吸引學員急躁進場
    # 2. 但 60MA (季線) 仍顯著下彎助跌 (SMA60 < prev_SMA60)
    # 3. 或 20MA/60MA 仍呈空頭排列 (SMA20 < SMA60 * 0.985)，上方存在大量套牢與均線反壓！
    # 實戰心法：宜列入鎖股名單觀察，等待均線理順或打第二隻腳，切忌第一根急躁重倉。
    # ----------------------------------------------------
    four_ma_not_ready = False
    if len(df) >= 40:
        prev_sma60 = float(df.iloc[-2].get('SMA_60', sma60))
        is_60ma_falling = (sma60 < prev_sma60 * 0.999)
        # 處於反彈或剛放量突破嘗試
        is_rebound_attempt = (c >= sma5 and is_red) or (vol_ratio >= 1.15)
        # 均線未理順：20MA 仍小於 60MA 且季線下彎助跌
        if is_60ma_falling and (sma20 < sma60 * 0.985) and is_rebound_attempt:
            four_ma_not_ready = True

    signals_dict['four_ma_not_ready_warning'] = four_ma_not_ready
    if four_ma_not_ready:
        signals.append("⚠️ 四線尚未做好 (季線下彎助跌·上方均線反壓·朱老師提醒切勿急躁重倉)")

    # ====================================================
    # 做空波段與即時策略 (空方體系)
    # ====================================================
    is_black = (c < o)
    is_5ma_falling = (sma5 <= prev_sma5)
    is_bear = bool(trend_info.get('lower_highs', False) and trend_info.get('lower_lows', False)) or trend_info.get('trend_status', '').startswith('空頭')

    # 策略 A_空：頭低底低 (六字訣空頭確認)
    if is_bear and c <= sma5 and is_5ma_falling:
        signals_dict['lower_highs_lows'] = True
        signals.append("頭低底低 (空頭走勢確認)")

    # 策略 B_空：雙線死亡交叉 / 雙線下彎 (5MA 向下穿過 20MA 或雙線同步下彎)
    is_death_cross_today = (sma5 <= sma20 and prev_sma5 >= prev_sma20 and is_5ma_falling)
    is_death_cross_recent = (sma5 <= sma20 and float(prev2['SMA_5']) >= float(prev2['SMA_20']) and is_5ma_falling) if len(df) > 2 else False
    is_dual_ma_falling = (sma5 < sma20 and is_5ma_falling and sma20 <= prev_sma20)
    if is_death_cross_today or is_death_cross_recent or is_dual_ma_falling:
        signals_dict['death_cross_5_20'] = True
        signals.append("雙線死亡交叉/雙線下彎 (5MA向下跌破20MA或同步下彎)")

    # 策略 C_空：彈後準進場 (弱勢反彈測線無力，轉折黑K空點)
    recent_highs = df.iloc[-4:-1]['High'].max() if len(df) >= 4 else h
    tested_res_or_ma = (recent_highs >= sma20 * 0.98 or h >= sma5 * 0.99)
    res_val = trend_info.get('resistance', 0) or (c * 1.08)
    not_broken_res = h <= res_val * 1.015
    is_5ma_falling_or_turn = is_5ma_falling or (c <= sma5 and sma5 <= prev_sma5 * 1.01) or (sma20 <= prev_sma20 and c <= sma5)

    # 助教 10/25 旺宏 (2337) 權威過濾器：「K線橫盤還沒跌破，不是彈後空進場點！」
    # 檢查近 4~7 天是否處於 K 線橫盤區間內，且今日收盤價 c 尚未實質跌破橫盤區間下緣 (l_cons)
    is_trapped_in_kline_cons = False
    if len(df) >= 5 and is_black and c <= sma5:
        cons_win = df.iloc[-6:-1] if len(df) >= 6 else df.iloc[-4:-1]
        h_cons = float(cons_win['High'].max())
        l_cons = float(cons_win['Low'].min())
        amp_cons = (h_cons - l_cons) / (l_cons + 1e-9)
        if amp_cons <= 0.068 and c >= l_cons * 0.997:
            is_trapped_in_kline_cons = True

    if (is_bear or sma5 <= sma20) and tested_res_or_ma and not_broken_res and is_black and c <= sma5 and is_5ma_falling_or_turn:
        if is_trapped_in_kline_cons:
            signals_dict['kline_consolidation_not_broken_no_short'] = True
            signals.append("⏸️ K線橫盤還沒跌破 (助教10/25旺宏指引：雖碰5均後收黑K，但K線橫盤尚未跌破，非做空進場點)")
        else:
            signals_dict['rebound_short'] = True
            signals.append("彈後準進場 (反彈測線無力，轉折黑K跌破5MA)")
            # 助教 10/23 京元電子 (2449) 指引：彈後空下跌若離下方支撐較近 (<= 4.5%)，提醒注意支撐止跌
            if support > 0 and c > support and ((c - support) / (c + 1e-9)) <= 0.045:
                signals_dict['rebound_short_near_support'] = True
                signals.append("⚠️ 彈後空離支撐近 (助教10/23京元電指引：與時間無關指價差空間近，可做空但遇支撐須注意止跌)")
            # 助教 10/25 華新科 (2492) 指引：頭頭低/破前低位置屬彈後空下跌，但月線仍向上、均線未空排
            if sma20 > prev_sma20 * 1.0005:
                signals_dict['rebound_short_ma20_still_rising_warning'] = True
                signals.append("⚠️ 位置彈後空但月線仍向上 (助教10/25華新科指引：多單早該於頭頭低/破前低出場；目前彈後空但月線仍向上未空排，留意月線扣抵支撐)")

    # 助教 10/25 金居 (8358) & 10/27 指引：空頭確認/急跌剛碰到季線(60MA)或支撐區，要看季線是否有撐，建議等彈後空下跌更穩
    if (is_bear or c < sma20) and is_black and change_pct <= -3.0:
        near_ma60_sup = (sma60 > 0 and abs(c - sma60) / (sma60 + 1e-9) <= 0.032) or (l <= sma60 <= h)
        near_prev_sup = (support > 0 and abs(c - support) / (support + 1e-9) <= 0.030)
        if near_ma60_sup or near_prev_sup:
            signals_dict['bear_confirm_at_ma60_support_wait_bounce'] = True
            signals.append("⚠️ 空頭急跌剛碰季線/支撐 (助教10/25金居&10/27指引：要看季線/支撐是否有撐，僅能短線操作；建議等反彈後再做彈後空下跌更穩)")

    # 助教 10/25 美股 PG 寶僑指引：左長紅右長黑是變盤徵兆，注意下一個交易日是否跌破5日線；低位階未破5均與停損續抱觀察
    if is_prev_large_red and is_black:
        signals_dict['left_red_right_black_watch_5ma'] = True
        if c >= sma5 and not is_high_position and c >= support * 0.99:
            signals_dict['left_red_right_black_low_pos_hold'] = True
            signals.append("👀 左長紅右長黑變盤徵兆·未破5均續抱觀察 (助教10/25寶僑PG指引：左長紅右長黑注意次日是否破5日線；目前位階不高且未破5均與停損，守停損觀察)")
        else:
            signals.append("⚠️ 左長紅右長黑變盤徵兆 (助教10/25指引：注意下一個交易日是否跌破5日線，破5均確認轉弱出場)")

    # 林穎老師 10/25 技術分析影片指引：長紅突破站上 20MA，但 20MA 方向向下，須承受隔天、隔兩天股價不漲的狀況
    if is_red and c >= sma20 and (c > prev_h or change_pct >= 2.2) and (sma20 < prev_sma20 * 0.9995):
        signals_dict['breakout_20ma_falling_stall_warning'] = True
        signals.append("⏳ 站上20MA但20MA向下·防隔兩天不漲 (林穎老師10/25影片指引：收盤在20MA上但20MA方向向下，須承受隔天、隔兩天股價不漲；待20MA向上才易主升急噴)")

    # 助教 10/25 台光電 (2383) 指引：盤中過高收盤未過＝假的過高（壓力未被突破，上影線即壓力）
    if trend_info.get('unconfirmed_shadow_high_pierce', False):
        signals_dict['fake_high_intraday_pierce_only'] = True
        signals.append("⚠️ 盤中過高收盤未過＝假過高 (助教10/25台光電指引：確認過高看收盤價，上影線即壓力；若未補量收盤過高反破5MA，實質為矩形盤整/頭頭低先賣)")

    # 助教 10/23 臻鼎-KY (4958) 指引：多頭回檔以「三天二缺口」方式急跌疑似出貨 & 向上跳空後又跳空回來
    if len(df) >= 5:
        recent4_bars = df.iloc[-4:]
        down_gaps_3d = 0
        for g_i in range(1, len(recent4_bars)):
            if float(recent4_bars.iloc[g_i]['High']) < float(recent4_bars.iloc[g_i - 1]['Low']):
                down_gaps_3d += 1
        if down_gaps_3d >= 2:
            signals_dict['three_days_two_gaps_down_warning'] = True
            signals.append("🚨 多頭回檔三天二缺口 (助教10/23臻鼎-KY指引：多頭回檔以三天二缺口方式急跌，有可能是主力出貨)")
        if len(df) >= 12 and down_gaps_3d >= 1:
            prior10 = df.iloc[-12:-2]
            had_up_gap = any(float(prior10.iloc[k]['Low']) > float(prior10.iloc[k - 1]['High']) for k in range(1, len(prior10)))
            if had_up_gap and is_black:
                signals_dict['gap_up_then_gap_down_reversal'] = True
                signals.append("⚠️ 向上跳空後又跳空回來 (助教10/23臻鼎-KY指引：防島狀反轉或M頭主力出貨)")

    # 助教 10/23 南亞 (1303) 指引：長黑吞噬跌破 5 均轉盤整，但若還在月線上可鎖多頭 ABC
    if signals_dict.get('bearish_engulfing', False) and c < sma5 and c >= sma20 and (sma20 >= prev_sma20 * 0.998):
        signals_dict['bearish_engulf_to_abc_watch'] = True
        signals.append("💡 長黑吞噬破5均轉盤整·守月線上鎖多頭ABC (助教10/23南亞指引：短線先出場，目前盤整等突破，破低轉空，若還在月線上鎖多頭ABC)")

    # 助教 10/29 達航科技 (4577) 指引：波段已漲過一成 (>10%)，昨日黑K大量今日紅K大量覆蓋黑K，「看訊號，準備停利」切忌追高
    if is_red and prev_c < float(prev['Open']) and vol_ratio >= 1.5 and c >= float(prev['High']):
        swing_g = float(signals_dict.get('swing_gain', 0.0))
        if swing_g >= 10.0 or (c >= sma20 * 1.10):
            signals_dict['gain_over_10pct_take_profit_alert'] = True
            signals.append("🎯 漲過一成遇大量長紅吞噬·看訊號準備停利 (助教10/29達航指引：波段累計漲逾10%，高檔爆量長紅覆蓋黑K防主力拉高，看訊號準備停利出場，切忌追高！)")

    # 助教 10/29 群聯 (8299) 指引：箱型整理震盪，建議等帶量突破區間再進，在區間操作常一直停損
    if trend_info.get('trend_status') == "盤整趨勢" and not signals_dict.get('box_range_breakout', False) and not signals_dict.get('darvas_breakout', False):
        signals_dict['box_in_range_warning'] = True
        signals.append("⚠️ 箱型整理區間內震盪 (助教10/29群聯指引：建議以突破區間為進場依據，在區間內操作常一直停損，耐心等帶量突破！)")

    # 助教 10/29 大盤指引：轉折是訊號不是進場位置與條件（空頭或月線下彎出晨星轉折，嚴禁盲目進場做多）
    if signals_dict.get('morning_star', False) or signals_dict.get('hammer', False):
        if c < sma20 or sma20 < prev_sma20 * 0.9995:
            signals_dict['rebound_signal_not_entry_warning'] = True
            signals.append("⚠️ 轉折是訊號非進場條件 (助教10/29大盤指引：月線下或月線下彎出晨星/變盤線只是轉強訊號，非做多進場條件，量縮上攻無力防假反彈！)")

    # 助教 10/29 旭隼 (6409) 指引：長紅突破次日收黑留下影線，黑K可當回測（未破停損），守原停損續抱
    if len(df) >= 3:
        p2 = df.iloc[-2]
        p2_c = float(p2['Close'])
        p2_o = float(p2['Open'])
        p2_l = float(p2['Low'])
        p2_is_big_red = (p2_c >= p2_o * 1.03) or (float(p2.get('change_pct', 0)) >= 3.5)
        if p2_is_big_red and is_black and c >= p2_l:
            lower_shadow = min(o, c) - l
            body = abs(c - o)
            if lower_shadow >= body * 0.8:
                signals_dict['breakout_next_day_shadow_pullback'] = True
                signals.append("🛡️ 突破次日黑K下影線回測 (助教10/29旭隼指引：長紅突破次日黑K有下影線可視為支撐回測，未破停損續抱)")

    # 助教 10/30 華新科 (2492) / 頎邦 (6147) 指引：遭遇「二個頭壓」未過壓前不操作
    peaks_list = trend_info.get('peaks', [])
    overhead_peaks = [p for p in peaks_list if float(p.get('price', 0)) > c * 1.002]
    if len(overhead_peaks) >= 2:
        p1 = float(overhead_peaks[-1]['price'])
        p2 = float(overhead_peaks[-2]['price'])
        # 距離最近的頭部壓在 3.5% 以內
        if (min(p1, p2) - c) / c <= 0.035:
            signals_dict['two_peaks_resistance_alert'] = True
            signals.append(f"⚠️ 遭遇二個頭部重壓 (前波 {p2:.2f}元 與 {p1:.2f}元 雙頭套牢反壓，助教10/30指引：過壓前不操作！)")

    # 助教 10/30 百一 (6152) 指引：突破攻擊量若明顯小於前波套牢壓力量，動能不足防高點受阻
    if (signals_dict.get('abc_correction_breakout', False) or signals_dict.get('box_range_breakout', False)) and len(df) >= 20:
        prior_vol_max = float(df.iloc[-25:-5]['Volume'].max())
        if prior_vol_max > 0 and v < prior_vol_max * 0.7:
            signals_dict['low_vol_breakout_vs_pressure_alert'] = True
            signals.append("⚠️ 攻擊量小於前波套牢量 (助教10/30百一指引：突破量能小於壓力量，不確定高點是否能到，需補量)")

    # 助教 10/30 佳世達 (2352) 指引：爆量如果是低點後續過高，比過高當日爆量安心
    if signals_dict.get('ma_squeeze_breakout', False) or signals_dict.get('box_range_breakout', False):
        if len(df) >= 15:
            prior_low_vol = df.iloc[-15:-1]['Volume'].max()
            if prior_low_vol >= v_ma20 * 1.8:
                signals_dict['bottom_volume_better_than_breakout'] = True
                signals.append("💡 底部爆量洗淨後續過高 (助教10/30佳世達指引：低點爆量後續過高，籌碼扎實安心起漲)")

    # 助教 11/02 東捷資訊 (6697) 指引：突破進場次日是否持續向上走，黑K就不太對了
    if len(df) >= 3:
        p2 = df.iloc[-2]
        p2_c = float(p2['Close'])
        p2_o = float(p2['Open'])
        p2_h = float(p2['High'])
        p2_is_breakout = (p2_c >= p2_o * 1.03 or float(p2.get('change_pct', 0)) >= 3.0) and (p2_c >= float(df.iloc[-10:-2]['High'].max()) * 0.998)
        if p2_is_breakout and is_black and c < p2_c:
            signals_dict['breakout_next_day_black_warning'] = True
            signals.append("⚠️ 進場次日收黑走勢不對 (助教11/02東捷指引：突破次日必須延續向上，收黑K走勢不太對，嚴守保本停損！)")

    # 助教 11/02 國巨 (2327) 指引：剛跌破長期支撐位置不可直接追空，防跌深強彈
    if len(df) >= 60:
        long_term_low = float(df.iloc[-120:-5]['Low'].min())
        if c <= long_term_low * 1.015 and c >= long_term_low * 0.97 and is_black:
            signals_dict['near_long_term_support_no_short'] = True
            signals.append("⚠️ 剛跌破長期支撐不可追空 (助教11/02國巨指引：跌破長期支撐防技術強彈，等彈後空下跌再進！)")

    # 助教 11/02 光寶科 (惡哩俠) 指引：N字底突破前高確立，為多頭起漲第一根
    if trend_info.get('bottom_type') == "N字底" or signals_dict.get('bottom_breakout', False):
        if is_red and change_pct >= 2.0 and c > float(prev['High']):
            signals_dict['n_shape_bottom_breakout'] = True
            signals.append("🚀 N字底型態確立·多頭起漲第一根 (助教11/02指引：收盤突破前高確立N字底，標準做多起漲買點！)")

    # 助教 11/02 榮科 (4989) 指引：寬幅大區間內部轉折不看，抓高低點出來觀察就好
    if trend_info.get('trend_status') == "盤整趨勢" and len(df) >= 30:
        high_30 = float(df.iloc[-30:]['High'].max())
        low_30 = float(df.iloc[-30:]['Low'].min())
        if (high_30 - low_30) / low_30 >= 0.15 and low_30 * 1.04 < c < high_30 * 0.96:
            signals_dict['wide_range_box_ignore_minor_turns'] = True
            signals.append("📦 大區間內部轉折不看 (助教11/02榮科指引：大區間內細部轉折不看，抓高低點出來觀察就好！)")

    # 助教 11/03 大盤指引：凹洞量嚴格定義（今日成交量 <= 昨日成交量二分之一以下，且止跌）
    if prev_v > 0 and v <= prev_v * 0.50 and abs(change_pct) <= 2.5:
        signals_dict['is_cavity_vol_valid'] = True
        signals.append("🕳️ 凹洞量成立 (助教11/03大盤指引：今日量<=昨日量50%以下，待明日補量確認起漲！)")

    # 助教 11/03 鼎固-KY (2923) / 華廣 (4737) 指引：選股流動性門檻建議至少 500 張（最好 1000 張以上）
    if v_ma20 > 0 and v_ma20 < 500:
        signals_dict['low_liquidity_risk_under_500'] = True
        signals.append("⚠️ 流動性不足 500 張 (助教11/03指引：均量不足500張易劇烈滑價，嚴防流通性風險！)")

    # 助教 11/03 協易機 (4533) 指引：大敵當前多根上影線，上有重壓可以選擇不進場
    if len(df) >= 4:
        recent3_bars = df.iloc[-4:-1]
        shadow_count = sum(1 for idx, b in recent3_bars.iterrows() if (float(b['High']) - max(float(b['Open']), float(b['Close']))) >= abs(float(b['Close']) - float(b['Open'])) * 0.7)
        if shadow_count >= 2 and (signals_dict.get('pullback_buy', False) or c >= sma5):
            signals_dict['heavy_upper_shadows_enemy_ahead'] = True
            signals.append("⚠️ 大敵當前賣壓沉重 (助教11/03協易機指引：前幾天多根長上影線有大壓，可以選擇不進場！)")

    # 助教 11/03 華廣 (4737) 指引：突破次日大跌是很奇怪的一件事，防假突破倒貨
    if len(df) >= 3:
        p2 = df.iloc[-2]
        p2_c = float(p2['Close'])
        p2_o = float(p2['Open'])
        if (p2_c >= p2_o * 1.05 or float(p2.get('change_pct', 0)) >= 5.0) and change_pct <= -5.0 and is_black:
            signals_dict['breakout_next_day_crash_anomaly'] = True
            signals.append("🚨 突破次日大跌異常 (助教11/03華廣指引：突破次日大跌是很奇怪的一件事，防假突破摜殺！)")

    # 助教 11/04 華新(1605)/全球傳動(4540)指引：下跌連三黑也是波段低檔，反彈機率高，不可低檔盲目追空
    if len(df) >= 3:
        last3 = df.iloc[-3:]
        all_3_black = all(float(b['Close']) < float(b['Open']) for _, b in last3.iterrows())
        cum_fall = (float(df.iloc[-1]['Close']) - float(df.iloc[-3]['Open'])) / (float(df.iloc[-3]['Open']) + 1e-9) * 100
        if all_3_black and cum_fall <= -3.0:
            signals_dict['consecutive_3_black_rebound_risk'] = True
            signals.append("⚠️ 下跌連三黑波段低檔防反彈 (助教11/04指引：連三黑反彈機率高勿低檔追空)")

    # 助教 11/04 指引：不可省略前面的壓力自己找位子進場！頂到前高帶上影線為受阻訊號
    if len(df) >= 15:
        prev_high_20 = float(df.iloc[-20:-2]['High'].max())
        curr_h = float(last['High'])
        curr_c = float(last['Close'])
        curr_o = float(last['Open'])
        upper_shadow = curr_h - max(curr_o, curr_c)
        body = abs(curr_c - curr_o)
        if prev_high_20 > 0 and (abs(curr_h - prev_high_20) / prev_high_20 <= 0.035 or curr_h >= prev_high_20 * 0.985):
            if upper_shadow >= max(body * 0.4, curr_c * 0.008):
                signals_dict['overhead_resistance_too_close_trap'] = True
                signals.append("⚠️ 上方前高受阻大壓力 (助教11/04指引：不可省略前面壓力自己找位子進場，上影線為變盤訊號)")

    # 助教 11/04 南亞科/大盤指引：到了滿足點並不表示止跌，要有所跌訊號跟紅K確認！
    if is_black and change_pct <= -2.0 and c <= sma20:
        signals_dict['target_met_awaiting_reversal'] = True

    # 助教 11/06 晉泰(6221)指引：低檔起漲已大漲，高檔爆大量長上影線未過前高，主力拉高出貨嚴禁追多
    if len(df) >= 30:
        lowest_60 = float(df.iloc[-60:-5]['Low'].min()) if len(df) >= 60 else float(df['Low'].min())
        if lowest_60 > 0 and (c / lowest_60) >= 1.5:
            recent5 = df.iloc[-5:-1]
            has_heavy_shadow = any(
                (float(b['High']) - max(float(b['Open']), float(b['Close']))) >= abs(float(b['Close']) - float(b['Open'])) * 1.2
                and float(b['Volume']) >= v_ma5 * 1.3
                for _, b in recent5.iterrows()
            )
            prev_top = float(recent5['High'].max())
            if has_heavy_shadow and h < prev_top:
                signals_dict['high_shadow_doubled_stock_risk'] = True
                signals.append("⚠️ 翻倍股高檔爆量上影線未過 (助教11/06晉泰指引：起漲已翻倍，高檔爆量長上影未過前高嚴禁追多)")

    # 助教 11/06 華城(1519)指引：空頭跌深在低檔等反彈，目前不適用急追加空，須等反彈站上5均再跌破
    if trend_info.get('trend') == '空頭' and sma5 < sma20:
        if len(df) >= 5:
            cum_5d_fall = (c - float(df.iloc[-5]['Open'])) / (float(df.iloc[-5]['Open']) + 1e-9) * 100
            if cum_5d_fall <= -8.0 and not is_black:
                signals_dict['rebound_waiting_for_bounce_short'] = True
                signals.append("⚠️ 低檔等反彈不急加空 (助教11/06華城指引：空頭跌深等站上5均後再跌破之彈後空)")

    # 助教 11/06 趨勢指引：單看紅K是回後買上漲，隨後黑K跌破昨低才確認頭頭低
    if is_black and c < prev_l and c < sma5 and prev_c >= float(prev.get('SMA_5', prev_c)):
        signals_dict['trend_turn_lower_high_confirmed'] = True
        signals.append("🚨 黑K跌破確認頭頭低 (助教11/06指引：單看紅K回後買，黑K跌破才確認頭頭低，紀律停損)")

    # 助教 11/10 啟碁(6285) & 大盤指引：搶 V 轉四大訊號 (急跌 + 年線/半年線重要支撐 + 止跌大量 + 紅K過高)
    if is_red and c > prev_h:
        is_deep_fall = False
        if len(df) >= 6:
            fall_5d = (c - float(df.iloc[-6]['Open'])) / (float(df.iloc[-6]['Open']) + 1e-9) * 100
            if fall_5d <= -6.0 or (c < sma20 and c < sma60):
                is_deep_fall = True
        hit_major_support = False
        if 'SMA_240' in last and not pd.isna(last['SMA_240']):
            sma240 = float(last['SMA_240'])
            if l <= sma240 * 1.025 and c >= sma240 * 0.98:
                hit_major_support = True
        elif 'SMA_120' in last and not pd.isna(last['SMA_120']):
            sma120 = float(last['SMA_120'])
            if l <= sma120 * 1.025 and c >= sma120 * 0.98:
                hit_major_support = True
        elif len(df) >= 30:
            past_low = float(df.iloc[-30:-5]['Low'].min())
            if l <= past_low * 1.02 and c >= past_low * 0.98:
                hit_major_support = True
        has_stop_fall_vol = (vol_ratio >= 1.3) or (float(prev['Volume']) >= float(prev.get('Volume_MA5', v_ma5)) * 1.3)

        if is_deep_fall and hit_major_support and has_stop_fall_vol:
            signals_dict['v_reversal_rebound_setup'] = True
            signals.append("⚡ 搶V轉四大訊號成立 (助教11/10啟碁指引：急跌+重要支撐+止跌大量+紅K過高，逆勢單嚴守停損3%~5%)")

    # 助教 11/10 景碩(3189) & 欣興(3037)指引：突破前日高點必須包含上影線 (未過最高價不符進場條件)
    if is_red and c > prev_c and c < prev_h:
        signals_dict['breakout_high_must_include_shadow'] = True
        signals.append("⚠️ 未過前日高點上影線 (助教11/10景碩/欣興指引：過昨高必須過最高價上影線，否則不符進場條件)")

    # 助教 11/10 金山電(8042)指引：空頭趨勢指標收斂非反轉 (月線下彎空排絕不做多)
    is_bearish_trend = (trend_info.get('trend') == '空頭') or (c < sma20 and sma20 < prev_sma20)
    has_indicator_bounce = False
    if 'KD_K' in last and 'KD_D' in last:
        has_indicator_bounce = float(last['KD_K']) > float(last['KD_D']) and float(prev.get('KD_K', 0)) <= float(prev.get('KD_D', 0))
    if is_bearish_trend and (has_indicator_bounce or signals_dict.get('abc_correction_breakout', False)):
        signals_dict['bearish_indicator_rebound_trap'] = True
        signals.append("🚨 空頭指標收斂誘多陷阱 (助教11/10金山電指引：月線下彎空頭排列，指標金叉/破切僅為空頭反彈，絕不做多)")

    # 助教 11/10 光聖(6442)指引：爆量不一定是紅K本身，止跌大量過高為準
    if len(df) >= 4 and is_red:
        recent3 = df.iloc[-4:-1]
        heavy_bars = recent3[recent3['Volume'] >= v_ma5 * 1.5]
        if not heavy_bars.empty:
            max_heavy_h = float(heavy_bars['High'].max())
            if c >= max_heavy_h:
                signals_dict['stop_fall_vol_not_limited_to_red'] = True
                signals.append("💡 突破止跌大量K線高點 (助教11/10光聖指引：爆量不限紅黑，越過止跌大量高點即為轉強訊號)")

    # 助教 11/11 晶宏(3141)指引：突破季線但未成底底高 (單腳急拉未打底，等第二隻腳回測有守再進)
    if 'SMA_60' in last and not pd.isna(last['SMA_60']):
        sma60 = float(last['SMA_60'])
        if is_red and c >= sma60 and prev_c < sma60:
            # 檢視近 15 天是否有實質第二隻腳 (兩個顯著波谷且底底高)
            has_two_legs = False
            if trend_info and 'troughs' in trend_info and len(trend_info['troughs']) >= 2:
                t1, t2 = trend_info['troughs'][-2], trend_info['troughs'][-1]
                if t2['price'] > t1['price']:
                    has_two_legs = True
            if not has_two_legs:
                signals_dict['bottom_breakout_no_higher_low_wait_leg2'] = True
                signals.append("⚠️ 突破季線但未成底底高 (助教11/11晶宏指引：單腳急拉未成底底高，等第二隻腳回測有守再進)")

    # 助教 11/11 中電(1611)指引：一字底帶上影線非真突破 (最好是實體K線且必須收過左側大量K線高點)
    if signals_dict.get('flat_base_breakout', False) or (is_red and c > prev_h and c < h * 0.985):
        upper_shadow = h - max(o, c)
        body = abs(c - o)
        if upper_shadow >= body * 0.8:
            signals_dict['flat_base_shadow_not_breakout'] = True
            signals.append("⚠️ 一字底帶上影線非真突破 (助教11/11中電指引：一字底突破最好是實體K線，且必須實質收過左側大量高點)")

    # 助教 11/11 台灣虎航(6757)指引：底部爆量長紅非出貨，均線未完成易回測三大支撐 (1/2價、均線、轉折高點)
    is_at_bottom = (c <= sma60 * 1.10) if ('SMA_60' in last and not pd.isna(last['SMA_60'])) else True
    is_not_full_multima = not (sma5 > sma10 and sma10 > sma20 and sma20 > sma60)
    if is_at_bottom and is_red and change_pct >= 3.5 and vol_ratio >= 1.5 and is_not_full_multima:
        signals_dict['bottom_heavy_red_three_supports'] = True
        signals.append("💎 底部爆量長紅三大回測支撐 (助教11/11虎航指引：位處底部非出貨，均線未完成易回測1/2價、均線、轉折高點三大支撐)")

    # 助教 11/11 金山電(8042)指引：做空緊鄰季線與區間支撐有撐不可空 (做空避開支撐鐵律)
    if 'SMA_60' in last and not pd.isna(last['SMA_60']):
        sma60 = float(last['SMA_60'])
        is_touching_ma60_support = (l <= sma60 * 1.015 and c >= sma60 * 0.99)
        lower_shadow = min(o, c) - l
        if is_touching_ma60_support and lower_shadow >= (h - l) * 0.3:
            signals_dict['short_near_quarterly_ma_support_risk'] = True
            signals.append("⚠️ 緊鄰季線有撐不追空 (助教11/11金山電指引：K線遇季線反應有撐且有區間支撐，做空勝率低)")

    # 助教 11/11 急跌急漲指引：急跌急漲均線跟不上受制下彎月線反壓 (發發4-6案例)
    if c < sma20 and sma20 < prev_sma20:
        if len(df) >= 4 and is_red and change_pct >= 2.0:
            signals_dict['v_rebound_ma20_overhead_resistance'] = True
            signals.append("⚠️ V轉均線跟不上遇月線反壓 (助教11/11指引：急跌急漲均線跟不上，受制於下彎月線沉重壓力易不如預期)")

    # 助教 11/12 誠美材(4960)指引：ABC突破最好站上5均且需收紅K (切線斜率越斜壓力越大)
    if signals_dict.get('abc_correction_breakout', False):
        if is_black or c < sma5:
            signals_dict['abc_cutline_breakout_must_stand_5ma'] = True
            signals.append("⚠️ ABC突破未站穩5均或收黑K (助教11/12誠美材指引：突破最好站上5均且需收紅K，斜率越斜反壓越大)")

    # 助教 11/12 聯發科(2454) & 群創(3481)指引：錯過搶反彈最佳時機不追，後續等趨勢轉多
    if c < sma20 and up_days >= 3:
        signals_dict['rebound_missed_best_timing_no_chase'] = True
        signals.append("⚠️ 錯過搶反彈最佳時機不追 (助教11/12聯發科/群創指引：反彈已推升錯過第一起漲點不追，後續等趨勢轉多)")

    # 助教 11/12 台汽電(8926)指引：空頭波數完成四線空排起算
    is_4ma_bear_strict = (sma5 < sma10 and sma10 < sma20 and sma20 < sma60 and sma20 < prev_sma20)
    if is_4ma_bear_strict:
        signals_dict['bearish_wave_count_4ma_start'] = True

    # 助教 11/12 仁寶(2324) & 英業達(2356)指引：盤整破底為空頭確認非彈後空
    if is_black and c < prev_l and trend_info.get('trend_status') in ['盤整趨勢', '盤整']:
        past_support = df.iloc[-20:-1]['Low'].min() if len(df) >= 20 else prev_l
        if c < past_support:
            signals_dict['breakdown_vs_rebound_short_distinction'] = True
            signals.append("🚨 破底空頭確認賣點 (助教11/12仁寶/英業達指引：盤整破底為趨勢翻空之空頭確認，非維持空頭之彈後空)")

    # 助教 11/12 英業達(2356)指引：腰斬股末跌段做空防強彈洗盤
    if len(df) >= 40:
        high_past_60 = float(df.iloc[-60:]['High'].max())
        if high_past_60 > 0 and (high_past_60 - c) / high_past_60 >= 0.45:
            signals_dict['bearish_halved_stock_late_stage_risk'] = True
            signals.append("⚠️ 腰斬股末跌段做空防強彈 (助教11/12英業達指引：跌達起跌價1/2容易是底部，末跌段做空容易被洗停損)")

    # 助教 11/12 訊映(4155)指引：假突破跌回橫盤停損 (回到橫盤出場或守5%)
    if len(df) >= 4 and is_black and c < sma5:
        if signals_dict.get('kline_consolidation_breakout', False) or (prev_c > float(df.iloc[-4:-1]['High'].max())):
            signals_dict['fake_breakout_return_box_exit'] = True
            signals.append("🛡️ 假突破跌回橫盤停損 (助教11/12訊映指引：假突破跌回橫盤可出場或守5%，注意後續是否真下跌)")

    # 助教 11/12 奇鋐(3017)指引：反彈站上月線正式轉強，續抱守5MA
    if c >= sma20 and prev_c < float(prev.get('SMA_20', sma20)) and is_red:
        signals_dict['rebound_stand_20ma_hold_guard_5ma'] = True
        signals.append("🚀 反彈站上月線正式轉強 (助教11/12奇鋐指引：站上月線正式轉強，持股續抱守5MA移動停利)")

    # 助教 11/13 儒鴻(1476)指引：挑戰前高價過量未過之價量背離
    if is_red and c > prev_c and len(df) >= 20:
        high_past_20 = float(df.iloc[-20:-1]['High'].max())
        vol_past_20_max = float(df.iloc[-20:-1]['Volume'].max())
        if c >= high_past_20 * 0.98 and vol < vol_past_20_max * 0.85:
            signals_dict['breakout_volume_divergence_warning'] = True
            signals.append("⚠️ 挑戰前高價量背離 (助教11/13儒鴻指引：價格創高但量能未超越前波巨量峰值，屬量價背離防誘多拉回)")

    # 助教 11/13 富喬(1815)指引：空頭反彈遇阻下跌為常態
    if c < sma20 and is_black and is_5ma_falling:
        signals_dict['bearish_rebound_drop_is_normal'] = True
        signals.append("📉 空頭反彈遇阻轉黑下跌為常態 (助教11/13富喬指引：原趨勢本就空頭，反彈遇阻下跌是常態，切勿逆勢摸底)")

    # 助教 11/13 轉折波向左追溯鐵律
    if is_red and c >= sma5 and prev_c >= float(prev.get('SMA_5', sma5)):
        signals_dict['turning_point_5ma_strict_rule'] = True

    # 助教 11/13 華城(1519)指引：VOL成交量紅綠顏色純屬軟體設定無關買賣
    signals_dict['vol_color_misconception_filter'] = True

    # 助教 11/17 廣豐(1416)指引：前方有高檔爆量黑K主力出貨，回後買上漲可不進場
    if signals_dict.get('pullback_buy', False) or (is_red and c >= sma5 and prev_c < sma5):
        if len(df) >= 15:
            past_vol_max = df.iloc[-20:-1]['Volume'].max() if len(df) >= 20 else df.iloc[:-1]['Volume'].max()
            for idx in range(max(0, len(df)-20), len(df)-1):
                r = df.iloc[idx]
                if r['Close'] < r['Open'] and r['Volume'] >= past_vol_max * 0.8:
                    signals_dict['high_volume_black_k_pullback_no_buy'] = True
                    signals.append("⚠️ 高檔爆量黑K主力出貨排雷 (助教11/17廣豐指引：前方有高檔爆量黑K出貨訊號，回後買上漲可以不進場)")
                    break

    # 助教 11/17 台積電(2330)指引：第二隻腳底底高與 N字底 vs W底 1/2 價研判
    if len(df) >= 10:
        if c >= sma5 and prev_c < prev_sma5 and is_red:
            signals_dict['second_leg_bottom_rebound_setup'] = True
            signals.append("🦵 第二隻腳觀察 (助教11/17台積電指引：跌破5均找高點，若再出紅K站上5均且守前低，完成底底高第二隻腳)")
        signals_dict['n_to_w_bottom_half_price_rule'] = True

    # 助教 11/17 選股 5-2 指引：特別報價選股看「量放大股」非「量大股」
    if vol_ratio >= 1.3:
        signals_dict['vol_amplified_not_just_high_vol'] = True
    # ----------------------------------------------------
    # 助教 11/19 專屬實戰定錨指引 (日盤 + 夜盤)
    # ----------------------------------------------------
    # 1. 助教 11/19 宣德(5457)指引：多頭確認不等於符合進場條件（上方緊鄰下彎季線反壓不足 3%~5% 或均線未多排）
    if signals_dict.get('multilink_bottom_breakout', False) or (is_red and c >= sma5 and c >= sma20):
        if sma60 > c and (sma60 - c) / c <= 0.05 and sma60 < prev_sma60:
            signals_dict['bullish_confirmed_not_buy_signal'] = True
            signals.append("⚠️ 多頭確認但未符進場條件 (助教11/19宣德指引：底底高頭頭高多頭確認，但上方緊鄰下彎季線反壓不足5%，做多七不買一票否決！)")

    # 2. 助教 11/19 聯發科(2454)指引：第二隻腳進場表態收「價漲黑K（開高走低）」不買（做多七不買第七條）
    if signals_dict.get('second_leg_bottom_rebound_setup', False) or (c >= sma5 and prev_c < prev_sma5):
        if is_black and change_pct > 0:
            signals_dict['advance_black_k_rejection'] = True
            signals.append("❌ 做多七不買排雷 (助教11/19聯發科指引：打第二隻腳但收價漲黑K開高走低，主力未真表態，嚴禁進場！)")

    # 3. 助教 11/19 大盤指引：圓弧頂/M頭破頸線確認後，等反彈回測頸線/均線反壓不過再放空
    if signals_dict.get('top_breakdown', False) or signals_dict.get('ma20_death_break', False):
        signals_dict['topping_pattern_rebound_short_wait'] = True
        signals.append("📉 頭部確認等回測再空 (助教11/19大盤指引：圓弧頂/頭部跌破確認後離前低近不盲追，等弱勢反彈回測壓力不過出轉折黑K再放空)")

    # 4. 助教 11/19 創新服務(7828)與祥碩(5269)指引：空頭跌深長紅漲停或低檔橫移僅為盤整，等趨勢轉多
    if sma20 < prev_sma20 and c < sma20:
        if is_red and change_pct >= 9.5:
            signals_dict['consolidation_counter_trend_no_buy'] = True
            signals.append("🛑 跌深反彈初轉盤整 (助教11/19創新服務指引：空頭長紅漲停過昨高僅轉盤整，月線下彎未成多排，盤整不進場！)")

    # ----------------------------------------------------
    # 助教 11/23 專屬實戰定錨指引
    # ----------------------------------------------------
    # 1. K線橫盤第1根起算3根成立，第4天起任一天收盤突破或跌破皆算 (助教11/23 6-10指引)
    if signals_dict.get('kline_consolidation_breakout', False) or signals_dict.get('kline_consolidation_breakdown', False):
        signals_dict['kline_consolidation_3day_min_rule'] = True

    # 2. 逆向思考剛過月線試單(月線尚未必翻揚)：若隔日或回測跌破月線恐空頭續勢應全砍 (助教11/23 11/18節目解析)
    if prev_c >= prev_sma20 and c < sma20 and sma20 <= prev_sma20:
        signals_dict['reverse_trial_buy_above_ma20_stop'] = True
        signals.append("🎯 逆向試單破月線全砍警訊 (助教11/23指引：過月線試單若月線下彎且回測破月線，恐空頭續勢應全部停損！)")

    # 3. 頭部確認後若強彈站回月線或突破頸線，警示原空頭型態可能回測失敗 (助教11/23大盤圓弧頂指引)
    if signals_dict.get('topping_pattern_rebound_short_wait', False) and is_red and change_pct >= 2.0 and c > sma20:
        signals_dict['pattern_retest_failure_invalidation'] = True
        signals.append("🔄 頭部型態回測失效警示 (助教11/23大盤指引：圓弧頂/頭部回測壓力若無壓強彈轉多，原下跌目標不會到達)")

    # ----------------------------------------------------
    # 助教 11/25 專屬實戰定錨指引 + 布林通道擴充
    # ----------------------------------------------------
    # 1. 收盤價高於5均即站上，但若為黑K次日易下跌 (助教11/25晶豪科指引)
    if c > sma5:
        signals_dict['close_above_ma5_any_k_rule'] = True

    # 2. 空頭反彈遇下彎月線壓力警示 (助教11/25指引：見撐不是撐，要看壓力重不重)
    if sma20 < prev_sma20 and is_red and c < sma20 and (sma20 - c) / c <= 0.04:
        signals_dict['bearish_rebound_pressure_alert'] = True
        signals.append("⚠️ 空頭反彈近月線壓力 (助教11/25指引：空頭特性『見撐不是撐，要看壓力重不重』，將觸及下彎月線反壓區)")

    # 3. 喇叭擴散型態簡易偵測 (高點墊高且低點墊低，近15日高點創高且低點亦創低)
    if len(df) >= 20:
        recent10_h = df.iloc[-10:]['High'].max()
        prev10_h = df.iloc[-20:-10]['High'].max()
        recent10_l = df.iloc[-10:]['Low'].min()
        prev10_l = df.iloc[-20:-10]['Low'].min()
        if recent10_h > prev10_h and recent10_l < prev10_l and c >= recent10_h * 0.98:
            signals_dict['megaphone_broadening_pattern_alert'] = True
            signals.append("📢 喇叭擴散型態警示 (助教11/25潤弘指引：高過前高且低破前低，突破前高時留意上緣擴散軌反壓)")

    # 4. 獨立布林通道 (20MA ± 2σ) 輔助診斷計算 (嚴格隔離：絕不寫入主 signals 列表，僅存於 bollinger_info)
    if len(df) >= 20:
        bb_info = compute_bollinger_info(df, vol_ratio=vol_ratio)
        signals_dict['bollinger_info'] = bb_info
        signals_dict['bollinger_squeeze_breakout'] = bool(bb_info.get('squeeze_breakout', False))
        signals_dict['bollinger_upper_band_walk'] = bool(bb_info.get('upper_band_walk', False))
        signals_dict['bollinger_lower_band_rebound'] = bool(bb_info.get('lower_band_rebound', False))

    # 策略 D_空：頂部起跌 (高檔整理或頭部型態完成，首度放量跌破均線)
    past20_high = df.iloc[-25:-5]['High'].max() if len(df) >= 25 else h
    is_near_top = (c >= past20_high * 0.85) or (sma20 >= sma60 * 0.98)
    is_breakdown_today = (c <= sma5 and c <= sma20 and is_black and (change_pct <= -0.5 or vol_ratio >= 1.1) and is_5ma_falling)
    if is_near_top and is_breakdown_today:
        signals_dict['top_breakdown'] = True
        signals.append("頂部起跌 (高檔放量長黑跌破均線)")

    # 策略 E_空：低檔起跌 (空頭破底續殺)
    if c <= sma60 and sma5 < sma20 and change_pct <= -1.2 and is_black and (c <= df.iloc[-10:-1]['Low'].min() * 1.01) and is_5ma_falling:
        signals_dict['low_breakdown'] = True
        signals.append("低檔起跌 (弱勢跌破前低續殺)")

    # 策略 F_空：均線糾結跌破 / 四線空排 (四線空排崩跌警訊)
    is_4ma_bear_order = (sma5 <= sma10 and sma10 <= sma20 and sma20 <= sma60)
    is_4ma_falling = (is_5ma_falling and sma20 <= prev_sma20)
    if is_4ma_bear_order and is_4ma_falling:
        signals_dict['bearish_alignment_4ma'] = True

    if len(df) >= 25:
        sub_period_short = df.iloc[-40:-1] if len(df) >= 40 else df.iloc[:-1]
        rng_min_short = sub_period_short['Low'].min()
        ma_list_prev = [prev_sma5, prev_sma10, prev_sma20, prev_sma60] if len(df) >= 60 else [prev_sma5, prev_sma10, prev_sma20]
        prev_dispersion = (max(ma_list_prev) - min(ma_list_prev)) / (min(ma_list_prev) + 1e-9)

        # 均線糾結跌破：先前四線糾結 (離散度 <= 6%) 或平台整理，今日長黑摜破四線與低點支撐
        is_breakdown_all_mas = (c <= sma5 and c <= sma10 and c <= sma20 and c <= sma60)
        if (prev_dispersion <= 0.06 or c <= rng_min_short * 1.01) and is_breakdown_all_mas and is_black and is_5ma_falling:
            signals_dict['ma_squeeze_breakdown'] = True
            signals_dict['flat_top_breakdown'] = True
            signals.append("均線糾結跌破 (四線空排崩跌初跌段)")

    # ----------------------------------------------------
    # 趨勢線鐵律：做多要在月線上 (跌破月線3天助漲未回且月線下彎 = 多頭終結)
    # ----------------------------------------------------
    if len(df) >= 3:
        past3_closes = df.iloc[-3:]['Close']
        past3_sma20s = df.iloc[-3:]['SMA_20'] if 'SMA_20' in df else past3_closes
        days_below_ma20 = (past3_closes < past3_sma20s).sum()
        is_20ma_falling = (sma20 < prev_sma20 * 0.999)
        if days_below_ma20 >= 3 and is_20ma_falling:
            signals_dict['ma20_death_break'] = True
            signals.append("🔴 趨勢線鐵律：跌破月線3天助漲未回且月線下彎 (多頭終結清倉)")

    # 策略 J_空：一點鐘放空 (1:00 PM 尾盤選股)
    if is_black and c <= sma5 and is_5ma_falling and change_pct <= -0.5:
        signals_dict['one_pm_short'] = True
        signals.append("一點鐘放空 (尾盤弱勢收黑跌破操盤線)")

    # 策略 K_空：盤中弱勢 (跌破帶量)
    if change_pct <= -1.2 and is_black and c <= sma5 and vol_ratio >= 1.05:
        signals_dict['intraday_weak'] = True
        signals.append("盤中弱勢 (量大摜破操盤線)")

    # ----------------------------------------------------
    # 策略 CH6-10：K線橫盤的跌破 (3天橫盤黑K摜破空點)
    # 實戰心法鐵律：
    # 1. 過去 3 天橫盤整理未破亦未過第 1 根
    # 2. 今日大量黑 K 收盤摜破前 3 天橫盤最低點
    # 3. 5MA 下彎跌破 (c <= sma5 and is_5ma_falling)
    # ----------------------------------------------------
    if len(df) >= 4 and is_black and c <= sma5 and is_5ma_falling:
        past3_s = df.iloc[-4:-1]
        h3_s = float(past3_s['High'].max())
        l3_s = float(past3_s['Low'].min())
        amp3_s = (h3_s - l3_s) / (l3_s + 1e-9)
        if amp3_s <= 0.065 and c < l3_s and (vol_ratio_5 >= 1.05 or change_pct <= -1.0):
            signals_dict['kline_consolidation_breakdown'] = True
            signals.append("📊 K線橫盤跌破 (3天橫盤黑K摜破)")

    # ----------------------------------------------------
    # 策略：跌破反彈 ABC 修正上升切線 (短多做底失敗重回主跌)
    # 實戰心法鐵律：
    # 1. 下跌波後，出現 A-B-C 三波反彈 (上升旗型，20天內)
    # 2. 20MA 月線下彎壓制 (sma20 <= prev_sma20 * 1.002)
    # 3. 大量中長黑 K 跌破上升切線 (跌破反彈 B 點)，短多做底失敗，重回主跌段！
    # ----------------------------------------------------
    if len(df) >= 12 and is_black and c <= sma5 and is_5ma_falling and sma20 <= prev_sma20 * 1.002:
        sub_abc_s = df.iloc[-20:-1] if len(df) >= 20 else df.iloc[:-1]
        low_idx = sub_abc_s['Low'].idxmin()
        if low_idx < sub_abc_s.index[-2]:
            after_l = sub_abc_s.loc[low_idx:]
            if len(after_l) >= 3:
                b_trough = float(after_l.iloc[1:-1]['Low'].min()) if len(after_l) > 2 else float(after_l['Low'].mean())
                if c < b_trough and (vol_ratio_5 >= 1.05 or change_pct <= -1.0):
                    signals_dict['abc_rebound_breakdown'] = True
                    signals.append("📐 跌破反彈ABC切線 (短多做底失敗重回主跌)")

    # ----------------------------------------------------
    # 策略：跌破下跌軌道線 (空頭加速趕底轉強)
    # 實戰心法鐵律：
    # 1. 空頭沿下降軌道線緩步下跌 (5MA < 20MA)
    # 2. 今日大量中長黑 K 收盤摜破下降軌道線，空頭轉強加速趕底！
    # ----------------------------------------------------
    if len(df) >= 20 and (is_bear or sma5 < sma20) and is_black and (c <= sma5) and is_5ma_falling and change_pct <= -2.0 and vol_ratio_5 >= 1.25:
        past15_s = df.iloc[-16:-1]
        lower_bound = float(past15_s['Low'].min())
        if c <= lower_bound * 0.995:
            signals_dict['descending_channel_breakdown'] = True
            signals.append("📉 跌破下降軌道線 (空頭加速趕底)")

    # ----------------------------------------------------
    # 策略：跌破反彈紅K低點 (弱勢反彈破底·空頭再轉弱)
    # 實戰心法鐵律：
    # 1. 弱勢空頭急跌時，過去 1~3 天爆大量收紅 K 反彈
    # 2. 20MA 月線維持下彎 (sma20 <= prev_sma20 * 1.002)
    # 3. 今日大量中長黑 K 收盤跌破該反彈紅 K 最低點，空頭再轉弱！
    # ----------------------------------------------------
    if len(df) >= 5 and is_black and (c <= sma5) and is_5ma_falling and sma20 <= prev_sma20 * 1.002:
        past3_bars_s = df.iloc[-4:-1]
        for _, r_row in past3_bars_s.iterrows():
            r_v = float(r_row['Volume'])
            r_vma = float(r_row.get('Vol_MA5', r_v))
            r_is_red = (float(r_row['Close']) > float(r_row['Open']))
            if r_vma > 0 and r_v >= r_vma * 1.2 and r_is_red:
                if c < float(r_row['Low']):
                    signals_dict['breakdown_rebound_red_low'] = True
                    signals.append("⚡ 跌破大量紅K低點 (弱勢反彈破底·空頭再轉弱)")
                    break

    # ----------------------------------------------------
    # 空頭防守注意：次日並排紅K實體棒，易為假下跌
    # ----------------------------------------------------
    if is_red and not is_bear and float(prev['Close']) < float(prev['Open']) and c >= float(prev['Open']) * 0.99:
        signals_dict['is_parallel_red_warning'] = True
        signals.append("⚠️ 並列紅K (空方防假下跌·嚴守停損)")

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
    # 成交量位階與位置決定命運 (經典量價操盤心法：起漲爆量進場 vs 高檔爆量防出貨)
    # 基本量為 5MA 量；攻擊量 >= 1.25倍 5MA量；爆量 >= 2.0倍 5MA量
    # ----------------------------------------------------
    is_high_position = is_multi_bagger or (c >= sma20 * 1.15) or (len(df) >= 40 and c >= df.iloc[-40:]['Low'].min() * 1.35)
    is_low_position = is_near_bottom or (sma5 <= sma60 * 1.08) or (c <= sma20 * 1.06)
    signals_dict['is_high_position'] = is_high_position

    # 攻擊量 (5MA量 1.25倍以上，且收紅K站上5MA)
    is_attack_vol = (vol_ratio_5 >= 1.25) and is_red and (c >= sma5)
    # 爆大量 (5MA量 或 20MA量 2.0倍以上)
    is_heavy_vol = (vol_ratio_5 >= 2.0 or vol_ratio_20 >= 2.0)
    # 止跌量 (量縮至 5MA量 55% 以下且不破昨低)
    is_stop_fall_vol = (vol_ratio_5 <= 0.55) and (l >= prev_l * 0.995) and (c >= l + (h - l) * 0.25)

    # 量價背離：價漲量急縮背離 (排除大突破、主升第二波與飽滿長紅) 或 高檔滯漲爆量
    is_vp_div_bull = (change_pct >= 1.2 and vol_ratio_5 <= 0.60 and not is_box_breakout and not is_main_wave_2nd and not is_solid_bull)
    is_vp_div_bear = (abs(change_pct) <= 0.4 and vol_ratio_5 >= 1.8 and is_high_position)
    is_volume_price_divergence = is_vp_div_bull or is_vp_div_bear

    signals_dict['is_attack_vol'] = is_attack_vol
    signals_dict['is_stop_fall_vol'] = is_stop_fall_vol
    signals_dict['is_volume_price_divergence'] = is_volume_price_divergence

    if is_false_breakout_dump:
        volume_tag = "假突破誘多"
        volume_status = "🚨 假突破誘多出貨 (長黑灌破長紅低點，嚴禁做多)"
    elif is_turnover_success:
        volume_tag = "換手成功"
        volume_status = "🔥 換手量成功 (高檔爆量後強勢過高，主力換手完畢續噴)"
    elif is_heavy_vol:
        if is_high_position or has_long_upper_shadow or (not is_red and change_pct <= 0):
            volume_tag = "高檔爆量"
            volume_status = "⚠️ 高檔爆大量 (防主力倒貨，嚴禁追高)"
            signals.append("⚠️ 高檔爆量 (短線停利賣點，防主力倒貨)")
        elif is_low_position or is_red:
            volume_tag = "爆量起漲"
            volume_status = "🚀 爆量攻擊起漲 (主力強勢介入表態)"
            signals.append("🚀 爆量攻擊起漲 (低檔爆大量紅K表態)")
        else:
            volume_tag = "高檔巨量"
            volume_status = "📊 爆量巨量推升"
    elif is_attack_vol:
        volume_tag = "攻擊量"
        volume_status = "⚡ 5MA攻擊量 (放量達標，多方發動攻擊)"
        signals.append("⚡ 5MA攻擊量 (放量達標，多方強勢發動)")
    elif is_stop_fall_vol:
        volume_tag = "止跌量"
        volume_status = "🛡️ 止跌量 (量縮半且不破低，短線防守)"
        signals.append("🛡️ 止跌量 (量縮半且不破低，短線防守契機)")
    elif vol_ratio <= 0.60:
        volume_tag = "量縮整理"
        volume_status = "⏳ 量縮整理 (等待主力補量表態)"
    else:
        volume_tag = "常態量"
        volume_status = "常態量 (量能平穩)"

    if is_vp_div_bull:
        signals.append("⚠️ 量價背離 (價漲量急縮，多方動能匱乏注意拉回)")
    elif is_vp_div_bear:
        signals.append("⚠️ 量價背離 (高檔出量滯漲，防主力倒貨)")

    signals_dict['volume_tag'] = volume_tag
    signals_dict['volume_status'] = volume_status
    signals_dict['vol_ratio'] = round(vol_ratio, 2)

    # ----------------------------------------------------
    # CH6-15 飆股操盤與智慧 K 線交易法 (Smart K-Line Trading)
    # 實戰心法鐵律：
    # 1. 智慧 K 線交易法：每天收盤沒有跌破前一天 K 線最低點就持股續抱！
    # 2. 下午 1:20 檢視，若確認跌破前一日最低點即掛單賣出。
    # 3. 獲利 > 20% 高檔爆大量長上影黑 K 先賣 1/2。
    # 4. 飆股五大量價燈號研判。
    # ----------------------------------------------------
    smart_kline_defend = round(float(prev['Low']), 2)
    smart_kline_safe = (c >= smart_kline_defend)
    signals_dict['smart_kline_defend'] = smart_kline_defend
    signals_dict['smart_kline_safe'] = smart_kline_safe

    if not smart_kline_safe and is_high_position:
        signals_dict['smart_kline_exit_warning'] = True
        signals.append("⚠️ 智慧K線退場警戒 (跌破前一日最低點，13:20掛單賣出)")

    # 飆股量價五燈號研判
    if change_pct >= 2.5 and vol_ratio_5 <= 0.85 and c >= sma5:
        signals_dict['explosive_stock_status'] = "🟢 無量飆漲 (主力鎖碼急漲，續抱)"
    elif change_pct >= 0.5 and 0.85 < vol_ratio_5 <= 1.45 and c >= sma5:
        signals_dict['explosive_stock_status'] = "🟢 溫和量價齊揚 (多方穩健推升，續抱)"
    elif vol_ratio_5 >= 1.5 and ((h - l) / (l + 1e-9)) >= 0.05:
        signals_dict['explosive_stock_status'] = "🟡 量大劇烈震盪 (高檔主力洗盤，建議先賣1/2)"
    elif vol_ratio_5 >= 2.0 and change_pct >= 0 and is_high_position:
        signals_dict['explosive_stock_status'] = "🟡 高檔爆大量 (注意次日走勢，可先賣1/2)"
    elif vol_ratio_5 >= 1.6 and is_black and ((o - c) / (o + 1e-9)) >= 0.015 and is_high_position:
        signals_dict['explosive_stock_status'] = "🔴 爆大量開高走低長黑 (賣壓湧現主力倒貨，全數賣出)"
    else:
        signals_dict['explosive_stock_status'] = "常態波動"

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
    # CH7 實戰停損與風控全攻略 & 短線 3~5 天波段價差專屬操盤卡
    # ----------------------------------------------------
    # 若前高壓力小於或等於現價（代表已突破或在歷史高點），目標價依「等幅對稱波」或 +10% 測距滿足點
    if res_price <= c * 1.02:
        calc_target = round(c + max(c * 0.08, c - sup_price), 2)
    else:
        calc_target = res_price

    # 1. 四大策略停損點位 (7-2 策略停損法)
    # (A) K 線戰法停損：做多以進場當天(或最新突破/轉折紅K)最低點為停損點
    recent_red_low = l if is_red else None
    if recent_red_low is None:
        for idx in range(len(df) - 2, max(-1, len(df) - 6), -1):
            row_k = df.iloc[idx]
            if float(row_k['Close']) >= float(row_k['Open']):
                recent_red_low = float(row_k['Low'])
                break
    if recent_red_low is None:
        recent_red_low = l
    kline_stop = round(float(recent_red_low), 2)

    # (B) 均線操作法停損：以 5MA 操盤生命線為停損點
    ma5_stop = round(float(sma5), 2)

    # (C) 形態/趨勢停損法：守轉折前底 (支撐) 或型態頸線 (Neckline)
    pattern_stop = round(float(sup_price), 2)

    # (D) 固定比例法停損：以進價 5% 為標準，10% 為絕對極限
    fixed_5pct_stop = round(float(c * 0.95), 2)
    absolute_10pct_stop = round(float(c * 0.90), 2)

    # 助教推薦最適停損點 (Primary Recommended Stop Loss)
    # 官方原則：停損幅度最好在 5%~10% 之間，最好不要超過 10%
    candidate_stops = []
    if pattern_stop < c and ((c - pattern_stop) / c) <= 0.095:
        candidate_stops.append((pattern_stop, "形態/頸線停損", f"守波段前底/頸線 {pattern_stop} 元"))
    if kline_stop < c and ((c - kline_stop) / c) <= 0.095:
        candidate_stops.append((kline_stop, "K線低點停損", f"守關鍵紅K最低點 {kline_stop} 元"))
    if ma5_stop < c and ((c - ma5_stop) / c) <= 0.07:
        candidate_stops.append((ma5_stop, "5MA均線停損", f"守 5MA 操盤線 {ma5_stop} 元"))

    if candidate_stops:
        rec_stop_val, rec_stop_type, rec_stop_desc = max(candidate_stops, key=lambda x: x[0])
    else:
        rec_stop_val = fixed_5pct_stop
        rec_stop_type = "固定 5% 停損"
        rec_stop_desc = f"守固定 5% 風控保命線 {fixed_5pct_stop} 元"

    if (c - rec_stop_val) / c > 0.10:
        rec_stop_val = fixed_5pct_stop
        rec_stop_type = "固定 5% 停損"
        rec_stop_desc = f"停損防守超過10%極限，嚴格以固定5%保命線 {fixed_5pct_stop} 元為限"

    rec_risk = max(0.01, c - rec_stop_val)
    rec_reward = max(0.01, calc_target - c)
    rr_ratio = round(rec_reward / rec_risk, 1)
    risk_pct = round((rec_risk / c) * 100, 1)
    reward_pct = round((rec_reward / c) * 100, 1)

    # 2. CH7-3 停損的改變：獲利達 7% 以上轉為移動停利 (Trailing Stop)
    swing_gain = round(((c - sup_price) / (sup_price + 1e-9)) * 100, 1) if sup_price > 0 else 0.0
    is_trailing_stop_active = (swing_gain >= 7.0 or ((c - kline_stop) / (kline_stop + 1e-9)) * 100 >= 7.0)
    trailing_stop_price = round(max(sup_price, sma5), 2) if is_trailing_stop_active else rec_stop_val

    # 3. 每日檢視警示機制 (CH7-3 不套牢準則：跌幅超過 5% 列為警示股)
    is_drop_5pct_warning = (change_pct <= -5.0)

    # 4. 絕對停損危險警訊檢核 (明顯錯誤不可凹單)
    absolute_warnings = []
    if sup_price > 0 and c < sup_price:
        absolute_warnings.append("⚠️ 摜破盤整箱底/前波支撐 (絕對停損·禁止凹單)")
    if is_drop_5pct_warning:
        absolute_warnings.append("⚠️ 今日重挫逾 5% (風控警示股·準備賣出)")
    if is_high_position and is_black and vol_ratio_5 >= 1.5 and c < sma5:
        absolute_warnings.append("⚠️ 高檔爆量長黑反轉 (絕對停損·空頭確認)")
    # 5. 高檔爆量遭遇線停利 SOP (助教 10/13 雷迪克 & 10/22 德宏指導)
    if is_high_position and is_black and (vol_ratio >= 1.4 or vol_ratio_5 >= 1.4):
        signals_dict['is_encounter_line'] = True
        absolute_warnings.append("⚠️ 高檔爆量遭遇線 (停利SOP：高獲利先出一半，另一半跌破大量低點出場)")
        signals.append("⚠️ 高檔爆量遭遇線 (停利SOP：高獲利先出一半，另一半跌破大量低點出場)")
        if is_bull and c >= sma5 and l >= sup_price * 0.99:
            signals_dict['heavy_black_trend_intact_watch_next'] = True
            signals.append("👀 爆量黑K但未破5均與前波底撐 (助教10/22德宏指引：前低指前波轉折底而非昨低；趨勢不變支撐沒破先看次日，觸-5%則依紀律)")
    if signals_dict.get('attack_vol_insufficient_for_res', False) and (c >= o):
        signals.append("⚠️ 攻擊量未達壓力量50% (助教10/13華新指導：化解左側套牢重壓，攻擊量至少需達壓力量50%，防撞牆假突破)")
    if change_pct <= -9.5 or (sup_price > 0 and (sup_price - c) / sup_price >= 0.10):
        absolute_warnings.append("🛑 跌幅逾 10% 終極鐵律 (絕對停損·壯士斷腕)")

    signals_dict['ch7_stop_loss'] = {
        "kline_stop": kline_stop,
        "ma5_stop": ma5_stop,
        "pattern_stop": pattern_stop,
        "fixed_5pct_stop": fixed_5pct_stop,
        "absolute_10pct_stop": absolute_10pct_stop,
        "recommended_stop": rec_stop_val,
        "stop_type": rec_stop_type,
        "stop_desc": rec_stop_desc,
        "risk_pct": risk_pct,
        "is_trailing_stop_active": is_trailing_stop_active,
        "trailing_stop_price": trailing_stop_price,
        "swing_gain": swing_gain,
        "is_drop_5pct_warning": is_drop_5pct_warning,
        "absolute_warnings": absolute_warnings
    }

    signals_dict['swing_3_5d'] = {
        "stop_loss": rec_stop_val,
        "ma5_defend": sma5,
        "target_res": calc_target,
        "rr_ratio": rr_ratio,
        "risk_pct": risk_pct,
        "reward_pct": reward_pct,
        "stop_type": rec_stop_type,
        "kline_stop": kline_stop,
        "pattern_stop": pattern_stop,
        "fixed_5pct_stop": fixed_5pct_stop,
        "trailing_stop_price": trailing_stop_price,
        "is_trailing_stop_active": is_trailing_stop_active,
        "is_drop_5pct_warning": is_drop_5pct_warning
    }

    if is_drop_5pct_warning:
        signals.append("🚨 單日重挫逾 5% (風控警示·準備賣出)")
    if is_trailing_stop_active:
        signals.append(f"🏆 獲利逾 7% 啟動移動停利 (守 5MA {sma5:.2f}元)")

    # ----------------------------------------------------
    # 三均線短中長線綜合戰法 (3張部位管理 SOP) & 10%停利門檻 (CH8)
    # ----------------------------------------------------
    held_shares = 0
    ma5_held = (c >= sma5)
    ma10_held = (c >= sma10)
    ma20_held = (c >= sma20)

    if ma5_held: held_shares += 1
    if ma10_held: held_shares += 1
    if ma20_held: held_shares += 1

    held_pct = round((held_shares / 3.0) * 100)

    # 翻倍極限 (+100%) 與腰斬極限 (-50%) 判定
    highest_120 = float(df.iloc[-120:]['High'].max()) if len(df) >= 120 else float(df['High'].max())
    drop_from_top_pct = round(((c - highest_120) / (highest_120 + 1e-9)) * 100, 1) if highest_120 > 0 else 0.0
    is_halved_from_top = (drop_from_top_pct <= -48.0)
    is_doubled_from_bottom = is_multi_bagger or (bagger_multiple >= 1.95)

    # 10% 獲利門檻洗盤保護與停利判定
    is_ten_pct_reached = (swing_gain >= 10.0)

    if held_shares == 3:
        three_ma_advice = "三線全守穩（滿水位 3/3）：短中長線趨勢完好，持股續抱，讓利潤奔馳！"
    elif held_shares == 2:
        if not ma5_held:
            if is_ten_pct_reached:
                three_ma_advice = "跌破 5MA（獲利逾10%調節）：短線獲利已豐，5MA 跌破立即停利 1/3，剩餘 2/3 守 10MA/20MA 續抱！"
            else:
                three_ma_advice = "跌破 5MA（獲利未達10%洗盤）：屬波段初升正常洗盤，未破前低前給予震盪彈性防賣飛，部位調為 2/3。"
        elif not ma10_held:
            three_ma_advice = "跌破 10MA（調節至 2/3）：中線轉弱調節 1/3，守 5MA/20MA 關鍵均線。"
        else:
            three_ma_advice = "跌破 20MA（保留短中線 2/3）：月線跌破警訊，留意短線 5MA 能否迅速帶動站回。"
    elif held_shares == 1:
        if ma20_held:
            three_ma_advice = "跌破 5MA與10MA（調節至 1/3）：僅存 20MA 長線 1/3 部位，嚴密戒備月線防守！"
        elif ma5_held:
            three_ma_advice = "僅站上 5MA（弱勢反彈 1/3）：中長線均線壓制，僅適合作為短線試單 1/3 部位。"
        else:
            three_ma_advice = "僅站上 10MA（偏弱震盪 1/3）：均線分歧，部位嚴格控制在 1/3 以內。"
    else:
        three_ma_advice = "跌破 20MA（空手 0/3）：三線全破，波段多頭結束，全數出清離場！"

    if is_doubled_from_bottom:
        three_ma_advice += " 【高檔翻倍鐵律】波段已大漲 1 倍，嚴禁做長線！全面切換為短線 5MA 操作，破 5MA 即全走！"

    signals_dict['three_ma_strategy'] = {
        "held_shares": held_shares,
        "held_pct": held_pct,
        "ma5_held": ma5_held,
        "ma10_held": ma10_held,
        "ma20_held": ma20_held,
        "sma5": sma5,
        "sma10": sma10,
        "sma20": sma20,
        "is_ten_pct_reached": is_ten_pct_reached,
        "swing_gain": swing_gain,
        "is_doubled_from_bottom": is_doubled_from_bottom,
        "bagger_multiple": bagger_multiple,
        "is_halved_from_top": is_halved_from_top,
        "drop_from_top_pct": drop_from_top_pct,
        "advice": three_ma_advice
    }

    if held_shares == 3 and is_bull:
        signals.append(f"🧭 三均線多頭滿載 (3/3 全守穩：5MA {sma5:.2f} / 10MA {sma10:.2f} / 20MA {sma20:.2f})")
    elif not ma5_held and is_ten_pct_reached:
        signals.append("🛑 獲利逾 10% 跌破 5MA (短線停利賣出 1/3，保全戰果)")
    elif is_doubled_from_bottom:
        signals.append(f"⚠️ 波段已大漲 {bagger_multiple:.1f} 倍 (翻倍極限：嚴禁做長線，僅限短線 5MA 操作)")

    # ----------------------------------------------------
    # 實戰停利操盤全攻略 (CH9 紀律停利 · 獲利目標 · 四大高檔反轉現象)
    # ----------------------------------------------------
    # 1. 9-1 依據紀律停利 (Discipline-Based Take Profit)
    # 短線做多：採用 5MA，收盤跌破 5MA 停利出場；多頭趨勢不變 + 股價在 20MA 之上持續做多 (拉回守穩再找轉折進場)
    # 長線做多：採用 20MA，收盤跌破 20MA 停利；多頭趨勢不變 + 股價在 20MA+60MA 之上持續做多
    ma5_tp_hit = (c < sma5)
    ma20_tp_hit = (c < sma20)

    if ma5_tp_hit:
        short_tp_status = "🚨 跌破 5MA 操盤線 (短線多單紀律停利出場)"
        if is_bull and c >= sma20:
            short_tp_rebuy = "💡 多頭架構未破且在 20MA 之上，短線獲利入袋；待拉回守穩 20MA 轉折向上、再度突破 5MA 時重新進場！"
        else:
            short_tp_rebuy = "⚠️ 短線走弱跌破 5MA，保守觀望，嚴禁急於承接。"
    else:
        short_tp_status = f"🟢 守穩 5MA 操盤線 ({sma5:.2f}元)，短線多單持股續抱"
        short_tp_rebuy = "多頭攻擊推升中，守穩 5MA 讓利潤奔馳。"

    if ma20_tp_hit:
        long_tp_status = "🚨 跌破 20MA 月線 (長線多單紀律停利出場)"
    elif c >= sma20 and sma20 >= sma60:
        long_tp_status = f"🟢 守穩 20MA ({sma20:.2f}元) 與 60MA ({sma60:.2f}元) 之上，長線多單波段續抱"
    else:
        long_tp_status = f"🟡 站上 20MA ({sma20:.2f}元)，中長線觀察均線多頭排列。"

    # 2. 9-2 依據獲利目標設定停利 (Target-Based Take Profit) - 6大日線壓力關卡
    # (1) 長均線壓力
    long_mas = []
    for ma_name, ma_val in [('20MA', sma20), ('60MA', sma60), ('120MA', float(last.get('SMA_120', 0))), ('240MA', float(last.get('SMA_240', 0)))]:
        if ma_val > c * 1.002:
            long_mas.append((ma_name, round(ma_val, 2)))
    long_mas.sort(key=lambda x: x[1])
    res_long_ma = long_mas[0] if long_mas else (None, None)

    # (2) 前高壓力
    recent_high_60 = float(df.iloc[-60:]['High'].max()) if len(df) >= 60 else float(df['High'].max())
    res_prior_high = round(recent_high_60, 2) if recent_high_60 > c * 1.005 else None

    # (3) 下降切線壓力 (若有下降趨勢線)
    res_desc_line = round(res_price, 2) if res_price > c * 1.005 else None

    # (4) 向上盤整區壓力 (箱型整理上緣)
    box_high_val = float(df.iloc[-20:]['High'].max()) if len(df) >= 20 else float(df['High'].max())
    res_box_top = round(box_high_val, 2) if is_consolidation and box_high_val > c * 1.005 else None

    # (5) 大量向下跳空缺口壓力 (整合 gap_detector 精準抓取未回補空方真空帶)
    res_down_gap = None
    res_down_gap_label = "向下跳空缺口壓力"
    nearest_bearish_g = None
    try:
        from core.gap_detector import detect_unfilled_gaps
        gaps_info = detect_unfilled_gaps(df, lookback_bars=120)
        nearest_bearish_g = gaps_info.get("nearest_overhead_gap")
        if nearest_bearish_g:
            res_down_gap = nearest_bearish_g['rem_bottom']
            res_down_gap_label = f"空方缺口反壓 ({nearest_bearish_g['rem_bottom']:.1f}~{nearest_bearish_g['rem_top']:.1f}元)"
    except Exception:
        pass

    # (6) 大量下跌黑K壓力
    res_heavy_black = unresolved_blacks[-1]['high'] if unresolved_blacks else None

    # 彙整最近的第一道壓力目標
    candidate_pressures = []
    if res_long_ma[1]: candidate_pressures.append((f"長均線壓力 ({res_long_ma[0]})", res_long_ma[1]))
    if res_prior_high: candidate_pressures.append(("波段前高壓力", res_prior_high))
    if res_desc_line: candidate_pressures.append(("下降切線/形態壓力", res_desc_line))
    if res_box_top: candidate_pressures.append(("盤整區頸線壓力", res_box_top))
    if res_down_gap: candidate_pressures.append((res_down_gap_label, res_down_gap))
    if res_heavy_black: candidate_pressures.append(("爆量黑K重壓", res_heavy_black))

    candidate_pressures = [p for p in candidate_pressures if p[1] > c * 1.003]
    candidate_pressures.sort(key=lambda x: x[1])
    nearest_target = candidate_pressures[0] if candidate_pressures else ("創波段新高，上方無實體均線與前高壓力", round(c * 1.10, 2))

    # 3. 9-3 依據訊號準備停利 (四大高檔反轉現象)
    # 高檔環境檢定 (累積漲幅逾 15% 或距 20MA 乖離大或波段翻倍)
    is_high_for_tp = is_high_position or is_multi_bagger or (c >= sma20 * 1.12) or (swing_gain >= 15.0)
    reversal_alerts = []

    # 現象一：高檔跌破連續 2 日大量 K 線低點
    # 高檔連續 2 日爆出大量，今日收盤摜破這兩天大量區之最低點 -> 一日反轉主力出貨確立！
    rev1_triggered = False
    rev1_low = 0.0
    rev1_desc = ""
    if len(df) >= 4 and is_high_for_tp:
        v1 = float(df['Volume'].iloc[-2])
        v2 = float(df['Volume'].iloc[-3])
        vma20_1 = float(df.get('Vol_MA20', df['Volume']).iloc[-2])
        vma20_2 = float(df.get('Vol_MA20', df['Volume']).iloc[-3])
        vma5_1 = float(df.get('Vol_MA5', df['Volume']).iloc[-2])
        vma5_2 = float(df.get('Vol_MA5', df['Volume']).iloc[-3])

        is_v1_heavy = (v1 >= vma20_1 * 1.3 or v1 >= vma5_1 * 1.2)
        is_v2_heavy = (v2 >= vma20_2 * 1.3 or v2 >= vma5_2 * 1.2)

        if is_v1_heavy and is_v2_heavy:
            rev1_low = round(min(float(df['Low'].iloc[-2]), float(df['Low'].iloc[-3])), 2)
            if c < rev1_low:
                rev1_triggered = True
                rev1_desc = f"高檔前兩日連續爆大量，今日收盤 ({c:.2f}元) 跌破兩日大量最低點 ({rev1_low:.2f}元)，一日反轉主力出貨確立！多單果斷全數停利退場！"
                reversal_alerts.append(f"🚨【高檔反轉·跌破兩日大量低點】跌破前兩日爆量低點 {rev1_low:.2f} 元 (主力出貨一日反轉·果斷全數停利)")
                signals.append(f"🚨 高檔跌破連續兩日大量低點 ({rev1_low:.2f}元·主力出貨一日反轉·果斷全數停利)")

    # 現象二：高檔出現爆大量長黑 K 或 長黑吞噬 K 線
    # 若爆量長黑未破前一日低點，但獲利 > 15%，先停利 1/2，次日下跌全數賣出；若已破前低，全數賣出！
    rev2_triggered = False
    rev2_action = ""
    rev2_desc = ""
    if is_high_for_tp and is_black and (vol_ratio >= 1.4 or vol_ratio_5 >= 1.35):
        black_drop = (o - c) / o if o > 0 else 0
        if black_drop >= 0.018 or change_pct <= -2.0:
            rev2_triggered = True
            if c < prev_l:  # 跌破前一日低點 (長黑吞噬 / 貫穿)
                rev2_action = "全數停利賣出"
                rev2_desc = f"高檔爆大量收長黑且跌破前日最低點 ({prev_l:.2f}元) 形成長黑吞噬/貫穿，主力帶頭倒貨大逃殺，多單全數停利賣出！"
                reversal_alerts.append(f"🛑【高檔反轉·爆量長黑吞噬】摜破前低 {prev_l:.2f} 元 (主力帶頭倒貨·多單果斷全數停利)")
                signals.append("🛑 高檔爆量長黑吞噬 (主力倒貨·多單果斷全數停利)")
            else:  # 未破前一日低點
                if swing_gain >= 15.0 or (c >= sma20 * 1.15):
                    rev2_action = "先停利賣出 1/2"
                    rev2_desc = f"高檔爆大量長黑但未跌破前日低點 ({prev_l:.2f}元)，波段獲利已逾 15%：依心法先停利賣出 1/2！次日若續跌破大量低點，剩餘 1/2 全數清倉！"
                    reversal_alerts.append("⚠️【高檔反轉·爆量長黑】獲利逾 15% 且爆量長黑：先停利賣出 1/2！次日若續跌破大量低點全數清倉！")
                    signals.append("⚠️ 高檔爆量長黑未破前低 (獲利逾15%·先停利 1/2，次日破低全出)")
                else:
                    rev2_action = "短線高度警戒，守前低"
                    rev2_desc = f"高檔爆大量長黑未破前日低點 ({prev_l:.2f}元)，嚴密防守該黑K低點 ({l:.2f}元) 與前低，次日開低破低立即停利！"
                    reversal_alerts.append(f"⚠️【高檔反轉·爆量長黑警戒】嚴守前低 {prev_l:.2f} 元與今日低點 {l:.2f} 元，次日轉弱立即停利！")

    # 現象三：高檔出現爆大量長上影線 K 線 (避雷針 / 射擊之星)
    # 若未破前一日低點，但獲利 > 15%，先停利 1/2，次日下跌全數賣出；若破前低全出！
    rev3_triggered = False
    rev3_action = ""
    rev3_desc = ""
    if is_high_for_tp and (vol_ratio >= 1.35 or vol_ratio_5 >= 1.30):
        upper_body = max(c, o)
        upper_shadow = h - upper_body
        body_len = abs(c - o)
        tot_range = h - l + 1e-9
        if upper_shadow >= 1.3 * body_len and (upper_shadow / tot_range) >= 0.45:
            rev3_triggered = True
            if c < prev_l:  # 收盤已破前低
                rev3_action = "全數停利賣出"
                rev3_desc = f"高檔爆大量長上影線且摜破前日低點 ({prev_l:.2f}元)，多頭上攻無力主力逢高倒貨，多單果斷全數停利！"
                reversal_alerts.append(f"🛑【高檔反轉·避雷針破低】高檔爆量長上影線破前低 {prev_l:.2f} 元 (主力逢高出貨·多單全數停利)")
                signals.append("🛑 高檔爆量長上影破前低 (主力逢高倒貨·多單全數停利)")
            else:  # 未破前低
                if swing_gain >= 15.0 or (c >= sma20 * 1.15):
                    rev3_action = "先停利賣出 1/2"
                    rev3_desc = f"高檔爆大量長上影線（避雷針），波段獲利已逾 15%：依心法先停利賣出 1/2！次日若開低走低或跌破前低，剩餘 1/2 全數清倉！"
                    reversal_alerts.append("⚠️【高檔反轉·爆量避雷針】獲利逾 15% 留長上影線：先停利賣出 1/2！次日開低破低全出！")
                    signals.append("⚠️ 高檔爆量長上影避雷針 (獲利逾15%·先停利 1/2，次日開低破低全出)")
                else:
                    rev3_action = "防守避雷針低點"
                    rev3_desc = f"高檔爆大量長上影線，上檔賣壓沉重，守今日低點 {l:.2f} 元，次日開低摜破立即停利！"
                    reversal_alerts.append(f"⚠️【高檔反轉·避雷針警戒】留長上影線，防守低點 {l:.2f} 元，次日破線停利！")

    # 現象四：多頭走勢出現爆大量「頭頭低」盤整，短線多單停利；跌破盤整低點空頭確認，長線多單停利
    rev4_short_triggered = False
    rev4_long_triggered = False
    rev4_desc = ""
    box_low_recent = float(df.iloc[-5:]['Low'].min()) if len(df) >= 5 else l
    if is_high_for_tp and len(df) >= 8:
        # 近期 3~5 日高點低於前方波段高點 (頭頭低盤整)
        peak_idx = df.iloc[-15:]['High'].idxmax()
        peak_h = float(df.loc[peak_idx, 'High'])
        recent_h_max = float(df.iloc[-4:]['High'].max())

        # 嚴謹檢核：波段高點確實曾爆大量，且出現頭頭低滯漲
        peak_vol = float(df.loc[peak_idx, 'Volume'])
        vma20_peak = float(df.get('Vol_MA20', df['Volume']).loc[peak_idx])
        is_peak_heavy_vol = peak_vol >= vma20_peak * 1.35
        is_lower_high = (peak_h > recent_h_max * 1.015) and (df.index.get_loc(peak_idx) < len(df) - 3)

        # 依朱老師心法：高檔爆量頭頭低，且收盤摜破 5MA 操盤線時，短線多單才停利！
        # 若股價依然守穩 5MA 之上，則屬於多頭守線續抱，絕不可自相矛盾判定立即停利
        if is_peak_heavy_vol and is_lower_high and (c < sma5):
            rev4_short_triggered = True
            if c < box_low_recent * 1.001:  # 收盤跌破近期盤整低點
                rev4_long_triggered = True
                rev4_desc = f"多頭高檔爆量頭頭低盤整後，今日收盤 ({c:.2f}元) 跌破盤整低點 ({box_low_recent:.2f}元)【空頭確認】，長線多單依心法全數停利清倉！"
                reversal_alerts.append(f"🚨【高檔反轉·破盤整空頭確認】收盤跌破盤整低點 {box_low_recent:.2f} 元 (空頭確認·長線多單全數停利清倉)")
                signals.append(f"🚨 跌破高檔盤整低點 {box_low_recent:.2f} 元 (空頭確認·長線多單全數停利清倉)")
            else:
                rev4_desc = f"多頭高檔出現爆大量「頭頭低」盤整且摜破 5MA，短線多單依心法立即停利出場！長線多單嚴密防守盤整下緣支撐 ({box_low_recent:.2f}元)！"
                reversal_alerts.append(f"⚠️【高檔反轉·頭頭低破5均】跌破 5MA 操盤線，短線多單停利出場！長線多單守盤整低點 {box_low_recent:.2f} 元！")
                signals.append("⚠️ 高檔爆量頭頭低破5均 (短線多單停利·長線守盤整箱底)")

    # 綜合 CH9 實戰停利導航核心字典
    signals_dict['ch9_take_profit'] = {
        "is_high_for_tp": is_high_for_tp,
        "ma5_tp_hit": ma5_tp_hit,
        "ma5_price": sma5,
        "short_tp_status": short_tp_status,
        "short_tp_rebuy": short_tp_rebuy,
        "ma20_tp_hit": ma20_tp_hit,
        "ma20_price": sma20,
        "long_tp_status": long_tp_status,
        "nearest_target_name": nearest_target[0],
        "nearest_target_price": nearest_target[1],
        "candidate_pressures": candidate_pressures,
        "reversal_alerts": reversal_alerts,
        "rev1_break_2day_low": {
            "triggered": rev1_triggered,
            "two_day_low": rev1_low,
            "desc": rev1_desc
        },
        "rev2_heavy_vol_black": {
            "triggered": rev2_triggered,
            "action": rev2_action,
            "desc": rev2_desc
        },
        "rev3_upper_shadow": {
            "triggered": rev3_triggered,
            "action": rev3_action,
            "desc": rev3_desc
        },
        "rev4_lower_highs_box": {
            "short_triggered": rev4_short_triggered,
            "long_triggered": rev4_long_triggered,
            "box_low": box_low_recent,
            "desc": rev4_desc
        }
    }

    # ----------------------------------------------------
    # 股票套牢診斷與五大實戰解套導航儀 (CH10 散戶常見問題解答 · 五大解套 SOP)
    # ----------------------------------------------------
    peak_60 = float(df.iloc[-60:]['High'].max()) if len(df) >= 60 else float(df['High'].max())
    drawdown_pct = round(max(0.0, (peak_60 - c) / (peak_60 + 1e-9) * 100), 1)

    # 判定 5% 警示機制 (CH10 積極防範：每日檢視若跌幅超過 5% 列為警示股準備賣出)
    is_caution_5pct = (drawdown_pct >= 5.0 and drawdown_pct < 10.0)

    # 均線趨勢與空方特徵
    sma20_down = (sma20 < prev_sma20 * 0.999)
    is_bear = (trend_info.get('trend_status') == "空頭趨勢") or (c < sma20 and sma20_down)
    is_bottoming = signals_dict.get('is_stop_fall_vol', False) or signals_dict.get('bottom_breakout', False) or trend_info.get('higher_lows', False)

    # 套牢位階分類與五大實戰解套 SOP
    if drawdown_pct <= 2.5 or c >= peak_60 * 0.985:
        trap_level = "強勢創高多頭"
        sop_step = 0
        sop_name = "多頭創新高·回後買上漲"
        sop_action = "多頭趨勢不變股價會一直創新高！切勿預設立場懼高，守穩 5MA/20MA 讓利潤奔馳；若欲進場切忌盲目追高，掌握『回後買上漲』拉回量縮守穩均線轉折再切入！"
        mindset_advice = "【散戶第 7 大錯誤：不敢買進價格創新高的股票】98% 散戶認為太高不敢買，因而錯失主升段大飆股！只要趨勢多頭不變，每一次拉回有守都是黃金買點。"
    elif drawdown_pct < 10.0:
        trap_level = "輕微回檔 (<10%)"
        sop_step = 1
        sop_name = "SOP 1: 守進場低點/5MA·果斷停損"
        sop_action = f"波段回檔尚未超過 10% 警戒線，做多以進場 K 線低點 (或 5MA {sma5:.2f}元) 為停損點，收盤跌破立刻執行停損，絕不可拖成大套牢！"
        mindset_advice = "【散戶第 1 大錯誤：當虧損很小時不願賠錢出場】失敗的進場在第一時間都有讓你小賠出場的機會；被情緒左右不願認賠，容易拖延成重度套牢！每日跌幅逾 5% 立即列為警示股準備出場。"
        if is_caution_5pct and is_bear:
            signals.append("⚠️ 自高點回檔已達 5% (觸發警示股防守機制·準備賣出停損)")
    elif 10.0 <= drawdown_pct < 20.0:
        trap_level = "中度套牢 (10%~20%)"
        sop_step = 2
        sop_name = "SOP 2: 反彈遇壓不漲·斷然認賠出場"
        sop_action = f"波段回檔已達 10%~20% 中度套牢區！股票反彈遇均線壓力 (如 20MA {sma20:.2f}元 / 5MA {sma5:.2f}元) 或前高壓力不漲時，斷然認賠出場！"
        mindset_advice = "【散戶第 2 大錯誤：嚴禁向下攤平買進降低成本】向下攤平是在加碼正在下跌的股票！求解套反而卡死更多資金在空頭股。必須趁反彈遇阻時果斷減碼認賠，轉移資金。"
        if is_bear:
            signals.append(f"🟡 自高點回檔達 {drawdown_pct:.1f}% (進入中度套牢區·反彈遇壓斷然認賠出場)")
    else:  # drawdown_pct >= 20.0
        if is_bottoming and not sma20_down:
            trap_level = "重度套牢 (>20%) 打底蓄勢中"
            sop_step = 5
            sop_name = "SOP 5: 大量止跌打底·等反轉多頭再加碼"
            sop_action = "低檔已出現爆大量止跌或初步打底型態，切勿盲目急躁加碼！必須耐心等待打底完成、多頭趨勢確立（底底高、站上揚升 20MA）時再順勢加碼解套！"
            mindset_advice = "底部打底需要時間消化籌碼，打底未完成前嚴禁急著向下攤平，等確認走出第二隻腳轉折多頭才能出手。"
            if is_bear:
                signals.append(f"🟣 自高點回檔重挫 {drawdown_pct:.1f}% 但低檔爆量打底 (耐心等打底完成·多頭確立再加碼)")
        else:
            trap_level = "重度套牢 (>20%) 空頭進行中"
            sop_step = 3
            sop_name = "SOP 3 & 4: 反彈賣出反手做空賺價差解套 / 換股操作"
            sop_action = f"波段重挫已逾 20% 且空頭趨勢進行中！反彈遇下彎 20MA ({sma20:.2f}元) 賣出後【反手做空賺價差解套】（直到出現底底高停止放空回補）；或賣出後【換股操作】其他多頭強勢股獲利解套！"
            mindset_advice = "【認清被套牢的三大後果】短期 3~5 年不一定能解套 (如大立光 6075 套牢 8 年)、公司經營不善恐下市血本無歸、資金失去流動性。反彈遇下彎月線賣出並反手放空，以空方獲利彌補虧損！"
            if is_bear:
                signals.append(f"🚨 自高點回檔重挫 {drawdown_pct:.1f}% (重度套牢空頭進行中·反彈賣出反手做空或換股解套)")

    # 組合反手做空賺價差解套指引
    short_hedge_guide = {
        "is_suitable": is_bear and sma20_down,
        "bounce_resistance": round(sma20, 2),
        "entry_rule": f"反彈至下彎 20MA ({sma20:.2f} 元) 或 5MA ({sma5:.2f} 元) 遇阻收黑時賣出並反手做空",
        "exit_rule": "持續放空賺取下跌價差，直到日線出現「底底高」反轉向上時，空單全數回補、停止操作",
        "stop_rule": f"若強勢長紅突破站穩 20MA ({sma20:.2f} 元) 則空單停損離場"
    }

    # 資金凍結與向下攤平禁令檢核
    stagnant_warning = (signals_dict.get('is_consolidation', False) and vol_ratio < 0.85)

    signals_dict['ch10_trap_diagnosis'] = {
        "peak_60d": round(peak_60, 2),
        "drawdown_pct": drawdown_pct,
        "trap_level": trap_level,
        "is_caution_5pct": is_caution_5pct,
        "sop_step": sop_step,
        "sop_name": sop_name,
        "sop_action": sop_action,
        "mindset_advice": mindset_advice,
        "short_hedge_guide": short_hedge_guide,
        "stagnant_warning": stagnant_warning,
        "average_down_warning": "❌ 【嚴禁向下攤平】向下攤平是在加碼正在下跌的股票，為散戶最致命錯誤！只會卡死更多資金，越套越深！"
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
    # 14大淘汰選股法即時檢核
    # ----------------------------------------------------
    elim_info = check_14_elimination_rules(df, trend_info, last, prev, signals_dict)
    signals_dict['elimination_info'] = elim_info

    # ----------------------------------------------------
    # CH11-2 做多絕對不可進場的 7 大禁忌位置 (做多七不買) 檢核
    # ----------------------------------------------------
    do_not_buy_info = check_do_not_buy_rules(df, trend_info, last, prev, signals_dict)
    signals_dict['ch11_do_not_buy'] = do_not_buy_info

    if do_not_buy_info['pass_all'] and is_bull:
        signals.append("🛡️ 完美避開做多七大禁忌 (符合高勝率進場規範)")
    elif not do_not_buy_info['pass_all']:
        for v in do_not_buy_info['violations'][:1]:
            signals.append(f"⚠️ 做多禁忌：{v[1]}")

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
    if has_long_upper_shadow:
        safety_reasons.append(f"今日盤中留長上影線 (+{upper_shadow_pct:.1f}%) 避雷針，高檔遭遇獲利調節或解套賣壓")
    if c < sma60 and sma20 < sma60:
        safety_reasons.append("季線 (60MA) 下彎壓制，屬空方反彈非主升")
    if vol_ratio >= 3.5 and is_red:
        safety_reasons.append("今日爆量過猛 (超過均量3.5倍)，常伴隨前波解套賣壓，依助教指引宜等次日回測支撐再上漲")
    if res_price > c and (res_price - c) / c <= 0.028:
        safety_reasons.append(f"上方緊臨密集前高頭部壓力 ({res_price:.2f} 元)，空間狹窄風報比差，突破易遇解套回測")
    if signals_dict.get('ma20_death_break', False):
        safety_reasons.append("跌破月線已超過 3 天且月線下彎，依趨勢線鐵律『做多要在月線上，跌破3天助漲未回多頭徹底終結』，嚴禁逆勢做多！")
    if is_false_breakout_dump:
        safety_reasons.append("【致命警訊·假突破誘多】突破長紅3天內長黑灌破最低點，主力誘多出貨必跑！")

    if nearest_bearish_g and 0 <= nearest_bearish_g.get('distance_pct', 99) <= 3.0:
        safety_reasons.append(f"上方緊臨重大空方跳空缺口反壓 ({nearest_bearish_g['rem_bottom']}~{nearest_bearish_g['rem_top']} 元，距現價僅 +{nearest_bearish_g['distance_pct']:.1f}%)，套牢賣壓沉重嚴防逢高摜回")

    # 加入 14 大淘汰檢核項目 (前2項代表性警示)
    if elim_info['is_eliminated']:
        for r in elim_info['reasons'][:2]:
            if r not in safety_reasons:
                safety_reasons.append(f"⚠️ {r}")

    if signals_dict.get('four_ma_not_ready_warning', False):
        safety_reasons.append("四線尚未做好：季線 (60MA) 仍下彎或未多頭排列，上方均線反壓沉重，依朱老師提醒宜先鎖股觀察，切勿過早重倉！")

    is_four_ma_launch = signals_dict.get('bullish_alignment', False) and (signals_dict.get('main_wave_2nd', False) or signals_dict.get('box_range_breakout', False) or signals_dict.get('pullback_buy', False)) and (c >= sma5 and c >= o)

    # 做多七大禁忌強制連動安全評級 (淘汰9成不適合標的)
    v_count = do_not_buy_info.get('violation_count', 0)
    has_chase_violation = any(v[0] in [2, 6] for v in do_not_buy_info.get('violations', []))
    has_fatal_violation = any(v[0] in [1, 4, 5] for v in do_not_buy_info.get('violations', []))

    if not do_not_buy_info.get('pass_all', True):
        for v in do_not_buy_info.get('violations', []):
            safety_reasons.append(f"⚠️ 做多禁忌：{v[1]} ({v[2]})")

    if is_false_breakout_dump or signals_dict.get('ma20_death_break', False) or (has_fatal_violation and v_count >= 2):
        signals_dict['safety_rating'] = "🔴 命中淘汰"
    elif elim_info['is_eliminated'] and not is_four_ma_launch:
        signals_dict['safety_rating'] = "🔴 命中淘汰" if elim_info['eliminated_count'] >= 2 else "🟡 警訊注意"
    elif up_days >= 4 or bias20 >= 12.0 or has_chase_violation:
        signals_dict['safety_rating'] = "🔴 嚴禁追高"
    elif (elim_info['is_eliminated'] and is_four_ma_launch) or (is_multi_bagger and not is_four_ma_launch) or unresolved_blacks or has_long_upper_shadow or (up_days >= 3 and bias20 >= 8.0) or (vol_ratio >= 3.5 and is_red) or (nearest_bearish_g and 0 <= nearest_bearish_g.get('distance_pct', 99) <= 3.0) or signals_dict.get('four_ma_not_ready_warning', False) or (v_count > 0) or (c < o) or (c < sma5):
        signals_dict['safety_rating'] = "🟡 警訊注意"
    else:
        signals_dict['safety_rating'] = "🟢 安全首選"

    signals_dict['safety_reasons'] = safety_reasons

    return signals_dict, signals


def categorize_signals(signals_list: list) -> dict:
    """
    將偵測到的技術分析訊號分類為 5 大實戰維度，避免資訊轟炸與文字牆
    """
    def _categorize(title: str) -> str:
        t_l = title.lower()
        if any(k in t_l for k in ['頭低', '死亡交叉', '下彎', '彈後', '起跌', '放空', '弱勢', '跌破', '並列紅k']):
            return 'bearish'
        if any(k in t_l for k in ['停利', '警戒', '背離', '誘多', '重挫', '防出貨', '四線尚未做好', '尚未做好']):
            return 'exit_risk'
        if any(k in t_l for k in ['爆量', '攻擊量', '盤中強勢', '一點鐘', '換手', '止跌量', '連三紅']):
            return 'volume_timing'
        if any(k in t_l for k in ['黃金交叉', '無敵鐵金剛', '回後準', '第二波', '起漲', '長抱', '糾結突破', '創高無壓']):
            return 'ma'
        if any(k in t_l for k in ['箱型', 'abc', '黑k', '紅k', '軌道', '底', '缺口', '橫盤', '底部反轉']):
            return 'pattern'
        return 'ma'

    categories = {
        'pattern': {'title': '🧱 型態突破', 'color': '#60A5FA', 'bg': '#1E293B', 'border': '#3B82F6', 'items': []},
        'ma': {'title': '📈 均線動能', 'color': '#34D399', 'bg': '#064E3B', 'border': '#10B981', 'items': []},
        'volume_timing': {'title': '⚡ 量能時機', 'color': '#FBBF24', 'bg': '#451A03', 'border': '#F59E0B', 'items': []},
        'exit_risk': {'title': '🛡️ 停利防守', 'color': '#C084FC', 'bg': '#2E1065', 'border': '#8B5CF6', 'items': []},
        'bearish': {'title': '📉 空方警戒', 'color': '#F87171', 'bg': '#450A0A', 'border': '#EF4444', 'items': []}
    }

    for s in signals_list:
        if ' (' in s and s.endswith(')'):
            t = s.split(' (')[0].strip()
            d = s.split(' (')[1][:-1].strip()
        else:
            t = s.strip()
            d = ''
        c_key = _categorize(t)
        categories[c_key]['items'].append({'title': t, 'desc': d, 'raw': s})

    return categories


def compute_bollinger_info(df: pd.DataFrame, vol_ratio: float = None) -> dict:
    """
    獨立計算布林通道 (20MA ± 2σ) 輔助診斷結構，完全隔離於《技術分析全攻略》正課主訊號之外。
    回傳欄位：
      - available: bool
      - upper, mid, lower: float (上軌 +2σ、中軌 20MA、下軌 -2σ)
      - bandwidth_pct: float (通道頻寬 %)
      - percent_b: float (%B 位階百分比，100%=上軌，50%=中軌，0%=下軌)
      - mid_dir: str ('上揚' / '下彎' / '走平')
      - band_state, band_state_color: 通道狀態 (縮口擠壓 / 開口擴張 / 水平盤整 / 常態通道)
      - price_position, price_pos_color: 股價位階 (貼上軌運行 / 回測中軌 20MA / 觸及或跌破下軌 等)
      - squeeze_breakout, upper_band_walk, lower_band_rebound, mid_band_pullback: bool
      - triggers: list[dict] (布林專屬觸發提示)
    """
    if df is None or len(df) < 20 or 'Close' not in df.columns:
        return {"available": False}

    close_s = df['Close'].astype(float)
    mid_s = close_s.rolling(20).mean()
    std_s = close_s.rolling(20).std()

    bb_mid = float(mid_s.iloc[-1]) if pd.notna(mid_s.iloc[-1]) else 0.0
    cur_std = float(std_s.iloc[-1]) if pd.notna(std_s.iloc[-1]) else 0.0
    if bb_mid <= 0:
        return {"available": False}

    bb_upper = bb_mid + 2.0 * cur_std
    bb_lower = bb_mid - 2.0 * cur_std

    c = float(close_s.iloc[-1])
    o = float(df['Open'].iloc[-1]) if 'Open' in df.columns else c
    h = float(df['High'].iloc[-1]) if 'High' in df.columns else c
    l = float(df['Low'].iloc[-1]) if 'Low' in df.columns else c
    prev_c = float(close_s.iloc[-2]) if len(df) >= 2 else c
    prev_l = float(df['Low'].iloc[-2]) if (len(df) >= 2 and 'Low' in df.columns) else prev_c
    is_red = (c >= o) and (c >= prev_c * 0.998)

    if vol_ratio is None:
        if 'Volume' in df.columns and len(df) >= 6:
            v_ma5 = float(df['Volume'].iloc[-6:-1].mean())
            vol_ratio = float(df['Volume'].iloc[-1]) / (v_ma5 + 1e-9) if v_ma5 > 0 else 1.0
        else:
            vol_ratio = 1.0

    prev_mid = float(mid_s.iloc[-2]) if (len(df) >= 2 and pd.notna(mid_s.iloc[-2])) else bb_mid
    prev3_mid = float(mid_s.iloc[-4]) if (len(df) >= 4 and pd.notna(mid_s.iloc[-4])) else prev_mid
    prev_std = float(std_s.iloc[-2]) if (len(df) >= 2 and pd.notna(std_s.iloc[-2])) else cur_std
    prev_bb_upper = prev_mid + 2.0 * prev_std
    prev_bb_lower = prev_mid - 2.0 * prev_std

    bw_series = ((mid_s + 2.0 * std_s) - (mid_s - 2.0 * std_s)) / (mid_s + 1e-9)
    bw_curr = (bb_upper - bb_lower) / (bb_mid + 1e-9)
    bw_prev = float(bw_series.iloc[-2]) if (len(df) >= 2 and pd.notna(bw_series.iloc[-2])) else bw_curr
    valid_bws = bw_series.iloc[-20:-1].dropna()
    min_width_20 = float(valid_bws.min()) if len(valid_bws) >= 5 else bw_curr
    avg_width_20 = float(valid_bws.mean()) if len(valid_bws) >= 5 else bw_curr

    bandwidth_pct = round(bw_curr * 100.0, 2)
    band_span = bb_upper - bb_lower
    percent_b = round(((c - bb_lower) / (band_span + 1e-9)) * 100.0, 1) if band_span > 0 else 50.0

    # 中軌 20MA 方向
    mid_chg_3d = (bb_mid - prev3_mid) / (prev3_mid + 1e-9)
    if mid_chg_3d > 0.004:
        mid_dir = "↗ 上揚"
    elif mid_chg_3d < -0.004:
        mid_dir = "↘ 下彎"
    else:
        mid_dir = "→ 走平"

    # 1. 通道狀態判定：縮口擠壓 / 開口擴張 / 水平盤整 / 常態趨勢通道
    is_squeeze = (bw_curr <= 0.12) or (len(valid_bws) >= 10 and bw_curr <= min_width_20 * 1.10 and bw_curr <= 0.18)
    is_expanding = (bw_curr > bw_prev * 1.07) and (bw_curr >= avg_width_20 * 1.05 or c > bb_upper or c < bb_lower)
    is_flat_box = abs(mid_chg_3d) <= 0.006 and not is_expanding

    if is_squeeze and not (c > bb_upper and bw_curr > bw_prev * 1.12):
        band_state = "🤏 縮口擠壓 (Squeeze)"
        band_state_color = "#FBBF24"
    elif is_expanding:
        band_state = "📣 開口擴張 (波動放大)"
        band_state_color = "#38BDF8"
    elif is_flat_box:
        band_state = "↔️ 水平盤整 (箱型區間)"
        band_state_color = "#CBD5E1"
    else:
        band_state = "🌊 常態趨勢通道"
        band_state_color = "#94A3B8"

    # 2. 股價位階判定：貼上軌運行 / 回測中軌 20MA / 觸及或跌破下軌
    dist_mid_pct = abs(c - bb_mid) / (bb_mid + 1e-9)
    if c > bb_upper:
        price_position = "🚀 站上/突破上軌 (+2σ外)"
        price_pos_color = "#FF4D4F"
    elif c >= bb_upper * 0.985 or percent_b >= 85.0:
        price_position = "🔥 貼上軌運行 (強勢貼帶)"
        price_pos_color = "#FB923C"
    elif dist_mid_pct <= 0.015 or (l <= bb_mid <= h):
        price_position = "🎯 回測/貼近中軌 20MA"
        price_pos_color = "#38BDF8"
    elif c < bb_lower:
        price_position = "❄️ 跌破下軌 (-2σ外超跌)"
        price_pos_color = "#EF4444"
    elif c <= bb_lower * 1.015 or percent_b <= 15.0:
        price_position = "🛡️ 觸及下軌邊緣 (測試下軌)"
        price_pos_color = "#34D399"
    elif c > bb_mid:
        price_position = "🟢 中上軌多方區"
        price_pos_color = "#4ADE80"
    else:
        price_position = "🟠 中下軌弱勢區"
        price_pos_color = "#F59E0B"

    # 3. 專屬觸發提示 (4招實戰精華)
    squeeze_breakout = bool(prev_c <= prev_bb_upper and c > bb_upper and is_red and vol_ratio >= 1.5 and min_width_20 <= 0.12)
    upper_band_walk = bool(c >= bb_upper * 0.985 and bb_mid > prev_mid and is_red)
    lower_band_rebound = bool((prev_c < prev_bb_lower or prev_l < prev_bb_lower) and c > bb_lower and is_red)
    mid_band_pullback = bool(bb_mid > prev_mid and prev_c >= prev_mid and l <= bb_mid * 1.015 and c >= bb_mid and is_red)

    triggers = []
    if squeeze_breakout:
        triggers.append({
            "badge": "🎯 縮口帶量突破",
            "color": "#FF4D4F",
            "desc": f"前波通道極度收斂（最窄頻寬 {round(min_width_20*100,1)}%），今日放量（{vol_ratio:.1f}x）實體紅K突破上軌 {bb_upper:.2f} 元，屬布林波動率起爆訊號。"
        })
    if upper_band_walk:
        triggers.append({
            "badge": "🚀 貼上軌抱單",
            "color": "#FB923C",
            "desc": f"股價緊貼上軌（{bb_upper:.2f} 元）且中軌 20MA 向上翻揚，強勢貼帶運行中，布林法以動態中軌 {bb_mid:.2f} 元作為波段移動停利參考。"
        })
    if mid_band_pullback:
        triggers.append({
            "badge": "💎 回測中軌有守",
            "color": "#38BDF8",
            "desc": f"中軌 20MA（{bb_mid:.2f} 元）維持上揚，股價回測中軌不破收紅K，符合布林強勢股回測中軌低接觀察條件。"
        })
    if lower_band_rebound:
        triggers.append({
            "badge": "🪃 破下軌迅速收回",
            "color": "#34D399",
            "desc": f"前日觸破下軌後，今日紅K迅速站回下軌（{bb_lower:.2f} 元）之上，短線超跌恐慌宣洩，可觀察朝中軌 {bb_mid:.2f} 元反彈力道（若中軌下彎須防反壓）。"
        })
    if is_flat_box and not triggers:
        triggers.append({
            "badge": "📦 水平箱型區間",
            "color": "#CBD5E1",
            "desc": f"中軌 20MA 走平，布林上軌（{bb_upper:.2f} 元）與下軌（{bb_lower:.2f} 元）形成水平箱型區間，未帶量開口前屬區間震盪。"
        })

    return {
        "available": True,
        "upper": round(bb_upper, 2),
        "mid": round(bb_mid, 2),
        "lower": round(bb_lower, 2),
        "bandwidth_pct": bandwidth_pct,
        "min_width_20_pct": round(min_width_20 * 100.0, 2),
        "percent_b": percent_b,
        "mid_dir": mid_dir,
        "band_state": band_state,
        "band_state_color": band_state_color,
        "price_position": price_position,
        "price_pos_color": price_pos_color,
        "squeeze_breakout": squeeze_breakout,
        "upper_band_walk": upper_band_walk,
        "lower_band_rebound": lower_band_rebound,
        "mid_band_pullback": mid_band_pullback,
        "triggers": triggers,
    }

