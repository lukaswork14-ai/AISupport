"""Khách đăng ký: email để lại trên landing page / Marketplace công khai -> phễu liên hệ cho phòng GTM.

Lưu ở DATA_DIR/waitlist.json (danh sách dict). Mỗi khách: email, src, at, status, note, contacted_at.
"""
import datetime as dt
import json
import re
import threading

from config import DATA_DIR

FILE = DATA_DIR / "waitlist.json"
_LOCK = threading.Lock()
EMAIL_RE = re.compile(r"^[^@\s<>]{1,64}@[^@\s<>]{1,190}\.[A-Za-z]{2,24}$")
STATUS = {"moi": "Mới", "da_lien_he": "Đã liên hệ", "dang_trao_doi": "Đang trao đổi", "dung_thu": "Đang dùng thử",
          "khach": "Thành khách hàng", "bo_qua": "Bỏ qua"}


def _load() -> list[dict]:
    try:
        return json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else []
    except Exception:
        return []


def _save(rows: list[dict]):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(rows[-5000:], ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def add(email: str, src: str = "", interest: str = "") -> bool:
    """Thêm khách mới (bỏ qua email trùng nhưng ghi thêm sở thích). Trả True nếu là khách mới."""
    email = (email or "").strip().lower()[:254]
    if not EMAIL_RE.match(email):
        raise ValueError("Email chưa đúng, anh kiểm tra lại nhé.")
    with _LOCK:
        rows = _load()
        for r in rows:
            if r.get("email") == email:
                if interest and interest not in r.setdefault("interests", []):
                    r["interests"].append(interest[:80])
                    _save(rows)
                return False
        rows.append({"email": email, "src": (src or "")[:120], "at": _now(), "status": "moi",
                     "interests": [interest[:80]] if interest else []})
        _save(rows)
        n = len(rows)
    try:
        from core import security
        what = f" quan tâm “{interest}”" if interest else ""
        security.alert_once(f"wl:{email}", f"🎉 Có khách đăng ký mới{what}: {email} (tổng {n}). Xem ở app › Khách đăng ký.", every=10**9)
    except Exception:
        pass
    return True


def _src_label(s: str) -> str:
    s = s or ""
    if s.startswith("market:"):
        return "Marketplace"
    if "utm_source=" in s:
        m = re.search(r"utm_source=([^&]+)", s)
        return m.group(1)[:30] if m else "Landing"
    return "Landing"


def overview() -> dict:
    rows = sorted(_load(), key=lambda r: r.get("at", ""), reverse=True)
    today = dt.date.today()
    days = [(today - dt.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
    per_day = {d: 0 for d in days}
    by_status = {k: 0 for k in STATUS}
    by_src: dict[str, int] = {}
    for r in rows:
        r.setdefault("status", "moi")
        d = (r.get("at") or "")[:10]
        if d in per_day:
            per_day[d] += 1
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
        lab = _src_label(r.get("src", ""))
        r["src_label"] = lab
        by_src[lab] = by_src.get(lab, 0) + 1
    total = len(rows)
    contacted = total - by_status.get("moi", 0) - by_status.get("bo_qua", 0)
    text = (f"Có {total} khách đăng ký, {by_status.get('moi', 0)} chưa liên hệ, {by_status.get('khach', 0)} đã thành khách hàng."
            if total else "Chưa có khách đăng ký nào từ landing page.")
    return {"text": text, "items": rows, "total": total, "contacted": contacted, "by_status": by_status, "by_src": by_src,
            "per_day": [{"d": d, "n": per_day[d]} for d in days], "statuses": STATUS}


def set_status(email: str, status: str, note: str = "") -> dict:
    if status not in STATUS:
        raise ValueError("Trạng thái không hợp lệ")
    email = (email or "").strip().lower()
    with _LOCK:
        rows = _load()
        r = next((x for x in rows if x.get("email") == email), None)
        if not r:
            raise ValueError("Không tìm thấy khách này")
        r["status"] = status
        r["updated"] = _now()
        if status != "moi" and not r.get("contacted_at"):
            r["contacted_at"] = _now()
        if note is not None and note != "":
            r["note"] = note.strip()[:1000]
        _save(rows)
    return {"text": f"Đã chuyển {email} sang “{STATUS[status]}”.", "item": r}
