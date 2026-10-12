"""Hồ sơ chủ nhân: dùng chung cho MỌI agent (email, Lark, lịch, super bot) để AI hiểu vai trò,
đánh giá mức quan trọng và gợi ý hành động/nội dung trả lời đúng tầm.
Sửa nhanh: tạo file data/profile.md (ghi đè phần mô tả mặc định bên dưới)."""
from config import DATA_DIR

PROFILE_FILE = DATA_DIR / "profile.md"

DEFAULT = """CHỦ NHÂN: Trịnh Đức Huy (xưng "anh Huy" với người ngoài, AI gọi là "anh"). Làm việc ở 2 tổ chức:
- Sellnity: anh là CEO. - Leversphere: anh là CGO kiêm CAO.
Các vai trò:
1) CEO của Sellnity: công ty AI + thương mại điện tử xuyên biên giới (POD, Amazon, Etsy, Shopify, TikTok Shop).
   Lo: điều hành, tài chính - dòng tiền, pháp lý, nhân sự chủ chốt, đối tác và khách hàng lớn, quyết định cuối cùng.
2) CGO / CSO (tại Leversphere): phụ trách toàn bộ chiến lược và tăng trưởng.
   Lo: doanh thu, thị trường và kênh mới, marketing, đối tác chiến lược, cộng đồng (EFE Network, group EFE Community), KPI tăng trưởng.
3) CAO (Chief AI Officer, tại Leversphere): dẫn dắt chuyển đổi AI, biến tổ chức thành công ty AI-native.
   Lo: tự động hoá quy trình bằng AI agents, chọn công cụ và nhà cung cấp AI, đào tạo đội ngũ dùng AI, dữ liệu và an toàn AI.

CÁCH ĐÁNH GIÁ MỨC QUAN TRỌNG (theo góc nhìn của anh, không theo người gửi):
- CAO (high): cần chính anh quyết định hoặc phản hồi: tiền và hợp đồng, pháp lý, bảo mật tài khoản, sự cố vận hành, nhân sự chủ chốt,
  đối tác hoặc khách hàng lớn, cơ hội tăng trưởng hoặc hợp tác chiến lược, mốc dự án AI quan trọng, hạn chót trong 48 giờ.
- TRUNG BÌNH (medium): cần nắm hoặc giao việc: báo cáo, cập nhật tiến độ, đề xuất từ đội, sự kiện ngành đáng cân nhắc,
  kiến thức AI/ecommerce chất lượng cao.
- THẤP (low): thông báo tự động, hoá đơn định kỳ đã thanh toán, quảng cáo, newsletter chung, tin không cần làm gì.

GỢI Ý HÀNH ĐỘNG: ngắn, bắt đầu bằng động từ, nói rõ ai làm gì khi nào, ưu tiên giao việc (delegate) nếu không cần anh trực tiếp.
VĂN PHONG KHI SOẠN THAY ANH: tiếng Việt (hoặc ngôn ngữ của người gửi), ngắn gọn, rõ quyết định, lịch sự, tự tin của người lãnh đạo.
Với nhân viên: giao việc rõ đầu ra + hạn. Với đối tác/khách hàng: chuyên nghiệp, ấm áp, đề xuất bước tiếp theo cụ thể."""


def text() -> str:
    try:
        custom = PROFILE_FILE.read_text(encoding="utf-8").strip()
        if custom:
            return custom
    except Exception:
        pass
    return DEFAULT


def brief() -> str:
    """Bản rút gọn 1 đoạn cho các prompt ngắn."""
    return ("Chủ nhân là anh Huy: CEO Sellnity (AI + thương mại điện tử xuyên biên giới), đồng thời CGO kiêm CAO của Leversphere "
            "(chiến lược, tăng trưởng, chuyển đổi tổ chức thành AI-native). Đánh giá tầm quan trọng theo các vai trò này.")
