"""
最高指揮官專屬 · 雲端定時全自動 LINE 盯盤監控腳本
用途：
1. 本地定時排程執行 (Windows Task Scheduler / cron)
2. GitHub Actions 雲端工作流自動排程執行 (週一至週五 12:40, 13:15)
3. 讀取最新實戰持股行情，偵測賣點與停損，自動推播至最高指揮官手機 LINE！
"""

import sys
import os
import argparse
import datetime

# 加入根目錄至 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.copilot import load_portfolio, inspect_portfolio, get_copilot_recommendation
from core.notifier import (
    get_line_config, send_line_push_message,
    format_portfolio_alert, format_tail_recommendation
)
from core.tracker import record_copilot_recommendations, update_all_tracking_performance

def run_monitor(mode: str = "auto"):
    print(f"[{datetime.datetime.now()}] 啟動最高指揮官 LINE 智慧盯盤任務 (模式: {mode})...")
    
    cfg = get_line_config()
    if not cfg.get("enabled", False):
        print("提示：LINE 推播功能目前未啟用 (enabled=False)，任務結束。")
        return
    if not cfg.get("is_configured", False):
        print("警告：尚未設定 LINE Token 或 User ID，無法發送。")
        return
        
    portfolio = load_portfolio(user_id="master")
    active_holdings = [h for h in portfolio if h.get("status") == "HOLDING"]
    
    # 1. 診斷在庫持股
    if active_holdings:
        print(f"正在即時診斷 {len(active_holdings)} 檔在庫持股行情...")
        inspected = inspect_portfolio(active_holdings)
        
        alert_only = (mode == "alert_only") or cfg.get("alert_on_sell_only", False)
        msg_holdings = format_portfolio_alert(inspected, alert_only=alert_only)
        
        if msg_holdings:
            print("正在發送持股通報至手機 LINE...")
            ok, res_msg = send_line_push_message(msg_holdings)
            print(f"持股通報發送結果: {ok} ({res_msg})")
        else:
            print("目前所有持股走勢健康 (無破線/停損警戒)，略過發送。")
    else:
        print("目前無在庫持股。")
        
    # 2. 若為尾盤模式 (tail_briefing)，同時發送今日 12:40 Top 5 推薦名冊
    if mode in ("tail", "full"):
        print("正在計算今日 12:40 尾盤 Top 5 精選推薦...")
        try:
            rec_data = get_copilot_recommendation(enable_realtime=True)
            msg_rec = format_tail_recommendation(rec_data)
            print("正在發送尾盤推薦至手機 LINE...")
            ok_rec, res_rec = send_line_push_message(msg_rec)
            # 自動將今日尾盤 Top 5 登錄至推薦追蹤日誌並更新歷史每日績效
            try:
                rec_cnt = record_copilot_recommendations(rec_data)
                update_all_tracking_performance(force_refresh=False)
                print(f"已自動登錄 {rec_cnt} 檔今日尾盤推薦至追蹤日誌，並完成每日發酵天數更新。")
            except Exception as trk_err:
                print(f"自動更新推薦日誌失敗: {trk_err}")
        except Exception as e:
            print(f"計算尾盤推薦失敗: {e}")
            
    print(f"[{datetime.datetime.now()}] LINE 智慧盯盤任務執行完畢！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LINE 持股盯盤排程監控腳本")
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "alert_only", "tail", "full"],
                        help="執行模式: auto(自動判斷), alert_only(僅有警報才發), tail(尾盤持股+推薦), full(全量推播)")
    args = parser.parse_args()
    run_monitor(mode=args.mode)
