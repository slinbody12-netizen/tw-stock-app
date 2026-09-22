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
    if not trend_info.get('higher_lows', False) and (trend_info.get('lower_lows', False) or (c < sma60 and not signals_dict.get('bottom_breakout', False))):
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
    if signals_dict.get('is_multi_bagger', False):
        bagger_m = signals_dict.get('bagger_multiple', 1.0)
        reasons.append(f"【規則4·暴漲{bagger_m:.1f}倍高檔區】波段漲幅已翻倍，主力獲利豐厚隨時出貨，嚴禁長抱")
        
    # 規則 5：高檔爆量連三黑
    if len(df) >= 3 and (is_high or signals_dict.get('is_multi_bagger', False)):
        last3 = df.iloc[-3:]
        all_black = (last3['Close'] <= last3['Open']).all()
        any_heavy = (last3['Volume'] >= last3.get('Vol_MA5', last3['Volume']) * 1.25).any()
        if all_black and any_heavy:
            reasons.append("【規則5·高檔爆量連三黑】高檔連續收黑倒貨，典型三黑烏鴉出貨訊號")
            
    # 規則 6：前波爆量黑K重壓未化解
    if signals_dict.get('unresolved_blacks'):
        reasons.append(f"【規則6·爆量黑K套牢重壓】前方有巨量黑K高點 ({signals_dict['unresolved_blacks'][-1]['high']}元) 重壓未化解")
        
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
    if signals_dict.get('is_multi_bagger', False) and trend_info.get('lower_highs', False):
        reasons.append("【規則10·翻倍股頭頭低】倍數大漲後反彈不過前高，確認高檔做頭轉空")
        
    # 規則 11：指標 (KD) 高檔背離
    if len(df) >= 12 and 'K' in df.columns:
        recent_bars = df.iloc[-12:]
        if c >= float(recent_bars['Close'].max()) * 0.992:
            max_k = float(recent_bars['K'].max())
            cur_k = float(last.get('K', 50))
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
        if shadow_cnt >= 5:
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
        "flat_base_breakout": False,  # 一字底
        "n_pattern_bottom": False,    # N字底
        "rounding_bottom": False,     # 圓弧底
        "is_attack_vol": False,       # 攻擊量 (5MA量 1.25倍以上)
        "is_stop_fall_vol": False,    # 止跌量 (5MA量 50%以下急縮且不破低)
        "is_volume_price_divergence": False, # 量價背離 (價漲量縮 / 價平量增)
        "elimination_info": {"is_eliminated": False, "reasons": []}, # 14大淘汰檢核

        # 波段做空核心子策略
        "lower_highs_lows": False,    # 頭低底低 (六字訣空頭確認)
        "rebound_short": False,       # 彈後準進場 (反彈測線無力·短線空點)
        "top_breakdown": False,       # 頂部起跌 (高檔頭部放量長黑破線)
        "low_breakdown": False,       # 低檔起跌 (破前低弱勢續殺)
        "death_cross_5_20": False,    # 雙線死亡交叉 / 雙線下彎
        "ma_squeeze_breakdown": False,# 🌀 均線糾結跌破 (四線空排崩跌初跌段)
        "bearish_alignment_4ma": False,# 均線四線空排 (5 < 10 < 20 < 60MA 全數下彎)
        "ma20_death_break": False,    # 🔴 跌破月線3天助漲未回且月線下彎 (多頭終結清倉)
        "flat_top_breakdown": False,  # 一字頭 (平躺橫盤跌破)
        "n_pattern_top": False,       # 倒N字底 (反彈不過前高再破低)
        "rounding_top": False,        # 圓弧頂 (頭部蓋頂)
        
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
    v_ma5 = float(last['Vol_MA5']) if 'Vol_MA5' in last and not np.isnan(last['Vol_MA5']) else (float(df['Volume'].tail(5).mean()) if len(df) >= 5 else v)
    v_ma20 = float(last['Vol_MA20']) if 'Vol_MA20' in last and not np.isnan(last['Vol_MA20']) else v
    vol_ratio_5 = round(v / v_ma5, 2) if v_ma5 > 0 else 1.0
    vol_ratio_20 = round(v / v_ma20, 2) if v_ma20 > 0 else 1.0
    vol_ratio = vol_ratio_5  # 標準：以 5MA 基本量為基準比率

    prev_c = round(float(prev['Close']), 2)
    prev_h = round(float(prev['High']), 2)
    prev_l = round(float(prev['Low']), 2)
    change_pct = ((c - prev_c) / prev_c) * 100 if prev_c > 0 else 0
    is_red = (c >= o)

    # 實體與上影線分析 (用以精準識別與過濾「避雷針 / 衝高拉回」)
    body = abs(c - o)
    upper_shadow = max(0.0, h - max(o, c))
    total_range = max(0.01, h - l)
    upper_shadow_ratio = upper_shadow / total_range
    upper_shadow_pct = round((upper_shadow / c) * 100, 2) if c > 0 else 0.0

    # 長上影線（避雷針）判定：上影線佔全日高低振幅 40% 以上，且相對於收盤價超過 1.2%
    has_long_upper_shadow = (upper_shadow_ratio >= 0.40 and upper_shadow_pct >= 1.2) or (upper_shadow >= body * 1.4 and upper_shadow_pct >= 1.0)
    # 實體飽滿收高 (無長上影線)：收在當日最高點 1.5% 內，或上影線小於實體紅K 0.6 倍
    is_solid_bull = (h - c) <= (c * 0.015) or (upper_shadow <= body * 0.6)

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
    if vol_ratio >= 2.0 or abs(change_pct) >= 5.0:
        chili = 3
    elif vol_ratio >= 1.3 or abs(change_pct) >= 2.5:
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
    # 策略 🏆：無敵鐵金剛 / 三線合一 (官方 App 最高勝率 7~8 成旗艦波段戰法)
    # 實戰心法鐵律 (大師核心操盤心法)：
    # 1. 轉折波：多頭型態已確認 (底底高 + 頭頭高，即 is_bull)
    # 2. 雙線翻揚：5MA >= 20MA 且 5MA 走升 (is_5ma_rising)、20MA 走平或向上翻揚
    # 3. 今日 K 棒：當日收實體紅 K (c >= o) 且收盤價站穩 5MA 操盤線 (c >= sma5)
    # 操作紀律：買進後守穩 5MA 一路續抱，跌破 5MA 立即紀律停利出場！
    # ----------------------------------------------------
    is_20ma_rising = (sma20 >= prev_sma20 * 0.998)
    if is_bull and sma5 >= sma20 and is_5ma_rising and is_20ma_rising and is_red and (c >= sma5):
        signals_dict['iron_man'] = True
        signals.append("🏆 無敵鐵金剛 (多頭確立+雙線翻揚+今日紅K站上5MA)")

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

    is_5ma_turning = is_5ma_rising or (c >= sma5 and sma5 >= df.iloc[-2]['SMA_5'] * 0.99) or (sma20 >= df.iloc[-2]['SMA_20'] and c >= sma5)
    if (is_bull or signals_dict['golden_cross_5_20'] or sma5 >= sma20) and tested_ma and not_broken_support and is_red and stand_on_5ma and is_5ma_turning:
        signals_dict['pullback_buy'] = True
        signals.append("回後準進場 (拉回測線有守，轉折紅K站回5MA)")

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
    # 策略 E：高檔起漲 (強勢多頭高檔休息後再發動)
    # ----------------------------------------------------
    if c >= sma60 and sma5 > sma20 and change_pct >= 1.5 and is_red and (c >= df.iloc[-10:-1]['High'].max() * 0.99) and is_5ma_rising:
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

        # 四線離散在 5.2% 以內（四線高度靠攏平躺），且過去 30~50 天橫盤振幅小於 25% (低檔長期打底)
        is_ma_squeezed = (ma_dispersion <= 0.052) or (abs(sma5 - sma20) / (sma20 + 1e-9) <= 0.035 and abs(sma10 - sma20) / (sma20 + 1e-9) <= 0.035)
        # 一口氣站上/突破四線糾結
        is_standing_all_mas = (c >= sma5 and c >= sma10 and c >= sma20 and c >= (sma60 * 0.992))

        if amplitude <= 0.25 and is_ma_squeezed and is_standing_all_mas and is_red and is_5ma_rising and (c >= rng_max * 0.98 or vol_ratio >= 1.05 or change_pct >= 0.8):
            signals_dict['ma_squeeze_breakout'] = True
            signals_dict['flat_base_breakout'] = True
            signals.append("均線糾結突破 (四線糾結起漲第一根)")

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
    if (is_bear or sma5 <= sma20) and tested_res_or_ma and not_broken_res and is_black and c <= sma5 and is_5ma_falling_or_turn:
        signals_dict['rebound_short'] = True
        signals.append("彈後準進場 (反彈測線無力，轉折黑K跌破5MA)")

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

    # 量價背離：價漲量急縮背離 或 高檔滯漲爆量
    is_vp_div_bull = (change_pct >= 1.2 and vol_ratio_5 <= 0.7)
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
    # 若前高壓力小於或等於現價（代表已突破或在歷史高點），目標價依「等幅對稱波」或 +10% 測距滿足點
    if res_price <= c * 1.02:
        calc_target = round(c + max(c * 0.08, c - sup_price), 2)
    else:
        calc_target = res_price

    stop_loss = round(min(l, sup_price), 2)
    if stop_loss >= c:
        stop_loss = round(c * 0.95, 2)

    risk = max(0.01, c - stop_loss)
    reward = max(0.01, calc_target - c)
    rr_ratio = round(reward / risk, 1)
    risk_pct = round((risk / c) * 100, 1)
    reward_pct = round((reward / c) * 100, 1)

    signals_dict['swing_3_5d'] = {
        "stop_loss": stop_loss,
        "ma5_defend": sma5,
        "target_res": calc_target,
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
    # 14大淘汰選股法即時檢核
    # ----------------------------------------------------
    elim_info = check_14_elimination_rules(df, trend_info, last, prev, signals_dict)
    signals_dict['elimination_info'] = elim_info

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

    # 加入 14 大淘汰檢核項目 (前2項代表性警示)
    if elim_info['is_eliminated']:
        for r in elim_info['reasons'][:2]:
            if r not in safety_reasons:
                safety_reasons.append(f"⚠️ {r}")

    if is_false_breakout_dump or signals_dict.get('ma20_death_break', False) or elim_info['eliminated_count'] >= 2 or up_days >= 4 or bias20 >= 12.0:
        signals_dict['safety_rating'] = "🔴 命中淘汰" if elim_info['is_eliminated'] else "🔴 嚴禁追高"
    elif elim_info['is_eliminated'] or is_multi_bagger or unresolved_blacks or has_long_upper_shadow or (up_days >= 3 and bias20 >= 8.0) or (vol_ratio >= 3.5 and is_red):
        signals_dict['safety_rating'] = "🟡 警訊注意"
    else:
        signals_dict['safety_rating'] = "🟢 安全首選"

    signals_dict['safety_reasons'] = safety_reasons

    return signals_dict, signals
