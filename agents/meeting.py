"""Meeting Studio: thu âm thanh cuộc họp từ nhiều nguồn -> chép lời tiếng Việt (mốc thời gian + người nói)
-> AI biên tập: recap, quyết định, việc tiếp theo, câu hỏi còn mở, sơ đồ cả buổi (mọi ý có mốc thời gian để nghe lại)
-> tự phân loại (tổ chức / vai trò / dự án / phòng ban / loại cuộc họp) -> lưu vào Obsidian, liên kết ghi chú
-> hỏi lại bất cứ lúc nào: tìm trong kho cuộc họp, trả lời ngắn gọn kèm nguồn.

Nguồn âm thanh: tải file, ghi âm trong Mini App, gửi file/voice vào bot Telegram, (sau) thiết bị Plaud, bot dự họp online.
Dữ liệu: data/meetings/<id>/meta.json + audio.mp3."""
import base64
import datetime as dt
import json
import logging
import math
import os
import queue as _queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from config import DATA_DIR, IS_TENANT, LLM_MODEL, OBSIDIAN_VAULT
from llm import ask_json, fix_vi, make_client

log = logging.getLogger("meeting")
ROOT = DATA_DIR / "meetings"
INBOX = ROOT / "_inbox"
TAXO = ROOT / "taxonomy.json"
STT_MODEL = __import__("os").getenv("MEETING_STT_MODEL", "google/gemini-2.5-flash")
CHUNK_SEC = 300  # mỗi đoạn gửi đi chép lời (5 phút): đủ ngữ cảnh, không quá dài để model bỏ sót
_lock = threading.Lock()

ORGS = {  # tổ chức -> vai trò của anh Huy (superHuy dự họp với vai trò tương ứng)
    "sellnity": {"name": "Sellnity", "role": "CEO", "desc": "AI + POD thương mại điện tử xuyên biên giới"},
    "leversphere": {"name": "Leversphere", "role": "CGO kiêm CAO", "desc": "tăng trưởng và AI"},
    "ca-nhan": {"name": "Cá nhân", "role": "Cá nhân", "desc": "việc riêng, sức khoẻ, gia đình, học tập"},
}
TYPES = ["Họp nội bộ", "Họp ban lãnh đạo", "1-1", "Đối tác", "Khách hàng", "Nhà đầu tư", "Tuyển dụng", "Đào tạo / chia sẻ",
         "Brainstorm", "Báo cáo tiến độ", "Khác"]


# ------------------------------------------------------------------ đồng ý ghi âm (quyết định #7 + thẻ 15, họp 17/10/2026)
# Bản của khách (IS_TENANT): biên bản từ ghi âm tạm đóng cho tới khi có DPIA (anh đặt SUPERYOU_RECORDING=1 trên VPS).
# Khi mở: mỗi bản ghi phải có xác nhận đồng ý (thời điểm, nguồn, phiên bản câu chữ); thiếu thì KHÔNG gửi âm thanh đi chép lời.
CONSENT_VERSION = "2026-10-17"
CONSENT_TEXT = ("superYou sẽ ghi âm và chuyển thành văn bản cuộc họp này, tách theo người nói. Âm thanh và văn bản được xử lý "
                "bởi mô hình AI, có thể ở nước ngoài. Bạn xác nhận đã thông báo cho mọi người tham gia và được họ đồng ý.")
RECORDING_CLOSED_TEXT = ("Biên bản từ ghi âm đang tạm đóng trong giai đoạn thử nghiệm để hoàn tất hồ sơ bảo vệ dữ liệu. "
                         "Bạn vẫn có thể dán ghi chú cuộc họp vào ô chat để superYou làm biên bản.")


def consent_required() -> bool:
    return IS_TENANT


def recording_enabled() -> bool:
    return (not IS_TENANT) or __import__("os").getenv("SUPERYOU_RECORDING", "0").strip() == "1"


def rec_policy() -> dict:
    return {"enabled": recording_enabled(), "consent": consent_required(), "consent_text": CONSENT_TEXT, "version": CONSENT_VERSION,
            "closed_text": "" if recording_enabled() else RECORDING_CLOSED_TEXT}


def make_consent(source: str) -> dict:
    return {"ok": True, "version": CONSENT_VERSION, "at": dt.datetime.now().isoformat(timespec="seconds"), "source": str(source)[:40]}


# ------------------------------------------------------------------ lưu trữ
def _dir(mid: str):
    return ROOT / mid


def load(mid: str) -> dict | None:
    try:
        return json.loads((_dir(mid) / "meta.json").read_text(encoding="utf-8"))
    except Exception:
        return None


def save(m: dict):
    d = _dir(m["id"])
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "meta.json.tmp"
    tmp.write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(d / "meta.json")


def patch(mid: str, **kw) -> dict:
    with _lock:
        m = load(mid) or {"id": mid}
        m.update(kw)
        save(m)
        return m


def all_meetings() -> list[dict]:
    out = []
    if ROOT.exists():
        for p in ROOT.iterdir():
            if p.is_dir() and not p.name.startswith("_"):
                m = load(p.name)
                if m:
                    out.append(m)
    out.sort(key=lambda m: m.get("started") or m.get("created", ""), reverse=True)
    return out


def taxonomy() -> dict:
    try:
        t = json.loads(TAXO.read_text(encoding="utf-8"))
    except Exception:
        t = {}
    t.setdefault("projects", {})   # org -> [tên dự án]
    t.setdefault("departments", {})  # org -> [phòng ban]
    t.setdefault("people", {})     # tên -> {org, role}
    return t


def _learn_taxonomy(labels: dict, people: list[str]):
    t = taxonomy()
    org = labels.get("org") or "khac"
    for key, val in (("projects", labels.get("project")), ("departments", labels.get("department"))):
        if val and val not in t[key].setdefault(org, []):
            t[key][org].append(val)
    for p in people or []:
        if p and not re.fullmatch(r"(S|Người nói )\d+", p):
            t["people"].setdefault(p, {"org": org})
    ROOT.mkdir(parents=True, exist_ok=True)
    TAXO.write_text(json.dumps(t, ensure_ascii=False, indent=1), encoding="utf-8")


# ------------------------------------------------------------------ âm thanh
def _ff() -> str:
    from agents.reel_video import _ffmpeg
    return _ffmpeg()


def _duration(path) -> float:
    r = subprocess.run([_ff(), "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else 0.0


def normalize(src, dst):
    """Chuẩn hoá về mp3 mono 16 kHz 40 kbps (giọng nói rõ, file nhỏ: ~18 MB/giờ). Lọc nhiễu nhẹ + cân âm lượng."""
    r = subprocess.run([_ff(), "-y", "-i", str(src), "-vn", "-ac", "1", "-ar", "16000",
                        "-af", "highpass=f=70,lowpass=f=7800,dynaudnorm=f=250:g=15", "-b:a", "40k", str(dst)],
                       capture_output=True, text=True)
    if r.returncode != 0 or not dst.exists():
        raise RuntimeError("Không đọc được file âm thanh: " + r.stderr[-300:])


def _chunks(audio, dur: float, work) -> list[tuple[float, str]]:
    n = max(1, math.ceil(dur / CHUNK_SEC))
    out = []
    for i in range(n):
        start = i * CHUNK_SEC
        p = work / f"c{i:03d}.mp3"
        subprocess.run([_ff(), "-y", "-ss", str(start), "-t", str(CHUNK_SEC + 2), "-i", str(audio), "-c", "copy", str(p)],
                       capture_output=True)
        if p.exists() and p.stat().st_size > 2000:
            out.append((float(start), str(p)))
    return out


# ------------------------------------------------------------------ chép lời
STT_PROMPT = """Bạn là thư ký chép lời cuộc họp chuyên nghiệp. Đây là đoạn {k}/{n} của một cuộc họp (đoạn này bắt đầu ở phút {start} của cả buổi).
Chép lời CHÍNH XÁC, đầy đủ bằng tiếng Việt (giữ nguyên thuật ngữ tiếng Anh như họ nói: KPI, sprint, POD, Etsy...).
Bỏ âm đệm vô nghĩa (ờ, à, ừm) nhưng không tóm tắt, không bỏ ý. Không bịa phần không nghe rõ: ghi "[không rõ]".
TỪ VỰNG HAY GẶP (nghe gần giống thì viết đúng chính tả này): {vocab}
CÁCH NGƯỜI VIỆT HAY ĐỌC: {aliases}
Tách lượt theo NGƯỜI NÓI, gán nhãn S1, S2, S3... theo giọng. {known}
Nếu ai được gọi tên trong lúc nói (vd "anh Huy ơi", "em Lan báo cáo"), ghi tên vào "names".
Mốc "t" là thời điểm bắt đầu câu, tính TỪ ĐẦU ĐOẠN NÀY, dạng MM:SS. Mỗi lượt nói tối đa ~3 câu; nói dài thì tách nhiều lượt.
Trả về DUY NHẤT JSON:
{{"segments": [{{"t": "MM:SS", "spk": "S1", "text": "..."}}],
 "speakers": {{"S1": {{"name": "tên nếu biết, ngược lại rỗng", "voice": "mô tả giọng ngắn: nam/nữ, trầm/cao, vai trò có vẻ là gì"}}}}}}"""


BASE_VOCAB = ["Sellnity", "Leversphere", "superHuy", "Huy", "POD", "print on demand", "Etsy", "Amazon", "Shopify", "TikTok Shop",
              "Temu", "Shein", "Lark", "OpenAI", "Claude", "ChatGPT", "AI agent", "AI-native", "KPI", "OKR", "ROAS", "CPA", "GMV",
              "SKU", "fulfillment", "listing", "seller", "Hyrox", "VMM"]


ALIASES = {"Etsy": "ét-xi, ét xy, SC", "Sellnity": "xeo-ni-ti, sen-ni-ty, Salini", "Shopify": "sóp-pi-phai", "Leversphere": "li-vơ-sphia, lever sphere",
           "TikTok Shop": "tíc tóc shop", "Amazon": "a-ma-dôn", "POD": "pi-ô-đi, bót", "KPI": "ka-pi-ai", "ROAS": "rô-át"}


def aliases() -> str:
    return "; ".join(f"nghe như “{v}” → viết “{k}”" for k, v in ALIASES.items())


def vocabulary() -> str:
    """Từ điển riêng: tên công ty, dự án, phòng ban, người đã biết + file data/meetings/glossary.txt (anh tự thêm)."""
    t = taxonomy()
    words = list(BASE_VOCAB)
    for v in list(t["projects"].values()) + list(t["departments"].values()):
        words += v
    words += list(t["people"])
    try:
        words += [w.strip() for w in (ROOT / "glossary.txt").read_text(encoding="utf-8").replace(",", "\n").splitlines() if w.strip()]
    except Exception:
        pass
    seen, out = set(), []
    for w in words:
        if w and w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return ", ".join(out[:150])


def _sec(t) -> float:
    if isinstance(t, (int, float)):
        return float(t)
    parts = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", str(t))][-3:]
    s = 0.0
    for x in parts:
        s = s * 60 + x
    return s


def transcribe_chunk(path: str, k: int, n: int, start: float, speakers: dict) -> dict:
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    known = ""
    if speakers:
        known = "Các người nói đã nhận diện ở đoạn trước (giữ ĐÚNG nhãn nếu là cùng người): " + "; ".join(
            f"{k_}: {v.get('name') or '?'} ({v.get('voice', '')})" for k_, v in speakers.items())
    prompt = STT_PROMPT.format(k=k, n=n, start=f"{int(start // 60)}", known=known, vocab=vocabulary(), aliases=aliases())
    last = ""
    for attempt in range(3):
        try:
            kw = {"response_format": {"type": "json_object"}} if attempt == 0 else {}
            r = make_client().chat.completions.create(
                model=STT_MODEL, max_tokens=16000, temperature=0.1, **kw,
                messages=[{"role": "user", "content": [{"type": "text", "text": prompt},
                                                       {"type": "input_audio", "input_audio": {"data": b64, "format": "mp3"}}]}],
                timeout=300)
            from llm import parse_json
            txt = r.choices[0].message.content or ""
            res = parse_json(txt)
            if isinstance(res, dict) and res.get("segments"):
                return res
            last = f"[finish={r.choices[0].finish_reason}] {txt[-300:]}"
        except Exception as e:  # noqa: BLE001
            last = str(e)[:300]
            time.sleep(3 + attempt * 4)
    raise RuntimeError(f"Chưa chép lời được đoạn {k}/{n}: {last}")


def _cut(audio, work, a: float, b: float) -> str:
    p = work / f"r{int(a * 10)}_{int(b * 10)}.mp3"
    subprocess.run([_ff(), "-y", "-ss", f"{a:.2f}", "-t", f"{b - a + 1:.2f}", "-i", str(audio), "-c", "copy", str(p)], capture_output=True)
    return str(p)


def _merge_speakers(speakers: dict, res: dict):
    for spk, info in (res.get("speakers") or {}).items():
        info = info if isinstance(info, dict) else {"voice": str(info)}
        cur = speakers.setdefault(spk, {"name": "", "voice": ""})
        cur["voice"] = cur["voice"] or info.get("voice", "")
        cur["name"] = cur["name"] or (info.get("name") or "")


def _transcribe_once(audio, work, a: float, b: float, k: int, n: int, speakers: dict) -> list[dict]:
    path = _cut(audio, work, a, b)
    if not Path(path).exists() or Path(path).stat().st_size < 1500:
        return []
    res = transcribe_chunk(path, k, n, a, speakers)
    _merge_speakers(speakers, res)
    out = []
    for s in res.get("segments") or []:
        txt = fix_vi(str(s.get("text", ""))).strip()
        if txt:
            out.append({"s": round(a + min(_sec(s.get("t", 0)), b - a + 1), 1), "spk": str(s.get("spk") or "S1")[:12], "text": txt})
    return sorted(out, key=lambda x: x["s"])


def _transcribe_range(audio, work, a: float, b: float, k: int, n: int, speakers: dict) -> list[dict]:
    """Chép lời [a, b] giây. Model đôi khi dừng sớm hoặc bỏ sót một quãng (nhất là đoạn dài, nội dung lặp):
    kiểm tra độ phủ; phần cuối chưa chép thì chép tiếp (tối đa 8 lần), quãng trống > 45 giây ở giữa thì chép lại riêng quãng đó."""
    out = _transcribe_once(audio, work, a, b, k, n, speakers)
    for _ in range(8):  # chép tiếp phần đuôi còn thiếu
        last = out[-1]["s"] if out else a
        if b - last <= 40:
            break
        more = _transcribe_once(audio, work, last + 4 if out else a, b, k, n, speakers)
        more = [x for x in more if x["s"] > last + 1]
        if not more:
            break  # quãng cuối không có tiếng nói
        log.info("Chép tiếp phần đuôi %.0f-%.0f giây", last, b)
        out += more
    marks = [x["s"] for x in out]
    for i in range(len(marks) - 1):  # quãng trống ở giữa
        ga, gb = marks[i] + 4, marks[i + 1]
        if gb - ga > 45:
            fill = [x for x in _transcribe_once(audio, work, ga, gb, k, n, speakers) if ga - 1 < x["s"] < gb - 1]
            if fill:
                log.info("Chép bù quãng trống %.0f-%.0f giây", ga, gb)
                out += fill
    out.sort(key=lambda x: x["s"])
    dedup = []  # chỗ chép nối/chép bù có thể lặp lại cùng một câu
    for x in out:
        if any(abs(x["s"] - y["s"]) < 8 and (x["text"] in y["text"] or y["text"] in x["text"]) for y in dedup[-4:]):
            continue
        dedup.append(x)
    return dedup


# ------------------------------------------------------------------ biên tập
RECAP = """Bạn là chánh văn phòng của anh Huy, biên tập biên bản cuộc họp sắc gọn, đúng sự thật.
Anh Huy: CEO Sellnity (AI + POD xuyên biên giới) và CGO kiêm CAO của Leversphere. superHuy là trợ lý AI của anh.
{memory}
{kb}
BẢNG PHÂN LOẠI ĐÃ DÙNG (ưu tiên dùng lại đúng tên để ghi chú liên kết nhau; chỉ tạo tên mới khi thật sự khác):
- Tổ chức: sellnity (anh là CEO) | leversphere (anh là CGO kiêm CAO) | ca-nhan | khac
- Dự án đã có: {projects}
- Phòng ban đã có: {departments}
- Người đã biết: {people}
- Loại cuộc họp: {types}
{hint}
NGÀY HỌP: {mdate} ({wd}). Hạn chót nói kiểu "thứ Sáu này", "cuối tuần sau" thì quy ra ngày cụ thể YYYY-MM-DD theo ngày họp.
QUY TẮC: chỉ dùng thông tin có trong lời thoại. Mỗi ý PHẢI có "t" = số giây (lấy từ mốc [mm:ss] của câu làm bằng chứng) để anh bấm nghe lại.
Không bịa người phụ trách hay hạn chót; không rõ thì để rỗng. Viết tiếng Việt, ngắn, rõ, có số liệu nếu có.

LỜI THOẠI (mốc [phút:giây] | người nói | nội dung):
{transcript}

Trả về DUY NHẤT JSON:
{{"title": "tiêu đề cuộc họp ≤ 70 ký tự, cụ thể",
 "summary": "3-5 câu: mục đích, kết quả chính",
 "labels": {{"org": "sellnity|leversphere|ca-nhan|khac", "project": "tên dự án hoặc rỗng", "department": "phòng ban hoặc rỗng",
            "type": "một loại ở trên", "topics": ["2-5 chủ đề ngắn, viết thường, gạch nối"], "confidence": 0-1}},
 "speakers": {{"S1": "tên thật nếu suy ra được từ lời thoại (vd được gọi tên), ngược lại rỗng"}},
 "sections": [{{"title": "chủ đề thảo luận", "t": giây, "points": [{{"text": "ý chính", "t": giây}}]}}],
 "decisions": [{{"text": "quyết định đã chốt", "t": giây, "owner": ""}}],
 "next_steps": [{{"text": "việc cần làm", "owner": "", "due": "YYYY-MM-DD hoặc rỗng", "t": giây}}],
 "suggestions": [{{"text": "đề xuất của superHuy để ra quyết định / bước tiếp theo tốt hơn (có lý do ngắn)", "t": giây}}],
 "open_questions": [{{"text": "vấn đề còn bỏ ngỏ", "t": giây}}],
 "mindmap": {{"label": "chủ đề trung tâm", "children": [{{"label": "nhánh", "t": giây, "children": [{{"label": "ý", "t": giây}}]}}]}}}}"""


def _fmt(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60:02d}:{sec % 60:02d}"


def transcript_text(m: dict, limit: int = 120000) -> str:
    names = m.get("speakers") or {}
    lines = [f"[{_fmt(s['s'])}] {names.get(s['spk'], {}).get('name') or s['spk']}: {s['text']}" for s in m.get("segments", [])]
    txt = "\n".join(lines)
    if len(txt) > limit:  # rất dài: giữ cân bằng đầu-giữa-cuối
        step = len(lines) / (limit / 120)
        txt = "\n".join(lines[int(i * step)] for i in range(int(len(lines) / step)))
    return txt


def recap(m: dict) -> dict:
    from core import memory
    t = taxonomy()
    proj = "; ".join(f"{o}: {', '.join(v)}" for o, v in t["projects"].items()) or "(chưa có)"
    dept = "; ".join(f"{o}: {', '.join(v)}" for o, v in t["departments"].items()) or "(chưa có)"
    people = ", ".join(list(t["people"])[:60]) or "(chưa có)"
    hint = ""
    if m.get("hint"):
        hint = f"GỢI Ý CỦA ANH HUY VỀ CUỘC HỌP NÀY: {m['hint']}"
    if m.get("calendar"):
        hint += f"\nLỊCH TRÙNG GIỜ: {m['calendar']}"
    try:
        md = dt.date.fromisoformat((m.get("started") or "")[:10])
    except ValueError:
        md = dt.date.today()
    kbq = " ".join([m.get("hint") or "", m.get("title") or "", " ".join(x["text"] for x in (m.get("segments") or [])[:40])])[:2500]
    kb_block = ""
    try:
        from core import kb
        kb_block, _ = kb.context(kbq, k=4, max_chars=2200, min_score=3.0)
        if kb_block:
            kb_block += ("\n(Bối cảnh Second Brain chỉ dùng để phân loại đúng và viết mục suggestions sát thực tế; "
                         "KHÔNG đưa vào tóm tắt/quyết định như thể đã nói trong họp. Có thể nêu [[ghi chú]] trong suggestions.)")
    except Exception:
        pass
    prompt = RECAP.format(memory=memory.context(1500), kb=kb_block, projects=proj, departments=dept, people=people, types=" | ".join(TYPES),
                          hint=hint, transcript=transcript_text(m), mdate=md.isoformat(),
                          wd=["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"][md.weekday()])
    res = ask_json(prompt, 9000, 3, ok=lambda x: isinstance(x, dict) and x.get("summary") and x.get("sections"), tag="meeting-recap")
    if not res:
        raise RuntimeError("superHuy chưa biên tập được biên bản, thử lại sau ít phút.")
    return res


# ------------------------------------------------------------------ Obsidian
def _slug(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", s or "")
    return re.sub(r"\s+", " ", s).strip()[:70] or "Cuoc hop"


def _tag(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").lower().replace("đ", "d"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _moc(folder: str, name: str, body: str):
    p = OBSIDIAN_VAULT / folder / f"{_slug(name)}.md"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return p.stem


def to_obsidian(m: dict) -> str:
    """Ghi biên bản theo chuẩn second brain: PARA + MOC + frontmatter (Dataview) + thẻ phân cấp + liên kết người/dự án/tổ chức
    + việc cần làm dạng Obsidian Tasks + audio nhúng để nghe lại trong Obsidian."""
    r, lab = m.get("recap") or {}, m.get("labels") or {}
    org = ORGS.get(lab.get("org"), {"name": "Khác", "role": ""})
    date = (m.get("started") or m.get("created", ""))[:10] or dt.date.today().isoformat()
    proj, dept = lab.get("project", ""), lab.get("department", "")
    if proj:
        folder = f"01 Projects/{_slug(proj)}/Meetings"
    else:
        folder = f"02 Areas/{org['name']}/Meetings" + (f"/{_slug(dept)}" if dept else "")
    # MOC (bản đồ nội dung) cho tổ chức, dự án; ghi chú người
    org_link = _moc(f"02 Areas/{org['name']}", org["name"],
                    f"---\ntype: moc\norg: {lab.get('org', '')}\n---\n# {org['name']}\nVai trò của anh Huy: {org['role']}\n\n"
                    f"## Cuộc họp\n```dataview\nTABLE date, type, project, department FROM #meeting AND #org/{_tag(org['name'])} SORT date DESC\n```\n")
    proj_link = _moc(f"01 Projects/{_slug(proj)}", proj,
                     f"---\ntype: project\norg: {lab.get('org', '')}\nstatus: active\n---\n# {proj}\nThuộc [[{org_link}]]\n\n"
                     f"## Cuộc họp\n```dataview\nTABLE date, type FROM #meeting AND #project/{_tag(proj)} SORT date DESC\n```\n"
                     f"## Việc đang mở\n```tasks\nnot done\ntags include #project/{_tag(proj)}\n```\n") if proj else ""
    names = m.get("speakers") or {}
    people = sorted({(v.get("name") or "").strip() for v in names.values() if (v.get("name") or "").strip()})
    for p in people:
        _moc("03 Resources/People", p, f"---\ntype: person\norg: {lab.get('org', '')}\n---\n# {p}\n\n## Cuộc họp\n"
                                       f"```dataview\nLIST FROM #meeting AND [[{_slug(p)}]] SORT date DESC\n```\n")
    tags = ["meeting", f"org/{_tag(org['name'])}", f"role/{_tag(org['role'])}"] + ([f"project/{_tag(proj)}"] if proj else []) + \
           ([f"dept/{_tag(dept)}"] if dept else []) + [f"meeting-type/{_tag(lab.get('type', ''))}"] + [f"topic/{_tag(x)}" for x in lab.get("topics", [])][:5]
    # audio đính kèm để nghe lại trong Obsidian
    att = OBSIDIAN_VAULT / "Attachments" / "Meetings"
    att.mkdir(parents=True, exist_ok=True)
    audio_name = f"{date} {m['id']}.mp3"
    src = _dir(m["id"]) / "audio.mp3"
    embed = os.getenv("OBSIDIAN_EMBED_AUDIO", "1") != "0"  # VPS + vault git: không đẩy file âm thanh nặng lên git
    if embed and src.exists() and not (att / audio_name).exists():
        shutil.copy2(src, att / audio_name)
    tline = lambda x: f" `{_fmt(x.get('t', 0))}`" if x.get("t") is not None else ""  # noqa: E731
    pl = lambda s: "[[" + s + "]]" if s in people else s  # noqa: E731
    title = r.get("title") or m.get("title") or "Cuộc họp"
    fm = ["---", f'title: "{title.replace(chr(34), chr(39))}"', "type: meeting", f"date: {date}",
          f"duration: {_fmt(m.get('duration', 0))}", f"org: {lab.get('org', '')}", f'role: "{org["role"]}"',
          f'project: "{proj}"', f'department: "{dept}"', f'meeting_type: "{lab.get("type", "")}"',
          "participants: [" + ", ".join(f'"[[{p}]]"' for p in people) + "]", f"source: {m.get('source', '')}",
          f"superhuy_id: {m['id']}", "tags: [" + ", ".join(tags) + "]", "---", ""]
    body = [f"# {title}", "", f"Thuộc: [[{org_link}]]" + (f" › [[{proj_link}]]" if proj_link else "") + (f" › {dept}" if dept else ""),
            f"Người tham gia: {', '.join('[[' + p + ']]' for p in people) or '(chưa rõ tên)'}", "",
            f"![[{audio_name}]]" if embed else "🎧 Nghe lại âm thanh: mở superHuy › Họp (mỗi ý có mốc giờ để bấm nghe)", "",
            "## Tóm tắt", r.get("summary", ""), ""]
    if r.get("decisions"):
        body += ["## Quyết định"] + [f"- {d['text']}" + (f" ({pl(d['owner'])})" if d.get("owner") else "") + tline(d) for d in r["decisions"]] + [""]
    if r.get("next_steps"):
        body += ["## Việc tiếp theo"] + [f"- [ ] {s['text']}" + (f" 👤 {pl(s['owner'])}" if s.get("owner") else "") +
                                          (f" 📅 {s['due']}" if s.get("due") else "") + (f" #project/{_tag(proj)}" if proj else "") + tline(s)
                                          for s in r["next_steps"]] + [""]
    if r.get("suggestions"):
        body += ["## superHuy đề xuất"] + [f"- {s['text']}" + tline(s) for s in r["suggestions"]] + [""]
    if r.get("open_questions"):
        body += ["## Còn bỏ ngỏ"] + [f"- {q['text']}" + tline(q) for q in r["open_questions"]] + [""]
    if r.get("sections"):
        body += ["## Diễn biến"]
        for s in r["sections"]:
            body += [f"### {s['title']}{tline(s)}"] + [f"- {p['text']}{tline(p)}" for p in s.get("points", [])]
        body += [""]
    mm = r.get("mindmap")
    if mm:  # sơ đồ Mermaid (Obsidian hiển thị sẵn)
        lines, n = ["```mermaid", "mindmap", f"  root(({_mmsafe(mm.get('label', title))}))"], 0

        def walk(node, depth):
            for c in node.get("children", [])[:8]:
                lines.append("  " * (depth + 1) + _mmsafe(c.get("label", "")))
                walk(c, depth + 1)
        walk(mm, 1)
        lines.append("```")
        body += ["## Sơ đồ cuộc họp"] + lines + [""]
    body += ["## Lời thoại", "> [!note]- Bấm để mở lời thoại đầy đủ", *("> " + ln for ln in transcript_text(m, 400000).split("\n")), ""]
    folder_p = OBSIDIAN_VAULT / folder
    folder_p.mkdir(parents=True, exist_ok=True)
    old = m.get("obsidian")
    path = folder_p / f"{date} {_slug(title)}.md"
    if old and old != str(path):
        try:
            from pathlib import Path
            Path(old).unlink(missing_ok=True)
        except Exception:
            pass
    path.write_text("\n".join(fm + body), encoding="utf-8")
    try:
        _decision_log(m, org, proj, date, path.stem, r.get("decisions") or [])
    except Exception:
        log.exception("Không ghi được nhật ký quyết định")
    daily = OBSIDIAN_VAULT / "05 Daily" / f"{date}.md"
    daily.parent.mkdir(parents=True, exist_ok=True)
    line = f"- 🎙 [[{path.stem}]] ({org['name']}{' › ' + proj if proj else ''})\n"
    cur = daily.read_text(encoding="utf-8") if daily.exists() else f"# {date}\n\n"
    if path.stem not in cur:
        daily.write_text(cur + line, encoding="utf-8")
    return str(path)


def _decision_log(m: dict, org: dict, proj: str, date: str, note: str, decisions: list[dict]):
    """Nhật ký quyết định theo tổ chức (tích luỹ qua mọi cuộc họp): superHuy và anh tra lại "đã từng chốt gì" trước khi ra quyết định mới.
    Mỗi cuộc họp là 1 khối có mốc <!-- superhuy:id -->, làm lại biên bản thì thay đúng khối đó."""
    p = OBSIDIAN_VAULT / f"02 Areas/{org['name']}" / "Nhat ky quyet dinh.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    head = (f"---\ntitle: \"Nhật ký quyết định {org['name']}\"\ntype: decision-log\ngenerated_by: superhuy\ntags: [decision-log, org/{_tag(org['name'])}]\n---\n"
            f"# Nhật ký quyết định · {org['name']}\nsuperHuy tự ghi mọi quyết định đã chốt trong các cuộc họp (mới nhất ở trên). "
            "Anh có thể ghi thêm quyết định ngoài họp ngay trong file này.\n\n")
    cur = p.read_text(encoding="utf-8") if p.exists() else head
    a, b = f"<!-- superhuy:{m['id']} -->", f"<!-- /superhuy:{m['id']} -->"
    blocks = re.findall(r"<!-- superhuy:(\w+) -->[\s\S]*?<!-- /superhuy:\1 -->", cur)
    found = {k: re.search(r"<!-- superhuy:" + k + r" -->[\s\S]*?<!-- /superhuy:" + k + r" -->", cur).group(0) for k in blocks}
    rest = re.sub(r"<!-- superhuy:(\w+) -->[\s\S]*?<!-- /superhuy:\1 -->\n?", "", cur).rstrip("\n")
    found.pop(m["id"], None)
    if decisions:
        block = [a, f"### {date} · [[{note}]]" + (f" · {proj}" if proj else "")]
        block += [f"- {d['text']}" + (f" ({d['owner']})" if d.get("owner") else "") for d in decisions]
        found[m["id"]] = "\n".join(block + [b])
    day = lambda x: (re.search(r"### (\d{4}-\d{2}-\d{2})", x) or [None, ""])[1]  # noqa: E731
    cur = rest + "\n\n" + "\n".join(sorted(found.values(), key=day, reverse=True)) + "\n"
    p.write_text(cur, encoding="utf-8")


def _mmsafe(s: str) -> str:
    return re.sub(r"[()\[\]{}\"`]", " ", s or "").strip()[:60] or "…"


# ------------------------------------------------------------------ quy trình
_jobs: "_queue.Queue[str]" = _queue.Queue()
_worker = None


def _ensure_worker():
    global _worker
    if _worker and _worker.is_alive():
        return
    _worker = threading.Thread(target=_loop, daemon=True, name="meeting-worker")
    _worker.start()


def _loop():
    while True:
        mid = _jobs.get()
        try:
            process(mid)
        except Exception as e:  # noqa: BLE001
            log.exception("Xử lý cuộc họp lỗi")
            patch(mid, status="error", err=str(e)[:400], step="")
        finally:
            _jobs.task_done()


def resume_pending():
    for m in all_meetings():
        if m.get("status") in ("queued", "working"):
            _jobs.put(m["id"])
    if not _jobs.empty():
        _ensure_worker()


def _calendar_hint(started: str) -> str:
    """Lịch Google/Lark trùng thời điểm ghi âm -> gợi ý tên cuộc họp, người dự."""
    try:
        from agents import calendar_agent
        t = dt.datetime.fromisoformat(started)
        if t.tzinfo is None:
            t = t.replace(tzinfo=calendar_agent.TZ)
        for e in calendar_agent.get_events(t.date()):
            if e.get("all_day") or e.get("source") == "system":
                continue
            if e["start"] - dt.timedelta(minutes=20) <= t <= e["end"]:
                return f"{e['title']} ({e['start']:%H:%M}-{e['end']:%H:%M})" + (f", mô tả: {e.get('desc', '')[:200]}" if e.get("desc") else "")
    except Exception:
        log.debug("calendar hint lỗi", exc_info=True)
    return ""


def create(src_path: str, source: str, title: str = "", hint: str = "", started: str = "", consent: dict | None = None) -> dict:
    """Nhận 1 file âm thanh (bất kỳ định dạng ffmpeg đọc được) -> tạo cuộc họp và xếp hàng xử lý.
    Bản của khách: phải mở ghi âm (recording_enabled) và có consent từ make_consent(); nếu không thì xoá file, báo lỗi."""
    if not recording_enabled() or (consent_required() and not (consent or {}).get("ok")):
        try:
            Path(src_path).unlink()
        except Exception:
            pass
        raise ValueError(RECORDING_CLOSED_TEXT if not recording_enabled() else "Cần xác nhận đồng ý ghi âm trước khi làm biên bản.")
    mid = dt.datetime.now().strftime("%y%m%d") + "-" + uuid.uuid4().hex[:5]
    d = _dir(mid)
    d.mkdir(parents=True, exist_ok=True)
    started = started or dt.datetime.now().isoformat(timespec="seconds")
    m = {"id": mid, "title": title or "", "hint": hint, "source": source, "created": dt.datetime.now().isoformat(timespec="seconds"),
         "started": started, "status": "queued", "step": "Đang xếp hàng", "progress": 0, "raw": str(src_path)}
    if consent:
        m["consent"] = {k: consent.get(k) for k in ("version", "at", "source")}
    save(m)
    _jobs.put(mid)
    _ensure_worker()
    return m


def _prepare(mid: str) -> dict:
    """Chuẩn hoá âm thanh gốc -> audio.mp3, đo thời lượng, tìm lịch trùng giờ. Xong thì xoá file gốc tạm."""
    from pathlib import Path
    m = load(mid)
    d = _dir(mid)
    if (d / "audio.mp3").exists() and m.get("duration"):
        return m
    patch(mid, step="Đang chuẩn hoá âm thanh", progress=1)
    raw = Path(m.get("raw") or "")
    normalize(raw, d / "audio.mp3")
    dur = _duration(d / "audio.mp3")
    if dur < 3:
        raise ValueError("File âm thanh quá ngắn hoặc không có tiếng.")
    if INBOX in raw.parents:
        try:
            raw.unlink()
        except Exception:
            pass
    return patch(mid, duration=round(dur, 1), calendar=_calendar_hint(m.get("started", "")))


def process(mid: str):
    m0 = load(mid) or {}
    if consent_required() and not (recording_enabled() and m0.get("consent")):
        # chốt chặn thứ hai: không gửi âm thanh ra ngoài khi thiếu log đồng ý (kể cả bản ghi tồn từ trước)
        patch(mid, status="error", err="Thiếu xác nhận đồng ý ghi âm nên không chép lời.", step="")
        return
    patch(mid, status="working", err="")
    m = _prepare(mid)
    m = patch(mid, step="Đang chép lời", progress=3)
    d = _dir(mid)
    audio = d / "audio.mp3"
    if not m.get("segments"):
        work = d / "chunks"
        work.mkdir(exist_ok=True)
        dur = m.get("duration") or _duration(audio)
        n = max(1, math.ceil(dur / CHUNK_SEC))
        segs, speakers = [], {}
        for k in range(n):
            a, b = k * CHUNK_SEC, min(dur, (k + 1) * CHUNK_SEC)
            patch(mid, step=f"Đang chép lời đoạn {k + 1}/{n}", progress=int(5 + 70 * k / n))
            segs += _transcribe_range(audio, work, a, b, k + 1, n, speakers)
        segs.sort(key=lambda x: x["s"])
        for i, s_ in enumerate(segs):
            s_["e"] = segs[i + 1]["s"] if i + 1 < len(segs) else dur
        shutil.rmtree(work, ignore_errors=True)
        m = patch(mid, segments=segs, speakers={k: {"name": v.get("name", ""), "voice": v.get("voice", "")} for k, v in speakers.items()})
    m = patch(mid, step="superHuy đang biên tập biên bản", progress=80)
    r = recap(m)
    spk = m.get("speakers") or {}
    for k, name in (r.pop("speakers", None) or {}).items():
        if name and k in spk and not spk[k].get("name"):
            spk[k]["name"] = name
    labels = r.pop("labels", {}) or {}
    if m.get("labels_locked"):
        labels = m.get("labels") or labels
    m = patch(mid, recap=r, labels=labels, speakers=spk, title=m.get("title") or r.get("title", ""), step="Đang lưu vào Obsidian", progress=93)
    _learn_taxonomy(labels, [v.get("name") for v in spk.values()])
    try:
        path = to_obsidian(m)
        m = patch(mid, obsidian=path)
    except Exception as e:
        log.exception("Ghi Obsidian lỗi")
        m = patch(mid, obsidian_err=str(e)[:200])
    m = patch(mid, status="done", step="", progress=100, done_at=dt.datetime.now().isoformat(timespec="seconds"))
    try:
        from config import OWNER_CHAT_ID
        from core import activation
        activation.first_result(OWNER_CHAT_ID, "bien_ban")
    except Exception:
        pass
    try:
        from core import notify
        org = ORGS.get(labels.get("org"), {}).get("name", "")
        txt = (f"🎙 Biên bản họp đã xong: {m['title']}\n{org}{' › ' + labels['project'] if labels.get('project') else ''} · {_fmt(m.get('duration', 0))}\n\n"
               f"{r.get('summary', '')}\n")
        if r.get("decisions"):
            txt += "\nQuyết định:\n" + "\n".join("• " + x["text"] for x in r["decisions"][:6])
        if r.get("next_steps"):
            txt += "\n\nViệc tiếp theo:\n" + "\n".join("• " + x["text"] + (f" ({x['owner']})" if x.get("owner") else "") for x in r["next_steps"][:8])
        txt += "\n\nMở app › Họp để nghe lại từng ý."
        notify.send(text=txt)
    except Exception:
        log.debug("notify lỗi", exc_info=True)


def reprocess(mid: str, what: str = "recap") -> dict:
    m = load(mid)
    if not m:
        raise ValueError("Không tìm thấy cuộc họp")
    if what == "all":
        patch(mid, segments=[], recap={})
    patch(mid, status="queued", step="Đang xếp hàng", progress=0, err="")
    _jobs.put(mid)
    _ensure_worker()
    return {"text": "Đang làm lại biên bản, xong sẽ báo anh."}


def rename_speaker(mid: str, spk: str, name: str) -> dict:
    with _lock:
        m = load(mid)
        m.setdefault("speakers", {}).setdefault(spk, {})["name"] = name.strip()
        save(m)
    _learn_taxonomy(m.get("labels") or {}, [name])
    if m.get("status") == "done":
        try:
            patch(mid, obsidian=to_obsidian(load(mid)))
        except Exception:
            log.exception("Ghi lại Obsidian lỗi")
    return {"text": f"Đã đổi {spk} thành {name}"}


def set_labels(mid: str, **kw) -> dict:
    with _lock:
        m = load(mid)
        lab = m.get("labels") or {}
        for k, v in kw.items():
            if v is not None:
                lab[k] = v
        m["labels"], m["labels_locked"] = lab, True
        save(m)
    _learn_taxonomy(lab, [])
    if m.get("status") == "done":
        patch(mid, obsidian=to_obsidian(load(mid)))
    return {"text": "Đã cập nhật phân loại và ghi lại vào Obsidian"}


def delete(mid: str) -> dict:
    trash = ROOT / "_trash"
    trash.mkdir(parents=True, exist_ok=True)
    src = _dir(mid)
    if src.exists():
        src.rename(trash / mid)  # chuyển vào thùng rác, không xoá hẳn
    return {"text": "Đã chuyển cuộc họp vào thùng rác"}


# ------------------------------------------------------------------ hỏi lại
def _tokens(s: str) -> list[str]:
    import unicodedata
    s = unicodedata.normalize("NFC", (s or "").lower())
    return [w for w in re.findall(r"\w+", s) if len(w) > 1]


def search(q: str, k: int = 30, mid: str = "") -> list[dict]:
    """BM25 đơn giản trên lời thoại (gom 3 lượt liền nhau) + recap của mọi cuộc họp."""
    qt = _tokens(q)
    if not qt:
        return []
    docs = []
    for m in ([load(mid)] if mid else all_meetings()):
        if not m or m.get("status") != "done":
            continue
        names = m.get("speakers") or {}
        segs = m.get("segments") or []
        for i in range(0, len(segs), 2):
            win = segs[i:i + 3]
            txt = " ".join(f"{names.get(s['spk'], {}).get('name') or s['spk']}: {s['text']}" for s in win)
            docs.append({"mid": m["id"], "title": m.get("title", ""), "date": (m.get("started") or "")[:10], "t": win[0]["s"], "text": txt})
        r = m.get("recap") or {}
        for key in ("decisions", "next_steps", "suggestions", "open_questions"):
            for x in r.get(key, []):
                docs.append({"mid": m["id"], "title": m.get("title", ""), "date": (m.get("started") or "")[:10], "t": x.get("t", 0),
                             "text": f"[{key}] {x.get('text', '')} {x.get('owner', '')}", "boost": 1.3})
        docs.append({"mid": m["id"], "title": m.get("title", ""), "date": (m.get("started") or "")[:10], "t": 0,
                     "text": f"[tóm tắt] {m.get('title', '')}. {r.get('summary', '')}", "boost": 1.5})
    if not docs:
        return []
    N = len(docs)
    toks = [_tokens(d["text"] + " " + d["title"]) for d in docs]
    avg = sum(len(t) for t in toks) / N
    df = {}
    for t in toks:
        for w in set(t):
            df[w] = df.get(w, 0) + 1
    scored = []
    for d, t in zip(docs, toks):
        tf = {}
        for w in t:
            tf[w] = tf.get(w, 0) + 1
        s = 0.0
        for w in qt:
            if w in tf:
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf[w] * 2.2 / (tf[w] + 1.2 * (0.25 + 0.75 * len(t) / avg))
        if s > 0:
            scored.append((s * d.get("boost", 1), d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:k]]


ASK = """Bạn là superHuy, trả lời câu hỏi của anh Huy dựa trên KHO BIÊN BẢN CUỘC HỌP bên dưới.
Trả lời XÚC TÍCH (2-5 câu hoặc vài gạch đầu dòng), đúng trọng tâm. Chỉ dùng thông tin trong nguồn; không có thì nói rõ là chưa thấy trong các cuộc họp đã lưu.
Sau mỗi ý, gắn nguồn dạng [n] theo số thứ tự nguồn. Hôm nay: {today}.
CÂU HỎI: {q}
NGUỒN:
{src}
Trả về DUY NHẤT JSON: {{"answer": "...", "used": [số thứ tự nguồn đã dùng]}}"""


def ask(question: str, meeting_id: str = "") -> dict:
    hits = search(question, 28, meeting_id)
    if not hits:
        latest = [m for m in all_meetings() if m.get("status") == "done"][:6]
        hits = [{"mid": m["id"], "title": m.get("title", ""), "date": (m.get("started") or "")[:10], "t": 0,
                 "text": "[tóm tắt] " + (m.get("recap") or {}).get("summary", "")} for m in latest]
    if not hits:
        return {"text": "Chưa có cuộc họp nào trong kho. Anh ghi âm hoặc tải file họp lên trang Họp nhé.", "sources": []}
    src = "\n".join(f"[{i + 1}] ({h['date']} · {h['title']} · {_fmt(h['t'])}) {h['text'][:600]}" for i, h in enumerate(hits))
    res = ask_json(ASK.format(today=dt.date.today().isoformat(), q=question, src=src), 2500, 2,
                   ok=lambda x: isinstance(x, dict) and x.get("answer"), tag="meeting-ask") or {}
    used = []
    for n in res.get("used") or []:
        try:
            h = hits[int(n) - 1]
            used.append({"n": int(n), "mid": h["mid"], "title": h["title"], "date": h["date"], "t": h["t"], "at": _fmt(h["t"])})
        except Exception:
            continue
    ans = res.get("answer") or "superHuy chưa trả lời được, anh hỏi lại giúp em."
    text = ans + ("\n\nNguồn: " + "; ".join(f"[{u['n']}] {u['title']} {u['date']} @{u['at']}" for u in used) if used else "")
    return {"text": text, "answer": ans, "sources": used}


# ------------------------------------------------------------------ xem
def view_list() -> dict:
    rows = []
    for m in all_meetings()[:80]:
        r, lab = m.get("recap") or {}, m.get("labels") or {}
        rows.append({k: m.get(k) for k in ("id", "title", "status", "step", "progress", "err", "source", "started", "duration")}
                    | {"title": m.get("title") or r.get("title", ""), "org": lab.get("org", ""), "project": lab.get("project", ""), "department": lab.get("department", ""),
                       "type": lab.get("type", ""), "summary": r.get("summary", ""), "n_next": len(r.get("next_steps") or []),
                       "n_dec": len(r.get("decisions") or [])})
    return {"items": rows, "orgs": ORGS, "taxonomy": taxonomy()}


def view(mid: str) -> dict:
    m = load(mid)
    if not m:
        raise ValueError("Không tìm thấy cuộc họp")
    m = dict(m)
    m["title"] = m.get("title") or (m.get("recap") or {}).get("title", "")
    m["audio"] = str(_dir(mid) / "audio.mp3")
    m["obsidian_rel"] = str(m.get("obsidian", "")).replace(str(OBSIDIAN_VAULT), "").lstrip("/")
    return m


# ------------------------------------------------------------------ tự kiểm tra
DEMO = [
    ("NamMinh", "Chào cả nhà, hôm nay mình họp nhanh về dự án AI Agent Factory của Sellnity. Lan cập nhật tiến độ giúp anh nhé."),
    ("HoaiMy", "Dạ anh Huy, tuần này team đã AI hoá xong ba quy trình: tạo mô tả sản phẩm, trả lời ticket khách hàng và báo cáo quảng cáo hằng ngày."),
    ("HoaiMy", "Riêng quy trình báo cáo quảng cáo giúp tiết kiệm khoảng mười hai giờ mỗi tuần cho team marketing."),
    ("NamMinh", "Tốt. Còn vướng mắc gì không em?"),
    ("HoaiMy", "Vướng nhất là dữ liệu đơn hàng Etsy chưa đồng bộ tự động, nên agent báo cáo vẫn phải chờ người xuất file."),
    ("NamMinh", "Vậy mình chốt: tuần sau ưu tiên kết nối API Etsy. Lan phụ trách, hạn chót thứ Sáu này. Anh sẽ duyệt ngân sách năm trăm đô cho công cụ đồng bộ."),
    ("HoaiMy", "Dạ em nhận. Còn việc tuyển thêm một kỹ sư AI thì anh tính sao ạ?"),
    ("NamMinh", "Cái đó để anh bàn thêm với ban lãnh đạo, tuần sau trả lời em."),
]


def _demo_audio():
    from agents.reel_video import _tts
    work = ROOT / "_selftest"
    work.mkdir(parents=True, exist_ok=True)
    out = work / "demo.wav"
    if out.exists() and out.stat().st_size > 10000:
        return work, out
    parts = []
    for i, (voice, text) in enumerate(DEMO):
        w = str(work / f"p{i}.wav")
        _tts(text, w, voice, "+0%")
        parts.append(w)
    lst = work / "list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    subprocess.run([_ff(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], capture_output=True)
    return work, out


def selftest_http(port: int, repeat: int = 11, wait: int = 900) -> dict:
    """Kiểm tra đầu-cuối đúng đường đi của Mini App: âm thanh dạng webm/opus (như ghi âm trong app), dài > 1 đoạn chép lời,
    tải lên theo phần qua /api/upload -> /api/run hop.tao -> chờ xong -> hop.xem -> phát lại /media (Range) -> hop.hoi."""
    import urllib.request
    from webapp import server as srv
    work, demo = _demo_audio()
    longf = work / "long.webm"
    subprocess.run([_ff(), "-y", "-stream_loop", str(repeat - 1), "-i", str(demo), "-c:a", "libopus", "-b:a", "32k", "-ac", "1", str(longf)],
                   capture_output=True)
    if not longf.exists() or longf.stat().st_size < 10000:  # ffmpeg không có opus -> dùng m4a (như iPhone ghi)
        longf = work / "long.m4a"
        subprocess.run([_ff(), "-y", "-stream_loop", str(repeat - 1), "-i", str(demo), "-c:a", "aac", "-b:a", "48k", "-ac", "1", str(longf)],
                       capture_output=True)
    tok = srv.make_session(srv.OWNER_CHAT_ID)
    base = f"http://127.0.0.1:{port}"

    def call(path, data=None, raw=None, headers=None):
        h = {"X-Session": tok, **(headers or {})}
        body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
        if data is not None:
            h["Content-Type"] = "application/json"
        req = urllib.request.Request(base + path, data=body, headers=h, method="POST" if body is not None else "GET")
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(), dict(r.headers)
    try:
        blob = longf.read_bytes()
        uid, CH = "e2e" + uuid.uuid4().hex[:8], 1_500_000  # phần nhỏ để thử ghép nhiều phần
        for i in range(0, len(blob), CH):
            st, b, _ = call(f"/api/upload?id={uid}&seq={i // CH}", raw=blob[i:i + CH], headers={"Content-Type": "application/octet-stream"})
            assert json.loads(b).get("ok"), b[:200]
        _, b, _ = call("/api/run", {"agent": "hop", "action": "tao", "params": {"upload_id": uid, "name": longf.name, "source": "Kiểm tra đầu-cuối",
                                                                                "hint": "Cuộc họp DEMO kiểm tra hệ thống, Sellnity"}})
        res = json.loads(b)
        assert "result" in res, res
        mid = res["result"]["id"]
        t0 = time.time()
        while time.time() - t0 < wait:
            m = load(mid)
            if m.get("status") in ("done", "error"):
                break
            time.sleep(8)
        m = load(mid)
        assert m.get("status") == "done", m.get("err") or m.get("step")
        _, b, _ = call("/api/run", {"agent": "hop", "action": "xem", "params": {"id": mid}})
        v = json.loads(b)["result"]
        segs = v.get("segments") or []
        spk = {s["spk"] for s in segs}
        st, b, hd = call(v["audio"], headers={"Range": "bytes=0-1023"})
        _, b2, _ = call("/api/run", {"agent": "hop", "action": "hoi", "params": {"question": "Ngân sách cho công cụ đồng bộ là bao nhiêu?", "meeting_id": mid}})
        ans = json.loads(b2)["result"]
        _, page, _ = call("/")
        return {"id": mid, "duration": round(m.get("duration", 0)), "segments": len(segs), "last_t": round(segs[-1]["s"]) if segs else 0,
                "speakers": sorted(spk), "audio_status": st, "audio_type": hd.get("Content-Type"),
                "answer": ans.get("answer", "")[:140], "sources": len(ans.get("sources") or []), "ui_has_meet": b"function vMeet" in page,
                "obsidian": bool(m.get("obsidian"))}
    finally:
        srv.SESSIONS.pop(tok, None)


def selftest(wait: int = 600) -> dict:
    """Tạo 1 đoạn hội thoại 2 giọng (tiếng Việt) rồi chạy cả quy trình; trả về kết quả rút gọn."""
    work, out = _demo_audio()
    keep = INBOX / f"selftest-{uuid.uuid4().hex[:6]}.wav"
    INBOX.mkdir(parents=True, exist_ok=True)
    shutil.copy2(out, keep)
    m = create(str(keep), "tự kiểm tra", hint="Cuộc họp thử nghiệm của Sellnity, dự án AI Agent Factory")
    t0 = time.time()
    while time.time() - t0 < wait:
        cur = load(m["id"])
        if cur.get("status") in ("done", "error"):
            break
        time.sleep(5)
    cur = load(m["id"])
    if cur.get("status") != "done":
        raise RuntimeError(cur.get("err") or f"Chưa xong sau {wait}s: {cur.get('step')}")
    r = cur.get("recap") or {}
    return {"id": m["id"], "segments": len(cur.get("segments") or []), "speakers": len(cur.get("speakers") or {}),
            "decisions": len(r.get("decisions") or []), "next_steps": len(r.get("next_steps") or []),
            "org": (cur.get("labels") or {}).get("org"), "obsidian": bool(cur.get("obsidian"))}
