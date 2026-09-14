# -*- coding: utf-8 -*-
"""
AI 課程助教問答與深度實戰決策核心 (AI Teaching Assistant Pro - 支援歷史覆盤時光機)
1. 支援自然語言日期抽取 (如 8/26, 8月21日, 2026-08-26, 昨天, 前天, 上週五)
2. 支援指定日期歷史時光倒流切片 (Historical Replay Slicing)
3. 自動排查爆量黑K套牢、連漲追高、前高距離
4. 給出明確操作定調與後續應對劇本
5. 支援純課程觀念理論深度解答 (如 跌破5MA與虧損5%停損區別、一字底突破、均線扣抵)
"""

import re
import pandas as pd
import numpy as np
from core.data_fetcher import fetch_stock_kline, load_stock_list
from core.wave_engine import calculate_turning_points
from core.trend_analyzer import analyze_trend
from core.signal_detector import detect_signals

COURSE_KNOWLEDGE = {
    "回後買上漲": (
        "【回後買上漲 核心要訣】\n"
        "1. 先決條件：大趨勢必須先確認為多頭（頭頭高、底底高），或一字底強勢放量突破。\n"
        "2. 回檔特徵：多頭上漲後必然會拉回修正，回檔時低點「絕不能跌破前一波波段低點（支撐底）」。\n"
        "3. 均線支撐：回測 5MA 或 20MA（月線）通常有強烈支撐，成交量通常呈現「價跌量縮」。\n"
        "4. 進場確認：當拉回有守後，出現一根實體紅 K 棒重新「收盤站上 5MA」或「突破前一天 K 棒高點」，就是最佳進場點！"
    ),
    "一字底": (
        "【一字底 飆股起漲型態】\n"
        "1. 整理時間：在極狹幅區間內橫盤至少 60 天（2 個月以上），時間越長爆發力越強。\n"
        "2. 均線狀態：5MA、10MA、20MA、60MA 全數呈水平「平躺糾結」狀態。\n"
        "3. K線特徵：整理過程中常出現帶上影線之 K 線試盤。\n"
        "4. 突破訊號：當日出現長紅 K 棒，成交量放大至 20 日均量 1.5 倍以上強勢突破箱頂。\n"
        "5. 操作：突破當天或次日進場，後續常伴隨連續漲勢！"
    ),
    "實戰五步驟": (
        "【技術分析實戰五步驟】\n"
        "步驟一【六字訣確認趨勢】：多頭只做「頭頭高、底底高」；空頭只做「頭頭低、底底低」。\n"
        "步驟二【觀察均線排列】：做多必須 5MA > 10MA > 20MA > 60MA 四線多排或至少雙線多排向上。\n"
        "步驟三【檢視量能變化】：底部盤整需有進貨量（Volume > 20MA Volume），量增價漲。\n"
        "步驟四【K線進場與停損】：短線站上 5MA 進場，跌破 5MA 或虧損 5% 果斷停損；中波段跌破 20MA 或跌 8%~15% 停損。\n"
        "步驟五【資金控管與停利】：短線達 5%~8%、中線達 8%~15% 嚴格分批或全數停利，入袋為安！"
    ),
    "停損停利": (
        "【停損與停利心法】\n"
        "1. 順勢不逆勢，買強不買弱，買低不追高，停損不套牢，停利不猶豫。\n"
        "2. 短線停損：收盤跌破 5MA，或進場點虧損達 5%。\n"
        "3. 破前低停損：多頭架構一旦跌破前一個波段低點（底），多頭破壞，立刻出場。\n"
        "4. 停利時機：達到預設目標價、或出現高檔爆量長黑、或跌破 5MA 轉折向下時毫不猶豫執行。"
    ),
    "均線扣抵": (
        "【均線移動扣抵原理】\n"
        "1. 5MA 扣抵：將今日收盤價與 5 天前的收盤價比較。\n"
        "2. 若今日股價 > 5天前扣抵價，均線明天將「扣低助漲向上」；若今日股價 < 5天前扣抵價，均線將「扣高下彎助跌」。\n"
        "3. 20MA / 60MA 同理，操作前先看未來 3 天扣抵位置，可提前預判均線助漲或下彎壓力！"
    )
}

def extract_target_symbol(query: str, default_code: str = "2330"):
    """
    從問題文字中自動抽取股票代號或名稱
    回傳 (code, has_explicit_stock)
    """
    code_matches = re.findall(r'\b\d{4}\b', query)
    if not code_matches:
        code_matches = re.findall(r'\d{4}', query)
    if code_matches:
        return code_matches[0], True
    
    all_stocks = load_stock_list()
    for s in all_stocks:
        if s['name'] in query:
            return s['code'], True

    # 只有明確使用代名詞指稱當前畫面上個股時，才判定為針對當前股票診斷
    context_keywords = ["這檔", "該股", "這支", "手中持股", "這檔股票", "目前這檔", "當前個股", "這檔目前"]
    if any(k in query for k in context_keywords):
        return default_code, True

    return default_code, False

def extract_date_from_query(query: str, df: pd.DataFrame):
    """
    從問題中自動提取指定的日期 (支援 8/26, 08/26, 8-26, 8月26日, 2026-08-26, 昨天, 前天, 上週五等)
    """
    if df.empty:
        return None

    q = query.strip()
    latest_ts = df['Date'].iloc[-1]
    latest_year = latest_ts.year

    q_no_code = re.sub(r'\d{4}', ' ', q)

    m_full = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})[日號]?', q)
    if m_full:
        y, m, d = int(m_full.group(1)), int(m_full.group(2)), int(m_full.group(3))
        return f"{y:04d}-{m:02d}-{d:02d}"

    m_md = re.search(r'(\d{1,2})[月/\.-](\d{1,2})[日號]?', q_no_code)
    if m_md:
        m, d = int(m_md.group(1)), int(m_md.group(2))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return f"{latest_year:04d}-{m:02d}-{d:02d}"

    if any(k in q for k in ["昨天", "昨日", "前一天", "前一日"]):
        if len(df) >= 2:
            return df['Date'].iloc[-2].strftime('%Y-%m-%d')
    elif any(k in q for k in ["前天", "前日", "前兩天", "前二天", "前2天"]):
        if len(df) >= 3:
            return df['Date'].iloc[-3].strftime('%Y-%m-%d')
    elif any(k in q for k in ["大前天", "前三天", "前3天"]):
        if len(df) >= 4:
            return df['Date'].iloc[-4].strftime('%Y-%m-%d')
    elif any(k in q for k in ["上週五", "上星期五", "上禮拜五"]):
        for k in range(len(df) - 1, max(-1, len(df) - 15), -1):
            dt = df.iloc[k]['Date']
            if dt.weekday() == 4 and dt.date() != latest_ts.date():
                return dt.strftime('%Y-%m-%d')

    return None

def answer_conceptual_question(query: str) -> str:
    """
    回答技術分析全攻略純課程觀念理論與紀律疑難
    """
    q = query.strip()

    if ("5MA" in q and "5%" in q) or ("停損" in q and ("區別" in q or "差異" in q or "差別" in q or "怎麼配" in q or "如何搭配" in q)):
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：跌破 5MA 停損 與 虧損 5% 停損 的本質差異與實戰搭配】**

在《技術分析全攻略》課程體系中，這兩個停損機制分別代表「**技術面指標防守**」與「**資金風控絕對防線**」，具有完全不同的防護任務：

---
#### 🛡️ 一、跌破 5MA 停損 ——「技術面攻擊慣性破壞」
1. **核心意義**：
   - 5MA（5日移動平均線）是極短線多頭強勢上攻的「操盤生命線」。
   - 多頭發動時，K棒通常會沿著 5MA 連續推升。只要每天收盤都在 5MA 之上，代表短線多方控盤節奏完好，持股者無須預設立場猜頂，一路抱牢奔跑。
   - 一旦出現實體黑 K「收盤正式跌破 5MA」，代表短線攻擊動能減弱，容易轉為橫盤震盪或即將拉回測試 20MA（月線）。
2. **出場依據**：以「**K 線與均線的型態轉折**」為準，不看個人目前部位賺多或賺少。

---
#### 💰 二、虧損 5% 停損 ——「本金安全之鐵的紀律保險絲」
1. **核心意義**：
   - 這是以「**個人進場成本價**」為基準的嚴格停損底線。
   - 保全本金是股票市場長期存活的唯一鐵律！若買進後市場出現突發利空、跳空下殺或個人判斷錯誤，只要單筆部位帳面虧損達到 **5%**，必須立刻「市價無條件停損出場」。
2. **出場依據**：以「**帳面虧損金額比例**」為準，不論技術線型如何，絕不凹單、絕不心存僥倖！

---
#### ⚡ 三、兩者如何搭配執行？——【何者先到，就執行何者！】
實戰操盤時特別強調：**絕不可把兩者孤立看待，而是要同時設定「雙重保險」**：
- 📌 **情況 A（先跌破 5MA，虧損尚未達 5%）**：
  例如買進後股價小幅拉回 1.5%，但收盤已收在 5MA 之下。此時應依據「跌破 5MA 停損」立即退場，只賠 1.5% 就能保全 98.5% 的本金，**絕不能心存僥倖說「等跌滿 5% 再砍」**！
- 📌 **情況 B（突發跳空大跌，直接虧損滿 5%）**：
  若遇到系統性重挫或跳空，即便均線指標尚未完全跌破，只要帳面虧損觸及 **-5%**，立即無條件停損砍單，杜絕擴大成 10%、20% 的毀滅性套牢！

---
#### 🎯 助教金句總結：
> **「順勢不逆勢，買強不買弱，買低不追高，停損不套牢，停利不猶豫！」**
> 跌破 5MA 是為了在攻擊熄火時優雅出場保住獲利；虧損 5% 是為了保命防身，把虧損鎖在最小範圍。兩者並行，才能在股海立於不敗之地！"""

    if "一字底" in q:
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：一字底（箱型橫盤突破）飆股型態之判斷條件與進場點】**

「一字底」是《技術分析全攻略》中最具爆發力的主升段起漲型態，其核心特徵與確認要件如下：

---
#### 🔍 一、一字底的四大標準確認要件：
1. **橫盤時間足夠長**：
   - 股價在狹幅區間內橫向水平整理，時間至少達到 **60 個交易日（2~3 個月以上）**，時間越長、浮額洗得越乾淨，後續突破噴出的爆發力越驚人！
2. **四條均線水平糾結**：
   - 5MA、10MA、20MA、60MA 全數由發散轉為呈水平線狀「高度糾結平躺」，此為主力長期在低檔暗中吃貨吸籌的典型特徵。
3. **區間波動極度壓縮**：
   - 整理期間成交量大多萎縮至冰點（量縮整理），期間偶有帶上下影線的紅黑K棒進行「試盤與洗盤」。
4. **帶量長紅向上突破**：
   - 突破當天必須出現**實體長紅 K 棒**，且成交量必須放大至 **20 日均量的 1.5 倍至 2 倍以上**，強勢收盤突破箱型整理的最高點（箱頂壓力）！

---
#### 🚀 二、實戰進場時機與操作紀律：
1. **第一買點（突破當天）**：
   - 當天盤中或尾盤確認放量站上箱頂，或以實體紅 K 漲幅逾 3.5%~5% 正式確認一字底突破時，立刻進場！
2. **第二買點（回測不破）**：
   - 若錯過突破當天，切勿在連續大漲後追高。等待股價突破後出現 1~3 天量縮回測箱頂（前波高點）或回測 5MA，回測有守再度拉出轉折紅 K 時切入。
3. **停損紀律**：
   - 以突破紅 K 的低點、或是箱頂支撐價為基準，跌破即代表假突破，嚴格停損出場。"""

    if ("實戰五步驟" in q) or ("五步驟" in q) or ("量化紀律" in q):
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：技術分析實戰操作五步驟之量化紀律】**

實戰操作五步驟是將所有技術指標化繁為簡的SOP量化進出場指南：

---
1. **步驟一【六字訣確認趨勢】（定方向）**：
   - 做多只做多頭：必須滿足「**頭頭高、底底高**」；
   - 放空只做空頭：必須滿足「**頭頭低、底底低**」；
   - 盤整走勢高低未同向突破：不急於進場，先列入【等突破】鎖股池。

2. **步驟二【檢視均線排列】（看阻力）**：
   - 做多時，均線必須呈多頭排列（5MA > 10MA > 20MA > 60MA），且均線方向向上；
   - 至少要求 5MA 與 20MA 呈黃金交叉向上。頭頂絕不可有下彎的季線（60MA）重壓。

3. **步驟三【檢視成交量能】（找動能）**：
   - 多頭發動必須「價漲量增」；
   - 突破關鍵壓力或起漲紅 K，成交量必須達到 **20 日均量的 1.5 倍以上**；
   - 回檔整理時必須「價跌量縮」，成交量低於 20MA 均量。

4. **步驟四【K線訊號進場與停損】（抓買賣點）**：
   - **進場訊號**：回測均線有守出轉折紅 K 站上 5MA，或一字底帶量突破箱頂；
   - **停損紀律**：進場前先算好停損價！短線跌破 5MA 或虧損達 5% 果斷停損出場，絕不凹單。

5. **步驟五【資金控管與停利】（保獲利）**：
   - 單檔股票持股部位不超過總資金 20%~30%；
   - 短線獲利 5%~8%、中波段獲利 8%~15% 達到目標價或高檔爆量長黑時，毫不猶豫分批停利入袋！"""

    if ("扣抵" in q) or ("均線扣抵" in q):
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：均線扣抵原理與預判均線助漲助跌心法】**

均線（Moving Average）的走勢方向並非由今日股價單獨決定，而是取決於「今日收盤價」與「N 天前被替換掉的那一根 K 棒（扣抵值）」的大小比較：

---
#### 📐 一、扣抵計算核心公式：
- **今日 5MA** = (今日收盤 + 昨收 + 前天收 + 大前天收 + 4天前收) / 5
- **明日 5MA** = (明日收盤 + 今日收 + 昨收 + 前天收 + 大前天收) / 5
- 換句話說：明天 5MA 要往上揚還是往下彎，關鍵在於「**明天的股價是否高於 5 天前扣抵的那根 K 棒收盤價**」！

---
#### 📈 二、扣抵判讀三大實戰心法：
1. **扣低助漲（多方黃金加速期）**：
   - 當均線未來幾天的扣抵值落在「歷史相對低檔區」，代表只要目前的股價維持在平盤或微幅震盪，均線每天都會自動迅速往上揚升，形成強烈的「均線助漲支撐推力」！
2. **扣高助跌（空方下壓危險期）**：
   - 當均線未來幾天的扣抵值即將進入「歷史相對高檔區」，代表目前的股價必須大幅拉出大長紅才能維持均線上揚；一旦股價沒漲，均線就會被迫「扣低下彎」，形成沉重的反壓下蓋！
3. **操作應對**：
   - 買進前務必檢查 20MA（月線）與 60MA（季線）未來 3~5 天的扣抵位置：
     - 若扣低：順勢偏多操作，均線提供護盤底氣；
     - 若扣高：嚴防均線下彎反蓋，不宜重押或追高！"""

    if ("回後買上漲" in q) and ("什麼是" in q or "條件" in q or "要訣" in q or "定義" in q):
        return f"""### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：回後買上漲 核心型態與進場要訣】**

{COURSE_KNOWLEDGE['回後買上漲']}"""

    # 檢查是否詢問「回後買上漲 / 拉回找買點 / 漲幅過2% / 轉折紅K進場」
    if (("拉回" in q or "回檔" in q or "回後" in q) and ("買" in q or "進場" in q or "買點" in q or "位置" in q)) or \
       ("漲幅" in q and ("拉回" in q or "買點" in q or "進場" in q or "位置" in q or "買" in q)) or \
       ("回後買上漲" in q):
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：漲幅過 2% 是否算「拉回找買點（回後買上漲）」的進場位置？】**

許多學員在盤中常有疑問：「**股價拉回整理後，當天漲幅超過 2%，是不是就代表拉回找買點的進場位置出現了？**」

#### 💡 助教核心結論：
> ### 🛑 **「不能單憑漲幅過 2% 就衝動進場！漲幅只是動能表象，必須符合回後買上漲的 4 大核心量化紀律！」**

---

#### 🔍 為什麼「光漲幅過 2%」不等於安全買點？
1. **可能是均線下彎的「弱勢反彈假動作」**：
   若 5MA 操盤線仍在快速下彎助跌，股價當天即使上漲 2%，但收盤若仍被下彎的 5MA 壓制在底下，這叫做「反彈碰壁」，隔天極易順著均線下彎慣性再破底！
2. **可能是拉高解套的長上影線**：
   若早盤衝高漲 2%~3%，但尾盤拉回留下長上影線（避雷針），代表上方解套賣壓沉重，並非真正主力吃籌碼的轉折長紅。

---

#### 📋 助教標準量化 SOP：標準「回後買上漲」進場 4 大必備要件

想要在 **12:40 - 13:30 尾盤** 穩健進場，必須同時滿足：

1. **【六字訣趨勢：底底高不可破】**：
   - 拉回整理過程中的最低點，**絕對不能跌破前一波起漲的波段低點（支撐底）**！跌破前低即轉為底底低或盤整，拉回不是買點，而是破線逃命點。
2. **【回測支撐量縮有守】**：
   - 股價回測 5MA 或 20MA（月線）時，成交量必須呈現「價跌量縮」的健康洗盤特徵。
3. **【尾盤實體紅 K 站穩 5MA】（最關鍵進場確認訊號！）**：
   - 漲幅約在 **+1.5% ~ +3.5%** 以上的實體紅 K，且在 **12:40 - 13:30 尾盤** 必須確認「**收盤價正式站上 5MA（操盤線）**」（或突破前一日高點）！
   - 同時 5MA 走平或開始微幅翻揚，才代表短線多方攻擊動能正式重啟。
4. **【上方無重大爆量長黑 K 套牢反壓】**：
   - 檢視前方 3%~5% 空間內有無剛爆大量留長黑 K 的套牢籌碼。若空間乾淨，進場勝率才高達 8 成以上！

---
🎯 **助教叮嚀一句話**：
「**趨勢底不破底 + 量縮測線有守 + 尾盤轉折紅 K 站上 5MA**」才是真正的拉回進場點；切記「只看均線與型態轉折，不單看漲幅數字」！"""

    # 六字訣趨勢
    if ("六字訣" in q) or ("頭頭高" in q) or ("底底高" in q) or ("趨勢判斷" in q):
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：六字訣判斷多空趨勢與實戰紀律】**

《技術分析全攻略》的核心操盤靈魂在於「順勢而為」，六字訣是辨識市場多空趨勢的最高原則：

---
#### 📈 一、多頭趨勢：【頭頭高、底底高】
- **特徵**：每一波上漲的高點突破前波高點（頭頭高 ↗），每一波拉回的低點不跌破前波低點（底底高 ↗）。
- **操作策略**：**只做多、不做空**！利用「回後買上漲」拉回找買點，或「突破起漲」做多，順著多頭浪潮一路賺波段！

#### 📉 二、空頭趨勢：【頭頭低、底底低】
- **特徵**：每一次反彈的高點比前波低（頭頭低 ↘），每一次下跌的低點跌破前波低點（底底低 ↘）。
- **操作策略**：**絕不做多、空手或放空**！反彈碰均線下彎反壓即是空點，切忌在空頭趨勢中盲目猜底搶反彈！

#### ⏸️ 三、盤整走勢：【高低未同向突破】
- **特徵**：股價在箱型或三角形區間內震盪整理，高點不過高、低點不破低。
- **操作策略**：**觀望不躁進**！將標的納入【等突破】鎖股池，等待帶量長紅突破箱頂時再第一時間進場！"""

    # 尾盤 12:40 - 13:30 一點鐘心法
    if ("一點鐘" in q) or ("12:40" in q) or ("1:00" in q) or ("13:30" in q) or ("尾盤" in q and ("進場" in q or "策略" in q or "時間" in q)):
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：為什麼選在 12:40 - 13:30 尾盤一點鐘進場？】**

#### 💡 助教核心解答：
1. **避開早盤主力假動作與當沖沖銷**：
   - 09:00~10:30 早盤震盪劇烈，經常有主力拉高出貨留長上影線、或假突破誘多。
2. **尾盤方向定調，騙線機率最低**：
   - 到了 12:40~13:30，當天的成交量與收盤價已大致底定，此時確認收實體紅 K 站上 5MA，代表今日多方主力實質勝出，次日延續上攻慣性機率最高！
3. **只承擔當晚非交易時間的風險**：
   - 尾盤買進後，當天立刻鎖定進場成本，隔天開高即可享受獲利，兼具高防守性與高爆發力！"""

    # 短線 3 至 5 天波段價差
    if ("3至5天" in q) or ("3~5天" in q) or ("3-5天" in q) or ("波段價差" in q) or ("短線波段" in q):
        return """### 🧑‍🏫 【技術分析實戰助教 · 課程觀念精闢解答】
> 🎯 **【核心疑難：短線 3 至 5 天波段價差操作與出場 SOP】**

短線 3 至 5 天波段價差是資金週轉率最高、最穩健的實戰打法：

---
#### 🎯 實戰操作四部曲：
1. **進場時機**：12:40 - 13:30 尾盤確認轉折紅 K 站上 5MA 進場。
2. **防守紀律**：以當日進場紅 K 的最低點或 5MA 為防守線，跌破果斷停損，將風險控制在 3% 以內。
3. **持股奔跑**：只要每日收盤維持在 5MA 之上且 5MA 持續上揚，持股續抱 3 至 5 天。
4. **停利出場訊號（符合任一即分批停利）**：
   - 短線獲利達 **5% ~ 8%** 或碰觸前波高點壓力。
   - 出現**跌破 5MA** 或**高檔爆量留長黑K**。"""

    return ""

def answer_general_ta_question(query: str) -> str:
    """
    純觀念或未指定個股的技術分析問題指引
    """
    q = query.strip()
    return f"""### 🧑‍🏫 【技術分析實戰助教 · 觀念指引】
針對您請教的實戰問題：「**{q}**」：

1. **核心技術面把關法則**：
   - **確認大趨勢（六字訣）**：做多先看「頭頭高、底底高」，多頭拉回測線有守才是高勝率買點。
   - **觀察均線（5MA 操盤線）**：買進必須站在 5MA 之上且 5MA 翻揚助漲；跌破 5MA 果斷退場。
   - **量價結構**：攻擊時放量（> 20MA 均量 1.5 倍），拉回整理時量縮。
   - **風控紀律**：跌破 5MA 或虧損達 5% 立即無條件停損保全本金。

💡 **助教貼心提示**：
如果您想請助教診斷**具體某檔股票**（例如想知道目前能不能買、支撐壓力在哪裡），請在問題中附上**股票代號或名稱**（例如：「*請問 2330 目前適合進場嗎？*」或「*請問 2851 在 8/26 為什麼不適合買？*」），助教將立即為您重現該股票的詳細技術面診斷與應對劇本！"""

def diagnose_stock_deeply(code: str, query: str = "", as_of_date: str = None):
    """
    深度診斷股票技術面，支援「歷史覆盤時光機」切片
    """
    df_raw, info = fetch_stock_kline(code, period="1y")
    if df_raw.empty or "error" in info:
        return None

    is_replay = False
    target_date_str = as_of_date if as_of_date else extract_date_from_query(query, df_raw)

    if target_date_str:
        target_ts = pd.to_datetime(target_date_str)
        sliced = df_raw[df_raw['Date'] <= target_ts].copy().reset_index(drop=True)
        if not sliced.empty:
            df = sliced
            is_replay = True
        else:
            df = df_raw
    else:
        df = df_raw

    if len(df) < 5:
        return None

    points, lines, highest_peak, lowest_trough = calculate_turning_points(df, ma_period=5)
    trend = analyze_trend(df, points)
    signals_dict, signals_list = detect_signals(df, trend)

    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    c = round(float(last['Close']), 2)
    o = round(float(last['Open']), 2)
    h = round(float(last['High']), 2)
    l = round(float(last['Low']), 2)
    v = float(last['Volume'])
    v_ma20 = float(last['Vol_MA20']) if not np.isnan(last['Vol_MA20']) else v

    sma5 = round(float(last['SMA_5']), 2)
    sma20 = round(float(last['SMA_20']), 2) if not np.isnan(last['SMA_20']) else sma5
    sma60 = round(float(last.get('SMA_60', sma20)), 2)

    # 1. 深度排查：過去 30 天是否有高檔爆量長黑K (主力出貨/套牢賣壓)
    heavy_black_ks = []
    sub30 = df.iloc[-30:] if len(df) >= 30 else df
    for _, r in sub30.iterrows():
        vol = r['Volume']
        vma = r.get('Vol_MA20', 0)
        is_black = (r['Close'] < r['Open']) or ((r['High'] - max(r['Open'], r['Close'])) > (r['High'] - r['Low']) * 0.4)
        if vma > 0 and vol >= vma * 1.6 and is_black:
            ratio = round(vol / vma, 1)
            heavy_black_ks.append({
                "date": r['Date'].strftime('%m/%d'),
                "full_date": r['Date'].strftime('%Y-%m-%d'),
                "high": round(float(r['High']), 2),
                "close": round(float(r['Close']), 2),
                "ratio": ratio
            })

    # 2. 檢測連漲天數 (是否追高)
    up_days = 0
    for k in range(len(df) - 1, max(0, len(df) - 6), -1):
        if df.iloc[k]['Close'] > df.iloc[k - 1]['Close']:
            up_days += 1
        else:
            break

    # 3. 距離前高壓力之獲利空間
    res = trend.get('resistance')
    sup = trend.get('support')
    space_to_res = ((res - c) / c * 100) if (res and res > c) else 0

    # 4. 型態優勢判定
    is_bull = trend.get('higher_highs', False) and trend.get('higher_lows', False)
    is_stand_5ma = c >= sma5
    is_red = c >= o
    is_break_yesterday = (c > float(prev['High']))

    recent_range_max = df.iloc[-8:-1]['High'].max() if len(df) >= 8 else c
    is_range_breakout = c >= recent_range_max * 0.995

    pros = []
    cons = []

    if is_bull:
        pros.append("多頭架構確認（頭頭高 ↗、底底高 ↗）")
    elif trend.get('higher_highs', False):
        pros.append("目前為頭頭高（多頭初升或反彈架構）")

    if is_stand_5ma and is_red:
        pros.append("當日收紅 K 站上 5MA 操盤線，符合短線進場觸發要件")

    if is_range_breakout:
        pros.append("屬於 K 線橫盤整理後的向上突破位置")

    if signals_dict.get('pullback_buy', False) or (is_stand_5ma and l <= sma5 * 1.02 and c > o):
        pros.append("符合『回後買上漲』型態位置（拉回測試均線有守出轉折紅 K）")

    # 檢查當日是否本身就是爆量黑K
    is_today_heavy_black = False
    if v_ma20 > 0 and v >= v_ma20 * 1.6 and (c < o or (h - max(o, c)) > (h - l) * 0.4):
        is_today_heavy_black = True
        cons.append(f"當日出現極端爆量長黑 K（成交量為 20 均量 {round(v/v_ma20, 1)} 倍，高點 {h:.2f} 元），主力高檔出貨套牢賣壓沉重！")

    # 檢查前方未化解的爆量黑K
    unresolved_black_ks = [b for b in heavy_black_ks if b['high'] >= c and b['full_date'] != last['Date'].strftime('%Y-%m-%d')]
    if unresolved_black_ks:
        for bk in unresolved_black_ks[-2:]:
            cons.append(f"前方 {bk['date']} 出現極端爆量黑 K（成交量為 20 均量 {bk['ratio']} 倍，高點 {bk['high']} 元），上方存在巨大套牢賣壓")

    if up_days >= 3:
        cons.append(f"股價截至當日已連續上漲 {up_days} 天，短線偏離均線，此時買進屬於追高，容易遇到短線回檔")

    if space_to_res > 0 and space_to_res < 3.0:
        cons.append(f"距離上方前波高點壓力 ({res:.2f} 元) 空間僅剩 {space_to_res:.1f}%，上方肉少骨頭多，風險報酬比不划算")

    if sma20 < sma60 and c < sma60:
        cons.append("季線 (60MA) 仍位於上方呈下彎壓制，屬於中長線反彈格局而非主升段")

    # 最終決策定調
    if is_today_heavy_black:
        decision = "🔴【高檔爆量長黑K，主力出貨警訊，嚴禁買進】"
        advice_summary = "當日爆出巨量長黑，高檔套牢賣壓極度沉重，此為主力出貨典型警訊，嚴禁在此進場摸底，持股者應依紀律嚴格執行防守停損！"
    elif cons:
        if pros:
            decision = "🟡【符合進場型態與位置，但「不適合現在進場」】"
            advice_summary = "是多頭確認與進場位置，也是 K 線橫盤突破，雖然符合進場條件；但因前方存在重大賣壓瑕疵，此時進場勝率不高，極易碰壁拉回！"
        else:
            decision = "🔴【不符合進場條件，建議觀望不買】"
            advice_summary = "當前技術面型態偏弱或架構未完成，切勿逆勢摸底。"
    else:
        if pros and len(pros) >= 2:
            decision = "🟢【符合條件，適合進場】"
            advice_summary = "多頭型態完整、轉折訊號明確，且前方無重大爆量黑K阻礙，可依進場紀律執行操作。"
        else:
            decision = "⚪【條件尚不齊全，放入鎖股池等待】"
            advice_summary = "當前尚未出現明確多頭發動關鍵訊號，建議先列入鎖股池追蹤觀察。"

    return {
        "code": info['code'],
        "name": info['name'],
        "as_of_date": last['Date'].strftime('%Y-%m-%d'),
        "is_replay": is_replay,
        "close": c,
        "open": o,
        "high": h,
        "low": l,
        "volume": int(v),
        "vol_ma20": int(v_ma20),
        "vol_ratio": round(v / v_ma20, 2) if v_ma20 > 0 else 1.0,
        "change": round(c - float(prev['Close']), 2),
        "change_pct": round(((c - float(prev['Close'])) / float(prev['Close'])) * 100, 2),
        "sma5": sma5,
        "sma20": sma20,
        "sma60": sma60,
        "trend_status": trend['trend_status'],
        "support": sup,
        "resistance": res,
        "decision": decision,
        "advice_summary": advice_summary,
        "pros": pros,
        "cons": cons,
        "heavy_black_ks": unresolved_black_ks,
        "is_today_heavy_black": is_today_heavy_black,
        "up_days": up_days,
        "stage": signals_dict.get('watchlist_stage', '觀察中')
    }

def answer_question(user_query: str, stock_context: dict = None, as_of_date: str = None) -> str:
    """
    回答學員問題，具備真實助教之建議性、研判性、純觀念教學與歷史覆盤時光機
    """
    q = user_query.strip()
    
    default_code = stock_context.get('code', '2330') if stock_context else '2330'
    target_code, has_explicit_stock = extract_target_symbol(q, default_code)

    # 1. 若明確指定個股或代號（例如提問中含有 2851、台積電，或明確指稱「這檔」）：
    # 優先執行深度個股技術面診斷與歷史時光機覆盤
    if has_explicit_stock:
        diag = diagnose_stock_deeply(target_code, q, as_of_date=as_of_date)
        if diag:
            response_lines = []
            response_lines.append("### 🧑‍🏫 【技術分析實戰助教 · 實戰解答】")
            if diag['is_replay']:
                response_lines.append(f"> ⏳ **【歷史覆盤時光機 · 診斷基準日：{diag['as_of_date']}】**")
                response_lines.append(f"> *(時光倒流回溯：以 {diag['as_of_date']} 當天盤後收盤視角為您重現技術面與助教決策)*\n")

            response_lines.append(f"針對 **{diag['name']} ({diag['code']})** 在 **{diag['as_of_date']}** 的技術面與進場研判：")
            response_lines.append(f"- **當日收盤價**：{diag['close']:.2f} 元 ({'+' if diag['change']>=0 else ''}{diag['change']:.2f} 元, {'+' if diag['change_pct']>=0 else ''}{diag['change_pct']:.2f}%)")
            response_lines.append(f"- **趨勢架構**：{diag['trend_status']}")
            response_lines.append("")
            response_lines.append("#### 🎯 一、助教核心操作結論：")
            response_lines.append(f"> ### **{diag['decision']}**")
            response_lines.append(f"> **{diag['advice_summary']}**")
            response_lines.append("")

            response_lines.append("#### 🔍 二、條件符合點拆解（型態與位置）：")
            if diag['pros']:
                for p in diag['pros']:
                    response_lines.append(f"- ✅ **{p}**")
            else:
                response_lines.append("- ⚠️ 尚未具備明顯的多頭攻擊條件。")
            response_lines.append("")

            response_lines.append("#### ⚠️ 三、關鍵風險與瑕疵排查（助教叮嚀）：")
            if diag['cons']:
                for c in diag['cons']:
                    response_lines.append(f"- ❌ **{c}**")
            else:
                response_lines.append("- ✅ 前方無重大爆量黑 K 阻礙，且離前高壓力仍有發揮空間，量價結構相對乾淨。")
            response_lines.append("")

            response_lines.append("#### 📋 四、助教給您的後續應對劇本：")
            if diag['is_today_heavy_black']:
                response_lines.append("1. **【絕對觀望不可摸底】**：今日爆出巨量長黑，主力出貨確立，下方支撐均可能被摜破，萬萬不可貪便宜摸底！")
                response_lines.append("2. **【持股防守紀律】**：手中持有者應於跌破 5MA 或虧損達 5% 時嚴格執行停損，保護本金。")
            elif diag['heavy_black_ks']:
                max_bk = max(diag['heavy_black_ks'], key=lambda x: x['high'])
                response_lines.append("1. **【想進場的安全買點】**：")
                response_lines.append(f"   - **化解賣壓才買**：必須等待後續出現中長紅 K 棒，且收盤價「**正式放量站上 {max_bk['date']} 的爆量黑 K 高點 {max_bk['high']:.2f} 元**」，代表主力有決心吃掉上面的套牢籌碼，屆時進場才是安全追隨主力的起漲點！")
                response_lines.append("   - **回測鎖股**：若股價受阻拉回，不要急著去接，先放入鎖股池 **【回檔等上漲】**，等待回測 20MA（月線）量縮有守、再出轉折紅 K 站回 5MA 時再做評估。")
            elif diag['up_days'] >= 3:
                response_lines.append(f"1. **【絕不追高原則】**：目前已連漲 {diag['up_days']} 天，寧可錯過也不追高。先將其放入鎖股池 **【高檔等回檔】**，等待拉回測 5MA 或 20MA 不破前低、重新轉折向上時再行切入。")
            else:
                response_lines.append("1. **【進場操作策略】**：若符合進場條件且進場，請依實戰五步驟設定好紀律，短線目標 5%~8%，達到目標毫不猶豫分批獲利。")

            response_lines.append("2. **【防守與停損點】**：")
            sup_val = diag['support'] if diag['support'] else (diag['close'] * 0.95)
            response_lines.append(f"   - 若已有持股或強烈想進場，短線停損請嚴格設定在 **5MA 操盤線 ({diag['sma5']:.2f} 元)** 或 **波段前低支撐 ({sup_val:.2f} 元)**，一旦跌破多頭架構即告破壞，請果斷停損出場，絕不凹單套牢！")

            for topic, content in COURSE_KNOWLEDGE.items():
                if topic in q:
                    response_lines.append(f"\n---\n📘 **【附錄：課程講義標準規範——{topic}】**\n{content}")
                    break

            return "\n".join(response_lines)
        else:
            return f"抱歉，無法取得股票代號 {target_code} 的行情數據，請確認代號是否正確。"

    # 2. 若為純課程觀念理論提問（未指定個股）：優先精準回答概念
    concept_reply = answer_conceptual_question(q)
    if concept_reply:
        return concept_reply

    # 3. 通用技術分析指導
    return answer_general_ta_question(q)

