"""Trình hướng dẫn cài đặt: hỏi từng thông tin một và tự ghi file .env.

Chạy:  python setup.py
Khóa nhập vào chỉ lưu trong file .env trên máy bạn.
"""
import getpass
import time
from pathlib import Path

import requests

ENV_FILE = Path(__file__).resolve().parent / ".env"


def ask(prompt: str, secret: bool = False, default: str = "") -> str:
    value = (getpass.getpass(prompt + ": ") if secret else input(prompt + ": ")).strip()
    return value or default


def detect_chat_id(token: str) -> int | None:
    print("\nBây giờ hãy mở Telegram, tìm bot vừa tạo và nhắn cho nó chữ 'hi'.")
    print("Mình sẽ tự nhận ra chat ID của bạn (chờ tối đa 2 phút)...")
    deadline = time.time() + 120
    offset = None
    while time.time() < deadline:
        r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates",
                         params={"timeout": 10, "offset": offset}, timeout=30)
        data = r.json()
        if not data.get("ok"):
            print("Token không hợp lệ:", data.get("description"))
            return None
        for upd in data["result"]:
            offset = upd["update_id"] + 1
            msg = upd.get("message")
            if msg:
                chat = msg["chat"]
                print(f"Đã nhận tin từ: {chat.get('first_name', '')} (chat ID {chat['id']})")
                if input("Đúng là bạn chứ? (y/n): ").strip().lower().startswith("y"):
                    return chat["id"]
    return None


def check_token(token: str):
    """Trả về username bot nếu token hợp lệ, ngược lại None."""
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=20)
        data = r.json()
        return data["result"]["username"] if data.get("ok") else None
    except Exception as e:
        print("Không kết nối được Telegram:", e)
        return None


def main():
    print("=== CÀI ĐẶT ĐỘI QUÂN AGENTS ===\n")
    print("1) Mở Telegram, nhắn @BotFather lệnh /newbot, đặt tên và username (kết thúc bằng 'bot').")
    print("   Token có dạng 123456789:AAxxxxxxxx (có dấu hai chấm ở giữa, không có khoảng trắng).")
    while True:
        token = ask("Dán TOKEN BotFather trả về (ký tự sẽ bị ẩn)", secret=True).replace(" ", "")
        username = check_token(token)
        if username:
            print(f"Token hợp lệ. Bot của bạn là @{username}")
            break
        print("Token chưa đúng, hãy copy lại toàn bộ dòng token từ BotFather và dán lại.\n")
    chat_id = detect_chat_id(token)
    while not chat_id:
        raw = ask("Không tự nhận được. Nhập chat ID thủ công (nhắn @userinfobot để lấy; chỉ gồm chữ số)")
        if raw.lstrip("-").isdigit():
            chat_id = int(raw)

    print("\n2) Dùng khóa OpenRouter (https://openrouter.ai/keys). Nên đặt hạn mức credit/chi tiêu cho khóa.")
    api_key = ask("Dán khóa OpenRouter (bắt đầu bằng sk-or-)", secret=True)

    print("\n3) (Tùy chọn) Link ICS của Lark / Apple Calendar. Nhiều link thì ngăn cách bằng dấu phẩy.")
    ics = ask("Dán link ICS (Enter để bỏ qua)", default="")

    ENV_FILE.write_text(
        f"TELEGRAM_TOKEN={token}\nOWNER_CHAT_ID={chat_id}\nLLM_API_KEY={api_key}\nLLM_BASE_URL=https://openrouter.ai/api/v1\nLLM_MODEL=~deepseek/deepseek-v4-flash-latest\n"
        f"TIMEZONE=Asia/Ho_Chi_Minh\nICS_URLS={ics}\n"
        f"REMINDER_HOUR=21\nEMAIL_DIGEST_EVERY_HOURS=1\n"
    )
    try:
        ENV_FILE.chmod(0o600)
    except Exception:
        pass
    print("\nĐã lưu cấu hình vào .env.")


if __name__ == "__main__":
    main()
