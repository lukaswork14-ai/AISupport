"""Video reels dọc 1080x1920 tối ưu cho Facebook Reels:
- Hook chữ cực lớn ngay khung đầu (3 giây đầu), không ảnh rườm rà.
- Chữ trên màn hình + phụ đề lời đọc (người xem không bật tiếng vẫn hiểu), con số được tô màu nhấn.
- Nằm trong vùng an toàn (tránh phần Facebook phủ nút/caption ở trên, dưới và cạnh phải).
- Thanh tiến trình theo cảnh ở trên cùng + chuyển động zoom nhẹ mỗi cảnh để giữ mắt người xem.
- Nhịp nhanh: giọng đọc AI nhanh hơn, cắt khoảng lặng giữa cảnh."""
import datetime as dt
import logging
import re

from PIL import Image, ImageDraw

from agents.imagecard import FONT_BOLD, FONT_REG, PALETTES, _font, _wrap
from agents.reel_video import _dur, _ffmpeg, _run, _tts
from config import DATA_DIR

log = logging.getLogger("fb-reel")
VW, VH = 1080, 1920
SAFE_L, SAFE_R, SAFE_T, SAFE_B = 84, 960, 300, 1480  # vùng an toàn trên Reels
NUM = re.compile(r"\d")


def _bg(topic: str) -> tuple[Image.Image, tuple]:
    key = next((k for k in PALETTES if k.lower() in (topic or "").lower()), "default")
    top, bottom, accent = PALETTES[key]
    img = Image.new("RGB", (VW, VH), top)
    d = ImageDraw.Draw(img)
    for y in range(VH):
        t = y / VH
        d.line([(0, y), (VW, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img, accent


def _rich_line(d, x, y, line, font, color, accent):
    """Vẽ 1 dòng, từ có chữ số (7,5 / 870 / 2020 / USD đi kèm) tô màu nhấn."""
    words = line.split(" ")
    hi = [bool(NUM.search(w)) for w in words]
    for i, w in enumerate(words):  # đơn vị ngay sau con số cũng tô màu
        if not hi[i] and i and hi[i - 1] and w.lower().strip(".,!?") in ("tỷ", "triệu", "nghìn", "usd", "đô", "%", "ngày", "tháng", "năm", "người", "lần"):
            hi[i] = True
    for i, w in enumerate(words):
        d.text((x, y), w, font=font, fill=accent if hi[i] else color)
        x += d.textlength(w + " ", font=font)


def _fit(d, text, max_w, max_h, start, minimum=56, lh=1.18):
    size = start
    while size > minimum:
        f = _font(FONT_BOLD, size)
        lines = _wrap(d, text, f, max_w)
        if len(lines) * size * lh <= max_h:
            return f, lines, size
        size -= 6
    f = _font(FONT_BOLD, minimum)
    return f, _wrap(d, text, f, max_w), minimum


def frame(path, i, total, big, sub, topic, label="", handle="", kind="beat"):
    img, accent = _bg(topic)
    d = ImageDraw.Draw(img)
    # thanh tiến trình theo cảnh
    gap, x0, w = 10, SAFE_L, SAFE_R - SAFE_L
    seg = (w - gap * (total - 1)) / total
    for k in range(total):
        xa = x0 + k * (seg + gap)
        d.rounded_rectangle([xa, 200, xa + seg, 208], radius=4, fill=accent if k <= i else (90, 98, 120))
    if handle:
        d.text((SAFE_L, 232), handle, font=_font(FONT_BOLD, 34), fill=(225, 228, 236))
    y_top, maxw = SAFE_T + 60, SAFE_R - SAFE_L
    if label:
        fl = _font(FONT_BOLD, 34)
        lab = label.upper()[:26]
        tw = d.textlength(lab, font=fl)
        d.rounded_rectangle([SAFE_L, y_top, SAFE_L + tw + 44, y_top + 62], radius=31, fill=accent)
        d.text((SAFE_L + 22, y_top + 11), lab, font=fl, fill=(15, 18, 28))
        y_top += 110
    sub_lines = []
    fs = _font(FONT_REG, 50)
    if sub:
        sub_lines = _wrap(d, sub, fs, maxw)[:4]
    sub_h = len(sub_lines) * 66 + (60 if sub_lines else 0)
    area = SAFE_B - y_top - sub_h
    fb, lines, size = _fit(d, big, maxw, area * 0.9, 150 if kind == "hook" else 128)
    block = len(lines) * int(size * 1.18)
    y = y_top + max(0, (area - block) // 2)
    for ln in lines:
        _rich_line(d, SAFE_L, y, ln, fb, (255, 255, 255), accent)
        y += int(size * 1.18)
    if sub_lines:
        y += 40
        d.rectangle([SAFE_L, y, SAFE_L + 120, y + 8], fill=accent)
        y += 34
        for ln in sub_lines:
            _rich_line(d, SAFE_L, y, ln, fs, (214, 219, 230), accent)
            y += 66
    img.save(path)


def make(reel: dict, topic: str = "", label: str = "", handle: str = "", name: str = "reel",
         voice: str | None = None, fast: bool = True, motion: bool = True) -> tuple[str, str]:
    """Dựng reels từ kịch bản {hook, beats[{on_screen, voiceover}], cta}. Trả về (đường dẫn mp4, engine giọng)."""
    ff = _ffmpeg()
    work = DATA_DIR / "video_tmp" / name
    work.mkdir(parents=True, exist_ok=True)
    scenes = [("hook", reel.get("hook", ""), "", reel.get("hook", ""))]
    for b in reel.get("beats") or []:
        scenes.append(("beat", b.get("on_screen") or b.get("voiceover", ""), b.get("voiceover", ""), b.get("voiceover", "")))
    if reel.get("cta"):
        scenes.append(("cta", reel["cta"], "Bình luận suy nghĩ của bạn bên dưới", reel["cta"]))
    total, rate, gap = len(scenes), ("+14%" if fast else "+6%"), (0.12 if fast else 0.35)
    parts, engine = [], ""
    for i, (kind, big, sub, speech) in enumerate(scenes):
        png, wav, seg = (str(work / f"s{i}.{x}") for x in ("png", "wav", "mp4"))
        frame(png, i, total, big, sub, topic, label if kind == "hook" else "", handle, kind)
        engine = _tts(speech or big, wav, voice, rate)
        dur = _dur(wav) + gap
        frames = max(1, int(dur * 30))
        if motion:  # zoom chậm 0 -> 4%, phóng ảnh gốc trước để chữ không rung
            vf = (f"scale=2160:3840,zoompan=z='1+0.04*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                  f":d={frames}:s=1080x1920:fps=30,format=yuv420p")
            args = [ff, "-y", "-i", png, "-i", wav, "-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]", "-map", "1:a"]
        else:
            args = [ff, "-y", "-loop", "1", "-framerate", "30", "-i", png, "-i", wav, "-pix_fmt", "yuv420p"]
        _run(args + ["-af", f"apad=pad_dur={gap}", "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast",
                     "-crf", "20", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", seg])
        parts.append(seg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    out_dir = DATA_DIR / "videos"
    out_dir.mkdir(exist_ok=True)
    out = str(out_dir / f"{name}-{dt.datetime.now():%Y%m%d-%H%M%S}.mp4")
    _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", out])
    return out, engine
