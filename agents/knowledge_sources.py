"""Danh mục NGUỒN TRI THỨC của Second Brain (mở rộng dần): mỗi nguồn nạp dữ liệu về để superHuy tra cứu khi trả lời.

Thêm nguồn mới: viết 1 module có status() / sync() (ghi .md vào data/knowledge/<id>/ với frontmatter kb_source, kb_label)
rồi khai báo trong SOURCES bên dưới. Chỉ mục core/kb.py tự đọc mọi file trong data/knowledge.
"""
import logging

log = logging.getLogger("knowledge")


def _obsidian() -> dict:
    from core import kb, vault_sync
    st, s = vault_sync.status(), kb.stats()
    return {"id": "obsidian", "name": "Obsidian", "connected": True, "two_way": True, "syncing": False,
            "last_sync": st.get("last_commit", ""), "detail": f"{s['notes']} ghi chú · {s['own']} anh tự viết",
            "sync_enabled": st.get("enabled", False)}


def _gemini() -> dict:
    from agents import gemini_notebook as g
    st = g.status()
    st["detail"] = (f"{st['notebooks']} notebook · {st['sources']} nguồn · {st['notes']} ghi chú" if st["connected"]
                    else "Chưa kết nối")
    return st


# id -> (hàm trạng thái, hàm đồng bộ)
SOURCES = {
    "obsidian": (_obsidian, lambda: __import__("core.vault_sync", fromlist=["sync"]).sync()),
    "gemini": (_gemini, lambda: __import__("agents.gemini_notebook", fromlist=["sync"]).sync()["text"]),
}


def all_status() -> list[dict]:
    out = []
    for sid, (st, _) in SOURCES.items():
        try:
            out.append(st())
        except Exception as e:
            log.exception("Trạng thái nguồn %s lỗi", sid)
            out.append({"id": sid, "name": sid, "connected": False, "detail": f"Lỗi: {e}"})
    return out


def sync(source: str) -> dict:
    if source not in SOURCES:
        raise ValueError("Không có nguồn này")
    return {"text": str(SOURCES[source][1]())}


def sync_all_connected():
    """Lịch định kỳ: đồng bộ các nguồn ngoài Obsidian (Obsidian đã có lịch 10 phút riêng)."""
    from agents import gemini_notebook as g
    if g.connected():
        g.sync()
