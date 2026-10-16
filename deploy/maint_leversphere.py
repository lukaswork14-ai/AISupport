"""Một lần: cập nhật mục tiêu Leversphere (AI-native POD company) trong trí nhớ và viết lại tài liệu sống theo mục tiêu mới."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR  # noqa: E402
from core import memory  # noqa: E402
from agents import strategy  # noqa: E402

FLAG = DATA_DIR / "strategy" / ".leversphere_ai_native"
if FLAG.exists():
    print("đã chạy"); sys.exit()
NEW = ("Leversphere là công ty POD (print on demand); anh Huy là CGO kiêm CAO, mục tiêu biến Leversphere thành AI-native POD company: "
       "ứng dụng AI tối đa để tăng năng suất, tăng doanh thu, cắt chi phí và công sức không cần thiết.")
n = 0
for f in memory.facts():
    if "Leversphere" in f["text"] and ("agentic e-commerce" in f["text"] or "chuyển Leversphere" in f["text"]):
        memory.update(f["id"], NEW)
        n += 1
if not n:
    memory.add(NEW, "work", "anh")
FLAG.parent.mkdir(parents=True, exist_ok=True)
FLAG.write_text("ok")
r = strategy.build("leversphere")
print("memory_updated", n, "|", r.get("text"))
