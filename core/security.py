"""Khóa bảo mật dùng chung cho Mini App và super bot.
- Mã PIN chỉ lưu dạng băm PBKDF2 (APP_PIN_HASH trong .env), không bao giờ lưu mã gốc.
- Sai quá 5 lần: khóa 15 phút và báo động qua Telegram.
- Bot Telegram tự khóa lại sau BOT_LOCK_MINUTES phút không dùng (mặc định 30)."""
import hashlib
import hmac
import json
import os
import secrets
import threading
import time

from config import DATA_DIR

STATE_FILE = DATA_DIR / "security.json"
MAX_FAILS = 5
LOCKOUT_SEC = 15 * 60
_lock = threading.Lock()


def _load() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _save(d: dict):
    STATE_FILE.write_text(json.dumps(d))
    try:
        os.chmod(STATE_FILE, 0o600)
    except Exception:
        pass


def hash_pin(pin: str, salt: str | None = None, rounds: int = 240_000) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), rounds).hex()
    return f"pbkdf2:{rounds}:{salt}:{dk}"


def pin_enabled() -> bool:
    return os.getenv("APP_PIN_HASH", "").startswith("pbkdf2:")


def pin_length() -> int:
    try:
        return int(os.getenv("APP_PIN_LEN", "6"))
    except ValueError:
        return 6


def _match(pin: str) -> bool:
    try:
        _, rounds, salt, dk = os.getenv("APP_PIN_HASH", "").split(":")
        return hmac.compare_digest(hash_pin(pin, salt, int(rounds)).split(":")[3], dk)
    except Exception:
        return False


def locked_out() -> int:
    """Số giây còn bị khóa do nhập sai nhiều lần (0 = không bị khóa)."""
    return max(0, int(_load().get("lockout_until", 0) - time.time()))


def verify(pin: str, source: str) -> tuple[bool, str]:
    """Kiểm tra PIN. Trả về (đúng?, thông báo). Ghi nhận số lần sai, khóa tạm và báo động."""
    with _lock:
        st = _load()
        wait = int(st.get("lockout_until", 0) - time.time())
        if wait > 0:
            return False, f"Tạm khóa do nhập sai nhiều lần. Thử lại sau {wait // 60 + 1} phút."
        if _match(pin or ""):
            st["fails"] = 0
            st["last_ok"] = time.time()
            _save(st)
            return True, "ok"
        st["fails"] = int(st.get("fails", 0)) + 1
        left = MAX_FAILS - st["fails"]
        alert = None
        if left <= 0:
            st["fails"] = 0
            st["lockout_until"] = time.time() + LOCKOUT_SEC
            alert = (f"🚨 Cảnh báo bảo mật: nhập sai mã PIN {MAX_FAILS} lần liên tiếp ({source}). "
                     f"Đã khóa 15 phút. Nếu không phải bạn, hãy đổi mã PIN và kiểm tra tài khoản Telegram.")
            msg = "Sai mã PIN quá nhiều lần. Đã khóa 15 phút."
        else:
            msg = f"Sai mã PIN. Còn {left} lần thử."
        _save(st)
    if alert:
        _notify(alert)
    return False, msg


def set_pin(new_pin: str):
    from core.envfile import set_env
    if not (new_pin.isdigit() and 4 <= len(new_pin) <= 8):
        raise ValueError("Mã PIN gồm 4 đến 8 chữ số.")
    set_env("APP_PIN_HASH", hash_pin(new_pin))
    set_env("APP_PIN_LEN", str(len(new_pin)))


# ---------------------------------------------------------------- khóa super bot
def bot_lock_minutes() -> int:
    try:
        return int(os.getenv("BOT_LOCK_MINUTES", "30"))
    except ValueError:
        return 30


def bot_unlocked() -> bool:
    if not pin_enabled():
        return True
    return _load().get("bot_until", 0) > time.time()


def unlock_bot():
    with _lock:
        st = _load()
        st["bot_until"] = time.time() + bot_lock_minutes() * 60
        _save(st)


def touch_bot():
    """Gia hạn khi chủ nhân đang dùng (khóa sau N phút KHÔNG dùng)."""
    with _lock:
        st = _load()
        if st.get("bot_until", 0) > time.time():
            st["bot_until"] = time.time() + bot_lock_minutes() * 60
            _save(st)


def lock_bot():
    with _lock:
        st = _load()
        st["bot_until"] = 0
        _save(st)


# ---------------------------------------------------------------- báo động
_last_alert: dict[str, float] = {}


def alert_once(key: str, text: str, every: int = 3600):
    """Báo động qua Telegram, tối đa 1 lần/giờ cho mỗi key (tránh bị spam)."""
    if time.time() - _last_alert.get(key, 0) < every:
        return
    _last_alert[key] = time.time()
    _notify(text)


def _notify(text: str):
    try:
        from core import notify
        threading.Thread(target=lambda: notify.send(text=text), daemon=True).start()
    except Exception:
        pass
