# -*- coding: utf-8 -*-
"""
core/ambush_detector.py
【守株待兔 · 主力深蹲潛伏雷達】
專門在「全市場尚未爆發、主力暗中吃貨」的極致壓縮期，提前發掘潛在飆股！

核心量化依據（朱家泓老師技術分析全攻略）：
1. CH03 均線扣抵即將由高轉低（均線被動翻揚助攻時間之窗）
2. CH04 窒息量與凹洞量（賣壓徹底枯竭）
3. CH05 守株待兔一字底與獵兔計劃（箱型振幅 <= 10%~12%）
4. CH06 6-15 均線極致糾結戰法（4線收斂帶寬 Bandwidth <= 3.5%）
"""

import os
import json
import time
import pickle
import numpy as np
import pandas as pd
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CACHE_DIR = os.path.join(DATA_DIR, "cache")
AMBUSH_WATCHLIST_FILE = os.path.join(DATA_DIR, "ambush_watchlist.json")

def analyze_stock_ambush_potential(df: pd.DataFrame, code: str, name: str = "", chips_data: dict = None) -> dict:
    """
    深度診斷個股是否處於「主力暗中吃貨 · 均線極致壓縮」的潛伏蓄勢期。
    """
    if df is None or len(df) < 65:
        return None

    # 確保指標計算完整 (5MA, 10MA, 20MA, 60MA, 成交量均線)
    df = df.copy()
    if 'SMA5' not in df.columns or df['SMA5'].isna().all():
        df['SMA5'] = df['Close'].rolling(5).mean()
    if 'SMA10' not in df.columns or df['SMA10'].isna().all():
        df['SMA10'] = df['Close'].rolling(10).mean()
    if 'SMA20' not in df.columns or df['SMA20'].isna().all():
        df['SMA20'] = df['Close'].rolling(20).mean()
    if 'SMA60' not in df.columns or df['SMA60'].isna().all():
        df['SMA60'] = df['Close'].rolling(60).mean()
    if 'VOL_MA5' not in df.columns:
        df['VOL_MA5'] = df['Volume'].rolling(5).mean()
    if 'VOL_MA20' not in df.columns:
        df['VOL_MA20'] = df['Volume'].rolling(20).mean()

    cur = df.iloc[-1]
    c_cur = float(cur['Close'])
    o_cur = float(cur['Open'])
    h_cur = float(cur['High'])
    l_cur = float(cur['Low'])
    v_cur = float(cur['Volume'])

    ma5 = float(cur['SMA5']) if pd.notna(cur['SMA5']) else c_cur
    ma10 = float(cur['SMA10']) if pd.notna(cur['SMA10']) else c_cur
    ma20 = float(cur['SMA20']) if pd.notna(cur['SMA20']) else c_cur
    ma60 = float(cur['SMA60']) if pd.notna(cur['SMA60']) else c_cur

    mas = [ma5, ma10, ma20, ma60]
    min_ma = min(mas)
    max_ma = max(mas)
    if min_ma <= 0:
        return None

    # 1. 均線極致收斂度 (Bandwidth %)
    bandwidth = round(((max_ma - min_ma) / min_ma) * 100, 2)
    # 三線收斂度 (5/10/20MA)
    mas_3 = [ma5, ma10, ma20]
    bw_3 = round(((max(mas_3) - min(mas_3)) / min(mas_3)) * 100, 2)

    # 2. 過去 40 根 K 棒之箱型整理振幅 (Box Amplitude)
    box_slice = df.iloc[-40:]
    box_high = round(float(box_slice['High'].max()), 2)
    box_low = round(float(box_slice['Low'].min()), 2)
    if box_low <= 0:
        return None
    amplitude = round(((box_high - box_low) / box_low) * 100, 2)
    dist_to_box_high = round(((box_high - c_cur) / c_cur) * 100, 2)

    # 3. 糾結維持天數 (Squeeze Days: 連續多少天帶寬 <= 4.5%)
    squeeze_days = 0
    for i in range(len(df) - 1, max(len(df) - 70, 60), -1):
        row_mas = [df['SMA5'].iloc[i], df['SMA10'].iloc[i], df['SMA20'].iloc[i], df['SMA60'].iloc[i]]
        if any(pd.isna(x) or x <= 0 for x in row_mas):
            break
        bw = (max(row_mas) - min(row_mas)) / min(row_mas) * 100
        if bw <= 4.8:
            squeeze_days += 1
        else:
            break

    # 4. 量能特徵 (窒息量/凹洞量 vs 今日放量)
    vol_ma5 = float(cur['VOL_MA5']) if pd.notna(cur['VOL_MA5']) and cur['VOL_MA5'] > 0 else 1.0
    vol_ma20 = float(cur['VOL_MA20']) if pd.notna(cur['VOL_MA20']) and cur['VOL_MA20'] > 0 else 1.0
    vol_ratio_5 = round(v_cur / vol_ma5, 2)
    vol_ratio_20 = round(v_cur / vol_ma20, 2)

    # 5. 均線扣抵預判 (CH03: 今日收盤 > 扣抵價 => 均線上揚)
    deduct_20_cur = float(df['Close'].iloc[-20]) if len(df) >= 20 else c_cur
    deduct_60_cur = float(df['Close'].iloc[-60]) if len(df) >= 60 else c_cur

    is_20ma_rising = c_cur >= deduct_20_cur
    is_60ma_rising = c_cur >= deduct_60_cur

    # 未來 5 天扣抵趨勢預判
    fut_20 = df['Close'].iloc[-19:-14].tolist() if len(df) >= 20 else []
    fut_60 = df['Close'].iloc[-59:-54].tolist() if len(df) >= 60 else []
    
    # 判斷未來 5 天扣抵是否維持低檔有利上揚
    favorable_deduct_count = sum(1 for p in fut_20 if c_cur >= p) + sum(1 for p in fut_60 if c_cur >= p)

    # 6. 狀態判定 (Stage Classification)
    # A. 今日帶量突破 (STAGE_BREAKOUT_TODAY)
    is_today_breakout = (c_cur >= box_high * 0.995) and (c_cur >= o_cur) and (vol_ratio_5 >= 1.3 or v_cur >= 1.5 * vol_ma20) and (c_cur > ma5)
    # B. 蓄勢待發·臨門一腳 (STAGE_READY)
    is_ready_to_launch = (bandwidth <= 3.8 or bw_3 <= 2.2) and (amplitude <= 13.0) and (dist_to_box_high <= 3.0) and is_20ma_rising
    # C. 耐心潛伏·深蹲蓄勢 (STAGE_ACCUMULATING)
    is_accumulating = (bandwidth <= 4.5 or bw_3 <= 3.0) and (amplitude <= 14.0) and (squeeze_days >= 15)

    if not (is_today_breakout or is_ready_to_launch or is_accumulating):
        return None

    # 7. 計算「潛伏蓄勢指數」(Ambush Score 0 ~ 100)
    score = 50.0
    if bandwidth <= 2.5: score += 20.0
    elif bandwidth <= 3.5: score += 15.0
    elif bandwidth <= 4.5: score += 10.0

    if amplitude <= 8.0: score += 15.0
    elif amplitude <= 11.0: score += 10.0

    if squeeze_days >= 40: score += 15.0
    elif squeeze_days >= 25: score += 10.0

    if is_20ma_rising and is_60ma_rising: score += 15.0
    elif is_20ma_rising: score += 10.0

    if favorable_deduct_count >= 6: score += 10.0

    if is_today_breakout:
        stage = "STAGE_BREAKOUT_TODAY"
        stage_text = "🚀 今日放量突破 · 飆股正式起跑"
        stage_color = "#FF4D4F"
        score = max(score, 90.0)
    elif is_ready_to_launch:
        stage = "STAGE_READY"
        stage_text = "⚡ 臨門一腳 · 隨時放量噴出"
        stage_color = "#FAAD14"
        score = max(score, 80.0)
    else:
        stage = "STAGE_ACCUMULATING"
        stage_text = "📦 耐心潛伏 · 主力深蹲吃貨"
        stage_color = "#10B981"

    # 籌碼輔助 (若有)
    mf_val = 0
    if chips_data:
        mf_val = chips_data.get('mf', 0)
        if mf_val > 0:
            score += 5.0

    # 實戰操作指引
    if stage == "STAGE_BREAKOUT_TODAY":
        action_guide = f"今日帶量衝破箱頂 {box_high} 元！屬朱老師 CH06 均線糾結起漲第一根，若開盤未達漲停可順勢進場，已鎖死者切勿追高，等次日回測 5MA。"
    elif stage == "STAGE_READY":
        action_guide = f"四線收斂僅 {bandwidth}%，距箱頂 {box_high} 元僅 {dist_to_box_high}%！扣抵條件極佳，建議於現價 {c_cur} 附近輕倉 20%~30% 提前伏擊，帶量衝過 {box_high} 元立即加碼！"
    else:
        action_guide = f"四線平躺糾結已維持 {squeeze_days} 天，40天箱型振幅僅 {amplitude}%，主力洗盤充分。可於箱底 {box_low} ~ 區間中軸建立底倉耐心守株待兔。"

    return {
        "code": code,
        "name": name,
        "close": c_cur,
        "bandwidth": bandwidth,
        "bandwidth_3": bw_3,
        "amplitude": amplitude,
        "squeeze_days": squeeze_days,
        "box_high": box_high,
        "box_low": box_low,
        "dist_to_box_high": dist_to_box_high,
        "vol_ratio_5": vol_ratio_5,
        "vol_ratio_20": vol_ratio_20,
        "is_20ma_rising": is_20ma_rising,
        "is_60ma_rising": is_60ma_rising,
        "stage": stage,
        "stage_text": stage_text,
        "stage_color": stage_color,
        "ambush_score": round(score, 1),
        "action_guide": action_guide,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def scan_ambush_pool(limit: int = 50) -> list:
    """
    掃描全市場快照與快取，挑選符合潛伏蓄勢資格的標的，並依 Ambush Score 排序。
    """
    snapshot_path = os.path.join(DATA_DIR, "screener_snapshot.pkl")
    stocks_to_scan = []

    # 1. 優先從 screener_snapshot 或 cache 載入
    if os.path.exists(snapshot_path):
        try:
            with open(snapshot_path, 'rb') as f:
                snap_list = pickle.load(f)
            for item in snap_list:
                stocks_to_scan.append((item.get('code'), item.get('name')))
        except Exception:
            pass

    # 2. 若有 cache 檔案，一併補齊
    if os.path.exists(CACHE_DIR):
        try:
            for f in os.listdir(CACHE_DIR):
                if f.endswith('_6mo.pkl') or f.endswith('_1y.pkl'):
                    code = f.split('.')[0]
                    if not any(s[0] == code for s in stocks_to_scan):
                        stocks_to_scan.append((code, ""))
        except Exception:
            pass

    results = []
    for code, name in stocks_to_scan:
        # 尋找快取檔
        df = None
        for suffix in ['_6mo.pkl', '_1y.pkl', '_3mo.pkl']:
            for mkt in ['.TW', '.TWO']:
                p = os.path.join(CACHE_DIR, f"{code}{mkt}{suffix}")
                if os.path.exists(p):
                    try:
                        with open(p, 'rb') as fp:
                            raw = pickle.load(fp)
                        if isinstance(raw, pd.DataFrame):
                            df = raw
                            break
                        elif isinstance(raw, dict) and 'data' in raw:
                            df = raw['data']
                            break
                    except Exception:
                        pass
            if df is not None:
                break

        if df is not None:
            res = analyze_stock_ambush_potential(df, code, name)
            if res:
                results.append(res)

    results.sort(key=lambda x: x['ambush_score'], reverse=True)
    results = results[:limit]

    # 保存每日追蹤檔案
    save_ambush_watchlist(results)
    return results

def save_ambush_watchlist(watchlist: list):
    try:
        with open(AMBUSH_WATCHLIST_FILE, 'w', encoding='utf-8') as f:
            json.dump(watchlist, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AMBUSH] Save watchlist error: {e}")

def load_ambush_watchlist() -> list:
    if os.path.exists(AMBUSH_WATCHLIST_FILE):
        try:
            with open(AMBUSH_WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return scan_ambush_pool()

if __name__ == '__main__':
    print("Testing ambush scanner...")
    res = scan_ambush_pool(limit=10)
    print(f"Found {len(res)} ambush candidates:")
    for r in res[:5]:
        print(f"[{r['stage_text']}] {r['code']} {r['name']} | 帶寬: {r['bandwidth']}% | 振幅: {r['amplitude']}% | 評分: {r['ambush_score']}")
