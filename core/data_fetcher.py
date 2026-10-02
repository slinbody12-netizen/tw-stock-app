# -*- coding: utf-8 -*-
"""
數據獲取與指標計算模組
支援台股 (TWSE/TPEx) 日線歷史數據抓取、代碼與名稱搜尋、快取與各類常用技術指標計算。
"""

import os
import json
import time
import pickle
import requests
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
import yfinance as yf

def get_tw_now():
    """獲取台灣標準時間 (UTC+8) Timestamp，避免海外伺服器 (AWS / Streamlit Cloud) 時區偏差"""
    try:
        return pd.Timestamp.now(tz='Asia/Taipei').tz_localize(None)
    except Exception:
        return (pd.Timestamp.utcnow() + pd.Timedelta(hours=8)).tz_localize(None)

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
STOCK_LIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'tw_stock_list.json')

def load_stock_list():
    if os.path.exists(STOCK_LIST_PATH):
        with open(STOCK_LIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

_STOCK_LIST = load_stock_list()

# 常見異體字、簡體字、日文新字體與台股習慣用字正規化對照表
CHAR_NORM_MAP = {
    '鐡': '鐵', '臺': '台', '豊': '豐', '恒': '恆', '証': '證',
    '峯': '峰', '羣': '群', '鷄': '雞', '宝': '寶', '国': '國',
    '华': '華', '创': '創', '电': '電', '联': '聯', '阳': '陽',
    '达': '達', '广': '廣', '发': '發', '钛': '鈦', '钰': '鈺',
    '钜': '鉅', '铖': '鋮', '桦': '樺', '强': '強', '温': '溫',
    '黄': '黃', '线': '線', '缆': '纜', '纸': '紙', '纺': '紡',
    '织': '織', '润': '潤', '胜': '勝', '声': '聲', '银': '銀',
    '车': '車', '轮': '輪', '药': '藥', '医': '醫', '运': '運',
    '钢': '鋼', '机': '機', '飞': '飛', '软': '軟', '体': '體',
    '硕': '碩', '伟': '偉', '凯': '凱', '业': '業', '实': '實',
    '际': '際', '优': '優', '讯': '訊', '视': '視', '环': '環',
    '圆': '圓', '龙': '龍', '荣': '榮', '兴': '興', '诚': '誠',
    '铭': '銘', '顺': '順', '硅': '矽', '纬': '緯', '颖': '穎'
}

def normalize_stock_name(text: str) -> str:
    """
    正規化股票名稱與查詢字串：全形轉半形、異體字與俗體字標準化
    """
    if not text:
        return ""
    res = []
    for ch in str(text).strip():
        code = ord(ch)
        if code == 0x3000:
            ch = ' '
        elif 0xFF01 <= code <= 0xFF5E:
            ch = chr(code - 0xFEE0)
        ch = CHAR_NORM_MAP.get(ch, ch)
        res.append(ch)
    return ''.join(res)

# 常見公司簡稱、全名、俗稱別名與代號對照表
STOCK_ALIASES = {
    '東鋼': '2006',
    '東和鋼': '2006',
    '東和鋼鐵': '2006',
    '中鋼': '2002',
    '中國鋼鐵': '2002',
    '台積': '2330',
    '台積電': '2330',
    '台灣積體電路': '2330',
    '台積公司': '2330',
    '聯電': '2303',
    '聯華電子': '2303',
    '聯發': '2454',
    '聯發科': '2454',
    '聯發科技': '2454',
    '鴻海': '2317',
    '鴻海精密': '2317',
    '大立光': '3008',
    '大立光電': '3008',
    '長榮': '2603',
    '長榮海運': '2603',
    '長榮航': '2618',
    '長榮航空': '2618',
    '華航': '2610',
    '中華航空': '2610',
    '陽明': '2609',
    '陽明海運': '2609',
    '萬海': '2615',
    '萬海航運': '2615',
    '富邦金': '2881',
    '富邦金控': '2881',
    '國泰金': '2882',
    '國泰金控': '2882',
    '中信金': '2891',
    '中信金控': '2891',
    '兆豐金': '2886',
    '兆豐金控': '2886',
    '玉山金': '2884',
    '玉山金控': '2884',
    '華南金': '2880',
    '華南金控': '2880',
    '第一金': '2892',
    '第一金控': '2892',
    '元大金': '2885',
    '元大金控': '2885',
    '台新金': '2887',
    '台新金控': '2887',
    '永豐金': '2890',
    '永豐金控': '2890',
    '合庫金': '5880',
    '合庫金控': '5880',
    '開發金': '2883',
    '凱基金': '2883',
    '凱基金控': '2883',
    '台達電': '2308',
    '台達電子': '2308',
    '廣達': '2382',
    '廣達電腦': '2382',
    '華碩': '2357',
    '華碩電腦': '2357',
    '緯創': '3231',
    '緯創資通': '3231',
    '光寶科': '2301',
    '光寶科技': '2301',
    '研華': '2395',
    '研華科技': '2395',
    '技嘉': '2376',
    '技嘉科技': '2376',
    '微星': '2377',
    '微星科技': '2377',
    '仁寶': '2324',
    '仁寶電腦': '2324',
    '英業達': '2356',
    '英業達科技': '2356',
    '和碩': '4938',
    '和碩聯合': '4938',
    '宏碁': '2353',
    '宏碁電腦': '2353',
    '友達': '2409',
    '友達光電': '2409',
    '群創': '3481',
    '群創光電': '3481',
    '高鐵': '2633',
    '台灣高鐵': '2633',
    '統一超': '2912',
    '統一超商': '2912',
    '7-11': '2912',
    '711': '2912',
    '全家': '5903',
    '全家便利': '5903',
    '裕隆': '2201',
    '裕隆汽車': '2201',
    '和泰車': '2207',
    '和泰汽車': '2207',
    '中華電': '2412',
    '中華電信': '2412',
    '台灣大': '3045',
    '台灣大哥大': '3045',
    '遠傳': '4904',
    '遠傳電信': '4904',
    '力積電': '6770',
    '旺宏': '2337',
    '旺宏電子': '2337',
    '南亞科': '2408',
    '南亞科技': '2408',
    '世界': '5347',
    '世界先進': '5347',
    '穩懋': '3105',
    '穩懋半導體': '3105',
    '欣興': '3037',
    '欣興電子': '3037',
    '景碩': '3189',
    '景碩科技': '3189',
    '健鼎': '3044',
    '健鼎科技': '3044',
    '金像電': '2368',
    '金像電子': '2368',
    '台光電': '2383',
    '台光電子': '2383',
    '聯茂': '6213',
    '聯茂電子': '6213',
    '智邦': '2345',
    '智邦科技': '2345',
    '日月光': '3711',
    '日月光投控': '3711',
    '良得': '2462',
    '良得電': '2462',
    '良得電子': '2462',
    '良維': '6290',
    '良維科技': '6290',
    '晟銘電': '3013',
    '晟銘電子': '3013',
    '川湖': '2059',
    '川湖科技': '2059',
    '神達': '3706',
    '神達電腦': '3706',
    '神達投控': '3706'
}

FULL_STOCK_MAP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'tw_full_stock_map.json')
_FULL_STOCK_MAP = None

def load_full_stock_map():
    global _FULL_STOCK_MAP
    if _FULL_STOCK_MAP is not None:
        return _FULL_STOCK_MAP
    if os.path.exists(FULL_STOCK_MAP_PATH):
        try:
            with open(FULL_STOCK_MAP_PATH, 'r', encoding='utf-8') as f:
                _FULL_STOCK_MAP = json.load(f)
                return _FULL_STOCK_MAP
        except Exception:
            pass
    return {}

def search_stocks(query: str):
    """
    依股票代號、中文名稱、別名或產業搜尋股票，支援異體字自動正規化與全市場字典擴展
    """
    if not query:
        return _STOCK_LIST[:20]
    clean_q = query.strip()
    norm_q = normalize_stock_name(clean_q).upper()
    full_map = load_full_stock_map()

    matches = []
    seen = set()

    # 1. 優先檢查別名庫 (如「東鋼」-> 2006、「高鐵」-> 2633)
    alias_code = STOCK_ALIASES.get(normalize_stock_name(clean_q))
    if alias_code:
        for s in _STOCK_LIST:
            if s['code'] == alias_code:
                matches.append(s)
                seen.add(s['code'])
                break
        if alias_code not in seen and alias_code in full_map:
            it = full_map[alias_code]
            matches.append({'code': alias_code, 'name': it.get('name', alias_code), 'market': it.get('market', 'TW'), 'industry': '台股標的'})
            seen.add(alias_code)

    # 2. 精選 186 檔清單檢索 (包含代號、正規化名稱、產業)
    for s in _STOCK_LIST:
        if s['code'] in seen:
            continue
        c = s['code'].upper()
        n = normalize_stock_name(s['name']).upper()
        ind = normalize_stock_name(s.get('industry', '')).upper()
        if norm_q in c or norm_q in n or norm_q in ind:
            matches.append(s)
            seen.add(s['code'])

    # 3. 若精選清單結果較少 (<10)，自動從全市場 2350 檔字典補充
    if len(matches) < 10:
        for code_k, it in full_map.items():
            if code_k in seen:
                continue
            n = normalize_stock_name(it.get('name', '')).upper()
            if norm_q in code_k.upper() or norm_q in n:
                matches.append({'code': code_k, 'name': it.get('name', code_k), 'market': it.get('market', 'TW'), 'industry': '台股標的'})
                seen.add(code_k)
                if len(matches) >= 20:
                    break

    return matches

def resolve_ticker(query: str):
    """
    解析使用者輸入（代碼、中文名稱、俗稱或別名），
    自動容錯正規化 (例如 鐡->鐵、臺->台、東鋼->東和鋼鐵)，
    回傳 (ticker, code, name, market, industry, has_futures, has_cb)
    """
    q = query.strip()
    norm_q = normalize_stock_name(q)

    if norm_q in ["大盤", "加權指數", "^TWII", "加權"]:
        return "^TWII", "^TWII", "加權指數", "INDEX", "大盤指數", True, False

    stock_list = load_stock_list()
    full_map = load_full_stock_map()

    # 0. 檢查別名庫 (精準代碼映射，如 東鋼/東和鋼鐡 -> 2006, 台積 -> 2330)
    if norm_q in STOCK_ALIASES:
        target_c = STOCK_ALIASES[norm_q]
        for s in stock_list:
            if s['code'] == target_c:
                market = s.get('market', 'TW')
                return f"{s['code']}.{market}", s['code'], s['name'], market, s.get('industry', ''), s.get('has_futures', False), s.get('has_cb', False)
        if target_c in full_map:
            item = full_map[target_c]
            mkt = item.get('market', 'TW')
            return f"{target_c}.{mkt}", target_c, item.get('name', target_c), mkt, "台股標的", False, False

    # 1. 在精選 186 檔清單中查找 (支援字元正規化)
    for s in stock_list:
        if norm_q == s['code'] or norm_q == normalize_stock_name(s['name']):
            market = s.get('market', 'TW')
            ticker = f"{s['code']}.{market}"
            return ticker, s['code'], s['name'], market, s.get('industry', ''), s.get('has_futures', False), s.get('has_cb', False)

    # 2. 在全市場 2350 檔完整代碼字典中查找 (代碼完全吻合 或 正規化名稱完全吻合)
    if norm_q in full_map:
        item = full_map[norm_q]
        mkt = item.get('market', 'TW')
        return f"{norm_q}.{mkt}", norm_q, item.get('name', norm_q), mkt, "台股標的", False, False

    for code_k, item in full_map.items():
        if norm_q == normalize_stock_name(item.get('name', '')):
            mkt = item.get('market', 'TW')
            return f"{code_k}.{mkt}", code_k, item.get('name', code_k), mkt, "台股標的", False, False

    # 3. 雙向模糊匹配：針對前綴、簡稱、全稱容錯 (長度 >= 2)
    if len(norm_q) >= 2:
        # 3A. 前向匹配 (query 是名稱的前綴或子字串，如 '台積' -> '台積電')
        candidates_forward = []
        for s in stock_list:
            sn_norm = normalize_stock_name(s['name'])
            if sn_norm.startswith(norm_q):
                candidates_forward.append((1, len(sn_norm), s))
            elif norm_q in sn_norm:
                candidates_forward.append((2, len(sn_norm), s))
        if candidates_forward:
            candidates_forward.sort(key=lambda x: (x[0], x[1]))
            s = candidates_forward[0][2]
            market = s.get('market', 'TW')
            return f"{s['code']}.{market}", s['code'], s['name'], market, s.get('industry', ''), s.get('has_futures', False), s.get('has_cb', False)

        # 3B. 反向匹配 (名稱是 query 的子字串，如 '陽明海運' -> '陽明'，'大立光電' -> '大立光')
        candidates_backward = []
        for s in stock_list:
            sn_norm = normalize_stock_name(s['name'])
            if sn_norm in norm_q:
                candidates_backward.append((-len(sn_norm), s))
        if candidates_backward:
            candidates_backward.sort(key=lambda x: x[0])
            s = candidates_backward[0][1]
            market = s.get('market', 'TW')
            return f"{s['code']}.{market}", s['code'], s['name'], market, s.get('industry', ''), s.get('has_futures', False), s.get('has_cb', False)

        # 3C. 在全市場 full_map 中匹配反向與前向
        full_candidates = []
        for code_k, item in full_map.items():
            name_norm = normalize_stock_name(item.get('name', ''))
            if not name_norm or len(name_norm) < 2:
                continue
            if name_norm in norm_q:
                full_candidates.append((1, -len(name_norm), code_k, item))
            elif name_norm.startswith(norm_q):
                full_candidates.append((2, len(name_norm), code_k, item))
            elif norm_q in name_norm:
                full_candidates.append((3, len(name_norm), code_k, item))
        if full_candidates:
            full_candidates.sort(key=lambda x: (x[0], x[1]))
            best = full_candidates[0]
            code_k, item = best[2], best[3]
            mkt = item.get('market', 'TW')
            return f"{code_k}.{mkt}", code_k, item.get('name', code_k), mkt, "台股標的", False, False

    # 若是純數字代碼但未在字典中
    if q.isdigit():
        return f"{q}.TW", q, q, "TW", "自訂股票", False, False

    # 若含有 .TW 或 .TWO
    if q.upper().endswith('.TW') or q.upper().endswith('.TWO'):
        code = q.split('.')[0]
        return q.upper(), code, code, "TW", "自訂股票", False, False

    return f"{q}.TW", q, q, "TW", "自訂股票", False, False

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    計算均線 (5, 10, 20, 60)、成交量20MA、KD、MACD、RSI、乖離率
    """
    df = df.copy()
    
    # 均線
    df['SMA_5'] = df['Close'].rolling(window=5).mean()
    df['SMA_10'] = df['Close'].rolling(window=10).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_60'] = df['Close'].rolling(window=60).mean()

    # 均量
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()   # 5MA 基本量標準
    df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()

    # KD (9, 3, 3)
    low_min = df['Low'].rolling(window=9).min()
    high_max = df['High'].rolling(window=9).max()
    rsv = ((df['Close'] - low_min) / (high_max - low_min + 1e-9)) * 100
    rsv = rsv.fillna(50)

    k_vals = []
    d_vals = []
    k = 50.0
    d = 50.0
    for r in rsv:
        k = (2.0 / 3.0) * k + (1.0 / 3.0) * r
        d = (2.0 / 3.0) * d + (1.0 / 3.0) * k
        k_vals.append(k)
        d_vals.append(d)
    df['K'] = k_vals
    df['D'] = d_vals

    # MACD (12, 26, 9)
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['MACD'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['DIF'] - df['MACD']

    # RSI (3, 6, 14)
    delta = df['Close'].diff()
    for span in [3, 6, 14]:
        gain = (delta.where(delta > 0, 0)).rolling(window=span).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=span).mean()
        rs = gain / (loss + 1e-9)
        df[f'RSI_{span}'] = 100 - (100 / (1 + rs))

    # 乖離率 BIAS
    df['BIAS_5'] = ((df['Close'] - df['SMA_5']) / (df['SMA_5'] + 1e-9)) * 100
    df['BIAS_20'] = ((df['Close'] - df['SMA_20']) / (df['SMA_20'] + 1e-9)) * 100

    return df

def fetch_realtime_quote(code: str, market: str = "TW") -> dict:
    """
    從台灣證券交易所 (TWSE) / 櫃買中心 (TPEx) 官方 MIS 接口取得盤中即時行情，
    若遇境外伺服器 (如 Streamlit Cloud / AWS) 連線阻擋，自動無縫切換 Yahoo Finance 雙引擎備援！
    """
    if not code:
        return {}

    tw_now = get_tw_now()
    is_index = code in ["^TWII", "TWII", "t00", "TSE", "IX0001"]

    # 1. 第一優先：台灣證券交易所 (TWSE) / 櫃買中心 (TPEx) 官方 MIS 接口 (0.4秒極速，含 13:33 官方收盤撮合價)
    try:
        if is_index:
            url = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch=tse_t00.tw&json=1&delay=0"
        elif code.isdigit():
            ch_candidates = [f"otc_{code}.tw", f"tse_{code}.tw"] if market == "TWO" else [f"tse_{code}.tw", f"otc_{code}.tw"]
            url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={'|'.join(ch_candidates)}&json=1&delay=0"
        else:
            url = None

        if url:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/javascript, */*; q=0.01',
                'Referer': 'https://mis.twse.com.tw/stock/fibest.jsp'
            }
            r = requests.get(url, headers=headers, timeout=(2.5, 3.5))
            if r.status_code == 200:
                data = r.json()
                items = data.get('msgArray', [])
                target_item = None
                for it in items:
                    if is_index or it.get('c') == code:
                        target_item = it
                        break
                if target_item:
                    d_str = target_item.get('d', '')
                    t_str = target_item.get('t', '')
                    if d_str and len(d_str) == 8:
                        today_date = pd.to_datetime(f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}")
                        date_formatted = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"
                        o = float(target_item.get('o', 0)) if target_item.get('o') not in [None, '-', ''] else 0.0
                        h = float(target_item.get('h', 0)) if target_item.get('h') not in [None, '-', ''] else 0.0
                        l = float(target_item.get('l', 0)) if target_item.get('l') not in [None, '-', ''] else 0.0
                        y = float(target_item.get('y', 0)) if target_item.get('y') not in [None, '-', ''] else 0.0
                        z = target_item.get('z', '-')
                        if z in ['-', '', None]:
                            b_list = target_item.get('b', '').split('_')
                            a_list = target_item.get('a', '').split('_')
                            if b_list and b_list[0] and b_list[0] != '-':
                                z = b_list[0]
                            elif a_list and a_list[0] and a_list[0] != '-':
                                z = a_list[0]
                            else:
                                z = y
                        c = float(z) if z not in [None, '-', ''] else y
                        if c > 0:
                            if o <= 0: o = c
                            if h <= 0: h = max(o, c)
                            if l <= 0: l = min(o, c)
                            chg = round(c - y, 2)
                            pct = round((chg / y) * 100, 2) if y > 0 else 0.0
                            v_lots = int(target_item.get('v', 0) or 0)
                            return {
                                "code": "^TWII" if is_index else code,
                                "name": "加權指數" if is_index else target_item.get('n', code),
                                "date": today_date,
                                "date_str": date_formatted,
                                "time": t_str,
                                "open": o,
                                "high": h,
                                "low": l,
                                "close": c,
                                "prev_close": y,
                                "change": chg,
                                "change_pct": pct,
                                "volume": v_lots * 1000,
                                "volume_lots": v_lots,
                                "is_realtime": True
                            }
    except Exception:
        pass

    # 2. 第二優先（雲端海外備援）：Yahoo Finance fast_info (專克境外伺服器連線阻擋)
    try:
        yf_ticker_str = "^TWII" if is_index else (
            code if "." in code else f"{code}.{market}"
        )
        t = yf.Ticker(yf_ticker_str)
        fi = dict(t.fast_info)
        c = float(fi.get('lastPrice') or fi.get('last_price') or 0)
        if c > 0:
            y = float(fi.get('regularMarketPreviousClose') or fi.get('previousClose') or c)
            o = float(fi.get('open') or c)
            h = float(fi.get('dayHigh') or c)
            l = float(fi.get('dayLow') or c)
            chg = round(c - y, 2)
            pct = round((chg / y) * 100, 2) if y > 0 else 0.0
            v_shares = int(fi.get('lastVolume') or 0)
            return {
                "code": code,
                "name": "加權指數" if is_index else code,
                "date": tw_now.floor('D'),
                "date_str": tw_now.strftime('%Y-%m-%d'),
                "time": tw_now.strftime('%H:%M:%S'),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "prev_close": y,
                "change": chg,
                "change_pct": pct,
                "volume": v_shares,
                "volume_lots": int(v_shares / 1000) if v_shares else 0,
                "is_realtime": True
            }
    except Exception:
        pass

    return {}

def _fetch_realtime_chunk(chunk):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://mis.twse.com.tw/stock/fibest.jsp'
    }
    ch_list = []
    for code, market in chunk:
        if code in ["^TWII", "TWII", "t00"]:
            ch_list.append("tse_t00.tw")
            continue
        if not code or not code.isdigit():
            continue
        p = "otc_" if market == "TWO" else "tse_"
        ch_list.append(f"{p}{code}.tw")
    if not ch_list:
        return {}

    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={'|'.join(ch_list)}&json=1&delay=0"
    res = {}
    try:
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code == 200:
            for it in r.json().get('msgArray', []):
                code = it.get('c')
                if not code:
                    continue
                if code == "t00":
                    code = "^TWII"
                d_str = it.get('d', '')
                t_str = it.get('t', '')
                if not d_str or len(d_str) != 8:
                    continue
                today_date = pd.to_datetime(f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}")
                date_formatted = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"

                o = float(it.get('o', 0)) if it.get('o') not in [None, '-', ''] else 0.0
                h = float(it.get('h', 0)) if it.get('h') not in [None, '-', ''] else 0.0
                l = float(it.get('l', 0)) if it.get('l') not in [None, '-', ''] else 0.0
                y = float(it.get('y', 0)) if it.get('y') not in [None, '-', ''] else 0.0
                v_lots = int(it.get('v', 0)) if it.get('v') not in [None, '-', ''] else 0
                v_shares = v_lots * 1000

                z = it.get('z', '-')
                if z == '-' or not z:
                    z = it.get('trade', {}).get('z', '-')
                if z == '-' or not z:
                    b_list = it.get('b', '').split('_')
                    a_list = it.get('a', '').split('_')
                    if b_list and b_list[0] and b_list[0] != '-':
                        z = b_list[0]
                    elif a_list and a_list[0] and a_list[0] != '-':
                        z = a_list[0]
                    else:
                        z = y

                c = float(z) if z not in [None, '-', ''] else y
                if c <= 0:
                    continue
                if o <= 0: o = c
                if h <= 0: h = max(o, c)
                if l <= 0: l = min(o, c)
                chg = round(c - y, 2)
                pct = round((chg / y) * 100, 2) if y > 0 else 0.0

                res[code] = {
                    "code": code,
                    "name": it.get('n', ''),
                    "date": today_date,
                    "date_str": date_formatted,
                    "time": t_str,
                    "open": o,
                    "high": h,
                    "low": l,
                    "close": c,
                    "prev_close": y,
                    "change": chg,
                    "change_pct": pct,
                    "volume": v_shares,
                    "volume_lots": v_lots,
                    "is_realtime": True
                }
    except Exception:
        pass
    return res

def batch_fetch_realtime_quotes(stock_list: list) -> dict:
    """
    批次獲取多檔股票之盤中即時行情 (並行請求 + Yahoo Finance fast_info 全球備援)
    """
    if not stock_list:
        return {}

    items_to_query = []
    for item in stock_list:
        if isinstance(item, str):
            _, code, _, mkt, _, _, _ = resolve_ticker(item)
            items_to_query.append((code, mkt))
        elif isinstance(item, dict):
            items_to_query.append((item.get('code', ''), item.get('market', 'TW')))

    chunk_size = 35
    chunks = [items_to_query[i:i+chunk_size] for i in range(0, len(items_to_query), chunk_size)]

    all_results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        for partial in executor.map(_fetch_realtime_chunk, chunks):
            all_results.update(partial)

    # 關鍵防護：若 TWSE MIS 在境外伺服器 (如 AWS / Streamlit Cloud) 遭到阻擋導致回傳不足，
    # 全自動無縫切換 Yahoo Finance fast_info 並行備援！
    if len(all_results) < len(items_to_query) * 0.3:
        missing_items = [it for it in items_to_query if it[0] not in all_results]
        def _get_yf_quote(it):
            code, mkt = it
            q = fetch_realtime_quote(code, market=mkt)
            return code, q

        with ThreadPoolExecutor(max_workers=10) as ex:
            for c, q in ex.map(_get_yf_quote, missing_items):
                if q and q.get('close', 0) > 0:
                    all_results[c] = q

    return all_results

def fetch_stock_kline(query: str, period="1y", force_refresh=False, enable_realtime=True, realtime_quote=None):
    """
    獲取台股日K線數據，回傳 (df, info_dict)
    """
    ticker, code, name, market, industry, has_futures, has_cb = resolve_ticker(query)
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_{period}.pkl")
    cache_file_1y = os.path.join(CACHE_DIR, f"{ticker}_1y.pkl")

    df = None
    fallback_df = None

    # 檢查快取 (優先檢查本檔，或1年快取，並嚴格檢核時效性)
    if not force_refresh:
        for cf in [cache_file, cache_file_1y]:
            if os.path.exists(cf):
                try:
                    with open(cf, 'rb') as f:
                        loaded = pickle.load(f)
                    if isinstance(loaded, pd.DataFrame) and not loaded.empty and len(loaded) >= 5:
                        if fallback_df is None:
                            fallback_df = loaded

                        last_cached_dt = pd.to_datetime(loaded['Date'].iloc[-1]).date()
                        tw_now = get_tw_now()
                        days_diff = (today_dt - last_cached_dt).days
                        market_closed = (tw_now.hour > 14) or (tw_now.hour == 14 and tw_now.minute >= 30)

                        # 盤後時間 (14:30後)：若最後一筆仍是今天之前，且快取未在近1小時內更新過，才需從 Yahoo 重新拉取已收盤日K
                        if is_weekday and market_closed and last_cached_dt < today_dt:
                            mtime = os.path.getmtime(cf)
                            if (time.time() - mtime) > 3600:
                                continue

                        # 盤中時段 (09:00~14:30) 或近4天內快取：歷史日K直接載入，盤中最新K棒由下方即時行情拼接引擎無縫補齊
                        if days_diff <= 4:
                            df = loaded
                            break
                except Exception:
                    pass

    if df is None or df.empty:
        raw = pd.DataFrame()
        try:
            stock = yf.Ticker(ticker)
            raw = stock.history(period=period, auto_adjust=False)
        except Exception:
            raw = pd.DataFrame()

        if raw.empty and code.isdigit():
            try:
                alt_market = "TWO" if market == "TW" else "TW"
                alt_ticker = f"{code}.{alt_market}"
                raw = yf.Ticker(alt_ticker).history(period=period, auto_adjust=False)
                if not raw.empty:
                    ticker = alt_ticker
                    market = alt_market
            except Exception:
                raw = pd.DataFrame()

        if raw.empty:
            # 若網路獲取失敗但有舊快取，則降級使用舊快取避免拋出異常
            if fallback_df is not None and not fallback_df.empty:
                df = fallback_df
            else:
                return pd.DataFrame(), {
                    "ticker": ticker, "code": code, "name": name,
                    "market": market, "industry": industry, "error": "查無此股票行情數據"
                }

        # 整理欄位
        raw = raw.reset_index()
        raw['Date'] = pd.to_datetime(raw['Date']).dt.tz_localize(None)
        cols_to_keep = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        df = raw[[c for c in cols_to_keep if c in raw.columns]].copy()
        for col in ['Open', 'High', 'Low', 'Close']:
            df[col] = df[col].astype(float)
        df['Volume'] = df['Volume'].fillna(0).astype(int)
        
        # 排除休市日或無成交日 (若是大盤指數則允許 Volume == 0)
        if ticker.startswith("^"):
            df = df[df['Close'] > 0].reset_index(drop=True)
        else:
            df = df[df['Volume'] > 0].reset_index(drop=True)
        if len(df) < 5:
            return pd.DataFrame(), {
                "ticker": ticker, "code": code, "name": name,
                "market": market, "industry": industry, "error": "交易天數不足"
            }

        df = calculate_indicators(df)

        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(df, f)
        except Exception:
            pass

    # ---------------- 證交所盤中即時行情無縫拼接 ----------------
    quote = realtime_quote
    if quote is None and enable_realtime and (code.isdigit() or code.startswith("^") or code in ["^TWII", "TWII", "t00"]) and not df.empty:
        try:
            quote = fetch_realtime_quote(code, market=market)
        except Exception:
            quote = None

    if quote and quote.get('close', 0) > 0 and not df.empty:
        try:
            q_dt = pd.to_datetime(quote['date'])
            df_last_dt = pd.to_datetime(df['Date'].iloc[-1])

            q_open = float(quote.get('open', 0) or 0)
            q_close = float(quote.get('close', 0) or 0)
            q_high = float(quote.get('high', 0) or 0)
            q_low = float(quote.get('low', 0) or 0)
            q_vol = int(quote.get('volume', 0) or 0)

            if q_close > 0:
                if q_open <= 0: q_open = q_close
                if q_high <= 0: q_high = max(q_open, q_close)
                if q_low <= 0: q_low = min(q_open, q_close)

                # 若當日日K已存在於最後一列，更新為最新盤中撮合值
                if df_last_dt.date() == q_dt.date():
                    idx = df.index[-1]
                    cur_h = float(df.loc[idx, 'High']) if pd.notnull(df.loc[idx, 'High']) else q_close
                    cur_l = float(df.loc[idx, 'Low']) if pd.notnull(df.loc[idx, 'Low']) else q_close
                    cur_v = int(df.loc[idx, 'Volume']) if pd.notnull(df.loc[idx, 'Volume']) else 0

                    df.loc[idx, 'Open'] = q_open if q_open > 0 else float(df.loc[idx, 'Open'])
                    df.loc[idx, 'High'] = max(q_high, q_close, cur_h)
                    df.loc[idx, 'Low'] = min(q_low, q_close, cur_l) if q_low > 0 else cur_l
                    df.loc[idx, 'Close'] = q_close
                    df.loc[idx, 'Volume'] = max(q_vol, cur_v)
                elif q_dt.date() > df_last_dt.date():
                    # 歷史日K只到昨收，將今天盤中長出來的最新K棒拼接上去
                    new_candle = pd.DataFrame([{
                        'Date': q_dt,
                        'Open': q_open,
                        'High': max(q_high, q_close),
                        'Low': min(q_low, q_close),
                        'Close': q_close,
                        'Volume': q_vol
                    }])
                    df = pd.concat([df, new_candle], ignore_index=True)

                # 重新計算均線與技術指標 (使5MA/20MA與轉折波完全包含今日即時現價)
                df = calculate_indicators(df)
        except Exception:
            pass

    # 提取即時摘要資訊 (嚴密防護：確保 df 具備有效資料)
    if df is None or df.empty or len(df) == 0:
        return pd.DataFrame(), {
            "ticker": ticker, "code": code, "name": name,
            "market": market, "industry": industry, "error": "查無有效行情數據"
        }

    last_row = df.iloc[-1]
    prev_row = df.iloc[-2] if len(df) > 1 else last_row
    
    if quote and quote.get('prev_close', 0) > 0:
        prev_close_val = float(quote['prev_close'])
    else:
        prev_close_val = float(prev_row['Close'])

    change = last_row['Close'] - prev_close_val
    change_pct = (change / prev_close_val) * 100 if prev_close_val != 0 else 0

    sma5_val = round(float(last_row.get('SMA_5', last_row['Close'])), 2)
    sma20_val = round(float(last_row.get('SMA_20', last_row['Close'])), 2)
    sma60_val = round(float(last_row.get('SMA_60', last_row['Close'])), 2) if 'SMA_60' in df.columns else sma20_val

    # 計算 5 日與 20 日累積報酬率 (動能)
    idx_5 = max(0, len(df) - 6)
    idx_20 = max(0, len(df) - 21)
    p_close = float(last_row['Close'])
    p_5 = float(df['Close'].iloc[idx_5]) if idx_5 < len(df) else p_close
    p_20 = float(df['Close'].iloc[idx_20]) if idx_20 < len(df) else p_close
    return_5d = round(((p_close - p_5) / (p_5 + 1e-9)) * 100, 2)
    return_20d = round(((p_close - p_20) / (p_20 + 1e-9)) * 100, 2)

    info = {
        "ticker": ticker,
        "code": code,
        "name": name,
        "market": market,
        "industry": industry,
        "has_futures": has_futures,
        "has_cb": has_cb,
        "latest_date": last_row['Date'].strftime('%Y-%m-%d'),
        "close": round(float(last_row['Close']), 2),
        "open": round(float(last_row['Open']), 2),
        "high": round(float(last_row['High']), 2),
        "low": round(float(last_row['Low']), 2),
        "prev_close": round(float(prev_close_val), 2),
        "change": round(float(change), 2),
        "change_pct": round(float(change_pct), 2),
        "volume": int(last_row['Volume']),
        "volume_str": f"{int(last_row['Volume'] / 1000):,} 張" if ticker != "^TWII" else f"{int(last_row['Volume'] / 100000000)} 億",
        "sma5": sma5_val,
        "sma20": sma20_val,
        "sma60": sma60_val,
        "return_5d": return_5d,
        "return_20d": return_20d,
        "is_realtime": bool(quote and quote.get('is_realtime')),
        "quote_time": quote.get('time', '') if quote else ''
    }

    return df, info
