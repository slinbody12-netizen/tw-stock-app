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

import random
import string

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PORTFOLIO_DIR = os.path.join(DATA_DIR, "portfolios")
DEFAULT_PORTFOLIO_FILE = os.path.join(DATA_DIR, "user_portfolio.json")
AUTH_REQUESTS_FILE = os.path.join(DATA_DIR, "copilot_auth_requests.json")
USERS_FILE = os.path.join(DATA_DIR, "copilot_users.json")
ADMIN_CONFIG_FILE = os.path.join(DATA_DIR, "admin_config.json")
DEFAULT_MASTER_PIN = "IvanCmdr#8899"

def get_master_pin() -> str:
    """取得最高指揮官安全金鑰 (支援環境變數、配置檔與預設金鑰)"""
    env_pin = os.getenv("COPILOT_PIN")
    if env_pin and str(env_pin).strip():
        return str(env_pin).strip()
    if os.path.exists(ADMIN_CONFIG_FILE):
        try:
            with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                p = cfg.get("master_pin")
                if p and str(p).strip():
                    return str(p).strip()
        except Exception:
            pass
    return DEFAULT_MASTER_PIN

def set_master_pin(new_pin: str) -> tuple[bool, str]:
    """更新最高指揮官安全金鑰"""
    clean_pin = str(new_pin).strip()
    if len(clean_pin) < 6:
        return False, "密碼長度至少需 6 位！"
    try:
        os.makedirs(os.path.dirname(ADMIN_CONFIG_FILE), exist_ok=True)
        cfg = {}
        if os.path.exists(ADMIN_CONFIG_FILE):
            try:
                with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
        cfg["master_pin"] = clean_pin
        cfg["updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(ADMIN_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return True, f"最高指揮官金鑰已成功更新為：`{clean_pin}`！請妥善保存！"
    except Exception as e:
        return False, f"儲存失敗：{e}"

COPILOT_MASTER_PIN = get_master_pin()

def get_portfolio_file(user_id: str = "master") -> str:
    """獲取指定使用者的獨立持股存儲路徑 (一人一保險庫)"""
    if not user_id or user_id == "master":
        return DEFAULT_PORTFOLIO_FILE
    os.makedirs(PORTFOLIO_DIR, exist_ok=True)
    safe_id = "".join(c for c in str(user_id) if c.isalnum() or c in "_-")
    return os.path.join(PORTFOLIO_DIR, f"portfolio_{safe_id}.json")

def load_portfolio(user_id: str = "master") -> list:
    """讀取指定使用者在庫實戰持股名冊"""
    file_path = get_portfolio_file(user_id)
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading portfolio for {user_id}: {e}")
        return []

def save_portfolio(portfolio: list, user_id: str = "master") -> bool:
    """保存指定使用者的持股名冊至磁碟"""
    file_path = get_portfolio_file(user_id)
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(portfolio, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving portfolio for {user_id}: {e}")
        return False

def add_holding(code: str, name: str, buy_price: float, stop_loss: float = None, target_price: float = None, 
                strategy: str = "回後準進場", buy_reason: str = "", shares: int = 1000, trade_type: str = "現股",
                buy_date: str = None, user_id: str = "master") -> dict:
    """使用者點擊【我買了】或手動新增時，新增持股追蹤至專屬庫存"""
    portfolio = load_portfolio(user_id=user_id)
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
    save_portfolio(portfolio, user_id=user_id)
    return new_item

def load_preset_user_holdings(user_id: str = "master") -> tuple[int, list]:
    """
    一鍵載入使用者專屬 4 檔持股 (美時 0.5張, 麗正 1張, 晟銘電現股 10張, 晟銘電融資 1張, 勤誠 100股)
    """
    presets = [
        {"code": "1795", "name": "美時", "buy_price": 268.11, "trade_type": "現股", "shares": 500, "buy_reason": "歷史波段建倉 0.5張 (尋求下一波反彈解套賣點)"},
        {"code": "2838", "name": "聯邦銀", "buy_price": 21.45, "trade_type": "現股", "shares": 1000, "buy_reason": "尾盤精選作戰 1張 (成本 21.45 元，波段續抱守5MA)"},
        {"code": "3013", "name": "晟銘電", "buy_price": 114.84, "trade_type": "現股", "shares": 10000, "buy_reason": "歷史現股建倉 10張 (尋求反彈高點減碼逃命)"},
        {"code": "3013", "name": "晟銘電", "buy_price": 88.34, "trade_type": "融資", "shares": 1000, "buy_reason": "融資持股 1張 (利息與維持率壓力，鎖定88.5元平手解套)"},
        {"code": "8210", "name": "勤誠", "buy_price": 1088.96, "trade_type": "現股", "shares": 100, "buy_reason": "伺服器龍頭建倉 100股 (尋求月線/反彈波賣點)"},
    ]
    portfolio = load_portfolio(user_id=user_id)
    added_count = 0
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    for p in presets:
        existing_item = next((
            h for h in portfolio 
            if h.get("code") == p["code"] and 
            h.get("trade_type", "現股") == p["trade_type"] and 
            abs(float(h.get("buy_price", 0)) - p["buy_price"]) < 0.01 and 
            h.get("status") == "HOLDING"
        ), None)
        if existing_item:
            if existing_item.get("shares") != p["shares"]:
                existing_item["shares"] = p["shares"]
                existing_item["buy_reason"] = p["buy_reason"]
                added_count += 1
        else:
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
                        "note": f"載入庫存：以 {p['buy_price']} 元買進 {p['trade_type']} {p['shares']} 股，啟動套牢解套與高點賣點雷達。"
                    }
                ]
            })
            added_count += 1
    if added_count > 0:
        save_portfolio(portfolio, user_id=user_id)
    return added_count, portfolio

def close_holding(holding_id: str, sell_price: float, sell_reason: str = "手動獲利/停損出場", 
                  sell_shares: int = None, user_id: str = "master") -> tuple[bool, str, dict]:
    """使用者點擊【我賣了】時，結算獲利並歸檔至專屬歷史戰報 (支援全數結算或分批減碼)"""
    portfolio = load_portfolio(user_id=user_id)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    found = False
    closed_res = {}
    msg = ""

    for item in portfolio:
        if item.get("id") == holding_id:
            found = True
            buy_p = float(item["buy_price"])
            total_shares = int(item.get("shares", 1000))
            name = item.get("name", item.get("code", "標的"))
            
            # 判斷是否為分批減碼 (賣出股數小於總股數)
            is_partial = (sell_shares is not None and 0 < int(sell_shares) < total_shares)
            
            if is_partial:
                act_shares = int(sell_shares)
                rem_shares = total_shares - act_shares
                item["shares"] = rem_shares
                pnl_pct = round(((sell_price - buy_p) / buy_p) * 100, 2)
                pnl_amt = round((sell_price - buy_p) * act_shares, 0)
                item.setdefault("history_logs", []).append({
                    "date": today_str,
                    "event": "PARTIAL_SELL",
                    "note": f"分批減碼 {act_shares} 股 (以 {sell_price} 元賣出)，剩餘 {rem_shares} 股繼續守護。"
                })
                # 建立一筆獨立的 CLOSED 戰報紀錄
                closed_res = {
                    "id": f"{item['id']}_closed_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "code": item["code"],
                    "name": name,
                    "buy_date": item.get("buy_date", today_str),
                    "buy_price": buy_p,
                    "stop_loss": item.get("stop_loss", 0.0),
                    "target_price": item.get("target_price", 0.0),
                    "strategy": item.get("strategy", ""),
                    "buy_reason": item.get("buy_reason", ""),
                    "trade_type": item.get("trade_type", "現股"),
                    "shares": act_shares,
                    "status": "CLOSED",
                    "created_at": item.get("created_at", datetime.datetime.now().isoformat()),
                    "sell_date": today_str,
                    "sell_price": float(sell_price),
                    "sell_reason": f"{sell_reason} (分批減碼)",
                    "realized_pnl_pct": pnl_pct,
                    "realized_pnl_amt": pnl_amt,
                    "history_logs": [
                        {
                            "date": today_str,
                            "event": "SELL",
                            "note": f"分批減碼以 {sell_price} 元結算 {act_shares} 股 ({sell_reason})，實現損益: {pnl_pct}% ({pnl_amt:,.0f} 元)"
                        }
                    ]
                }
                portfolio.append(closed_res)
                msg = f"已成功分批減碼賣出【{name}】{act_shares:,} 股！已歸檔至實戰戰報，剩餘 {rem_shares:,} 股繼續在庫守護！"
            else:
                act_shares = total_shares if sell_shares is None else int(sell_shares)
                pnl_pct = round(((sell_price - buy_p) / buy_p) * 100, 2)
                pnl_amt = round((sell_price - buy_p) * act_shares, 0)
                item["status"] = "CLOSED"
                item["sell_date"] = today_str
                item["sell_price"] = float(sell_price)
                item["sell_reason"] = sell_reason
                item["realized_pnl_pct"] = pnl_pct
                item["realized_pnl_amt"] = pnl_amt
                item.setdefault("history_logs", []).append({
                    "date": today_str,
                    "event": "SELL",
                    "note": f"全數以 {sell_price} 元結算出場 ({sell_reason})，實現損益: {pnl_pct}% ({pnl_amt:,.0f} 元)"
                })
                closed_res = item
                msg = f"已全數結算【{name}】({act_shares:,} 股)！已自動移至【📜 實戰戰報紀錄】（持股守護神中已自動移除，無需手動刪除）！"
            break

    if found:
        save_portfolio(portfolio, user_id=user_id)
        return True, msg, closed_res
    return False, "找不到該持股部位", {}

def add_closed_holding(code: str, name: str, buy_price: float, sell_price: float, 
                       shares: int = 1000, trade_type: str = "現股", 
                       buy_date: str = None, sell_date: str = None, 
                       sell_reason: str = "手動結算補登", user_id: str = "master") -> dict:
    """手動補登一筆已完成的歷史實戰交易戰報"""
    portfolio = load_portfolio(user_id=user_id)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    b_date = buy_date if buy_date else today_str
    s_date = sell_date if sell_date else today_str
    
    buy_p = float(buy_price)
    sell_p = float(sell_price)
    shs = int(shares)
    pnl_pct = round(((sell_p - buy_p) / buy_p) * 100, 2)
    pnl_amt = round((sell_p - buy_p) * shs, 0)
    
    h_id = f"port_{code}_{trade_type}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_manual"
    item = {
        "id": h_id,
        "code": code,
        "name": name,
        "buy_date": b_date,
        "buy_price": buy_p,
        "stop_loss": 0.0,
        "target_price": 0.0,
        "strategy": "實戰記錄",
        "buy_reason": "歷史交易補登",
        "trade_type": trade_type,
        "shares": shs,
        "status": "CLOSED",
        "created_at": datetime.datetime.now().isoformat(),
        "sell_date": s_date,
        "sell_price": sell_p,
        "sell_reason": sell_reason,
        "realized_pnl_pct": pnl_pct,
        "realized_pnl_amt": pnl_amt,
        "history_logs": [
            {
                "date": s_date,
                "event": "MANUAL_LOG",
                "note": f"手動補登戰報：以 {buy_p} 買進，{sell_p} 結算 ({sell_reason})，實現損益: {pnl_pct}% ({pnl_amt:,.0f} 元)"
            }
        ]
    }
    portfolio.append(item)
    save_portfolio(portfolio, user_id=user_id)
    return item

def delete_holding(holding_id: str, user_id: str = "master") -> bool:
    """刪除單筆紀錄"""
    portfolio = load_portfolio(user_id=user_id)
    portfolio = [p for p in portfolio if p.get("id") != holding_id]
    return save_portfolio(portfolio, user_id=user_id)

def export_portfolio_json(user_id: str = "master") -> str:
    """匯出當前使用者的完整持股與戰報 JSON 字串"""
    portfolio = load_portfolio(user_id=user_id)
    return json.dumps(portfolio, ensure_ascii=False, indent=2)

def import_portfolio_json(json_str: str, user_id: str = "master", mode: str = "merge") -> tuple[bool, str, int]:
    """
    從 JSON 字串還原持股與戰報 (支援 merge 合併 或 replace 完整覆蓋)
    """
    try:
        data = json.loads(json_str.strip())
        if not isinstance(data, list):
            return False, "JSON 格式錯誤：最外層必須是陣列清單 []", 0
        
        valid_items = []
        for d in data:
            if isinstance(d, dict) and "code" in d and "buy_price" in d:
                valid_items.append(d)
                
        if not valid_items:
            return False, "未解析到任何有效的持股資料", 0
            
        if mode == "replace":
            save_portfolio(valid_items, user_id=user_id)
            return True, f"成功覆蓋還原 {len(valid_items)} 筆持股/戰報！", len(valid_items)
        else:
            # 合併模式：依 id 或 code+buy_date+trade_type 去重
            existing = load_portfolio(user_id=user_id)
            existing_ids = {x.get("id") for x in existing if x.get("id")}
            added = 0
            for item in valid_items:
                i_id = item.get("id")
                if not i_id or i_id not in existing_ids:
                    existing.append(item)
                    if i_id:
                        existing_ids.add(i_id)
                    added += 1
            save_portfolio(existing, user_id=user_id)
            return True, f"成功合併匯入 {added} 筆新紀錄（原有紀錄已完整保留）！", added
    except Exception as e:
        return False, f"匯入失敗：{e}", 0

# ========================================================
# 特務權限申請審批與多用戶管理引擎 (SaaS Access Control)
# ========================================================
def get_auth_requests() -> list:
    """讀取所有特務權限開通申請單"""
    if not os.path.exists(AUTH_REQUESTS_FILE):
        return []
    try:
        with open(AUTH_REQUESTS_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading auth requests: {e}")
        return []

def save_auth_requests(requests: list) -> bool:
    """保存特務權限申請單"""
    try:
        os.makedirs(os.path.dirname(AUTH_REQUESTS_FILE), exist_ok=True)
        with open(AUTH_REQUESTS_FILE, "w", encoding="utf-8") as f:
            json.dump(requests, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving auth requests: {e}")
        return False

def submit_access_request(name: str, email: str, reason: str = "") -> dict:
    """一般用戶送出 VIP 特務開通申請"""
    requests = get_auth_requests()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    req_id = f"req_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}"
    
    clean_email = email.strip().lower()
    clean_name = name.strip()
    
    # 檢查是否已有相同 Email 的 pending 申請
    for r in requests:
        if r.get("email", "").strip().lower() == clean_email and r.get("status") == "PENDING":
            return {"success": False, "msg": "您已有一筆審核中的申請，請靜待指揮官核准！", "request": r}
            
    new_req = {
        "request_id": req_id,
        "name": clean_name,
        "email": clean_email,
        "reason": reason.strip(),
        "request_time": now_str,
        "status": "PENDING",
        "assigned_pin": None
    }
    requests.insert(0, new_req)
    save_auth_requests(requests)
    return {"success": True, "msg": "開通申請已成功送達指揮官！", "request": new_req}

def get_copilot_users() -> list:
    """讀取所有已核准特務成員"""
    if not os.path.exists(USERS_FILE):
        return []
    try:
        with open(USERS_FILE, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading copilot users: {e}")
        return []

def save_copilot_users(users: list) -> bool:
    """保存特務成員清單"""
    try:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving copilot users: {e}")
        return False

def verify_copilot_pin(pin: str) -> dict | None:
    """
    驗證特務金鑰：
    1. 若符合最高指揮官 Master PIN (7777)，回傳 ADMIN
    2. 若符合已核准 VIP 用戶金鑰且狀態為 ACTIVE，回傳 VIP_USER
    3. 否則回傳 None
    """
    pin_str = str(pin).strip()
    if not pin_str:
        return None
        
    if pin_str == get_master_pin():
        return {
            "user_id": "master",
            "name": "最高指揮官 (您)",
            "email": "owner@system.local",
            "role": "ADMIN",
            "status": "ACTIVE"
        }
        
    users = get_copilot_users()
    for u in users:
        if str(u.get("pin", "")).strip() == pin_str and u.get("status") == "ACTIVE":
            return u
            
    return None

def approve_access_request(request_id: str, custom_pin: str = None) -> tuple[bool, str, dict]:
    """
    最高指揮官審批通過：
    1. 產生專屬 6 碼隨機金鑰 (或自訂)
    2. 更新申請單狀態為 APPROVED
    3. 加入 copilot_users.json
    4. 初始化該用戶專屬獨立空白庫存檔
    """
    requests = get_auth_requests()
    target_req = None
    for r in requests:
        if r.get("request_id") == request_id:
            target_req = r
            break
            
    if not target_req:
        return False, "找不到該筆申請單", {}
        
    users = get_copilot_users()
    existing_pins = {str(u.get("pin")) for u in users}
    existing_pins.add(get_master_pin())
    
    if custom_pin and str(custom_pin).strip():
        new_pin = str(custom_pin).strip()
    else:
        while True:
            new_pin = "".join(random.choices(string.digits, k=6))
            if new_pin not in existing_pins:
                break
                
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = f"usr_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}"
    
    new_user = {
        "user_id": user_id,
        "name": target_req.get("name", "VIP學員"),
        "email": target_req.get("email", ""),
        "reason": target_req.get("reason", ""),
        "pin": new_pin,
        "role": "VIP_USER",
        "status": "ACTIVE",
        "approved_at": now_str
    }
    
    users.append(new_user)
    save_copilot_users(users)
    
    target_req["status"] = "APPROVED"
    target_req["assigned_pin"] = new_pin
    target_req["approved_at"] = now_str
    save_auth_requests(requests)
    
    # 建立專屬獨立空白庫存檔
    save_portfolio([], user_id=user_id)
    
    return True, new_pin, new_user

def reject_access_request(request_id: str) -> bool:
    """最高指揮官駁回申請"""
    requests = get_auth_requests()
    for r in requests:
        if r.get("request_id") == request_id:
            r["status"] = "REJECTED"
            r["rejected_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_auth_requests(requests)
            return True
    return False

def revoke_user_access(user_id: str) -> bool:
    """最高指揮官撤銷/凍結某成員權限"""
    users = get_copilot_users()
    for u in users:
        if u.get("user_id") == user_id:
            u["status"] = "SUSPENDED"
            u["suspended_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_copilot_users(users)
            return True
    return False

def reactivate_user_access(user_id: str) -> bool:
    """最高指揮官恢復解凍某成員權限"""
    users = get_copilot_users()
    for u in users:
        if u.get("user_id") == user_id:
            u["status"] = "ACTIVE"
            if "suspended_at" in u:
                del u["suspended_at"]
            save_copilot_users(users)
            return True
    return False

def delete_copilot_user(user_id: str) -> bool:
    """最高指揮官徹底刪除某成員及其個人保險庫檔案"""
    users = get_copilot_users()
    new_users = [u for u in users if u.get("user_id") != user_id]
    if len(new_users) != len(users):
        save_copilot_users(new_users)
        # 刪除其獨立保險庫檔案
        p_file = get_portfolio_file(user_id)
        if os.path.exists(p_file) and user_id != "master":
            try:
                os.remove(p_file)
            except Exception:
                pass
        return True
    return False

def add_direct_vip_user(name: str, email: str, pin: str, reason: str = "指揮官手動建檔") -> tuple[bool, str, dict]:
    """最高指揮官手動直接新增 VIP 成員 (無需申請單)"""
    clean_name = name.strip()
    clean_pin = pin.strip()
    if not clean_name:
        return False, "請輸入成員姓名！", {}
    if not clean_pin:
        return False, "請指定存取金鑰 (PIN)！", {}
        
    users = get_copilot_users()
    existing_pins = {str(u.get("pin")) for u in users}
    existing_pins.add(get_master_pin())
    if clean_pin in existing_pins:
        return False, f"金鑰 `{clean_pin}` 已被其他成員或指揮官佔用，請更換！", {}
        
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = f"usr_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(100, 999)}"
    new_user = {
        "user_id": user_id,
        "name": clean_name,
        "email": email.strip(),
        "reason": reason.strip(),
        "pin": clean_pin,
        "role": "VIP_USER",
        "status": "ACTIVE",
        "approved_at": now_str
    }
    users.append(new_user)
    save_copilot_users(users)
    save_portfolio([], user_id=user_id)
    return True, f"成功手動建立 VIP 成員【{clean_name}】，金鑰為：`{clean_pin}`", new_user



# ========================================================
# 核心大腦 1：今日尾盤 AI 唯一首選推薦 (魔鬼級 5 重濾網)
# ========================================================
def get_copilot_recommendation(force_refresh: bool = False, enable_realtime: bool = True) -> dict:
    """
    全自動運算今日 12:40 - 13:30 尾盤作戰精選 Top 5 作戰名冊
    嚴格遵循實戰技術分析鐵律：
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
            "advice_detail": "經技術分析全攻略引擎 5 重嚴格濾網檢驗，全市場今日無符合「回後測線有守且風報比合格」之安全買點。實戰心法：『看不懂不買、沒條件不買』，寧可錯過也不要貿然追高！"
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
    自動執行專業常態波段診斷 + 套牢解套與高點賣點作戰雷達：
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
                        status_desc = f"🎯 <b>解套賣點浮現</b>：當前股價 ({curr_p}元) 已來到買進成本 ({buy_p}元) 附近，虧損幾乎完全彌平！依操盤心法『解套先求保本』，建議今日於尾盤逢高掛單分批或全部賣出出清，收回全額本金！"
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
                    status_color = "#FAAD14"
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
                    status_desc = f"🔥 <b>戰術加碼</b>：持股拉回測線有守，今日再度浮現【回後準進場】轉折紅K，符合『買兩張長短配』加碼訊號，尾盤可加碼第 2 張！"
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

