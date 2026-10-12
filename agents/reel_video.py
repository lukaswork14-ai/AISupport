"""Dựng video reels dọc 1080x1920 kiểu 'Bản tin sáng': khung hình Pillow + giọng đọc AI tiếng Việt + ghép bằng ffmpeg.
Giọng đọc: edge-tts (vi-VN-HoaiMyNeural / NamMinh), dự phòng giọng 'Linh' có sẵn của macOS, cuối cùng là video không tiếng."""
import asyncio
import datetime as dt
import logging
import os
import shutil
import subprocess
import re
import wave

from PIL import Image, ImageDraw

from agents.imagecard import FONT_BOLD, FONT_REG, _font, _wrap
from config import DATA_DIR

log = logging.getLogger("reel-video")
VW, VH = 1080, 1920
BG, INK, MUTED, ACCENT, LINE = (247, 245, 240), (24, 24, 27), (120, 118, 112), (224, 98, 38), (222, 219, 212)
VOICES = {"HoaiMy": "vi-VN-HoaiMyNeural", "NamMinh": "vi-VN-NamMinhNeural"}
SETTINGS = DATA_DIR / "settings.json"


def get_voice() -> str:
    import json
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8")).get("voice", "vi-VN-NamMinhNeural")
    except Exception:
        return os.getenv("TTS_VOICE", "vi-VN-NamMinhNeural")


def set_voice(name: str):
    import json
    try:
        d = json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d["voice"] = VOICES.get(name, name)
    SETTINGS.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
        if not exe:
            raise RuntimeError("Chưa có ffmpeg. Chạy lại Khoi-dong.command để cài imageio-ffmpeg.")
        return exe


def _run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-600:])


# ------------------------------------------------------------------ khung hình
def _base(date_str: str, right: str, prefix: str = "BẢN TIN · "):
    img = Image.new("RGB", (VW, VH), BG)
    d = ImageDraw.Draw(img)
    pad = 80
    d.text((pad, 110), f"{prefix}{date_str}", font=_font(FONT_BOLD, 32), fill=MUTED)
    tw = d.textlength(right, font=_font(FONT_BOLD, 32))
    d.text((VW - pad - tw, 110), right, font=_font(FONT_BOLD, 32), fill=MUTED)
    d.line([(pad, 168), (VW - pad, 168)], fill=LINE, width=2)
    d.text((pad, VH - 130), "Giọng đọc được tạo bằng AI", font=_font(FONT_REG, 26), fill=MUTED)
    return img, d, pad


def frame_intro(items, date_str, handle, path):
    img, d, pad = _base(date_str, f"{len(items)} TIN")
    d.text((pad, 260), "Tin sáng nay", font=_font(FONT_BOLD, 128), fill=INK)
    d.text((pad, 470), f"{len(items):02d}", font=_font(FONT_BOLD, 150), fill=ACCENT)
    d.text((pad + 260, 560), "tin đáng chú ý", font=_font(FONT_REG, 46), fill=MUTED)
    y = 780
    f = _font(FONT_BOLD, 38)
    for i, it in enumerate(items, 1):
        d.line([(pad, y), (VW - pad, y)], fill=LINE, width=2)
        d.text((pad, y + 26), f"{i:02d}", font=_font(FONT_BOLD, 32), fill=ACCENT)
        ln = _wrap(d, it["headline_vi"], f, VW - 2 * pad - 90)
        ln = _wrap(d, it["headline_vi"], f, VW - 2 * pad - 130)
        txt = ln[0] + ("…" if len(ln) > 1 else "")
        d.text((pad + 90, y + 22), txt, font=f, fill=INK)
        y += 150
    if handle:
        d.text((pad, VH - 200), handle, font=_font(FONT_BOLD, 36), fill=INK)
    img.save(path)


def frame_item(it, n, total, date_str, path):
    img, d, pad = _base(date_str, f"{n:02d}/{total:02d}")
    d.text((pad, 250), f"{n:02d}", font=_font(FONT_BOLD, 180), fill=ACCENT)
    tag = (it.get("topic") or "TIN").upper()
    ft = _font(FONT_BOLD, 32)
    tw = d.textlength(tag, font=ft)
    d.rounded_rectangle([pad, 480, pad + tw + 50, 540], radius=30, fill=INK)
    d.text((pad + 25, 490), tag, font=ft, fill=BG)
    y = 600
    size = 70
    while size > 46:
        fh = _font(FONT_BOLD, size)
        lines = _wrap(d, it["headline_vi"], fh, VW - 2 * pad)
        if len(lines) <= 5:
            break
        size -= 6
    for ln in lines:
        d.text((pad, y), ln, font=fh, fill=INK)
        y += int(size * 1.25)
    y += 40
    d.rectangle([pad, y, pad + 140, y + 10], fill=ACCENT)
    y += 60
    fs = _font(FONT_REG, 42)
    for ln in _wrap(d, it.get("summary_vi", ""), fs, VW - 2 * pad)[:9]:
        d.text((pad, y), ln, font=fs, fill=(60, 60, 64))
        y += 60
    src = it.get("source", "").replace("GNews: ", "")
    d.text((pad, VH - 200), f"Nguồn: {src}", font=_font(FONT_REG, 32), fill=MUTED)
    img.save(path)


def frame_outro(handle, date_str, path):
    img, d, pad = _base(date_str, "HẾT")
    f = _font(FONT_BOLD, 84)
    y = 640
    for ln in _wrap(d, "Tin nào bạn quan tâm nhất?", f, VW - 2 * pad):
        d.text((pad, y), ln, font=f, fill=INK)
        y += 105
    y += 30
    for ln in _wrap(d, "Comment số thứ tự, mình sẽ viết phân tích sâu hơn.", _font(FONT_REG, 48), VW - 2 * pad):
        d.text((pad, y), ln, font=_font(FONT_REG, 48), fill=MUTED)
        y += 66
    if handle:
        d.text((pad, y + 80), f"Theo dõi {handle} để nhận bản tin mỗi sáng", font=_font(FONT_BOLD, 40), fill=ACCENT)
    img.save(path)


# ------------------------------------------------------------------ giọng đọc
def _tts_edge(text, mp3, voice=None, rate="+8%"):
    import edge_tts

    async def go():
        await edge_tts.Communicate(text, voice or get_voice(), rate=rate).save(mp3)
    asyncio.run(go())


def _tts(text: str, out_wav: str, voice: str | None = None, rate: str = "+8%") -> str:
    """Trả về tên engine đã dùng. Luôn tạo ra out_wav."""
    ff = _ffmpeg()
    tmp = out_wav + ".src"
    try:
        _tts_edge(text, tmp + ".mp3", VOICES.get(voice, voice) if voice else None, rate)
        _run([ff, "-y", "-i", tmp + ".mp3", "-ar", "44100", "-ac", "1", out_wav])
        return "edge-tts"
    except Exception as e:
        log.warning("edge-tts lỗi: %s", e)
    if shutil.which("say"):
        try:
            _run(["say", "-v", "Linh", "-o", tmp + ".aiff", text])
            _run([ff, "-y", "-i", tmp + ".aiff", "-ar", "44100", "-ac", "1", out_wav])
            return "macOS say"
        except Exception as e:
            log.warning("say lỗi: %s", e)
    secs = max(3.0, len(text.split()) / 2.6)  # không có giọng: im lặng theo độ dài lời
    _run([ff, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{secs:.1f}", out_wav])
    return "silent"


def _dur(wav_path: str) -> float:
    with wave.open(wav_path) as w:
        return w.getnframes() / float(w.getframerate())


# ------------------------------------------------------------------ dựng video
def narration(items, date_vi):
    segs = [f"Bản tin sáng ngày {date_vi}. Đây là {len(items)} tin AI và thương mại điện tử đáng chú ý nhất trong 24 giờ qua."]
    for i, it in enumerate(items, 1):
        first = re.split(r"(?<=[.!?])\s+", (it.get("summary_vi") or "").strip())[0]
        segs.append(f"Tin số {i}. {it['headline_vi']}. {first}")
    segs.append("Tin nào bạn quan tâm nhất? Comment số thứ tự để mình viết phân tích sâu hơn nhé.")
    return segs


def make_bantin_video(items: list[dict], handle: str = "") -> tuple[str, str]:
    """Trả về (đường dẫn mp4, engine giọng đọc)."""
    ff = _ffmpeg()
    today = dt.date.today()
    date_str = today.strftime("%d.%m.%Y")
    date_vi = f"{today.day} tháng {today.month}"
    work = DATA_DIR / "video_tmp"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)
    frames = [str(work / f"f{i}.png") for i in range(len(items) + 2)]
    frame_intro(items, date_str, handle, frames[0])
    for i, it in enumerate(items, 1):
        frame_item(it, i, len(items), date_str, frames[i])
    frame_outro(handle, date_str, frames[-1])
    engine = ""
    parts = []
    for i, (png, text) in enumerate(zip(frames, narration(items, date_vi))):
        wav = str(work / f"a{i}.wav")
        engine = _tts(text, wav)
        seg = str(work / f"s{i}.mp4")
        _run([ff, "-y", "-loop", "1", "-framerate", "30", "-i", png, "-i", wav,
              "-af", "apad=pad_dur=0.6", "-t", f"{_dur(wav) + 0.6:.2f}",
              "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "128k", "-ar", "44100", seg])
        parts.append(seg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    out_dir = DATA_DIR / "videos"
    out_dir.mkdir(exist_ok=True)
    out = str(out_dir / f"bantin-{today.isoformat()}.mp4")
    _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", out])
    return out, engine


def voice_sample(name: str) -> str:
    """Tạo file mp3 nghe thử cho một giọng (cần mạng)."""
    out = DATA_DIR / f"sample-{name}.mp3"
    _tts_edge("Chào bạn, đây là bản tin sáng về AI và thương mại điện tử. Hôm nay có năm tin đáng chú ý dành cho anh em seller.",
              str(out), VOICES[name])
    return str(out)


# ------------------------------------------------------------ video từ kịch bản reels của 1 bài
def _frame_text(path, left, right, tag, big, small="", image=None, big_size=88):
    img, d, pad = _base(left, right, prefix="")
    y = 230
    if tag:
        ft = _font(FONT_BOLD, 32)
        tw = d.textlength(tag.upper(), font=ft)
        d.rounded_rectangle([pad, y, pad + tw + 50, y + 60], radius=30, fill=INK)
        d.text((pad + 25, y + 10), tag.upper(), font=ft, fill=BG)
        y += 110
    if image:
        try:
            pic = Image.open(image).convert("RGB")
            w = VW - 2 * pad
            h = int(pic.height * w / pic.width)
            if h > 760:
                h = 760
                pic = pic.crop((0, 0, pic.width, int(pic.width * h / w)))
            pic = pic.resize((w, h))
            img.paste(pic, (pad, y))
            y += h + 50
        except Exception:
            pass
    size = big_size
    while size > 48:
        fb = _font(FONT_BOLD, size)
        lines = _wrap(d, big, fb, VW - 2 * pad)
        if len(lines) * size * 1.25 <= (VH - 360 - y) * 0.75:
            break
        size -= 6
    fs = _font(FONT_REG, 44)
    small_lines = _wrap(d, small, fs, VW - 2 * pad)[:8] if small else []
    if not image:  # căn giữa khối chữ theo chiều dọc cho cảnh chỉ có chữ
        block = len(lines) * int(size * 1.25) + (90 + len(small_lines) * 62 if small_lines else 0)
        y = max(y, (VH - block) // 2 - 40)
    for ln in lines:
        d.text((pad, y), ln, font=fb, fill=INK)
        y += int(size * 1.25)
    if small:
        y += 30
        d.rectangle([pad, y, pad + 140, y + 10], fill=ACCENT)
        y += 50
        for ln in small_lines:
            d.text((pad, y), ln, font=fs, fill=(70, 70, 74))
            y += 62
    img.save(path)


def make_post_video(reel: dict, topic: str = "", source: str = "", card_image: str | None = None,
                    handle: str = "", name: str = "bai", voice: str | None = None, rate: str = "+8%") -> tuple[str, str]:
    """Dựng video dọc từ kịch bản reels (hook -> các cảnh -> CTA). Trả về (mp4, engine giọng)."""
    ff = _ffmpeg()
    work = DATA_DIR / "video_tmp" / name
    work.mkdir(parents=True, exist_ok=True)
    beats = reel.get("beats") or []
    scenes = [("hook", reel.get("hook", ""), "", reel.get("hook", ""), card_image)]
    for b in beats:
        scenes.append(("beat", b.get("on_screen", ""), b.get("voiceover", ""), b.get("voiceover", ""), None))
    cta = reel.get("cta", "")
    if cta:
        scenes.append(("cta", cta, f"Theo dõi {handle}" if handle else "", cta, None))
    total = len(scenes)
    src = (source or "").replace("GNews: ", "")
    parts, engine = [], ""
    for i, (kind, big, small, speech, image) in enumerate(scenes):
        png, wav, seg = (str(work / f"{name}{i}.{x}") for x in ("png", "wav", "mp4"))
        _frame_text(png, src.upper()[:28] or "REELS", f"{i + 1:02d}/{total:02d}",
                    topic if kind == "hook" else "", big or speech, "" if kind == "hook" else small,
                    image=image, big_size=96 if kind == "hook" else 104)
        engine = _tts(speech or big, wav, voice, rate)
        gap = 0.15 if rate != "+8%" else 0.4  # nhịp nhanh cho reels: cắt khoảng lặng giữa cảnh
        _run([ff, "-y", "-loop", "1", "-framerate", "30", "-i", png, "-i", wav,
              "-af", f"apad=pad_dur={gap}", "-t", f"{_dur(wav) + gap:.2f}",
              "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-pix_fmt", "yuv420p",
              "-c:a", "aac", "-b:a", "128k", "-ar", "44100", seg])
        parts.append(seg)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    out_dir = DATA_DIR / "videos"
    out_dir.mkdir(exist_ok=True)
    out = str(out_dir / f"{name}-{dt.datetime.now():%Y%m%d-%H%M%S}.mp4")
    _run([ff, "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", out])
    return out, engine
