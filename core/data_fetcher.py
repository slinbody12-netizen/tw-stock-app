# -*- coding: utf-8 -*-
"""
數據獲取與指標計算模組
支援台股 (TWSE/TPEx) 日線歷史數據抓取、代碼與名稱搜尋、快取與各類常用技術指標計算。
"""

import os
import json
import time
import pickle
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

def resolve_ticker(query: str):
    """
    解析使用者輸入（代碼或名稱），回傳 (ticker, code, name, market, industry)
    """
    q = query.strip()
    if q == "大盤" or q == "加權指數" or q == "^TWII":
        return "^TWII", "^TWII", "加權指數", "INDEX", "大盤指數"

    # 先在清單中查找
    stock_list = load_stock_list()
    for s in stock_list:
        if q == s['code'] or q == s['name']:
            market = s.get('market', 'TW')
            ticker = f"{s['code']}.{market}"
            return ticker, s['code'], s['name'], market, s.get('industry', ''), s.get('has_futures', False), s.get('has_cb', False)

    # 若是純數字代碼但未在預設清單中
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

def fetch_stock_kline(query: str, period="1y", force_refresh=False):
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
                        if isinstance(loaded, pd.DataFrame):
                            df = loaded
                            break
                except Exception:
                    pass

    if df is None:
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
            # 建立空快取，避免重複請求網路超時
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(pd.DataFrame(), f)
            except Exception:
                pass
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

    # 提取即時摘要資訊
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
        "volume_str": f"{int(last_row['Volume'] / 1000):,} 張" if ticker != "^TWII" else f"{int(last_row['Volume'] / 100000000)} 億"
    }

    return df, info
