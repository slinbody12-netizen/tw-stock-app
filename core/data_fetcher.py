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

    # 1. 若為加權指數 (^TWII)，Yahoo Finance fast_info 全球暢通、毫無海外阻擋，優先直接獲取
    if is_index:
        try:
            t = yf.Ticker("^TWII")
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
                    "code": "^TWII",
                    "name": "加權指數",
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

    # 2. 嘗試官方 TWSE MIS 接口 (毫秒級撮合)
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
            r = requests.get(url, headers=headers, timeout=(1.5, 2.0))
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
                                "code": code,
                                "name": target_item.get('n', code),
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

    # 3. 全球備援雙引擎：Yahoo Finance fast_info (100% 暢通，專克雲端環境與境外 IP 阻擋)
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
                        today_dt = tw_now.date()
                        is_weekday = today_dt.weekday() < 5
                        market_started = (tw_now.hour > 9) or (tw_now.hour == 9 and tw_now.minute >= 0)

                        # 若今天為平日且已過 09:00 開盤，但快取的最後一筆日K停留在今天之前，視為過期不可直接採用！
                        if is_weekday and market_started and last_cached_dt < today_dt:
                            continue

                        # 1. 若該快取檔在近 6 小時內剛寫入/更新過，且日期完整，直接載入
                        mtime = os.path.getmtime(cf)
                        if (time.time() - mtime) < 21600:
                            df = loaded
                            break

                        # 2. 檢核最後一根 K 棒是否在 4 天內 (涵蓋週四/週五/週末連假)
                        days_diff = (today_dt - last_cached_dt).days
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
        "return_5d": return_5d,
        "return_20d": return_20d,
        "is_realtime": bool(quote and quote.get('is_realtime')),
        "quote_time": quote.get('time', '') if quote else ''
    }

    return df, info
