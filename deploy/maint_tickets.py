"""Một lần: dọn phiếu nâng cấp trùng và ghi kết quả xử lý từng phiếu (theo tiêu chí ổn định, nhanh, tiết kiệm, an toàn)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agents import repo_radar as r  # noqa: E402
from config import DATA_DIR  # noqa: E402

FLAG = DATA_DIR / "repos" / ".maint_2026_10_16"
if FLAG.exists():
    print("maint: đã chạy trước đó"); sys.exit()
D = {
    "web search": ("xong", "Đã làm: superHuy có công cụ tìm trên web (DuckDuckGo, dự phòng Google News + Wikipedia) và đọc nội dung trang, miễn phí, không cần khoá. Trợ lý tự dùng khi cần thông tin mới và ghi nguồn."),
    "firecrawl vào công cụ săn tin": ("xong", "Đã làm theo cách nhẹ hơn: dùng trafilatura (miễn phí, chạy ngay trên VPS) để lấy đúng phần bài chính khi săn tin và phân tích CAO, thay vì Firecrawl (trả phí hoặc phải tự chạy dịch vụ nặng)."),
    "sandbox tool output": ("xong", "Đã làm: kết quả công cụ dài được rút gọn thông minh (giữ đầu và cuối) trước khi đưa cho mô hình, đỡ tốn token và trả lời nhanh hơn."),
    "ifixai": ("bo", "Không làm: hiện đã có kiểm thử giao diện, kiểm thử video và chẩn đoán VPS tự động; thêm công cụ ngoài làm triển khai chậm hơn mà lợi ích nhỏ."),
    "hyperframes": ("bo", "Không làm lúc này: cần Node + Chromium dựng video, nặng cho VPS 4 GB; pipeline ffmpeg hiện tại đã ổn định và nhanh."),
    "agent reach": ("bo", "Không làm: thu thập Twitter/Reddit dễ bị chặn và rủi ro điều khoản dịch vụ; săn tin hiện dùng nguồn RSS ổn định."),
    "bộ nhớ nén": ("bo", "Không làm: superHuy đã có trí nhớ dài hạn + Second Brain tìm kiếm BM25; theo dõi repo để học thêm khi chín hơn."),
    "plugin marketplace": ("bo", "Không làm: quá lớn so với lợi ích cho 1 người dùng; Reel Studio đã có công thức + skill News Studio."),
    "voicestudio": ("bo", "Không làm: cần GPU; giọng edge-tts miễn phí đang chạy tốt trên VPS."),
    "kho footage": ("bo", "Không làm lúc này: cần kho video bản quyền và tài nguyên dựng lớn."),
    "playwright mcp": ("bo", "Không làm: chạy trình duyệt trên VPS tốn RAM; công cụ đọc web mới đáp ứng phần lớn nhu cầu."),
    "scrapling": ("bo", "Không làm: trùng với công cụ đọc web + trafilatura vừa thêm."),
    "vẽ sơ đồ": ("bo", "Để sau: Mini App đã có sơ đồ tư duy cho biên bản họp; sẽ cân nhắc khi cần sơ đồ trong trò chuyện."),
}
rows = r._read(r.TICKETS, [])
seen = {}
for t in rows:
    key = (t["repo"], t["title"].strip().lower())
    if key in seen:
        r.set_ticket(t["id"], "bo", f"Trùng với phiếu {seen[key]} (bấm áp dụng 2 lần).")
        continue
    seen[key] = t["id"]
    low = t["title"].lower()
    for k, (st, note) in D.items():
        if k in low:
            r.set_ticket(t["id"], st, note)
            break
FLAG.write_text("ok")
print("maint:", [(t["title"][:40], t["status"]) for t in r._read(r.TICKETS, [])])
