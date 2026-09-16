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

def add_holding(code: str, name: str, buy_price: float, stop_loss: float, target_price: float, 
                strategy: str = "回後準進場", buy_reason: str = "", shares: int = 1000) -> dict:
    """使用者點擊【我買了】時，新增持股追蹤"""
    portfolio = load_portfolio()
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    holding_id = f"port_{code}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    new_item = {
        "id": holding_id,
        "code": code,
        "name": name,
        "buy_date": today_str,
        "buy_price": float(buy_price),
        "stop_loss": float(stop_loss),
        "target_price": float(target_price),
        "strategy": strategy,
        "buy_reason": buy_reason,
        "shares": int(shares),
        "status": "HOLDING",
        "created_at": datetime.datetime.now().isoformat(),
        "history_logs": [
            {
                "date": today_str,
                "event": "BUY",
                "note": f"以 {buy_price} 元進場買進，初始停損設為 {stop_loss} 元，波段目標價 {target_price} 元。"
            }
        ]
    }
    portfolio.append(new_item)
    save_portfolio(portfolio)
    return new_item

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
    自動執行朱家泓 4 大操盤狀態診斷：
    1. 🚨 破線停損 (跌破買進低點或 5MA，立即出場)
    2. 🏁 達標停利 (觸及波段滿足目標價，分批停利)
    3. ➕ 回測加碼 (拉回測線有守再度翻揚，買兩張長短配加碼)
    4. 🛡️ 安心續抱 (穩健運行於 5MA 之上，無任何敗象)
    """
    results = []
    for item in portfolio:
        if item.get("status") != "HOLDING":
            continue
            
        code = item["code"]
        name = item.get("name", code)
        buy_p = float(item["buy_price"])
        stop_p = float(item.get("stop_loss", buy_p * 0.95))
        target_p = float(item.get("target_price", buy_p * 1.10))
        shares = int(item.get("shares", 1000))
        
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
            high_p = float(df.iloc[-1]["High"])
            
            pnl_pct = round(((curr_p - buy_p) / buy_p) * 100, 2)
            pnl_amt = round((curr_p - buy_p) * shares, 0)
            
            # 狀態裁決
            status_type = "HOLD"
            status_badge = "🛡️ 安心續抱"
            status_color = "#52C41A"
            status_desc = f"股價 ({curr_p}元) 穩穩守在 5MA ({sma5:.2f}元) 之上，多頭走勢健康，無轉弱跡象，抱緊波段！"
            
            # 1. 停損檢驗：收盤跌破停損價 或 跌破 5MA 下彎
            if curr_p < stop_p:
                status_type = "STOP_LOSS"
                status_badge = "🚨 跌破停損點！"
                status_color = "#FF4D4F"
                status_desc = f"⚠️ <b>緊急警報</b>：當前股價 ({curr_p}元) 已摜破設定之防守價 ({stop_p}元)！請於今日尾盤 13:00~13:30 嚴格執行紀律停損，杜絕損失擴大！"
            elif curr_p < sma5 and not sig_dict.get('pullback_buy', False):
                status_type = "BREAK_MA5"
                status_badge = "🛑 跌破 5MA 操盤線！"
                status_color = "#FAAD14"
                status_desc = f"⚠️ <b>轉弱注意</b>：收盤價跌破 5MA ({sma5:.2f}元)，短線波段慣性改變，若今日尾盤無法站回，建議先獲利了結或減碼防守！"
                
            # 2. 停利檢驗：觸及目標價
            elif high_p >= target_p or curr_p >= target_p:
                status_type = "TARGET_HIT"
                status_badge = "🏁 達標停利！"
                status_color = "#FA8C16"
                status_desc = f"🎉 <b>恭喜達標</b>：股價已達前波壓力目標價 ({target_p}元)！建議先獲利了結 1/2 入袋為安，剩餘張數守 5MA 讓獲利奔馳！"
                
            # 3. 加碼檢驗：持股中回測 5MA/20MA 守穩又出轉折紅K
            elif sig_dict.get('pullback_buy', False) and curr_p > buy_p:
                status_type = "ADD_POSITION"
                status_badge = "➕ 回測有守·加碼點！"
                status_color = "#1890FF"
                status_desc = f"🔥 <b>戰術加碼</b>：持股拉回測線有守，今日再度浮現【回後準進場】轉折紅K，符合朱老師『買兩張長短配』加碼訊號，尾盤可加碼第 2 張！"
                
            results.append({
                "id": item["id"],
                "code": code,
                "name": name,
                "buy_date": item.get("buy_date", ""),
                "buy_price": buy_p,
                "stop_loss": stop_p,
                "target_price": target_p,
                "shares": shares,
                "curr_price": curr_p,
                "curr_change_pct": curr_chg,
                "pnl_pct": pnl_pct,
                "pnl_amt": pnl_amt,
                "sma5": sma5,
                "sma20": sma20,
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
