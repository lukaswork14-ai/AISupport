"""Đo kích hoạt và North Star phía máy chủ (thẻ 16, họp liên phòng ban 17/10/2026).

Ba sự kiện, chỉ gồm id người dùng + mốc giờ, KHÔNG chứa nội dung của khách:
- signup:        tạo tài khoản (HQ) hoặc instance khách khởi động lần đầu
- first_result:  kết quả đầu tiên (biên bản, bản tin, câu trả lời chat hoặc biên bản thử)
- active_day:    một ngày có dùng (tối đa 1 lần/ngày/người)

Định nghĩa (Company OS / lộ trình GTM):
- Kích hoạt 24 giờ = có first_result trong 24 giờ sau signup.
- North Star = số người có >= 4 ngày hoạt động trong 7 ngày gần nhất.

Dữ liệu: DATA_DIR/activation.json. Mỗi instance khách có DATA_DIR riêng nên số liệu không trộn giữa các khách.
Mọi lỗi ghi đều bị nuốt: đo lường không bao giờ làm hỏng luồng chính.
"""
import datetime as dt
import json
import statistics
import threading

from config import DATA_DIR

FILE = DATA_DIR / "activation.json"
_LOCK = threading.Lock()
KEEP_DAYS = 120


def _now() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        if isinstance(d, dict) and isinstance(d.get("users"), dict):
            return d
    except Exception:
        pass
    return {"users": {}}


def _save(d: dict):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    tmp.replace(FILE)


def _user(d: dict, uid: str) -> dict:
    return d["users"].setdefault(str(uid)[:40], {"signup": "", "first_result": "", "first_kind": "", "days": []})


def signup(uid) -> None:
    try:
        with _LOCK:
            d = _load()
            u = _user(d, uid)
            if not u["signup"]:
                u["signup"] = _now().isoformat()
                _save(d)
    except Exception:
        pass


def first_result(uid, kind: str = "") -> None:
    """Ghi kết quả đầu tiên (chỉ lần đầu) và tính luôn là một ngày hoạt động."""
    try:
        with _LOCK:
            d = _load()
            u = _user(d, uid)
            changed = False
            if not u["signup"]:
                u["signup"] = _now().isoformat()
                changed = True
            if not u["first_result"]:
                u["first_result"] = _now().isoformat()
                u["first_kind"] = str(kind)[:20]
                changed = True
            changed = _mark_day(u) or changed
            if changed:
                _save(d)
    except Exception:
        pass


def _mark_day(u: dict) -> bool:
    today = dt.date.today().isoformat()
    if u["days"] and u["days"][-1] == today:
        return False
    u["days"].append(today)
    cut = (dt.date.today() - dt.timedelta(days=KEEP_DAYS)).isoformat()
    u["days"] = [x for x in u["days"] if x >= cut]
    return True


def active_day(uid) -> None:
    try:
        with _LOCK:
            d = _load()
            u = _user(d, uid)
            if not u["signup"]:
                u["signup"] = _now().isoformat()
            if _mark_day(u):
                _save(d)
    except Exception:
        pass


def summary(days: int = 30, prefix: str = "") -> dict:
    """Tỷ lệ kích hoạt 24 giờ (người đăng ký trong `days` ngày qua, đã đủ 24 giờ), thời gian tới kết quả đầu, North Star."""
    d = _load()
    now = _now()
    since = now - dt.timedelta(days=days)
    week = {(dt.date.today() - dt.timedelta(days=i)).isoformat() for i in range(7)}
    eligible = activated = 0
    minutes: list[float] = []
    north = 0
    for uid, u in d["users"].items():
        if prefix and not uid.startswith(prefix):
            continue
        if len([x for x in u.get("days", []) if x in week]) >= 4:
            north += 1
        try:
            s = dt.datetime.fromisoformat(u["signup"]) if u.get("signup") else None
        except ValueError:
            s = None
        if not s or s < since:
            continue
        f = None
        if u.get("first_result"):
            try:
                f = dt.datetime.fromisoformat(u["first_result"])
                minutes.append(max(0.0, (f - s).total_seconds() / 60))
            except ValueError:
                f = None
        if now - s >= dt.timedelta(hours=24):
            eligible += 1
            if f and f - s <= dt.timedelta(hours=24):
                activated += 1
    rate = round(100 * activated / eligible) if eligible else None
    med = round(statistics.median(minutes), 1) if minutes else None
    text = (f"Kích hoạt 24 giờ: {rate}% ({activated}/{eligible})" if rate is not None else "Kích hoạt 24 giờ: chưa đủ người đủ 24 giờ")
    text += f" · tới kết quả đầu (trung vị): {med} phút" if med is not None else " · chưa có kết quả đầu"
    text += f" · North Star (≥4 ngày/7 ngày): {north}"
    return {"text": text, "users": sum(1 for k in d["users"] if k.startswith(prefix)), "eligible": eligible, "activated": activated, "rate_pct": rate,
            "median_minutes_to_first": med, "north_star": north}
