"""
最高指揮官專屬 · LINE Messaging API 智慧盯盤與警報推播引擎
功能：
1. 封裝 LINE Official Account (Messaging API) Push Message API
2. 自動格式化實戰在庫持股診斷訊息（包含紅綠燈、買進價、現價、5MA、停損保命位、融資維持率）
3. 自動格式化每日 12:40 尾盤 Top 5 精選推薦清單
4. 安全保存與讀取指揮官個人專屬金鑰 (嚴格隔離，其他用戶完全無權限)
"""

import os
import json
import datetime
import urllib.request
import urllib.error

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
ADMIN_CONFIG_FILE = os.path.join(DATA_DIR, "admin_config.json")
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"

def get_line_config() -> dict:
    """讀取最高指揮官 LINE 推播設定"""
    cfg = {
        "channel_access_token": "",
        "user_id": "",
        "enabled": False,
        "alert_on_sell_only": False,
        "updated_at": ""
    }
    
    # 支援環境變數優先
    env_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
    env_uid = os.getenv("LINE_USER_ID")
    if env_token:
        cfg["channel_access_token"] = env_token.strip()
    if env_uid:
        cfg["user_id"] = env_uid.strip()
        
    if os.path.exists(ADMIN_CONFIG_FILE):
        try:
            with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if not cfg["channel_access_token"] and saved.get("line_channel_access_token"):
                    cfg["channel_access_token"] = saved.get("line_channel_access_token", "").strip()
                if not cfg["user_id"] and saved.get("line_user_id"):
                    cfg["user_id"] = saved.get("line_user_id", "").strip()
                cfg["enabled"] = bool(saved.get("line_enabled", False))
                cfg["alert_on_sell_only"] = bool(saved.get("line_alert_on_sell_only", False))
                cfg["updated_at"] = saved.get("line_updated_at", "")
        except Exception as e:
            print(f"Error reading LINE config: {e}")
            
    if cfg["channel_access_token"] and cfg["user_id"]:
        cfg["is_configured"] = True
    else:
        cfg["is_configured"] = False
        
    return cfg

def save_line_config(channel_access_token: str, user_id: str, enabled: bool = True, alert_on_sell_only: bool = False) -> tuple[bool, str]:
    """保存最高指揮官 LINE 推播設定至 admin_config.json"""
    token_clean = str(channel_access_token).strip()
    uid_clean = str(user_id).strip()
    
    if not token_clean:
        return False, "Channel Access Token 不得為空！"
    if not uid_clean:
        return False, "LINE User ID 不得為空！"
        
    try:
        cfg = {}
        if os.path.exists(ADMIN_CONFIG_FILE):
            try:
                with open(ADMIN_CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
            except Exception:
                cfg = {}
                
        cfg["line_channel_access_token"] = token_clean
        cfg["line_user_id"] = uid_clean
        cfg["line_enabled"] = bool(enabled)
        cfg["line_alert_on_sell_only"] = bool(alert_on_sell_only)
        cfg["line_updated_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        os.makedirs(os.path.dirname(ADMIN_CONFIG_FILE), exist_ok=True)
        with open(ADMIN_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
            
        return True, "最高指揮官專屬 LINE 推播金鑰已安全保存成功！"
    except Exception as e:
        return False, f"儲存失敗：{e}"

def send_line_push_message(message_text: str, token: str = None, user_id: str = None) -> tuple[bool, str]:
    """
    透過 LINE Messaging API 發送 Push Message 至指揮官個人 LINE
    """
    cfg = get_line_config()
    final_token = token.strip() if token and str(token).strip() else cfg.get("channel_access_token", "")
    final_uid = user_id.strip() if user_id and str(user_id).strip() else cfg.get("user_id", "")
    
    if not final_token or not final_uid:
        return False, "未設定有效的 Channel Access Token 或 User ID，請先至指揮官後台設定！"
        
    payload = {
        "to": final_uid,
        "messages": [
            {
                "type": "text",
                "text": message_text
            }
        ]
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {final_token}"
    }
    
    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(LINE_PUSH_URL, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status in (200, 201):
                return True, "LINE 訊息推播成功！"
            else:
                return False, f"LINE 伺服器回應狀態碼：{response.status}"
    except urllib.error.HTTPError as he:
        err_body = he.read().decode("utf-8", errors="ignore")
        return False, f"HTTP {he.code} 推播失敗：{err_body}"
    except Exception as e:
        return False, f"連線失敗：{e}"

def format_portfolio_alert(inspected_list: list, alert_only: bool = False) -> str:
    """
    將持股診斷列表格式化為清爽專業的 LINE 訊息格式
    alert_only: 若為 True，只推播出現出場/警戒訊號的標的
    """
    if not inspected_list:
        return "🛡️【持股守護神】目前庫存清單暫無股票。"
        
    now_str = datetime.datetime.now().strftime("%Y/%m/%d %H:%M")
    
    # 統計警報與持股狀態
    critical_items = []
    caution_items = []
    healthy_items = []
    
    for item in inspected_list:
        st_type = item.get("status_type", "")
        if any(k in st_type for k in ["STOP", "MARGIN", "BREAK_MA5_WEAK"]):
            critical_items.append(item)
        elif any(k in st_type for k in ["TARGET", "REBOUND_EXIT", "BREAKEVEN"]):
            caution_items.append(item)
        else:
            healthy_items.append(item)
            
    if alert_only and not critical_items and not caution_items:
        return "" # 無需發送
        
    lines = []
    lines.append(f"🤖【AI持股守護神 · 實戰盤中通報】")
    lines.append(f"⏰ 通報時間：{now_str}")
    lines.append("────────────────")
    
    # 1. 重點緊急警報（若有）
    if critical_items:
        lines.append("🚨【特別警戒 · 出場/防守指示】")
        for it in critical_items:
            t_type = f"({it.get('trade_type', '現股')})" if it.get('trade_type') != "現股" else ""
            pnl_sign = "+" if it.get('pnl_pct', 0) >= 0 else ""
            margin_str = f" | 維持率 {it.get('margin_ratio')}%" if it.get('margin_ratio') else ""
            lines.append(f"🔴 {it['name']} ({it['code']}){t_type} 現價 {it['curr_price']}元 ({pnl_sign}{it['pnl_pct']}%)")
            lines.append(f"   ▶ 操盤狀態：{it.get('status_badge')}{margin_str}")
            lines.append(f"   ▶ 5MA：{it.get('sma5'):.2f}元 ｜ 保命底線：{it.get('floor_stop'):.2f}元")
            lines.append(f"   💡 操作指引：{_clean_html(it.get('status_desc'))[:100]}...")
            lines.append("")
            
    # 2. 達標/反彈賣點（若有）
    if caution_items:
        lines.append("🎯【解套/獲利 · 建議分批賣出】")
        for it in caution_items:
            t_type = f"({it.get('trade_type', '現股')})" if it.get('trade_type') != "現股" else ""
            pnl_sign = "+" if it.get('pnl_pct', 0) >= 0 else ""
            lines.append(f"🟡 {it['name']} ({it['code']}){t_type} 現價 {it['curr_price']}元 ({pnl_sign}{it['pnl_pct']}%)")
            lines.append(f"   ▶ 操盤狀態：{it.get('status_badge')}")
            lines.append(f"   ▶ 第一反彈賣點：{it.get('target_rebound_1'):.2f}元 ｜ 目標：{it.get('target_price'):.2f}元")
            lines.append(f"   💡 操作指引：{_clean_html(it.get('status_desc'))[:100]}...")
            lines.append("")
            
    # 3. 正常續抱（非 alert_only 模式才印）
    if not alert_only and healthy_items:
        lines.append("🟢【健康推升 · 守5MA安心續抱】")
        for it in healthy_items:
            t_type = f"({it.get('trade_type', '現股')})" if it.get('trade_type') != "現股" else ""
            pnl_sign = "+" if it.get('pnl_pct', 0) >= 0 else ""
            margin_str = f" (融資維持率 {it.get('margin_ratio')}%)" if it.get('margin_ratio') else ""
            lines.append(f"🟢 {it['name']} ({it['code']}){t_type}：{it['curr_price']}元 ({pnl_sign}{it['pnl_pct']}%)")
            lines.append(f"   ▶ 5MA操盤線：{it.get('sma5'):.2f}元{margin_str}")
        lines.append("")
        
    lines.append("────────────────")
    return "\n".join(lines)

def format_tail_recommendation(rec_data: dict) -> str:
    """
    將每日 12:40 尾盤 Top 5 推薦格式化為 LINE 訊息
    """
    picks = rec_data.get("picks", [])
    now_str = datetime.datetime.now().strftime("%Y/%m/%d")
    
    lines = []
    lines.append(f"🎯【AI操盤副駕駛 · 12:40 尾盤作戰指示】")
    lines.append(f"📅 日期：{now_str} 尾盤精選 Top 5")
    lines.append("────────────────")
    
    if not picks:
        lines.append("⚠️ 今日全市場濾網未達標，建議空手觀望，保留現金！")
        return "\n".join(lines)
        
    for p in picks:
        rank = p.get("rank", 1)
        name = p.get("name", "")
        code = p.get("code", "")
        close_p = p.get("close", 0)
        chg = p.get("change_pct", 0)
        chg_sign = "+" if chg >= 0 else ""
        ma5 = p.get("ma5", close_p)
        stop_p = p.get("stop_loss", 0)
        target_p = p.get("target_price", 0)
        rr = p.get("rr_ratio", 1.0)
        badge = p.get("cost_badge", "")
        
        lines.append(f"🏆 No.{rank} 【{name} ({code})】")
        lines.append(f"   現價：{close_p} 元 ({chg_sign}{chg}%) ｜ 5MA：{ma5:.2f} 元")
        lines.append(f"   🛑 嚴守停損：{stop_p:.2f} 元 ｜ 🏁 波段目標：{target_p:.2f} 元")
        lines.append(f"   ⚖️ 風報比 1 : {rr} ｜ {badge}")
        lines.append("")
        
    lines.append("────────────────")
    lines.append("⏰ 操作指引：若 12:40~13:30 股價穩踩 5MA 之上，可於尾盤限價佈局；嚴守停損紀律！")
    return "\n".join(lines)

def _clean_html(raw_html: str) -> str:
    """移除 HTML 標籤保留純文字"""
    if not raw_html:
        return ""
    import re
    clean = re.sub(r"<.*?>", "", str(raw_html))
    clean = clean.replace("&nbsp;", " ").replace("&gt;", ">").replace("&lt;", "<")
    return clean.strip()
