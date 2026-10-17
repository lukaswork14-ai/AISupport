"""Chạy qua diag (idempotent): ghi quyết định của anh (duyệt tất cả, chat 17/10 09:11) vào bảng Phòng ban và cập nhật tiến độ."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents import board  # noqa: E402

NOTE = "Anh duyệt trong chat 17/10 09:11 (riêng thông tin thanh toán anh làm sau)."
RESULT = {
    "seed:cso": ("xong", "Phòng Bán hàng (CSO ảo) đã chạy: HQ › Bán hàng CSO. Chấm điểm ICP, soạn thư theo đuổi chờ anh duyệt (07:45 mỗi sáng), phễu RevOps, kế hoạch tuần lên bảng thứ Hai."),
    "seed:ops": ("xong", "Phòng Vận hành (AI) đã chạy: HQ › Vận hành. Tenant, QC, ổ đĩa, chi phí/khách (23:40 mỗi tối), ngưỡng cảnh báo, báo cáo tuần thứ Hai 06:55."),
    "seed:packs": ("xong", "3 gói Phòng ban AI đã lên kệ (loại mới 'pack' = skill + workflow + tri thức): Finance OS cho chủ shop 299k, Sales Desk cho solopreneur 299k, Law Office 999k."),
    "seed:private": ("xong", "superYou Private: core/private_llm.py, chế độ off/hybrid/strict, cấu hình LOCAL_LLM_BASE_URL/LOCAL_LLM_MODEL/PRIVATE_MODE trong .env tenant; đổi trong HQ › Vận hành › AI tại chỗ. Chờ GTM định giá gói Private."),
    "seed:content": ("xong", "Studio có công thức 'Phòng ban AI (founder-led, 60–90s)' trong Công thức kênh; chọn khi dựng video. GTM lên lịch 2 video/tuần."),
    "seed:cfo": ("dang_lam", "Finance OS sẵn sàng; chờ anh ghi tiền mặt và chi phí cố định trong HQ › Tài chính CFO (hoặc nhắn superHuy 'ghi tiền mặt ...')."),
}
d = board._load()
n = 0
for x in list(d["items"].values()):
    k = x.get("key", "")
    if k in RESULT and x["status"] == "cho_duyet":
        board.decide(x["id"], "duyet", NOTE, 7)
        n += 1
    if k in RESULT and board._load()["items"][x["id"]]["status"] in ("da_duyet", "dang_lam"):
        st, res = RESULT[k]
        cur = board._load()["items"][x["id"]]
        if cur["status"] != st or cur.get("result") != res:
            board.progress(x["id"], st, res, "Phòng Product")
            n += 1
print(f"board_decide: {n} cập nhật; {board.overview()['counts']}")
