"""Điểm khởi chạy: bot Telegram (long-polling) + bộ lập lịch cho các agent."""
import asyncio
import datetime as dt
import json
import logging
import os
import re
import threading

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from telegram import (BotCommand, BotCommandScopeChat, BotCommandScopeDefault, InlineKeyboardButton, InlineKeyboardMarkup,
                      MenuButtonDefault, MenuButtonWebApp, Update, WebAppInfo)
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import brain
import hub
import news_bot
from agents import calendar_agent, email_agent, news_agent
from core import bot_guard, digests, notify, qc, store
from webapp import server as webapp_server
from webapp.tunnel import Tunnel
from config import (EMAIL_DIGEST_HOURS, LARK_DIGEST_HOURS, NEWS_HOUR, OWNER_CHAT_ID, REMINDER_HOUR,
                    TELEGRAM_TOKEN, TIMEZONE, require_config)

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # không ghi token Telegram vào log
logging.getLogger("httpx2").setLevel(logging.WARNING)
log = logging.getLogger("agent-army")
HISTORY: list[dict] = []
MAX_HISTORY = 16

# Chỉ chủ nhân (đúng chat ID) mới được điều khiển bot: đây là khóa bảo mật quan trọng nhất.
# Lớp thứ 2 (lớp 1 là core/bot_guard chạy trước mọi handler). Không có OWNER_CHAT_ID thì chặn hết.
OWNER_ONLY = filters.User(user_id=OWNER_CHAT_ID or -1) & filters.ChatType.PRIVATE


async def send(app: Application, text: str):
    for i in range(0, len(text), 4000):  # Telegram giới hạn ~4096 ký tự/tin
        await app.bot.send_message(chat_id=OWNER_CHAT_ID, text=text[i:i + 4000])


async def job_evening_reminder(app: Application):
    log.info("Chạy nhắc lịch ngày mai")
    text = await asyncio.to_thread(calendar_agent.tomorrow_reminder)
    extra = []
    try:
        from agents import finance, tasks_hub
        from agents import growth
        extra = [x for x in (await asyncio.to_thread(growth.today_line), await asyncio.to_thread(tasks_hub.digest_line),
                             await asyncio.to_thread(finance.digest_line)) if x]
    except Exception:
        log.exception("Không lấy được tóm tắt việc/tài chính")
    await send(app, "🔔 Nhắc lịch ngày mai\n\n" + text + ("\n\n" + "\n".join(extra) if extra else ""))


async def job_morning_plan(app: Application):
    """Sáng sớm: superHuy lập lịch trình hôm nay và gửi vào Telegram."""
    from agents import planner
    try:
        p = await asyncio.to_thread(planner.plan)
    except Exception as e:
        log.exception("Lỗi lập lịch trình sáng")
        await send(app, f"⚠️ superHuy chưa lập được lịch trình hôm nay: {e}")
        return
    await send(app, "☀️ Chào buổi sáng anh Huy!\n\n" + p["text"] + "\n\nMở app › Phát triển để chỉnh và đưa các khối vào Google Calendar.")


async def job_finance_monthly(app: Application):
    """Ngày 1 hằng tháng: báo cáo + phân tích tài chính tháng trước."""
    from agents import finance
    prev = (dt.date.today().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    r = await asyncio.to_thread(finance.month_report, prev)
    if not r["income"] and not r["expense"]:
        return
    a = await asyncio.to_thread(finance.analyze, prev)
    head = (f"💰 Báo cáo tài chính tháng {prev[5:]}/{prev[:4]}\n"
            f"Thu {finance.fmt(r['income'])} · Chi {finance.fmt(r['expense'])} · Còn {finance.fmt(r['net'])}\n\n")
    await send(app, head + a["text"])


async def job_email_digest(app: Application):
    """Phiên email buổi tối: phân loại hộp thư (nhãn, ưu tiên) + tổng hợp phân tích kể từ phiên trước."""
    log.info("Chạy phiên email buổi tối")
    try:
        from agents import mailbox
        if mailbox.gmail_ready():
            await asyncio.to_thread(mailbox.sync, 2)
    except Exception:
        log.exception("Lỗi phân loại hộp thư")
    text = await asyncio.to_thread(email_agent.hourly_digest)
    if text:
        digests.save("email", text)
        await send(app, text)


async def job_lark_digest(app: Application):
    from agents import lark_agent
    if not lark_agent.ready():
        return
    log.info("Chạy tổng hợp tin nhắn Lark")
    try:
        lt = await asyncio.to_thread(lark_agent.digest)
        if lt:
            digests.save("lark", lt)
            await send(app, lt)
    except Exception as e:
        log.exception("Lỗi tổng hợp Lark")
        await send(app, f"⚠️ Không đọc được tin nhắn Lark: {e}")


WEBAPP_PORT = int(os.getenv("WEBAPP_PORT", "8787"))
from config import DATA_DIR  # noqa: E402
DATA_FILE_MENU = DATA_DIR / "menu_url.txt"


def bootstrap_extra() -> dict:
    """Dữ liệu cho màn hình Mini App (tin hôm nay, Studio, nơi đăng)."""
    try:
        nt = json.loads(news_agent.NEWS_FILE.read_text(encoding="utf-8"))
    except Exception:
        nt = {}
    return {"news": nt.get("items", []), "news_date": nt.get("date", ""),
            "contents": store.recent(60), "targets": hub.dich_list()["items"],
            "settings": hub.settings_snapshot(), "today": dt.date.today().isoformat(),
            "connections": hub.connections_status(), "digests": digests.load(), "cq": _cq()}


def _cq() -> dict:
    try:
        from agents import content_hub
        return content_hub.queue_view()
    except Exception:
        log.exception("Không đọc được hàng chờ Nội dung")
        return {}


def _app_button(app: Application):
    url = app.bot_data.get("webapp_url")
    return InlineKeyboardMarkup([[InlineKeyboardButton("📱 Mở app", web_app=WebAppInfo(url=url))]]) if url else None


async def cmd_app(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mk = _app_button(ctx.application)
    if not mk:
        await update.message.reply_text("Mini App đang khởi động đường hầm, thử lại sau 30 giây nhé.")
        return
    await update.message.reply_text("Bảng điều khiển của bạn:", reply_markup=mk)


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📱 Bấm nút \"Mở app\" cạnh ô chat (hoặc /app) để dùng giao diện đầy đủ.\n\n"
        "Super bot đã sẵn sàng. Bạn cứ nhắn tự nhiên, ví dụ:\n"
        "• Mai mình có lịch gì?\n• Tóm tắt email 6 giờ qua\n\n"
        "Lệnh nhanh: /lich (lịch ngày mai) · /email (tóm tắt email 3 giờ qua)\n"
        "/tin (Top 5 tin hot) · /viet 2 (viết content cho tin số 2)"
    )


async def cmd_lich(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(await asyncio.to_thread(calendar_agent.tomorrow_reminder))


async def cmd_email(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    text = await asyncio.to_thread(email_agent.hourly_digest, 3)
    await update.message.reply_text(text or "Không có email mới.")


async def answer_text(ctx: ContextTypes.DEFAULT_TYPE, text: str):
    await ctx.bot.send_chat_action(chat_id=OWNER_CHAT_ID, action=ChatAction.TYPING)
    HISTORY.append({"role": "user", "content": text})
    try:
        answer = await asyncio.to_thread(brain.chat, HISTORY[-MAX_HISTORY:])
    except Exception as e:
        log.exception("Lỗi super bot")
        answer = f"⚠️ Có lỗi khi xử lý: {e}"
    HISTORY.append({"role": "assistant", "content": answer})
    del HISTORY[:-MAX_HISTORY]
    await ctx.bot.send_message(chat_id=OWNER_CHAT_ID, text=answer[:4000])


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await answer_text(ctx, update.message.text)


RESTART_FLAG = DATA_DIR / "restart.flag"


async def job_restart_watch(app: Application):
    """Khởi động lại không cần màn hình: tạo file data/restart.flag -> bot thoát, launchd (KeepAlive) tự chạy lại."""
    if qc.SELFTEST_FLAG.exists():
        try:
            qc.SELFTEST_FLAG.unlink()
        except Exception:
            pass
        import threading
        threading.Thread(target=qc.selftest, daemon=True, name="selftest").start()  # chạy riêng, không chặn restart
    if RESTART_FLAG.exists():
        try:
            RESTART_FLAG.unlink()
        except Exception:
            pass
        log.info("Có yêu cầu khởi động lại (restart.flag), thoát để launchd chạy lại")
        os._exit(0)


CONTENT_SCAN_HOURS = [int(x) for x in os.getenv("CONTENT_SCAN_HOURS", "7,15").split(",") if x.strip().isdigit()]


async def job_content_scan(app: Application):
    """Săn tin cho trang Nội dung (tin theo chủ đề + case founder AI), báo số tin chờ duyệt."""
    from agents import content_hub
    r = await asyncio.to_thread(content_hub.scan)
    if r.get("added"):
        await send(app, f"📰 {r['added']} tin mới đang chờ anh duyệt ở trang Nội dung (quẹt phải để tạo reels). Tổng chờ duyệt: {r['pending']}.")


async def job_game_shield():
    from agents import game
    await asyncio.to_thread(game.shield_job)


async def job_learning_nightly():
    from agents import learning
    await asyncio.to_thread(learning.nightly)


async def job_learning_remind():
    from agents import learning
    from core import notify
    t = learning.today_text()
    if t:
        notify.send(text=t + "\nMở app › Phát triển › Học tập để học, làm quiz và nộp bài thực hành.")


def _learning_bootstrap():
    """Lần đầu: tạo khoá Claude Code 30 ngày (dựa trên Claude HowTo) với bài thực hành cho Leversphere và Sellnity."""
    from agents import learning
    try:
        if not learning._load():
            learning.create_course("", template="claude-code-30")
            from core import notify
            notify.send(text="📚 superHuy đã tạo khoá “Claude Code 30 ngày: xây đội agent cho Leversphere & Sellnity”. "
                             "Bài ngày 1 (kèm audio, quiz, bài thực hành) đã sẵn trong app › Phát triển › Học tập.")
    except Exception:
        log.exception("Tạo khoá học đầu tiên lỗi")


async def job_strategy_weekly():
    """Thứ Hai: viết lại 2 tài liệu sống (Roimaxx, Leversphere) từ insight tuần qua."""
    from agents import strategy
    await asyncio.to_thread(strategy.weekly)
    from core import notify
    notify.send(text="🧭 Đã cập nhật tài liệu chiến lược tuần này: mô hình kinh doanh Roimaxx và lộ trình chuyển đổi Leversphere. "
                     "Mở app › Nội dung › Chiến lược để xem.")


def _strategy_bootstrap():
    """Lần đầu: nạp bối cảnh + săn tin chiến lược + viết bản đầu của 2 tài liệu."""
    from agents import content_hub, strategy
    from core import memory, notify
    memory.seed_once([
        ("work", "Roimaxx: định vị ban đầu là one-stop-shop e-commerce enabler, nay anh Huy định hướng thành agentic e-commerce enabler "
                 "(giúp doanh nghiệp khác triển khai agentic commerce: Agents Factory + agency/consulting chuyển đổi AI)."),
        ("work", "Leversphere là công ty POD (print on demand); anh Huy là CGO kiêm CAO, đang lập lộ trình chuyển Leversphere sang mô hình agentic e-commerce."),
    ])
    if any(strategy.doc(k).get("version") for k in strategy.LENSES):
        return
    try:
        if len(strategy._load()) < 4:
            for t in strategy.LENSES:
                content_hub.scan(t)
        strategy.weekly()
        notify.send(text="🧭 superHuy đã có bản đầu tiên của 2 tài liệu chiến lược: mô hình kinh doanh agentic commerce cho Roimaxx "
                         "và lộ trình chuyển đổi agentic cho Leversphere, kèm các phân tích CAO. Mở app › Nội dung › Chiến lược.")
    except Exception:
        log.exception("Khởi tạo tài liệu chiến lược lỗi")


async def job_knowledge_sync():
    """Nạp lại các nguồn tri thức ngoài Obsidian (Gemini Notebook...) 6 giờ/lần."""
    from agents import knowledge_sources
    try:
        await asyncio.to_thread(knowledge_sources.sync_all_connected)
    except Exception as e:
        log.warning("Đồng bộ nguồn tri thức lỗi: %s", e)


async def job_vault_sync(app: Application):
    from core import qc, vault_sync
    try:
        await asyncio.to_thread(vault_sync.sync)
        qc.report("vault", "Đồng bộ Obsidian (git)", True, "", "")
    except Exception as e:
        log.warning("Đồng bộ vault lỗi: %s", e)
        qc.report("vault", "Đồng bộ Obsidian (git)", False, str(e)[:200], "Kiểm tra VAULT_GIT_REMOTE và deploy key của repo vault.")


_SCHED: list = []
JOB_NAMES = {"job_morning_plan": "Lịch trình buổi sáng", "job_evening_reminder": "Nhắc lịch buổi tối", "job_finance_monthly": "Báo cáo tài chính tháng", "job_lark_digest": "Tổng hợp tin nhắn Lark",
             "job_email_digest": "Phân tích email buổi tối", "job_news": "Bản tin sáng", "job_content_scan": "Săn tin cho trang Nội dung"}


async def job_qc_quick(app: Application):
    await asyncio.to_thread(qc.quick_checks, WEBAPP_PORT)


async def job_qc_connections(app: Application):
    await asyncio.to_thread(qc.connection_checks)


def _on_job_event(ev):
    """Job tự động lỗi hoặc bị lỡ (máy ngủ/tắt) -> báo QC."""
    from apscheduler.events import EVENT_JOB_ERROR
    job = _SCHED[0].get_job(ev.job_id) if _SCHED else None
    name = JOB_NAMES.get(getattr(job, "name", "") or "")
    if not name:
        return
    if ev.code == EVENT_JOB_ERROR:
        qc.incident(f"job:{ev.job_id}", f"Việc tự động “{name}” bị lỗi: {str(ev.exception)[:300]}")
    else:
        qc.incident(f"miss:{ev.job_id}", f"Việc tự động “{name}” bị lỡ lượt chạy (có thể máy Mac đang ngủ/tắt). "
                    "Bật “Prevent automatic sleeping” trong Cài đặt pin của Mac để không bị lỡ.", every=6 * 3600)


async def cmd_qc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🩺 Đang kiểm tra...")
    await asyncio.to_thread(qc.quick_checks, WEBAPP_PORT)
    await asyncio.to_thread(qc.connection_checks)
    await update.message.reply_text(qc.status_text())


async def post_init(app: Application):
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    scheduler.add_job(job_evening_reminder, CronTrigger(hour=REMINDER_HOUR, minute=0), args=[app],
                      misfire_grace_time=3600, coalesce=True)
    # tự động khi không bấm: Lark theo khung giờ, email 1 phiên buổi tối (bấm trong app = cập nhật ngay)
    scheduler.add_job(job_lark_digest, CronTrigger(hour=LARK_DIGEST_HOURS, minute=0), args=[app],
                      misfire_grace_time=1800, coalesce=True)
    scheduler.add_job(job_email_digest, CronTrigger(hour=EMAIL_DIGEST_HOURS, minute=2), args=[app],
                      misfire_grace_time=3600, coalesce=True)
    plan_at = os.getenv("PLAN_MORNING_AT", "06:30").strip()
    if plan_at.lower() not in ("off", "0", ""):
        ph, pm = (int(x) for x in plan_at.split(":")[:2])
        scheduler.add_job(job_morning_plan, CronTrigger(hour=ph, minute=pm), args=[app], misfire_grace_time=3 * 3600, coalesce=True)
    scheduler.add_job(job_finance_monthly, CronTrigger(day=1, hour=8, minute=40), args=[app],
                      misfire_grace_time=6 * 3600, coalesce=True)
    scheduler.add_job(news_bot.job_news, CronTrigger(hour=NEWS_HOUR, minute=0), args=[app],
                      misfire_grace_time=3600, coalesce=True)
    from core import vault_sync
    if vault_sync.enabled():
        scheduler.add_job(job_vault_sync, "interval", minutes=10, args=[app], coalesce=True, max_instances=1,
                          misfire_grace_time=600, next_run_time=dt.datetime.now() + dt.timedelta(minutes=1))
    scheduler.add_job(job_game_shield, CronTrigger(hour=0, minute=15), misfire_grace_time=6 * 3600, coalesce=True)
    scheduler.add_job(job_learning_nightly, CronTrigger(hour=23, minute=20), misfire_grace_time=3 * 3600, coalesce=True)
    scheduler.add_job(job_learning_remind, CronTrigger(hour=20, minute=0), misfire_grace_time=3600, coalesce=True)
    scheduler.add_job(job_strategy_weekly, CronTrigger(day_of_week="mon", hour=6, minute=20), misfire_grace_time=6 * 3600, coalesce=True)
    scheduler.add_job(job_knowledge_sync, "interval", hours=6, coalesce=True, max_instances=1, misfire_grace_time=3600,
                      next_run_time=dt.datetime.now() + dt.timedelta(minutes=3))
    for h in CONTENT_SCAN_HOURS:
        scheduler.add_job(job_content_scan, CronTrigger(hour=h, minute=10), args=[app], misfire_grace_time=3600, coalesce=True)
    scheduler.add_job(job_restart_watch, "interval", seconds=15, args=[app], coalesce=True, max_instances=1)
    # QC: kiểm tra nhanh mỗi 5 phút, kết nối mỗi giờ; báo ngay khi job lỗi/bị lỡ
    scheduler.add_job(job_qc_quick, "interval", minutes=5, args=[app], coalesce=True, max_instances=1, misfire_grace_time=240,
                      next_run_time=dt.datetime.now() + dt.timedelta(minutes=2))
    scheduler.add_job(job_qc_connections, "interval", minutes=60, args=[app], coalesce=True, max_instances=1, misfire_grace_time=1800,
                      next_run_time=dt.datetime.now() + dt.timedelta(minutes=3))
    from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_MISSED
    scheduler.add_listener(_on_job_event, EVENT_JOB_ERROR | EVENT_JOB_MISSED)
    _SCHED.append(scheduler)
    scheduler.start()
    app.bot_data["scheduler"] = scheduler
    loop = asyncio.get_running_loop()

    # cho mọi công cụ (kể cả chạy từ Mini App) gửi được tin/ảnh/video vào chat
    async def _send(text=None, photo=None, video=None, document=None, caption=None):
        if text:
            for i in range(0, len(text), 4000):
                await app.bot.send_message(chat_id=OWNER_CHAT_ID, text=text[i:i + 4000], disable_web_page_preview=True)
        for kind, path in (("photo", photo), ("video", video), ("document", document)):
            if path:
                with open(path, "rb") as f:
                    fn = getattr(app.bot, f"send_{kind}")
                    await fn(chat_id=OWNER_CHAT_ID, caption=caption, read_timeout=300, write_timeout=300, **{kind: f})

    notify.set_sender(lambda **kw: asyncio.run_coroutine_threadsafe(_send(**kw), loop).result(timeout=600))

    # dữ liệu Phát triển ban đầu (3 mục tiêu + thói quen khởi đầu + trí nhớ nền), chỉ chạy 1 lần
    try:
        from agents import growth
        await asyncio.to_thread(growth.seed)
    except Exception:
        log.exception("Không khởi tạo được dữ liệu Phát triển")

    # Nội dung: làm tiếp các tin đã duyệt nhưng chưa tạo xong (bot vừa khởi động lại)
    try:
        from agents import content_hub
        content_hub.resume_pending()
    except Exception:
        log.exception("Không khôi phục được hàng chờ Nội dung")

    try:
        from agents import meeting
        meeting.resume_pending()
    except Exception:
        log.exception("Không khôi phục được hàng chờ Meeting Studio")

    threading.Thread(target=_strategy_bootstrap, daemon=True, name="strategy-boot").start()
    threading.Thread(target=_learning_bootstrap, daemon=True, name="learning-boot").start()
    try:  # phông chữ cho video bản tin (tải 1 lần)
        from agents import newscast
        threading.Thread(target=newscast.ensure_fonts, daemon=True).start()
    except Exception:
        pass

    # Second Brain: ghi chú "superHuy hiểu về anh" trong Obsidian (hai chiều) + dựng sẵn chỉ mục tri thức
    try:
        from core import kb, memory
        memory.export_to_vault()
        threading.Thread(target=kb.refresh, kwargs={"force": True}, daemon=True).start()
    except Exception:
        log.exception("Không khởi tạo được Second Brain")

    # tên hiển thị của bot: superHuy (chỉ đổi khi khác, Telegram giới hạn số lần đổi)
    try:
        if (await app.bot.get_my_name()).name != "superHuy":
            await app.bot.set_my_name("superHuy")
            await app.bot.set_my_short_description("Siêu trợ lý cá nhân của anh Huy")
    except Exception:
        log.exception("Không đổi được tên bot")

    # người khác mở bot: không thấy nút app, không thấy danh sách lệnh
    try:
        await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
        await app.bot.delete_my_commands(scope=BotCommandScopeDefault())
        await app.bot.set_my_commands([BotCommand("app", "Mở bảng điều khiển"), BotCommand("lich", "Lịch ngày mai"),
                                       BotCommand("email", "Tóm tắt email 3 giờ qua"), BotCommand("tin", "Top 5 tin hot"),
                                       BotCommand("qc", "Kiểm tra tình trạng hệ thống"),
                                       BotCommand("khoa", "Khóa bot và Mini App ngay")],
                                      scope=BotCommandScopeChat(OWNER_CHAT_ID))
    except Exception:
        log.exception("Không đặt được menu/lệnh")

    # Mini App: server nội bộ + đường hầm HTTPS + nút menu
    webapp_server.EXTRA_BOOTSTRAP = bootstrap_extra
    try:
        webapp_server.serve(WEBAPP_PORT)
    except OSError:
        log.exception("Không mở được cổng %s cho Mini App", WEBAPP_PORT)

    async def _set_menu(url: str):
        app.bot_data["webapp_url"] = url
        await app.bot.set_chat_menu_button(chat_id=OWNER_CHAT_ID,
                                           menu_button=MenuButtonWebApp(text="Mở app", web_app=WebAppInfo(url=url)))
        log.info("Đã gắn nút menu Mini App")
        last = DATA_FILE_MENU.read_text().strip() if DATA_FILE_MENU.exists() else ""
        if url != last:  # địa chỉ mới: gửi nút mở app mới (Telegram máy tính có thể nhớ địa chỉ cũ)
            DATA_FILE_MENU.write_text(url)
            await app.bot.send_message(chat_id=OWNER_CHAT_ID, text="📱 Mini App đã cập nhật. Bấm nút dưới để mở:",
                                       reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📱 Mở app", web_app=WebAppInfo(url=url))]]))

    def _pair():
        from agents import gcal_bridge
        msg = gcal_bridge.auto_pair()
        if msg:
            notify.send(text=msg)
    loop.run_in_executor(None, _pair)

    tunnel = Tunnel(WEBAPP_PORT, lambda url: asyncio.run_coroutine_threadsafe(_set_menu(url), loop).result(timeout=60))
    tunnel.start()
    app.bot_data["tunnel"] = tunnel
    await send(app, "✅ Đội quân agents đã khởi động. Bấm \"Mở app\" cạnh ô chat để mở bảng điều khiển.")


async def on_audio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Anh gửi file ghi âm / voice / video họp vào bot -> Meeting Studio chép lời và làm biên bản."""
    from agents import meeting
    msg = update.message
    obj = msg.voice or msg.audio or msg.video or msg.video_note or msg.document
    if msg.document and not ((msg.document.mime_type or "").startswith(("audio/", "video/"))
                             or re.search(r"\.(m4a|mp3|wav|aac|ogg|opus|webm|mp4|mov|flac|amr)$", msg.document.file_name or "", re.I)):
        return
    size = getattr(obj, "file_size", 0) or 0
    if size > 20 * 1024 * 1024:
        await msg.reply_text("File lớn hơn 20 MB nên Telegram không cho bot tải. Anh mở app › Họp › Tải file để gửi file lớn nhé.")
        return
    name = getattr(obj, "file_name", None) or ("voice.ogg" if msg.voice else "video.mp4" if (msg.video or msg.video_note) else "audio.m4a")
    meeting.INBOX.mkdir(parents=True, exist_ok=True)
    path = meeting.INBOX / f"tg-{msg.message_id}-{re.sub(r'[^A-Za-z0-9._-]', '_', name)}"
    f = await obj.get_file()
    await f.download_to_drive(str(path))
    m = await asyncio.to_thread(meeting.create, str(path), "Telegram", "", msg.caption or "",
                                msg.date.astimezone().replace(tzinfo=None).isoformat(timespec="seconds"))
    await msg.reply_text("🎙 Đã nhận âm thanh. superHuy đang chép lời và làm biên bản, xong em gửi tóm tắt vào đây. "
                         "Anh có thể ghi chú bối cảnh (vd: họp Leversphere, dự án X) ở phần chú thích khi gửi file.")


def main():
    require_config()
    if (DATA_DIR / "DISABLED").exists():
        # Bot đã chuyển sang máy chủ khác (VPS): máy này đứng yên, không nhận tin Telegram để tránh tranh nhau.
        # Bật lại: xoá file data/DISABLED rồi khởi động lại.
        import time
        log.warning("Bot đang TẮT trên máy này (có file data/DISABLED). Đứng chờ, không kết nối Telegram.")
        while (DATA_DIR / "DISABLED").exists():
            time.sleep(60)
        log.info("Đã xoá data/DISABLED, khởi động bot.")
    asyncio.set_event_loop(asyncio.new_event_loop())  # Python 3.14 không tự tạo event loop
    app = Application.builder().token(TELEGRAM_TOKEN).post_init(post_init).build()
    bot_guard.install(app, replay=answer_text)  # PHẢI gắn trước các handler khác
    app.add_handler(CommandHandler("start", cmd_start, filters=OWNER_ONLY))
    app.add_handler(CommandHandler("app", cmd_app, filters=OWNER_ONLY))
    app.add_handler(CommandHandler("qc", cmd_qc, filters=OWNER_ONLY))
    app.add_handler(CommandHandler("lich", cmd_lich, filters=OWNER_ONLY))
    app.add_handler(CommandHandler("email", cmd_email, filters=OWNER_ONLY))
    news_bot.register(app, OWNER_ONLY)

    async def on_error(update, ctx: ContextTypes.DEFAULT_TYPE):
        # lỗi mạng tạm thời (máy ngủ, mất wifi): chỉ ghi 1 dòng, bot tự kết nối lại
        log.warning("Lỗi (bot tự xử lý tiếp): %s", ctx.error)
    app.add_error_handler(on_error)
    app.add_handler(MessageHandler(OWNER_ONLY & (filters.VOICE | filters.AUDIO | filters.VIDEO | filters.VIDEO_NOTE | filters.Document.ALL), on_audio))
    app.add_handler(MessageHandler(OWNER_ONLY & filters.TEXT & ~filters.COMMAND, on_text))
    log.info("Đang chạy. Nhấn Ctrl+C để dừng.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
