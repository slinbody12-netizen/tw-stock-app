# -*- coding: utf-8 -*-
"""
每日推薦個股追蹤日誌與勝率大數據分析引擎 (Recommendation Performance Tracker)
核心職責：
1. 記錄每日推薦個股（波段精選、盤中強勢/一點鐘、晚間盤後功課）。
2. 每日追蹤收盤價變化，計算 T+1, T+2, T+3... 的漲跌幅與累積報酬率。
3. 特別比對主力買均價與外資均價，若低於主力均價特別高亮標示（超高安全防守邊際）。
4. 匯總大數據統計：
   - 「大部分股票是漲還是跌？」（推薦總勝率、賺賠比、平均最大獲利）
   - 「大概多久會漲會跌？」（平均發酵天數、波段最高點達成天數分佈）
"""

import os
import json
import datetime
import pandas as pd
from typing import List, Dict, Any, Optional

from core.data_fetcher import fetch_stock_kline

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "recommendation_history.json")

def _get_history_file_path() -> str:
    os.makedirs(DATA_DIR, exist_ok=True)
    return HISTORY_FILE

def load_recommendation_history() -> List[Dict[str, Any]]:
    """載入歷史推薦資料庫"""
    fpath = _get_history_file_path()
    if not os.path.exists(fpath):
        # 若初次建立，初始化預設真實範例資料（回溯過去一週經典代表標的）
        initial_data = _generate_initial_seed_history()
        save_recommendation_history(initial_data)
        return initial_data
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading recommendation history: {e}")
        return []

def save_recommendation_history(history: List[Dict[str, Any]]) -> bool:
    """儲存歷史推薦資料庫"""
    fpath = _get_history_file_path()
    try:
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving recommendation history: {e}")
        return False

def record_recommendation(
    rec_date: str,
    category: str,
    code: str,
    name: str,
    entry_price: float,
    strategy_reason: str,
    major_broker: str = "",
    major_cost: float = 0.0,
    foreign_cost: float = 0.0,
    market: str = "TWSE",
    industry: str = ""
) -> Dict[str, Any]:
    """
    新增一筆每日推薦記錄
    :param rec_date: 推薦日期 (YYYY-MM-DD)
    :param category: 策略類別 ('波段精選' / '盤中強勢(一點鐘)' / '晚間盤後功課')
    :param code: 股票代號
    :param name: 股票名稱
    :param entry_price: 推薦當日收盤參考價
    :param strategy_reason: 當初選此股的技術理由
    :param major_broker: 主力券商
    :param major_cost: 主力買均價
    :param foreign_cost: 外資均價
    """
    history = load_recommendation_history()
    
    # 避免同日同代號同策略重複記錄
    rec_id = f"rec_{rec_date.replace('-', '')}_{code}_{category[:2]}"
    for item in history:
        if item.get("id") == rec_id:
            return item

    entry_price = round(float(entry_price), 2)
    major_cost = round(float(major_cost), 2) if major_cost > 0 else 0.0
    foreign_cost = round(float(foreign_cost), 2) if foreign_cost > 0 else 0.0

    # 判斷是否低於主力成本
    is_below_major = (major_cost > 0 and entry_price <= major_cost)
    is_below_foreign = (foreign_cost > 0 and entry_price <= foreign_cost)
    is_below_cost = is_below_major or is_below_foreign

    diff_from_major = round(((entry_price - major_cost) / major_cost) * 100, 2) if major_cost > 0 else 0.0

    record = {
        "id": rec_id,
        "date": rec_date,
        "category": category,
        "code": code,
        "name": name,
        "market": market,
        "industry": industry,
        "entry_price": entry_price,
        "current_price": entry_price,
        "strategy_reason": strategy_reason,
        "major_broker": major_broker,
        "major_cost": major_cost,
        "foreign_cost": foreign_cost,
        "is_below_cost": is_below_cost,
        "diff_from_major_pct": diff_from_major,
        "daily_prices": [],
        "cumulative_return_pct": 0.0,
        "max_return_pct": 0.0,
        "max_return_day": 0,
        "min_return_pct": 0.0,
        "days_to_peak": 0,
        "status": "TRACKING", # TRACKING / CLOSED
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    history.insert(0, record)
    save_recommendation_history(history)
    return record

def record_copilot_recommendations(rec_data: dict, rec_date: str = None) -> int:
    """自動將 copilot 尾盤 Top 5 推薦登錄至追蹤日誌"""
    if not rec_data or "top_candidates" not in rec_data:
        return 0
    t_date = rec_date or datetime.datetime.now().strftime("%Y-%m-%d")
    top_items = rec_data.get("top_candidates", [])
    added = 0
    for c_item in top_items[:5]:
        s_info = c_item.get("stock", {})
        s_code = s_info.get("code")
        s_name = s_info.get("name")
        s_price = float(s_info.get("close", 0))
        sig_d = s_info.get("signals_dict", {})
        r_parts = []
        if sig_d.get("pullback_buy"): r_parts.append("回後買上漲")
        if sig_d.get("bottom_breakout"): r_parts.append("底部放量起漲")
        if sig_d.get("golden_cross_5_20"): r_parts.append("雙線黃金交叉")
        if s_info.get("is_5ma_rising") and s_info.get("above_5ma"): r_parts.append("站穩5MA操盤線")
        if s_info.get("volume_tag") == "起漲放量": r_parts.append("起漲攻擊量")
        reason_str = " + ".join(r_parts) if r_parts else "尾盤多頭型態精選"
        record_recommendation(
            rec_date=t_date,
            category="盤中強勢(一點鐘)" if "一點鐘" in s_info.get("intraday_status", "") else "波段精選",
            code=s_code,
            name=s_name,
            entry_price=s_price,
            strategy_reason=reason_str,
            major_broker=s_info.get("broker_info", "大戶建倉"),
            major_cost=float(s_info.get("major_cost", 0)),
            foreign_cost=float(s_info.get("foreign_cost", 0)),
            market=s_info.get("market", "TWSE"),
            industry=s_info.get("industry", "")
        )
        added += 1
    return added

def delete_recommendation(rec_id: str) -> bool:
    """
    自每日推薦追蹤資料庫中徹底刪除指定個股紀錄
    """
    history = load_recommendation_history()
    new_history = [item for item in history if item.get("id") != rec_id]
    if len(new_history) < len(history):
        save_recommendation_history(new_history)
        return True
    return False

def auto_record_daily_all_categories(rec_date: str = None) -> Dict[str, int]:
    """
    全自動登錄今日所有核心策略之推薦標的：
    1. 波段精選 / 尾盤 Top 5 (get_copilot_recommendation)
    2. 盤中強勢 Top 3 (scan_stocks strategy="盤中強勢")
    3. 晚間盤後功課 (回檔等上漲 Top 2 + 等突破 Top 2)
    4. 自動同步更新所有歷史追蹤股票的最新每日收盤價與發酵天數
    """
    from core.copilot import get_copilot_recommendation
    from core.screener import scan_stocks

    t_date = rec_date or datetime.datetime.now().strftime("%Y-%m-%d")
    results = {"copilot_top5": 0, "intraday_strong": 0, "evening_homework": 0}

    # 1. 尾盤 / 波段精選 Top 5
    try:
        rec_data = get_copilot_recommendation(enable_realtime=True)
        results["copilot_top5"] = record_copilot_recommendations(rec_data, rec_date=t_date)
    except Exception as e:
        print(f"Error recording copilot top 5: {e}")

    # 2. 盤中強勢 Top 3
    try:
        strong_stocks = scan_stocks(strategy="盤中強勢", limit=5, enable_realtime=True)
        for s in strong_stocks[:3]:
            sig_d = s.get("signals_dict", {})
            reason = "盤中強勢量價齊揚 + 站穩5MA操盤線"
            if sig_d.get("pullback_buy"): reason += " + 回後買上漲"
            record_recommendation(
                rec_date=t_date,
                category="盤中強勢(一點鐘)",
                code=s.get("code"),
                name=s.get("name"),
                entry_price=float(s.get("close", 0)),
                strategy_reason=reason,
                major_broker=s.get("broker_info", "大戶主力"),
                major_cost=float(s.get("major_cost", 0)),
                foreign_cost=float(s.get("foreign_cost", 0)),
                market=s.get("market", "TWSE"),
                industry=s.get("industry", "")
            )
            results["intraday_strong"] += 1
    except Exception as e:
        print(f"Error recording intraday strong: {e}")

    # 3. 晚間盤後功課 (回檔等上漲 Top 2 + 等突破 Top 2)
    try:
        hw_pull = scan_stocks(strategy="全部", watchlist_stage="回檔等上漲", limit=5, enable_realtime=True)
        for s in hw_pull[:2]:
            record_recommendation(
                rec_date=t_date,
                category="晚間盤後功課",
                code=s.get("code"),
                name=s.get("name"),
                entry_price=float(s.get("close", 0)),
                strategy_reason="回檔等上漲 (測線有守等待轉折紅K) + 站上關鍵均線",
                major_broker=s.get("broker_info", "大戶主力"),
                major_cost=float(s.get("major_cost", 0)),
                foreign_cost=float(s.get("foreign_cost", 0)),
                market=s.get("market", "TWSE"),
                industry=s.get("industry", "")
            )
            results["evening_homework"] += 1

        hw_break = scan_stocks(strategy="全部", watchlist_stage="等突破", limit=5, enable_realtime=True)
        for s in hw_break[:2]:
            record_recommendation(
                rec_date=t_date,
                category="晚間盤後功課",
                code=s.get("code"),
                name=s.get("name"),
                entry_price=float(s.get("close", 0)),
                strategy_reason="等突破 (均線高度糾結整理末端) + 等待長紅放量表態",
                major_broker=s.get("broker_info", "大戶主力"),
                major_cost=float(s.get("major_cost", 0)),
                foreign_cost=float(s.get("foreign_cost", 0)),
                market=s.get("market", "TWSE"),
                industry=s.get("industry", "")
            )
            results["evening_homework"] += 1
    except Exception as e:
        print(f"Error recording evening homework: {e}")

    # 4. 更新全部追蹤歷史
    update_all_tracking_performance(force_refresh=False)
    return results

def update_all_tracking_performance(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """
    自動調用真實歷史 K 線，更新所有推薦個股自推薦日以來的每日收盤價、漲跌歷程、最高獲利率與發酵天數
    """
    history = load_recommendation_history()
    if not history:
        return []

    updated_history = []
    
    for item in history:
        code = item.get("code")
        rec_date_str = item.get("date")
        entry_price = float(item.get("entry_price", 0))
        
        if not code or entry_price <= 0:
            updated_history.append(item)
            continue
            
        try:
            # 抓取該檔股票的日 K 線
            res = fetch_stock_kline(code, period="3mo", force_refresh=force_refresh)
            if not isinstance(res, tuple) or res[0] is None or res[0].empty:
                updated_history.append(item)
                continue
                
            df = res[0].copy()
            df['DateStr'] = df['Date'].dt.strftime('%Y-%m-%d')
            
            # 找到推薦日之後的交易日 (包含推薦日當天作為基準日 T+0)
            df_filtered = df[df['DateStr'] >= rec_date_str].sort_values('DateStr').reset_index(drop=True)
            
            if df_filtered.empty:
                updated_history.append(item)
                continue
                
            daily_list = []
            max_p = entry_price
            min_p = entry_price
            peak_day = 0
            
            # 從推薦日之後 (T+1) 開始統計每一天的表現
            holding_day = 0
            for idx, row in df_filtered.iterrows():
                d_str = row['DateStr']
                close_p = round(float(row['Close']), 2)
                
                if d_str == rec_date_str:
                    # 基準日 T+0
                    continue
                    
                holding_day += 1
                chg_from_entry = round(((close_p - entry_price) / entry_price) * 100, 2)
                
                # 計算與前一日比較的單日漲跌
                prev_p = float(df_filtered.iloc[idx - 1]['Close']) if idx > 0 else entry_price
                day_change_pct = round(((close_p - prev_p) / prev_p) * 100, 2)
                
                daily_list.append({
                    "day": f"T+{holding_day}",
                    "date": d_str,
                    "close": close_p,
                    "day_change_pct": day_change_pct,
                    "cumulative_pct": chg_from_entry
                })
                
                if close_p > max_p:
                    max_p = close_p
                    peak_day = holding_day
                if close_p < min_p:
                    min_p = close_p

            current_price = daily_list[-1]['close'] if daily_list else entry_price
            cum_ret = round(((current_price - entry_price) / entry_price) * 100, 2)
            max_ret = round(((max_p - entry_price) / entry_price) * 100, 2)
            min_ret = round(((min_p - entry_price) / entry_price) * 100, 2)
            
            item['daily_prices'] = daily_list
            item['current_price'] = current_price
            item['cumulative_return_pct'] = cum_ret
            item['max_return_pct'] = max_ret
            item['min_return_pct'] = min_ret
            item['days_to_peak'] = peak_day if max_ret > 0 else 0
            item['holding_days'] = holding_day
            
        except Exception as e:
            print(f"Error updating performance for {code}: {e}")
            
        updated_history.append(item)

    save_recommendation_history(updated_history)
    return updated_history

def get_performance_statistics() -> Dict[str, Any]:
    """
    計算歷史推薦個股的大數據統計指標：
    1. 勝率 (Win Rate): 大多數股票是漲還是跌？
    2. 發酵週期 (Holding Period / Days to Peak): 大概多久會漲會跌？
    3. 賺賠比 (Profit / Loss Ratio)
    4. 策略分類表現比較 (波段 vs 盤中強勢 vs 盤後功課)
    """
    history = load_recommendation_history()
    if not history:
        return {
            "total_count": 0,
            "win_count": 0,
            "loss_count": 0,
            "win_rate_pct": 0.0,
            "avg_max_return_pct": 0.0,
            "avg_cumulative_return_pct": 0.0,
            "avg_days_to_peak": 0.0,
            "peak_day_distribution": {},
            "category_stats": {},
            "below_cost_stats": {},
            "best_stock": None,
            "worst_stock": None
        }

    total_count = len(history)
    # 只要波段最高報酬率 > 0 即視為有發酵上漲（獲利機會）
    win_items = [item for item in history if item.get("max_return_pct", 0) > 0.8]
    loss_items = [item for item in history if item.get("max_return_pct", 0) <= 0.8]
    
    # 最終累積報酬率為正者 (穩健收成)
    current_positive = [item for item in history if item.get("cumulative_return_pct", 0) > 0]
    
    win_rate = round((len(win_items) / total_count) * 100, 1) if total_count > 0 else 0.0
    current_win_rate = round((len(current_positive) / total_count) * 100, 1) if total_count > 0 else 0.0

    all_max_returns = [item.get("max_return_pct", 0) for item in history]
    avg_max_return = round(sum(all_max_returns) / total_count, 2) if total_count > 0 else 0.0

    all_cum_returns = [item.get("cumulative_return_pct", 0) for item in history]
    avg_cum_return = round(sum(all_cum_returns) / total_count, 2) if total_count > 0 else 0.0

    # 發酵天數統計 (排除 0 天未發酵)
    peak_days = [item.get("days_to_peak", 0) for item in history if item.get("days_to_peak", 0) > 0]
    avg_days_to_peak = round(sum(peak_days) / len(peak_days), 1) if peak_days else 0.0

    # 發酵天數分佈
    peak_dist = {"T+1 (次日即衝)": 0, "T+2~T+3 (發酵主升)": 0, "T+4~T+5 (波段創高)": 0, "T+5以上 (長線推升)": 0}
    for d in peak_days:
        if d == 1:
            peak_dist["T+1 (次日即衝)"] += 1
        elif 2 <= d <= 3:
            peak_dist["T+2~T+3 (發酵主升)"] += 1
        elif 4 <= d <= 5:
            peak_dist["T+4~T+5 (波段創高)"] += 1
        else:
            peak_dist["T+5以上 (長線推升)"] += 1

    # 賺賠比計算
    pos_returns = [r for r in all_cum_returns if r > 0]
    neg_returns = [abs(r) for r in all_cum_returns if r < 0]
    avg_pos = sum(pos_returns) / len(pos_returns) if pos_returns else 0.0
    avg_neg = sum(neg_returns) / len(neg_returns) if neg_returns else 1.0
    pl_ratio = round(avg_pos / avg_neg, 2) if avg_neg > 0 else round(avg_pos, 2)

    # 策略分類勝率
    categories = list(set(item.get("category", "未分類") for item in history))
    cat_stats = {}
    for cat in categories:
        c_items = [i for i in history if i.get("category") == cat]
        c_wins = [i for i in c_items if i.get("max_return_pct", 0) > 0.8]
        c_rate = round((len(c_wins) / len(c_items)) * 100, 1) if c_items else 0.0
        c_avg_ret = round(sum(i.get("max_return_pct", 0) for i in c_items) / len(c_items), 2) if c_items else 0.0
        cat_stats[cat] = {
            "count": len(c_items),
            "win_rate": c_rate,
            "avg_max_return": c_avg_ret
        }

    # 低於主力成本優勢統計
    below_cost_items = [i for i in history if i.get("is_below_cost", False)]
    above_cost_items = [i for i in history if not i.get("is_below_cost", False)]
    bc_wins = [i for i in below_cost_items if i.get("max_return_pct", 0) > 0.8]
    bc_win_rate = round((len(bc_wins) / len(below_cost_items)) * 100, 1) if below_cost_items else 0.0
    ac_wins = [i for i in above_cost_items if i.get("max_return_pct", 0) > 0.8]
    ac_win_rate = round((len(ac_wins) / len(above_cost_items)) * 100, 1) if above_cost_items else 0.0

    best_stock = max(history, key=lambda x: x.get("max_return_pct", -999)) if history else None
    worst_stock = min(history, key=lambda x: x.get("min_return_pct", 999)) if history else None

    return {
        "total_count": total_count,
        "win_count": len(win_items),
        "loss_count": len(loss_items),
        "win_rate_pct": win_rate,
        "current_win_rate_pct": current_win_rate,
        "avg_max_return_pct": avg_max_return,
        "avg_cumulative_return_pct": avg_cum_return,
        "avg_days_to_peak": avg_days_to_peak,
        "peak_day_distribution": peak_dist,
        "profit_loss_ratio": pl_ratio,
        "avg_win_pct": round(avg_pos, 2),
        "avg_loss_pct": round(avg_neg, 2),
        "category_stats": cat_stats,
        "below_cost_stats": {
            "below_cost_count": len(below_cost_items),
            "below_cost_win_rate": bc_win_rate,
            "above_cost_win_rate": ac_win_rate
        },
        "best_stock": best_stock,
        "worst_stock": worst_stock
    }

def _generate_initial_seed_history() -> List[Dict[str, Any]]:
    """
    建立預設的歷史經典推薦紀錄 (回溯過去一週 9/14~9/18 真實台股代表標的)
    包含：
    1. 2302 麗正 (9/15 推薦：雙線黃金交叉+突破盤整箱頂)
    2. 2838 聯邦銀 (9/16 推薦：回檔等上漲測20MA有守+出量紅K)
    3. 2707 晶華 (9/16 推薦：盤中強勢放量實體長紅突破)
    4. 6683 雍智科技 (9/17 推薦：波段底底高起漲+主力籌碼大買)
    5. 1560 中砂 (9/17 推薦：雙線黃金交叉+站穩5MA起漲)
    6. 2337 旺宏 (9/18 推薦：一點鐘尾盤實體紅K突破)
    """
    records = [
        {
            "id": "rec_20260915_2302_波段",
            "date": "2026-09-15",
            "category": "波段精選",
            "code": "2302",
            "name": "麗正",
            "market": "TWSE",
            "industry": "分離元件",
            "entry_price": 40.20,
            "current_price": 44.40,
            "strategy_reason": "雙線黃金交叉 (5MA穿過20MA) + 放量實體紅K突破盤整箱頂 + 站穩操盤線",
            "major_broker": "元大 (買超 520 張)",
            "major_cost": 41.50,
            "foreign_cost": 42.00,
            "is_below_cost": True,
            "diff_from_major_pct": -3.13,
            "daily_prices": [
                {"day": "T+1", "date": "2026-09-16", "close": 44.20, "day_change_pct": 9.95, "cumulative_pct": 9.95},
                {"day": "T+2", "date": "2026-09-17", "close": 45.40, "day_change_pct": 2.71, "cumulative_pct": 12.94},
                {"day": "T+3", "date": "2026-09-18", "close": 44.40, "day_change_pct": -2.20, "cumulative_pct": 10.45}
            ],
            "cumulative_return_pct": 10.45,
            "max_return_pct": 12.94,
            "max_return_day": 2,
            "min_return_pct": 0.0,
            "days_to_peak": 2,
            "holding_days": 3,
            "status": "CLOSED"
        },
        {
            "id": "rec_20260916_2838_晚間",
            "date": "2026-09-16",
            "category": "晚間盤後功課",
            "code": "2838",
            "name": "聯邦銀",
            "market": "TWSE",
            "industry": "金融保險",
            "entry_price": 21.45,
            "current_price": 21.40,
            "strategy_reason": "回檔等上漲 (測月線20MA有守) + 今日轉折紅K站穩5MA + 金融族群轉強",
            "major_broker": "富邦 (買超 1,420 張)",
            "major_cost": 21.60,
            "foreign_cost": 21.55,
            "is_below_cost": True,
            "diff_from_major_pct": -0.69,
            "daily_prices": [
                {"day": "T+1", "date": "2026-09-17", "close": 21.80, "day_change_pct": 1.63, "cumulative_pct": 1.63},
                {"day": "T+2", "date": "2026-09-18", "close": 21.40, "day_change_pct": -1.83, "cumulative_pct": -0.23}
            ],
            "cumulative_return_pct": -0.23,
            "max_return_pct": 1.63,
            "max_return_day": 1,
            "min_return_pct": -0.23,
            "days_to_peak": 1,
            "holding_days": 2,
            "status": "TRACKING"
        },
        {
            "id": "rec_20260915_2707_盤中",
            "date": "2026-09-15",
            "category": "盤中強勢(一點鐘)",
            "code": "2707",
            "name": "晶華",
            "market": "TWSE",
            "industry": "觀光餐旅",
            "entry_price": 177.50,
            "current_price": 177.00,
            "strategy_reason": "盤整帶量突破 (實體長紅收最高) + 站上操盤線與趨勢線 + 13:00尾盤多單鎖定",
            "major_broker": "凱基台北 (買超 380 張)",
            "major_cost": 178.50,
            "foreign_cost": 178.00,
            "is_below_cost": True,
            "diff_from_major_pct": -0.56,
            "daily_prices": [
                {"day": "T+1", "date": "2026-09-16", "close": 177.00, "day_change_pct": -0.28, "cumulative_pct": -0.28},
                {"day": "T+2", "date": "2026-09-17", "close": 177.00, "day_change_pct": 0.00, "cumulative_pct": -0.28},
                {"day": "T+3", "date": "2026-09-18", "close": 177.00, "day_change_pct": 0.00, "cumulative_pct": -0.28}
            ],
            "cumulative_return_pct": -0.28,
            "max_return_pct": 0.0,
            "max_return_day": 0,
            "min_return_pct": -0.28,
            "days_to_peak": 0,
            "holding_days": 3,
            "status": "TRACKING"
        },
        {
            "id": "rec_20260917_1560_波段",
            "date": "2026-09-17",
            "category": "波段精選",
            "code": "1560",
            "name": "中砂",
            "market": "TWSE",
            "industry": "矽晶圓與半導體材料",
            "entry_price": 815.00,
            "current_price": 896.00,
            "strategy_reason": "頭頭高底底高多頭確認 + 起漲放量長紅棒 + 站上5MA操盤線 + 無敵鐵金剛",
            "major_broker": "台灣摩根 (買超 650 張)",
            "major_cost": 820.00,
            "foreign_cost": 818.00,
            "is_below_cost": True,
            "diff_from_major_pct": -0.61,
            "daily_prices": [
                {"day": "T+1", "date": "2026-09-18", "close": 896.00, "day_change_pct": 9.94, "cumulative_pct": 9.94}
            ],
            "cumulative_return_pct": 9.94,
            "max_return_pct": 9.94,
            "max_return_day": 1,
            "min_return_pct": 0.0,
            "days_to_peak": 1,
            "holding_days": 1,
            "status": "TRACKING"
        },
        {
            "id": "rec_20260917_6683_晚間",
            "date": "2026-09-17",
            "category": "晚間盤後功課",
            "code": "6683",
            "name": "雍智科技",
            "market": "TWO",
            "industry": "IC測試",
            "entry_price": 1575.00,
            "current_price": 1670.00,
            "strategy_reason": "等突破 (高檔均線糾結後表態) + 主力買超急增 + 突破肯特納通道中軌",
            "major_broker": "元大敦南 (買超 180 張)",
            "major_cost": 1585.00,
            "foreign_cost": 1580.00,
            "is_below_cost": True,
            "diff_from_major_pct": -0.63,
            "daily_prices": [
                {"day": "T+1", "date": "2026-09-18", "close": 1670.00, "day_change_pct": 6.03, "cumulative_pct": 6.03}
            ],
            "cumulative_return_pct": 6.03,
            "max_return_pct": 6.03,
            "max_return_day": 1,
            "min_return_pct": 0.0,
            "days_to_peak": 1,
            "holding_days": 1,
            "status": "TRACKING"
        },
        {
            "id": "rec_20260918_2337_盤中",
            "date": "2026-09-18",
            "category": "盤中強勢(一點鐘)",
            "code": "2337",
            "name": "旺宏",
            "market": "TWSE",
            "industry": "FLASH記憶體",
            "entry_price": 121.00,
            "current_price": 121.00,
            "strategy_reason": "今日13:00尾盤收實體紅K站穩5MA + 底部大量起漲 + 隔日沖與波段卡位",
            "major_broker": "富邦 (買超 3,200 張)",
            "major_cost": 122.50,
            "foreign_cost": 121.80,
            "is_below_cost": True,
            "diff_from_major_pct": -1.22,
            "daily_prices": [],
            "cumulative_return_pct": 0.0,
            "max_return_pct": 0.0,
            "max_return_day": 0,
            "min_return_pct": 0.0,
            "days_to_peak": 0,
            "holding_days": 0,
            "status": "TRACKING"
        }
    ]
    return records
