"""Reel Studio: dựng và chỉnh video bản tin tới khi ưng ý, rồi đóng gói "công thức" thành kỹ năng của một News Studio.

- Dựng nền (không chặn app): tiến độ theo %, từng bước; xong là có PHIÊN BẢN mới (giữ 8 bản gần nhất, chọn lại được bản bất kỳ).
- Chỉnh nhanh bằng lời ("giọng nam, đọc chậm hơn, hook mạnh hơn, bỏ nhạc"): superHuy hiểu yêu cầu -> đổi cài đặt và/hoặc sửa kịch bản -> dựng lại.
- Sửa kịch bản trực tiếp từng cảnh (lời đọc + chữ trên màn hình) rồi dựng lại, không cần AI viết lại.
- Công thức (recipe): lưu bộ cài đặt + cấu trúc cảnh + quy tắc biên tập rút ra từ các lần anh chỉnh -> Second Brain (Obsidian);
  đặt làm mặc định để mọi video sau theo công thức đó.
- Skill News Studio: gộp mọi công thức + phản hồi của anh thành SKILL.md (định dạng Claude skill) để superHuy (và Claude Code) dùng lại.
"""
import datetime as dt
import json
import logging
import re
import threading
import time
import uuid

from config import CARD_HANDLE, DATA_DIR, OBSIDIAN_VAULT
from core import notify, store
from llm import ask_json, fix_vi

log = logging.getLogger("reel-studio")
DIR = DATA_DIR / "studio"
RECIPES = DIR / "recipes.json"
FEEDBACK = DIR / "feedback.json"
SKILL = DIR / "news-studio-SKILL.md"
VOICES = {"NamMinh": "Nam · miền Bắc (NamMinh)", "HoaiMy": "Nữ · miền Bắc (HoaiMy)"}
SPEEDS = {"cham": ("Chậm, rõ", "+0%"), "vua": ("Vừa", "+6%"), "nhanh": ("Nhanh kiểu reels", "+12%")}
MUSIC = {"tat": ("Tắt", 0.0), "nhe": ("Nhẹ", 0.35), "vua": ("Vừa", 0.55), "to": ("To", 0.8)}
LENS = [30, 45, 60, 90]
_locks: dict[str, threading.Lock] = {}


def _rj(p, d):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return d


def _wj(p, v):
    DIR.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


# ------------------------------------------------------------------ cài đặt + công thức mặc định
def default_settings() -> dict:
    from agents import content_hub
    c = content_hub.cfg()
    s = {"voice": c.get("voice") or "NamMinh", "speed": "nhanh" if c.get("fast", True) else "vua",
         "music": "vua" if c.get("music", True) else "tat", "len": int(c.get("reel_len") or 60)}
    r = default_recipe()
    if r:
        s.update({k: v for k, v in (r.get("settings") or {}).items() if k in s})
    return s


def _norm(s: dict) -> dict:
    d = default_settings()
    out = {**d, **{k: v for k, v in (s or {}).items() if v not in (None, "")}}
    if out["voice"] not in VOICES:
        out["voice"] = "NamMinh"
    if out["speed"] not in SPEEDS:
        out["speed"] = "nhanh"
    if out["music"] not in MUSIC:
        out["music"] = "vua"
    out["len"] = int(out["len"]) if int(out.get("len") or 60) in LENS else 60
    return out


def rules_text() -> str:
    """Quy tắc kênh đưa vào lúc viết kịch bản: công thức mặc định + tóm tắt skill News Studio."""
    parts = []
    r = default_recipe()
    if r:
        parts.append("CÔNG THỨC KÊNH ĐANG DÙNG (bắt buộc theo): " + "; ".join(r.get("rules") or []))
        if r.get("structure"):
            parts.append("Cấu trúc cảnh ưu tiên: " + " -> ".join(r["structure"]))
        if r.get("hooks"):
            parts.append("Mẫu hook anh thích: " + " | ".join(r["hooks"][:3]))
    fb = _rj(FEEDBACK, [])[-12:]
    if fb:
        parts.append("ANH TỪNG YÊU CẦU CHỈNH (hãy làm đúng ngay từ đầu): " + "; ".join(x["text"] for x in fb))
    return "\n".join(parts)


# ------------------------------------------------------------------ trạng thái 1 video
def state(cid: str) -> dict:
    r = store.get(cid)
    if not r or r.get("kind") != "video":
        raise ValueError("Không tìm thấy video")
    m = r.get("meta") or {}
    sc = m.get("newscast") or {}
    return {"id": cid, "title": r["title"], "video": r.get("video"), "image": r.get("image"), "caption": r.get("text", ""),
            "first_comment": m.get("first_comment", ""), "duration": m.get("duration"), "chapters": m.get("chapters") or [],
            "settings": _norm(m.get("settings") or {}), "script": sc, "engine": m.get("engine"), "voice_engine": m.get("voice_engine"),
            "versions": [{k: v for k, v in x.items() if k != "script"} for x in (m.get("versions") or [])][-8:],
            "current": m.get("current_version", ""), "render": m.get("render") or {}, "item": m.get("item", ""),
            "options": {"voices": VOICES, "speeds": {k: v[0] for k, v in SPEEDS.items()}, "music": {k: v[0] for k, v in MUSIC.items()}, "lens": LENS},
            "recipe": (default_recipe() or {}).get("name", "")}


def _set_render(cid: str, **kw):
    r = store.get(cid)
    m = dict(r.get("meta") or {})
    m["render"] = {**(m.get("render") or {}), **kw, "at": _now()}
    store.update(cid, meta=m)


def _item_for(m: dict, title: str) -> dict:
    from agents import content_hub
    return content_hub.find(m.get("item", "")) or {"headline_vi": title.replace("Reels: ", ""), "source": m.get("source", ""),
                                                     "url": m.get("url", ""), "topic": m.get("topic", ""), "track": m.get("track", "tin")}


def render(cid: str, settings: dict | None = None, script: dict | None = None, rewrite: bool = False, angle: str = "", note: str = "") -> dict:
    """Bắt đầu dựng nền 1 phiên bản mới. Trả về ngay; app hỏi tiến độ bằng state()."""
    r = store.get(cid)
    if not r or r.get("kind") != "video":
        raise ValueError("Không tìm thấy video")
    lock = _locks.setdefault(cid, threading.Lock())
    if lock.locked():
        raise ValueError("Video này đang được dựng, anh chờ bản hiện tại xong nhé")
    m = r.get("meta") or {}
    st = _norm({**(m.get("settings") or {}), **(settings or {})})
    _set_render(cid, status="running", step="Chuẩn bị", pct=2, started=_now(), error="", note=note, settings=st)

    def work():
        from agents import content_agent, content_hub, newscast
        t0 = time.time()
        with lock:
            try:
                rec = store.get(cid)
                mm = rec.get("meta") or {}
                it = _item_for(mm, rec["title"])
                sc = script or mm.get("newscast")
                if rewrite or not sc or (sc.get("len") and sc.get("len") != st["len"] and not script):
                    _set_render(cid, step="Viết kịch bản bản tin", pct=4)
                    body = it.get("body") or content_hub._page_text(it.get("url", "")) or it.get("raw", "") or it.get("summary_vi", "")
                    sc = newscast.write_script(it, body, st["len"], content_agent.get_style(), angle, rules=rules_text())
                out = newscast.make(sc, it, name=f"reel-{cid}", voice=st["voice"], brand=CARD_HANDLE, rate=SPEEDS[st["speed"]][1],
                                    music=MUSIC[st["music"]][1] > 0, music_vol=MUSIC[st["music"]][1] or 0.55,
                                    progress=lambda msg, pct: _set_render(cid, step=msg, pct=max(5, min(99, pct))))
                rec = store.get(cid)
                mm = dict(rec.get("meta") or {})
                vid = uuid.uuid4().hex[:6]
                ver = {"id": vid, "video": out["video"], "image": out.get("poster"), "duration": out["duration"], "chapters": out["chapters"],
                       "settings": st, "script": sc, "note": note, "at": _now(), "voice_engine": out["engine"]}
                mm.update(newscast=sc, chapters=out["chapters"], duration=out["duration"], voice_engine=out["engine"], engine="newscast",
                          settings=st, reel=newscast.script_text(sc), current_version=vid, len=st["len"],
                          versions=((mm.get("versions") or []) + [ver])[-8:],
                          render={"status": "done", "step": "Xong", "pct": 100, "at": _now(), "secs": round(time.time() - t0), "version": vid})
                cap = rec.get("text") or ""
                if sc.get("caption") and (rewrite or not cap):
                    tags = " ".join(h if h.startswith("#") else "#" + h for h in (sc.get("hashtags") or [])[:5])
                    cap = sc["caption"].strip() + ("\n\n" + tags if tags else "")
                store.update(cid, video=out["video"], image=out.get("poster") or rec.get("image"), meta=mm, text=cap)
                if time.time() - t0 > 90:
                    notify.send(text=f"🎬 Đã dựng xong bản mới ({round(out['duration'])} giây): {rec['title'].replace('Reels: ', '')}. Mở app › Nội dung › Đã tạo để xem.")
            except Exception as e:
                log.exception("Dựng video lỗi")
                _set_render(cid, status="error", step="Lỗi", pct=0, error=str(e)[:300])

    threading.Thread(target=work, daemon=True, name=f"render-{cid}").start()
    return {**state(cid), "text": "Đang dựng bản mới"}


def rerender(cid: str, voice: str = "", speed: str = "", music: str = "", length: int = 0, rewrite: bool = False, angle: str = "") -> dict:
    return render(cid, {"voice": voice, "speed": speed, "music": music, "len": int(length or 0) or None}, rewrite=bool(rewrite), angle=angle,
                  note="Dựng lại" + (" + viết lại kịch bản" if rewrite else ""))


# ------------------------------------------------------------------ chỉnh nhanh bằng lời
QUICK = """Bạn là đạo diễn dựng bản tin video. Anh Huy xem bản hiện tại và yêu cầu chỉnh: "{ins}"
CÀI ĐẶT HIỆN TẠI: {settings}
LỰA CHỌN: voice {voices}; speed {speeds}; music {music}; len {lens} (giây).
KỊCH BẢN HIỆN TẠI (JSON): {script}
Hãy hiểu đúng ý anh:
- Yêu cầu về giọng/tốc độ/nhạc/độ dài -> đổi "settings" (chỉ các khoá cần đổi). "giọng nam" = NamMinh, "giọng nữ" = HoaiMy.
- Yêu cầu về nội dung (hook, số liệu, câu chữ, thứ tự, bớt/thêm cảnh, giọng văn) -> trả "scenes" ĐÃ SỬA (giữ đúng cấu trúc JSON từng cảnh, giữ sự thật).
  Không đổi nội dung thì "scenes": null. Nếu đổi độ dài mà không yêu cầu nội dung khác thì "rewrite": true để viết lại theo độ dài mới.
- "learning": 1 quy tắc ngắn rút ra từ yêu cầu để lần sau làm đúng ngay (vd "Luôn dùng giọng nam, đọc vừa phải").
Trả về DUY NHẤT JSON: {{"settings": {{}}, "scenes": null, "rewrite": false, "summary": "đã hiểu và sẽ chỉnh gì (1 câu)", "learning": "..."}}"""


def quick_edit(cid: str, instruction: str) -> dict:
    instruction = (instruction or "").strip()[:500]
    if not instruction:
        raise ValueError("Anh nói muốn sửa gì nhé")
    s = state(cid)
    r = ask_json(QUICK.format(ins=instruction, settings=json.dumps(s["settings"], ensure_ascii=False), voices=list(VOICES),
                              speeds=list(SPEEDS), music=list(MUSIC), lens=LENS,
                              script=json.dumps({"scenes": (s["script"] or {}).get("scenes")}, ensure_ascii=False)[:9000]),
                 6000, 2, ok=lambda x: isinstance(x, dict) and "summary" in x, tag="quick-edit")
    if not r:
        raise RuntimeError("superHuy chưa hiểu yêu cầu, anh nói cụ thể hơn giúp em")
    script = None
    if isinstance(r.get("scenes"), list) and len(r["scenes"]) >= 3 and s["script"]:
        script = {**s["script"], "scenes": [x for x in r["scenes"] if isinstance(x, dict) and x.get("voiceover")]}
    fb = _rj(FEEDBACK, [])
    fb.append({"text": (r.get("learning") or instruction)[:200], "ins": instruction, "cid": cid, "at": _now()})
    _wj(FEEDBACK, fb[-80:])
    out = render(cid, r.get("settings") or {}, script=script, rewrite=bool(r.get("rewrite")) and not script, note=instruction)
    return {**out, "text": fix_vi(r.get("summary") or "Đang dựng lại theo yêu cầu")}


def edit_script(cid: str, scenes: str) -> dict:
    """Anh sửa trực tiếp lời đọc/chữ từng cảnh -> dựng lại (không dùng AI)."""
    s = state(cid)
    try:
        new = json.loads(scenes) if isinstance(scenes, str) else scenes
    except Exception:
        raise ValueError("Kịch bản sửa không hợp lệ")
    old = (s["script"] or {}).get("scenes") or []
    if not isinstance(new, list) or len(new) < 2:
        raise ValueError("Kịch bản cần ít nhất 2 cảnh")
    merged = []
    for k, x in enumerate(new):
        base = dict(old[k]) if k < len(old) else {"type": x.get("type", "headline"), "on_screen": {}}
        base["voiceover"] = str(x.get("voiceover") or base.get("voiceover") or "").strip()
        if isinstance(x.get("on_screen"), dict):
            base["on_screen"] = {**(base.get("on_screen") or {}), **x["on_screen"]}
        if base["voiceover"]:
            merged.append(base)
    return render(cid, script={**(s["script"] or {}), "scenes": merged}, note="Sửa kịch bản trực tiếp")


def choose_version(cid: str, vid: str) -> dict:
    r = store.get(cid)
    m = dict(r.get("meta") or {})
    v = next((x for x in m.get("versions") or [] if x["id"] == vid), None)
    if not v:
        raise ValueError("Không tìm thấy phiên bản")
    from agents import newscast
    m.update(current_version=vid, newscast=v.get("script") or m.get("newscast"), chapters=v.get("chapters"), duration=v.get("duration"),
             settings=v.get("settings"), reel=newscast.script_text(v.get("script") or {}))
    store.update(cid, video=v["video"], image=v.get("image") or r.get("image"), meta=m)
    return {**state(cid), "text": "Đã chọn phiên bản này làm bản chính"}


def set_caption(cid: str, caption: str) -> dict:
    store.update(cid, text=(caption or "").strip())
    return {"text": "Đã lưu caption"}


# ------------------------------------------------------------------ công thức (recipe) -> Second Brain
RECIPE = """Từ video bản tin anh Huy ĐÃ ƯNG Ý dưới đây, hãy rút ra "công thức" để superHuy làm các video sau đúng chuẩn này.
CÀI ĐẶT: {settings}
KỊCH BẢN: {script}
CÁC LẦN ANH YÊU CẦU CHỈNH: {fb}
GHI CHÚ CỦA ANH: {notes}
Trả về DUY NHẤT JSON: {{"name": "tên công thức ngắn", "summary": "1-2 câu", "structure": ["chuỗi kiểu cảnh, vd hook", "headline", "stat", "..."],
"rules": ["5-8 quy tắc biên tập cụ thể: độ dài câu, nhịp, cách dùng số liệu, giọng văn, hook, CTA, đồ hoạ"],
"hooks": ["2-3 mẫu hook rút từ kịch bản (dạng khuôn mẫu)"], "dos": ["..."], "donts": ["..."]}}"""


def recipes() -> dict:
    rows = _rj(RECIPES, [])
    return {"items": rows, "default": next((r["id"] for r in rows if r.get("default")), ""), "skill": skill_view().get("updated", "")}


def default_recipe() -> dict | None:
    return next((r for r in _rj(RECIPES, []) if r.get("default")), None)


def save_recipe(cid: str, name: str = "", notes: str = "", make_default: bool = True) -> dict:
    s = state(cid)
    fb = [x["ins"] for x in _rj(FEEDBACK, []) if x.get("cid") == cid] or [x["ins"] for x in _rj(FEEDBACK, [])[-8:]]
    r = ask_json(RECIPE.format(settings=json.dumps(s["settings"], ensure_ascii=False), script=json.dumps(s["script"], ensure_ascii=False)[:7000],
                               fb="; ".join(fb) or "(không)", notes=notes or "(không)"),
                 3000, 2, ok=lambda x: isinstance(x, dict) and x.get("rules"), tag="recipe")
    if not r:
        raise RuntimeError("superHuy chưa rút được công thức, anh thử lại sau ít phút")
    rec = {"id": uuid.uuid4().hex[:6], "name": (name or r.get("name") or "Công thức bản tin").strip()[:60], "summary": fix_vi(r.get("summary", "")),
           "settings": s["settings"], "structure": r.get("structure") or [], "rules": r.get("rules") or [], "hooks": r.get("hooks") or [],
           "dos": r.get("dos") or [], "donts": r.get("donts") or [], "example_video": cid, "notes": notes, "at": _now(), "default": bool(make_default)}
    rows = _rj(RECIPES, [])
    if make_default:
        for x in rows:
            x["default"] = False
    rows.append(rec)
    _wj(RECIPES, rows[-30:])
    try:
        rec["note"] = _recipe_note(rec, s)
    except Exception:
        log.exception("Không ghi công thức vào Obsidian")
    threading.Thread(target=lambda: _safe(build_skill), daemon=True).start()
    return {**rec, "text": f"Đã lưu công thức “{rec['name']}” vào Second Brain" + (" và đặt làm mặc định" if make_default else "")}


def _safe(fn):
    try:
        fn()
    except Exception:
        log.exception("Lỗi %s", getattr(fn, "__name__", "job"))


def _recipe_note(rec: dict, s: dict) -> str:
    from agents import newscast
    folder = OBSIDIAN_VAULT / "02 Areas/News Studio/Cong thuc"
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", rec["name"]).strip()[:60]
    st = rec["settings"]
    bl = lambda xs: "\n".join(f"- {x}" for x in xs or [])  # noqa: E731
    p = folder / f"{safe}.md"
    p.write_text(f"---\ntitle: \"{rec['name']}\"\ntype: reel-recipe\ngenerated_by: superhuy\ndate: {rec['at'][:10]}\ntags: [news-studio, recipe]\n---\n"
                 f"# Công thức: {rec['name']}\n{rec['summary']}\n\n## Cài đặt\n- Giọng: {VOICES.get(st['voice'])}\n- Tốc độ: {SPEEDS[st['speed']][0]}\n"
                 f"- Nhạc nền: {MUSIC[st['music']][0]}\n- Độ dài: {st['len']} giây\n\n## Cấu trúc cảnh\n{' → '.join(rec['structure'])}\n\n"
                 f"## Quy tắc biên tập\n{bl(rec['rules'])}\n\n## Mẫu hook\n{bl(rec['hooks'])}\n\n## Nên\n{bl(rec['dos'])}\n\n## Tránh\n{bl(rec['donts'])}\n\n"
                 f"## Kịch bản mẫu\n```\n{newscast.script_text(s['script'] or {})}\n```\n", encoding="utf-8")
    return str(p.relative_to(OBSIDIAN_VAULT))


def set_default(rid: str) -> dict:
    rows = _rj(RECIPES, [])
    for x in rows:
        x["default"] = x["id"] == rid
    _wj(RECIPES, rows)
    return {"text": "Đã đặt công thức mặc định cho video sau"}


def delete_recipe(rid: str) -> dict:
    _wj(RECIPES, [x for x in _rj(RECIPES, []) if x["id"] != rid])
    return {"text": "Đã xoá công thức"}


# ------------------------------------------------------------------ skill News Studio
SKILLP = """Bạn biên soạn một SKILL (định dạng Claude skill: SKILL.md có frontmatter name/description) cho "News Studio" của anh Huy:
một kênh BẢN TIN VIDEO dọc chuyên nghiệp trên mạng xã hội về AI, thương mại điện tử, agentic commerce, founder — cho cộng đồng seller/founder Việt.
Skill này để superHuy (và Claude Code) sản xuất bản tin đúng chuẩn kênh, mỗi lần đều tốt hơn.
DỮ LIỆU:
- Công thức anh đã duyệt: {recipes}
- Các lần anh yêu cầu chỉnh video: {fb}
- Năng lực hệ thống: săn tin + phân tích CAO, phóng viên đào sâu, kịch bản nhiều kiểu cảnh (hook, headline, stat, compare, timeline, list, quote, image,
  analysis, cta), giọng edge-tts NamMinh/HoaiMy, phụ đề sáng theo từ, nhạc nền tự né giọng, ảnh bài báo/Wikipedia/Pexels.
Viết SKILL.md tiếng Việt, gồm: frontmatter (name: news-studio, description 1 câu khi nào dùng), ## Định vị kênh và khán giả, ## Quy trình sản xuất
(chọn tin -> đào sâu -> kịch bản -> dựng -> kiểm tra -> đăng -> đo), ## Công thức video chuẩn (cấu trúc cảnh, độ dài, nhịp, giọng, nhạc),
## Quy tắc biên tập (trung thực, số liệu, câu chữ, hook, CTA), ## Mẫu hook, ## Checklist chất lượng trước khi đăng, ## Chỉ số theo dõi và cách cải tiến,
## Những điều anh Huy đã yêu cầu (bài học từ phản hồi).
Trả về DUY NHẤT JSON: {{"skill_md": "toàn văn SKILL.md", "summary": "2 câu"}}"""


def build_skill() -> dict:
    rows = _rj(RECIPES, [])
    fb = _rj(FEEDBACK, [])
    r = ask_json(SKILLP.format(recipes=json.dumps([{k: x.get(k) for k in ("name", "settings", "structure", "rules", "hooks", "dos", "donts", "default")}
                                                   for x in rows], ensure_ascii=False)[:8000] or "(chưa có)",
                               fb="; ".join(x["ins"] for x in fb[-40:]) or "(chưa có)"),
                 8000, 2, ok=lambda x: isinstance(x, dict) and len(x.get("skill_md") or "") > 800, tag="news-skill")
    if not r:
        raise RuntimeError("superHuy chưa soạn được skill, thử lại sau")
    md = r["skill_md"].strip()
    if not md.startswith("---"):
        md = "---\nname: news-studio\ndescription: Sản xuất bản tin video dọc chuẩn kênh superHuy (AI, thương mại điện tử, agentic commerce).\n---\n" + md
    DIR.mkdir(parents=True, exist_ok=True)
    SKILL.write_text(md, encoding="utf-8")
    meta = {"updated": _now(), "summary": fix_vi(r.get("summary", "")), "recipes": len(rows), "feedback": len(fb)}
    _wj(DIR / "skill.json", meta)
    try:
        p = OBSIDIAN_VAULT / "Skills/news-studio"
        p.mkdir(parents=True, exist_ok=True)
        (p / "SKILL.md").write_text(md, encoding="utf-8")
        meta["obsidian"] = "Skills/news-studio/SKILL.md"
        _wj(DIR / "skill.json", meta)
    except Exception:
        log.exception("Không ghi SKILL.md vào Obsidian")
    return {**meta, "md": md, "text": "Đã cập nhật skill News Studio"}


def skill_view() -> dict:
    meta = _rj(DIR / "skill.json", {})
    md = SKILL.read_text(encoding="utf-8") if SKILL.exists() else ""
    return {**meta, "md": md}
