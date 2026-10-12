"""Lịch Lark của chủ nhân (đọc lịch + duyệt lời mời họp) qua OAuth người dùng.
Đăng nhập 1 lần trong Mini App (Kết nối > Lịch Lark). Token được tự gia hạn bằng refresh token
(lưu ở data/lark_user.json, quyền 600, không in ra log). Lark không cho bot tự đọc lịch cá nhân nên cần bước này."""
import datetime as dt
import json
import logging
import os
import threading
import time

import requests

from config import DATA_DIR

log = logging.getLogger("lark-cal")
TOKEN_FILE = DATA_DIR / "lark_user.json"
SCOPES = "calendar:calendar calendar:calendar:readonly task:task:read task:task:write task:tasklist:read task:tasklist:write offline_access"
_lock = threading.Lock()


def _api() -> str:
    return os.getenv("LARK_DOMAIN", "https://open.larksuite.com").rstrip("/")


def ready() -> bool:
    try:
        d = json.loads(TOKEN_FILE.read_text())
        return bool(d.get("refresh_token")) and d.get("refresh_expires_at", 0) > time.time()
    except Exception:
        return False


def _save(d: dict):
    TOKEN_FILE.write_text(json.dumps(d))
    os.chmod(TOKEN_FILE, 0o600)


def _store(resp: dict, extra: dict | None = None):
    now = time.time()
    d = {"access_token": resp["access_token"], "expires_at": now + int(resp.get("expires_in", 7200)) - 120,
         "refresh_token": resp.get("refresh_token", ""),
         "refresh_expires_at": now + int(resp.get("refresh_token_expires_in", resp.get("refresh_expires_in", 30 * 86400)))}
    d.update(extra or {})
    _save(d)
    return d


def exchange(code: str, redirect_uri: str) -> str:
    """Đổi code (sau khi chủ nhân bấm Cho phép) lấy token, lưu lại. Trả về tên lịch chính."""
    r = requests.post(f"{_api()}/open-apis/authen/v2/oauth/token", timeout=30, json={
        "grant_type": "authorization_code", "client_id": os.getenv("LARK_APP_ID", ""),
        "client_secret": os.getenv("LARK_APP_SECRET", ""), "code": code, "redirect_uri": redirect_uri}).json()
    if not r.get("access_token"):
        raise RuntimeError(f"Lark không cấp quyền: {r.get('error_description') or r.get('msg') or r.get('error')}")
    if not r.get("refresh_token"):
        log.warning("Lark không trả refresh token (thiếu quyền offline_access)")
    d = _store(r)
    me = _get("/open-apis/authen/v1/user_info", tok=d["access_token"])
    cal = _primary(d["access_token"])
    d.update(open_id=me.get("open_id", ""), name=me.get("name", ""), calendar_id=cal.get("calendar_id", ""))
    _save(d)
    return cal.get("summary") or "Lịch chính"


def _token() -> str:
    with _lock:
        try:
            d = json.loads(TOKEN_FILE.read_text())
        except Exception:
            raise RuntimeError("Chưa kết nối lịch Lark (Thêm > Kết nối > Lịch Lark).")
        if d.get("expires_at", 0) > time.time():
            return d["access_token"]
        if not d.get("refresh_token") or d.get("refresh_expires_at", 0) < time.time():
            raise RuntimeError("Phiên lịch Lark đã hết hạn, hãy kết nối lại (Thêm > Kết nối > Lịch Lark).")
        r = requests.post(f"{_api()}/open-apis/authen/v2/oauth/token", timeout=30, json={
            "grant_type": "refresh_token", "client_id": os.getenv("LARK_APP_ID", ""),
            "client_secret": os.getenv("LARK_APP_SECRET", ""), "refresh_token": d["refresh_token"]}).json()
        if not r.get("access_token"):
            raise RuntimeError(f"Không gia hạn được lịch Lark: {r.get('error_description') or r.get('msg')}. Hãy kết nối lại.")
        keep = {k: d[k] for k in ("open_id", "name", "calendar_id") if k in d}
        return _store(r, keep)["access_token"]


def _req(method: str, path: str, tok: str | None = None, **kw) -> dict:
    r = requests.request(method, _api() + path, headers={"Authorization": f"Bearer {tok or _token()}"}, timeout=30, **kw)
    d = r.json()
    if d.get("code") not in (0, None):
        raise RuntimeError(f"Lark: {d.get('msg')} (mã {d.get('code')})")
    return d.get("data", {})


def _get(path: str, tok: str | None = None, **params) -> dict:
    return _req("GET", path, tok, params=params)


def _primary(tok: str | None = None) -> dict:
    d = _req("POST", "/open-apis/calendar/v4/calendars/primary", tok)
    cals = d.get("calendars") or []
    return (cals[0].get("calendar") if cals else {}) or {}


def _meta() -> dict:
    d = json.loads(TOKEN_FILE.read_text())
    if not d.get("calendar_id"):
        d["calendar_id"] = _primary().get("calendar_id", "")
        _save(d)
    return d


def _ts(t: dict, tz) -> tuple[dt.datetime | None, bool]:
    if t.get("date"):
        return dt.datetime.combine(dt.date.fromisoformat(t["date"]), dt.time.min, tzinfo=tz), True
    return dt.datetime.fromtimestamp(int(t.get("timestamp", 0)), tz), False


def _instances(start: dt.datetime, end: dt.datetime) -> list[dict]:
    cid = _meta()["calendar_id"]
    d = _get(f"/open-apis/calendar/v4/calendars/{cid}/events/instance_view",
             start_time=str(int(start.timestamp())), end_time=str(int(end.timestamp())), user_id_type="open_id")
    return [e for e in (d.get("items") or []) if e.get("status") != "cancelled"]


def _my_status(e: dict, meta: dict) -> str:
    """accept | tentative | decline | needs_action | organizer"""
    org = (e.get("event_organizer") or {}).get("user_id")
    if org and org == meta.get("open_id"):
        return "organizer"
    for k in ("self_rsvp_status", "rsvp_status"):
        if e.get(k):
            return e[k]
    try:
        d = _get(f"/open-apis/calendar/v4/calendars/{meta['calendar_id']}/events/{e['event_id']}/attendees",
                 user_id_type="open_id", page_size=100)
        for a in d.get("items") or []:
            if a.get("user_id") == meta.get("open_id"):
                return a.get("rsvp_status") or "needs_action"
    except Exception:
        pass
    return "accept"


def events(day: dt.date, tz) -> list[dict]:
    start = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
    out = []
    for e in _instances(start, start + dt.timedelta(days=1)):
        s, all_day = _ts(e.get("start_time") or {}, tz)
        en, _ = _ts(e.get("end_time") or {}, tz)
        out.append({"id": "lark:" + e.get("event_id", ""), "title": e.get("summary") or "(không tiêu đề)",
                    "start": None if all_day else s, "end": None if all_day else en, "all_day": all_day,
                    "location": (e.get("location") or {}).get("name", ""), "priority": "normal",
                    "source": "Lark", "editable": False})
    return out


def invites(days: int = 21, tz=None) -> list[dict]:
    meta = _meta()
    now = dt.datetime.now(tz)
    out = []
    for e in _instances(now, now + dt.timedelta(days=min(days, 40))):
        st = _my_status(e, meta)
        if st not in ("needs_action", "tentative"):
            continue
        s, all_day = _ts(e.get("start_time") or {}, tz)
        en, _ = _ts(e.get("end_time") or {}, tz)
        out.append({"id": e.get("event_id", ""), "source": "lark", "title": e.get("summary") or "(không tiêu đề)",
                    "start": s.isoformat(), "end": en.isoformat() if en else s.isoformat(), "all_day": all_day,
                    "location": (e.get("location") or {}).get("name", ""),
                    "organizer": (e.get("event_organizer") or {}).get("display_name", ""),
                    "status": "maybe" if st == "tentative" else "pending",
                    "description": (e.get("description") or "")[:500], "link": e.get("app_link", "")})
    return out


def rsvp(event_id: str, status: str):
    """status: yes | no | maybe"""
    cid = _meta()["calendar_id"]
    _req("POST", f"/open-apis/calendar/v4/calendars/{cid}/events/{event_id}/reply",
         json={"rsvp_status": {"yes": "accept", "no": "decline", "maybe": "tentative"}.get(status, "accept")})
