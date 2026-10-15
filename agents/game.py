"""Game hoá hành trình phát triển của anh Huy (mục Phát triển).

Cơ chế (theo các nguyên tắc game hoá đã được kiểm chứng: phản hồi tức thì, tiến bộ nhìn thấy được, mục tiêu ngắn hạn,
phần thưởng có ý nghĩa, không phạt nặng):
- XP cho mọi hành động tốt: check-in thói quen, xong việc, học xong bài, quiz, bài thực hành đạt, ôn tập, cột mốc mục tiêu, ghi chỉ số.
- CẤP ĐỘ + danh hiệu theo tổng XP (đường cong tăng dần). Lên cấp nhận VẬT PHẨM.
- VÀNG (xu) đi kèm XP -> đổi PHẦN THƯỞNG THẬT do anh tự đặt (massage, sách, nửa ngày nghỉ...) trong Cửa hàng.
- NHIỆM VỤ NGÀY (3 nhiệm vụ, thưởng thêm khi xong cả 3) + THỬ THÁCH TUẦN.
- HUY HIỆU thành tựu (chuỗi 7/30 ngày, khoá học, điểm 9+...).
- VẬT PHẨM: Khiên chuỗi (giữ chuỗi 1 ngày lỡ), Bình x2 XP (24 giờ), Rương vàng, Khung avatar/danh hiệu (trang trí).
Mọi điểm đều có NHẬT KÝ để anh xem vì sao được điểm. Mỗi sự kiện chỉ tính 1 lần (chống cộng trùng).
"""
import datetime as dt
import json
import logging
import math
import random
import threading
import uuid

from config import DATA_DIR

log = logging.getLogger("game")
FILE = DATA_DIR / "game.json"
_lock = threading.Lock()

XP = {  # sự kiện -> (XP, mô tả)
    "habit": (10, "Check-in thói quen"),
    "task": (15, "Hoàn thành việc"),
    "lesson": (40, "Học xong 1 ngày"),
    "quiz_pass": (10, "Quiz đạt"),
    "quiz_perfect": (20, "Quiz tuyệt đối"),
    "practice_pass": (50, "Bài thực hành đạt"),
    "practice_great": (30, "Bài thực hành 9+ (thưởng thêm)"),
    "review": (15, "Ôn tập giãn cách"),
    "milestone": (100, "Đạt cột mốc mục tiêu"),
    "metric": (5, "Ghi chỉ số"),
    "quest": (0, "Nhiệm vụ ngày"),
    "quest_all": (50, "Xong cả 3 nhiệm vụ ngày"),
    "weekly": (150, "Thử thách tuần"),
    "levelup": (0, "Lên cấp"),
    "chest": (0, "Mở rương"),
}
TITLES = ["Tân binh", "Người học việc", "Chiến binh kỷ luật", "Kỵ sĩ năng suất", "Chiến lược gia", "Thủ lĩnh",
          "Kiến trúc sư AI", "Đại sư agentic", "Huyền thoại", "Thần thoại"]
ITEMS = {
    "shield": {"name": "Khiên chuỗi", "icon": "🛡️", "desc": "Tự giữ chuỗi thói quen khi anh lỡ 1 ngày", "price": 120},
    "potion": {"name": "Bình x2 XP", "icon": "⚗️", "desc": "Nhân đôi XP trong 24 giờ", "price": 200},
    "chest": {"name": "Rương vàng", "icon": "🎁", "desc": "Mở ra 50–250 vàng hoặc 1 vật phẩm", "price": 0},
    "frame": {"name": "Khung avatar Hoàng kim", "icon": "🖼️", "desc": "Trang trí hồ sơ (mở khoá ở cấp 5)", "price": 0},
}
BADGES = {
    "first_lesson": ("📘", "Bài học đầu tiên", "Học xong ngày đầu của 1 khoá"),
    "streak7": ("🔥", "Lửa 7 ngày", "Chuỗi thói quen 7 ngày"),
    "streak30": ("🌋", "Núi lửa 30 ngày", "Chuỗi thói quen 30 ngày"),
    "course_done": ("🎓", "Tốt nghiệp", "Hoàn thành 1 khoá học"),
    "practice9": ("💎", "Kim cương", "Bài thực hành đạt 9+"),
    "perfect5": ("🎯", "Xạ thủ", "5 quiz tuyệt đối"),
    "tasks50": ("⚔️", "Chiến binh 50 việc", "Hoàn thành 50 việc"),
    "habits100": ("🌱", "Gieo hạt 100", "100 lần check-in thói quen"),
    "level5": ("👑", "Thủ lĩnh", "Đạt cấp 5"),
    "milestone": ("🏔️", "Chinh phục", "Đạt cột mốc mục tiêu đầu tiên"),
}
DEFAULT_REWARDS = [
    {"id": "r1", "name": "1 ly cà phê ngon", "price": 150, "icon": "☕"},
    {"id": "r2", "name": "Mua 1 cuốn sách", "price": 400, "icon": "📚"},
    {"id": "r3", "name": "1 buổi massage", "price": 1200, "icon": "💆"},
    {"id": "r4", "name": "Nửa ngày nghỉ trọn vẹn", "price": 2500, "icon": "🏖️"},
]


def _today() -> dt.date:
    try:
        from zoneinfo import ZoneInfo

        from config import TIMEZONE
        return dt.datetime.now(ZoneInfo(TIMEZONE)).date()
    except Exception:
        return dt.date.today()


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d.setdefault("xp", 0)
    d.setdefault("gold", 0)
    d.setdefault("log", [])
    d.setdefault("seen", {})
    d.setdefault("items", {"shield": 1, "chest": 1})
    d.setdefault("badges", {})
    d.setdefault("rewards", DEFAULT_REWARDS)
    d.setdefault("redeemed", [])
    d.setdefault("counters", {})
    d.setdefault("quests", {})
    d.setdefault("boost_until", "")
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    d["log"] = d["log"][-400:]
    d["seen"] = dict(list(d["seen"].items())[-3000:])
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


# ------------------------------------------------------------------ cấp độ
def level_of(xp: int) -> dict:
    """Cấp n cần 100*n^1.6 XP tích luỹ (cấp 2: 300, cấp 5: ~1.3k, cấp 10: ~4k...)."""
    lv, need = 1, 0
    while True:
        nxt = int(100 * (lv + 1) ** 1.6) + need if lv > 1 else 300
        if xp < nxt:
            break
        need, lv = nxt, lv + 1
    cur_floor = need
    nxt = int(100 * (lv + 1) ** 1.6) + need if lv > 1 else 300
    return {"level": lv, "title": TITLES[min(lv - 1, len(TITLES) - 1)], "floor": cur_floor, "next": nxt,
            "progress": round((xp - cur_floor) / max(1, nxt - cur_floor), 3)}


# ------------------------------------------------------------------ nhiệm vụ ngày + thử thách tuần
QUEST_POOL = [
    {"k": "habit", "n": 3, "t": "Check-in 3 thói quen"},
    {"k": "task", "n": 2, "t": "Hoàn thành 2 việc"},
    {"k": "lesson", "n": 1, "t": "Học xong bài hôm nay"},
    {"k": "quiz_pass", "n": 1, "t": "Làm đạt 1 quiz"},
    {"k": "review", "n": 1, "t": "Ôn tập 1 lượt"},
    {"k": "metric", "n": 1, "t": "Ghi 1 chỉ số mục tiêu"},
]


def _quests_today(d: dict) -> list[dict]:
    day = _today().isoformat()
    if day not in d["quests"]:
        rnd = random.Random(day)
        pick = [QUEST_POOL[2], QUEST_POOL[0]] + rnd.sample([q for q in QUEST_POOL if q["k"] not in ("lesson", "habit")], 1)
        d["quests"] = {day: [{**q, "done": 0, "xp": 30 if q["k"] != "lesson" else 40, "claimed": False} for q in pick]}
    return d["quests"][day]


def _week_key() -> str:
    y, w, _ = _today().isocalendar()
    return f"{y}-W{w:02d}"


def _weekly(d: dict) -> dict:
    wk = _week_key()
    c = d["counters"].get(wk) or {}
    goal = {"lesson": 5, "habit": 15, "task": 10}
    prog = {k: min(c.get(k, 0), v) for k, v in goal.items()}
    done = all(prog[k] >= goal[k] for k in goal)
    return {"week": wk, "goal": goal, "progress": prog, "done": done, "claimed": d["seen"].get(f"weekly:{wk}") is not None,
            "text": "Tuần này: 5 ngày học, 15 check-in thói quen, 10 việc xong"}


# ------------------------------------------------------------------ trao điểm
def award(event: str, ref: str = "", note: str = "", xp: int | None = None) -> dict | None:
    """Cộng XP + vàng cho 1 sự kiện (mỗi (event, ref) chỉ 1 lần). Trả về thông tin để app hiện hiệu ứng."""
    if event not in XP:
        return None
    try:
        with _lock:
            d = _load()
            key = f"{event}:{ref or _today().isoformat()}"
            if ref and key in d["seen"]:
                return None
            base = XP[event][0] if xp is None else int(xp)
            boost = d["boost_until"] and d["boost_until"] > dt.datetime.now().isoformat()
            gain = base * (2 if boost else 1)
            before = level_of(d["xp"])
            d["xp"] += gain
            d["gold"] += gain // 2
            d["seen"][key] = _today().isoformat()
            wk = _week_key()
            d["counters"].setdefault(wk, {})
            d["counters"][wk][event] = d["counters"][wk].get(event, 0) + 1
            d["counters"]["total_" + event] = d["counters"].get("total_" + event, 0) + 1
            entry = {"at": dt.datetime.now().isoformat(timespec="seconds"), "event": event, "xp": gain, "gold": gain // 2,
                     "note": note or XP[event][1], "boost": bool(boost)}
            d["log"].append(entry)
            extra = []
            # nhiệm vụ ngày
            qs = _quests_today(d)
            for q in qs:
                if q["k"] == event and not q["claimed"]:
                    q["done"] = min(q["n"], q["done"] + 1)
                    if q["done"] >= q["n"]:
                        q["claimed"] = True
                        d["xp"] += q["xp"]
                        d["gold"] += q["xp"] // 2
                        d["log"].append({"at": entry["at"], "event": "quest", "xp": q["xp"], "gold": q["xp"] // 2, "note": f"Nhiệm vụ: {q['t']}"})
                        extra.append(f"Nhiệm vụ “{q['t']}” +{q['xp']} XP")
            if all(q["claimed"] for q in qs) and f"quest_all:{_today()}" not in d["seen"]:
                d["seen"][f"quest_all:{_today()}"] = 1
                d["xp"] += XP["quest_all"][0]
                d["items"]["chest"] = d["items"].get("chest", 0) + 1
                d["log"].append({"at": entry["at"], "event": "quest_all", "xp": XP["quest_all"][0], "gold": 0, "note": "Xong cả 3 nhiệm vụ ngày + 1 rương"})
                extra.append("Xong 3 nhiệm vụ ngày: +50 XP và 1 rương 🎁")
            wkly = _weekly(d)
            if wkly["done"] and not wkly["claimed"]:
                d["seen"][f"weekly:{wk}"] = 1
                d["xp"] += XP["weekly"][0]
                d["items"]["potion"] = d["items"].get("potion", 0) + 1
                d["log"].append({"at": entry["at"], "event": "weekly", "xp": XP["weekly"][0], "gold": 0, "note": "Thử thách tuần + Bình x2 XP"})
                extra.append("Hoàn thành thử thách tuần: +150 XP và Bình x2 XP ⚗️")
            new_badges = _check_badges(d)
            after = level_of(d["xp"])
            lvl_up = after["level"] > before["level"]
            if lvl_up:
                d["items"]["chest"] = d["items"].get("chest", 0) + (after["level"] - before["level"])
                if after["level"] % 3 == 0:
                    d["items"]["shield"] = d["items"].get("shield", 0) + 1
                d["log"].append({"at": entry["at"], "event": "levelup", "xp": 0, "gold": 0,
                                 "note": f"Lên cấp {after['level']} · {after['title']} (+rương)"})
            _save(d)
        res = {"xp": gain, "gold": gain // 2, "note": entry["note"], "level_up": after if lvl_up else None,
               "badges": new_badges, "extra": extra, "total": d["xp"]}
        if lvl_up or new_badges:
            try:
                from core import notify
                msg = (f"⬆️ Lên cấp {after['level']}: {after['title']}! Nhận rương thưởng 🎁" if lvl_up else "") + \
                      ("".join(f"\n{BADGES[b][0]} Huy hiệu mới: {BADGES[b][1]}" for b in new_badges))
                notify.send(text=msg.strip())
            except Exception:
                pass
        return res
    except Exception:
        log.exception("Cộng điểm lỗi")
        return None


def _check_badges(d: dict) -> list[str]:
    c, got = d["counters"], []

    def give(b):
        if b not in d["badges"]:
            d["badges"][b] = _today().isoformat()
            got.append(b)
    if c.get("total_lesson", 0) >= 1:
        give("first_lesson")
    if c.get("total_task", 0) >= 50:
        give("tasks50")
    if c.get("total_habit", 0) >= 100:
        give("habits100")
    if c.get("total_quiz_perfect", 0) >= 5:
        give("perfect5")
    if c.get("total_practice_great", 0) >= 1:
        give("practice9")
    if c.get("total_milestone", 0) >= 1:
        give("milestone")
    if level_of(d["xp"])["level"] >= 5:
        give("level5")
    if c.get("course_done", 0) >= 1:
        give("course_done")
    st = c.get("best_streak", 0)
    if st >= 7:
        give("streak7")
    if st >= 30:
        give("streak30")
    return got


def note_streak(n: int):
    with _lock:
        d = _load()
        if n > d["counters"].get("best_streak", 0):
            d["counters"]["best_streak"] = n
            _check_badges(d)
            _save(d)


def note_course_done():
    with _lock:
        d = _load()
        d["counters"]["course_done"] = d["counters"].get("course_done", 0) + 1
        _check_badges(d)
        _save(d)


# ------------------------------------------------------------------ vật phẩm, cửa hàng, phần thưởng thật
def use_item(item: str) -> dict:
    with _lock:
        d = _load()
        if d["items"].get(item, 0) <= 0:
            raise ValueError("Anh chưa có vật phẩm này")
        d["items"][item] -= 1
        if item == "potion":
            d["boost_until"] = (dt.datetime.now() + dt.timedelta(hours=24)).isoformat(timespec="seconds")
            msg = "Bình x2 XP đã kích hoạt: nhân đôi XP trong 24 giờ ⚗️"
        elif item == "chest":
            roll = random.random()
            if roll < 0.15:
                d["items"]["shield"] = d["items"].get("shield", 0) + 1
                msg = "Rương mở ra 🛡️ Khiên chuỗi!"
            elif roll < 0.27:
                d["items"]["potion"] = d["items"].get("potion", 0) + 1
                msg = "Rương mở ra ⚗️ Bình x2 XP!"
            else:
                g = random.choice([50, 80, 100, 150, 250])
                d["gold"] += g
                msg = f"Rương mở ra {g} vàng 🪙"
            d["log"].append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": "chest", "xp": 0, "gold": 0, "note": msg})
        elif item == "shield":
            d["items"]["shield"] += 1  # khiên dùng tự động khi lỡ chuỗi, không bấm dùng
            raise ValueError("Khiên chuỗi tự kích hoạt khi anh lỡ 1 ngày thói quen, không cần bấm")
        else:
            msg = "Đã dùng"
        _save(d)
    return {"text": msg, **profile()}


def buy(item: str) -> dict:
    if item not in ITEMS or not ITEMS[item]["price"]:
        raise ValueError("Vật phẩm này không bán")
    with _lock:
        d = _load()
        p = ITEMS[item]["price"]
        if d["gold"] < p:
            raise ValueError(f"Cần {p} vàng, anh đang có {d['gold']}")
        d["gold"] -= p
        d["items"][item] = d["items"].get(item, 0) + 1
        _save(d)
    return {"text": f"Đã mua {ITEMS[item]['name']}", **profile()}


def add_reward(name: str, price: int, icon: str = "🎁") -> dict:
    with _lock:
        d = _load()
        d["rewards"].append({"id": uuid.uuid4().hex[:6], "name": name.strip()[:60], "price": max(10, int(price)), "icon": icon or "🎁"})
        _save(d)
    return profile()


def remove_reward(rid: str) -> dict:
    with _lock:
        d = _load()
        d["rewards"] = [r for r in d["rewards"] if r["id"] != rid]
        _save(d)
    return profile()


def redeem(rid: str) -> dict:
    with _lock:
        d = _load()
        r = next((x for x in d["rewards"] if x["id"] == rid), None)
        if not r:
            raise ValueError("Không tìm thấy phần thưởng")
        if d["gold"] < r["price"]:
            raise ValueError(f"Cần {r['price']} vàng, anh đang có {d['gold']}. Cố thêm chút nữa nhé!")
        d["gold"] -= r["price"]
        d["redeemed"].append({**r, "at": dt.datetime.now().isoformat(timespec="seconds")})
        d["log"].append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": "chest", "xp": 0, "gold": -r["price"],
                         "note": f"Đổi thưởng: {r['name']}"})
        _save(d)
    return {"text": f"{r['icon']} Đã đổi “{r['name']}”. Anh xứng đáng được tận hưởng!", **profile()}


def protect_streak(habit_id: str, missed_day: str) -> bool:
    """Dùng 1 Khiên chuỗi để giữ chuỗi khi lỡ ngày (growth gọi khi tính chuỗi)."""
    with _lock:
        d = _load()
        key = f"shield:{habit_id}:{missed_day}"
        if key in d["seen"]:
            return True
        if d["items"].get("shield", 0) <= 0:
            return False
        d["items"]["shield"] -= 1
        d["seen"][key] = _today().isoformat()
        d["log"].append({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": "chest", "xp": 0, "gold": 0,
                         "note": f"🛡️ Khiên chuỗi giữ chuỗi ngày {missed_day}"})
        _save(d)
        return True


def shielded(habit_id: str) -> set:
    d = _load()
    return {k.split(":")[2] for k in d["seen"] if k.startswith(f"shield:{habit_id}:")}


# ------------------------------------------------------------------ xem
def profile() -> dict:
    d = _load()
    lv = level_of(d["xp"])
    qs = _quests_today(d)
    with _lock:
        _save(d)
    today = _today().isoformat()
    xp_today = sum(x["xp"] for x in d["log"] if x["at"][:10] == today)
    boost = d["boost_until"] if d["boost_until"] > dt.datetime.now().isoformat() else ""
    return {"xp": d["xp"], "gold": d["gold"], "level": lv, "xp_today": xp_today, "quests": qs, "weekly": _weekly(d),
            "items": [{"id": k, **ITEMS[k], "qty": d["items"].get(k, 0)} for k in ITEMS],
            "badges": [{"id": k, "icon": v[0], "name": v[1], "desc": v[2], "at": d["badges"].get(k)} for k, v in BADGES.items()],
            "rewards": d["rewards"], "redeemed": d["redeemed"][-10:], "log": d["log"][-30:][::-1], "boost_until": boost,
            "xp_table": {k: v for k, v in XP.items() if v[0]}}


def shield_job():
    """00:15: thói quen ngày hôm qua bị lỡ mà đang có chuỗi ≥ 3 -> tự dùng Khiên chuỗi (nếu có) để giữ chuỗi."""
    from agents import growth
    y = _today() - dt.timedelta(days=1)
    d = growth._load()
    used = []
    for h in d.get("habits", []):
        if h.get("archived") or (h.get("schedule") or {}).get("type") == "weekly" or not growth.due_on(h, y):
            continue
        done = set(d["checkins"].get(h["id"], []))
        if y.isoformat() in done or y.isoformat() in shielded(h["id"]):
            continue
        if growth.streak(h, done, y - dt.timedelta(days=1)) >= 3 and protect_streak(h["id"], y.isoformat()):
            used.append(h["title"])
    if used:
        from core import notify
        notify.send(text="🛡️ Khiên chuỗi đã giữ chuỗi cho: " + ", ".join(used) + ". Hôm nay quay lại nhé!")
