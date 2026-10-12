"""Ghi/đọc Google Calendar qua Apps Script chạy trong tài khoản của chủ nhân (xem integrations/gcal_bridge.gs).
Cấu hình: GCAL_BRIDGE_URL (dán 1 lần trong Mini App). Khóa GCAL_BRIDGE_KEY do script tự sinh khi ghép cặp."""
import datetime as dt
import os

import requests

PRIORITIES = {  # ma trận Eisenhower
    "red": "Gấp và quan trọng",
    "orange": "Quan trọng, chưa gấp",
    "blue": "Gấp, ít quan trọng",
    "normal": "Bình thường",
}


def ready() -> bool:
    return bool(os.getenv("GCAL_BRIDGE_URL", "").strip() and os.getenv("GCAL_BRIDGE_KEY", "").strip())


def _post(payload: dict, timeout: int = 40) -> dict:
    url = os.getenv("GCAL_BRIDGE_URL", "").strip()
    if not url:
        raise RuntimeError("Chưa kết nối cầu nối Google Calendar (Thêm > Kết nối > Lịch).")
    r = requests.post(url, json={**payload, "key": os.getenv("GCAL_BRIDGE_KEY", "")}, timeout=timeout)
    try:
        d = r.json()
    except Exception:
        raise RuntimeError(f"Cầu nối lịch phản hồi không hợp lệ (HTTP {r.status_code}). Kiểm tra lại link triển khai.")
    if not d.get("ok"):
        raise RuntimeError({"unauthorized": "Cầu nối lịch từ chối khóa (cần ghép cặp lại).",
                            "not_found": "Không tìm thấy sự kiện."}.get(d.get("error"), d.get("error", "Lỗi không rõ")))
    return d


def pair(url: str) -> str:
    """Ghép cặp lần đầu: script tự sinh khóa và trả về đúng 1 lần. Trả về tên lịch mặc định."""
    from core.envfile import set_env
    url = url.strip()
    if not url.startswith("https://script.google.com/"):
        raise ValueError("Link phải bắt đầu bằng https://script.google.com/ (link Web app khi Deploy).")
    r = requests.post(url, json={"action": "pair"}, timeout=40)
    d = r.json()
    set_env("GCAL_BRIDGE_URL", url)
    if d.get("ok"):
        set_env("GCAL_BRIDGE_KEY", d["key"])
        return d.get("calendar", "")
    if d.get("error") == "already_paired" and os.getenv("GCAL_BRIDGE_KEY"):
        return _post({"action": "ping"}).get("calendar", "")
    raise RuntimeError("Script đã ghép cặp với thiết bị khác. Xóa thuộc tính KEY trong Project Settings của script rồi thử lại.")


def list_events(day: dt.date, tz) -> list[dict]:
    start = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    d = _post({"action": "list", "start": start.isoformat(), "end": (start + dt.timedelta(days=1)).isoformat()})
    out = []
    for e in d.get("events", []):
        s = dt.datetime.fromisoformat(e["start"].replace("Z", "+00:00")).astimezone(tz)
        en = dt.datetime.fromisoformat(e["end"].replace("Z", "+00:00")).astimezone(tz)
        out.append({"id": e["id"], "title": e["title"] or "(không tiêu đề)", "start": None if e["allDay"] else s,
                    "end": None if e["allDay"] else en, "all_day": e["allDay"], "location": e.get("location", ""),
                    "priority": e.get("priority", "normal"), "source": "Google · " + e.get("calendar", ""),
                    "editable": bool(e.get("mine"))})
    return out


def create(title: str, start: dt.datetime, end: dt.datetime | None, all_day: bool, priority: str = "normal",
           location: str = "", description: str = "") -> str:
    d = _post({"action": "create", "title": title, "start": start.isoformat(),
               "end": (end or start + dt.timedelta(hours=1)).isoformat(), "allDay": all_day,
               "priority": priority, "location": location, "description": description})
    return d["id"]


def set_priority(event_id: str, priority: str):
    _post({"action": "set_priority", "id": event_id, "priority": priority})


def delete(event_id: str):
    _post({"action": "delete", "id": event_id})


def invites(days: int = 21) -> list[dict]:
    """Lời mời họp chưa trả lời (hoặc đang 'có thể') trong N ngày tới."""
    d = _post({"action": "invites", "days": days}, timeout=60)
    return [{"id": e["id"], "source": "google", "title": e.get("title") or "(không tiêu đề)", "start": e["start"],
             "end": e["end"], "all_day": e.get("allDay", False), "location": e.get("location", ""),
             "organizer": e.get("organizer", ""), "status": "maybe" if e.get("status") == "MAYBE" else "pending",
             "guests": e.get("guests", 0), "description": e.get("description", "")} for e in d.get("invites", [])]


def rsvp(event_id: str, status: str):
    """status: yes | no | maybe"""
    _post({"action": "rsvp", "id": event_id, "status": status})


def auto_pair() -> str | None:
    """Khi khởi động: nếu đã có link Web app mà chưa có khóa thì tự ghép cặp. Trả về thông báo hoặc None."""
    url = os.getenv("GCAL_BRIDGE_URL", "").strip()
    if not url or os.getenv("GCAL_BRIDGE_KEY", "").strip():
        return None
    try:
        name = pair(url)
        return f"📅 Đã kết nối tạo lịch Google ({name}). Giờ bạn tạo lịch, gắn màu và duyệt lời mời họp ngay trong Mini App."
    except Exception as e:
        return f"⚠️ Chưa ghép được cầu nối Google Calendar: {e}"
