"""Kho nội dung chung (Studio): mọi bài viết, ảnh bản tin, video do bất kỳ agent nào tạo ra đều vào đây,
để Mini App, Telegram và công cụ đăng bài dùng chung một nguồn."""
import datetime as dt
import json
import threading
import uuid

from config import DATA_DIR

FILE = DATA_DIR / "contents.json"
_lock = threading.Lock()
KINDS = {"post": "Bài viết", "bantin": "Ảnh bản tin", "video": "Video", "note": "Ghi chú"}


def _load() -> list[dict]:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(rows):
    FILE.write_text(json.dumps(rows[-300:], ensure_ascii=False, indent=1), encoding="utf-8")


def add(kind: str, title: str, text: str, image: str | None = None, video: str | None = None,
        meta: dict | None = None) -> str:
    cid = uuid.uuid4().hex[:8]
    with _lock:
        rows = _load()
        rows.append({"id": cid, "kind": kind, "title": title, "text": text, "image": image, "video": video,
                     "status": "draft", "created": dt.datetime.now().isoformat(timespec="seconds"),
                     "posts": [], "meta": meta or {}})
        _save(rows)
    return cid


def get(cid: str) -> dict | None:
    return next((r for r in _load() if r["id"] == cid), None)


def update(cid: str, **fields) -> dict | None:
    with _lock:
        rows = _load()
        for r in rows:
            if r["id"] == cid:
                r.update(fields)
                _save(rows)
                return r
    return None


def log_post(cid: str, target_id: str, mode: str, link: str = ""):
    with _lock:
        rows = _load()
        for r in rows:
            if r["id"] == cid:
                r.setdefault("posts", []).append({"target": target_id, "mode": mode, "link": link,
                                                  "at": dt.datetime.now().isoformat(timespec="seconds")})
                if mode == "api":
                    r["status"] = "posted"
                _save(rows)


def recent(limit: int = 40, kind: str | None = None) -> list[dict]:
    rows = [r for r in _load() if not kind or r["kind"] == kind]
    return list(reversed(rows))[:limit]
