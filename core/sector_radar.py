# -*- coding: utf-8 -*-
"""
全自動主流族群熱度雷達引擎 (Sector Heat Radar Pro)
1. 建立 Top-Down（由上而下）雙維度量化模型：
   - 資金集中度 (45% 權重)：全市場成交金額佔比 (Turnover Share %)
   - 族群漲幅強度 (35% 權重)：族群內部平均漲跌幅 (Avg Change %)
   - 多頭齊漲廣度 (20% 權重)：族群內站穩 5MA 且收紅之強勢股比例 (Bull Ratio %)
2. 自動識別市場當前火熱主流板塊 (Top 5 Hot Sectors)
3. 為個股推薦引擎提供主流風口加權 (+35分) 與冷門降權 (-40分)
4. 毫秒級快取機制，支援盤中與盤後高速查詢
"""

import time
from collections import defaultdict

_SECTOR_HEAT_CACHE = None
_SECTOR_HEAT_TIME = 0

# 產業大類標準化對照表 (Granular Industry -> Broad Sector Category)
BROAD_SECTOR_MAP = {
    # 光學與鏡片
    '光學鏡片': '光學鏡片', '光學': '光學鏡片', '鏡片': '光學鏡片', '光學元件': '光學鏡片', '車載光學': '光學鏡片',
    '光電': '光電/光學', '光電業': '光電/光學',
    # 航運
    '貨櫃航運': '航運業', '散裝航運': '航運業', '航空': '航運業', '陸運': '航運業', '物流': '航運業',
    # 金融
    '金控': '金融保險', '銀行': '金融保險', '證券': '金融保險', '保險': '金融保險', '租賃': '金融保險',
    # 半導體 / IC
    '晶圓代工': '半導體/IC', 'IC設計': '半導體/IC', '驅動IC': '半導體/IC', '半導體封測': '半導體/IC',
    '記憶體': '半導體/IC', '矽晶圓': '半導體/IC', '矽智財ASIC': '半導體/IC', 'IC基板': '半導體/IC',
    # AI 伺服器與散熱硬體
    '散熱模組': 'AI與散熱硬體', '伺服器代工': 'AI與散熱硬體', 'PCB': 'AI與散熱硬體', '玻纖布': 'AI與散熱硬體',
    '電子零組件': 'AI與散熱硬體', '電腦及週邊設備業': 'AI與散熱硬體', '機殼': 'AI與散熱硬體',
    '電源供應器': 'AI與散熱硬體', '代工組裝': 'AI與散熱硬體',
    # 網通與 CPO 光通訊
    '光通訊': '通訊與CPO', '網通設備': '通訊與CPO', '通訊設備': '通訊與CPO', '天線': '通訊與CPO',
    # 電子通路
    'IC通路': '電子通路', '電子零組件通路': '電子通路',
    # 被動元件
    '被動元件': '被動元件', '電阻': '被動元件', '電容': '被動元件', '電感': '被動元件',
    # 軟體與資服
    '系統整合': '軟體與資服', '軟體其他': '軟體與資服', '雲端服務': '軟體與資服', '資訊安全': '軟體與資服',
    # 工業電腦 / 物聯網
    '工業電腦': '工業電腦/物聯網', '自動化設備': '工業電腦/物聯網', '機器人': '工業電腦/物聯網',
    # 重電與綠能
    '重電設備': '電機與重電', '電機機械': '電機與重電', '風電': '電機與重電', '太陽能': '電機與重電',
    '太陽能網版': '電機與重電', '儲能': '電機與重電', '電線電纜': '電機與重電',
    # 傳產原物料 (常態防禦/冷門)
    '水泥工業': '傳產原物料', '塑膠工業': '傳產原物料', '鋼鐵工業': '傳產原物料',
    '橡膠工業': '傳產原物料', '玻璃陶瓷': '傳產原物料', '造紙工業': '傳產原物料', '紡織纖維': '傳產原物料',
    # 生技醫療
    '醫療器材': '生技醫療', '製藥': '生技醫療', '新藥研發': '生技醫療', '生技醫藥': '生技醫療',
    # 汽車零組件
    '汽車工業': '汽車與車用', '車用電子': '汽車與車用', '電動車': '汽車與車用',
    # 營建
    '建材營造': '建材營造', '營造工程': '建材營造'
}

def resolve_broad_sector(raw_industry: str) -> str:
    """將細分產業對齊至宏觀主流類股"""
    if not raw_industry:
        return "其他電子"
    raw = raw_industry.strip()
    return BROAD_SECTOR_MAP.get(raw, raw)

def calculate_sector_heat_rankings(stocks_data: list = None, force_refresh=False) -> list:
    """
    依全市場股票數據，即時運算全市場族群熱度排行榜 (Sector Heat Rankings)
    回傳按熱度降序排列之族群字典清單
    """
    global _SECTOR_HEAT_CACHE, _SECTOR_HEAT_TIME
    now = time.time()
    if not force_refresh and _SECTOR_HEAT_CACHE is not None and (now - _SECTOR_HEAT_TIME) < 180:
        return _SECTOR_HEAT_CACHE

    if stocks_data is None:
        try:
            from core.screener import get_all_analyzed_stocks
            stocks_data = get_all_analyzed_stocks(enable_realtime=False)
        except Exception:
            stocks_data = []

    if not stocks_data:
        return _SECTOR_HEAT_CACHE or []

    sector_groups = defaultdict(lambda: {
        'count': 0,
        'turnover': 0.0,
        'total_chg': 0.0,
        'bull_count': 0,
        'leader_stocks': []
    })

    total_market_turnover = 0.0

    for s in stocks_data:
        raw_ind = s.get('industry', '其他')
        sector_name = resolve_broad_sector(raw_ind)
        close_p = float(s.get('close', 0) or 0)
        vol = float(s.get('volume', 0) or 0)
        chg = float(s.get('change_pct', 0) or 0)

        # 成交金額 (以億元為單位)
        turnover_e = (close_p * vol) / 100000000.0
        total_market_turnover += turnover_e

        sec = sector_groups[sector_name]
        sec['count'] += 1
        sec['turnover'] += turnover_e
        sec['total_chg'] += chg

        # 判定該個股是否為多頭推升中 (站在 5MA 之上且未跌)
        if s.get('above_5ma', False) and chg >= 0:
            sec['bull_count'] += 1

        sec['leader_stocks'].append({
            'code': s.get('code', ''),
            'name': s.get('name', ''),
            'close': close_p,
            'change_pct': chg,
            'quality_score': float(s.get('quality_score', 0) or 0),
            'turnover_e': turnover_e
        })

    total_market_turnover = max(total_market_turnover, 1.0)
    ranked_sectors = []

    for sec_name, d in sector_groups.items():
        if d['count'] < 1:
            continue

        avg_chg = round(d['total_chg'] / d['count'], 2)
        turnover_share = round((d['turnover'] / total_market_turnover) * 100.0, 2)
        bull_ratio = round((d['bull_count'] / d['count']) * 100.0, 1)

        # 按照成交額與品質排序該族群代表龍頭
        d['leader_stocks'].sort(key=lambda x: (x['turnover_e'], x['quality_score']), reverse=True)
        top_stocks = d['leader_stocks'][:5]

        # 核心熱度模型 (0 ~ 100 分)
        # 1. 資金集中度 (45%): 佔比每 1% 得 3 分，上限 45 分
        score_turnover = min(turnover_share * 3.0, 45.0)
        # 2. 漲幅強度 (35%): 均漲幅每 1% 得 8 分，上限 35 分，負漲幅扣分
        score_momentum = max(min((avg_chg + 1.0) * 8.0, 35.0), 0.0)
        # 3. 齊漲廣度 (20%): 站穩 5MA 比例 100% 得 20 分
        score_breadth = (bull_ratio / 100.0) * 20.0

        heat_score = round(score_turnover + score_momentum + score_breadth, 1)

        # 評級標籤與配色
        if heat_score >= 50.0 or turnover_share >= 15.0:
            badge = "🔥 超熱門主流"
            badge_color = "#FF4D4F"
            level = "SUPER_HOT"
        elif heat_score >= 38.0 or turnover_share >= 5.0:
            badge = "⚡ 資金聚焦"
            badge_color = "#FA8C16"
            level = "HOT"
        elif heat_score >= 26.0:
            badge = "⚪ 常態輪動"
            badge_color = "#1890FF"
            level = "NORMAL"
        else:
            badge = "❄️ 冷門邊緣"
            badge_color = "#8C8C8C"
            level = "COLD"

        ranked_sectors.append({
            "sector": sec_name,
            "count": d['count'],
            "turnover_e": round(d['turnover'], 1),
            "turnover_share": turnover_share,
            "avg_chg": avg_chg,
            "bull_ratio": bull_ratio,
            "heat_score": heat_score,
            "badge": badge,
            "badge_color": badge_color,
            "level": level,
            "leader_stocks": top_stocks,
            "leader_names": [s['name'] for s in top_stocks]
        })

    # 按熱度分數嚴格降序排列
    ranked_sectors.sort(key=lambda x: x['heat_score'], reverse=True)

    # 依客觀綜合排名重新標註等級與勳章
    for rank, sec in enumerate(ranked_sectors, 1):
        sec['rank'] = rank
        if rank <= 5 or sec['turnover_share'] >= 10.0:
            sec['badge'] = "🔥 超熱門主流"
            sec['badge_color'] = "#FF4D4F"
            sec['level'] = "SUPER_HOT"
        elif rank <= 12 or sec['turnover_share'] >= 3.0:
            sec['badge'] = "⚡ 資金聚焦"
            sec['badge_color'] = "#FA8C16"
            sec['level'] = "HOT"
        elif rank <= 25 or sec['turnover_share'] >= 0.8:
            sec['badge'] = "⚪ 常態輪動"
            sec['badge_color'] = "#1890FF"
            sec['level'] = "NORMAL"
        else:
            sec['badge'] = "❄️ 冷門邊緣"
            sec['badge_color'] = "#8C8C8C"
            sec['level'] = "COLD"

    _SECTOR_HEAT_CACHE = ranked_sectors
    _SECTOR_HEAT_TIME = now
    return ranked_sectors

def get_sector_heat_rankings(stocks_data: list = None, force_refresh=False) -> list:
    """便捷獲取主流族群熱度排行榜（優先讀取記憶體快取）"""
    return calculate_sector_heat_rankings(stocks_data=stocks_data, force_refresh=force_refresh)

def get_stock_sector_info(stock_record: dict, sector_rankings: list = None) -> dict:
    """
    查詢指定個股所屬族群的熱度數據、排名與加權權重
    """
    if not sector_rankings:
        sector_rankings = _SECTOR_HEAT_CACHE or []

    raw_ind = stock_record.get('industry', '其他')
    sector_name = resolve_broad_sector(raw_ind)

    # 查表匹配
    for sec in sector_rankings:
        if sec['sector'] == sector_name:
            return {
                "sector": sector_name,
                "rank": sec['rank'],
                "heat_score": sec['heat_score'],
                "turnover_share": sec['turnover_share'],
                "avg_chg": sec['avg_chg'],
                "badge": sec['badge'],
                "badge_color": sec['badge_color'],
                "level": sec['level'],
                "is_top_mainstream": sec['rank'] <= 5 or sec['turnover_share'] >= 8.0,
                "is_cold_marginal": sec['rank'] > 20 and sec['turnover_share'] < 1.0
            }

    # 預設一般
    return {
        "sector": sector_name,
        "rank": 99,
        "heat_score": 25.0,
        "turnover_share": 0.5,
        "avg_chg": 0.0,
        "badge": "⚪ 常態輪動",
        "badge_color": "#1890FF",
        "level": "NORMAL",
        "is_top_mainstream": False,
        "is_cold_marginal": False
    }
