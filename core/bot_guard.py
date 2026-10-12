"""Lớp bảo vệ super bot Telegram (chạy TRƯỚC mọi handler khác):
1. Chỉ chủ nhân, trong chat riêng, mới được bot phản hồi. Người lạ: im lặng + báo động cho chủ nhân.
2. Bot bị thêm vào group: tự rời group ngay.
3. Khóa bằng mã PIN: bàn phím số dạng nút bấm (mã không nằm lại trong lịch sử chat).
   Tự khóa lại sau BOT_LOCK_MINUTES phút không dùng. Lệnh /khoa để khóa ngay."""
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatType
from telegram.ext import (ApplicationHandlerStop, CallbackQueryHandler, CommandHandler, ContextTypes, TypeHandler)

from config import OWNER_CHAT_ID
from core import security

log = logging.getLogger("guard")
_replay = None  # hàm xử lý lại tin nhắn đang chờ sau khi mở khóa: async fn(ctx, text)


def _keypad() -> InlineKeyboardMarkup:
    b = lambda t, d: InlineKeyboardButton(t, callback_data=f"pin:{d}")
    rows = [[b(str(n), n) for n in r] for r in ((1, 2, 3), (4, 5, 6), (7, 8, 9))]
    rows.append([b("⌫", "del"), b("0", 0), b("✕", "x")])
    return InlineKeyboardMarkup(rows)


def _text(n: int, note: str = "") -> str:
    L = security.pin_length()
    dots = " ".join("●" if i < n else "○" for i in range(L))
    return f"🔒 SuperHuy đang khóa\nNhập mã PIN để mở khóa\n\n{dots}" + (f"\n\n{note}" if note else "")


async def _show_keypad(ctx: ContextTypes.DEFAULT_TYPE, note: str = ""):
    ctx.bot_data["pin_buf"] = ""
    old = ctx.bot_data.get("pin_msg")
    if old:
        try:
            await ctx.bot.delete_message(OWNER_CHAT_ID, old)
        except Exception:
            pass
    m = await ctx.bot.send_message(OWNER_CHAT_ID, _text(0, note), reply_markup=_keypad())
    ctx.bot_data["pin_msg"] = m.message_id


def _describe(user) -> str:
    name = " ".join(x for x in (user.first_name, user.last_name) if x) or "(không tên)"
    return name + (f" @{user.username}" if user.username else "") + f", ID {user.id}"


async def guard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user = update.effective_chat, update.effective_user

    # bot bị thêm vào group/kênh: rời ngay
    if update.my_chat_member:
        if chat and chat.type != ChatType.PRIVATE and update.my_chat_member.new_chat_member.status in ("member", "administrator"):
            try:
                await ctx.bot.leave_chat(chat.id)
            except Exception:
                pass
            security.alert_once(f"grp:{chat.id}", f"🚨 Có người ({_describe(user) if user else '?'}) thêm super bot vào "
                                f"nhóm “{chat.title}”. Bot đã tự rời nhóm.")
        raise ApplicationHandlerStop

    if not user or not OWNER_CHAT_ID or user.id != OWNER_CHAT_ID or (chat and chat.type != ChatType.PRIVATE):
        if user and not user.is_bot:
            txt = (update.effective_message.text or "")[:80] if update.effective_message else ""
            security.alert_once(f"bot:{user.id}", f"🚨 Người lạ ({_describe(user)}) vừa nhắn super bot"
                                + (f": “{txt}”" if txt else "") + ". Đã chặn, bot không phản hồi.")
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass
        raise ApplicationHandlerStop

    cq = update.callback_query
    if cq and (cq.data or "").startswith("pin:"):
        return  # để handler bàn phím xử lý
    if security.bot_unlocked():
        security.touch_bot()
        return
    msg = update.effective_message
    if msg and msg.text and not msg.text.startswith("/"):
        ctx.bot_data["pending_text"] = msg.text
    if cq:
        try:
            await cq.answer("🔒 Nhập mã PIN trước.")
        except Exception:
            pass
    await _show_keypad(ctx, "Tin nhắn của bạn sẽ được xử lý ngay sau khi mở khóa." if ctx.bot_data.get("pending_text") else "")
    raise ApplicationHandlerStop


async def on_pin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    key = q.data.split(":", 1)[1]
    buf = ctx.bot_data.get("pin_buf", "")
    if key == "x":
        ctx.bot_data["pin_buf"] = ""
        ctx.bot_data.pop("pending_text", None)
        await q.answer("Đã hủy")
        try:
            await q.message.delete()
        except Exception:
            pass
        return
    if security.bot_unlocked():
        await q.answer("Bot đang mở khóa")
        try:
            await q.message.delete()
        except Exception:
            pass
        return
    buf = buf[:-1] if key == "del" else (buf + key)[:security.pin_length()]
    ctx.bot_data["pin_buf"] = buf
    if len(buf) < security.pin_length():
        await q.answer()
        try:
            await q.edit_message_text(_text(len(buf)), reply_markup=_keypad())
        except Exception:
            pass
        return
    ok, note = security.verify(buf, "Telegram bot")
    ctx.bot_data["pin_buf"] = ""
    if not ok:
        await q.answer(note, show_alert=False)
        try:
            await q.edit_message_text(_text(0, "⚠️ " + note), reply_markup=_keypad())
        except Exception:
            pass
        return
    security.unlock_bot()
    await q.answer("Đã mở khóa")
    try:
        await q.edit_message_text(f"🔓 Đã mở khóa. Bot tự khóa lại sau {security.bot_lock_minutes()} phút không dùng (/khoa để khóa ngay).")
    except Exception:
        pass
    ctx.bot_data.pop("pin_msg", None)
    pending = ctx.bot_data.pop("pending_text", None)
    if pending and _replay:
        await _replay(ctx, pending)


async def cmd_khoa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    security.lock_bot()
    try:
        from webapp import server
        server.end_all_sessions()
    except Exception:
        pass
    await update.message.reply_text("🔒 Đã khóa super bot và đăng xuất Mini App. Nhắn bất kỳ để mở khóa bằng mã PIN.")


def install(app, replay=None):
    """Gắn lớp bảo vệ vào bot. replay: async fn(ctx, text) xử lý tin nhắn bị giữ lại khi đang khóa."""
    global _replay
    _replay = replay
    app.add_handler(TypeHandler(Update, guard), group=-1)
    app.add_handler(CallbackQueryHandler(on_pin, pattern=r"^pin:"), group=0)
    app.add_handler(CommandHandler("khoa", cmd_khoa), group=0)
