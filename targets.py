"""Danh bạ nơi đăng (trang cá nhân, group, page). Sửa targets.json để thêm/bớt nơi đăng.
- type: profile | group | page | other
- default_for: loại nội dung được tick sẵn: post (bài viết), bantin (ảnh bản tin), video
- fb_page: tên page khớp với FB_PAGES trong .env -> đăng tự động qua API. Không có thì bot gửi gói nội dung để bạn tự đăng."""
import json

from agents import publisher
from config import BASE_DIR

FILE = BASE_DIR / "targets.json"
ICON = {"profile": "👤", "group": "👥", "page": "📄", "other": "🔗"}


def load() -> list[dict]:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def get(tid: str) -> dict | None:
    return next((t for t in load() if t["id"] == tid), None)


def defaults(kind: str) -> list[str]:
    return [t["id"] for t in load() if kind in t.get("default_for", [])]


def api_page(t: dict) -> dict | None:
    """Trả về cấu hình page (id, token) nếu nơi đăng này có thể đăng tự động."""
    want = (t.get("fb_page") or "").lower()
    if t.get("type") != "page" or not want:
        return None
    return next((p for p in publisher.pages() if p["name"].lower() == want), None)


def label(t: dict) -> str:
    return f"{ICON.get(t.get('type'), '🔗')} {t['name']}"


def describe() -> str:
    lines = ["🎯 NƠI ĐĂNG ĐÃ KHAI BÁO\n"]
    for t in load():
        mode = "đăng tự động" if api_page(t) else "gửi gói để bạn bấm đăng"
        lines.append(f"{label(t)} ({mode})\n   {t.get('url', '')}")
    lines.append("\nSửa danh sách trong file targets.json. Page muốn đăng tự động cần token trong .env (FB_PAGES).")
    return "\n".join(lines)
