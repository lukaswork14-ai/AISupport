"""Tạo thẻ ảnh minh họa 1080x1350 (tỉ lệ 4:5 cho Facebook/Instagram/Threads) bằng Pillow, không cần API ảnh."""
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from config import DATA_DIR

W, H = 1080, 1350
FONT_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
FONT_REG = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
PALETTES = {  # (nền trên, nền dưới, màu nhấn)
    "TikTok": ((17, 17, 27), (44, 20, 60), (37, 244, 238)),
    "Amazon": ((16, 24, 40), (35, 47, 62), (255, 153, 0)),
    "Etsy": ((40, 22, 14), (86, 42, 20), (245, 130, 50)),
    "Shopify": ((10, 30, 22), (24, 64, 44), (149, 191, 71)),
    "default": ((12, 20, 40), (30, 41, 90), (99, 179, 237)),
}


def _font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _gradient(top, bottom):
    img = Image.new("RGB", (W, H), top)
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_w:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def make_card(card: dict, source: str, topic: str, name: str, handle: str = "") -> str:
    key = next((k for k in PALETTES if k.lower() in (topic or "").lower()), "default")
    top, bottom, accent = PALETTES[key]
    img = _gradient(top, bottom)
    d = ImageDraw.Draw(img)
    pad = 80
    max_w = W - 2 * pad

    # nhãn chủ đề
    tag = (card.get("tag") or topic or "TIN HOT").upper()
    f_tag = _font(FONT_BOLD, 34)
    tw = d.textlength(tag, font=f_tag)
    d.rounded_rectangle([pad, 110, pad + tw + 56, 178], radius=34, fill=accent)
    d.text((pad + 28, 122), tag, font=f_tag, fill=(15, 15, 20))

    # tiêu đề: tự giảm cỡ chữ cho vừa
    headline = card.get("headline", "")
    size = 84
    while size > 44:
        f_h = _font(FONT_BOLD, size)
        lines = _wrap(d, headline, f_h, max_w)
        if len(lines) <= 5:
            break
        size -= 6
    y = 250
    for ln in lines:
        d.text((pad, y), ln, font=f_h, fill=(255, 255, 255))
        y += int(size * 1.22)

    # vạch nhấn
    y += 30
    d.rectangle([pad, y, pad + 140, y + 10], fill=accent)
    y += 70

    # 3 ý chính
    f_b = _font(FONT_REG, 42)
    for b in card.get("bullets", [])[:3]:
        d.ellipse([pad, y + 14, pad + 22, y + 36], fill=accent)
        for ln in _wrap(d, b, f_b, max_w - 60):
            d.text((pad + 56, y), ln, font=f_b, fill=(228, 232, 240))
            y += 56
        y += 28

    # chân trang
    f_s = _font(FONT_REG, 30)
    d.text((pad, H - 120), f"Nguồn: {source}", font=f_s, fill=(160, 170, 190))
    if handle:
        hw = d.textlength(handle, font=_font(FONT_BOLD, 32))
        d.text((W - pad - hw, H - 122), handle, font=_font(FONT_BOLD, 32), fill=accent)

    out_dir = DATA_DIR / "cards"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"{name}.png"
    img.save(path, "PNG")
    return str(path)


def make_digest_card(items: list[dict], date_str: str, name: str, handle: str = "", title: str = "Tin sáng nay") -> str:
    """Thẻ 'bản tin sáng' nền sáng, tiêu đề lớn, danh sách tin đánh số (kiểu bản tin điểm tin hằng ngày)."""
    bg, ink, muted, accent = (247, 245, 240), (24, 24, 27), (120, 118, 112), (224, 98, 38)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)
    pad = 80
    d.text((pad, 90), f"BẢN TIN · {date_str}", font=_font(FONT_BOLD, 28), fill=muted)
    tw = d.textlength(f"{len(items)} TIN", font=_font(FONT_BOLD, 28))
    d.text((W - pad - tw, 90), f"{len(items)} TIN", font=_font(FONT_BOLD, 28), fill=muted)
    d.line([(pad, 140), (W - pad, 140)], fill=(210, 207, 200), width=2)
    d.text((pad, 165), title, font=_font(FONT_BOLD, 104), fill=ink)
    y = 320
    d.text((pad, y), f"{len(items):02d}", font=_font(FONT_BOLD, 96), fill=accent)
    d.text((pad + 170, y + 62), "tin đáng chú ý", font=_font(FONT_REG, 36), fill=muted)
    y += 175
    f_n, f_t, f_s = _font(FONT_BOLD, 28), _font(FONT_BOLD, 34), _font(FONT_REG, 24)
    row_h = (H - 130 - y) // max(len(items), 1)
    for i, it in enumerate(items, 1):
        d.line([(pad, y), (W - pad, y)], fill=(222, 219, 212), width=2)
        d.text((pad, y + 20), f"{i:02d}", font=f_n, fill=accent)
        lines = _wrap(d, it.get("headline_vi", ""), f_t, W - 2 * pad - 90)
        if len(lines) > 2:
            lines = [lines[0], lines[1].rstrip(" ,.:;") + "…"]
        yy = y + 16
        for ln in lines:
            d.text((pad + 90, yy), ln, font=f_t, fill=ink)
            yy += 42
        d.text((pad + 90, yy + 2), f"{it.get('source', '').replace('GNews: ', '')} · {it.get('topic', '')}", font=f_s, fill=muted)
        y += row_h
    if handle:
        d.text((pad, H - 90), handle, font=_font(FONT_BOLD, 30), fill=ink)
    out_dir = DATA_DIR / "cards"
    out_dir.mkdir(exist_ok=True)
    path = out_dir / f"{name}.png"
    img.save(path, "PNG")
    return str(path)
