"""Cầu nối để mọi công cụ (kể cả chạy trong Mini App) gửi được tin/ảnh/video vào chat Telegram của chủ nhân."""
import logging

log = logging.getLogger("notify")
_sender = None


def set_sender(fn):
    """fn(text=None, photo=None, video=None, document=None, caption=None) -> None (main.py gắn vào)."""
    global _sender
    _sender = fn


def send(**kw):
    if _sender is None:
        return
    try:
        _sender(**kw)
    except Exception:
        log.exception("Không gửi được vào Telegram")
