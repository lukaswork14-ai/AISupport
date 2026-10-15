"""Nơi khai báo TẤT CẢ agent và công cụ của hệ thống (đọc core/registry.py để hiểu cách hoạt động).
Muốn thêm công cụ mới: viết hàm trả về dict {"text": ..., "image": ..., ...} rồi thêm Action vào agent phù hợp
(hoặc tạo Agent mới). Super bot và Mini App sẽ tự nhận."""
import datetime as dt
import json
import os
import re

import targets as targets_mod
from agents import (calendar_agent, content_agent, content_hub, strategy, learning, reel_studio, gemini_notebook, knowledge_sources, meeting, meeting_share, email_agent, fb_connect, gcal_bridge, imagecard, lark_agent, mailbox, news_agent, publisher,
                    reel_video, second_brain)
from config import CARD_HANDLE, DATA_DIR
from core import digests, notify, store
from core.registry import Action, Agent, Param, register


# ================================================================ Lịch
def _day(text: str, default: dt.date) -> dt.date:
    """Hiểu ngày: 2026-10-12, 12/10, hôm nay, mai/ngày mai, mốt/ngày kia, hôm qua, thứ 2..chủ nhật."""
    t = (text or "").strip().lower()
    today = dt.date.today()
    if not t:
        return default
    try:
        return dt.date.fromisoformat(t[:10])
    except ValueError:
        pass
    words = {"hôm nay": 0, "nay": 0, "today": 0, "ngày mai": 1, "mai": 1, "tomorrow": 1, "ngày kia": 2, "mốt": 2, "hôm qua": -1}
    for k, v in words.items():
        if t == k or t.startswith(k + " "):
            return today + dt.timedelta(days=v)
    m = re.match(r"(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?$", t)
    if m:
        y = int(m.group(3)) if m.group(3) else today.year
        return dt.date(y + 2000 if y < 100 else y, int(m.group(2)), int(m.group(1)))
    wd = {"chủ nhật": 6, "cn": 6, "thứ 2": 0, "thứ hai": 0, "thứ 3": 1, "thứ ba": 1, "thứ 4": 2, "thứ tư": 2, "thứ 5": 3, "thứ năm": 3,
          "thứ 6": 4, "thứ sáu": 4, "thứ 7": 5, "thứ bảy": 5}
    for k, v in wd.items():
        if t.startswith(k):
            return today + dt.timedelta(days=(v - today.weekday()) % 7)
    raise ValueError(f"Chưa hiểu ngày “{text}”, anh ghi dạng 12/10 hoặc “mai” nhé.")


def lich_ngay(date: str = "") -> dict:
    day = _day(date, dt.date.today() + dt.timedelta(days=1))
    evs = calendar_agent.get_events(day)
    return {"text": calendar_agent.format_schedule(day), "items": calendar_agent.serialize(evs),
            "can_write": gcal_bridge.ready()}


def lich_hieu(text: str) -> dict:
    d = calendar_agent.parse_text(text)
    return {"text": f"{d.get('title')} · {d.get('date')} {d.get('start') or 'cả ngày'}", "fields": d}


def lich_tao(title: str, date: str, start: str = "", duration_min: int = 60, all_day: bool = False,
             priority: str = "normal", location: str = "", note: str = "") -> dict:
    if not gcal_bridge.ready():
        raise ValueError("Chưa bật quyền tạo lịch. Vào Thêm > Kết nối > Tạo lịch Google để bật (một lần).")
    if not title.strip():
        raise ValueError("Cần có tiêu đề")
    tz = calendar_agent.TZ
    day = _day(date, dt.date.today())
    if all_day or not start:
        s = dt.datetime.combine(day, dt.time.min, tzinfo=tz)
        e, all_day = None, True
    else:
        hh, mm = (int(x) for x in start.split(":")[:2])
        s = dt.datetime.combine(day, dt.time(hh, mm), tzinfo=tz)
        e = s + dt.timedelta(minutes=int(duration_min or 60))
    gcal_bridge.create(title.strip(), s, e, bool(all_day), priority, location, note)
    when = f"{day:%d/%m}" + ("" if all_day else f" {s:%H:%M}–{e:%H:%M}")
    return {"text": f"Đã thêm “{title.strip()}” vào lịch ({when}, {gcal_bridge.PRIORITIES.get(priority, 'Bình thường').lower()})."}


def lich_tao_nhanh(text: str) -> dict:
    d = calendar_agent.parse_text(text)
    return lich_tao(d.get("title", text), d["date"], d.get("start", ""), d.get("duration_min", 60),
                    d.get("all_day", False), d.get("priority", "normal"), d.get("location", ""))


def lich_uutien(event_id: str, priority: str) -> dict:
    gcal_bridge.set_priority(event_id, priority)
    return {"text": "Đã đổi mức ưu tiên."}


def lich_xoa(event_id: str) -> dict:
    gcal_bridge.delete(event_id)
    return {"text": "Đã xóa sự kiện."}


def lich_loimoi(days: int = 21) -> dict:
    """Gộp lời mời họp chưa trả lời từ Google + Lark, kèm cảnh báo trùng với lịch đã có."""
    from agents import lark_calendar
    tz = calendar_agent.TZ
    items, errs = [], []
    if gcal_bridge.ready():
        try:
            items += gcal_bridge.invites(days)
        except Exception as e:
            errs.append(f"Google: {e}")
    if lark_calendar.ready():
        try:
            items += lark_calendar.invites(days, tz)
        except Exception as e:
            errs.append(f"Lark: {e}")
    cache: dict = {}
    for it in items:
        s = dt.datetime.fromisoformat(it["start"].replace("Z", "+00:00")).astimezone(tz)
        e = dt.datetime.fromisoformat(it["end"].replace("Z", "+00:00")).astimezone(tz)
        it["date"], it["time"] = s.date().isoformat(), "Cả ngày" if it["all_day"] else f"{s:%H:%M}–{e:%H:%M}"
        it["_s"] = s
        if it["all_day"]:
            it["conflicts"] = []
            continue
        if s.date() not in cache:
            try:
                cache[s.date()] = calendar_agent.get_events(s.date())
            except Exception:
                cache[s.date()] = []
        try:
            it["conflicts"] = [x["title"] for x in cache[s.date()] if x.get("start") and x.get("end")
                               and x["start"] < e and s < x["end"] and x["title"] != it["title"]][:3]
        except TypeError:
            it["conflicts"] = []
    items.sort(key=lambda x: x["_s"])
    for it in items:
        it.pop("_s", None)
    n = len(items)
    text = (f"{n} lời mời họp đang chờ bạn trả lời." if n else "Không có lời mời họp nào đang chờ.") + \
        ("".join(f"\n• {i['date'][8:]}/{i['date'][5:7]} {i['time']} {i['title']}" + (" ⚠️ trùng lịch" if i["conflicts"] else "")
                 for i in items[:10]))
    if errs:
        text += "\n⚠️ " + "; ".join(errs)
    return {"text": text, "items": items, "sources": {"google": gcal_bridge.ready(), "lark": lark_calendar.ready()}}


def lich_traloi(source: str, event_id: str, status: str) -> dict:
    from agents import lark_calendar
    if status not in ("yes", "no", "maybe"):
        raise ValueError("Trạng thái phải là yes, no hoặc maybe")
    (lark_calendar if source == "lark" else gcal_bridge).rsvp(event_id, status)
    return {"text": {"yes": "Đã nhận lời tham dự.", "no": "Đã từ chối lời mời.", "maybe": "Đã trả lời: có thể tham dự."}[status]}


PRI_OPTS = [{"value": k, "label": v} for k, v in gcal_bridge.PRIORITIES.items()]
register(Agent("lich", "Lịch", "📅", "Xem, tạo sự kiện và gắn màu ưu tiên (Google + Lark)", order=10, actions=[
    Action("ngay", "Xem lịch một ngày", lich_ngay, icon="📅", llm=True,
           desc="Lấy lịch của một ngày đã sắp xếp, có mức ưu tiên và cảnh báo trùng lịch.",
           params=[Param("date", "Ngày", hint="YYYY-MM-DD, bỏ trống = ngày mai")]),
    Action("tao_nhanh", "Thêm lịch bằng một câu", lich_tao_nhanh, icon="➕", llm=True, long=True,
           desc="Tạo sự kiện Google Calendar từ câu tự nhiên, ví dụ 'Họp CJ 3h chiều mai 1 tiếng, gấp và quan trọng'.",
           params=[Param("text", "Mô tả sự kiện", "textarea", required=True)]),
    Action("hieu", "Hiểu câu mô tả lịch", lich_hieu, hidden=True, long=True, params=[Param("text", "Câu", required=True)]),
    Action("tao", "Tạo sự kiện", lich_tao, hidden=True, long=True, params=[
        Param("title", "Tiêu đề", required=True), Param("date", "Ngày", required=True), Param("start", "Giờ bắt đầu"),
        Param("duration_min", "Thời lượng (phút)", "number", default=60), Param("all_day", "Cả ngày", "bool"),
        Param("priority", "Ưu tiên", "select", options=PRI_OPTS, default="normal"), Param("location", "Địa điểm"),
        Param("note", "Ghi chú", "textarea")]),
    Action("uutien", "Đổi ưu tiên", lich_uutien, hidden=True, long=True,
           params=[Param("event_id", "ID", required=True), Param("priority", "Ưu tiên", "select", options=PRI_OPTS, required=True)]),
    Action("xoa", "Xóa sự kiện", lich_xoa, hidden=True, long=True, params=[Param("event_id", "ID", required=True)]),
    Action("loimoi", "Lời mời họp chờ duyệt", lich_loimoi, icon="📨", llm=True, long=True,
           desc="Liệt kê lời mời họp (Google + Lark) chưa trả lời trong 3 tuần tới, có cảnh báo trùng lịch.",
           params=[Param("days", "Số ngày tới", "number", default=21)]),
    Action("traloi", "Trả lời lời mời họp", lich_traloi, hidden=True, long=True, params=[
        Param("source", "Nguồn", required=True), Param("event_id", "ID", required=True),
        Param("status", "Trả lời", "select", options=["yes", "no", "maybe"], required=True)]),
]))


# ================================================================ Email
def email_tomtat(hours: int = 6) -> dict:
    hours = max(1, min(int(hours), 72))
    text = email_agent.hourly_digest(force_hours=hours) or "Không có email mới."
    digests.save("email", text)
    return {"text": text}


# ---- cập nhật ngay khi bấm (khung thời gian nối tiếp lịch tự động, có chống chạy trùng)
import threading as _th
_live_lock = {"email": _th.Lock(), "lark": _th.Lock()}


def _since_slot(hours_csv: str, min_h: int, max_h: int) -> int:
    """Số giờ kể từ khung giờ tự động gần nhất (ít nhất min_h, nhiều nhất max_h)."""
    now = dt.datetime.now()
    slots = sorted(int(h) for h in hours_csv.split(",") if h.strip().isdigit())
    past = [now.replace(hour=h, minute=0, second=0, microsecond=0) for h in slots]
    past = [t for t in past if t <= now] or [now.replace(hour=slots[-1], minute=0, second=0, microsecond=0) - dt.timedelta(days=1)]
    h = int((now - max(past)).total_seconds() // 3600) + 1
    return max(min_h, min(max_h, h))


def _fresh(kind: str, minutes: int = 3) -> bool:
    at = (digests.load().get(kind) or {}).get("at")
    try:
        return (dt.datetime.now() - dt.datetime.fromisoformat(at)).total_seconds() < minutes * 60
    except Exception:
        return False


def email_capnhat() -> dict:
    """Cập nhật ngay (bấm trong app): email kể từ phiên tối gần nhất."""
    from config import EMAIL_DIGEST_HOURS
    with _live_lock["email"]:
        if not _fresh("email"):
            text = email_agent.hourly_digest(force_hours=_since_slot(EMAIL_DIGEST_HOURS, 3, 26))
            digests.save("email", text)
    return {"digests": digests.load(), "text": "Đã cập nhật email."}


def lark_capnhat() -> dict:
    from config import LARK_DIGEST_HOURS
    if not lark_agent.ready():
        return {"digests": digests.load(), "text": "Chưa kết nối Lark."}
    with _live_lock["lark"]:
        if not _fresh("lark"):
            text = lark_agent.digest(_since_slot(LARK_DIGEST_HOURS, 3, 24))
            digests.save("lark", text)
    return {"digests": digests.load(), "text": "Đã cập nhật tin nhắn Lark."}


def email_hopthu(refresh: bool = True, days: int = 3) -> dict:
    if refresh:
        r = mailbox.sync(int(days or 3))
        items = r["items"]
        note = f"{r['new']} thư mới đã được phân loại." if r["new"] else "Không có thư mới."
    else:
        items, note = mailbox.inbox(), ""
    return {"items": items, "labels": mailbox.LABELS, "text": note,
            "platforms": {"gmail": mailbox.gmail_ready(), "lark": mailbox.lark_mail_ready()}}


def email_boqua(uid: str) -> dict:
    mailbox.skip(uid)
    return {"text": "Đã bỏ qua"}


def email_nhan(uid: str, label: str) -> dict:
    mailbox.relabel(uid, label)
    return {"text": f"Đã gắn nhãn {mailbox.LABELS.get(label, label)}"}


def email_nhap(uid: str, hint: str = "") -> dict:
    return {"text": mailbox.draft_reply(uid, hint)}


def email_soan(brief: str, tone: str = "chuyên nghiệp") -> dict:
    d = mailbox.compose(brief, tone)
    return {"text": d.get("body", ""), "subject": d.get("subject", "")}


def email_gui(platform: str, to: str, subject: str, body: str, reply_uid: str = "") -> dict:
    who = mailbox.send(platform or "gmail", to, subject, body, reply_uid)
    return {"text": f"Đã gửi tới {who} qua {'Lark Mail' if platform == 'lark' else 'Gmail'}."}


LABEL_OPTS = [{"value": k, "label": v} for k, v in mailbox.LABELS.items()]
register(Agent("email", "Email", "📧", "Hộp thư: tóm tắt, gắn nhãn, duyệt nhanh, trả lời và gửi thư", order=20, actions=[
    Action("capnhat", "Cập nhật email ngay", email_capnhat, hidden=True, long=True),
    Action("tomtat", "Tóm tắt email", email_tomtat, icon="📧", llm=True, long=True,
           desc="Tổng hợp email trong N giờ gần nhất thành chủ đề và việc cần làm.",
           params=[Param("hours", "Số giờ nhìn lại", "number", default=6)]),
    Action("hopthu", "Đồng bộ và phân loại hộp thư", email_hopthu, icon="🗂", llm=True, long=True,
           desc="Lấy thư mới, AI gắn nhãn Công việc/Kiến thức/Cá nhân/Quan trọng/Tài chính/Quảng cáo (gắn cả trong Gmail).",
           params=[Param("refresh", "Lấy thư mới", "bool", default=True), Param("days", "Số ngày", "number", default=3)]),
    Action("boqua", "Bỏ qua thư", email_boqua, hidden=True, long=True, params=[Param("uid", "UID", required=True)]),
    Action("nhan", "Đổi nhãn thư", email_nhan, hidden=True, long=True,
           params=[Param("uid", "UID", required=True), Param("label", "Nhãn", "select", options=LABEL_OPTS, required=True)]),
    Action("nhap", "Nháp trả lời", email_nhap, hidden=True, long=True,
           params=[Param("uid", "UID", required=True), Param("hint", "Ý muốn trả lời")]),
    Action("soan", "AI viết thư", email_soan, hidden=True, long=True,
           params=[Param("brief", "Ý chính", "textarea", required=True), Param("tone", "Giọng", default="chuyên nghiệp")]),
    Action("gui", "Gửi thư", email_gui, hidden=True, long=True, params=[
        Param("platform", "Nền tảng", "select", options=["gmail", "lark"], default="gmail"), Param("to", "Tới", required=True),
        Param("subject", "Tiêu đề", required=True), Param("body", "Nội dung", "textarea", required=True), Param("reply_uid", "Trả lời thư")]),
]))


# ================================================================ Tin nhắn Lark
def lark_tomtat(hours: int = 6) -> dict:
    text = lark_agent.digest(max(1, min(int(hours), 72))) or "Không có tin nhắn mới."
    digests.save("lark", text)
    return {"text": text}


def lark_groups() -> dict:
    if not lark_agent.ready():
        return {"text": "Chưa kết nối Lark."}
    cs = lark_agent.chats()
    return {"text": f"Bot đang ở {len(cs)} group:\n" + "\n".join("• " + c["name"] for c in cs) if cs else
                    "Bot chưa được thêm vào group nào. Thêm bot vào các group Lark cần theo dõi.", "items": cs}


def lark_join() -> dict:
    from agents import lark_oauth
    if not lark_agent.ready():
        raise ValueError("Chưa kết nối Lark (Cài đặt > Kết nối Lark).")
    url = lark_oauth.authorize_url(lark_oauth.new_state())
    return {"text": "Bấm nút bên dưới, đăng nhập Lark (nếu được hỏi) và bấm Cho phép/Authorize. "
                    "Bot sẽ tự thêm vào mọi group có bạn rồi báo kết quả qua Telegram.", "open_url": url}


register(Agent("lark", "Tin nhắn Lark", "💬", "Tổng hợp tin nhắn các group Lark: chủ đề + việc cần xử lý", order=25, actions=[
    Action("capnhat", "Cập nhật Lark ngay", lark_capnhat, hidden=True, long=True),
    Action("tomtat", "Tóm tắt tin nhắn Lark", lark_tomtat, icon="💬", llm=True, long=True,
           desc="Tổng hợp tin nhắn trong các group Lark (có bot) trong N giờ gần nhất.",
           params=[Param("hours", "Số giờ nhìn lại", "number", default=6)]),
    Action("groups", "Các group đang theo dõi", lark_groups, icon="👥", long=True),
    Action("join", "Thêm bot vào mọi group của tôi", lark_join, icon="➕",
           desc="Đăng nhập Lark 1 lần, bot tự vào tất cả group có bạn."),
]))


# ================================================================ Săn tin
def tin_top(refresh: bool = False) -> dict:
    res = news_agent.get_today(bool(refresh))
    return {"text": news_agent.format_digest(res), "items": res["items"]}


def tin_luu(n: int) -> dict:
    items = news_agent.load_today()
    if not 1 <= int(n) <= len(items):
        raise ValueError("Chưa có tin số đó, hãy quét tin trước.")
    path = second_brain.save_news(items[int(n) - 1])
    return {"text": "Đã lưu vào Obsidian: " + path.replace(str(second_brain.OBSIDIAN_VAULT), "")}


register(Agent("tin", "Săn tin", "📰", "Top 5 tin hot về AI và ecommerce mỗi ngày", order=30, actions=[
    Action("top", "Top 5 tin hôm nay", tin_top, icon="🔥", llm=True, long=True,
           desc="Lấy Top 5 tin hot hôm nay (AI, ecommerce, TikTok Shop, Amazon, Etsy, Shopify, POD).",
           params=[Param("refresh", "Quét lại từ đầu", "bool", default=False)]),
    Action("luu", "Lưu tin vào Obsidian", tin_luu, icon="📥", hidden=True, params=[Param("n", "Số tin", "number", required=True)]),
]))


# ================================================================ Studio nội dung
def bantin_caption(items: list[dict]) -> str:
    today = dt.date.today().strftime("%d.%m.%Y")
    lines = [f"Bản tin sáng · {today}", f"{len(items)} tin đáng chú ý trong 24 giờ qua", ""]
    for i, it in enumerate(items, 1):
        lines.append(f"{i}. {it['headline_vi']} ({it['source'].replace('GNews: ', '')})")
    lines += ["", "Mình chọn lọc từ nhiều nguồn uy tín về AI và thương mại điện tử. Tin nào bạn quan tâm nhất, comment số để mình viết sâu hơn.",
              "", "#TinTuc #AI #Ecommerce #TikTokShop #Amazon #Etsy"]
    return "\n".join(lines)


def viet_bai(n: int, angle: str = "") -> dict:
    items = news_agent.load_today()
    if not 1 <= int(n) <= len(items):
        raise ValueError("Chưa có tin số đó, hãy quét tin trước.")
    item = items[int(n) - 1]
    c = content_agent.make_content(item, angle or "")
    img = imagecard.make_card(c["card"], item["source"], item["topic"], f"tin{n}-{dt.datetime.now():%H%M%S}", CARD_HANDLE)
    text = content_agent.format_post(item, c)
    cid = store.add("post", item["headline_vi"], text, image=img,
                    meta={"n": int(n), "reel": content_agent.format_reel(c), "reel_data": c.get("reel", {}),
                          "topic": item.get("topic", ""), "source": item.get("source", ""),
                          "image_prompt": c.get("image_prompt", "")})
    return {"text": text, "image": img, "content_id": cid}


def video_tu_bai(content_id: str = "") -> dict:
    if not content_id:  # mặc định: bài viết mới nhất có kịch bản reels
        latest = next((r for r in store.recent(60, "post") if r.get("meta", {}).get("reel_data")), None)
        content_id = latest["id"] if latest else ""
    c = store.get(content_id)
    if not c or not c.get("meta", {}).get("reel_data"):
        raise ValueError("Bài này chưa có kịch bản reels dạng cấu trúc (bài tạo trước bản cập nhật). Hãy viết lại bài.")
    m = c["meta"]
    path, engine = reel_video.make_post_video(m["reel_data"], m.get("topic", ""), m.get("source", ""), c.get("image"),
                                              CARD_HANDLE, name=f"bai-{content_id}")
    r = m["reel_data"]
    cap = (r.get("caption") or c["title"]) + "\n\nGiọng đọc được tạo bằng AI."
    vid = store.add("video", "Reels: " + c["title"], cap, video=path, meta={"from": content_id, "voice_engine": engine})
    return {"text": cap, "video": path, "content_id": vid}


def ban_tin_anh() -> dict:
    items = news_agent.load_today()
    if not items:
        raise ValueError("Chưa có tin hôm nay, hãy quét tin trước.")
    img = imagecard.make_digest_card(items, dt.date.today().strftime("%d.%m.%Y"), f"bantin-{dt.datetime.now():%H%M%S}", CARD_HANDLE)
    cap = bantin_caption(items)
    cid = store.add("bantin", f"Bản tin sáng {dt.date.today():%d/%m}", cap, image=img)
    return {"text": cap, "image": img, "content_id": cid}


def ban_tin_video() -> dict:
    items = news_agent.load_today()
    if not items:
        raise ValueError("Chưa có tin hôm nay, hãy quét tin trước.")
    path, engine = reel_video.make_bantin_video(items, CARD_HANDLE)
    cap = bantin_caption(items) + "\n\nGiọng đọc được tạo bằng AI."
    cid = store.add("video", f"Video bản tin {dt.date.today():%d/%m}", cap, video=path, meta={"voice_engine": engine})
    return {"text": cap, "video": path, "content_id": cid}


def studio_list(kind: str = "") -> dict:
    rows = store.recent(40, kind or None)
    return {"items": rows, "text": "\n".join(f"• [{store.KINDS.get(r['kind'], r['kind'])}] {r['title']} ({r['status']})" for r in rows[:15]) or "Chưa có nội dung."}


def studio_sua(content_id: str, text: str) -> dict:
    r = store.update(content_id, text=text)
    if not r:
        raise ValueError("Không tìm thấy nội dung.")
    return {"text": "Đã lưu chỉnh sửa."}


def studio_luu_obsidian(content_id: str) -> dict:
    r = store.get(content_id)
    if not r:
        raise ValueError("Không tìm thấy nội dung.")
    path = second_brain.save_output(r["title"], r["text"], r["kind"])
    return {"text": "Đã lưu vào Obsidian: " + path.replace(str(second_brain.OBSIDIAN_VAULT), "")}


register(Agent("studio", "Studio", "🎬", "Viết bài, ảnh bản tin, video reels có giọng đọc AI", order=40, actions=[
    Action("viet", "Viết bài từ một tin", viet_bai, icon="✍️", long=True, llm=True,
           desc="Viết bài đăng + ảnh minh họa + kịch bản reels cho tin số N trong Top 5 hôm nay.",
           params=[Param("n", "Tin số", "number", default=1, required=True),
                   Param("angle", "Góc nhìn / chỉ đạo thêm", "textarea", hint="ví dụ: nhấn mạnh cơ hội cho seller POD")]),
    Action("bantin", "Ảnh bản tin sáng", ban_tin_anh, icon="📰", long=True, llm=True,
           desc="Tạo ảnh Bản tin sáng (Top 5) kèm caption."),
    Action("video_bai", "Dựng video reels cho một bài", video_tu_bai, icon="🎬", long=True, hidden=True, llm=True,
           desc="Dựng video reels (giọng đọc AI) từ kịch bản của bài viết. Bỏ trống content_id = bài viết mới nhất.",
           params=[Param("content_id", "ID bài viết (bỏ trống = bài mới nhất)")]),
    Action("video", "Video bản tin (giọng AI)", ban_tin_video, icon="🎞️", long=True,
           desc="Dựng video dọc 9:16 có giọng đọc AI tiếng Việt từ Top 5 tin hôm nay."),
    Action("list", "Danh sách nội dung", studio_list, icon="🗂", hidden=True,
           params=[Param("kind", "Loại", "select", options=[""] + list(store.KINDS))]),
    Action("sua", "Sửa nội dung", studio_sua, hidden=True,
           params=[Param("content_id", "ID", required=True), Param("text", "Nội dung", "textarea", required=True)]),
    Action("obsidian", "Lưu nội dung vào Obsidian", studio_luu_obsidian, hidden=True,
           params=[Param("content_id", "ID", required=True)]),
]))


# ================================================================ Nội dung (Săn tin + Studio hợp nhất)
def _noidung_text(v: dict) -> str:
    lines = [f"Hàng chờ duyệt: {len(v['new'])} tin; đang tạo: {sum(1 for i in v['working'] if i['status'] != 'error')}; đã tạo: {len(v['done'])}."]
    for i in v["new"][:12]:
        lines.append(f"• [{i['id']}] ({content_hub.TRACKS.get(i['track'], i['track'])}) {i['headline_vi']}")
    for i in v["working"]:
        lines.append(f"⏳ [{i['id']}] {i['headline_vi']} ({'lỗi: ' + i.get('err', '') if i['status'] == 'error' else 'đang tạo'})")
    return "\n".join(lines)


def noidung_tongquan() -> dict:
    v = content_hub.queue_view()
    return {**v, "text": _noidung_text(v)}


def _list_param(x) -> list[str] | None:
    if x in (None, ""):
        return None
    if isinstance(x, list):
        return [str(i).strip() for i in x if str(i).strip()]
    return [t.strip() for t in re.split(r"[,;\n]+", str(x)) if t.strip()]


def noidung_duyet(id: str, style: str = "", reel_len: int = 0, outputs: str = "", angle: str = "") -> dict:
    return content_hub.approve(id, style or "", int(reel_len or 0), _list_param(outputs), angle or "")


def noidung_caidat(topics: str = "", reel_len: int = 0, style: str = "", voice: str = "", outputs: str = "",
                   fast=None, tin=None, founder=None, roimaxx=None, leversphere=None, music=None) -> dict:
    c = content_hub.cfg()
    tracks = dict(c["tracks"])
    for k, v in (("roimaxx", roimaxx), ("leversphere", leversphere)):
        if v is not None:
            tracks[k] = bool(v) and str(v).lower() not in ("false", "0")
    if tin is not None:
        tracks["tin"] = bool(tin) and str(tin).lower() not in ("false", "0")
    if founder is not None:
        tracks["founder"] = bool(founder) and str(founder).lower() not in ("false", "0")
    c = content_hub.set_cfg(topics=_list_param(topics), reel_len=int(reel_len) if reel_len else None, style=style or None,
                            voice=voice or None, outputs=_list_param(outputs),
                            fast=None if fast is None else (bool(fast) and str(fast).lower() not in ("false", "0")), tracks=tracks,
                            music=None if music is None else (bool(music) and str(music).lower() not in ("false", "0")))
    return {"cfg": c, "text": f"Đã lưu: {len(c['topics'])} chủ đề, reels {c['reel_len']} giây, kiểu {content_hub.STYLES[c['style']]}, "
                              f"đầu ra: {', '.join(content_hub.OUTPUTS[o] for o in c['outputs'])}."}


def noidung_tai_video(cid: str) -> dict:
    from core import store as _st
    from webapp import server as _srv
    r = _st.get(cid)
    if not r or not r.get("video"):
        raise ValueError("Không tìm thấy video")
    name = re.sub(r"[^\w\-]+", "-", (r.get("title") or "video").replace("Reels: ", ""), flags=re.UNICODE).strip("-")[:60] or "video"
    return {"url": _srv.sign_download(r["video"], f"{name}.mp4"), "file_name": f"{name}.mp4"}


register(Agent("noidung", "Nội dung", "🎬", "Săn tin theo chủ đề + case founder AI, quẹt duyệt, tự tạo reels Facebook và bài đăng group/fanpage", order=35, actions=[
    Action("tongquan", "Hàng chờ nội dung", noidung_tongquan, icon="🗂", llm=True,
           desc="Xem hàng chờ duyệt tin (id, tuyến, tiêu đề), tin đang tạo và bộ nội dung đã tạo."),
    Action("quet", "Quét tin mới", content_hub.scan, icon="🔎", llm=True, long=True,
           desc="Săn tin mới cho trang Nội dung. track: tin (theo chủ đề) | founder (case founder/startup AI) | roimaxx (agentic commerce, "
                "mô hình kinh doanh enabler, kèm phân tích CAO) | leversphere (chuyển đổi agentic cho công ty POD, kèm phân tích CAO) | bỏ trống = mọi tuyến.",
           params=[Param("track", "Tuyến", "select", options=["", "tin", "founder", "roimaxx", "leversphere"], default="")]),
    Action("them", "Dán bài hoặc link", content_hub.add_manual, icon="📎", llm=True, long=True,
           desc="Thêm 1 bài anh gửi (dán chữ hoặc link) vào hàng chờ; make_now=true để tạo reels + bài đăng ngay.",
           params=[Param("text", "Nội dung bài", "textarea"), Param("url", "Link"), Param("make_now", "Tạo ngay", "bool", default=False)]),
    Action("duyet", "Duyệt và tạo reels", noidung_duyet, icon="✅", llm=True,
           desc="Duyệt 1 tin trong hàng chờ: tạo video reels chuẩn Facebook + bài group + bài fanpage (chạy nền). "
                "style: auto|founder|tin|bai_hoc; reel_len: 15|30|45|60; outputs: reel,group,page; angle: chỉ đạo thêm.",
           params=[Param("id", "ID tin", required=True), Param("style", "Kiểu", "select", options=list(content_hub.STYLES)),
                   Param("reel_len", "Độ dài reels (giây)", "number"), Param("outputs", "Đầu ra"), Param("angle", "Chỉ đạo thêm", "textarea")]),
    Action("boqua", "Bỏ qua tin", content_hub.skip, hidden=True, llm=True, desc="Bỏ qua 1 tin trong hàng chờ.",
           params=[Param("iid", "ID tin", required=True)]),
    Action("hoantac", "Đưa lại vào hàng chờ", content_hub.undo, hidden=True, params=[Param("iid", "ID tin", required=True)]),
    Action("bo", "Xem bộ nội dung", content_hub.pack_view, hidden=True, params=[Param("iid", "ID tin", required=True)]),
    Action("caidat", "Chủ đề & định dạng", noidung_caidat, icon="🎛", llm=True,
           desc="Đổi chủ đề săn tin (topics, cách nhau dấu phẩy, thay toàn bộ danh sách), bật/tắt tuyến (tin, founder), "
                "định dạng mặc định: reel_len 30|45|60|90, style auto|founder|tin|bai_hoc, voice HoaiMy|NamMinh, outputs reel,group,page, fast (nhịp nhanh).",
           params=[Param("topics", "Chủ đề", "textarea"), Param("reel_len", "Độ dài reels", "number"), Param("style", "Kiểu"),
                   Param("voice", "Giọng đọc"), Param("outputs", "Đầu ra"), Param("fast", "Nhịp nhanh", "bool"),
                   Param("tin", "Tuyến tin theo chủ đề", "bool"), Param("founder", "Tuyến founder", "bool"),
                   Param("roimaxx", "Tuyến agentic commerce (Roimaxx)", "bool"), Param("leversphere", "Tuyến chuyển đổi (Leversphere)", "bool"),
                   Param("music", "Nhạc nền video", "bool")]),
    Action("phan_tich", "Phân tích CAO 1 tin", content_hub.analyze_item, hidden=True, long=True, llm=True,
           desc="Phân tích chuyên sâu (vai CAO) 1 tin trong hàng chờ theo 2 lăng kính Roimaxx và Leversphere.",
           params=[Param("iid", "ID tin", required=True)]),
    Action("chien_luoc", "Chiến lược agentic commerce", strategy.overview, hidden=True, llm=True,
           desc="Tổng quan tình báo chiến lược: 2 tài liệu sống (Roimaxx mô hình kinh doanh agentic commerce enabler; Leversphere lộ trình "
                "chuyển đổi agentic e-commerce) + các insight đã phân tích gần đây."),
    Action("insight", "Xem 1 insight", strategy.insight, hidden=True, params=[Param("iid", "ID", required=True)]),
    Action("tai_lieu", "Xem tài liệu chiến lược", strategy.doc, hidden=True, llm=True,
           desc="Đọc toàn văn tài liệu chiến lược: lens = roimaxx (mô hình kinh doanh agentic commerce enabler) | leversphere (lộ trình chuyển đổi).",
           params=[Param("lens", "Lăng kính", required=True)]),
    Action("cap_nhat_tai_lieu", "Cập nhật tài liệu chiến lược", strategy.build, hidden=True, long=True, llm=True,
           desc="Viết lại tài liệu chiến lược từ insight mới nhất + Second Brain. lens = roimaxx | leversphere.",
           params=[Param("lens", "Lăng kính", required=True)]),
    Action("dung_lai", "Dựng lại video", reel_studio.rerender, hidden=True,
           params=[Param("cid", "ID video", required=True), Param("voice", "Giọng"), Param("speed", "Tốc độ"), Param("music", "Nhạc nền"),
                   Param("length", "Độ dài", "number"), Param("rewrite", "Viết lại kịch bản", "bool"), Param("angle", "Chỉ đạo thêm", "textarea")]),
    Action("studio", "Trạng thái Reel Studio", reel_studio.state, hidden=True, params=[Param("cid", "ID video", required=True)]),
    Action("chinh_nhanh", "Chỉnh nhanh video bằng lời", reel_studio.quick_edit, hidden=True, long=True, llm=True,
           desc="Sửa video bản tin theo yêu cầu bằng lời (giọng, tốc độ, nhạc, độ dài, hook, nội dung) rồi dựng lại. cid = ID video.",
           params=[Param("cid", "ID video", required=True), Param("instruction", "Yêu cầu", "textarea", required=True)]),
    Action("sua_kich_ban", "Sửa kịch bản và dựng lại", reel_studio.edit_script, hidden=True,
           params=[Param("cid", "ID video", required=True), Param("scenes", "Các cảnh (JSON)", "textarea", required=True)]),
    Action("chon_ban", "Chọn phiên bản video", reel_studio.choose_version, hidden=True,
           params=[Param("cid", "ID video", required=True), Param("vid", "ID phiên bản", required=True)]),
    Action("caption", "Lưu caption", reel_studio.set_caption, hidden=True,
           params=[Param("cid", "ID video", required=True), Param("caption", "Caption", "textarea")]),
    Action("cong_thuc_luu", "Lưu công thức reels", reel_studio.save_recipe, hidden=True, long=True, llm=True,
           desc="Lưu công thức làm reels anh ưng ý (cài đặt + cấu trúc + quy tắc) vào Second Brain, đặt làm mặc định cho video sau.",
           params=[Param("cid", "ID video", required=True), Param("name", "Tên công thức"), Param("notes", "Ghi chú", "textarea"),
                   Param("make_default", "Đặt mặc định", "bool", default=True)]),
    Action("cong_thuc_ds", "Các công thức reels", reel_studio.recipes, hidden=True),
    Action("cong_thuc_macdinh", "Đặt công thức mặc định", reel_studio.set_default, hidden=True, params=[Param("rid", "ID", required=True)]),
    Action("cong_thuc_xoa", "Xoá công thức", reel_studio.delete_recipe, hidden=True, params=[Param("rid", "ID", required=True)]),
    Action("skill_xem", "Skill News Studio", reel_studio.skill_view, hidden=True),
    Action("skill_capnhat", "Cập nhật skill News Studio", reel_studio.build_skill, hidden=True, long=True),
    Action("hoi_bai", "Hỏi phóng viên về 1 bài", content_hub.reporter_ask, hidden=True, long=True, llm=True,
           desc="Phóng viên công nghệ superHuy đào sâu 1 bài trong trang Nội dung (bối cảnh, số liệu, đối thủ, tin liên quan) và đề xuất ý tưởng "
                "cho công việc của anh. iid = ID tin, question = câu hỏi.",
           params=[Param("iid", "ID tin", required=True), Param("question", "Câu hỏi", "textarea", required=True)]),
    Action("hoi_bai_ds", "Trao đổi về 1 bài", content_hub.reporter_thread, hidden=True, params=[Param("iid", "ID tin", required=True)]),
    Action("hoi_bai_luu", "Lưu câu trả lời vào Second Brain", content_hub.reporter_save, hidden=True,
           params=[Param("iid", "ID tin", required=True), Param("idx", "Vị trí", "number", default=-1)]),
    Action("gui_video", "Gửi video vào Telegram", content_hub.send_video, hidden=True, params=[Param("cid", "ID video", required=True)]),
    Action("tai_video", "Link tải video", noidung_tai_video, hidden=True, params=[Param("cid", "ID video", required=True)]),
]))


# ================================================================ Học tập (trong Phát triển)
def hoc_tongquan() -> dict:
    v = learning.overview()
    t = learning.today_text()
    return {**v, "text": t or ("Chưa có khoá học nào." if not v["courses"] else "Hôm nay anh đã học xong các bài.")}


register(Agent("hoc", "Học tập", "📚", "Khoá học theo chủ đề: bài học, audio, quiz, ôn tập giãn cách, thực hành áp dụng Leversphere & Sellnity", order=56, actions=[
    Action("tongquan", "Khoá học của anh", hoc_tongquan, hidden=True, llm=True,
           desc="Các khoá học đang học, bài hôm nay, tiến độ, điểm quiz, câu cần ôn."),
    Action("tao", "Tạo khoá học", learning.create_course, hidden=True, long=True, llm=True,
           desc="Thiết kế khoá học mới theo chủ đề (bài mỗi ngày, quiz, thực hành áp dụng Leversphere/Sellnity). "
                "template: claude-code-30 (Claude Code 30 ngày) hoặc bỏ trống; sources: link tài liệu/repo tham khảo.",
           params=[Param("topic", "Chủ đề"), Param("goal", "Mục tiêu", "textarea"), Param("days", "Số ngày", "number", default=30),
                   Param("level", "Trình độ"), Param("sources", "Link tham khảo", "textarea"), Param("template", "Mẫu")]),
    Action("khoa", "Xem khoá học", learning.course, hidden=True, params=[Param("cid", "ID", required=True)]),
    Action("ngay", "Bài học 1 ngày", learning.day_view, hidden=True, long=True, llm=True,
           desc="Mở bài học của 1 ngày (tự soạn nếu chưa có): nội dung, tài nguyên, quiz, bài thực hành.",
           params=[Param("cid", "ID khoá", required=True), Param("day", "Ngày", "number", required=True)]),
    Action("audio", "Bài giảng audio", learning.make_audio, hidden=True, long=True,
           params=[Param("cid", "ID khoá", required=True), Param("day", "Ngày", "number", required=True), Param("voice", "Giọng")]),
    Action("quiz", "Nộp quiz", learning.quiz_submit, hidden=True,
           params=[Param("cid", "ID khoá", required=True), Param("day", "Ngày", "number", required=True), Param("answers", "Đáp án", required=True)]),
    Action("on_tap", "Câu cần ôn", learning.review_due, hidden=True, params=[Param("cid", "ID khoá", required=True)]),
    Action("on_tap_nop", "Nộp ôn tập", learning.review_submit, hidden=True,
           params=[Param("cid", "ID khoá", required=True), Param("answers", "Đáp án", required=True)]),
    Action("nop", "Nộp bài thực hành", learning.submit, hidden=True, long=True, llm=True,
           desc="Nộp bài thực hành của 1 ngày học để superHuy chấm theo tiêu chí và nhận xét.",
           params=[Param("cid", "ID khoá", required=True), Param("day", "Ngày", "number", required=True), Param("text", "Bài làm", "textarea"),
                   Param("link", "Link"), Param("reflection", "Phản tư", "textarea")]),
    Action("xong", "Đánh dấu xong ngày", learning.mark_done, hidden=True,
           params=[Param("cid", "ID khoá", required=True), Param("day", "Ngày", "number", required=True)]),
    Action("luu_tru", "Lưu trữ khoá", learning.archive, hidden=True, params=[Param("cid", "ID khoá", required=True)]),
]))


# ================================================================ Meeting Studio
def hop_tao(upload_id: str, name: str = "", title: str = "", hint: str = "", started: str = "", source: str = "Tải file") -> dict:
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,40}", upload_id or ""):
        raise ValueError("Mã tải lên không hợp lệ")
    part = meeting.INBOX / f"{upload_id}.part"
    if not part.exists() or part.stat().st_size < 2000:
        raise ValueError("Chưa nhận được file âm thanh, anh thử tải lại.")
    ext = (re.search(r"\.([A-Za-z0-9]{2,5})$", name or "") or [None, "bin"])[1].lower()
    raw = part.with_name(f"{upload_id}.{ext}")
    part.rename(raw)
    m = meeting.create(str(raw), source or "Tải file", title or "", hint or "", started or "")
    return {"id": m["id"], "text": "Đã nhận âm thanh. superHuy đang chép lời và biên tập, xong sẽ báo anh."}


def hop_danhsach() -> dict:
    v = meeting.view_list()
    lines = [f"• [{x['id']}] {x['title'] or '(đang xử lý)'} · {(x.get('started') or '')[:10]} · {meeting.ORGS.get(x['org'], {}).get('name', '')}"
             + (f" › {x['project']}" if x.get("project") else "") + ("" if x["status"] == "done" else f" ({x.get('step') or x['status']})")
             for x in v["items"][:20]]
    return {**v, "text": "\n".join(lines) or "Chưa có cuộc họp nào."}


def hop_xem(id: str) -> dict:
    m = meeting.view(id)
    r = m.get("recap") or {}
    txt = f"{m.get('title')}\n{r.get('summary', '')}"
    if r.get("decisions"):
        txt += "\nQuyết định: " + "; ".join(x["text"] for x in r["decisions"])
    if r.get("next_steps"):
        txt += "\nViệc tiếp theo: " + "; ".join(x["text"] + (f" ({x['owner']})" if x.get("owner") else "") for x in r["next_steps"])
    return {**m, "text": txt}


def hop_nhan(id: str, org: str = None, project: str = None, department: str = None, type: str = None) -> dict:
    return meeting.set_labels(id, org=org, project=project, department=department, type=type)


def hop_tu_dien(words: str) -> dict:
    f = meeting.ROOT / "glossary.txt"
    meeting.ROOT.mkdir(parents=True, exist_ok=True)
    cur = f.read_text(encoding="utf-8") if f.exists() else ""
    f.write_text(cur + "\n" + "\n".join(w.strip() for w in re.split(r"[,;\n]+", words) if w.strip()), encoding="utf-8")
    return {"text": "Đã thêm vào từ điển chép lời: " + words}


def hop_chia_se(mid: str, parts: str = "", days: int = 14, note: str = "") -> dict:
    return meeting_share.share_text(mid, parts or None, days, note)


def hop_chia_se_email(mid: str, to: str, parts: str = "", note: str = "", cc: str = "", platform: str = "gmail", days: int = 14) -> dict:
    return meeting_share.send_email(mid, to, parts or None, days, note, platform, cc)


def hop_chia_se_lark(mid: str, chat_id: str, parts: str = "", note: str = "", days: int = 14) -> dict:
    return meeting_share.send_lark(mid, chat_id, parts or None, days, note)


def hop_lark_nhom() -> dict:
    if not lark_agent.ready():
        return {"items": [], "text": "Chưa kết nối Lark."}
    items = lark_agent.chats()
    return {"items": items, "text": "\n".join(f"• {c['name']} ({c['id']})" for c in items) or "Bot chưa ở nhóm Lark nào."}


register(Agent("hop", "Họp", "🎙", "Meeting Studio: ghi âm, chép lời, biên bản họp, sơ đồ, hỏi lại nội dung các cuộc họp", order=33, actions=[
    Action("danhsach", "Các cuộc họp", hop_danhsach, icon="🗂", llm=True, desc="Danh sách cuộc họp đã ghi (id, tiêu đề, ngày, tổ chức, dự án, trạng thái)."),
    Action("xem", "Xem biên bản", hop_xem, hidden=True, llm=True, desc="Xem biên bản 1 cuộc họp theo id: tóm tắt, quyết định, việc tiếp theo.",
           params=[Param("id", "ID cuộc họp", required=True)]),
    Action("hoi", "Hỏi lại nội dung họp", meeting.ask, icon="❓", llm=True,
           desc="Hỏi bất cứ điều gì đã bàn trong các cuộc họp (ai phụ trách, đã chốt gì, số liệu...). Tự tìm trong kho biên bản + lời thoại, "
                "trả lời ngắn kèm nguồn (cuộc họp, mốc thời gian). meeting_id để giới hạn trong 1 cuộc họp.",
           params=[Param("question", "Câu hỏi", "textarea", required=True), Param("meeting_id", "ID cuộc họp (tuỳ chọn)")]),
    Action("tao", "Tạo cuộc họp từ file đã tải", hop_tao, hidden=True,
           params=[Param("upload_id", "Mã tải lên", required=True), Param("name", "Tên file"), Param("title", "Tiêu đề"),
                   Param("hint", "Ghi chú bối cảnh"), Param("started", "Bắt đầu lúc"), Param("source", "Nguồn")]),
    Action("doi_ten", "Đổi tên người nói", meeting.rename_speaker, hidden=True, llm=True, desc="Đặt tên thật cho người nói S1, S2... trong 1 cuộc họp.",
           params=[Param("mid", "ID cuộc họp", required=True), Param("spk", "Nhãn (S1...)", required=True), Param("name", "Tên", required=True)]),
    Action("nhan", "Sửa phân loại", hop_nhan, hidden=True, llm=True,
           desc="Sửa phân loại cuộc họp: org sellnity|leversphere|ca-nhan|khac, project, department, type. Tự ghi lại vào Obsidian.",
           params=[Param("id", "ID", required=True), Param("org", "Tổ chức"), Param("project", "Dự án"), Param("department", "Phòng ban"), Param("type", "Loại")]),
    Action("lam_lai", "Làm lại biên bản", meeting.reprocess, hidden=True, llm=True,
           desc="Biên tập lại biên bản (what=recap) hoặc chép lời lại từ đầu (what=all).",
           params=[Param("mid", "ID", required=True), Param("what", "recap|all", default="recap")]),
    Action("xoa", "Xoá cuộc họp", meeting.delete, hidden=True, params=[Param("mid", "ID", required=True)]),
    Action("tu_dien", "Thêm từ vào từ điển chép lời", hop_tu_dien, icon="📖", llm=True,
           desc="Thêm tên riêng/thuật ngữ (cách nhau dấu phẩy) để chép lời đúng chính tả.",
           params=[Param("words", "Các từ", "textarea", required=True)]),
    Action("chia_se", "Tạo liên kết chia sẻ biên bản", hop_chia_se, hidden=True, llm=True,
           desc="Tạo trang web chia sẻ biên bản 1 cuộc họp (tóm tắt, quyết định, ai làm gì, sơ đồ, dòng thời gian) + tin nhắn soạn sẵn "
                "để anh dán vào Zalo/Telegram/Lark/Messenger. parts: các phần, cách nhau dấu phẩy, trong "
                "summary,decisions,next_steps,mindmap,sections,open_questions,suggestions,transcript,audio (bỏ trống = mặc định, không gồm lời thoại/âm thanh).",
           params=[Param("mid", "ID cuộc họp", required=True), Param("parts", "Các phần", default=""),
                   Param("days", "Số ngày hiệu lực", "number", default=14), Param("note", "Lời nhắn kèm", default="")]),
    Action("chia_se_email", "Gửi biên bản qua email", hop_chia_se_email, hidden=True, llm=True,
           desc="Gửi biên bản cuộc họp qua email (HTML đẹp + liên kết trang chia sẻ). PHẢI hỏi anh xác nhận người nhận trước khi gửi.",
           params=[Param("mid", "ID cuộc họp", required=True), Param("to", "Email người nhận (nhiều người cách nhau dấu phẩy)", required=True),
                   Param("parts", "Các phần", default=""), Param("note", "Lời nhắn kèm", default=""), Param("cc", "CC", default=""),
                   Param("platform", "gmail hoặc lark", default="gmail"), Param("days", "Số ngày hiệu lực", "number", default=14)]),
    Action("chia_se_lark", "Gửi biên bản vào nhóm Lark", hop_chia_se_lark, hidden=True, llm=True,
           desc="Bot gửi biên bản + liên kết vào 1 nhóm Lark (lấy chat_id bằng hop__lark_nhom). PHẢI hỏi anh xác nhận nhóm trước khi gửi.",
           params=[Param("mid", "ID cuộc họp", required=True), Param("chat_id", "ID nhóm Lark", required=True),
                   Param("parts", "Các phần", default=""), Param("note", "Lời nhắn kèm", default=""), Param("days", "Số ngày hiệu lực", "number", default=14)]),
    Action("lark_nhom", "Các nhóm Lark có bot", hop_lark_nhom, hidden=True, llm=True, desc="Danh sách nhóm Lark (id, tên) mà bot superHuy đang ở trong."),
    Action("chia_se_ds", "Các liên kết đã chia sẻ", meeting_share.list_for, hidden=True, params=[Param("mid", "ID", required=True)]),
    Action("thu_hoi", "Thu hồi liên kết chia sẻ", meeting_share.revoke, hidden=True, llm=True,
           desc="Thu hồi 1 liên kết chia sẻ biên bản (người khác không mở được nữa).", params=[Param("token", "Mã liên kết", required=True)]),
    Action("da_gui", "Đánh dấu đã gửi", meeting_share.mark, hidden=True, params=[Param("token", "Mã"), Param("how", "Kênh")]),
]))


# ================================================================ Đăng bài
def dich_list(kind: str = "post") -> dict:
    rows = []
    for t in targets_mod.load():
        rows.append({**t, "label": targets_mod.label(t), "auto": bool(targets_mod.api_page(t)),
                     "default": kind in t.get("default_for", [])})
    return {"items": rows, "text": targets_mod.describe()}


def dang_bai(content_id: str, targets: str) -> dict:
    """targets: danh sách id nơi đăng, ngăn cách bởi dấu phẩy."""
    c = store.get(content_id)
    if not c:
        raise ValueError("Không tìm thấy nội dung.")
    results, lines = [], []
    manual_sent = False
    for tid in [x.strip() for x in str(targets).split(",") if x.strip()]:
        t = targets_mod.get(tid)
        if not t:
            continue
        page = targets_mod.api_page(t)
        if page:
            try:
                if c.get("video"):
                    link = publisher.post_video(page, c["video"], c["text"])
                elif c.get("image"):
                    link = publisher.post_photo(page, c["image"], c["text"])
                else:
                    link = publisher.post_text(page, c["text"])
                store.log_post(content_id, tid, "api", link)
                results.append({"target": tid, "name": t["name"], "mode": "api", "ok": True, "link": link})
                lines.append(f"✅ {t['name']}: đã đăng {link}")
            except Exception as e:
                results.append({"target": tid, "name": t["name"], "mode": "api", "ok": False, "error": str(e)})
                lines.append(f"⚠️ {t['name']}: {e}")
        else:
            store.log_post(content_id, tid, "manual", t.get("url", ""))
            results.append({"target": tid, "name": t["name"], "mode": "manual", "ok": True, "url": t.get("url", "")})
            lines.append(f"📋 {t['name']}: mở {t.get('url', '')} và dán nội dung")
            if not manual_sent:  # gửi gói vào chat để tải ảnh/video trên điện thoại
                manual_sent = True
                if c.get("video"):
                    notify.send(video=c["video"], caption=f"🎬 {c['title']} (tải về để đăng)")
                elif c.get("image"):
                    notify.send(photo=c["image"], caption=f"🖼 {c['title']} (tải về để đăng)")
                notify.send(text=c["text"])
    return {"text": "\n".join(lines) or "Chưa chọn nơi đăng.", "items": results}


register(Agent("dang", "Đăng bài", "📤", "Đăng lên Page (tự động) và Group/trang cá nhân (sao chép + mở)", order=50, actions=[
    Action("dich", "Danh sách nơi đăng", dich_list, icon="🎯", params=[Param("kind", "Loại nội dung", "select",
           options=list(store.KINDS), default="post")]),
    Action("dang", "Đăng nội dung", dang_bai, hidden=True,
           params=[Param("content_id", "ID nội dung", required=True), Param("targets", "Nơi đăng (id, cách nhau dấu phẩy)", required=True)]),
]))


# ================================================================ Second brain
def brain_luu(text: str) -> dict:
    path, title = second_brain.save_any(text)
    return {"text": f"Đã lưu: {title}\n{path.replace(str(second_brain.OBSIDIAN_VAULT), '')}"}


def brain_gan_day(limit: int = 15) -> dict:
    vault = second_brain.OBSIDIAN_VAULT
    files = sorted((p for p in vault.rglob("*.md") if "Templates" not in p.parts and p.name != "README.md"),
                   key=lambda p: p.stat().st_mtime, reverse=True)[:int(limit)] if vault.exists() else []
    items = [{"title": p.stem, "folder": str(p.parent.relative_to(vault))} for p in files]
    return {"items": items, "text": "\n".join(f"• {i['title']} ({i['folder']})" for i in items) or "Chưa có ghi chú."}


def brain_tim(query: str) -> dict:
    from core import kb
    hits = kb.search(query, k=8)
    if not hits:
        return {"text": f"Không thấy ghi chú nào khớp “{query}” trong Obsidian.", "items": []}
    items = [{"title": h["title"], "note": h["note"], "path": h["path"], "head": h["head"], "own": h["own"], "updated": h["updated"],
              "snippet": re.sub(r"\s+", " ", h["text"])[:280]} for h in hits]
    return {"items": items, "text": "\n".join(f"• [[{h['note']}]]{' › ' + h['head'] if h['head'] else ''} ({h['path']}): {h['snippet'][:220]}" for h in items)}


def brain_doc(path: str) -> dict:
    from core import kb
    n = kb.read_note(path)
    return {**n, "text": f"[[{n['title']}]] (sửa {n['updated']})\n{n['body'][:6000]}"}


def brain_ghi(title: str, content: str, kind: str = "kien-thuc", tags: str = "") -> dict:
    path = second_brain.save_knowledge(title, content, kind, [t.strip() for t in re.split(r"[,;]", tags or "") if t.strip()])
    rel = path.replace(str(second_brain.OBSIDIAN_VAULT), "").lstrip("/")
    return {"text": f"Đã ghi vào Second Brain: {rel}", "path": rel}


def brain_tongquan() -> dict:
    """Màn hình Second Brain: quy mô kho, đồng bộ, ghi chú anh vừa viết trên Mac, ghi chú superHuy vừa lưu."""
    from core import kb, memory, vault_sync
    st = vault_sync.status()
    st.pop("public_key", None)
    st.pop("remote", None)
    out = {"stats": kb.stats(), "sync": st, "sources": knowledge_sources.all_status(), "mac": vault_sync.recent_by("Obsidian Mac", 12), "recent": brain_gan_day(12)["items"],
           "memory": len(memory.facts()), "memory_extra": len(memory.vault_additions()), "memory_note": memory.VAULT_NOTE}
    return out


def brain_dongbo() -> dict:
    from core import vault_sync
    st = vault_sync.status()
    if not st["enabled"]:
        return {**st, "text": "Chưa bật đồng bộ Obsidian (thiếu VAULT_GIT_REMOTE trên máy chủ)."}
    r = vault_sync.sync()
    st = vault_sync.status()
    return {**st, "text": f"Đồng bộ Obsidian: {r}. Kho có {st['notes']} ghi chú, lần ghi gần nhất {st.get('last_commit', '?')}."}


def brain_nguon() -> dict:
    items = knowledge_sources.all_status()
    return {"items": items, "text": "\n".join(f"• {x['name']}: {'đã kết nối' if x.get('connected') else 'chưa kết nối'} · {x.get('detail', '')}"
                                             + (f" · đồng bộ {x['last_sync']}" if x.get("last_sync") else "") for x in items)}


register(Agent("brain", "Second Brain", "🧠", "Kho tri thức Obsidian: superHuy tra cứu khi trả lời, lưu kiến thức tích luỹ", order=60, actions=[
    Action("tongquan", "Tổng quan Second Brain", brain_tongquan, hidden=True),
    Action("luu", "Lưu link hoặc ghi chú", brain_luu, icon="📥", long=True, llm=True,
           desc="Lưu một link bài viết hoặc đoạn văn vào Obsidian (tự tóm tắt, gắn thẻ).",
           params=[Param("text", "Link hoặc nội dung", "textarea", required=True)]),
    Action("ghi", "Ghi kiến thức / kết luận", brain_ghi, icon="✍️", llm=True,
           desc="Ghi một kiến thức, kết luận, quyết định hoặc câu trả lời đáng giữ vào Second Brain (Obsidian) để tích luỹ, "
                "superHuy sẽ tham chiếu lại sau. content viết gọn, đủ ngữ cảnh (vì sao, khi nào áp dụng).",
           params=[Param("title", "Tiêu đề", required=True), Param("content", "Nội dung", "textarea", required=True),
                   Param("kind", "Loại: kien-thuc | quyet-dinh | bai-hoc | y-tuong", default="kien-thuc"),
                   Param("tags", "Thẻ, cách nhau dấu phẩy", default="")]),
    Action("gan_day", "Ghi chú gần đây", brain_gan_day, icon="🗒", llm=True,
           desc="Liệt kê các ghi chú mới lưu gần đây trong Obsidian.", params=[Param("limit", "Số lượng", "number", default=15)]),
    Action("tim", "Tìm trong Obsidian", brain_tim, icon="🔎", llm=True,
           desc="Tìm sâu trong kho ghi chú Obsidian của anh (gồm ghi chú anh tự viết trên Mac), không phân biệt dấu. "
                "Dùng khi anh hỏi về điều anh đã ghi chép, ý tưởng, tài liệu, quyết định trước đây.",
           params=[Param("query", "Từ khoá", required=True)]),
    Action("doc", "Đọc một ghi chú", brain_doc, hidden=True, llm=True,
           desc="Đọc toàn văn 1 ghi chú Obsidian theo path (lấy từ brain__tim).", params=[Param("path", "Đường dẫn", required=True)]),
    Action("dongbo", "Đồng bộ Obsidian ngay", brain_dongbo, icon="🔄", llm=True,
           desc="Đồng bộ ngay kho ghi chú giữa superHuy và Obsidian trên Mac (qua repo git), và báo tình trạng."),
    Action("nguon", "Các nguồn tri thức", brain_nguon, hidden=True, llm=True,
           desc="Tình trạng các nguồn tri thức đã kết nối (Obsidian, Gemini Notebook...)."),
    Action("dongbo_nguon", "Đồng bộ 1 nguồn tri thức", knowledge_sources.sync, hidden=True, long=True, llm=True,
           desc="Nạp lại dữ liệu từ 1 nguồn: obsidian | gemini.", params=[Param("source", "Nguồn", required=True)]),
    Action("gemini_ma", "Mã kết nối Gemini Notebook", gemini_notebook.new_code, hidden=True),
    Action("gemini_ngat", "Ngắt Gemini Notebook", gemini_notebook.disconnect, hidden=True,
           params=[Param("keep_data", "Giữ dữ liệu đã nạp", "bool", default=True)]),
    Action("notebook_ds", "Các notebook Gemini", gemini_notebook.list_text, hidden=True, llm=True,
           desc="Danh sách notebook trong Gemini Notebook (NotebookLM) của anh đã nạp vào superHuy."),
    Action("hoi_notebook", "Hỏi 1 notebook Gemini", gemini_notebook.ask, hidden=True, llm=True,
           desc="Hỏi trực tiếp 1 notebook trong Gemini Notebook (NotebookLM) của anh: Gemini trả lời dựa trên các nguồn của notebook đó, "
                "có trích nguồn. Dùng khi anh nhắc tên notebook hoặc cần câu trả lời sâu từ tài liệu trong notebook. notebook = tên (gần đúng) hoặc id.",
           params=[Param("question", "Câu hỏi", "textarea", required=True), Param("notebook", "Tên notebook", required=True)]),
]))



# ================================================================ Cài đặt
def chon_giong(voice: str) -> dict:
    reel_video.set_voice(voice)
    return {"text": f"Đã chọn giọng {voice} cho video."}


def nghe_thu(voice: str = "NamMinh") -> dict:
    path = reel_video.voice_sample(voice)
    notify.send(document=path, caption=f"🎙 Giọng {voice}")
    return {"text": f"Đã gửi bản nghe thử giọng {voice} vào chat Telegram.", "audio": path}


def ket_noi_lich_email(gmail: str = "", app_password: str = "", google_ics: str = "", lark_ics: str = "") -> dict:
    """Lưu cấu hình (không in ra bí mật) rồi kiểm tra thử."""
    from core.envfile import set_env
    import os
    lines = []
    if gmail:
        set_env("GMAIL_ADDRESS", gmail.strip())
    if app_password:
        set_env("GMAIL_APP_PASSWORD", app_password.replace(" ", "").strip())
    for key, val in (("GOOGLE_CAL_ICS", google_ics), ("LARK_ICS", lark_ics)):
        if val:
            v = val.strip().replace("webcal://", "https://")
            if not v.startswith("https://"):
                raise ValueError("Link lịch phải bắt đầu bằng https:// hoặc webcal://")
            set_env(key, v)
    if os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"):
        try:
            n = len(email_agent.fetch_emails_imap(int(dt.datetime.now().timestamp()) - 86400))
            lines.append(f"✅ Gmail (IMAP): đọc được {n} email trong 24 giờ qua. Không còn hết hạn 7 ngày.")
        except Exception as e:
            lines.append(f"⚠️ Gmail chưa đăng nhập được: {e}. Kiểm tra App Password và đã bật IMAP.")
    for label, url in calendar_agent.ics_sources():
        try:
            import requests
            r = requests.get(url, timeout=30)
            ok = r.ok and b"BEGIN:VCALENDAR" in r.content[:200]
            lines.append(f"{'✅' if ok else '⚠️'} Lịch {label}: {'đọc được' if ok else 'link không trả về lịch (HTTP ' + str(r.status_code) + ')'}")
        except Exception as e:
            lines.append(f"⚠️ Lịch {label}: {e}")
    return {"text": "\n".join(lines) or "Chưa nhập thông tin nào."}


def ket_noi_cau_noi_lich(url: str) -> dict:
    name = gcal_bridge.pair(url)
    return {"text": f"✅ Đã kết nối cầu nối Google Calendar ({name}). Giờ bạn tạo lịch và gắn màu ngay trong app."}


def ket_noi_lark_mail(address: str, password: str) -> dict:
    from core.envfile import set_env
    import smtplib, ssl
    with smtplib.SMTP_SSL("smtp.larksuite.com", 465, context=ssl.create_default_context(), timeout=30) as smtp:
        smtp.login(address.strip(), password.strip())
    set_env("LARK_MAIL_ADDRESS", address.strip())
    set_env("LARK_MAIL_PASSWORD", password.strip())
    return {"text": f"✅ Đã kết nối Lark Mail {address.strip()}. Bạn có thể chọn Lark khi soạn thư."}


def ket_noi_lark(app_id: str = "", app_secret: str = "", domain: str = "Lark quốc tế") -> dict:
    from core.envfile import set_env
    if app_id:
        set_env("LARK_APP_ID", app_id.strip())
    if app_secret:
        set_env("LARK_APP_SECRET", app_secret.strip())
    set_env("LARK_DOMAIN", "https://open.feishu.cn" if domain == "Feishu (Trung Quốc)" else "https://open.larksuite.com")
    lark_agent._tok.update(v=None, exp=0)
    try:
        cs = lark_agent.chats()
        return {"text": f"✅ Đã kết nối Lark. Bot đang ở {len(cs)} group" + (": " + ", ".join(c["name"] for c in cs[:10]) if cs else
                        ". Hãy thêm bot vào các group cần theo dõi (Cài đặt group > Bot > Thêm bot).")}
    except Exception as e:
        return {"text": f"⚠️ Chưa kết nối được Lark: {e}"}


def ket_noi_lich_lark() -> dict:
    from agents import lark_oauth, lark_calendar
    if not lark_agent.ready():
        raise ValueError("Cần kết nối app Lark trước (Kết nối > Lark).")
    url = lark_oauth.authorize_url(lark_oauth.new_state("calendar"), lark_calendar.SCOPES, lark_oauth.LOCAL_REDIRECT)
    return {"text": "Làm bước này trên máy Mac đang chạy bot: bấm nút dưới, đăng nhập Lark và chọn Authorize. "
                    "Xong quay lại app, lịch và lời mời họp Lark sẽ hiện ra.",
            "open_url": url}


def tinh_trang() -> dict:
    from core import qc
    port = int(os.getenv("WEBAPP_PORT", "8787"))
    qc.quick_checks(port)
    qc.connection_checks()
    items = qc.status_items()
    bad = [i for i in items if not i["ok"]]
    return {"items": items, "text": "Mọi thứ đang hoạt động bình thường." if not bad else f"{len(bad)} mục cần xử lý."}


def doi_pin(old_pin: str, new_pin: str) -> dict:
    from core import security
    if security.pin_enabled():
        ok, msg = security.verify(old_pin.strip(), "đổi mã PIN")
        if not ok:
            raise ValueError(msg)
    security.set_pin(new_pin.strip())
    return {"text": f"✅ Đã đổi mã PIN ({len(new_pin.strip())} số). Lần mở app sau sẽ dùng mã mới."}


def ket_noi_fb(token: str) -> dict:
    return fb_connect.connect(token)


# ------------------------------------------------------------------ VIỆC (tasks hub)
def _labels(v) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v]
    return [x.strip() for x in str(v or "").split(",") if x.strip()]


def viec_tongquan(refresh: bool = False) -> dict:
    from agents import tasks_hub
    d = tasks_hub.overview(bool(refresh))
    s = d["stats"]
    d["text"] = (f"Việc đang mở: {s['open']} · hạn hôm nay {s['today']} · quá hạn {s['overdue']} · cần xem xét {s['review']} · "
                 f"xong 30 ngày qua {s['done30']}.")
    top = [t for t in d["items"] if not t["done"]][:10]
    if top:
        d["text"] += "\n" + "\n".join(f"• [{t['id']}] {t['title']}" + (f" (hạn {t['due'][8:10]}/{t['due'][5:7]})" if t["due"] else "")
                                      + (" ⚠️ quá hạn" if t["overdue"] else "") for t in top)
    return d


def viec_hieu(text: str) -> dict:
    from agents import tasks_hub
    return tasks_hub.parse(text)


def viec_tao(title: str, due: str = "", time: str = "", source: str = "local", assignee_id: str = "", assignee: str = "",
             list_id: str = "", area: str = "work", labels="", notes: str = "") -> dict:
    from agents import tasks_hub
    if assignee and not assignee_id and source != "local":
        p = tasks_hub.find_person(assignee)
        if p:
            assignee_id, source = p["id"], "lark"
    return tasks_hub.create(title, due, time, source, assignee_id, list_id, area, _labels(labels), notes, assignee)


def viec_nhanh(text: str) -> dict:
    """Tạo việc bằng 1 câu (super bot dùng)."""
    from agents import tasks_hub
    d = tasks_hub.parse(text)
    return tasks_hub.create(d["title"], d["due"], d["time"], d["source"], d["assignee_id"], "", d["area"], d["labels"],
                            d["notes"], "" if d["assignee_id"] else d["assignee"])


def viec_xong(task_id: str, done: bool = True) -> dict:
    from agents import tasks_hub
    return tasks_hub.set_done(task_id, bool(done))


def viec_trangthai(task_id: str, status: str) -> dict:
    from agents import tasks_hub
    return tasks_hub.set_status(task_id, status)


def viec_giahan(task_id: str, due: str, time: str = "") -> dict:
    from agents import tasks_hub
    return tasks_hub.extend(task_id, due, time)


def viec_nhan(task_id: str, area: str = "", labels="") -> dict:
    from agents import tasks_hub
    return tasks_hub.tag(task_id, area, _labels(labels))


def viec_xoa(task_id: str) -> dict:
    from agents import tasks_hub
    return tasks_hub.delete_local(task_id)


def viec_goiy() -> dict:
    from agents import tasks_hub
    return tasks_hub.review()


AREA_OPTS = [{"value": "work", "label": "Công việc"}, {"value": "income", "label": "Thu nhập"},
             {"value": "health", "label": "Sức khoẻ"}, {"value": "relations", "label": "Quan hệ"},
             {"value": "skills", "label": "Năng lực"}, {"value": "self", "label": "Bản thân"}]

register(Agent("viec", "Việc", "✅", "Mọi việc từ Lark, Google Tasks và superHuy ở một nơi: tạo, giao việc, gắn nhãn, báo cáo",
               order=12, actions=[
    Action("tongquan", "Danh sách việc + báo cáo", viec_tongquan, icon="📋", llm=True, long=True,
           desc="Xem việc đang mở, hạn hôm nay, quá hạn, cần xem xét; số việc hoàn thành.",
           params=[Param("refresh", "Làm mới", "bool", default=False)]),
    Action("nhanh", "Tạo việc bằng 1 câu", viec_nhanh, icon="⚡", llm=True, long=True, hidden=True,
           desc="Ví dụ: 'Giao Linh làm báo cáo Q4 trước thứ 6, dự án Ads'. Có tên người -> giao qua Lark.",
           params=[Param("text", "Câu mô tả việc", required=True)]),
    Action("hieu", "Hiểu câu tạo việc", viec_hieu, long=True, hidden=True, params=[Param("text", "Câu", required=True)]),
    Action("tao", "Tạo việc", viec_tao, hidden=True, long=True, params=[
        Param("title", "Tên việc", required=True), Param("due", "Hạn (YYYY-MM-DD)"), Param("time", "Giờ (HH:MM)"),
        Param("source", "Lưu ở", "select", options=["local", "lark", "google"], default="local"),
        Param("assignee_id", "ID người nhận (Lark)"), Param("assignee", "Người nhận"), Param("list_id", "Danh sách/dự án"),
        Param("area", "Lĩnh vực", "select", options=AREA_OPTS, default="work"), Param("labels", "Nhãn"), Param("notes", "Ghi chú")]),
    Action("xong", "Đánh dấu xong", viec_xong, hidden=True, long=True, llm=True,
           params=[Param("task_id", "ID việc", required=True), Param("done", "Xong", "bool", default=True)]),
    Action("trangthai", "Đổi trạng thái", viec_trangthai, hidden=True, long=True,
           params=[Param("task_id", "ID việc", required=True), Param("status", "Trạng thái", "select", options=["todo", "doing", "done"], required=True)]),
    Action("giahan", "Gia hạn", viec_giahan, hidden=True, long=True, llm=True,
           params=[Param("task_id", "ID việc", required=True), Param("due", "Hạn mới (YYYY-MM-DD)", required=True), Param("time", "Giờ")]),
    Action("nhan", "Gắn nhãn", viec_nhan, hidden=True,
           params=[Param("task_id", "ID việc", required=True), Param("area", "Lĩnh vực"), Param("labels", "Nhãn")]),
    Action("xoa", "Xoá việc", viec_xoa, hidden=True, params=[Param("task_id", "ID việc", required=True)]),
    Action("goiy", "superHuy gợi ý xử lý việc tồn", viec_goiy, icon="✨", long=True, llm=True,
           desc="AI đề xuất gia hạn, làm ngay, giao việc hay bỏ cho từng việc quá hạn/treo lâu."),
]))


# ------------------------------------------------------------------ TÀI CHÍNH
def tc_tongquan(month: str = "") -> dict:
    from agents import finance
    d = finance.overview(month)
    r = d["report"]
    d["text"] = (f"Tháng {r['month'][5:]}/{r['month'][:4]}: thu {finance.fmt(r['income'])}, chi {finance.fmt(r['expense'])}, "
                 f"còn {finance.fmt(r['net'])}" + (f", tiết kiệm {r['savings_rate']:.0%}" if r["savings_rate"] is not None else "")
                 + f". Phải thu {finance.fmt(r['receivable'])}, phải trả {finance.fmt(r['payable'])}.")
    return d


def tc_ghi(text: str) -> dict:
    from agents import finance
    return finance.quick(text)


def tc_hieu(text: str) -> dict:
    from agents import finance
    return finance.parse(text)


def tc_them(kind: str, amount: str, category: str = "", note: str = "", date: str = "", account: str = "bank",
            party: str = "", due: str = "") -> dict:
    from agents import finance
    if kind in ("receivable", "payable"):
        return finance.add_debt(kind, party or note, amount, due, note)
    return finance.add_tx(kind, amount, category, note, date, account)


def tc_xoa(tx_id: str) -> dict:
    from agents import finance
    return finance.delete_tx(tx_id)


def tc_tatoan(debt_id: str, amount: str = "") -> dict:
    from agents import finance
    return finance.settle_debt(debt_id, amount or None)


def tc_ngansach(category: str, amount: str = "") -> dict:
    from agents import finance
    return finance.set_budget(category, amount)


def tc_phantich(month: str = "") -> dict:
    from agents import finance
    return finance.analyze(month)


register(Agent("taichinh", "Tài chính", "💰", "Thu chi, phải thu phải trả, ngân sách, báo cáo và phân tích hằng tháng",
               order=14, actions=[
    Action("tongquan", "Báo cáo tài chính tháng", tc_tongquan, icon="📊", llm=True,
           desc="Thu, chi, dòng tiền, tỷ lệ tiết kiệm, theo danh mục, phải thu/phải trả.",
           params=[Param("month", "Tháng (YYYY-MM)", hint="để trống = tháng này")]),
    Action("ghi", "Ghi thu chi bằng 1 câu", tc_ghi, icon="✍️", llm=True, long=True,
           desc="Ví dụ: 'cafe 45k', 'nhận lương 80tr', 'Linh nợ 5tr trả cuối tháng', 'trả tiền nhà 12tr'.",
           params=[Param("text", "Câu ghi chép", required=True)]),
    Action("hieu", "Hiểu câu thu chi", tc_hieu, long=True, hidden=True, params=[Param("text", "Câu", required=True)]),
    Action("them", "Thêm giao dịch", tc_them, hidden=True, params=[
        Param("kind", "Loại", "select", options=["expense", "income", "receivable", "payable"], required=True),
        Param("amount", "Số tiền", required=True), Param("category", "Danh mục"), Param("note", "Ghi chú"),
        Param("date", "Ngày"), Param("account", "Tài khoản"), Param("party", "Người/đơn vị"), Param("due", "Hạn")]),
    Action("xoa", "Xoá giao dịch", tc_xoa, hidden=True, params=[Param("tx_id", "ID", required=True)]),
    Action("tatoan", "Thu/trả nợ", tc_tatoan, hidden=True, params=[Param("debt_id", "ID", required=True), Param("amount", "Số tiền")]),
    Action("ngansach", "Đặt ngân sách", tc_ngansach, hidden=True,
           params=[Param("category", "Danh mục", required=True), Param("amount", "Số tiền/tháng")]),
    Action("phantich", "Phân tích & gợi ý tối ưu", tc_phantich, icon="✨", llm=True, long=True,
           desc="Trợ lý tài chính phân tích tháng và đề xuất tối ưu chi tiêu.",
           params=[Param("month", "Tháng (YYYY-MM)")]),
]))


# ------------------------------------------------------------------ PHÁT TRIỂN (mục tiêu, thói quen, lịch trình, trí nhớ)
def _sched(v) -> dict:
    """'daily' | 'weekdays' | 'weekly:3' | 'days:0,2,4' | dict"""
    if isinstance(v, dict):
        return v
    v = str(v or "daily").strip().lower()
    if v.startswith("weekly"):
        n = re.search(r"\d+", v)
        return {"type": "weekly", "times": int(n.group(0)) if n else 3}
    if v.startswith("days"):
        return {"type": "days", "days": sorted({int(x) for x in re.findall(r"\d", v) if int(x) < 7})}
    return {"type": "weekdays"} if v.startswith("weekday") else {"type": "daily"}


def pt_tongquan() -> dict:
    from agents import growth
    o = growth.overview()
    lines = [f"Thói quen hôm nay: {o['today_done']}/{o['today_due']}"]
    lines += [("✅ " if h["done_today"] else "⬜ ") + f"[{h['id']}] {h['title']}" + (f" · chuỗi {h['streak']}" if h["streak"] else "")
              for h in o["habits"] if h["due_today"]]
    lines.append("\nMục tiêu:")
    for g in o["goals"]:
        m = g.get("metric") or {}
        lines.append(f"• [{g['id']}] {g['title']}" + (f" · {m.get('name')}: {g['current']} {m.get('unit','')} → {m.get('target')}" if m.get("name") and g.get("current") is not None else "")
                     + (f" · còn {g['days_left']} ngày" if g.get("days_left") is not None else "")
                     + f" · cột mốc {g['milestones_done']}/{len(g.get('milestones') or [])}")
    return {**o, "text": "\n".join(lines)}


def pt_checkin(habit: str, done: bool = True, date: str = "") -> dict:
    from agents import growth
    h = next((x for x in growth._load()["habits"] if x["id"] == habit), None) or growth.find_habit(habit)
    if not h:
        raise ValueError(f"Không tìm thấy thói quen “{habit}”")
    return growth.checkin(h["id"], bool(done), date)


def pt_them_thoiquen(title: str, schedule: str = "daily", time: str = "", target: str = "", goal: str = "", area: str = "health", why: str = "") -> dict:
    from agents import growth
    g = (next((x for x in growth._load()["goals"] if x["id"] == goal), None) or growth.find_goal(goal)) if goal else None
    return growth.add_habit(title, (g or {}).get("area", area), (g or {}).get("id", ""), _sched(schedule), time, target, why)


def pt_sua_thoiquen(habit_id: str, title: str = "", schedule: str = "", time: str = "", target: str = "", archived: bool = False) -> dict:
    from agents import growth
    return growth.update_habit(habit_id, title=title or None, schedule=_sched(schedule) if schedule else None,
                               time=time or None, target=target or None, archived=True if archived else None)


def pt_ghi_chiso(goal: str, value: str, date: str = "", note: str = "") -> dict:
    from agents import growth
    g = next((x for x in growth._load()["goals"] if x["id"] == goal), None) or growth.find_goal(goal)
    if not g:
        raise ValueError(f"Không tìm thấy mục tiêu “{goal}”")
    return growth.log_metric(g["id"], value, date, note)


def pt_them_muctieu(title: str, area: str = "self", why: str = "", target_date: str = "", metric_name: str = "",
                    unit: str = "", start: str = "", target: str = "") -> dict:
    from agents import growth
    f = lambda x: float(str(x).replace(",", ".")) if str(x).strip() else None
    metric = {"name": metric_name, "unit": unit, "start": f(start), "target": f(target)} if metric_name else {}
    if metric and metric["start"] is not None and metric["target"] is not None:
        metric["direction"] = "down" if metric["target"] < metric["start"] else "up"
    return growth.add_goal(title, area, why, target_date, metric)


def pt_cotmoc(goal_id: str, index: int) -> dict:
    from agents import growth
    return growth.toggle_milestone(goal_id, int(index))


def pt_goiy(goal: str) -> dict:
    from agents import growth
    g = next((x for x in growth._load()["goals"] if x["id"] == goal), None) or growth.find_goal(goal)
    if not g:
        raise ValueError(f"Không tìm thấy mục tiêu “{goal}”")
    r = growth.coach(g["id"])
    r["text"] = (r.get("summary", "") + "\n\nThói quen đề xuất:\n" + "\n".join(f"• {h['title']} ({h.get('target','')})" for h in r.get("habits", []))
                 + "\n\nCột mốc:\n" + "\n".join(f"• {m}" for m in r.get("milestones", []))
                 + "\n\nTuần mẫu:\n" + "\n".join(r.get("week_plan", [])) + "\n\nMở trang Phát triển để thêm đề xuất vào thói quen.")
    return r


def pt_nhan_goiy(goal_id: str, kind: str, index: int) -> dict:
    from agents import growth
    return growth.accept_suggestion(goal_id, kind, int(index))


def pt_lichtrinh(date: str = "", note: str = "") -> dict:
    from agents import planner
    return planner.plan(date, note)


def pt_xem_lichtrinh(date: str = "") -> dict:
    from agents import planner
    from agents.calendar_agent import TZ
    d = (date or dt.datetime.now(TZ).date().isoformat())[:10]
    p = planner.get(d)
    return {**(p or {}), "plan": p, "text": planner._as_text(p) if p else "Chưa có lịch trình cho ngày này."}


def pt_ap_lichtrinh(date: str = "", indexes: str = "") -> dict:
    from agents import planner
    from agents.calendar_agent import TZ
    d = (date or dt.datetime.now(TZ).date().isoformat())[:10]
    idx = [int(x) for x in re.findall(r"\d+", indexes)] if str(indexes).strip() else None
    return planner.apply(d, idx)


def nho(text: str, kind: str = "profile") -> dict:
    from core import memory
    memory.add(text, kind, "anh")
    return {"text": "superHuy đã ghi nhớ."}


def quen(query: str) -> dict:
    from core import memory
    n = memory.forget_matching(query)
    return {"text": f"Đã quên {n} điều liên quan." if n else "Không tìm thấy điều nào khớp để quên."}


def nho_xoa(fact_id: str) -> dict:
    from core import memory
    return memory.remove(fact_id)


def nho_ds() -> dict:
    from core import memory
    return {"items": memory.facts(), "kinds": memory.KINDS, "text": memory.context() or "Chưa ghi nhớ gì."}


SCHED_HINT = "daily | weekdays | weekly:3 (3 lần/tuần) | days:0,2,4 (0=Thứ 2 … 6=Chủ nhật)"
register(Agent("phattrien", "Phát triển", "🌱", "Mục tiêu, thói quen, lịch trình ngày và những gì superHuy hiểu về anh",
               order=16, actions=[
    Action("tongquan", "Thói quen + mục tiêu hôm nay", pt_tongquan, icon="🌱", llm=True,
           desc="Xem thói quen cần làm hôm nay, chuỗi ngày, tiến độ mục tiêu và chỉ số."),
    Action("checkin", "Đánh dấu thói quen", pt_checkin, llm=True, hidden=True,
           desc="Đánh dấu đã làm (hoặc bỏ đánh dấu) một thói quen, theo id hoặc tên gần đúng.",
           params=[Param("habit", "Id hoặc tên thói quen", required=True), Param("done", "Đã làm", "bool", default=True),
                   Param("date", "Ngày (YYYY-MM-DD), mặc định hôm nay")]),
    Action("them_thoiquen", "Thêm thói quen", pt_them_thoiquen, llm=True, hidden=True,
           params=[Param("title", "Tên thói quen", required=True), Param("schedule", "Lịch lặp", hint=SCHED_HINT, default="daily"),
                   Param("time", "Giờ gợi ý HH:MM"), Param("target", "Mức cụ thể"), Param("goal", "Thuộc mục tiêu (id hoặc tên)"),
                   Param("area", "Lĩnh vực", "select", options=AREA_OPTS, default="health"), Param("why", "Vì sao")]),
    Action("sua_thoiquen", "Sửa/ẩn thói quen", pt_sua_thoiquen, hidden=True, llm=True,
           params=[Param("habit_id", "Id thói quen", required=True), Param("title", "Tên mới"), Param("schedule", "Lịch lặp", hint=SCHED_HINT),
                   Param("time", "Giờ"), Param("target", "Mức"), Param("archived", "Ẩn (lưu trữ)", "bool", default=False)]),
    Action("ghi_chiso", "Ghi chỉ số mục tiêu", pt_ghi_chiso, llm=True, hidden=True,
           desc="Ghi số đo cho mục tiêu, ví dụ cân nặng hôm nay 86,4 kg, km chạy tuần này.",
           params=[Param("goal", "Id hoặc tên mục tiêu/chỉ số", required=True), Param("value", "Giá trị", required=True),
                   Param("date", "Ngày"), Param("note", "Ghi chú")]),
    Action("them_muctieu", "Thêm mục tiêu", pt_them_muctieu, llm=True, hidden=True,
           params=[Param("title", "Mục tiêu", required=True), Param("area", "Lĩnh vực", "select", options=AREA_OPTS, default="self"),
                   Param("why", "Vì sao"), Param("target_date", "Hạn (YYYY-MM-DD)"), Param("metric_name", "Tên chỉ số"),
                   Param("unit", "Đơn vị"), Param("start", "Giá trị đầu"), Param("target", "Giá trị đích")]),
    Action("cotmoc", "Đánh dấu cột mốc", pt_cotmoc, hidden=True,
           params=[Param("goal_id", "Id mục tiêu", required=True), Param("index", "Thứ tự", "number", required=True)]),
    Action("goiy", "Huấn luyện viên AI đề xuất", pt_goiy, icon="✨", llm=True, long=True,
           desc="Đề xuất thói quen, cột mốc và tuần mẫu cho một mục tiêu (an toàn, khả thi).",
           params=[Param("goal", "Id hoặc tên mục tiêu", required=True)]),
    Action("nhan_goiy", "Thêm đề xuất", pt_nhan_goiy, hidden=True,
           params=[Param("goal_id", "Id mục tiêu", required=True), Param("kind", "habit|milestone", required=True),
                   Param("index", "Thứ tự", "number", required=True)]),
    Action("lichtrinh", "Lên lịch trình ngày", pt_lichtrinh, icon="🗓", llm=True, long=True,
           desc="superHuy lập thời khoá biểu tối ưu cho một ngày từ lịch họp, việc, thói quen và mục tiêu.",
           params=[Param("date", "Ngày (YYYY-MM-DD), mặc định hôm nay"), Param("note", "Ghi chú cho ngày (năng lượng, ưu tiên...)")]),
    Action("xem_lichtrinh", "Xem lịch trình đã lập", pt_xem_lichtrinh, hidden=True, llm=True, params=[Param("date", "Ngày")]),
    Action("ap_lichtrinh", "Đưa lịch trình vào Google Calendar", pt_ap_lichtrinh, llm=True, hidden=True, long=True,
           desc="Tạo sự kiện Google Calendar cho các khối đã chọn (mặc định: làm việc sâu, tập, học, gia đình).",
           params=[Param("date", "Ngày"), Param("indexes", "Số thứ tự khối, ví dụ '0,2,5' (để trống = khối chính)")]),
    Action("nho", "Ghi nhớ về anh", nho, llm=True, hidden=True,
           desc="Lưu một điều bền vững về anh (sức khoẻ, mục tiêu, sở thích, công việc, gia đình, nếp sinh hoạt).",
           params=[Param("text", "Điều cần nhớ", required=True),
                   Param("kind", "Loại", "select", options=["profile", "health", "goal", "work", "preference", "relation", "finance", "routine"], default="profile")]),
    Action("quen", "Quên một điều", quen, llm=True, hidden=True, params=[Param("query", "Từ khoá điều cần quên", required=True)]),
    Action("nho_xoa", "Xoá trí nhớ", nho_xoa, hidden=True, params=[Param("fact_id", "Id", required=True)]),
    Action("nho_ds", "Những gì superHuy nhớ", nho_ds, hidden=True),
]))


register(Agent("caidat", "Cài đặt", "⚙️", "Kết nối Gmail, lịch Google/Lark, Facebook Page, giọng đọc", order=90, actions=[
    Action("ketnoi", "Kết nối Gmail & lịch (không hết hạn)", ket_noi_lich_email, icon="🔗",
           desc="Gmail qua App Password + lịch Google/Lark qua link iCal bí mật. Bỏ trống ô nào thì giữ nguyên ô đó.",
           params=[Param("gmail", "Địa chỉ Gmail", hint="ten@gmail.com"),
                   Param("app_password", "App Password Gmail (16 ký tự)", "password"),
                   Param("google_ics", "Google Calendar: Địa chỉ bí mật iCal", "password"),
                   Param("lark_ics", "Lark Calendar: link đăng ký (CalDAV/ICS)", "password")]),
    Action("caunoilich", "Kết nối tạo lịch Google (cầu nối)", ket_noi_cau_noi_lich, icon="📅",
           desc="Dán link Web app của Apps Script 'SuperHuy Calendar Bridge'. Cho phép tạo sự kiện và gắn màu ưu tiên.",
           params=[Param("url", "Link Web app", "password", required=True)]),
    Action("larkmail", "Kết nối Lark Mail (gửi thư)", ket_noi_lark_mail, icon="✉️",
           desc="Lark Mail > Cài đặt > IMAP/SMTP: bật và tạo mật khẩu riêng, rồi dán vào đây.",
           params=[Param("address", "Địa chỉ Lark Mail", required=True), Param("password", "Mật khẩu IMAP/SMTP", "password", required=True)]),
    Action("lark", "Kết nối Lark (tin nhắn group)", ket_noi_lark, icon="💬",
           desc="App ID + App Secret của app Lark nội bộ có bật Bot. Không hết hạn.",
           params=[Param("app_id", "App ID", hint="cli_..."), Param("app_secret", "App Secret", "password"),
                   Param("domain", "Nền tảng", "select", options=["Lark quốc tế", "Feishu (Trung Quốc)"], default="Lark quốc tế")]),
    Action("larklich", "Kết nối lịch Lark", ket_noi_lich_lark, icon="📅",
           desc="Đăng nhập Lark 1 lần để xem lịch và duyệt lời mời họp ngay trong app."),
    Action("tinhtrang", "Tình trạng hệ thống", tinh_trang, icon="🩺", long=True, hidden=True,
           desc="QC kiểm tra máy chủ, link app, Gmail, AI, Lark, lịch."),
    Action("doipin", "Đổi mã PIN", doi_pin, icon="🔒",
           desc="Mã PIN 4 đến 8 số, dùng để mở Mini App và super bot.",
           params=[Param("old_pin", "Mã PIN hiện tại", "password"), Param("new_pin", "Mã PIN mới", "password", required=True)]),
    Action("facebook", "Kết nối Facebook Page", ket_noi_fb, icon="🔑",
           desc="Dán User Access Token (Graph API Explorer). Bot tự lấy token của các Page và lưu vào .env.",
           params=[Param("token", "User Access Token", "password", required=True)]),
    Action("giong", "Chọn giọng đọc video", chon_giong, icon="🎙",
           params=[Param("voice", "Giọng", "select", options=list(reel_video.VOICES), default="NamMinh", required=True)]),
    Action("nghe", "Nghe thử giọng", nghe_thu, icon="🔊", long=True,
           params=[Param("voice", "Giọng", "select", options=list(reel_video.VOICES), default="NamMinh")]),
]))


def settings_snapshot() -> dict:
    cur = reel_video.get_voice()
    return {"voice": next((k for k, v in reel_video.VOICES.items() if v == cur), cur)}


# ================================================================ Trạng thái kết nối (màn hình Kết nối)
def connections_status() -> list[dict]:
    import json as _j
    import os
    from config import DATA_DIR
    rows = []
    g = bool(os.getenv("GMAIL_ADDRESS") and os.getenv("GMAIL_APP_PASSWORD"))
    rows.append({"id": "gmail", "name": "Gmail", "ok": g, "detail": os.getenv("GMAIL_ADDRESS", "") if g else "Chưa kết nối",
                 "action": ["caidat", "ketnoi"]})
    cal = [lbl for lbl, _ in calendar_agent.ics_sources()]
    if gcal_bridge.ready():
        cal = ["Google (tạo được)"] + cal
    rows.append({"id": "calendar", "name": "Lịch", "ok": bool(cal),
                 "detail": " + ".join(dict.fromkeys(cal)) if cal else "Chưa có lịch nào", "action": ["caidat", "ketnoi"]})
    rows.append({"id": "gcal_write", "name": "Tạo lịch Google", "ok": gcal_bridge.ready(),
                 "detail": "Đã bật" if gcal_bridge.ready() else "Chưa bật, cần cầu nối Apps Script", "action": ["caidat", "caunoilich"]})
    from agents import lark_calendar
    from core import security
    rows.append({"id": "larkcal", "name": "Lịch Lark", "ok": lark_calendar.ready(),
                 "detail": "Xem lịch + duyệt lời mời" if lark_calendar.ready() else "Chưa kết nối, cần đăng nhập Lark 1 lần",
                 "action": ["caidat", "larklich"]})
    rows.append({"id": "security", "name": "Mã PIN", "ok": security.pin_enabled(),
                 "detail": (f"Bật · {security.pin_length()} số · bot tự khóa sau {security.bot_lock_minutes()} phút")
                 if security.pin_enabled() else "Chưa đặt mã PIN", "action": ["caidat", "doipin"]})
    rows.append({"id": "larkmail", "name": "Lark Mail", "ok": mailbox.lark_mail_ready(),
                 "detail": os.getenv("LARK_MAIL_ADDRESS", "") or "Chưa kết nối, chỉ gửi qua Gmail", "action": ["caidat", "larkmail"]})
    lark_ok = lark_agent.ready()
    joined = ""
    try:
        r = _j.loads((DATA_DIR / "lark_join_result.json").read_text(encoding="utf-8"))
        joined = f"Theo dõi {len(r['ok'])} group"
    except Exception:
        pass
    rows.append({"id": "lark", "name": "Lark", "ok": lark_ok, "detail": (joined or "Đã kết nối") if lark_ok else "Chưa kết nối",
                 "action": ["lark", "join"] if lark_ok else ["caidat", "lark"]})
    pages = publisher.pages()
    rows.append({"id": "facebook", "name": "Facebook Page", "ok": bool(pages),
                 "detail": ", ".join(p["name"] for p in pages) if pages else "Chưa có token, đăng thủ công",
                 "action": ["caidat", "facebook"]})
    vault = second_brain.OBSIDIAN_VAULT
    rows.append({"id": "obsidian", "name": "Obsidian", "ok": vault.exists(), "detail": "~/" + vault.name, "action": ["brain", "gan_day"]})
    return rows
