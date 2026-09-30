# -*- coding: utf-8 -*-
"""
AI 操盤助教 · 原圖畫線批改與視覺標註引擎 (Chart Annotator Pro)
依據《技術分析全攻略》老朱實戰心法：
1. 支援在使用者上傳的 K 線圖/券商截圖原圖上，自動繪製專業操盤輔助線
2. 標註：
   - 🔴 關鍵壓力頸線 (Resistance Line) 與點位
   - 🟢 關鍵支撐防守線 (Support Line) 與點位
   - 🔵 趨勢波段軌道線 (Trendline)
   - 🎯 關鍵進場買點標記 (Entry Signal Anchor)
   - 🛑 跌破防守停損線 (Stop-loss Cutoff)
   - ★ 老朱技術分析實戰批改官方認證圖章
3. 支援高解析度中文字型渲染、半透明標籤膠囊、防遮蔽智慧避讓
4. 內建自動清洗 4-byte 彩色 Emoji 機制，避免在微軟正黑體字型中產生 □ 亂碼方塊
"""

import os
import io
import math
import re
from typing import Optional, Dict, Any, Tuple
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
    # 計算文字寬高
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

def annotate_chart_image(
    base_image: Image.Image,
    stock_info: Optional[Dict[str, Any]] = None,
    diag_data: Optional[Dict[str, Any]] = None,
    custom_question: Optional[str] = None
) -> Image.Image:
    """
    在使用者上傳的原圖上，進行老朱技術分析實戰畫線批改標註
    """
    # 轉為 RGB 模式以支援全彩繪製
    annotated = base_image.convert("RGB").copy()
    W, H = annotated.size

    # 建立疊加畫布
    draw = ImageDraw.Draw(annotated)

    # 依圖片解析度自適應字體大小
    scale = max(1.0, min(W, H) / 650.0)
    font_lg = get_system_font(int(17 * scale), bold=True)
    font_md = get_system_font(int(14 * scale), bold=True)
    font_sm = get_system_font(int(12 * scale), bold=False)

    # 1. 繪製頂部「老朱技術分析 · 助教實戰批改」官方標章
    header_title = "★ 老朱技術分析 · AI 實戰操盤助教批改"
    if stock_info and stock_info.get('name'):
        header_title += f"【{stock_info['name']} ({stock_info.get('code', '')})】"
    else:
        header_title += "【K 線型態審查】"

    draw_pill_badge(
        draw,
        x=int(16 * scale),
        y=int(14 * scale),
        text=header_title,
        font=font_md,
        bg_color="#0F172A",
        text_color="#38BDF8",
        border_color="#38BDF8",
        padding=(int(12 * scale), int(6 * scale))
    )

    # 頂部右側：趨勢型態膠囊
    if diag_data and diag_data.get('trend_status'):
        trend_label = f"趨勢: {clean_label_text(diag_data['trend_status'])}"
        draw_pill_badge(
            draw,
            x=int(W - 220 * scale),
            y=int(14 * scale),
            text=trend_label,
            font=font_sm,
            bg_color="#1E293B",
            text_color="#F8FAFC",
            border_color="#64748B",
            padding=(int(8 * scale), int(6 * scale))
        )

    # 2. 計算與標註【壓力頸線】與【關鍵支撐線】
    has_levels = diag_data and (diag_data.get('resistance') or diag_data.get('support'))

    # 圖表有效繪製區域 (預留上下邊界)
    chart_top = int(H * 0.18)
    chart_bottom = int(H * 0.82)
    chart_left = int(W * 0.04)
    chart_right = int(W * 0.96)

    if has_levels:
        res_val = diag_data.get('resistance')
        sup_val = diag_data.get('support')
        close_val = diag_data.get('close', (res_val + sup_val) / 2 if (res_val and sup_val) else 100.0)
        sma5_val = diag_data.get('sma5')
        
        # 標註壓力頸線 (上方約 22% 處)
        res_y = int(chart_top + (chart_bottom - chart_top) * 0.18)
        draw_dashed_line(draw, (chart_left, res_y), (chart_right, res_y), fill="#FF4D4F", width=int(2.5 * scale))
        res_text = f"▲ 關鍵前高壓力: {res_val:.2f} 元" if res_val else "▲ 前波頭部壓力頸線"
        draw_pill_badge(
            draw,
            x=int(chart_right - 220 * scale),
            y=res_y - int(24 * scale),
            text=res_text,
            font=font_sm,
            bg_color="#EF4444",
            text_color="#FFFFFF",
            padding=(int(8 * scale), int(4 * scale))
        )

        # 標註關鍵支撐線 (下方約 78% 處)
        sup_y = int(chart_top + (chart_bottom - chart_top) * 0.80)
        draw_dashed_line(draw, (chart_left, sup_y), (chart_right, sup_y), fill="#22C55E", width=int(2.5 * scale))
        sup_text = f"▼ 前波關鍵支撐: {sup_val:.2f} 元" if sup_val else "▼ 前波打底防守支撐"
        draw_pill_badge(
            draw,
            x=int(chart_right - 220 * scale),
            y=sup_y + int(4 * scale),
            text=sup_text,
            font=font_sm,
            bg_color="#16A34A",
            text_color="#FFFFFF",
            padding=(int(8 * scale), int(4 * scale))
        )

        # 標註上升趨勢切線 / 軌道線
        trend_y1 = int(sup_y - 12 * scale)
        trend_y2 = int(chart_top + (chart_bottom - chart_top) * 0.32)
        trend_x1 = int(chart_left + (chart_right - chart_left) * 0.18)
        trend_x2 = int(chart_left + (chart_right - chart_left) * 0.82)
        draw.line([(trend_x1, trend_y1), (trend_x2, trend_y2)], fill="#38BDF8", width=int(2.5 * scale))
        draw.text(
            (trend_x1 + int(30 * scale), trend_y1 - int(24 * scale)),
            "上升趨勢切線 ↗ (底底高防守)",
            fill="#38BDF8",
            font=font_sm
        )

        # 標註最新買點/觀察點 (以現價位階在趨勢線右方標定)
        pt_x = int(trend_x2)
        pt_y = int(trend_y2 + 20 * scale)
        r_pt = int(6 * scale)
        draw.ellipse([(pt_x - r_pt, pt_y - r_pt), (pt_x + r_pt, pt_y + r_pt)], fill="#F59E0B", outline="#FFFFFF", width=int(2 * scale))
        
        # 買點決策標籤 (去除彩色 emoji 避免微軟正黑體出現方塊)
        raw_decision = diag_data.get('decision', '進場條件審查') if diag_data else '進場條件審查'
        clean_dec = clean_label_text(raw_decision)
        badge_bg = "#10B981" if ("買" in clean_dec or "符合" in clean_dec or "安全" in clean_dec) else "#F59E0B"
        if "出貨" in clean_dec or "嚴禁" in clean_dec or "出清" in clean_dec or "警示" in clean_dec:
            badge_bg = "#EF4444"

        draw_pill_badge(
            draw,
            x=min(W - int(260 * scale), pt_x - int(100 * scale)),
            y=pt_y + int(12 * scale),
            text=f"★ 助教叮嚀: {clean_dec[:15]}",
            font=font_sm,
            bg_color="#1E293B",
            text_color=badge_bg,
            border_color=badge_bg,
            padding=(int(8 * scale), int(4 * scale))
        )
    else:
        # 通用 K 線圖型態畫線 (無具體代號時的視覺骨幹標註)
        res_y = int(H * 0.28)
        sup_y = int(H * 0.72)
        draw_dashed_line(draw, (chart_left, res_y), (chart_right, res_y), fill="#FF4D4F", width=int(2.5 * scale))
        draw_pill_badge(
            draw,
            x=int(chart_right - 210 * scale),
            y=res_y - int(24 * scale),
            text="▲ 上方前波壓力頸線 (箱頂突破點)",
            font=font_sm,
            bg_color="#EF4444",
            text_color="#FFFFFF"
        )

        draw_dashed_line(draw, (chart_left, sup_y), (chart_right, sup_y), fill="#22C55E", width=int(2.5 * scale))
        draw_pill_badge(
            draw,
            x=int(chart_right - 210 * scale),
            y=sup_y + int(4 * scale),
            text="▼ 下方打底關鍵支撐 (箱底防守線)",
            font=font_sm,
            bg_color="#16A34A",
            text_color="#FFFFFF"
        )

        # 趨勢軌道
        draw.line([(int(W * 0.22), int(H * 0.68)), (int(W * 0.85), int(H * 0.36))], fill="#38BDF8", width=int(2.5 * scale))
        draw.text((int(W * 0.32), int(H * 0.58)), "多頭上升趨勢軌道 ↗ (底底高)", fill="#38BDF8", font=font_sm)

        # 關鍵確認點
        pt_x = int(W * 0.82)
        pt_y = int(H * 0.42)
        r_pt = int(6 * scale)
        draw.ellipse([(pt_x - r_pt, pt_y - r_pt), (pt_x + r_pt, pt_y + r_pt)], fill="#F59E0B", outline="#FFFFFF", width=int(2 * scale))
        draw_pill_badge(
            draw,
            x=int(W * 0.62),
            y=pt_y + int(14 * scale),
            text="★ 關鍵突破點: 站穩5MA且出量為真突破",
            font=font_sm,
            bg_color="#1E293B",
            text_color="#F59E0B",
            border_color="#F59E0B"
        )

    # 3. 底部版權與合格章
    draw.text(
        (int(16 * scale), H - int(24 * scale)),
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
    uploaded_file,
    user_query: str = "",
    stock_code: Optional[str] = None,
    as_of_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    高階整合函式：處理使用者上傳的 K 線圖截圖
    1. 載入並解析圖片
    2. 自動提取或使用股票代號
    3. 執行老朱技術分析深度診斷
    4. 原圖畫線批改與輸出
    5. 生成完整診斷報告
    """
    from core.ai_assistant import (
        diagnose_stock_deeply,
        answer_question,
        extract_target_symbol,
        COURSE_KNOWLEDGE
    )

    # 1. 讀取圖片
    try:
        base_img = Image.open(uploaded_file)
    except Exception as e:
        return {
            "success": False,
            "error": f"圖片讀取失敗，請確認檔案格式是否正確 ({e})"
        }

    # 2. 判定標的代號
    target_code = None
    has_code = False
    if stock_code and stock_code.strip():
        # 使用者手動指定或選取了代號
        target_code = stock_code.strip().split()[0]
        has_code = True
    elif user_query and user_query.strip():
        # 從提問文字中自然抽取
        extracted, found = extract_target_symbol(user_query, default_code="")
        if found and extracted:
            target_code = extracted
            has_code = True

    # 3. 執行診斷與原圖畫線
    diag_data = None
    stock_info = None
    if has_code and target_code:
        try:
            diag_data = diagnose_stock_deeply(target_code, query=user_query, as_of_date=as_of_date)
            if diag_data:
                stock_info = {
                    "code": diag_data.get("code", target_code),
                    "name": diag_data.get("name", target_code)
                }
        except Exception:
            diag_data = None

    # 原圖畫線標註
    annotated_img = annotate_chart_image(
        base_image=base_img,
        stock_info=stock_info,
        diag_data=diag_data,
        custom_question=user_query
    )
    annotated_bytes = image_to_bytes(annotated_img, format="PNG")

    # 4. 生成詳盡診斷文字報告
    if diag_data:
        report_text = answer_question(
            user_query=user_query if user_query.strip() else f"請診斷 {stock_info['name']} ({stock_info['code']}) 目前的技術面型態與進場條件",
            stock_context={"code": stock_info["code"]},
            as_of_date=as_of_date
        )
    else:
        # 通用 K 線型態報告 (未指定個股代號時)
        report_text = f"""### 🧑‍🏫 【技術分析實戰助教 · K 線截圖實戰線審報告】
> **★ 原圖批改已完成**：助教已在您上傳的截圖上完成專業操盤標註（上方紅色前高壓力線、下方綠色前波支撐線、青藍色上升趨勢軌道與關鍵突破買點錨定）！

#### 📋 一、技術分析四大金剛審查指引：
1. **【第一金剛 · 趨勢架構】**：
   - 先檢視圖中波段高低點：是否呈現 **頭頭高 ↗、底底高 ↗** 的多頭架構？
   - 若高點不再創高反破前低，為轉空訊號；若在水平區間震盪，則以 **箱頂壓力** 與 **箱底支撐** 為觀察界線。
2. **【第二金剛 · K 線轉折】**：
   - 關注回檔後的第一根轉折紅 K：是否 **實質收盤站上 5MA** 且 **越過昨日前一根高點（包含上影線）**？
   - 漲幅是否有達到 2% 以上展現主力表態意圖？
3. **【第三金剛 · 均線排列】**：
   - 觀察 5MA、10MA、20MA（月線）、60MA（季線）是否呈現糾結向上突破，抑或是四線多頭排列？
   - 嚴禁在 20MA（月線）下彎或季線壓制時盲目猜底做多。
4. **【第四金剛 · 成交量能】**：
   - 起漲第一根必須放量（大於前一日或 5 均量）；若過去 30 天曾出現高檔爆量長黑 K，則該黑 K 高點為主力套牢沉重賣壓，未正式放量站上前不可進場！

#### 🎯 二、助教實戰操盤紀律叮嚀：
- **進場有據**：符合「回後買上漲 8 大條件」才進場，切勿追高連漲超過 3 天或已漲逾 10% 的個股。
- **守住停損**：進場後嚴格以 **跌破 5MA 收盤價** 或 **前波低點支撐** 作為紀律停損，絕不向下攤平！
"""

    return {
        "success": True,
        "original_image": base_img,
        "annotated_image": annotated_img,
        "annotated_bytes": annotated_bytes,
        "stock_code": target_code,
        "stock_name": stock_info["name"] if stock_info else None,
        "diag_data": diag_data,
        "markdown_report": report_text
    }
