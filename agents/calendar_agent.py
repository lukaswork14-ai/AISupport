"""Agent 1: Trợ lý nhắc lịch. Gộp Google Calendar + các link ICS (Lark, Apple...)."""
import datetime as dt
from zoneinfo import ZoneInfo

import os

import requests

from config import TIMEZONE

TZ = ZoneInfo(TIMEZONE)


def _day_bounds(day: dt.date):
    start = dt.datetime.combine(day, dt.time.min, tzinfo=TZ)
    return start, start + dt.timedelta(days=1)


def ics_sources() -> list[tuple[str, str]]:
    """(nhãn, url) — đọc lại .env mỗi lần nên kết nối mới có hiệu lực ngay."""
    from agents import gcal_bridge
    out = []
    from agents import lark_calendar
    keys = [("GOOGLE_CAL_ICS", "Google")] if not gcal_bridge.ready() else []
    keys += [] if lark_calendar.ready() else [("LARK_ICS", "Lark")]
    keys += [("ICS_URLS", "Lịch")]
    for key, label in keys:
        for u in os.getenv(key, "").split(","):
            if u.strip():
                out.append((label, u.strip()))
    return out


def _google_events(day: dt.date) -> list[dict]:
    from agents import gcal_bridge
    if gcal_bridge.ready():  # cầu nối Apps Script: có màu ưu tiên + sửa được
        try:
            return gcal_bridge.list_events(day, TZ)
        except Exception:
            pass  # lỗi cầu nối -> dùng iCal bên dưới
    if os.getenv("GOOGLE_CAL_ICS", "").strip():
        return []  # đã dùng iCal bí mật của Google, không cần OAuth
    try:
        from googleapiclient.discovery import build
        from google_auth import get_credentials
        service = build("calendar", "v3", credentials=get_credentials(), cache_discovery=False)
    except Exception as e:  # chưa kết nối Google
        return [{"start": None, "end": None, "title": f"(Không đọc được Google Calendar: {e})",
                 "location": "", "source": "system", "all_day": True}]
    start, end = _day_bounds(day)
    out = []
    for cal in service.calendarList().list().execute().get("items", []):
        if cal.get("selected") is False:
            continue
        events = service.events().list(
            calendarId=cal["id"], timeMin=start.isoformat(), timeMax=end.isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=50,
        ).execute().get("items", [])
        for ev in events:
            s, e = ev["start"], ev["end"]
            all_day = "date" in s
            s_dt = None if all_day else dt.datetime.fromisoformat(s["dateTime"]).astimezone(TZ)
            e_dt = None if all_day else dt.datetime.fromisoformat(e["dateTime"]).astimezone(TZ)
            out.append({
                "start": s_dt, "end": e_dt, "all_day": all_day,
                "title": ev.get("summary", "(không tiêu đề)"),
                "location": ev.get("location") or ev.get("hangoutLink") or "",
                "source": "Google · " + cal.get("summary", ""),
            })
    return out


def _ics_events(day: dt.date) -> list[dict]:
    sources = ics_sources()
    if not sources:
        return []
    import icalendar
    import recurring_ical_events
    start, end = _day_bounds(day)
    out = []
    for i, (label, url) in enumerate(sources, 1):
        try:
            r = requests.get(url.replace("webcal://", "https://"), timeout=30)
            r.raise_for_status()
            cal = icalendar.Calendar.from_ical(r.content)
            for ev in recurring_ical_events.of(cal).between(start, end):
                s = ev.get("DTSTART").dt
                e = ev.get("DTEND").dt if ev.get("DTEND") else None
                all_day = not isinstance(s, dt.datetime)
                if not all_day:
                    s = s.astimezone(TZ) if s.tzinfo else s.replace(tzinfo=TZ)
                    if e is not None and isinstance(e, dt.datetime):
                        e = e.astimezone(TZ) if e.tzinfo else e.replace(tzinfo=TZ)
                out.append({
                    "start": None if all_day else s, "end": None if all_day else e,
                    "all_day": all_day, "title": str(ev.get("SUMMARY", "(không tiêu đề)")),
                    "location": str(ev.get("LOCATION", "") or ""), "source": label, "priority": "normal",
                })
        except Exception as ex:
            out.append({"start": None, "end": None, "all_day": True, "location": "",
                        "title": f"(Không đọc được lịch {label}: {ex})", "source": "system"})
    return out


def _lark_events(day: dt.date) -> list[dict]:
    from agents import lark_calendar
    if not lark_calendar.ready():
        return []
    try:
        return lark_calendar.events(day, TZ)
    except Exception as e:
        return [{"start": None, "end": None, "all_day": True, "location": "",
                 "title": f"(Không đọc được lịch Lark: {e})", "source": "system"}]


def get_events(day: dt.date) -> list[dict]:
    events = _google_events(day) + _lark_events(day) + _ics_events(day)
    # bỏ trùng (cùng giờ + cùng tên, thường do đồng bộ chéo giữa các lịch)
    seen, unique = set(), []
    for e in events:
        key = (e["start"], e["title"].strip().lower())
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda e: (e["start"] is not None, e["start"] or dt.datetime.min.replace(tzinfo=TZ)))
    return unique


def find_conflicts(events: list[dict]) -> list[tuple[dict, dict]]:
    timed = [e for e in events if e["start"] and e["end"]]
    return [(a, b) for i, a in enumerate(timed) for b in timed[i + 1:]
            if a["start"] < b["end"] and b["start"] < a["end"]]


def format_schedule(day: dt.date, header: str | None = None) -> str:
    events = get_events(day)
    weekday = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][day.weekday()]
    lines = [header or f"📅 Lịch {weekday}, {day:%d/%m/%Y}"]
    if not events:
        lines.append("\nKhông có sự kiện nào. Một ngày trống để làm việc sâu 🎯")
        return "\n".join(lines)
    lines.append("")
    dot = {"red": "🔴 ", "orange": "🟠 ", "blue": "🔵 "}
    for e in events:
        when = "Cả ngày" if e["all_day"] else f"{e['start']:%H:%M}–{e['end']:%H:%M}"
        loc = f"\n    📍 {e['location']}" if e["location"] else ""
        lines.append(f"• {when}  {dot.get(e.get('priority'), '')}{e['title']}{loc}")
    conflicts = find_conflicts(events)
    if conflicts:
        lines.append("\n⚠️ Trùng lịch:")
        for a, b in conflicts:
            lines.append(f"  - “{a['title']}” và “{b['title']}”")
    return "\n".join(lines)


def tomorrow_reminder() -> str:
    tomorrow = dt.datetime.now(TZ).date() + dt.timedelta(days=1)
    return format_schedule(tomorrow, header=None)


def serialize(events: list[dict]) -> list[dict]:
    """Dạng gọn cho Mini App."""
    return [{"id": e.get("id"), "title": e["title"], "all_day": e["all_day"],
             "start": e["start"].strftime("%H:%M") if e["start"] else "", "end": e["end"].strftime("%H:%M") if e["end"] else "",
             "location": e.get("location", ""), "priority": e.get("priority", "normal"), "source": e.get("source", ""),
             "editable": bool(e.get("editable"))} for e in events if e.get("source") != "system"]


PARSE_PROMPT = """Chuyển câu mô tả lịch tiếng Việt sau thành JSON. Hôm nay là {today} ({weekday}), múi giờ {tz}.
Trả về DUY NHẤT JSON: {{"title": tiêu đề ngắn gọn, "date": "YYYY-MM-DD", "start": "HH:MM" hoặc "" nếu cả ngày,
"duration_min": số phút (mặc định 60), "all_day": true/false, "location": "" hoặc địa điểm,
"priority": một trong red (gấp và quan trọng) | orange (quan trọng chưa gấp) | blue (gấp ít quan trọng) | normal}}.
"3h chiều" = 15:00, "sáng mai" = ngày mai 09:00 nếu không nói giờ. Câu: {text}"""


def parse_text(text: str) -> dict:
    import json
    import re
    from config import LLM_MODEL, TIMEZONE
    from llm import LLM_EXTRA, make_client
    now = dt.datetime.now(TZ)
    wd = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"][now.weekday()]
    resp = make_client().chat.completions.create(
        model=LLM_MODEL, extra_body=LLM_EXTRA, max_tokens=3000, temperature=0.3,
        messages=[{"role": "user", "content": PARSE_PROMPT.format(today=now.date().isoformat(), weekday=wd, tz=TIMEZONE, text=text)}])
    m = re.search(r"\{.*\}", resp.choices[0].message.content or "", re.S)
    if not m:
        raise RuntimeError("Chưa hiểu được câu này, bạn điền tay giúp nhé.")
    d = json.loads(m.group(0))
    d.setdefault("duration_min", 60)
    d["priority"] = d.get("priority") if d.get("priority") in ("red", "orange", "blue") else "normal"
    return d
