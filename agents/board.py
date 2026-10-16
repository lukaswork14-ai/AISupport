"""Phòng ban superYou: cơ chế đề xuất -> anh duyệt -> tự giao việc, chạy ngay trong hệ thống (không phụ thuộc phiên Claude).

Mỗi phòng ban là một "agent" (người hoặc AI). Phòng AI (CFO, CSO...) tự viết đề xuất lên bảng theo lịch; phòng Product/GTM
(các phiên Claude) ghi qua API. Anh là người quyết cuối: Duyệt / Cần làm rõ / Từ chối. Duyệt xong, phiếu tự chuyển thành
việc giao cho phòng phụ trách, có hạn và trạng thái; phòng xong việc ghi kết quả.

Dữ liệu: DATA_DIR/board.json {depts, items, log}.
"""
import datetime as dt
import json
import secrets
import threading

from config import DATA_DIR

FILE = DATA_DIR / "board.json"
_LOCK = threading.Lock()
DEPTS = {
    "product": {"name": "Product", "desc": "Phát triển superYou (app, hạ tầng, bảo mật)", "kind": "claude", "color": "#5B3FD9"},
    "gtm": {"name": "GTM", "desc": "Đưa sản phẩm ra thị trường, giá, kênh, nội dung", "kind": "claude", "color": "#0E7C6B"},
    "so": {"name": "Sản phẩm số", "desc": "Tài sản số, Xưởng clone, Marketplace", "kind": "owner", "color": "#C2410C"},
    "finance": {"name": "Tài chính (CFO)", "desc": "Doanh thu, chi phí, dòng tiền, dự báo, đề xuất hành động", "kind": "ai", "color": "#B4236B"},
    "sales": {"name": "Bán hàng (CSO)", "desc": "Khách tiềm năng, phễu, theo đuổi, đối tác", "kind": "ai", "color": "#2457C5"},
    "ops": {"name": "Vận hành", "desc": "Tenant, sự cố, chi phí hạ tầng", "kind": "ai", "color": "#7A5A00"},
    "qa": {"name": "Kiểm thử & Bảo mật (QA)", "desc": "Kiểm thử như người dùng thật trên đa nền tảng, bảo mật, chất lượng trước khi lên kệ", "kind": "claude", "color": "#B42346"},
}
STATUS = {"cho_duyet": "Chờ anh duyệt", "can_lam_ro": "Cần làm rõ", "da_duyet": "Đã duyệt", "dang_lam": "Đang triển khai", "xong": "Xong", "tu_choi": "Từ chối"}
PRIO = {"cao": "Cao", "vua": "Vừa", "thap": "Thấp"}


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("items", {})
    d.setdefault("log", [])
    d.setdefault("depts", {})
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def _log(d: dict, who: str, what: str):
    d["log"].append({"at": _now(), "who": who, "what": what[:240]})
    d["log"] = d["log"][-400:]


def propose(dept: str, title: str, summary: str, why: str = "", impact: str = "", cost: str = "", needs: str = "", priority: str = "vua",
            by: str = "", auto_assign_to: str = "", key: str = "") -> dict:
    """Một phòng ban đưa đề xuất. key: chống trùng (cùng key chưa đóng thì cập nhật thay vì tạo mới)."""
    dept = dept if dept in DEPTS else "product"
    with _LOCK:
        d = _load()
        if key:
            ex = next((x for x in d["items"].values() if x.get("key") == key and x["status"] in ("cho_duyet", "can_lam_ro", "da_duyet", "dang_lam")), None)
            if ex:
                ex.update({"summary": summary[:2000], "why": why[:1000], "impact": impact[:600], "cost": cost[:400], "needs": needs[:600], "updated": _now()})
                _save(d)
                return {"text": f"Đã cập nhật đề xuất “{ex['title']}”.", "id": ex["id"], "dup": True}
        x = {"id": secrets.token_hex(4), "dept": dept, "title": title[:160], "summary": summary[:2000], "why": why[:1000], "impact": impact[:600],
             "cost": cost[:400], "needs": needs[:600], "priority": priority if priority in PRIO else "vua", "by": by or DEPTS[dept]["name"],
             "assign_to": auto_assign_to if auto_assign_to in DEPTS else dept, "status": "cho_duyet", "key": key, "note": "", "result": "",
             "created": _now(), "updated": _now()}
        d["items"][x["id"]] = x
        _log(d, x["by"], f"Đề xuất: {x['title']}")
        _save(d)
    try:
        from core import security
        security.alert_once(f"board:{x['id']}", f"📋 {DEPTS[dept]['name']} đề xuất: “{x['title']}”. Duyệt trong superYou HQ › Phòng ban.", every=10**9)
    except Exception:
        pass
    return {"text": f"Đã đưa đề xuất “{x['title']}” lên bảng, chờ anh duyệt.", "id": x["id"]}


def decide(iid: str, decision: str, note: str = "", due_days: int = 7) -> dict:
    """Anh quyết: duyet | lam_ro | tu_choi. Duyệt -> tự giao việc cho phòng phụ trách."""
    with _LOCK:
        d = _load()
        x = d["items"].get(iid)
        if not x:
            raise ValueError("Không tìm thấy đề xuất")
        if decision == "duyet":
            x["status"] = "da_duyet"
            x["due"] = (dt.date.today() + dt.timedelta(days=max(1, int(due_days or 7)))).isoformat()
            msg = f"Đã duyệt, giao {DEPTS[x['assign_to']]['name']} làm trước {x['due'][8:10]}/{x['due'][5:7]}"
        elif decision == "lam_ro":
            x["status"] = "can_lam_ro"
            msg = "Đã yêu cầu làm rõ"
        elif decision == "tu_choi":
            x["status"] = "tu_choi"
            msg = "Đã từ chối"
        else:
            raise ValueError("Quyết định không hợp lệ")
        if note:
            x["note"] = note[:600]
        x["updated"] = _now()
        _log(d, "Anh Huy", f"{msg}: {x['title']}")
        _save(d)
    return {"text": f"{msg}: “{x['title']}”.", "item": x}


def progress(iid: str, status: str, result: str = "", by: str = "") -> dict:
    """Phòng phụ trách cập nhật: dang_lam | xong (kèm kết quả) | can_lam_ro."""
    with _LOCK:
        d = _load()
        x = d["items"].get(iid)
        if not x:
            raise ValueError("Không tìm thấy đề xuất")
        if status not in ("dang_lam", "xong", "can_lam_ro"):
            raise ValueError("Trạng thái không hợp lệ")
        if status in ("dang_lam", "xong") and x["status"] not in ("da_duyet", "dang_lam", "xong"):
            raise ValueError("Chỉ triển khai việc anh đã duyệt")
        x["status"] = status
        if result:
            x["result"] = result[:1500]
        x["updated"] = _now()
        _log(d, by or DEPTS[x["assign_to"]]["name"], f"{STATUS[status]}: {x['title']}")
        _save(d)
    return {"text": f"Đã cập nhật “{x['title']}”: {STATUS[status]}."}


def overview(status: str = "") -> dict:
    d = _load()
    items = sorted(d["items"].values(), key=lambda x: (x["status"] not in ("cho_duyet", "can_lam_ro"), x["updated"]), reverse=False)
    items = sorted(items, key=lambda x: x["updated"], reverse=True)
    if status in STATUS:
        items = [x for x in items if x["status"] == status]
    counts = {k: sum(1 for x in d["items"].values() if x["status"] == k) for k in STATUS}
    by_dept = {k: {"name": v["name"], "desc": v["desc"], "kind": v["kind"], "color": v["color"],
                   "open": sum(1 for x in d["items"].values() if x["assign_to"] == k and x["status"] in ("da_duyet", "dang_lam")),
                   "waiting": sum(1 for x in d["items"].values() if x["dept"] == k and x["status"] in ("cho_duyet", "can_lam_ro"))} for k, v in DEPTS.items()}
    queue = counts["cho_duyet"] + counts["can_lam_ro"]
    return {"text": f"Bảng phòng ban: {queue} đề xuất chờ anh quyết, {counts['da_duyet'] + counts['dang_lam']} việc đang triển khai.",
            "items": items[:300], "counts": counts, "depts": by_dept, "statuses": STATUS, "prios": PRIO, "log": d["log"][-40:][::-1]}


def brief() -> str:
    """Một đoạn ngắn cho bản tin sáng: gì chờ anh, gì đến hạn."""
    d = _load()
    today = dt.date.today().isoformat()
    wait = [x for x in d["items"].values() if x["status"] in ("cho_duyet", "can_lam_ro")]
    due = [x for x in d["items"].values() if x["status"] in ("da_duyet", "dang_lam") and x.get("due") and x["due"] <= today]
    out = []
    if wait:
        out.append(f"📋 {len(wait)} đề xuất chờ anh quyết: " + "; ".join(f"{DEPTS[x['dept']]['name']}: {x['title']}" for x in wait[:4]))
    if due:
        out.append(f"⏰ {len(due)} việc đến hạn: " + "; ".join(x["title"] for x in due[:4]))
    return "\n".join(out)
