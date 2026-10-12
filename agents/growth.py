"""Phát triển bản thân của superHuy: mục tiêu (có chỉ số + cột mốc), thói quen (lịch lặp, check-in, chuỗi ngày),
nhật ký chỉ số (cân nặng, km chạy...), và huấn luyện viên AI đề xuất thói quen/cột mốc/kế hoạch tuần cho từng mục tiêu.
An toàn sức khoẻ: giảm cân 0,5-1 kg/tuần, tăng khối lượng tập ≤10%/tuần, ưu tiên ngủ và hồi phục, khuyên khám sức khoẻ
trước mục tiêu sức bền lớn. Dữ liệu: data/growth.json."""
import datetime as dt
import json
import os
import re
import threading
import uuid

from config import DATA_DIR, LLM_MODEL
from core import memory, profile
from llm import LLM_EXTRA, PRECISE, ask_json, fix_vi, make_client

FILE = DATA_DIR / "growth.json"
AREAS = {"work": "Công việc", "income": "Thu nhập", "health": "Sức khoẻ", "relations": "Quan hệ", "skills": "Năng lực", "self": "Bản thân"}
WD = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
_lock = threading.Lock()


def _tz():
    from agents.calendar_agent import TZ
    return TZ


def today() -> dt.date:
    return dt.datetime.now(_tz()).date()


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    for k, v in (("goals", []), ("habits", []), ("checkins", {}), ("logs", {}), ("suggestions", {})):
        d.setdefault(k, v)
    return d


def _save(d: dict):
    FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        os.chmod(FILE, 0o600)
    except Exception:
        pass


def _id() -> str:
    return uuid.uuid4().hex[:8]


# ------------------------------------------------------------------ lịch lặp của thói quen
def due_on(h: dict, day: dt.date) -> bool:
    s = h.get("schedule") or {"type": "daily"}
    t = s.get("type", "daily")
    if t == "daily":
        return True
    if t == "weekdays":
        return day.weekday() < 5
    if t == "days":
        return day.weekday() in (s.get("days") or [])
    if t == "weekly":  # n lần/tuần: luôn hiện, đủ n lần thì coi như xong tuần
        return True
    return True


def sched_label(h: dict) -> str:
    s = h.get("schedule") or {"type": "daily"}
    t = s.get("type")
    if t == "weekdays":
        return "Thứ 2 - Thứ 6"
    if t == "days":
        return ", ".join(WD[i] for i in sorted(s.get("days") or []))
    if t == "weekly":
        return f"{s.get('times', 3)} lần/tuần"
    return "Mỗi ngày"


def _done_set(d: dict, hid: str) -> set:
    return set(d["checkins"].get(hid, []))


def _week_count(done: set, day: dt.date) -> int:
    ws = day - dt.timedelta(days=day.weekday())
    return sum(1 for i in range(7) if (ws + dt.timedelta(days=i)).isoformat() in done)


def streak(h: dict, done: set, day: dt.date | None = None) -> int:
    day = day or today()
    if (h.get("schedule") or {}).get("type") == "weekly":
        n, ws, need = 0, day - dt.timedelta(days=day.weekday()), int(h["schedule"].get("times", 3))
        if _week_count(done, day) < need:
            ws -= dt.timedelta(days=7)  # tuần này chưa đủ: tính từ tuần trước
        while _week_count(done, ws) >= need and n < 520:
            n += 1
            ws -= dt.timedelta(days=7)
        return n  # đơn vị: tuần
    n, cur = 0, day
    if cur.isoformat() not in done:
        cur -= dt.timedelta(days=1)  # hôm nay chưa làm thì không làm đứt chuỗi
    created = dt.date.fromisoformat(h.get("created", "2000-01-01")[:10])
    while cur >= created and n < 3650:
        if due_on(h, cur):
            if cur.isoformat() in done:
                n += 1
            else:
                break
        cur -= dt.timedelta(days=1)
    return n


def rate(h: dict, done: set, days: int = 30) -> float | None:
    end = today()
    start = max(end - dt.timedelta(days=days - 1), dt.date.fromisoformat(h.get("created", end.isoformat())[:10]))
    if (h.get("schedule") or {}).get("type") == "weekly":
        weeks = max(1, ((end - start).days + 1) / 7)
        return min(1.0, sum(1 for x in done if start.isoformat() <= x <= end.isoformat()) / (int(h["schedule"].get("times", 3)) * weeks))
    due = [start + dt.timedelta(days=i) for i in range((end - start).days + 1) if due_on(h, start + dt.timedelta(days=i))]
    if not due:
        return None
    return sum(1 for x in due if x.isoformat() in done) / len(due)


# ------------------------------------------------------------------ đọc
def _goal_view(g: dict, d: dict) -> dict:
    logs = sorted(d["logs"].get(g["id"], []), key=lambda x: x["date"])
    m = g.get("metric") or {}
    cur = logs[-1]["value"] if logs else m.get("start")
    prog = None
    if m.get("target") is not None and m.get("start") is not None and cur is not None and m["target"] != m["start"]:
        prog = max(0.0, min(1.0, (cur - m["start"]) / (m["target"] - m["start"])))
    days_left = None
    if g.get("target_date"):
        try:
            days_left = (dt.date.fromisoformat(g["target_date"]) - today()).days
        except ValueError:
            pass
    ms = g.get("milestones") or []
    return {**g, "logs": logs[-120:], "current": cur, "progress": prog, "days_left": days_left,
            "milestones_done": sum(1 for x in ms if x.get("done")), "habit_ids": [h["id"] for h in d["habits"] if h.get("goal_id") == g["id"] and not h.get("archived")]}


def overview() -> dict:
    d, day = _load(), today()
    habits = []
    for h in d["habits"]:
        if h.get("archived"):
            continue
        done = _done_set(d, h["id"])
        weekly = (h.get("schedule") or {}).get("type") == "weekly"
        habits.append({**h, "sched": sched_label(h), "due_today": due_on(h, day), "done_today": day.isoformat() in done,
                       "week_count": _week_count(done, day) if weekly else None, "streak": streak(h, done, day),
                       "rate30": rate(h, done, 30),
                       "last28": [(day - dt.timedelta(days=27 - i)).isoformat() in done for i in range(28)]})
    due = [h for h in habits if h["due_today"]]
    weeks = []
    for k in range(7, -1, -1):
        ws = day - dt.timedelta(days=day.weekday() + 7 * k)
        tot = ok = 0
        for h in d["habits"]:
            if h.get("archived"):
                continue
            done = _done_set(d, h["id"])
            created = dt.date.fromisoformat(h.get("created", "2000-01-01")[:10])
            for i in range(7):
                x = ws + dt.timedelta(days=i)
                if x > day or x < created or not due_on(h, x) or (h.get("schedule") or {}).get("type") == "weekly":
                    continue
                tot += 1
                ok += x.isoformat() in done
        weeks.append({"week": ws.strftime("%d/%m"), "rate": round(ok / tot, 3) if tot else None, "done": ok, "due": tot})
    return {"date": day.isoformat(), "habits": habits, "today_done": sum(h["done_today"] for h in due), "today_due": len(due),
            "goals": [_goal_view(g, d) for g in d["goals"] if g.get("status") != "archived"], "weeks": weeks,
            "areas": AREAS, "suggestions": d["suggestions"], "memory": memory.facts(), "memory_kinds": memory.KINDS}


# ------------------------------------------------------------------ ghi
def checkin(habit_id: str, done: bool = True, date: str = "") -> dict:
    day = (date or today().isoformat())[:10]
    with _lock:
        d = _load()
        h = next((x for x in d["habits"] if x["id"] == habit_id), None)
        if not h:
            raise ValueError("Không tìm thấy thói quen")
        s = set(d["checkins"].get(habit_id, []))
        (s.add if done else s.discard)(day)
        d["checkins"][habit_id] = sorted(s)
        _save(d)
    st = streak(h, set(d["checkins"][habit_id]))
    unit = "tuần" if (h.get("schedule") or {}).get("type") == "weekly" else "ngày"
    return {"text": (f"✓ {h['title']}" + (f" · chuỗi {st} {unit} 🔥" if st >= 2 else "")) if done else f"Đã bỏ đánh dấu {h['title']}",
            "streak": st}


def find_habit(q: str) -> dict | None:
    from agents.tasks_hub import _fold
    qq = _fold(q)
    hs = [h for h in _load()["habits"] if not h.get("archived")]
    exact = [h for h in hs if _fold(h["title"]) == qq]
    if exact:
        return exact[0]
    part = [h for h in hs if qq in _fold(h["title"]) or all(w in _fold(h["title"]) for w in qq.split())]
    return part[0] if part else None


def add_habit(title: str, area: str = "health", goal_id: str = "", schedule: dict | None = None, time_s: str = "",
              target: str = "", why: str = "") -> dict:
    if not title.strip():
        raise ValueError("Cần tên thói quen")
    h = {"id": _id(), "title": title.strip()[:120], "area": area if area in AREAS else "self", "goal_id": goal_id or "",
         "schedule": schedule or {"type": "daily"}, "time": time_s or "", "target": target or "", "why": why or "",
         "created": today().isoformat()}
    with _lock:
        d = _load()
        d["habits"].append(h)
        _save(d)
    return {"habit": h, "text": f"Đã thêm thói quen “{h['title']}” ({sched_label(h)})."}


def update_habit(habit_id: str, **kw) -> dict:
    with _lock:
        d = _load()
        for h in d["habits"]:
            if h["id"] == habit_id:
                for k in ("title", "area", "goal_id", "schedule", "time", "target", "why", "archived"):
                    if k in kw and kw[k] is not None:
                        h[k] = kw[k]
        _save(d)
    return {"text": "Đã cập nhật thói quen"}


def add_goal(title: str, area: str = "self", why: str = "", target_date: str = "", metric: dict | None = None,
             milestones: list[str] | None = None) -> dict:
    g = {"id": _id(), "title": title.strip()[:160], "area": area if area in AREAS else "self", "why": why, "target_date": target_date,
         "metric": metric or {}, "milestones": [{"title": m, "done": False} for m in milestones or []],
         "created": today().isoformat(), "status": "active"}
    with _lock:
        d = _load()
        d["goals"].append(g)
        _save(d)
    return {"goal": g, "text": f"Đã thêm mục tiêu “{g['title']}”."}


def update_goal(goal_id: str, **kw) -> dict:
    with _lock:
        d = _load()
        for g in d["goals"]:
            if g["id"] == goal_id:
                for k in ("title", "area", "why", "target_date", "metric", "status", "milestones"):
                    if k in kw and kw[k] is not None:
                        g[k] = kw[k]
        _save(d)
    return {"text": "Đã cập nhật mục tiêu"}


def toggle_milestone(goal_id: str, index: int) -> dict:
    with _lock:
        d = _load()
        g = next(x for x in d["goals"] if x["id"] == goal_id)
        g["milestones"][index]["done"] = not g["milestones"][index].get("done")
        _save(d)
    return {"text": "Đã cập nhật cột mốc"}


def log_metric(goal_id: str, value, date: str = "", note: str = "") -> dict:
    v = float(str(value).replace(",", "."))
    day = (date or today().isoformat())[:10]
    with _lock:
        d = _load()
        g = next((x for x in d["goals"] if x["id"] == goal_id), None)
        if not g:
            raise ValueError("Không tìm thấy mục tiêu")
        logs = [x for x in d["logs"].get(goal_id, []) if x["date"] != day]
        logs.append({"date": day, "value": v, "note": note})
        d["logs"][goal_id] = sorted(logs, key=lambda x: x["date"])
        _save(d)
    m = g.get("metric") or {}
    return {"text": f"Đã ghi {m.get('name', 'chỉ số')}: {v:g} {m.get('unit', '')}".strip()}


def find_goal(q: str) -> dict | None:
    from agents.tasks_hub import _fold
    qq = _fold(q)
    gs = [g for g in _load()["goals"] if g.get("status") != "archived"]
    for g in gs:
        if qq and (qq in _fold(g["title"]) or qq in _fold((g.get("metric") or {}).get("name", ""))):
            return g
    return None


# ------------------------------------------------------------------ huấn luyện viên AI
SAFETY = """NGUYÊN TẮC AN TOÀN (bắt buộc): giảm cân bền vững 0,5-1 kg/tuần, không nhịn đói, không ăn dưới mức năng lượng nền,
ưu tiên đạm, rau, ngủ 7-8 tiếng; tăng khối lượng chạy tối đa ~10%/tuần, có tuần giảm tải, kết hợp sức mạnh và phục hồi để tránh chấn thương;
mục tiêu sức bền lớn (ultra trail) cần khám sức khoẻ tim mạch trước khi tăng cường độ; không thay thế bác sĩ/HLV chuyên môn.
Không đề xuất thuốc, thực phẩm chức năng hay chế độ cực đoan."""

COACH = """Bạn là huấn luyện viên phát triển bản thân của anh Huy. {profile}
{memory}
{safety}
Hôm nay {today}. MỤC TIÊU: {goal}
Thói quen hiện có cho mục tiêu này: {habits}
Hãy đề xuất cụ thể, khả thi với lịch làm việc của một CEO bận rộn. Trả về DUY NHẤT JSON:
{{"summary": "2-3 câu chiến lược tổng thể",
 "habits": [{{"title": "thói quen ngắn, đo được", "schedule": {{"type": "daily|weekdays|weekly|days", "times": số lần/tuần nếu weekly, "days": [0-6] nếu days}},
              "time": "HH:MM gợi ý hoặc rỗng", "target": "mức cụ thể", "why": "≤ 80 ký tự"}}] (3-5 thói quen, không trùng thói quen hiện có),
 "milestones": ["cột mốc có thời hạn, ví dụ 'Tuần 4: chạy dài 21 km Z2'"] (3-6 cột mốc),
 "week_plan": ["T2: ...", "T3: ...", "T4: ...", "T5: ...", "T6: ...", "T7: ...", "CN: ..."]}}"""


def coach(goal_id: str) -> dict:
    d = _load()
    g = next((x for x in d["goals"] if x["id"] == goal_id), None)
    if not g:
        raise ValueError("Không tìm thấy mục tiêu")
    gv = _goal_view(g, d)
    goal_txt = json.dumps({k: gv.get(k) for k in ("title", "why", "target_date", "metric", "current", "days_left")}
                          | {"milestones": [m["title"] for m in g.get("milestones") or []]}, ensure_ascii=False)
    habits = ", ".join(h["title"] for h in d["habits"] if h.get("goal_id") == goal_id and not h.get("archived")) or "(chưa có)"
    prompt = COACH.format(profile=profile.brief(), memory=memory.context(2500), safety=SAFETY, today=today().isoformat(),
                          goal=goal_txt, habits=habits)
    res = ask_json(prompt, 6000, 2, ok=lambda x: isinstance(x, dict) and bool(x.get("habits") or x.get("summary")), tag="coach")
    if not res:
        raise RuntimeError("superHuy chưa soạn được đề xuất, thử lại sau ít phút.")
    res["at"] = dt.datetime.now(_tz()).isoformat(timespec="minutes")
    with _lock:
        d = _load()
        d["suggestions"][goal_id] = res
        _save(d)
    return {**res, "text": res.get("summary", "")}


def accept_suggestion(goal_id: str, kind: str, index: int) -> dict:
    d = _load()
    s = d["suggestions"].get(goal_id) or {}
    g = next((x for x in d["goals"] if x["id"] == goal_id), {})
    if kind == "habit":
        h = (s.get("habits") or [])[index]
        r = add_habit(h["title"], g.get("area", "self"), goal_id, h.get("schedule") or {"type": "daily"}, h.get("time", ""),
                      h.get("target", ""), h.get("why", ""))
    else:
        ms = (s.get("milestones") or [])[index]
        with _lock:
            d = _load()
            gg = next(x for x in d["goals"] if x["id"] == goal_id)
            if not any(m["title"] == ms for m in gg["milestones"]):
                gg["milestones"].append({"title": ms, "done": False})
            _save(d)
        r = {"text": "Đã thêm cột mốc"}
    with _lock:
        d = _load()
        sg = d["suggestions"].get(goal_id) or {}
        sg.setdefault("accepted", []).append(f"{kind}:{index}")
        _save(d)
    return r


def today_line() -> str:
    try:
        o = overview()
        if not o["today_due"]:
            return ""
        left = [h["title"] for h in o["habits"] if h["due_today"] and not h["done_today"]]
        return f"🌱 Thói quen hôm nay: {o['today_done']}/{o['today_due']}" + (f" (còn: {', '.join(left[:4])})" if left else " ✓")
    except Exception:
        return ""


# ------------------------------------------------------------------ dữ liệu khởi tạo (3 mục tiêu của anh Huy)
def seed():
    d = _load()
    if d.get("seeded"):
        return
    t = today()
    g1 = add_goal("Hoàn thành VMM 100 km tại Sa Pa (2027)", "health",
                  "Thử thách sức bền lớn: trail 100 km, nhiều độ cao; xây nền aerobic, sức mạnh chân và kỹ năng leo dốc.",
                  "", {"name": "Km chạy/đi bộ mỗi tuần", "unit": "km/tuần", "start": None, "target": 60, "direction": "up"},
                  ["Khám sức khoẻ tim mạch + đánh giá thể lực trước khi tăng tải",
                   "Hoàn thành 3 tháng nền aerobic: chạy Z2, 4-5 buổi/tuần",
                   "Chạy dài 21 km địa hình không đau mỏi bất thường",
                   "Hoàn thành 1 giải trail 30-42 km",
                   "Hoàn thành 1 giải trail 50-70 km có độ cao",
                   "Đăng ký VMM 100 km Sa Pa"])["goal"]
    g2 = add_goal("Làm chủ AI engineering, hoàn thành vai trò CAO: Sellnity thành công ty POD AI-native", "skills",
                  "Tự tay xây được agent và hệ thống AI vận hành, dẫn dắt chuyển đổi toàn công ty.",
                  "", {"name": "Số quy trình đã AI hoá", "unit": "quy trình", "start": 0, "target": 20, "direction": "up"},
                  ["Lập bản đồ quy trình POD (design, listing, CS, fulfillment, ads) và chấm điểm tiềm năng AI",
                   "Tự xây và vận hành 3 agent nội bộ (superHuy là agent đầu tiên)",
                   "AI hoá 5 quy trình có số liệu tiết kiệm thời gian/chi phí",
                   "Đào tạo 100% đội ngũ dùng AI hằng ngày, có playbook",
                   "Mỗi phòng ban có ít nhất 1 agent chạy production"])["goal"]
    end30 = (t + dt.timedelta(days=30)).isoformat()
    g3 = add_goal("Thon gọn, khoẻ mạnh thể chất và tinh thần trong 30 ngày", "health",
                  "37 tuổi, 1m75, 87 kg. Giảm mỡ bền vững, ngủ tốt, đầu óc minh mẫn để chạy đường dài.",
                  end30, {"name": "Cân nặng", "unit": "kg", "start": 87, "target": 83.5, "direction": "down"},
                  ["Tuần 1: ổn định giờ ngủ, bỏ đồ uống có đường, đi 8.000 bước/ngày",
                   "Tuần 2: 3 buổi sức mạnh, ăn đủ đạm mỗi bữa",
                   "Tuần 3: giảm ~1,5-2 kg so với ban đầu, vòng bụng giảm",
                   "Ngày 30: 83-84,5 kg, năng lượng và giấc ngủ tốt hơn"])["goal"]
    log_metric(g3["id"], 87, t.isoformat(), "Bắt đầu")
    add_habit("Cân buổi sáng sau khi thức dậy", "health", g3["id"], {"type": "daily"}, "06:15", "Ghi số cân vào app", "Theo dõi xu hướng, không ám ảnh từng ngày")
    add_habit("Chạy/đi bộ theo giáo án (Z2, nói chuyện được)", "health", g1["id"], {"type": "days", "days": [0, 1, 3, 4, 5, 6]}, "05:45",
              "40-60 phút, chủ yếu Z2", "Xây nền aerobic cho VMM")
    add_habit("Sức mạnh chân + core (kiểu Hyrox nhẹ)", "health", g1["id"], {"type": "weekly", "times": 3}, "18:30",
              "30-40 phút: squat, lunge, step-up, plank, sled/wall ball nếu có", "Chống chấn thương, leo dốc khoẻ")
    add_habit("Deep work AI engineering", "skills", g2["id"], {"type": "weekdays"}, "08:30", "60 phút không họp, không điện thoại",
              "Tự tay xây agent, học sâu")
    add_habit("Không đồ uống có đường, không rượu bia", "health", g3["id"], {"type": "daily"}, "", "Nước, trà, cà phê đen",
              "Cắt calo rỗng dễ nhất")
    add_habit("Ngủ trước 23:30", "health", g3["id"], {"type": "daily"}, "23:00", "Tắt màn hình 23:00", "Hồi phục, kiểm soát thèm ăn")
    with _lock:
        d = _load()
        d["seeded"] = True
        _save(d)
    memory.seed_once([
        ("health", "Anh Huy 37 tuổi, cao 1m75, nặng 87 kg (12/10/2026)"),
        ("goal", "Mục tiêu: hoàn thành giải chạy VMM 100 km tại Sa Pa trong năm 2027"),
        ("routine", "Đang luyện chạy và đi bộ mỗi ngày; mới bắt đầu tìm hiểu Hyrox"),
        ("goal", "Mục tiêu: trở thành master AI engineering, hoàn thành vai trò CAO, biến Sellnity thành công ty POD AI-native"),
        ("goal", "Mục tiêu 30 ngày (đến 11/11/2026): thon gọn, giảm cân bền vững, khoẻ cả thể chất lẫn tinh thần"),
        ("work", "Anh Huy là CEO Sellnity, đồng thời CGO/CSO và CAO (Chief AI Officer)"),
    ])
