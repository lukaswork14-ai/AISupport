"""Lưu bản tóm tắt email / Lark gần nhất để Mini App hiển thị mục "Cần bạn xử lý"."""
import datetime as dt
import json

from config import DATA_DIR

FILE = DATA_DIR / "digests.json"


def save(kind: str, text: str | None):
    if not text or text.startswith("⚠️") or text.startswith("Chưa kết nối") or text.startswith("Không có"):
        return
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d[kind] = {"text": text, "at": dt.datetime.now().isoformat(timespec="minutes")}
    FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
