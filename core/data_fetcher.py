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

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'cache')
STOCK_LIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'tw_stock_list.json')

def load_stock_list():
    if os.path.exists(STOCK_LIST_PATH):
        with open(STOCK_LIST_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

_STOCK_LIST = load_stock_list()

def search_stocks(query: str):
    """
    依股票代號、中文名稱或產業搜尋股票
    """
    if not query:
        return _STOCK_LIST[:20]
    q = query.strip().upper()
    matches = []
    for s in _STOCK_LIST:
        if q in s['code'] or q in s['name'] or q in s.get('industry', ''):
            matches.append(s)
    return matches

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

def resolve_ticker(query: str):
    """
    解析使用者輸入（代碼或名稱），回傳 (ticker, code, name, market, industry)
    """
    q = query.strip()
    if q == "大盤" or q == "加權指數" or q == "^TWII":
        return "^TWII", "^TWII", "加權指數", "INDEX", "大盤指數", True, False

    # 先在精選 186 檔清單中查找
    stock_list = load_stock_list()
    for s in stock_list:
        if q == s['code'] or q == s['name']:
            market = s.get('market', 'TW')
            ticker = f"{s['code']}.{market}"
            return ticker, s['code'], s['name'], market, s.get('industry', ''), s.get('has_futures', False), s.get('has_cb', False)

    # 在全市場 2350 檔完整代碼字典中查找
    full_map = load_full_stock_map()
    if q in full_map:
        item = full_map[q]
        mkt = item.get('market', 'TW')
        return f"{q}.{mkt}", q, item.get('name', q), mkt, "台股標的", False, False

    for code_k, item in full_map.items():
        if q == item.get('name'):
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
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()   # 基本量 (朱老師 CH4-2 標準)
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
    從台灣證券交易所 (TWSE) / 櫃買中心 (TPEx) 官方 MIS 接口取得盤中即時行情
    """
    if not code or not code.isdigit():
        return {}

    ch_candidates = [f"otc_{code}.tw", f"tse_{code}.tw"] if market == "TWO" else [f"tse_{code}.tw", f"otc_{code}.tw"]
    query_str = "|".join(ch_candidates)
    url = f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={query_str}&json=1&delay=0"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://mis.twse.com.tw/stock/fibest.jsp'
    }

    try:
        r = requests.get(url, headers=headers, timeout=4)
        if r.status_code != 200:
            return {}
        data = r.json()
        items = data.get('msgArray', [])
        target_item = None
        for it in items:
            if it.get('c') == code:
                target_item = it
                break
        if not target_item:
            return {}

        d_str = target_item.get('d', '')
        t_str = target_item.get('t', '')
        if not d_str or len(d_str) != 8:
            return {}

        today_date = pd.to_datetime(f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}")
        date_formatted = f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:]}"

        o = float(target_item.get('o', 0)) if target_item.get('o') not in [None, '-', ''] else 0.0
        h = float(target_item.get('h', 0)) if target_item.get('h') not in [None, '-', ''] else 0.0
        l = float(target_item.get('l', 0)) if target_item.get('l') not in [None, '-', ''] else 0.0
        y = float(target_item.get('y', 0)) if target_item.get('y') not in [None, '-', ''] else 0.0
        v_lots = int(target_item.get('v', 0)) if target_item.get('v') not in [None, '-', ''] else 0
        v_shares = v_lots * 1000

        z = target_item.get('z', '-')
        if z == '-' or not z:
            z = target_item.get('trade', {}).get('z', '-')
        if z == '-' or not z:
            b_list = target_item.get('b', '').split('_')
            a_list = target_item.get('a', '').split('_')
            if b_list and b_list[0] and b_list[0] != '-':
                z = b_list[0]
            elif a_list and a_list[0] and a_list[0] != '-':
                z = a_list[0]
            else:
                z = y

        c = float(z) if z not in [None, '-', ''] else y
        if c <= 0:
            return {}

        if o <= 0: o = c
        if h <= 0: h = max(o, c)
        if l <= 0: l = min(o, c)

        chg = round(c - y, 2)
        pct = round((chg / y) * 100, 2) if y > 0 else 0.0

        return {
            "code": code,
            "name": target_item.get('n', ''),
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
        return {}

def _fetch_realtime_chunk(chunk):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://mis.twse.com.tw/stock/fibest.jsp'
    }
    ch_list = []
    for code, market in chunk:
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
    批次獲取多檔股票之盤中即時行情 (並行請求，1~2秒內完成全市場更新)
    """
    if not stock_list:
        return {}

    items_to_query = []
    for item in stock_list:
        if isinstance(item, str):
            items_to_query.append((item, "TW"))
        elif isinstance(item, dict):
            items_to_query.append((item.get('code', ''), item.get('market', 'TW')))

    chunk_size = 35
    chunks = [items_to_query[i:i+chunk_size] for i in range(0, len(items_to_query), chunk_size)]

    all_results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        for partial in executor.map(_fetch_realtime_chunk, chunks):
            all_results.update(partial)

    return all_results

def fetch_stock_kline(query: str, period="1y", force_refresh=False, enable_realtime=True, realtime_quote=None):
    """
    抓取台股日K線數據，回傳 (df, info_dict)
    """
    ticker, code, name, market, industry, has_futures, has_cb = resolve_ticker(query)
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_{period}.pkl")

    df = None
    cache_file = os.path.join(CACHE_DIR, f"{ticker}_{period}.pkl")
    cache_file_1y = os.path.join(CACHE_DIR, f"{ticker}_1y.pkl")

    # 檢查快取 (優先檢查本檔，或1年快取)
    if not force_refresh:
        for cf in [cache_file, cache_file_1y]:
            if os.path.exists(cf):
                try:
                    with open(cf, 'rb') as f:
                        loaded = pickle.load(f)
                        if isinstance(loaded, pd.DataFrame) and not loaded.empty and len(loaded) >= 5:
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
        
        # 排除休市日或無成交日
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
    if quote is None and enable_realtime and code.isdigit() and not df.empty:
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
    change = last_row['Close'] - prev_row['Close']
    change_pct = (change / prev_row['Close']) * 100 if prev_row['Close'] != 0 else 0

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
        "prev_close": round(float(prev_row['Close']), 2),
        "change": round(float(change), 2),
        "change_pct": round(float(change_pct), 2),
        "volume": int(last_row['Volume']),
        "volume_str": f"{int(last_row['Volume'] / 1000):,} 張" if ticker != "^TWII" else f"{int(last_row['Volume'] / 100000000)} 億",
        "is_realtime": bool(quote and quote.get('is_realtime')),
        "quote_time": quote.get('time', '') if quote else ''
    }

    return df, info
