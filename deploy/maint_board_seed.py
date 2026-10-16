"""Chạy 1 lần trên VPS: đưa các đề xuất liên phòng ban (từ 7 video anh gửi + rà soát sản phẩm) lên bảng Phòng ban để anh duyệt trong HQ."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agents import board  # noqa: E402

P = [
    ("finance", "Finance OS: nhập tiền mặt, chi phí cố định và bật CFO brief 07:30",
     "CFO ảo đã chạy (Analyst, Forecaster, Strategist, brief). Để có số thật: anh ghi tiền mặt hiện có và các chi phí cố định (VPS, LLM, tên miền, công cụ). "
     "Thứ Hai hằng tuần Strategist tự đưa 3 hành động lên bảng.", "Video 'AI Financial Operating System' và 'Grok finance team' (ReStructure AI): một người, không nhân viên, vẫn có cả phòng tài chính.",
     "Anh thấy tiền mặt, runway và việc nên làm mỗi sáng.", "5 phút nhập liệu.", "", "cao", "finance", "seed:cfo"),
    ("sales", "Phòng Bán hàng (CSO ảo): theo đuổi khách đăng ký tự động",
     "Mô hình 'AI sales department' 7 agent + CSO: với superYou giai đoạn này cần 3 vai: Nghiên cứu (đọc email/website khách, xếp loại ICP), Theo đuổi (soạn email và tin nhắn theo kịch bản, anh duyệt rồi gửi), "
     "RevOps (phễu, tỷ lệ chuyển đổi, báo cáo tuần). Dữ liệu từ mục Khách hàng, dùng trí nhớ chung của superYou.",
     "Video 'AI Sales Department 24/7' (ReStructure AI).", "Không bỏ sót khách; tăng tỷ lệ chuyển từ đăng ký sang dùng thử.", "Khoảng 1 tuần làm.", "GTM: kịch bản liên hệ, định nghĩa ICP.", "cao", "product", "seed:cso"),
    ("product", "Gói 'superYou Private' cho doanh nghiệp: chạy AI tại chỗ (Ollama) để dữ liệu không rời máy chủ khách",
     "Video 'Private AI for law firms' và 'Local AI for free': khách ngành luật, y tế, tài chính muốn dữ liệu nằm tại chỗ. superYou đã tách được từng khách một máy chủ; thêm tuỳ chọn LLM nội bộ (Ollama, model 7B–32B) "
     "cho các việc thường ngày, giữ model đám mây cho việc khó. Bán kèm gói Doanh nghiệp giá cao hơn.", "Khác biệt với đối thủ chạy đám mây; đúng nhu cầu bảo mật của doanh nghiệp Việt.",
     "Mở phân khúc doanh nghiệp vừa, giá 25–40 triệu/khách.", "2 tuần kỹ thuật + 1 khách thí điểm.", "GTM: định giá gói Private, chọn ngành thí điểm (luật, kế toán).", "vua", "product", "seed:private"),
    ("so", "Gói ngành trên Marketplace: 'Phòng ban AI' đóng gói sẵn (Tài chính, Bán hàng, Văn phòng luật)",
     "Đóng gói mỗi 'phòng ban AI' thành bộ skill + workflow + gói tri thức bán theo gói: Finance OS cho chủ shop, Sales Desk cho solopreneur, Law Office cho văn phòng luật nhỏ. "
     "Xưởng clone dùng các blueprint này làm nguồn.", "Các video đều bán 'blueprint' từng phòng ban; Marketplace có thể bán thẳng bản chạy được.", "Sản phẩm giá 299k–999k, biên cao.", "Mỗi gói 2–3 ngày.", "GTM: thứ tự ra mắt gói.", "vua", "so", "seed:packs"),
    ("ops", "Phòng Vận hành (AI): QC hệ thống, chi phí hạ tầng và tenant báo cáo lên bảng",
     "Gom QC hiện có + chi phí VPS/LLM theo khách + tình trạng tenant thành một báo cáo tuần; sự cố và chi phí vượt ngưỡng tự thành đề xuất trên bảng.",
     "Khi có nhiều khách, anh không thể xem từng máy chủ.", "Giảm sự cố, kiểm soát chi phí theo khách.", "3 ngày.", "", "vua", "product", "seed:ops"),
    ("gtm", "Nội dung founder-led: chuỗi video ngắn 'Tôi điều hành công ty bằng superYou' theo mẫu ReStructure AI",
     "Mỗi video 60–90 giây: một phòng ban AI, một vấn đề thật, một kết quả, kết bằng 'bình luận để nhận blueprint' dẫn về landing/Marketplace. Studio bản tin của superYou dựng được.",
     "Kênh ReStructure AI tăng trưởng bằng đúng công thức này.", "Khách đăng ký giá rẻ, xây thương hiệu cá nhân anh.", "2 video/tuần, dùng Studio có sẵn.", "Product: template video 'phòng ban AI' trong Studio.", "cao", "gtm", "seed:content"),
]
for dept, title, summary, why, impact, cost, needs, prio, assign, key in P:
    print(board.propose(dept, title, summary, why, impact, cost, needs, prio, "Phòng Product (đề xuất liên phòng ban)", assign, key)["text"])
