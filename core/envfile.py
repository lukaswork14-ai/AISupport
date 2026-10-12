"""Ghi/sửa một khóa trong .env và cập nhật ngay cho tiến trình đang chạy (không cần khởi động lại)."""
import os

from config import BASE_DIR

ENV = BASE_DIR / ".env"


def set_env(key: str, value: str):
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lines = [l for l in lines if not l.startswith(key + "=")]
    lines.append(f"{key}={value}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(ENV, 0o600)
    os.environ[key] = value


def get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()
