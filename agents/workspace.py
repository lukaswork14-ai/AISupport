"""Không gian cá nhân của người dùng superYou: hồ sơ, cài đặt giao diện, workflow riêng (kéo thả), thư viện bước, trợ lý đồng hành.

- Hồ sơ: tên hiển thị, chức danh, công ty, ngành, mục tiêu, múi giờ, ngôn ngữ; AI dùng để trả lời đúng tầm (profile.md).
- Cài đặt: giao diện (theo hệ thống/sáng/tối), màu nhấn, mật độ, trang mở đầu, thông báo.
- Workflow riêng: người dùng ghép các bước từ thư viện (công cụ đọc/tổng hợp của superYou + workflow trên Marketplace), lưu, chạy,
  đặt lịch (sáng/tối), đăng lên Marketplace. Trợ lý đồng hành: từ một câu mục tiêu -> gợi ý chuỗi bước.

Dữ liệu: DATA_DIR/workspace.json {profile, prefs, workflows: {}, runs: []}.
"""
import datetime as dt
import json
import re
import secrets
import threading

from config import DATA_DIR

FILE = DATA_DIR / "workspace.json"
_LOCK = threading.Lock()
THEMES = {"system": "Theo hệ thống", "light": "Sáng", "dark": "Tối"}
ACCENTS = {"violet": "#6A3DF0", "jade": "#0B9877", "blue": "#2457C5", "rose": "#C21F78", "amber": "#C98205", "ink": "#15171A"}
DENSITY = {"comfortable": "Thoáng", "compact": "Gọn"}
HOMES = {"home": "Hôm nay", "tasks": "Việc", "meet": "Họp", "chat": "Trò chuyện", "mkt": "Marketplace"}
_WRITE = re.compile(r"(^|_)(tao|them|xong|ghi|sua|doi|luu|cai|go|chay|nhap|soan|dat|bat|tat|set|add|create|update|run|nhanh|giahan|checkin|ap|nho|quen|nop|duyet|boqua|caidat|chinh|chia|thu|hoi|lam|quet|viet|bantin|video|dongbo|nhan|caidat|wf|tro|tong_quan|repo)($|_)", re.I)
SCHED = {"": "Không", "morning": "Mỗi sáng 07:15", "evening": "Mỗi tối 20:30", "monday": "Thứ Hai 07:00"}


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("profile", {"name": "Huy", "title": "CEO", "company": "Sellnity", "industry": "AI + thương mại điện tử", "goals": "", "tz": "Asia/Ho_Chi_Minh", "lang": "vi"})
    d.setdefault("prefs", {"theme": "system", "accent": "violet", "density": "comfortable", "home": "home", "notify_brief": True, "notify_board": True, "haptics": True})
    d.setdefault("workflows", {})
    d.setdefault("runs", [])
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


# ------------------------------------------------------------------ hồ sơ và cài đặt
def get() -> dict:
    from core import flags, passkey
    d = _load()
    return {"profile": d["profile"], "prefs": d["prefs"], "themes": THEMES, "accents": ACCENTS, "density": DENSITY, "homes": HOMES,
            "passkeys": passkey.list_creds(), "flags": flags.for_user(), "tier_names": flags.TIERS}


def set_profile(name: str = "", title: str = "", company: str = "", industry: str = "", goals: str = "", tz: str = "", lang: str = "") -> dict:
    with _LOCK:
        d = _load()
        p = d["profile"]
        for k, v in (("name", name), ("title", title), ("company", company), ("industry", industry), ("goals", goals), ("tz", tz), ("lang", lang)):
            if v:
                p[k] = str(v).strip()[:200 if k == "goals" else 60]
        _save(d)
    # cập nhật profile.md để AI hiểu đúng người dùng (giữ bản dài nếu anh đã tự viết)
    try:
        from core import profile
        if not profile.PROFILE_FILE.exists() or profile.PROFILE_FILE.read_text(encoding="utf-8").startswith("CHỦ NHÂN (hồ sơ app)"):
            profile.PROFILE_FILE.write_text(
                f"CHỦ NHÂN (hồ sơ app): {p['name']} — {p['title']} tại {p['company']} ({p['industry']}).\nMục tiêu: {p.get('goals') or '(chưa ghi)'}.\n"
                f"Múi giờ {p['tz']}, ngôn ngữ {p['lang']}.\n\n" + profile.DEFAULT.split("\n", 4)[-1], encoding="utf-8")
    except Exception:
        pass
    return {"text": "Đã lưu hồ sơ.", "profile": p}


def set_prefs(**kw) -> dict:
    with _LOCK:
        d = _load()
        pr = d["prefs"]
        if kw.get("theme") in THEMES:
            pr["theme"] = kw["theme"]
        if kw.get("accent") in ACCENTS:
            pr["accent"] = kw["accent"]
        if kw.get("density") in DENSITY:
            pr["density"] = kw["density"]
        if kw.get("home") in HOMES:
            pr["home"] = kw["home"]
        for k in ("notify_brief", "notify_board", "haptics"):
            if kw.get(k) is not None and kw.get(k) != "":
                pr[k] = kw[k] in (True, "true", "1", 1, "on")
        _save(d)
    return {"text": "Đã lưu cài đặt.", "prefs": pr}


# ------------------------------------------------------------------ thư viện bước và workflow riêng
def library() -> dict:
    """Các bước có thể kéo thả: công cụ đọc/tổng hợp của superYou + workflow đã cài từ Marketplace."""
    from core import registry
    from agents import market
    steps = []
    for ag in sorted(registry.REGISTRY.values(), key=lambda a: a.order):
        if ag.id in ("market", "khach", "xuong", "phongban", "cfo", "caidat", "dang", "game"):
            continue
        for a in ag.actions:
            if not a.llm or market._DENY.search(f"{ag.id}.{a.id}") or _WRITE.search(a.id):
                continue
            steps.append({"id": f"{ag.id}.{a.id}", "agent": ag.id, "action": a.id, "label": a.label, "group": ag.name, "icon": ag.icon,
                          "desc": (a.desc or "")[:140], "params": [{"name": p.name, "label": p.label, "type": p.type, "default": p.default} for p in a.params if not p.required or p.default is not None][:4]})
    mk = [{"id": "mk:" + x["id"], "label": x["name"], "group": "Marketplace", "icon": "🛍", "desc": x["tagline"], "lid": x["id"], "installed": x["installed"], "price": x["price"]}
          for x in market.catalog()["items"] if x["type"] == "workflow"]
    return {"steps": steps, "market": mk, "sched": SCHED}


def list_workflows() -> dict:
    d = _load()
    return {"items": sorted(d["workflows"].values(), key=lambda w: w["updated"], reverse=True), "runs": d["runs"][-10:][::-1], "sched": SCHED}


def save_workflow(wid: str = "", name: str = "", steps: str = "", schedule: str = "", desc: str = "") -> dict:
    """steps: JSON [{agent, action, params, label}] hoặc text 'agent.action: nhãn' mỗi dòng."""
    from agents import market
    try:
        st = json.loads(steps) if steps.strip().startswith("[") else None
    except Exception:
        st = None
    if st is None:
        st = market._content_from("workflow", steps)["steps"]
    clean = []
    for s in st[:12]:
        s = {"agent": str(s.get("agent", ""))[:30], "action": str(s.get("action", ""))[:40], "params": {k: str(v)[:200] for k, v in (s.get("params") or {}).items()},
             "label": str(s.get("label") or "")[:60]}
        if not market._step_ok(s):
            raise ValueError(f"Bước {s['agent']}.{s['action']} gửi, đăng hoặc xoá dữ liệu nên không được dùng")
        clean.append(s)
    if not clean:
        raise ValueError("Workflow cần ít nhất một bước")
    with _LOCK:
        d = _load()
        w = d["workflows"].get(wid) if wid else None
        if not w:
            from core import accounts
            accounts.check_limit("workflows", len(d["workflows"]))
            wid = secrets.token_hex(4)
            w = {"id": wid, "created": _now(), "runs": 0}
            d["workflows"][wid] = w
        w.update({"name": (name or "Workflow mới").strip()[:80], "desc": desc.strip()[:300], "steps": clean, "schedule": schedule if schedule in SCHED else "", "updated": _now()})
        _save(d)
    return {"text": f"Đã lưu workflow “{w['name']}”" + (f", chạy {SCHED[w['schedule']].lower()}" if w["schedule"] else "") + ".", "id": wid}


def delete_workflow(wid: str) -> dict:
    with _LOCK:
        d = _load()
        d["workflows"].pop(wid, None)
        _save(d)
    return {"text": "Đã xoá workflow."}


def run_workflow(wid: str) -> dict:
    from core import registry
    d = _load()
    w = d["workflows"].get(wid)
    if not w:
        raise ValueError("Không tìm thấy workflow")
    parts, ok = [], 0
    for st in w["steps"]:
        label = st.get("label") or f"{st['agent']}.{st['action']}"
        try:
            r = registry.run(st["agent"], st["action"], dict(st.get("params") or {}))
            parts.append(f"## {label}\n{(r or {}).get('text', '').strip()[:2500] or '(không có nội dung)'}")
            ok += 1
        except Exception as e:
            parts.append(f"## {label}\nChưa chạy được: {str(e)[:200]}")
    text = f"# {w['name']}\n\n" + "\n\n".join(parts)
    with _LOCK:
        d = _load()
        if wid in d["workflows"]:
            d["workflows"][wid]["runs"] = d["workflows"][wid].get("runs", 0) + 1
            d["workflows"][wid]["last_run"] = _now()
        d["runs"].append({"wid": wid, "name": w["name"], "at": _now(), "ok": ok, "total": len(w["steps"]), "text": text[:6000]})
        d["runs"] = d["runs"][-50:]
        _save(d)
    try:
        from core import flags
        flags.track("workflow_run", props={"wid": wid})
    except Exception:
        pass
    return {"text": text, "ok": ok, "total": len(w["steps"])}


def run_scheduled(slot: str) -> int:
    """Gọi từ scheduler: chạy mọi workflow đặt lịch ở slot, gửi kết quả vào Telegram."""
    from core import notify
    d = _load()
    n = 0
    for w in list(d["workflows"].values()):
        if w.get("schedule") == slot:
            try:
                r = run_workflow(w["id"])
                notify.send(text=r["text"][:3800])
                n += 1
            except Exception:
                pass
    return n


def publish_workflow(wid: str, tagline: str = "", description: str = "", price: int = 0) -> dict:
    """Đăng workflow riêng lên Marketplace (nháp trong Studio, anh duyệt lên kệ)."""
    from agents import market
    d = _load()
    w = d["workflows"].get(wid)
    if not w:
        raise ValueError("Không tìm thấy workflow")
    body = "\n".join(f"{s['agent']}.{s['action']}: {s.get('label', '')}" for s in w["steps"])
    return market.studio_save("workflow", w["name"], tagline or w.get("desc", "")[:160], description or w.get("desc", ""), body, "nang-suat", price, "", False)


COACH = """Bạn là trợ lý đồng hành của superYou, giúp người dùng tự ghép workflow từ thư viện bước có sẵn.
Thư viện bước (id: mô tả): {lib}
Mục tiêu của người dùng: "{goal}"
Hãy đề xuất một workflow 2–6 bước chỉ dùng id trong thư viện, theo đúng thứ tự hợp lý, kèm tên ngắn và một câu giải thích vì sao.
Nếu mục tiêu cần bước gửi/đăng/xoá (không có trong thư viện), nói rõ người dùng sẽ tự làm bước đó sau khi xem kết quả.
Trả về JSON: {{"name": "...", "why": "...", "steps": [{{"id": "agent.action", "label": "tên bước ngắn"}}], "tip": "1 mẹo tinh chỉnh"}}"""


def coach(goal: str) -> dict:
    """Trợ lý đồng hành: từ mục tiêu -> gợi ý workflow (người dùng kéo thả chỉnh tiếp)."""
    import llm
    lib = library()["steps"]
    byid = {s["id"]: s for s in lib}
    res = llm.ask_json(COACH.format(lib="; ".join(f"{s['id']}: {s['label']}" for s in lib[:60]), goal=(goal or "").strip()[:300]), max_tokens=1200, tag="ws_coach",
                       ok=lambda r: isinstance(r, dict) and isinstance(r.get("steps"), list))
    if not res:
        raise ValueError("Trợ lý chưa gợi ý được lúc này, anh thử diễn đạt mục tiêu rõ hơn")
    steps = []
    for s in res["steps"][:6]:
        b = byid.get(str(s.get("id", "")))
        if b:
            steps.append({"agent": b["agent"], "action": b["action"], "params": {}, "label": str(s.get("label") or b["label"])[:60]})
    if not steps:
        raise ValueError("Gợi ý không khớp thư viện bước, anh thử lại")
    return {"name": str(res.get("name", "Workflow mới"))[:80], "why": str(res.get("why", ""))[:300], "tip": str(res.get("tip", ""))[:200], "steps": steps}
