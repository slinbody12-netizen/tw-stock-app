"""
AI 實戰操盤副駕駛 (Trading Copilot) 核心引擎
功能：
1. 每日尾盤自動嚴選唯一首選標的 (12:40 - 13:30 專屬作戰指示)
2. 個人實戰持股持久化管理 (本地/雲端同步)
3. 每日全自動持股盯盤守護 (停損警示、達標停利、回測加碼、安心續抱)
"""

import os
import json
import datetime
import pandas as pd
import numpy as np

from core.data_fetcher import fetch_stock_kline
from core.wave_engine import calculate_turning_points
from core.trend_analyzer import analyze_trend
from core.signal_detector import detect_signals
from core.screener import scan_stocks

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_portfolio.json")

def load_portfolio() -> list:
    """讀取使用者在庫實戰持股名冊"""
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    try:
        with open(PORTFOLIO_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading portfolio: {e}")
        return []

def save_portfolio(portfolio: list) -> bool:
    """保存持股名冊至磁碟"""
    try:
        os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving portfolio: {e}")
        return False

def add_holding(code: str, name: str, buy_price: float, stop_loss: float = None, target_price: float = None, 
                strategy: str = "回後準進場", buy_reason: str = "", shares: int = 1000, trade_type: str = "現股",
                buy_date: str = None) -> dict:
    """使用者點擊【我買了】或手動新增時，新增持股追蹤"""
    portfolio = load_portfolio()
    today_str = buy_date if buy_date else datetime.datetime.now().strftime("%Y-%m-%d")
    holding_id = f"port_{code}_{trade_type}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    buy_p = float(buy_price)
    stop_p = float(stop_loss) if stop_loss is not None and float(stop_loss) > 0 else round(buy_p * 0.95, 2)
    target_p = float(target_price) if target_price is not None and float(target_price) > 0 else round(buy_p * 1.10, 2)

    new_item = {
        "id": holding_id,
        "code": code,
        "name": name,
        "buy_date": today_str,
        "buy_price": buy_p,
        "stop_loss": stop_p,
        "target_price": target_p,
        "strategy": strategy,
        "buy_reason": buy_reason,
        "shares": int(shares),
        "trade_type": trade_type,
        "status": "HOLDING",
        "created_at": datetime.datetime.now().isoformat(),
        "history_logs": [
            {
                "date": today_str,
                "event": "BUY",
                "note": f"以 {buy_p} 元進場買進 ({trade_type})，初始防守價 {stop_p} 元，波段目標價 {target_p} 元。"
            }
        ]
    }
    portfolio.append(new_item)
    save_portfolio(portfolio)
    return new_item

def load_preset_user_holdings() -> tuple[int, list]:
    """
    一鍵載入使用者專屬 4 檔持股 (美時、麗正、晟銘電現股與融資、勤誠)
    """
    presets = [
        {"code": "1795", "name": "美時", "buy_price": 268.11, "trade_type": "現股", "shares": 1000, "buy_reason": "歷史波段建倉 (尋求下一波反彈解套賣點)"},
        {"code": "2302", "name": "麗正", "buy_price": 45.37, "trade_type": "現股", "shares": 1000, "buy_reason": "歷史建倉 (接近成本，尋求一波反彈保本出清)"},
        {"code": "3013", "name": "晟銘電", "buy_price": 114.84, "trade_type": "現股", "shares": 1000, "buy_reason": "歷史現股建倉 (尋求反彈高點減碼逃命)"},
        {"code": "3013", "name": "晟銘電", "buy_price": 88.34, "trade_type": "融資", "shares": 1000, "buy_reason": "融資持股 (利息與維持率壓力，鎖定88.5元平手解套)"},
        {"code": "8210", "name": "勤誠", "buy_price": 1088.96, "trade_type": "現股", "shares": 1000, "buy_reason": "伺服器龍頭歷史建倉 (尋求月線/反彈波賣點)"},
    ]
    portfolio = load_portfolio()
    added_count = 0
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    for p in presets:
        exists = any(
            h.get("code") == p["code"] and 
            h.get("trade_type", "現股") == p["trade_type"] and 
            abs(float(h.get("buy_price", 0)) - p["buy_price"]) < 0.01 and 
            h.get("status") == "HOLDING" 
            for h in portfolio
        )
        if not exists:
            h_id = f"port_{p['code']}_{p['trade_type']}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{added_count}"
            portfolio.append({
                "id": h_id,
                "code": p["code"],
                "name": p["name"],
                "buy_date": today_str,
                "buy_price": float(p["buy_price"]),
                "stop_loss": 0.0,
                "target_price": 0.0,
                "strategy": "解套救援雷達",
                "buy_reason": p["buy_reason"],
                "trade_type": p["trade_type"],
                "shares": int(p["shares"]),
                "status": "HOLDING",
                "created_at": datetime.datetime.now().isoformat(),
                "history_logs": [
                    {
                        "date": today_str,
                        "event": "PRESET_LOAD",
                        "note": f"載入庫存：以 {p['buy_price']} 元買進 {p['trade_type']}，啟動套牢解套與高點賣點雷達。"
                    }
                ]
            })
            added_count += 1
    if added_count > 0:
        save_portfolio(portfolio)
    return added_count, portfolio


def close_holding(holding_id: str, sell_price: float, sell_reason: str = "手動獲利/停損出場") -> bool:
    """使用者點擊【我賣了】時，結算獲利並歸檔"""
    portfolio = load_portfolio()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    found = False
    for item in portfolio:
        if item.get("id") == holding_id:
            item["status"] = "CLOSED"
            item["sell_date"] = today_str
            item["sell_price"] = float(sell_price)
            item["sell_reason"] = sell_reason
            buy_p = float(item["buy_price"])
            shares = int(item.get("shares", 1000))
            item["realized_pnl_pct"] = round(((sell_price - buy_p) / buy_p) * 100, 2)
            item["realized_pnl_amt"] = round((sell_price - buy_p) * shares, 0)
            item.setdefault("history_logs", []).append({
                "date": today_str,
                "event": "SELL",
                "note": f"以 {sell_price} 元結算出場 ({sell_reason})，實現損益: {item['realized_pnl_pct']}%"
            })
            found = True
            break
    if found:
        save_portfolio(portfolio)
    return found

def delete_holding(holding_id: str) -> bool:
    """刪除單筆紀錄"""
    portfolio = load_portfolio()
    portfolio = [p for p in portfolio if p.get("id") != holding_id]
    return save_portfolio(portfolio)

# ========================================================
# 核心大腦 1：今日尾盤 AI 唯一首選推薦 (魔鬼級 5 重濾網)
# ========================================================
def get_copilot_recommendation(force_refresh: bool = False, enable_realtime: bool = True) -> dict:
    """
    全自動運算今日 12:40 - 13:30 尾盤作戰精選 Top 5 作戰名冊
    嚴格遵循朱家泓實戰鐵律：
    1. 做多轉折波精華（回後買上漲首選、底部放量起漲、均線糾結突破、多頭排列起跑）
    2. 操盤線 5MA 走平向上，收盤站穩 5MA
    3. 拒絕避雷針（長上影線主力出貨）
    4. 拒絕暴漲 2 倍以上高檔風險股
    5. 安全評級排除嚴禁追高，風報比健康
    6. 依品質分數與風報比嚴選 Top 1 ~ Top 5
    """
    candidates = scan_stocks(strategy="全部", direction="多", limit=100, force_refresh=force_refresh, enable_realtime=enable_realtime)
    
    qualified = []
    for s in candidates:
        sig = s.get('signals_dict', {})
        swing = sig.get('swing_3_5d', {})
        c = float(s.get('close', 0))
        
        # 1. 策略必須是做多攻擊/轉折型態之一
        is_pullback = sig.get('pullback_buy', False)
        is_bottom = sig.get('bottom_breakout', False) or sig.get('consolidation_breakout_imminent', False)
        is_bull_break = (sig.get('higher_highs_lows', False) or s.get('is_bull', False)) and float(s.get('change_pct', 0)) >= 0
        is_gold_cross = sig.get('golden_cross_5_20', False)
        
        if not (is_pullback or is_bottom or is_bull_break or is_gold_cross):
            continue
            
        # 2. 操盤線 5MA 走升且收盤站穩 5MA
        if not (s.get('is_5ma_rising', True) and s.get('above_5ma', True)):
            continue
            
        # 3. 避雷針剔除
        if sig.get('has_long_upper_shadow', False):
            continue
            
        # 4. 暴漲高檔剔除
        if sig.get('is_multi_bagger', False):
            continue
            
        # 5. 安全評級排除嚴禁追高
        safety = s.get('safety_rating', '')
        if "嚴禁" in safety:
            continue
            
        # 6. 風報比檢驗 (至少 1.1 以上)
        rr = float(swing.get('rr_ratio', 0))
        if rr < 1.1:
            continue
            
        # 優先分數加權
        score = float(s.get('quality_score', 0))
        if is_pullback:
            score += 25  # 回後準進場是尾盤最高勝率型態
        elif is_bottom:
            score += 20  # 底部突破
        elif is_gold_cross:
            score += 15
        if s.get('chili_count', 1) >= 2:
            score += 15  # 主力動能支持
        if rr >= 2.0:
            score += 20  # 風報比極佳
        elif rr >= 1.5:
            score += 10
            
        qualified.append({
            "stock": s,
            "score": score,
            "is_pullback": is_pullback,
            "is_bottom": is_bottom,
            "rr": rr
        })
        
    if not qualified:
        return {
            "has_pick": False,
            "picks": [],
            "advice_title": "🛑 今日大盤偏弱或無完美訊號，建議【空手觀望，現金為王】",
            "advice_detail": "經技術分析全攻略引擎 5 重嚴格濾網檢驗，全市場今日無符合「回後測線有守且風報比合格」之安全買點。朱老師心法：『看不懂不買、沒條件不買』，寧可錯過也不要貿然追高！"
        }
        
    # 依加權分數排序
    qualified.sort(key=lambda x: x['score'], reverse=True)
    top_items = qualified[:5]
    
    badges = [
        "👑 No.1 唯一首選",
        "🥈 No.2 戰術精選",
        "🥉 No.3 戰術精選",
        "🎖️ No.4 戰術精選",
        "🎖️ No.5 戰術精選"
    ]
    
    picks = []
    for idx, item in enumerate(top_items):
        stk = item['stock']
        stk_sig = stk.get('signals_dict', {})
        stk_swing = stk_sig.get('swing_3_5d', {})
        close_p = float(stk['close'])
        stop_p = float(stk_swing.get('stop_loss', close_p * 0.95))
        target_p = float(stk_swing.get('target_res', close_p * 1.10))
        risk_pct = round(((close_p - stop_p) / close_p) * 100, 1)
        reward_pct = round(((target_p - close_p) / close_p) * 100, 1)
        
        strat_name = "回後準進場 (回後買上漲)" if item['is_pullback'] else ("底部起漲 (放量起跑點)" if item.get('is_bottom') else "多頭確認 (強勢起漲)")
        
        reasons = []
        if item['is_pullback']:
            reasons.append("🎯 <b>拉回測線有守</b>：前幾日回測均線支撐未跌破，今日轉折紅K確認站回 5MA 操盤線。")
        elif item.get('is_bottom'):
            reasons.append("🌱 <b>低檔放量起跑</b>：橫盤打底完成，首度出量紅K突破均線糾結。")
        else:
            reasons.append("🔥 <b>多頭排列攻擊</b>：均線多頭排列，股價站穩 5MA 展開波段推升。")
            
        reasons.append(f"📈 <b>操盤線翻揚助漲</b>：5MA 走平或翻揚向上，短線多頭慣性強勁。")
        reasons.append(f"⚖️ <b>絕佳風報比 1 : {stk_swing.get('rr_ratio', item['rr'])}</b>：下方防守空間僅 -{risk_pct}%，上方前高頸線潛在報酬 +{reward_pct}%。")
        if stk.get('chili_count', 1) >= 2:
            reasons.append(f"🌶️ <b>主力籌碼支持</b>：獲得主力特定買盤推升，動能評級達 {stk.get('chili_count')} 根辣椒。")
        if stk.get('major_cost', 0) > 0:
            reasons.append(f"💼 <b>大戶成本優勢</b>：主力5日建倉均價 {stk.get('major_cost')} 元，現價評定【{stk.get('cost_badge')}】。")
            
        action_plan = (
            f"⏰ <b>實戰操作指引</b>：今日 <b>12:40 - 13:30 尾盤</b>，若股價維持在 <b>{close_p} 元附近（收盤站穩 5MA）</b>，"
            f"即可於尾盤現價進場；進場後嚴格遵守紀律，以 <b>{stop_p} 元</b> 為短線停損防守點（跌破無條件離場），"
            f"波段目標先看前波壓力 <b>{target_p} 元</b>！"
        )
        
        picks.append({
            "rank": idx + 1,
            "rank_badge": badges[idx] if idx < len(badges) else f"No.{idx+1} 戰術精選",
            "code": stk['code'],
            "name": stk['name'],
            "market": stk.get('market', 'TW'),
            "industry": stk.get('industry', ''),
            "close": close_p,
            "change_pct": stk['change_pct'],
            "strategy": strat_name,
            "stop_loss": stop_p,
            "target_price": target_p,
            "risk_pct": risk_pct,
            "reward_pct": reward_pct,
            "rr_ratio": stk_swing.get('rr_ratio', item['rr']),
            "ma5": stk.get('sma5', close_p),
            "chili_count": stk.get('chili_count', 1),
            "major_cost": stk.get('major_cost', 0.0),
            "foreign_cost": stk.get('foreign_cost', 0.0),
            "cost_diff_pct": stk.get('cost_diff_pct', 0.0),
            "cost_badge": stk.get('cost_badge', ''),
            "why_buy": reasons,
            "action_plan": action_plan
        })
        
    top = picks[0]
    return {
        "has_pick": True,
        "picks": picks,
        "code": top['code'],
        "name": top['name'],
        "market": top['market'],
        "industry": top['industry'],
        "close": top['close'],
        "change_pct": top['change_pct'],
        "strategy": top['strategy'],
        "stop_loss": top['stop_loss'],
        "target_price": top['target_price'],
        "risk_pct": top['risk_pct'],
        "reward_pct": top['reward_pct'],
        "rr_ratio": top['rr_ratio'],
        "ma5": top['ma5'],
        "chili_count": top['chili_count'],
        "why_buy": top['why_buy'],
        "action_plan": top['action_plan']
    }

# ========================================================
# 核心大腦 2：全自動持股盯盤守護神 (持股動態診斷)
# ========================================================
def inspect_portfolio(portfolio: list) -> list:
    """
    遍歷使用者庫存，抓取最新日K與即時盤中撮合價，
    自動執行朱家泓常態波段診斷 + 套牢解套與高點賣點作戰雷達：
    1. 🔴 破保命底線 / 🚨 破線停損 (摜破波段前底或停損線，立即出場防守)
    2. ⚠️ 融資斷頭警戒 (針對融資標的，監控維持率與平手解套賣點)
    3. 🟡 逼近反彈高點 (月線/前高密集重壓，建議掛單分批賣出)
    4. 🟢 反彈推升中 (守穩 5MA，以 5MA 為移動防守續抱等賣點)
    5. 🟠 跌破 5MA 短線轉弱 (反彈動能受阻，提高戒備)
    6. 🏁 達標停利 / ➕ 回測加碼 / 🛡️ 安心續抱 (獲利波段守護)
    """
    results = []
    for item in portfolio:
        if item.get("status") != "HOLDING":
            continue
            
        code = item["code"]
        name = item.get("name", code)
        buy_p = float(item["buy_price"])
        shares = int(item.get("shares", 1000))
        trade_type = item.get("trade_type", "現股")
        strategy = item.get("strategy", "")
        
        try:
            df, info = fetch_stock_kline(code, period="6mo")
            if df is None or len(df) < 5:
                continue
                
            pts, lns, hp, lt = calculate_turning_points(df, ma_period=5, filter_mode="standard")
            trend_info = analyze_trend(df, pts)
            sig_dict, _ = detect_signals(df, trend_info)
            
            curr_p = float(info.get("close", df.iloc[-1]["Close"]))
            curr_chg = float(info.get("change_pct", 0.0))
            sma5 = float(df.iloc[-1].get("SMA_5", curr_p))
            sma20 = float(df.iloc[-1].get("SMA_20", curr_p))
            sma60 = float(df['Close'].rolling(60).mean().iloc[-1]) if len(df) >= 60 else round(sma20 * 1.10, 2)
            high_p = float(df.iloc[-1]["High"])
            
            lowest_20 = round(float(df['Low'].tail(20).min()), 2)
            highest_20 = round(float(df['High'].tail(20).max()), 2)
            
            pnl_pct = round(((curr_p - buy_p) / buy_p) * 100, 2)
            pnl_amt = round((curr_p - buy_p) * shares, 0)
            breakeven_diff_pct = round(((buy_p - curr_p) / curr_p) * 100, 2) if curr_p > 0 and curr_p < buy_p else 0.0
            
            # --- 計算三大關鍵解套作戰點位 ---
            # 1. 🛑 底線保命價 (Stop Floor)
            if lowest_20 < curr_p:
                floor_stop = lowest_20
            else:
                floor_stop = round(curr_p * 0.95, 2)
            if trade_type == "融資":
                floor_stop = max(floor_stop, lowest_20)
                
            # 2. 🎯 下一波第一反彈賣點 (Target Rebound 1)
            if curr_p < sma20:
                target_rebound_1 = round(sma20, 2)
            else:
                target_rebound_1 = round(min(highest_20, curr_p * 1.08), 2)
            # 若距離成本 < 8%，第一賣點直接鎖定買進成本 (求保本出清)
            if curr_p < buy_p and abs(curr_p - buy_p) / buy_p < 0.08:
                target_rebound_1 = buy_p
                
            # 3. 🏁 極限解套高點 (Target Rebound Extreme)
            target_rebound_extreme = round(min(highest_20, max(sma60, sma20 * 1.05)), 2)
            if target_rebound_extreme < target_rebound_1:
                target_rebound_extreme = round(target_rebound_1 * 1.05, 2)
            if buy_p > target_rebound_1 and buy_p < target_rebound_extreme:
                target_rebound_extreme = buy_p

            # 融資維持率估算
            margin_ratio = None
            if trade_type == "融資":
                margin_ratio = round((curr_p / buy_p) * 166.7, 1)

            # 常規自訂停損停利 (相容模式)
            custom_stop = float(item.get("stop_loss", 0.0))
            custom_target = float(item.get("target_price", 0.0))
            if custom_stop <= 0:
                custom_stop = floor_stop
            if custom_target <= 0:
                custom_target = target_rebound_1

            # --- 智能狀態裁決 ---
            is_trapped = (curr_p < buy_p)
            
            if is_trapped:
                # 【套牢持股救援與高點賣點雷達】
                if trade_type == "融資" and (curr_p <= floor_stop or (margin_ratio and margin_ratio < 135.0)):
                    status_type = "MARGIN_ALERT"
                    status_badge = "⚠️ 融資破底·嚴防斷頭！"
                    status_color = "#FF4D4F"
                    status_desc = f"⚠️ <b>融資緊急離場警報</b>：當前股價 ({curr_p}元) 已摜破波段保命前底 ({floor_stop}元)，估算融資維持率約 <b>{margin_ratio}%</b> (逼近 130% 斷頭追繳線)！融資具利息負擔與強制平倉風險，請立即執行平倉停損，嚴防損失無限擴大！"
                elif curr_p <= floor_stop:
                    status_type = "STOP_LOSS_FLOOR"
                    status_badge = "🔴 破保命底線！逃命離場"
                    status_color = "#FF4D4F"
                    status_desc = f"🚨 <b>底線失守警報</b>：當前股價 ({curr_p}元) 已摜破近期波段前底防守價 ({floor_stop}元)！空方慣性延續，若今日尾盤無法收腳站回，請嚴格執行停損逃命，切勿抱著僥倖心態一路凹單！"
                elif curr_p >= target_rebound_1 * 0.985:
                    if curr_p >= buy_p * 0.99:
                        status_type = "BREAKEVEN_EXIT"
                        status_badge = "🎉 逼近成本！保本出清"
                        status_color = "#FAAD14"
                        status_desc = f"🎯 <b>解套賣點浮現</b>：當前股價 ({curr_p}元) 已來到買進成本 ({buy_p}元) 附近，虧損幾乎完全彌平！依朱家泓心法『解套先求保本』，建議今日於尾盤逢高掛單分批或全部賣出出清，收回全額本金！"
                    else:
                        status_type = "REBOUND_EXIT"
                        status_badge = "🟡 逼近反彈高點！建議分批掛賣"
                        status_color = "#FAAD14"
                        status_desc = f"🎯 <b>反彈波高點警報</b>：當前股價 ({curr_p}元) 已逼近下一波反彈重壓區 ({target_rebound_1}元，月線/前高阻力)！反彈逢重壓極易拉回，建議今日尾盤開始掛單分批賣出 (減碼 1/2 或全部)，大幅少賠收回現金！"
                elif curr_p >= sma5:
                    status_type = "REBOUND_RISING"
                    status_badge = "🟢 反彈推升中·守5MA等賣點"
                    status_color = "#52C41A"
                    status_desc = f"📈 <b>反彈推升中</b>：當前股價 ({curr_p}元) 守穩於 5MA ({sma5:.2f}元) 之上，短線反彈動能推升中！暫時不急著在低檔亂殺低，以 5MA 為移動防守線續抱，耐心等待股價推升至第一反彈賣點 ({target_rebound_1}元) 再逢高掛賣！"
                else:
                    status_type = "BREAK_MA5_WEAK"
                    status_badge = "🟠 跌破 5MA·反彈受阻留意"
                    status_color = "#FA8C16"
                    status_desc = f"⚠️ <b>短線轉弱注意</b>：今日股價跌破 5MA ({sma5:.2f}元)，反彈推升動能受阻。下方絕對保命底線在 <b>{floor_stop}元</b> (若再跌破必須砍單逃命)。若今日尾盤無法站回 5MA，建議可先減碼部分部位防守，避免反彈行情夭折。"
            else:
                # 【常態波段獲利守護模式】
                if high_p >= custom_target or curr_p >= custom_target:
                    status_type = "TARGET_HIT"
                    status_badge = "🏁 達標停利！"
                    status_color = "#FA8C16"
                    status_desc = f"🎉 <b>恭喜達標</b>：股價已達前波壓力目標價 ({custom_target}元)！建議先獲利了結 1/2 入袋為安，剩餘張數守 5MA 讓獲利奔馳！"
                elif curr_p < custom_stop:
                    status_type = "STOP_LOSS"
                    status_badge = "🚨 跌破停損點！"
                    status_color = "#FF4D4F"
                    status_desc = f"⚠️ <b>緊急警報</b>：當前股價 ({curr_p}元) 已摜破設定之防守價 ({custom_stop}元)！請於今日尾盤 13:00~13:30 嚴格執行紀律停損，杜絕損失擴大！"
                elif curr_p < sma5 and not sig_dict.get('pullback_buy', False):
                    status_type = "BREAK_MA5"
                    status_badge = "🛑 跌破 5MA 操盤線！"
                    status_color = "#FAAD14"
                    status_desc = f"⚠️ <b>轉弱注意</b>：收盤價跌破 5MA ({sma5:.2f}元)，短線波段慣性改變，若今日尾盤無法站回，建議先獲利了結或減碼防守！"
                elif sig_dict.get('pullback_buy', False):
                    status_type = "ADD_POSITION"
                    status_badge = "➕ 回測有守·加碼點！"
                    status_color = "#1890FF"
                    status_desc = f"🔥 <b>戰術加碼</b>：持股拉回測線有守，今日再度浮現【回後準進場】轉折紅K，符合朱老師『買兩張長短配』加碼訊號，尾盤可加碼第 2 張！"
                else:
                    status_type = "HOLD"
                    status_badge = "🛡️ 安心續抱"
                    status_color = "#52C41A"
                    status_desc = f"股價 ({curr_p}元) 穩穩守在 5MA ({sma5:.2f}元) 之上，多頭走勢健康，無轉弱跡象，抱緊波段！"
                
            results.append({
                "id": item["id"],
                "code": code,
                "name": name,
                "trade_type": trade_type,
                "buy_date": item.get("buy_date", ""),
                "buy_price": buy_p,
                "stop_loss": custom_stop,
                "target_price": custom_target,
                "floor_stop": floor_stop,
                "target_rebound_1": target_rebound_1,
                "target_rebound_extreme": target_rebound_extreme,
                "is_trapped": is_trapped,
                "breakeven_diff_pct": breakeven_diff_pct,
                "margin_ratio": margin_ratio,
                "shares": shares,
                "curr_price": curr_p,
                "curr_change_pct": curr_chg,
                "pnl_pct": pnl_pct,
                "pnl_amt": pnl_amt,
                "sma5": sma5,
                "sma20": sma20,
                "sma60": sma60,
                "status_type": status_type,
                "status_badge": status_badge,
                "status_color": status_color,
                "status_desc": status_desc,
                "buy_reason": item.get("buy_reason", ""),
                "days_held": (datetime.datetime.now().date() - datetime.datetime.strptime(item.get("buy_date", datetime.datetime.now().strftime("%Y-%m-%d")), "%Y-%m-%d").date()).days
            })
        except Exception as e:
            print(f"Error inspecting {code}: {e}")
            continue
            
    return results

