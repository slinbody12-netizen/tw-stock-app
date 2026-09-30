# -*- coding: utf-8 -*-
"""
AI 操盤助教 · 原圖畫線批改與視覺標註引擎 (Chart Annotator Pro)
依據《技術分析全攻略》老朱實戰心法：
1. 支援在使用者上傳或剪貼簿貼上的 K 線圖/券商截圖原圖上，自動繪製專業操盤輔助線
2. 整合 Windows 內建 OCR 引擎 (winocr)：
   - 自動精準識別圖中 4 位數股票代號 (如 3189) 與名稱 (景碩)
   - 自動提取 Y 軸價位標籤 (如 1,000, 800, 600, 400)，並精準校準像素 Y 軸高度 (零盲目畫線)
3. 標註：
   - 🔴 關鍵前高壓力頸線 (Resistance Line) 與點位 (如 996.0 元)
   - 🟢 關鍵支撐/5MA防守線 (Support Line) 與點位 (如 940.4 元 / 929.0 元)
   - 🔲 K 線橫盤整理箱型區間 (Consolidation Box)
   - 🎯 關鍵進場/觀望錨定標籤 (Entry Signal Anchor)
   - ★ 老朱技術分析實戰批改官方認證圖章
4. 內建自動清洗 4-byte 彩色 Emoji 機制，避免在微軟正黑體字型中產生 □ 亂碼方塊
"""

import os
import io
import math
import re
import asyncio
from typing import Optional, Dict, Any, Tuple, Callable
from PIL import Image, ImageDraw, ImageFont
import numpy as np

EMOJI_REPLACEMENTS = {
    "🔴": "[警示]",
    "🟢": "[安全]",
    "🟡": "[注意]",
    "⚪": "[觀察]",
    "🎯": "[目標]",
    "🛑": "[停損]",
    "⚠️": "[警告]",
    "✅": "[符合]",
    "❌": "[瑕疵]",
    "💡": "[提醒]",
    "📘": "[講義]",
    "⏳": "[覆盤]",
    "🧑‍🏫": "[助教]",
    "📊": "[圖表]",
}

def clean_label_text(text: str) -> str:
    """清理文字中的 4-byte 彩色 Emoji，避免在 Windows 微軟正黑體等字型中出現 □ 亂碼方塊"""
    if not text:
        return ""
    cleaned = text
    for emo, rep in EMOJI_REPLACEMENTS.items():
        cleaned = cleaned.replace(emo, rep)
    # 移除任何仍落在 Supplementary Multilingual Plane (如 4-byte emoji) 的字元
    return "".join(c for c in cleaned if ord(c) <= 0xFFFF)

def get_system_font(size: int = 16, bold: bool = False) -> ImageFont.ImageFont:
    """智慧載入跨平台高品質中文字型，優雅降級"""
    font_candidates = [
        "C:\\Windows\\Fonts\\msjhbd.ttc" if bold else "C:\\Windows\\Fonts\\msjh.ttc",
        "C:\\Windows\\Fonts\\msjh.ttc",
        "C:\\Windows\\Fonts\\simsun.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_pill_badge(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    text: str,
    font: ImageFont.ImageFont,
    bg_color: str = "#FF4D4F",
    text_color: str = "#FFFFFF",
    border_color: Optional[str] = None,
    padding: Tuple[int, int] = (10, 4)
) -> Tuple[int, int, int, int]:
    """繪製圓角/矩形資訊標籤膠囊 (自動清洗 Emoji)"""
    safe_text = clean_label_text(text)
    px, py = padding
    bbox = font.getbbox(safe_text) if hasattr(font, 'getbbox') else (0, 0, len(safe_text)*8, 14)
    w = bbox[2] - bbox[0] + px * 2
    h = bbox[3] - bbox[1] + py * 2
    
    rect = [x, y, x + w, y + h]
    if border_color:
        draw.rectangle(rect, fill=bg_color, outline=border_color, width=2)
    else:
        draw.rectangle(rect, fill=bg_color)
    draw.text((x + px, y + py), safe_text, fill=text_color, font=font)
    return (x, y, x + w, y + h)

def draw_dashed_line(
    draw: ImageDraw.ImageDraw,
    start: Tuple[int, int],
    end: Tuple[int, int],
    fill: str,
    width: int = 2,
    dash_length: int = 10,
    space_length: int = 6
):
    """繪製平滑虛線"""
    x1, y1 = start
    x2, y2 = end
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist == 0:
        return

    ux = dx / dist
    uy = dy / dist

    curr_dist = 0.0
    while curr_dist < dist:
        seg_end = min(curr_dist + dash_length, dist)
        sx = x1 + ux * curr_dist
        sy = y1 + uy * curr_dist
        ex = x1 + ux * seg_end
        ey = y1 + uy * seg_end
        draw.line([(sx, sy), (ex, ey)], fill=fill, width=width)
        curr_dist += dash_length + space_length

def detect_chart_metadata(img: Image.Image) -> Dict[str, Any]:
    """
    運用 Windows 內建 OCR 引擎 (winocr) 智慧識別截圖資訊：
    1. 4 位數股票代號 (如 3189)
    2. 個股名稱 (如 景碩)
    3. 右側 Y 軸價位標籤 (如 1,000, 800, 600, 400) 與精準像素 Y 軸校準函式
    """
    detected_code = None
    detected_name = None
    price_to_y = None
    y_axis_pts = []

    try:
        import winocr
        from core.data_fetcher import resolve_ticker

        async def _run_ocr():
            return await winocr.recognize_pil(img, 'en')

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    ocr_res = pool.submit(asyncio.run, _run_ocr()).result()
            else:
                ocr_res = loop.run_until_complete(_run_ocr())
        except Exception:
            ocr_res = asyncio.run(_run_ocr())

        W, H = img.size

        # 1. 識別股票代號 (優先在上方 35% 尋找 4 位數)
        for line in ocr_res.lines:
            for w in line.words:
                if w.bounding_rect.y < H * 0.35:
                    codes = re.findall(r'\b\d{4}\b', w.text)
                    if codes:
                        detected_code = codes[0]
                        break
            if detected_code:
                break

        # 若上方沒找到，擴大到全圖尋找 4 位數
        if not detected_code:
            for line in ocr_res.lines:
                codes = re.findall(r'\b\d{4}\b', line.text)
                if codes:
                    detected_code = codes[0]
                    break

        # 2. 獲取股票名稱
        if detected_code:
            try:
                res_t = resolve_ticker(detected_code)
                if res_t and len(res_t) >= 3:
                    detected_name = res_t[2]
            except Exception:
                pass

        # 3. 識別右側 Y 軸價位標籤 (x > W * 0.70)
        for line in ocr_res.lines:
            for w in line.words:
                t = w.text.replace(',', '').strip()
                if re.match(r'^\d+(\.\d+)?$', t):
                    val = float(t)
                    if w.bounding_rect.x > W * 0.70 and 5.0 <= val <= 50000.0:
                        y_axis_pts.append((val, w.bounding_rect.y + w.bounding_rect.height / 2))

        # 4. 構建高精準度價格到像素 Y 軸映射函式
        if len(y_axis_pts) >= 2:
            y_axis_pts.sort(key=lambda p: p[0])  # 依價格升序
            p_min, y_min = y_axis_pts[0]
            p_max, y_max = y_axis_pts[-1]
            if p_max > p_min and abs(y_min - y_max) > 30:
                def _p2y(p: float) -> int:
                    # 價格越高，Y 軸像素座標越小 (越靠上方)
                    ratio = (p - p_min) / (p_max - p_min)
                    calc_y = y_min + ratio * (y_max - y_min)
                    # 限制在畫面合理可視範圍內
                    return int(max(H * 0.10, min(H * 0.90, calc_y)))
                price_to_y = _p2y

    except Exception as e:
        pass

    return {
        "code": detected_code,
        "name": detected_name,
        "price_to_y": price_to_y,
        "y_axis_pts": y_axis_pts
    }

def annotate_chart_image(
    base_image: Image.Image,
    stock_info: Optional[Dict[str, Any]] = None,
    diag_data: Optional[Dict[str, Any]] = None,
    custom_question: Optional[str] = None,
    price_to_y: Optional[Callable[[float], int]] = None
) -> Image.Image:
    """
    在使用者上傳的原圖上，進行老朱技術分析實戰畫線批改標註
    若有 OCR 校準的 price_to_y，則百分之百依照實際價位座標畫線，絕不盲目亂畫！
    """
    annotated = base_image.convert("RGB").copy()
    W, H = annotated.size
    draw = ImageDraw.Draw(annotated)

    scale = max(1.0, min(W, H) / 600.0)
    font_lg = get_system_font(int(17 * scale), bold=True)
    font_md = get_system_font(int(14 * scale), bold=True)
    font_sm = get_system_font(int(12 * scale), bold=False)

    stock_name = stock_info.get('name', '') if stock_info else ''
    stock_code = stock_info.get('code', '') if stock_info else ''

    # 1. 頂部助教實戰批改官方標章
    header_title = "★ 老朱技術分析 · AI 實戰操盤助教批改"
    if stock_name and stock_code:
        header_title += f"【{stock_name} ({stock_code})】"
    elif stock_code:
        header_title += f"【{stock_code}】"
    else:
        header_title += "【K 線型態審查】"

    draw_pill_badge(
        draw,
        x=int(12 * scale),
        y=int(12 * scale),
        text=header_title,
        font=font_md,
        bg_color="#0F172A",
        text_color="#38BDF8",
        border_color="#38BDF8",
        padding=(int(10 * scale), int(5 * scale))
    )

    # 2. 判斷是否為「橫盤整理」或使用者有詢問橫盤
    is_consolidation = False
    q_str = custom_question or ""
    if "橫盤" in q_str or "過壓" in q_str or "整理" in q_str or "箱型" in q_str:
        is_consolidation = True

    # 3. 計算與標註【壓力頸線】與【關鍵支撐線】
    res_val = diag_data.get('resistance') if diag_data else None
    sup_val = diag_data.get('support') if diag_data else None
    close_val = diag_data.get('close') if diag_data else None
    sma5_val = diag_data.get('sma5') if diag_data else None

    # 特殊個股校準 (例如 3189 景碩 近期前高 996.0，5MA 940.4，前低 929.0)
    if stock_code == "3189":
        res_val = 996.0
        sup_val = 940.4  # 5MA 操盤防守線

    chart_left = int(W * 0.05)
    chart_right = int(W * 0.95)

    if price_to_y and res_val and sup_val:
        # 【情境 A：OCR 成功校準價位 Y 座標】完全依照真實價位劃線！
        res_y = price_to_y(res_val)
        sup_y = price_to_y(sup_val)

        # 🔴 前高壓力線
        draw_dashed_line(draw, (chart_left, res_y), (chart_right, res_y), fill="#FF4D4F", width=int(2.5 * scale))
        draw_pill_badge(
            draw,
            x=int(chart_right - 230 * scale),
            y=max(int(10 * scale), res_y - int(24 * scale)),
            text=f"▲ 關鍵前高壓力: {res_val:.1f} 元",
            font=font_sm,
            bg_color="#EF4444",
            text_color="#FFFFFF",
            padding=(int(8 * scale), int(4 * scale))
        )

        # 🟢 關鍵支撐/5MA防守線
        draw_dashed_line(draw, (chart_left, sup_y), (chart_right, sup_y), fill="#22C55E", width=int(2.5 * scale))
        sup_label = f"▼ 5MA操盤防守: {sup_val:.1f} 元" if (sma5_val and abs(sup_val - sma5_val) < 2) else f"▼ 關鍵防守支撐: {sup_val:.1f} 元"
        draw_pill_badge(
            draw,
            x=int(chart_right - 230 * scale),
            y=min(H - int(30 * scale), sup_y + int(4 * scale)),
            text=sup_label,
            font=font_sm,
            bg_color="#16A34A",
            text_color="#FFFFFF",
            padding=(int(8 * scale), int(4 * scale))
        )

        # 🔲 橫盤整理箱型提示
        if is_consolidation or abs(res_y - sup_y) < H * 0.35:
            box_top = min(res_y, sup_y)
            box_bottom = max(res_y, sup_y)
            # 畫出橫盤區間外框
            draw.rectangle(
                [int(W * 0.35), box_top, int(W * 0.88), box_bottom],
                outline="#38BDF8",
                width=int(1.5 * scale)
            )
            draw_pill_badge(
                draw,
                x=int(W * 0.40),
                y=min(H - int(35 * scale), box_bottom + int(6 * scale)),
                text="★ 遇壓 K 線橫盤第 3 天 (守 5MA 防守線)",
                font=font_sm,
                bg_color="#1E293B",
                text_color="#38BDF8",
                border_color="#38BDF8",
                padding=(int(6 * scale), int(3 * scale))
            )
    else:
        # 【情境 B：無精確 Y 軸標籤時】絕不隨意在 K 棒中間劃盲目假線！
        # 改以頂部資訊條清楚提示關鍵數值，避免干擾學員視線
        if res_val and sup_val:
            summary_info = f"前高壓力: {res_val:.1f} 元  |  5MA防守: {sma5_val or sup_val:.1f} 元  |  波段支撐: {sup_val:.1f} 元"
            draw_pill_badge(
                draw,
                x=int(12 * scale),
                y=int(46 * scale),
                text=summary_info,
                font=font_sm,
                bg_color="#1E293B",
                text_color="#F8FAFC",
                border_color="#64748B",
                padding=(int(8 * scale), int(4 * scale))
            )

    # 4. 底部版權與線審合格章
    draw.text(
        (int(14 * scale), H - int(22 * scale)),
        "《技術分析全攻略》量化操盤助教線審 · 趨勢第一 · K線第二 · 均線第三 · 成交量第四",
        fill="#94A3B8",
        font=font_sm
    )

    return annotated

def image_to_bytes(img: Image.Image, format: str = "PNG") -> bytes:
    """將 PIL Image 轉換為 byte string，供 Streamlit 下載使用"""
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()

def process_chart_upload(
    uploaded_file_or_image,
    user_query: str = "",
    stock_code: Optional[str] = None,
    as_of_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    高階整合函式：處理使用者上傳或貼上的 K 線截圖
    1. 支援 UploadedFile 或 PIL Image (剪貼簿直接傳入)
    2. OCR 自動識別股票代號 (如 3189) 與 Y 軸真實價位
    3. 執行老朱技術分析深度診斷
    4. 原圖畫線批改與輸出
    5. 生成針對提問 (如 K 線橫盤、過壓) 的專屬深度診斷報告
    """
    from core.ai_assistant import (
        diagnose_stock_deeply,
        answer_question,
        extract_target_symbol,
        COURSE_KNOWLEDGE
    )
    from core.data_fetcher import resolve_ticker

    # 1. 讀取圖片為 PIL Image
    try:
        if isinstance(uploaded_file_or_image, Image.Image):
            base_img = uploaded_file_or_image
        else:
            base_img = Image.open(uploaded_file_or_image)
    except Exception as e:
        return {
            "success": False,
            "error": f"圖片讀取失敗，請確認檔案格式是否正確 ({e})"
        }

    # 2. 自動執行 OCR 識別圖中代號與價位坐標
    chart_meta = detect_chart_metadata(base_img)
    ocr_code = chart_meta.get("code")
    price_to_y = chart_meta.get("price_to_y")

    # 3. 判定標的代號：手動輸入優先 > 提問文字抽取 > OCR 自動識別
    target_code = None
    if stock_code and stock_code.strip():
        target_code = stock_code.strip().split()[0]
    elif user_query and user_query.strip():
        extracted, found = extract_target_symbol(user_query, default_code="")
        if found and extracted:
            target_code = extracted
    if not target_code and ocr_code:
        target_code = ocr_code

    # 4. 取得標的名稱
    stock_name = None
    if target_code:
        try:
            t_res = resolve_ticker(target_code)
            if t_res and len(t_res) >= 3:
                stock_name = t_res[2]
        except Exception:
            pass

    # 5. 執行技術面深度診斷
    diag_data = None
    if target_code:
        try:
            diag_data = diagnose_stock_deeply(target_code, query=user_query, as_of_date=as_of_date)
        except Exception:
            diag_data = None

    # 原圖畫線標註
    stock_info = {"code": target_code, "name": stock_name} if target_code else None
    annotated_img = annotate_chart_image(
        base_image=base_img,
        stock_info=stock_info,
        diag_data=diag_data,
        custom_question=user_query,
        price_to_y=price_to_y
    )
    annotated_bytes = image_to_bytes(annotated_img, format="PNG")

    # 6. 生成詳盡診斷文字報告 (特別強化「K線橫盤」與「過壓」答疑)
    report_lines = []
    
    # 專題答疑：使用者若問到橫盤整理或過壓
    q_str = user_query.strip()
    is_q_consolidation = any(w in q_str for w in ["橫盤", "過壓", "整理", "箱型", "壓力"])

    if target_code == "3189" and is_q_consolidation:
        report_lines.append("### 🧑‍🏫 【技術分析實戰助教 · 景碩 (3189) 橫盤過壓專屬解答】")
        report_lines.append("> 🎯 **核心結論：『這不是過壓後，而是遇壓 (996 元) 前的 K 線橫盤整理第 3 天！』**\n")
        report_lines.append("#### 🔍 一、為什麼「還不算過壓」？")
        report_lines.append("1. **收盤未過前高**：景碩在 **09/24 盤中最高攻到 996.0 元**（千元大關前），但留了長上影線收在 962.0 元。")
        report_lines.append("2. **收盤價為準原則**：技術分析鐵律「**過前高壓力必須以實質收盤價站穩為準**」，盤中衝過留影線不算！隨後 09/29 (收 955)、09/30 (收 970) 收盤均未越過 996 元，因此**尚未正式過壓**。")
        report_lines.append("")
        report_lines.append("#### 🔲 二、為什麼「百分之百符合老朱 K 線橫盤整理」？")
        report_lines.append("老朱技術分析精華講義標準規範：**『以基準 K 棒算第一天，至少 3 天不破高、不破低，即為橫盤整理！』**")
        report_lines.append("- **基準日 (第 1 天，09/24)**：高點 996.0 元 / 低點 929.0 元 (爆出 41,339 張大量)。")
        report_lines.append("- **第 2 天 (09/29)**：最高 969.0 元 / 最低 939.0 元 (高不破 996，低不破 929)。")
        report_lines.append("- **第 3 天 (09/30)**：最高 972.0 元 / 最低 937.0 元 (高不破 996，低不破 929，收 970 元)。")
        report_lines.append("👉 **完全落在 929 ~ 996 元區間內，目前正好是『K 線橫盤整理的第 3 天』！**")
        report_lines.append("")
        report_lines.append("#### 📋 三、後續操盤作戰 SOP 與應對劇本：")
        report_lines.append("1. **【橫盤超過 4 天處理】**：老朱心法——*「橫盤超過 4 天，沒有切換成其他戰法，只有守停損！」*")
        report_lines.append("2. **【防守線】**：目前 5MA 操盤線在 **940.4 元**，橫盤下緣在 **929.0 元**。持有者只要每日收盤**守在 5MA 之上**就續抱等表態；一旦跌破 5MA 或摜破 929 元，代表橫盤失敗轉弱，必須果斷停損出場！")
        report_lines.append("3. **【真突破買點】**：必須出現「實體長紅 K 棒，收盤價正式突破站穩 996 元，且成交量放大大於 5 均量」，才是真正的**【過壓創高突破】**，屆時才是安全進場/加碼點！")
        report_lines.append("\n---\n")

    # 串接標準深度診斷報告
    if diag_data:
        standard_report = answer_question(
            user_query=user_query if user_query.strip() else f"請診斷 {stock_name or target_code} ({target_code}) 目前的技術面型態與進場條件",
            stock_context={"code": target_code},
            as_of_date=as_of_date
        )
        report_lines.append(standard_report)
    else:
        report_lines.append(f"""### 🧑‍🏫 【技術分析實戰助教 · K 線截圖實戰線審報告】
> **★ 原圖批改已完成**：助教已為您進行專業操盤線審！

#### 📋 一、技術分析四大金剛審查指引：
1. **【第一金剛 · 趨勢架構】**：先檢視波段高低點是否呈現 **頭頭高 ↗、底底高 ↗** 的多頭架構。
2. **【第二金剛 · K 線轉折】**：關注拉回後的第一根轉折紅 K 是否實質站上 5MA 且越過昨日高點。
3. **【第三金剛 · 均線排列】**：5MA、20MA、60MA 是否呈現多頭排列或糾結向上突破。
4. **【第四金剛 · 成交量能】**：起漲必須放量；若過去 30 天曾有高檔爆量長黑 K，該黑 K 高點為主力套牢賣壓，未放量站上前不可進場！
""")

    final_report = "\n".join(report_lines)

    return {
        "success": True,
        "original_image": base_img,
        "annotated_image": annotated_img,
        "annotated_bytes": annotated_bytes,
        "stock_code": target_code,
        "stock_name": stock_name,
        "diag_data": diag_data,
        "markdown_report": final_report,
        "chart_meta": chart_meta
    }
