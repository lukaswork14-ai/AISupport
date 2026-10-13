"""Chia sẻ biên bản cuộc họp ra ngoài: trang web tạm (landing page có dòng thời gian + sơ đồ ý chính), tin nhắn chat, email, Lark.

- Mỗi lần chia sẻ tạo 1 liên kết bí mật /s/<mã> (khó đoán), có hạn dùng, thu hồi được bất cứ lúc nào.
- Trang chia sẻ là BẢN CHỤP lúc tạo link, chỉ gồm các phần anh chọn (mặc định không có lời thoại, âm thanh, đề xuất nội bộ của superHuy).
- Không cần đăng nhập để xem; trang có noindex, không gửi referrer.
"""
import datetime as dt
import html
import json
import re
import secrets
import threading
import time

from config import DATA_DIR

FILE = DATA_DIR / "meetings" / "shares.json"
PARTS = {"summary": "Tóm tắt", "decisions": "Quyết định", "next_steps": "Ai làm gì", "mindmap": "Sơ đồ ý chính",
         "sections": "Diễn biến", "open_questions": "Còn bỏ ngỏ", "suggestions": "Đề xuất của superHuy",
         "transcript": "Lời thoại đầy đủ", "audio": "Âm thanh cuộc họp"}
DEFAULT_PARTS = ["summary", "decisions", "next_steps", "mindmap", "sections", "open_questions"]
_lock = threading.Lock()


def _load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def base_url() -> str:
    from agents import lark_oauth
    return lark_oauth.base_url()


def url(token: str) -> str:
    return f"{base_url()}/s/{token}"


def _parts(parts) -> list[str]:
    if isinstance(parts, str):
        parts = [p.strip() for p in re.split(r"[,;\s]+", parts) if p.strip()]
    parts = [p for p in (parts or DEFAULT_PARTS) if p in PARTS]
    return parts or list(DEFAULT_PARTS)


def _snapshot(m: dict, parts: list[str]) -> dict:
    from agents import meeting
    r, lab = m.get("recap") or {}, m.get("labels") or {}
    org = meeting.ORGS.get(lab.get("org"), {"name": "", "role": ""})
    names = m.get("speakers") or {}
    snap = {"title": r.get("title") or m.get("title") or "Cuộc họp", "started": m.get("started") or m.get("created", ""),
            "duration": m.get("duration", 0), "org": org.get("name", ""), "project": lab.get("project", ""),
            "department": lab.get("department", ""), "type": lab.get("type", ""),
            "people": sorted({(v.get("name") or "").strip() for v in names.values() if (v.get("name") or "").strip()})}
    for p in ("summary", "decisions", "next_steps", "mindmap", "sections", "open_questions", "suggestions"):
        if p in parts and r.get(p):
            snap[p] = r[p]
    if "sections" not in snap and r.get("sections"):  # dòng thời gian luôn có (chỉ tên chủ đề + mốc giờ)
        snap["timeline"] = [{"title": s.get("title", ""), "t": s.get("t", 0)} for s in r["sections"]]
    if "transcript" in parts:
        snap["transcript"] = [{"s": s["s"], "who": (names.get(s["spk"]) or {}).get("name") or s["spk"], "text": s["text"]}
                              for s in m.get("segments") or []]
    return snap


def create(mid: str, parts=None, days: int = 14, note: str = "") -> dict:
    from agents import meeting
    m = meeting.load(mid)
    if not m or m.get("status") != "done":
        raise ValueError("Cuộc họp chưa có biên bản để chia sẻ")
    parts = _parts(parts)
    days = max(1, min(int(days or 14), 90))
    tok = secrets.token_urlsafe(12)
    rec = {"token": tok, "mid": mid, "parts": parts, "note": (note or "").strip()[:600], "created": time.time(),
           "expires": time.time() + days * 86400, "views": 0, "revoked": False, "snap": _snapshot(m, parts)}
    with _lock:
        d = _load()
        d[tok] = rec
        _save(d)
    return {"token": tok, "url": url(tok), "expires": _date(rec["expires"]), "parts": parts,
            "text": f"Đã tạo trang chia sẻ (hết hạn {_date(rec['expires'])}): {url(tok)}"}


def _date(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).strftime("%d/%m/%Y")


def _active(rec: dict | None) -> bool:
    return bool(rec) and not rec.get("revoked") and rec.get("expires", 0) > time.time()


def get(token: str) -> dict | None:
    rec = _load().get(token or "")
    return rec if _active(rec) else None


def list_for(mid: str) -> dict:
    out = []
    for rec in sorted(_load().values(), key=lambda r: -r["created"]):
        if rec["mid"] != mid:
            continue
        out.append({"token": rec["token"], "url": url(rec["token"]), "parts": rec["parts"], "views": rec.get("views", 0),
                    "created": _date(rec["created"]), "expires": _date(rec["expires"]), "active": _active(rec),
                    "revoked": rec.get("revoked", False), "sent": rec.get("sent", [])})
    return {"items": out, "parts": PARTS, "default": DEFAULT_PARTS}


def revoke(token: str) -> dict:
    with _lock:
        d = _load()
        if token not in d:
            raise ValueError("Không tìm thấy liên kết")
        d[token]["revoked"] = True
        _save(d)
    return {"text": "Đã thu hồi liên kết, người khác không mở được nữa."}


def _mark_sent(token: str, how: str):
    with _lock:
        d = _load()
        if token in d:
            d[token].setdefault("sent", []).append(f"{how} {dt.datetime.now():%H:%M %d/%m}")
            _save(d)


def hit(token: str):
    with _lock:
        d = _load()
        if token in d:
            d[token]["views"] = d[token].get("views", 0) + 1
            d[token]["last_view"] = time.time()
            _save(d)


# ------------------------------------------------------------------ văn bản cho chat / email
def _fmt(sec) -> str:
    sec = int(sec or 0)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60:02d}:{sec % 60:02d}"


def _when(snap: dict) -> str:
    try:
        d = dt.datetime.fromisoformat(snap["started"][:19])
        return f"{d:%H:%M} ngày {d:%d/%m/%Y}"
    except Exception:
        return ""


def _due(s: str) -> str:
    try:
        return dt.date.fromisoformat(s).strftime("%d/%m")
    except Exception:
        return s or ""


def message(snap: dict, link: str = "", note: str = "") -> str:
    """Bản tin nhắn văn bản thuần (Telegram, Zalo, Lark, Messenger đều hiển thị đúng)."""
    out = [f"📋 Biên bản họp: {snap['title']}", f"🕘 {_when(snap)} · {round((snap.get('duration') or 0) / 60)} phút"]
    if note:
        out += ["", note]
    if snap.get("summary"):
        out += ["", snap["summary"]]
    if snap.get("decisions"):
        out += ["", "✅ Đã chốt:"] + [f"• {d['text']}" + (f" ({d['owner']})" if d.get("owner") else "") for d in snap["decisions"]]
    if snap.get("next_steps"):
        out += ["", "👉 Ai làm gì:"] + [f"• {s.get('owner') or 'Chưa giao'}: {s['text']}" + (f" (hạn {_due(s['due'])})" if s.get("due") else "")
                                       for s in snap["next_steps"]]
    if snap.get("open_questions"):
        out += ["", "❓ Còn bỏ ngỏ:"] + [f"• {q['text']}" for q in snap["open_questions"]]
    if link:
        out += ["", f"🔗 Xem đầy đủ (sơ đồ, dòng thời gian): {link}"]
    return "\n".join(out)


def share_text(mid: str, parts=None, days: int = 14, note: str = "") -> dict:
    r = create(mid, parts, days, note)
    rec = _load()[r["token"]]
    return {**r, "message": message(rec["snap"], r["url"], rec.get("note", "")), "text": message(rec["snap"], r["url"], rec.get("note", ""))}


def send_email(mid: str, to: str, parts=None, days: int = 14, note: str = "", platform: str = "gmail", cc: str = "") -> dict:
    from agents import mailbox
    r = create(mid, parts, days, note)
    rec = _load()[r["token"]]
    snap = rec["snap"]
    sent = mailbox.send(platform, to, f"Biên bản họp: {snap['title']}", message(snap, r["url"], rec.get("note", "")), cc=cc,
                        html=email_html(snap, r["url"], rec.get("note", "")))
    _mark_sent(r["token"], f"email {sent}")
    return {**r, "text": f"Đã gửi biên bản tới {sent}. Liên kết xem đầy đủ: {r['url']}"}


def send_lark(mid: str, chat_id: str, parts=None, days: int = 14, note: str = "") -> dict:
    from agents import lark_agent
    r = create(mid, parts, days, note)
    rec = _load()[r["token"]]
    name = lark_agent.send_text(chat_id, message(rec["snap"], r["url"], rec.get("note", "")))
    _mark_sent(r["token"], f"Lark {name}")
    return {**r, "text": f"Đã gửi biên bản vào nhóm Lark {name}."}


def mark(token: str, how: str) -> dict:
    _mark_sent(token, how)
    return {"ok": True}


# ------------------------------------------------------------------ HTML
E = html.escape


def _tc(t, audio: bool) -> str:
    if t is None or t == "":
        return ""
    if audio:
        return f'<button class="tc" data-t="{float(t):.0f}" aria-label="Nghe từ {_fmt(t)}">▶ {_fmt(t)}</button>'
    return f'<span class="tc">{_fmt(t)}</span>'


def _wrap(s: str, n: int = 20) -> list[str]:
    out, cur = [], ""
    for w in str(s or "").split():
        if len((cur + " " + w).strip()) > n:
            if cur:
                out.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        out.append(cur)
    if len(out) > 3:
        out = out[:3]
        out[2] = out[2][:n - 1] + "…"
    return out or ["…"]


def mindmap_svg(mm: dict, title: str, audio: bool = False) -> str:
    """Cây ngang: gốc bên trái, nhánh, rồi ý. Vẽ sẵn phía máy chủ (không cần thư viện)."""
    COLW, NW, LH, PAD, GAP = 196, 172, 17, 10, 10
    nodes, links, y = [], [], [0.0]

    def place(n, depth):
        t = n.get("t") if depth else None
        lines = _wrap(n.get("label") or "", 20 if depth else 18)
        h = (len(lines) + (1 if t not in (None, "") else 0)) * LH + PAD * 2
        node = {"lines": lines, "h": h, "d": depth, "t": t, "x": depth * COLW}
        kids = [k for k in (n.get("children") or [])[:8] if isinstance(k, dict)]
        if not kids or depth >= 3:
            node["y"] = y[0]
            y[0] += h + GAP
        else:
            ch = [place(k, depth + 1) for k in kids]
            node["y"] = (ch[0]["y"] + ch[-1]["y"] + ch[-1]["h"]) / 2 - h / 2
            links.extend((node, c) for c in ch)
        nodes.append(node)
        return node

    place({"label": mm.get("label") or title, "children": mm.get("children") or []}, 0)
    W = (max(n["d"] for n in nodes) + 1) * COLW - (COLW - NW)
    H = max(y[0] - GAP, max(n["y"] + n["h"] for n in nodes))
    parts = [f'<svg class="mm" viewBox="0 0 {W} {H:.0f}" width="{W}" height="{H:.0f}" role="img" aria-label="Sơ đồ ý chính cuộc họp">']
    for a, b in links:
        x1, y1, x2, y2 = a["x"] + NW, a["y"] + a["h"] / 2, b["x"], b["y"] + b["h"] / 2
        mx = (x1 + x2) / 2
        parts.append(f'<path class="ml" d="M{x1:.0f} {y1:.0f} C{mx:.0f} {y1:.0f} {mx:.0f} {y2:.0f} {x2:.0f} {y2:.0f}"/>')
    for n in nodes:
        has_t = n["t"] not in (None, "") and n["d"]
        attr = f' data-t="{float(n["t"]):.0f}" tabindex="0" role="button"' if has_t and audio else ""
        parts.append(f'<g class="mn d{min(n["d"], 2)}{" go" if attr else ""}" transform="translate({n["x"]},{n["y"]:.0f})"{attr}>'
                     f'<rect width="{NW}" height="{n["h"]}" rx="12"/>')
        for i, ln in enumerate(n["lines"]):
            parts.append(f'<text x="12" y="{PAD + LH * (i + 1) - 4}">{E(ln)}</text>')
        if has_t:
            parts.append(f'<text class="mt" x="12" y="{PAD + LH * (len(n["lines"]) + 1) - 3}">{"▶ " if audio else ""}{_fmt(n["t"])}</text>')
        parts.append("</g>")
    parts.append("</svg>")
    return "".join(parts)


CSS = """
:root{--bg:#F6F3F9;--paper:#FFFFFF;--ink:#1B1724;--soft:#5E5670;--mute:#8A8299;--line:#E6E0EE;--plum:#A2338C;--violet:#6E4FE0;
--dec:#13805F;--dec-bg:#E7F5EF;--todo:#2563C9;--todo-bg:#EAF1FC;--open:#9A6A00;--open-bg:#FBF3E1;--sgt:#7A3FD0;--sgt-bg:#F1EAFB;
--s0:#6E4FE0;--s1:#C13F96;--s2:#13805F;--s3:#D06A1F;--s4:#2563C9;--s5:#9A6A00}
@media (prefers-color-scheme:dark){:root{--bg:#141019;--paper:#1D1825;--ink:#F3EFF8;--soft:#C3BAD2;--mute:#958CA6;--line:#2E2739;--plum:#EA7CC8;--violet:#A994FF;
--dec:#4FD1A5;--dec-bg:#12271F;--todo:#7EAEFF;--todo-bg:#152238;--open:#F2C14E;--open-bg:#2A2312;--sgt:#C2A3FF;--sgt-bg:#231A33}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 "Be Vietnam Pro",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:28px 16px 64px}
.brand{display:flex;align-items:center;gap:10px;color:var(--soft);font-size:14px;font-weight:500}
.orb{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,#7B5CF0,#C13F96);box-shadow:0 0 0 4px color-mix(in srgb,#A2338C 14%,transparent)}
h1{font-size:clamp(28px,6vw,44px);line-height:1.12;letter-spacing:-.02em;margin:22px 0 14px;font-weight:700;text-wrap:balance}
.pills{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 6px}
.pill{border:1px solid var(--line);background:var(--paper);border-radius:999px;padding:4px 12px;font-size:13.5px;color:var(--soft)}
.pill b{color:var(--ink);font-weight:600}
.note{margin:18px 0 0;padding:14px 16px;border-left:3px solid var(--plum);background:var(--paper);border-radius:0 12px 12px 0;color:var(--soft)}
.strip{margin:26px 0 8px}
.bar{display:flex;gap:3px;height:46px;border-radius:12px;overflow:hidden}
.bar>*{flex:1;min-width:10px;background:var(--c);color:#fff;border:0;padding:0 8px;font-family:inherit;font-size:12.5px;font-weight:600;line-height:46px;text-align:left;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;cursor:default}
.bar>button{cursor:pointer}.bar>button:hover{filter:brightness(1.08)}
.axis{display:flex;justify-content:space-between;color:var(--mute);font-size:12px;margin-top:6px}
.legend{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:4px 16px;margin:10px 0 0;padding:0;list-style:none;font-size:14px;color:var(--soft)}
.legend li{display:flex;gap:8px;align-items:baseline}.legend i{width:10px;height:10px;border-radius:3px;background:var(--c);flex:none;transform:translateY(1px)}
section{margin-top:40px}
h2{font-size:20px;letter-spacing:-.01em;margin:0 0 14px;display:flex;align-items:center;gap:10px}
h2 .n{font-size:13px;font-weight:600;color:var(--mute)}
.lead{font-size:18px;line-height:1.65;margin:0}
.card{background:var(--paper);border:1px solid var(--line);border-radius:16px}
ul.items{list-style:none;margin:0;padding:6px 0}
ul.items li{display:flex;gap:12px;align-items:flex-start;padding:12px 18px;border-top:1px solid var(--line)}
ul.items li:first-child{border-top:0}
.mk{flex:none;width:24px;height:24px;border-radius:8px;display:grid;place-items:center;font-size:13px;font-weight:700;margin-top:1px;background:var(--k-bg);color:var(--k)}
.dec{--k:var(--dec);--k-bg:var(--dec-bg)}.open{--k:var(--open);--k-bg:var(--open-bg)}.sgt{--k:var(--sgt);--k-bg:var(--sgt-bg)}
.grow{flex:1;min-width:0}.who{font-size:13.5px;color:var(--mute)}
.tc{flex:none;align-self:flex-start;font-family:inherit;font-size:12px;font-weight:500;line-height:1;color:var(--mute);margin-top:5px;white-space:nowrap;font-variant-numeric:tabular-nums}
button.tc{cursor:pointer;color:var(--plum);font-weight:600;background:color-mix(in srgb,var(--plum) 10%,transparent);border:0;border-radius:999px;padding:6px 9px;margin-top:0}
.owners{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(260px,1fr))}
.owner{padding:14px 16px}.owner h3{margin:0 0 6px;font-size:15px;display:flex;gap:8px;align-items:center}
.av{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:var(--todo-bg);color:var(--todo);font-size:13px;font-weight:700}
.owner ul{margin:0;padding:0;list-style:none}.owner li{padding:9px 0;border-top:1px dashed var(--line)}
.owner li:first-child{border-top:0}.owner .meta{display:flex;gap:10px;align-items:center;margin-top:4px}.owner .meta .tc{margin:0}
.due{font-size:12.5px;font-weight:600;color:var(--todo);white-space:nowrap}
.mmwrap{overflow-x:auto;padding:16px;-webkit-overflow-scrolling:touch}
svg.mm{display:block;max-width:none}
.ml{fill:none;stroke:color-mix(in srgb,var(--violet) 45%,transparent);stroke-width:1.6}
.mn rect{fill:var(--paper);stroke:var(--line)}.mn text{fill:var(--ink);font:13px "Be Vietnam Pro",sans-serif}
.mn.d0 rect{fill:var(--violet);stroke:none}.mn.d0 text{fill:#fff;font-weight:700;font-size:14px}
.mn.d1 rect{fill:color-mix(in srgb,var(--violet) 12%,var(--paper));stroke:color-mix(in srgb,var(--violet) 35%,transparent)}.mn.d1 text{font-weight:600}
.mn text.mt{fill:var(--plum);font-size:11px;font-weight:600}.mn.go{cursor:pointer}.mn.go:hover rect{stroke:var(--plum)}
.flow{padding:16px 18px;margin-bottom:10px}.flow h3{margin:0 0 4px;font-size:16px;display:flex;gap:10px;align-items:center}
.flow ul{margin:0;padding-left:18px;color:var(--soft)}.flow li{margin:4px 0}
details{margin-top:12px}summary{cursor:pointer;font-weight:600;padding:12px 0}
.tx p{margin:0;padding:8px 0;border-top:1px solid var(--line);display:grid;grid-template-columns:64px 1fr;gap:8px;font-size:15px}
.tx b{display:block;font-size:13px;color:var(--soft)}
.player{position:sticky;bottom:12px;margin-top:28px;padding:10px 12px;display:flex;gap:10px;align-items:center;box-shadow:0 8px 30px rgba(40,20,70,.12)}
.player audio{width:100%}
footer{margin-top:56px;color:var(--mute);font-size:13.5px;border-top:1px solid var(--line);padding-top:18px}
.dead{max-width:520px;margin:18vh auto;padding:0 16px;text-align:center}
:focus-visible{outline:2px solid var(--plum);outline-offset:2px}
@media print{.player,button.tc{display:none}body{background:#fff}.card{break-inside:avoid}}
"""

JS = """document.addEventListener('click',e=>{const b=e.target.closest('[data-t]');const a=document.getElementById('au');if(!b||!a)return;
a.currentTime=Math.max(0,+b.dataset.t-1);a.play().catch(()=>{});});
document.addEventListener('keydown',e=>{if(e.key==='Enter'&&e.target.matches('g[data-t]'))e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));});"""

HEAD = ('<!doctype html><html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer">'
        '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap" rel="stylesheet">')


def dead_page() -> str:
    return (HEAD + f"<title>Liên kết không còn hiệu lực</title><style>{CSS}</style></head><body><div class='dead'>"
            "<div class='brand' style='justify-content:center'><span class='orb'></span>superHuy</div>"
            "<h1 style='font-size:28px'>Liên kết này đã hết hạn hoặc bị thu hồi</h1>"
            "<p style='color:var(--soft)'>Anh/chị liên hệ người đã gửi để nhận liên kết mới.</p></div></body></html>")


def render(rec: dict) -> str:
    s, audio = rec["snap"], "audio" in rec["parts"]
    dur = float(s.get("duration") or 0) or 1.0
    try:
        d = dt.datetime.fromisoformat(s["started"][:19])
        day = f"{d.day} tháng {d.month}, {d.year}"
        hour = f"{d:%H:%M}"
    except Exception:
        day, hour = "", ""
    pills = [f'<span class="pill"><b>{E(day)}</b>{" lúc " + hour if hour else ""}</span>' if day else "",
             f'<span class="pill"><b>{max(1, round(dur / 60))}</b> phút</span>']
    if s.get("org"):
        pills.append(f'<span class="pill"><b>{E(s["org"])}</b>{" / " + E(s["project"]) if s.get("project") else ""}</span>')
    if s.get("type"):
        pills.append(f'<span class="pill">{E(s["type"])}</span>')
    if s.get("people"):
        pills.append(f'<span class="pill">{len(s["people"])} người: {E(", ".join(s["people"][:6]))}</span>')
    body = [f'<header><div class="brand"><span class="orb"></span>Biên bản họp do superHuy soạn</div><h1>{E(s["title"])}</h1>'
            f'<div class="pills">{"".join(pills)}</div>']
    if rec.get("note"):
        body.append(f'<p class="note">{E(rec["note"])}</p>')
    body.append("</header>")
    # dòng thời gian cuộc họp (dải tỉ lệ theo thời lượng từng chủ đề)
    secs = s.get("sections") or s.get("timeline") or []
    if secs:
        cells, legend = [], []
        for i, x in enumerate(secs):
            t0 = float(x.get("t") or 0)
            t1 = float(secs[i + 1].get("t") or dur) if i + 1 < len(secs) else dur
            c = f"var(--s{i % 6})"
            tag = "button" if audio else "div"
            extra = f' data-t="{t0:.0f}" aria-label="Nghe đoạn {E(x.get("title", ""))}"' if audio else ""
            cells.append(f'<{tag} style="flex:{max(0.04, (t1 - t0) / dur):.3f};--c:{c}" title="{E(x.get("title", ""))} · {_fmt(t0)}"{extra}>{E(x.get("title", ""))}</{tag}>')
            legend.append(f'<li style="--c:{c}"><i></i><span class="grow">{E(x.get("title", ""))}</span><span>{_fmt(t0)}</span></li>')
        body.append(f'<div class="strip" aria-label="Dòng thời gian cuộc họp"><div class="bar">{"".join(cells)}</div>'
                     f'<div class="axis"><span>00:00</span><span>{_fmt(dur)}</span></div><ul class="legend">{"".join(legend)}</ul></div>')
    if s.get("summary"):
        body.append(f'<section><h2>Tóm tắt</h2><p class="lead">{E(s["summary"])}</p></section>')

    def items(arr, cls, mark):
        lis = "".join(f'<li><span class="mk {cls}">{mark}</span><div class="grow">{E(x.get("text", ""))}'
                      f'{"<div class=who>" + E(x["owner"]) + "</div>" if x.get("owner") else ""}</div>{_tc(x.get("t"), audio)}</li>' for x in arr)
        return f'<ul class="items card">{lis}</ul>'

    if s.get("decisions"):
        body.append(f'<section><h2>Đã chốt <span class="n">{len(s["decisions"])}</span></h2>{items(s["decisions"], "dec", "✓")}</section>')
    if s.get("next_steps"):
        by: dict[str, list] = {}
        for x in s["next_steps"]:
            by.setdefault((x.get("owner") or "").strip() or "Chưa giao", []).append(x)
        cards = []
        for who, arr in sorted(by.items(), key=lambda kv: (kv[0] == "Chưa giao", kv[0])):
            lis = "".join(f'<li><div>{E(x.get("text", ""))}</div><div class="meta">'
                          f'{"<span class=due>Hạn " + E(_due(x["due"])) + "</span>" if x.get("due") else ""}{_tc(x.get("t"), audio)}</div></li>' for x in arr)
            cards.append(f'<div class="card owner"><h3><span class="av">{E(who[:1].upper())}</span>{E(who)}</h3><ul>{lis}</ul></div>')
        body.append(f'<section><h2>Ai làm gì <span class="n">{len(s["next_steps"])} việc</span></h2><div class="owners">{"".join(cards)}</div></section>')
    if s.get("open_questions"):
        body.append(f'<section><h2>Còn bỏ ngỏ</h2>{items(s["open_questions"], "open", "?")}</section>')
    if s.get("suggestions"):
        body.append(f'<section><h2>Đề xuất của superHuy</h2>{items(s["suggestions"], "sgt", "✦")}</section>')
    mm = s.get("mindmap") or {}
    if mm.get("children"):
        body.append(f'<section><h2>Sơ đồ ý chính</h2><div class="card mmwrap">{mindmap_svg(mm, s["title"], audio)}</div></section>')
    if s.get("sections"):
        flows = "".join(f'<div class="card flow"><h3><span class="grow">{E(x.get("title", ""))}</span>{_tc(x.get("t"), audio)}</h3>'
                        f'<ul>{"".join("<li>" + E(p.get("text", "")) + "</li>" for p in x.get("points") or [])}</ul></div>' for x in s["sections"])
        body.append(f'<section><h2>Diễn biến</h2>{flows}</section>')
    if s.get("transcript"):
        lines = "".join(f'<p><span>{_tc(x["s"], audio)}</span><span><b>{E(x["who"])}</b>{E(x["text"])}</span></p>' for x in s["transcript"])
        body.append(f'<section><details><summary>Lời thoại đầy đủ ({len(s["transcript"])} đoạn)</summary><div class="tx">{lines}</div></details></section>')
    if audio:
        body.append(f'<div class="card player"><audio id="au" controls preload="none" src="/s/{rec["token"]}/audio"></audio></div>')
    body.append(f'<footer>superHuy soạn biên bản này từ ghi âm cuộc họp. Liên kết riêng, có hiệu lực tới {_date(rec["expires"])}; '
                f'vui lòng không chia sẻ tiếp nếu chưa được phép.</footer>')
    desc = (s.get("summary") or "")[:200]
    return (HEAD + f'<title>{E(s["title"])}</title><meta property="og:title" content="Biên bản họp: {E(s["title"])}">'
            f'<meta property="og:description" content="{E(desc)}"><meta name="description" content="{E(desc)}">'
            f'<style>{CSS}</style></head><body><main class="wrap">{"".join(body)}</main><script>{JS}</script></body></html>')


def email_html(snap: dict, link: str, note: str = "") -> str:
    """Email HTML (style nội tuyến, bảng: hiển thị tốt trên Gmail/Outlook). Sơ đồ & dòng thời gian xem ở trang web."""
    def li(arr, color, mark):
        return "".join(f'<tr><td style="width:26px;vertical-align:top;color:{color};font-weight:700;padding:6px 0">{mark}</td>'
                       f'<td style="padding:6px 0;color:#1B1724">{E(x.get("text", ""))}'
                       f'{" <span style=color:#8A8299>(" + E(x["owner"]) + ")</span>" if x.get("owner") else ""}</td></tr>' for x in arr)
    blocks = []
    if note:
        blocks.append(f'<p style="margin:0 0 16px;padding:12px 14px;border-left:3px solid #A2338C;background:#F6F3F9;color:#5E5670">{E(note)}</p>')
    if snap.get("summary"):
        blocks.append(f'<p style="font-size:16px;line-height:1.6;margin:0 0 18px">{E(snap["summary"])}</p>')
    if snap.get("decisions"):
        blocks.append(f'<h3 style="margin:18px 0 6px;font-size:16px">Đã chốt</h3><table style="border-collapse:collapse;width:100%">{li(snap["decisions"], "#13805F", "✓")}</table>')
    if snap.get("next_steps"):
        rows = "".join(f'<tr><td style="padding:8px 10px;border-top:1px solid #E6E0EE;font-weight:600;white-space:nowrap">{E(x.get("owner") or "Chưa giao")}</td>'
                       f'<td style="padding:8px 10px;border-top:1px solid #E6E0EE">{E(x.get("text", ""))}</td>'
                       f'<td style="padding:8px 10px;border-top:1px solid #E6E0EE;color:#2563C9;white-space:nowrap">{E(_due(x.get("due", "")))}</td></tr>'
                       for x in snap["next_steps"])
        blocks.append('<h3 style="margin:22px 0 6px;font-size:16px">Ai làm gì</h3><table style="border-collapse:collapse;width:100%;font-size:14px">'
                      '<tr style="color:#8A8299;text-align:left"><th style="padding:6px 10px">Người</th><th style="padding:6px 10px">Việc</th>'
                      f'<th style="padding:6px 10px">Hạn</th></tr>{rows}</table>')
    if snap.get("open_questions"):
        blocks.append(f'<h3 style="margin:18px 0 6px;font-size:16px">Còn bỏ ngỏ</h3><table style="border-collapse:collapse;width:100%">{li(snap["open_questions"], "#9A6A00", "?")}</table>')
    return (f'<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1B1724;max-width:640px;margin:0 auto;padding:8px">'
            f'<div style="color:#8A8299;font-size:13px">Biên bản họp · {E(_when(snap))}</div>'
            f'<h2 style="font-size:22px;margin:6px 0 16px">{E(snap["title"])}</h2>{"".join(blocks)}'
            f'<p style="margin:26px 0"><a href="{E(link)}" style="background:#A2338C;color:#fff;text-decoration:none;padding:12px 18px;border-radius:10px;font-weight:600;display:inline-block">'
            f'Xem sơ đồ và dòng thời gian cuộc họp</a></p>'
            f'<p style="color:#8A8299;font-size:12.5px">Gửi từ superHuy, trợ lý AI của anh Huy.</p></div>')
