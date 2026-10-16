"""Tính năng theo cấp (feature flags), thử nghiệm A/B và gói người dùng cho superYou.

- Gói (tier): free | pro | business | owner. Chủ nhân luôn là owner.
- Flag: {key, name, desc, scope: off|owner|tier|all|pct, tiers: [...], pct: 0-100, since}. Bật/tắt từng tính năng theo phạm vi,
  giúp anh "áp dụng cho riêng tôi" (scope=owner) trước, rồi mở cho gói hoặc tất cả.
- Thử nghiệm (experiment): {key, name, hypothesis, variants: [A,B], split: 50, metric, status: draft|running|done, start, result}.
  Người dùng được gán biến thể ổn định theo hash(uid). Sự kiện (track) ghi theo biến thể; bảng kết quả = tỷ lệ chuyển đổi theo biến thể.
- Đề xuất tính năng mới từ nghiên cứu (AI) -> board.propose(dept=product) -> anh duyệt -> chọn phạm vi áp dụng.

Dữ liệu: DATA_DIR/flags.json {flags: {}, experiments: {}, events: [], users: {uid: {tier, ...}}}.
"""
import datetime as dt
import hashlib
import json
import threading

from config import DATA_DIR, OWNER_CHAT_ID

FILE = DATA_DIR / "flags.json"
_LOCK = threading.Lock()
TIERS = {"free": "Miễn phí", "pro": "Pro", "business": "Doanh nghiệp", "owner": "Chủ nhân"}
SCOPES = {"off": "Tắt", "owner": "Chỉ anh", "tier": "Theo gói", "pct": "Một phần người dùng", "all": "Tất cả"}
DEFAULT_FLAGS = {
    "workflow_builder": {"name": "Trình dựng workflow kéo thả", "desc": "Tự ghép các bước từ thư viện thành workflow riêng.", "scope": "all", "tiers": [], "pct": 100},
    "passkey_login": {"name": "Đăng nhập Face ID / vân tay", "desc": "Passkey thay mã PIN trên từng thiết bị.", "scope": "all", "tiers": [], "pct": 100},
    "assistant_coach": {"name": "Trợ lý đồng hành khi tinh chỉnh", "desc": "Gợi ý bước tiếp theo khi dựng workflow, cài skill.", "scope": "all", "tiers": [], "pct": 100},
    "cfo_brief": {"name": "CFO brief mỗi sáng", "desc": "Bản tin tài chính một trang.", "scope": "owner", "tiers": [], "pct": 100},
    "clone_factory": {"name": "Xưởng clone", "desc": "Quét thị trường và clone sản phẩm.", "scope": "owner", "tiers": [], "pct": 100},
    "private_llm": {"name": "AI tại chỗ (Ollama)", "desc": "Chạy model nội bộ cho gói Doanh nghiệp.", "scope": "off", "tiers": ["business"], "pct": 0},
}


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("flags", {})
    d.setdefault("experiments", {})
    d.setdefault("events", [])
    d.setdefault("users", {})
    for k, v in DEFAULT_FLAGS.items():
        d["flags"].setdefault(k, dict(v, key=k, since=_now()))
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def tier_of(uid: int | str) -> str:
    if str(uid) == str(OWNER_CHAT_ID):
        return "owner"
    return _load()["users"].get(str(uid), {}).get("tier", "free")


def _bucket(uid, key: str) -> int:
    return int(hashlib.sha256(f"{uid}|{key}".encode()).hexdigest()[:8], 16) % 100


def enabled(key: str, uid: int | str = OWNER_CHAT_ID) -> bool:
    f = _load()["flags"].get(key)
    if not f:
        return False
    t = tier_of(uid)
    if t == "owner" and f["scope"] != "off":
        return True
    s = f["scope"]
    if s == "all":
        return True
    if s == "tier":
        return t in (f.get("tiers") or [])
    if s == "pct":
        return _bucket(uid, key) < int(f.get("pct") or 0)
    return False


def for_user(uid: int | str = OWNER_CHAT_ID) -> dict:
    d = _load()
    out = {k: enabled(k, uid) for k in d["flags"]}
    var = {k: variant(k, uid) for k, e in d["experiments"].items() if e["status"] == "running"}
    return {"flags": out, "variants": var, "tier": tier_of(uid)}


def set_flag(key: str, scope: str, tiers: str = "", pct: int = 100, name: str = "", desc: str = "") -> dict:
    if scope not in SCOPES:
        raise ValueError("Phạm vi không hợp lệ")
    with _LOCK:
        d = _load()
        f = d["flags"].get(key) or {"key": key, "name": name or key, "desc": desc, "since": _now()}
        f.update({"scope": scope, "tiers": [t for t in (tiers or "").split(",") if t in TIERS], "pct": max(0, min(100, int(pct or 0))), "updated": _now()})
        if name:
            f["name"] = name[:80]
        if desc:
            f["desc"] = desc[:300]
        d["flags"][key] = f
        _save(d)
    return {"text": f"“{f['name']}”: {SCOPES[scope]}" + (f" ({', '.join(TIERS[t] for t in f['tiers'])})" if scope == "tier" else f" ({f['pct']}%)" if scope == "pct" else "") + "."}


# ------------------------------------------------------------------ thử nghiệm A/B
def variant(key: str, uid: int | str = OWNER_CHAT_ID) -> str:
    e = _load()["experiments"].get(key)
    if not e or e["status"] != "running":
        return ""
    vs = e.get("variants") or ["A", "B"]
    return vs[0] if _bucket(uid, "exp:" + key) < int(e.get("split") or 50) else vs[1]


def create_experiment(key: str, name: str, hypothesis: str, variants: str = "A,B", split: int = 50, metric: str = "convert") -> dict:
    with _LOCK:
        d = _load()
        vs = [v.strip()[:30] for v in (variants or "A,B").split(",") if v.strip()][:2] or ["A", "B"]
        d["experiments"][key] = {"key": key[:40], "name": name[:120], "hypothesis": hypothesis[:600], "variants": vs, "split": max(5, min(95, int(split or 50))),
                                 "metric": metric[:40] or "convert", "status": "draft", "created": _now()}
        _save(d)
    return {"text": f"Đã tạo thử nghiệm “{name}”. Bấm Chạy để bắt đầu chia người dùng."}


def set_experiment(key: str, status: str, result: str = "") -> dict:
    with _LOCK:
        d = _load()
        e = d["experiments"].get(key)
        if not e:
            raise ValueError("Không tìm thấy thử nghiệm")
        if status not in ("draft", "running", "done"):
            raise ValueError("Trạng thái không hợp lệ")
        e["status"] = status
        if status == "running" and not e.get("start"):
            e["start"] = _now()
        if status == "done":
            e["end"] = _now()
            e["result"] = result[:600]
        _save(d)
    return {"text": f"Thử nghiệm “{e['name']}”: {status}."}


def track(event: str, uid: int | str = OWNER_CHAT_ID, props: dict | None = None) -> None:
    """Ghi sự kiện (giữ 20.000 dòng gần nhất). Gắn kèm biến thể của mọi thử nghiệm đang chạy."""
    with _LOCK:
        d = _load()
        vs = {k: variant(k, uid) for k, e in d["experiments"].items() if e["status"] == "running"}
        d["events"].append({"at": _now(), "uid": str(uid), "ev": event[:40], "v": vs, "p": {k: str(v)[:60] for k, v in (props or {}).items()}})
        d["events"] = d["events"][-20000:]
        _save(d)


def results(key: str) -> dict:
    d = _load()
    e = d["experiments"].get(key)
    if not e:
        raise ValueError("Không tìm thấy thử nghiệm")
    out = {}
    for v in e["variants"]:
        users = {x["uid"] for x in d["events"] if x["v"].get(key) == v}
        conv = {x["uid"] for x in d["events"] if x["v"].get(key) == v and x["ev"] == e["metric"]}
        out[v] = {"users": len(users), "converted": len(conv), "rate": round(len(conv) / len(users) * 100, 1) if users else 0}
    return {"experiment": e, "variants": out}


def overview() -> dict:
    d = _load()
    exps = []
    for k, e in d["experiments"].items():
        r = results(k)["variants"] if e["status"] != "draft" else {}
        exps.append(e | {"results": r})
    tiers = {t: sum(1 for u in d["users"].values() if u.get("tier") == t) for t in TIERS}
    tiers["owner"] = 1
    ev7 = [x for x in d["events"] if x["at"] >= (dt.datetime.now() - dt.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")]
    top = {}
    for x in ev7:
        top[x["ev"]] = top.get(x["ev"], 0) + 1
    return {"flags": list(d["flags"].values()), "experiments": exps, "tiers": tiers, "scopes": SCOPES, "tier_names": TIERS,
            "events_7d": len(ev7), "top_events": sorted(top.items(), key=lambda x: -x[1])[:10]}


# ------------------------------------------------------------------ nghiên cứu, đề xuất tính năng (AI) -> bảng
RESEARCH = """Bạn là trưởng nhóm Product của superYou (siêu trợ lý AI cho nhà quản lý, solopreneur; có Marketplace skill/workflow/gói tri thức).
Dữ liệu dùng 7 ngày: {events}
Tính năng đang bật: {flags}
Gói người dùng: {tiers}
Dựa vào dữ liệu và các sản phẩm tương tự (Notion, Lindy, Zapier, Superhuman, Linear, Raycast), đề xuất 3 nâng cấp hoặc tính năng mới, mỗi cái:
title ngắn, why (dựa dữ liệu hoặc best practice cụ thể), impact (chỉ số kỳ vọng), scope đề xuất (owner|pro|all), effort (ngày).
Trả về JSON: {{"items": [{{"title": "...", "why": "...", "impact": "...", "scope": "...", "effort": 2}}]}}"""


def research_propose() -> dict:
    """AI nghiên cứu, đưa 3 đề xuất lên bảng Phòng ban (phòng Product) để anh duyệt rồi chọn phạm vi."""
    import llm
    from agents import board
    o = overview()
    res = llm.ask_json(RESEARCH.format(events=json.dumps(o["top_events"], ensure_ascii=False), flags=", ".join(f["name"] for f in o["flags"] if f["scope"] != "off"),
                                       tiers=json.dumps(o["tiers"])), max_tokens=2000, tag="flags_research", ok=lambda r: isinstance(r, dict) and r.get("items"))
    if not res:
        return {"text": "AI chưa đưa được đề xuất lúc này."}
    n = 0
    for it in res["items"][:3]:
        board.propose("product", str(it.get("title", ""))[:120], str(it.get("why", "")), why=str(it.get("why", "")), impact=str(it.get("impact", "")),
                      cost=f"~{it.get('effort', '?')} ngày", needs=f"Phạm vi đề xuất: {it.get('scope', 'owner')}", priority="vua", by="Product research (AI)",
                      key="research:" + str(it.get("title", ""))[:40])
        n += 1
    return {"text": f"Đã đưa {n} đề xuất nâng cấp lên bảng Phòng ban."}
