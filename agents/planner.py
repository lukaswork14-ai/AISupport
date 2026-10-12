"""Lịch trình ngày (routine) do superHuy đề xuất: ghép lịch họp cố định + việc tới hạn + thói quen + mục tiêu dài hạn
+ những gì superHuy biết về anh, thành một thời khoá biểu tối ưu cho ngày. Anh chọn khối nào thì đưa khối đó vào Google Calendar
(gắn màu ưu tiên). Lưu: data/plans.json theo ngày."""
import datetime as dt
import json
import re
import threading

from config import DATA_DIR, LLM_MODEL
from core import memory, profile
from llm import ask_json

FILE = DATA_DIR / "plans.json"
KINDS = {"meeting": "Lịch họp", "focus": "Làm việc sâu", "task": "Việc cần xong", "habit": "Thói quen", "workout": "Tập luyện",
         "meal": "Ăn uống", "rest": "Nghỉ & hồi phục", "family": "Gia đình & quan hệ", "learn": "Học", "admin": "Việc vặt & tin nhắn"}
COLOR = {"focus": "red", "task": "red", "workout": "orange", "learn": "orange", "habit": "orange", "family": "blue", "admin": "blue"}
_lock = threading.Lock()


def _tz():
    from agents.calendar_agent import TZ
    return TZ


def _load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(d: dict):
    keep = dict(sorted(d.items())[-60:])
    FILE.write_text(json.dumps(keep, ensure_ascii=False, indent=1), encoding="utf-8")


def get(date: str) -> dict | None:
    return _load().get(date)


PROMPT = """Bạn là superHuy, trợ lý lập kế hoạch ngày cho anh Huy. {profile}
{memory}
{safety}
NGÀY CẦN LẬP: {weekday} {date}. Giờ hiện tại: {now}.
LỊCH CỐ ĐỊNH (không được dời, không xếp chồng lên): {events}
VIỆC ĐẾN HẠN / QUÁ HẠN: {tasks}
THÓI QUEN CẦN LÀM HÔM NAY: {habits}
MỤC TIÊU DÀI HẠN: {goals}
GHI CHÚ CỦA ANH CHO HÔM NAY: {note}

Lập thời khoá biểu cả ngày (từ lúc thức dậy ~05:30 đến ngủ trước 23:30), tối ưu cho các mục tiêu nhưng thực tế với lịch của CEO:
- Giữ nguyên lịch cố định (kind "meeting", fixed true).
- Xếp 1-2 khối làm việc sâu 60-120 phút vào khung năng lượng tốt nhất, ưu tiên việc quan trọng nhất.
- Xếp thói quen vào giờ gợi ý của chúng nếu được; buổi tập phù hợp mục tiêu VMM/thon gọn, có khởi động/giãn cơ.
- Có bữa ăn, khoảng nghỉ ngắn, khung xử lý tin nhắn/email gom lại, thời gian cho gia đình buổi tối, wind-down trước khi ngủ.
- Nếu giờ hiện tại đã qua phần lớn buổi sáng, chỉ xếp từ bây giờ trở đi.
Trả về DUY NHẤT JSON:
{{"summary": "2-3 câu: trọng tâm của ngày và lý do", "focus": "1 việc quan trọng nhất hôm nay",
 "blocks": [{{"start": "HH:MM", "end": "HH:MM", "title": "ngắn gọn", "kind": "{kinds}", "fixed": true/false,
              "habit_id": "id nếu là thói quen", "task_id": "id nếu là việc", "note": "≤ 70 ký tự"}}]}}"""


def _context(day: dt.date) -> dict:
    from agents import calendar_agent, growth, tasks_hub
    try:
        evs = [e for e in calendar_agent.get_events(day) if e.get("source") != "system"]
        events = "; ".join(("Cả ngày" if e["all_day"] else f"{e['start']:%H:%M}-{e['end']:%H:%M}") + " " + e["title"] for e in evs) or "(trống)"
    except Exception as e:
        evs, events = [], f"(không đọc được lịch: {e})"
    try:
        items = tasks_hub.collect()["items"]
        due = [t for t in items if not t["done"] and t.get("due") and t["due"].date() <= day][:12]
        tasks = "; ".join(f"[{t['id']}] {t['title']}" + (" (quá hạn)" if t["overdue"] else "") for t in due) or "(không có)"
    except Exception:
        tasks = "(không đọc được)"
    g = growth.overview()
    habits = "; ".join(f"[{h['id']}] {h['title']}" + (f" lúc {h['time']}" if h.get("time") else "") + (f" ({h['target']})" if h.get("target") else "")
                       for h in g["habits"] if h["due_today"] and not h["done_today"]) or "(không có)"
    goals = "; ".join(x["title"] + (f" (còn {x['days_left']} ngày)" if x.get("days_left") is not None else "") for x in g["goals"]) or "(chưa có)"
    return {"events": events, "tasks": tasks, "habits": habits, "goals": goals, "evs": evs}


def plan(date: str = "", note: str = "") -> dict:
    from agents.growth import SAFETY
    tz = _tz()
    now = dt.datetime.now(tz)
    day = dt.date.fromisoformat(date[:10]) if date else now.date()
    c = _context(day)
    prompt = PROMPT.format(profile=profile.brief(), memory=memory.context(2500), safety=SAFETY,
                           weekday=["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"][day.weekday()],
                           date=day.isoformat(), now=now.strftime("%H:%M") if day == now.date() else "05:00",
                           events=c["events"], tasks=c["tasks"], habits=c["habits"], goals=c["goals"], note=note or "(không)",
                           kinds="|".join(KINDS))
    res = ask_json(prompt, 8000, 2, ok=lambda x: isinstance(x, dict) and bool(x.get("blocks")), tag="planner")
    if not res or not res.get("blocks"):
        raise RuntimeError("superHuy chưa lập được lịch trình, thử lại sau ít phút.")
    blocks = []
    for b in res["blocks"]:
        try:
            s, e = b["start"][:5], b["end"][:5]
            dt.time.fromisoformat(s)
            dt.time.fromisoformat(e)
        except Exception:
            continue
        blocks.append({"start": s, "end": e, "title": str(b.get("title", ""))[:80], "kind": b.get("kind") if b.get("kind") in KINDS else "focus",
                       "fixed": bool(b.get("fixed")), "habit_id": b.get("habit_id") or "", "task_id": b.get("task_id") or "",
                       "note": str(b.get("note", ""))[:120], "added": False})
    blocks.sort(key=lambda b: b["start"])
    out = {"date": day.isoformat(), "summary": res.get("summary", ""), "focus": res.get("focus", ""), "blocks": blocks,
           "note": note, "at": now.isoformat(timespec="minutes")}
    with _lock:
        d = _load()
        d[day.isoformat()] = out
        _save(d)
    return {**out, "text": _as_text(out)}


def _as_text(p: dict) -> str:
    lines = [f"🗓 Lịch trình {p['date'][8:10]}/{p['date'][5:7]} do superHuy đề xuất", p.get("summary", "")]
    if p.get("focus"):
        lines.append(f"🎯 Trọng tâm: {p['focus']}")
    lines.append("")
    lines += [f"{b['start']}–{b['end']}  {b['title']}" + (" 📌" if b["fixed"] else "") for b in p["blocks"]]
    return "\n".join(lines)


def apply(date: str, indexes: list[int] | None = None) -> dict:
    """Đưa các khối (không cố định) vào Google Calendar. indexes=None: tất cả khối focus/workout/learn/task/family."""
    from agents import gcal_bridge
    if not gcal_bridge.ready():
        raise ValueError("Chưa bật tạo lịch Google (Thêm › Kết nối › Tạo lịch Google).")
    tz = _tz()
    with _lock:
        d = _load()
        p = d.get(date[:10])
        if not p:
            raise ValueError("Chưa có lịch trình cho ngày này")
        idx = indexes if indexes is not None else [i for i, b in enumerate(p["blocks"])
                                                   if not b["fixed"] and b["kind"] in ("focus", "workout", "learn", "task", "family")]
        day = dt.date.fromisoformat(p["date"])
        n = 0
        for i in idx:
            if not 0 <= i < len(p["blocks"]):
                continue
            b = p["blocks"][i]
            if b["fixed"] or b.get("added"):
                continue
            s = dt.datetime.combine(day, dt.time.fromisoformat(b["start"]), tz)
            e = dt.datetime.combine(day, dt.time.fromisoformat(b["end"]), tz)
            if e <= s:
                e = s + dt.timedelta(minutes=30)
            gcal_bridge.create(b["title"], s, e, False, COLOR.get(b["kind"], "normal"), "",
                               (b.get("note") or "") + "\n— superHuy lên lịch")
            b["added"] = True
            n += 1
        _save(d)
    return {"text": f"Đã đưa {n} khối vào Google Calendar." if n else "Không có khối mới nào để thêm."}
