"""Giao diện Telegram cho Agent 3: bản tin Top 5, nút viết content, duyệt/viết lại/bỏ."""
import asyncio
import datetime as dt
import json
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from agents import content_agent, imagecard, news_agent, publisher, reel_video, second_brain
from config import CARD_HANDLE, DATA_DIR, OWNER_CHAT_ID
from core import store

log = logging.getLogger("news-bot")
DRAFTS_FILE = DATA_DIR / "drafts.json"


# ---------------------------------------------------------------- tiện ích
def _drafts() -> dict:
    try:
        return json.loads(DRAFTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_draft(n: int, item: dict, content: dict, image: str):
    d = _drafts()
    d[str(n)] = {"item": item, "content": content, "image": image}
    DRAFTS_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


async def _say(bot, text: str, **kw):
    for i in range(0, len(text), 4000):
        await bot.send_message(chat_id=OWNER_CHAT_ID, text=text[i:i + 4000],
                               disable_web_page_preview=True, **kw if i + 4000 >= len(text) else {})


def _is_owner(update: Update) -> bool:
    u = update.effective_user
    return bool(u and u.id == OWNER_CHAT_ID)


# ------------------------------------------------------------- bản tin Top 5
async def send_digest(bot, force: bool = True):
    await bot.send_chat_action(chat_id=OWNER_CHAT_ID, action=ChatAction.TYPING)
    try:
        result = await asyncio.to_thread(news_agent.get_today, force)
    except Exception as e:
        log.exception("Lỗi quét tin")
        await _say(bot, f"⚠️ Không quét được tin: {e}")
        return
    n = len(result["items"])
    buttons = [InlineKeyboardButton(f"✍️ Tin {i}", callback_data=f"w:{i}") for i in range(1, n + 1)]
    saves = [InlineKeyboardButton(f"📥 Lưu {i}", callback_data=f"s:{i}") for i in range(1, n + 1)]
    markup = InlineKeyboardMarkup([buttons, saves, [InlineKeyboardButton("📰 Bản tin sáng", callback_data="bt"),
                                                    InlineKeyboardButton("🎬 Video bản tin", callback_data="vd"),
                                                    InlineKeyboardButton("🔄 Quét lại", callback_data="scan")]]) if n else None
    await _say(bot, news_agent.format_digest(result) + "\n\n📥 Lưu = đưa vào Obsidian. 📰 = ảnh + caption bản tin sáng.", reply_markup=markup)


async def job_news(app: Application):
    log.info("Chạy săn tin hằng ngày")
    await send_digest(app.bot, force=True)


# ------------------------------------------------------- sản xuất content
def _review_markup(n: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Duyệt", callback_data=f"ok:{n}"),
        InlineKeyboardButton("🔁 Viết lại", callback_data=f"re:{n}"),
        InlineKeyboardButton("🗑 Bỏ", callback_data=f"no:{n}"),
    ]])


async def produce(bot, n: int, angle: str = ""):
    items = news_agent.load_today()
    if not 1 <= n <= len(items):
        await _say(bot, "Chưa có tin số đó. Gõ /tin để quét tin trước.")
        return
    item = items[n - 1]
    await bot.send_chat_action(chat_id=OWNER_CHAT_ID, action=ChatAction.TYPING)
    await _say(bot, f"✍️ Đang viết content cho tin {n}: {item['headline_vi']}")
    try:
        content = await asyncio.to_thread(content_agent.make_content, item, angle)
        image = await asyncio.to_thread(imagecard.make_card, content["card"], item["source"],
                                        item["topic"], f"tin{n}", CARD_HANDLE)
    except Exception as e:
        log.exception("Lỗi viết content")
        await _say(bot, f"⚠️ Không viết được content: {e}")
        return
    _save_draft(n, item, content, image)
    cid = store.add("post", item["headline_vi"], content_agent.format_post(item, content), image=image,
                    meta={"n": n, "reel": content_agent.format_reel(content), "reel_data": content.get("reel", {}),
                          "topic": item.get("topic", ""), "source": item.get("source", ""),
                          "image_prompt": content.get("image_prompt", "")})
    with open(image, "rb") as f:
        await bot.send_photo(chat_id=OWNER_CHAT_ID, photo=f, caption=f"🖼 Ảnh minh họa cho tin {n}")
    await _say(bot, "📝 BÀI ĐĂNG\n\n" + content_agent.format_post(item, content))
    await _say(bot, content_agent.format_reel(content), reply_markup=InlineKeyboardMarkup(
        _review_markup(n).inline_keyboard + ((InlineKeyboardButton("🎬 Dựng video reels", callback_data=f"rv:{cid}"),),)))
    if content.get("image_prompt"):
        await _say(bot, f"🎨 Prompt ảnh AI (tùy chọn): {content['image_prompt']}")


# ------------------------------------------------------------ bản tin sáng
def bantin_caption(items: list[dict]) -> str:
    import hub
    return hub.bantin_caption(items)


async def make_bantin(bot):
    items = news_agent.load_today()
    if not items:
        await _say(bot, "Chưa có tin hôm nay. Gõ /tin trước.")
        return
    date_str = dt.date.today().strftime("%d.%m.%Y")
    img = await asyncio.to_thread(imagecard.make_digest_card, items, date_str, "bantin", CARD_HANDLE)
    with open(img, "rb") as f:
        await bot.send_photo(chat_id=OWNER_CHAT_ID, photo=f, caption="📰 Ảnh Bản tin sáng")
    cap = bantin_caption(items)
    _set_last("bantin", {"image": img, "caption": cap})
    store.add("bantin", f"Bản tin sáng {dt.date.today():%d/%m}", cap, image=img)
    await _say(bot, "📝 CAPTION\n\n" + cap, reply_markup=_publish_markup("bantin"))


async def save_news_item(bot, n: int):
    items = news_agent.load_today()
    if not 1 <= n <= len(items):
        await _say(bot, "Chưa có tin số đó. Gõ /tin trước.")
        return
    path = await asyncio.to_thread(second_brain.save_news, items[n - 1])
    await _say(bot, f"📥 Đã lưu tin {n} vào Obsidian: {path.replace(str(second_brain.OBSIDIAN_VAULT), '')}")


# ------------------------------------------------------- video + đăng bài
LAST_FILE = DATA_DIR / "last_outputs.json"


def _get_last(key):
    try:
        return json.loads(LAST_FILE.read_text(encoding="utf-8")).get(key)
    except Exception:
        return None


def _set_last(key, val):
    try:
        d = json.loads(LAST_FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d[key] = val
    LAST_FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def _publish_markup(key: str):
    rows = [[InlineKeyboardButton(f"📤 Đăng lên {p['name']}", callback_data=f"pb:{key}:{i}")]
            for i, p in enumerate(publisher.pages())]
    rows.append([InlineKeyboardButton("📋 Gói nội dung để tự đăng (group, cá nhân...)", callback_data=f"pk:{key}")])
    return InlineKeyboardMarkup(rows)


async def make_video(bot):
    items = news_agent.load_today()
    if not items:
        await _say(bot, "Chưa có tin hôm nay. Gõ /tin trước.")
        return
    await _say(bot, "🎬 Đang dựng video bản tin (khoảng 1-2 phút)...")
    await bot.send_chat_action(chat_id=OWNER_CHAT_ID, action=ChatAction.UPLOAD_VIDEO)
    try:
        path, engine = await asyncio.to_thread(reel_video.make_bantin_video, items, CARD_HANDLE)
    except Exception as e:
        log.exception("Lỗi dựng video")
        await _say(bot, f"⚠️ Không dựng được video: {e}")
        return
    cap = bantin_caption(items) + "\n\nGiọng đọc được tạo bằng AI."
    _set_last("video", {"video": path, "caption": cap})
    store.add("video", f"Video bản tin {dt.date.today():%d/%m}", cap, video=path, meta={"voice_engine": engine})
    note = "" if engine == "edge-tts" else f" (giọng dự phòng: {engine})"
    with open(path, "rb") as f:
        await bot.send_video(chat_id=OWNER_CHAT_ID, video=f, caption=f"🎬 Video bản tin{note}",
                             supports_streaming=True, read_timeout=300, write_timeout=300)
    await _say(bot, "📝 CAPTION VIDEO\n\n" + cap, reply_markup=_publish_markup("video"))


async def send_voice_samples(bot):
    await _say(bot, "🎙 Đang tạo giọng nghe thử...")
    for name in reel_video.VOICES:
        try:
            path = await asyncio.to_thread(reel_video.voice_sample, name)
        except Exception as e:
            await _say(bot, f"⚠️ Không tạo được giọng {name}: {e}")
            continue
        with open(path, "rb") as f:
            await bot.send_audio(chat_id=OWNER_CHAT_ID, audio=f, title=f"Giọng {name}")
    cur = reel_video.get_voice()
    await _say(bot, f"Giọng đang dùng: {cur}. Chọn giọng cho video:", reply_markup=InlineKeyboardMarkup([[
        InlineKeyboardButton(f"Chọn {n}", callback_data=f"gv:{n}") for n in reel_video.VOICES]]))


def _bundle(key: str):
    if key == "bantin":
        d = _get_last("bantin")
        return (d or {}).get("caption"), (d or {}).get("image"), None
    if key == "video":
        d = _get_last("video")
        return (d or {}).get("caption"), None, (d or {}).get("video")
    d = _drafts().get(key)  # số tin của bài đã duyệt
    if not d:
        return None, None, None
    return content_agent.format_post(d["item"], d["content"]), d["image"], None


async def publish(bot, key: str, idx: int):
    text, image, video = _bundle(key)
    pages = publisher.pages()
    if not text or not 0 <= idx < len(pages):
        await _say(bot, "Không tìm thấy nội dung hoặc page. Tạo lại nội dung rồi thử lại.")
        return
    page = pages[idx]
    await _say(bot, f"📤 Đang đăng lên {page['name']}...")
    try:
        if video:
            link = await asyncio.to_thread(publisher.post_video, page, video, text)
        else:
            link = await asyncio.to_thread(publisher.post_photo, page, image, text)
    except Exception as e:
        log.exception("Lỗi đăng bài")
        await _say(bot, f"⚠️ Đăng thất bại: {e}")
        return
    await _say(bot, f"✅ Đã đăng lên {page['name']}: {link}")


async def send_pack(bot, key: str):
    text, image, video = _bundle(key)
    if not text:
        await _say(bot, "Không tìm thấy nội dung. Tạo lại rồi thử lại.")
        return
    targets = publisher.manual_targets()
    where = ("Nơi đăng thủ công: " + ", ".join(targets)) if targets else "Chưa khai báo MANUAL_TARGETS trong .env."
    if image:
        with open(image, "rb") as f:
            await bot.send_document(chat_id=OWNER_CHAT_ID, document=f, caption="Ảnh gốc (tải về để đăng)")
    if video:
        with open(video, "rb") as f:
            await bot.send_document(chat_id=OWNER_CHAT_ID, document=f, caption="Video gốc (tải về để đăng)",
                                    read_timeout=300, write_timeout=300)
    await _say(bot, f"📋 {where}\nNội dung bên dưới, nhấn giữ để copy:")
    await _say(bot, text)


# ------------------------------------------------------------------ handlers
async def cmd_tin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_digest(ctx.bot, force=True)


async def cmd_viet(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args or []
    if not args or not args[0].isdigit():
        await update.message.reply_text("Cú pháp: /viet 2  hoặc  /viet 2 nhấn mạnh cơ hội cho seller POD")
        return
    await produce(ctx.bot, int(args[0]), " ".join(args[1:]))


async def cmd_bantin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await make_bantin(ctx.bot)


async def cmd_luu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    arg = " ".join(ctx.args or []).strip()
    if not arg:
        await update.message.reply_text("Cú pháp: /luu <link bài viết>  hoặc  /luu <đoạn văn bản muốn lưu>")
        return
    await ctx.bot.send_chat_action(chat_id=OWNER_CHAT_ID, action=ChatAction.TYPING)
    try:
        path, title = await asyncio.to_thread(second_brain.save_any, arg)
    except Exception as e:
        log.exception("Lỗi lưu Obsidian")
        await update.message.reply_text(f"⚠️ Không lưu được: {e}")
        return
    await update.message.reply_text(f"📥 Đã lưu vào Obsidian: {title}\n{path.replace(str(second_brain.OBSIDIAN_VAULT), '')}")


async def cmd_video(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await make_video(ctx.bot)


async def cmd_giong(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_voice_samples(ctx.bot)


async def cmd_fbtoken(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    tok = " ".join(ctx.args or []).strip()
    try:  # xóa ngay tin nhắn chứa token khỏi chat
        await update.message.delete()
    except Exception:
        pass
    if not tok:
        await _say(ctx.bot, "Cú pháp: /fbtoken <User Access Token>. Tin nhắn sẽ tự xóa sau khi bot đọc.")
        return
    from agents import fb_connect
    try:
        res = await asyncio.to_thread(fb_connect.connect, tok)
        await _say(ctx.bot, res["text"])
    except Exception as e:
        await _say(ctx.bot, f"⚠️ Kết nối Facebook thất bại: {e}")


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not _is_owner(update):
        await q.answer("Không có quyền.", show_alert=True)
        return
    await q.answer()
    action, _, arg = (q.data or "").partition(":")
    if action == "scan":
        await send_digest(ctx.bot, force=True)
    elif action == "rv":
        import hub
        await _say(ctx.bot, "🎬 Đang dựng video reels cho bài (khoảng 1 phút)...")
        try:
            res = await asyncio.to_thread(hub.video_tu_bai, arg)
            with open(res["video"], "rb") as f:
                await ctx.bot.send_video(chat_id=OWNER_CHAT_ID, video=f, caption="🎬 Video reels",
                                         supports_streaming=True, read_timeout=300, write_timeout=300)
            await _say(ctx.bot, res["text"])
        except Exception as e:
            log.exception("Lỗi dựng video bài")
            await _say(ctx.bot, f"⚠️ Không dựng được video: {e}")
    elif action == "vd":
        await make_video(ctx.bot)
    elif action == "gv":
        reel_video.set_voice(arg)
        await _say(ctx.bot, f"🎙 Đã chọn giọng {arg} cho các video sau.")
    elif action == "pb":
        key, _, idx = arg.partition(":")
        await publish(ctx.bot, key, int(idx))
    elif action == "pk":
        await send_pack(ctx.bot, arg)
    elif action == "bt":
        await make_bantin(ctx.bot)
    elif action == "s":
        await save_news_item(ctx.bot, int(arg))
    elif action in ("w", "re"):
        await produce(ctx.bot, int(arg))
    elif action == "ok":
        d = _drafts().get(arg)
        if not d:
            await _say(ctx.bot, "Bản nháp này đã hết hạn. Gõ /viet " + arg + " để viết lại.")
            return
        path = content_agent.save_approved(d["item"], d["content"], d["image"])
        try:
            await asyncio.to_thread(second_brain.save_draft, d["item"], d["content"])
        except Exception:
            log.exception("Không lưu bản nháp vào Obsidian")
        await _say(ctx.bot, f"✅ Đã duyệt và lưu bộ content tin {arg}.\n"
                            f"Lưu ý: bot CHƯA tự đăng lên mạng xã hội, bạn copy bài/ảnh để đăng. "
                            f"(File: {path})", reply_markup=_publish_markup(arg))
    elif action == "no":
        await _say(ctx.bot, f"🗑 Đã bỏ bản nháp tin {arg}.")


def register(app: Application, owner_filter):
    app.add_handler(CommandHandler("tin", cmd_tin, filters=owner_filter))
    app.add_handler(CommandHandler("viet", cmd_viet, filters=owner_filter))
    app.add_handler(CommandHandler("bantin", cmd_bantin, filters=owner_filter))
    app.add_handler(CommandHandler("luu", cmd_luu, filters=owner_filter))
    app.add_handler(CommandHandler("video", cmd_video, filters=owner_filter))
    app.add_handler(CommandHandler("giong", cmd_giong, filters=owner_filter))
    app.add_handler(CommandHandler("fbtoken", cmd_fbtoken, filters=owner_filter))
    app.add_handler(CallbackQueryHandler(on_button))
