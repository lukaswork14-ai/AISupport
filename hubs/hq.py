"""Đăng ký công cụ superYou HQ: Phòng ban, CFO, Bán hàng (CSO), Vận hành, Khách đăng ký, Thử nghiệm.

Mảng sở hữu: Product Lead (xem docs/product-ownership.md). hub.py nạp module này; thêm/sửa công cụ của mảng ở đây.
"""
from agents import board, cfo, leads, ops, sales  # noqa: F401
from core.registry import Action, Agent, Param, register
from core import flags as _flags  # noqa: F401


# ================================================================ Phòng ban (đề xuất -> anh duyệt -> giao việc)
register(Agent("phongban", "Phòng ban", "🏢", "Các phòng ban superYou đề xuất, anh duyệt, việc tự giao về phòng phụ trách", order=59, actions=[
    Action("bang", "Bảng phòng ban", board.overview, hidden=True, llm=True,
           desc="Đề xuất của các phòng ban (Product, GTM, Sản phẩm số, Tài chính, Bán hàng, Vận hành): cái nào chờ anh duyệt, cái nào đang làm.",
           params=[Param("status", "Lọc trạng thái")]),
    Action("de_xuat", "Đưa đề xuất", board.propose, hidden=True, llm=True,
           desc="Ghi một đề xuất lên bảng phòng ban để anh duyệt. dept: product|gtm|so|finance|sales|ops.",
           params=[Param("dept", "Phòng", required=True), Param("title", "Tiêu đề", required=True), Param("summary", "Nội dung", "textarea", required=True),
                   Param("why", "Vì sao"), Param("impact", "Tác động"), Param("cost", "Chi phí, thời gian"), Param("needs", "Cần phòng khác"),
                   Param("priority", "Ưu tiên", default="vua"), Param("by", "Người đề xuất"), Param("auto_assign_to", "Giao cho"), Param("key", "Khoá chống trùng")]),
    Action("quyet", "Anh quyết định", board.decide, hidden=True,
           params=[Param("iid", "ID", required=True), Param("decision", "duyet|lam_ro|tu_choi", required=True), Param("note", "Ghi chú", "textarea"), Param("due_days", "Hạn (ngày)", "number", default=7)]),
    Action("tien_do", "Cập nhật tiến độ", board.progress, hidden=True,
           params=[Param("iid", "ID", required=True), Param("status", "dang_lam|xong|can_lam_ro", required=True), Param("result", "Kết quả", "textarea"), Param("by", "Phòng")]),
]))


# ================================================================ Tài chính superYou (CFO ảo)
register(Agent("cfo", "CFO superYou", "💼", "Finance OS: phân tích, dự báo, đề xuất hành động và bản tin tài chính mỗi sáng", order=59, actions=[
    Action("tong_quan", "Tổng quan tài chính superYou", cfo.overview, hidden=True),
    Action("phan_tich", "Analyst: bức tranh và cảnh báo", cfo.analyst, hidden=True, llm=True,
           desc="Doanh thu Marketplace, phí sàn, hoàn tiền, tập trung doanh thu, chi phí cố định, tiền mặt, cảnh báo bất thường."),
    Action("du_bao", "Forecaster: dự báo 3–6 tháng", cfo.forecast, hidden=True, llm=True,
           desc="Dự báo doanh thu, chi phí, tiền mặt và runway; kịch bản what-if: 'mất khách lớn', 'tăng giá', 'thuê thêm người', 'chạy quảng cáo'.",
           params=[Param("months", "Số tháng", "number", default=6), Param("scenario", "Kịch bản")]),
    Action("de_xuat", "Strategist: hành động nên làm", cfo.strategist, hidden=True, long=True, llm=True,
           desc="CFO xếp hạng 3–5 hành động tăng tiền mặt/doanh thu, cắt chi phí; anh duyệt thì thành việc trên bảng Phòng ban.",
           params=[Param("auto_propose", "Tự đưa lên bảng", "bool", default=False)]),
    Action("len_bang", "Đưa hành động lên bảng", cfo.to_board, hidden=True, params=[Param("action_id", "ID", required=True)]),
    Action("ban_tin", "CFO brief một trang", cfo.brief, hidden=True, llm=True, desc="Bản tin tài chính một trang: tiền mặt, thay đổi, nghĩa vụ, 3 việc nên làm.",
           params=[Param("save", "Lưu", "bool", default=True)]),
    Action("chi_phi_them", "Thêm chi phí cố định", cfo.add_cost, hidden=True, llm=True,
           desc="Ghi một chi phí vận hành cố định của superYou (VPS, tên miền, LLM, công cụ). Ví dụ: VPS 300k mỗi tháng.",
           params=[Param("name", "Tên", required=True), Param("amount", "Số tiền", required=True), Param("period", "Chu kỳ", default="monthly"),
                   Param("category", "Nhóm", default="ha_tang"), Param("note", "Ghi chú")]),
    Action("chi_phi_xoa", "Xoá chi phí", cfo.remove_cost, hidden=True, params=[Param("cid", "ID", required=True)]),
    Action("tien_mat", "Ghi tiền mặt hiện có", cfo.set_cash, hidden=True, llm=True, desc="Ghi số dư tiền mặt của superYou/Roimaxx để dự báo runway.",
           params=[Param("amount", "Số tiền", required=True)]),
]))


# ================================================================ Thử nghiệm và phân cấp (chỉ chủ nhân)
register(Agent("thunghiem", "Thử nghiệm", "🧪", "Bật tính năng theo phạm vi (riêng anh, theo gói, tất cả), A/B testing, đề xuất nâng cấp", order=59, actions=[
    Action("tong_quan", "Tính năng, thử nghiệm, gói", _flags.overview, hidden=True, llm=True,
           desc="Trạng thái các tính năng (bật cho ai), thử nghiệm A/B đang chạy và kết quả, số người dùng theo gói."),
    Action("bat", "Đặt phạm vi tính năng", _flags.set_flag, hidden=True,
           params=[Param("key", "Mã", required=True), Param("scope", "Phạm vi", required=True), Param("tiers", "Gói"), Param("pct", "Phần trăm", "number", default=100), Param("name", "Tên"), Param("desc", "Mô tả")]),
    Action("ab_tao", "Tạo thử nghiệm A/B", _flags.create_experiment, hidden=True,
           params=[Param("key", "Mã", required=True), Param("name", "Tên", required=True), Param("hypothesis", "Giả thuyết", "textarea"), Param("variants", "Biến thể", default="A,B"), Param("split", "Tỷ lệ A", "number", default=50), Param("metric", "Chỉ số", default="convert")]),
    Action("ab_trang_thai", "Chạy/dừng thử nghiệm", _flags.set_experiment, hidden=True, params=[Param("key", "Mã", required=True), Param("status", "Trạng thái", required=True), Param("result", "Kết luận", "textarea")]),
    Action("ab_ket_qua", "Kết quả thử nghiệm", _flags.results, hidden=True, params=[Param("key", "Mã", required=True)]),
    Action("nghien_cuu", "AI nghiên cứu, đề xuất nâng cấp", _flags.research_propose, hidden=True, long=True),
]))


# ================================================================ Bán hàng superYou (CSO ảo)
register(Agent("sales", "Phòng Bán hàng (CSO)", "📈", "CSO ảo: chấm điểm khách tiềm năng, soạn thư theo đuổi chờ anh duyệt, phễu RevOps và kế hoạch tuần", order=60, actions=[
    Action("tong_quan", "Tổng quan bán hàng", sales.overview, hidden=True),
    Action("phieu", "RevOps: phễu bán hàng", sales.pipeline, hidden=True, llm=True,
           desc="Phễu khách đăng ký → liên hệ → trao đổi → dùng thử → khách hàng; tỷ lệ chuyển đổi, dùng thử sắp hết hạn, khách bị bỏ quên, doanh thu."),
    Action("nghien_cuu", "Nghiên cứu: điểm ICP một khách", sales.research, hidden=True, long=True, llm=True,
           desc="Chấm điểm phù hợp (0–100), phân khúc (solopreneur/quản lý/doanh nghiệp) và bước tiếp theo cho một email khách.",
           params=[Param("email", "Email khách", required=True), Param("refresh", "Chấm lại", "bool", default=False)]),
    Action("soan", "Theo đuổi: soạn thư chờ duyệt", sales.draft, hidden=True, long=True, llm=True,
           desc="Soạn nháp thư tiếng Việt cho khách (chào mừng, nhắc dùng thử, sắp hết hạn, nâng cấp, hỏi thăm). Chỉ lưu nháp, anh duyệt mới gửi.",
           params=[Param("email", "Email khách", required=True),
                   Param("kind", "Loại thư", "select", options=[{"value": k, "label": v} for k, v in sales.KINDS.items()], default="chao_mung"),
                   Param("note", "Ý thêm", "textarea")]),
    Action("nhap", "Danh sách nháp", sales.drafts, hidden=True,
           params=[Param("status", "Trạng thái", "select", options=[""] + list(sales.DRAFT_STATUS), default="cho_duyet")]),
    Action("duyet", "Duyệt và gửi thư", sales.approve, hidden=True, long=True, params=[
        Param("did", "ID nháp", required=True), Param("send", "Gửi ngay", "bool", default=True),
        Param("platform", "Nền tảng", "select", options=["", "lark", "gmail"], default="")]),
    Action("tu_choi", "Bỏ nháp", sales.reject, hidden=True, params=[Param("did", "ID nháp", required=True), Param("note", "Lý do")]),
    Action("theo_duoi_tu_dong", "Soạn nháp theo đuổi hôm nay", sales.auto_followups, hidden=True, long=True, llm=True,
           desc="Quét khách mới chưa liên hệ và dùng thử sắp hết hạn, soạn nháp chờ anh duyệt (không tự gửi)."),
    Action("bao_cao_tuan", "Kế hoạch bán hàng tuần", sales.weekly_report, hidden=True, long=True, llm=True,
           desc="Tóm tắt phễu + 3 hành động đề xuất; đưa lên bảng Phòng ban nếu to_board.",
           params=[Param("to_board", "Đưa lên bảng", "bool", default=True)]),
]))


# ================================================================ Vận hành superYou
register(Agent("ops", "Vận hành superYou", "🛠", "Phòng Vận hành (AI): tenant, sức khỏe hệ thống, chi phí hạ tầng trên mỗi khách, cảnh báo theo ngưỡng", order=60, actions=[
    Action("tong_quan", "Tổng quan vận hành", ops.overview, hidden=True),
    Action("tenant", "Danh sách tenant", ops.tenants, hidden=True, llm=True,
           desc="Các instance khách (systemd superyou@<slug>): trạng thái dịch vụ, dung lượng dữ liệu, log cuối; kèm instance chính."),
    Action("suc_khoe", "Sức khỏe hệ thống", ops.system_health, hidden=True, llm=True,
           desc="Tóm tắt kết quả QC, ổ đĩa, tải CPU, bộ nhớ bot."),
    Action("chi_phi", "Ảnh chụp chi phí/khách", ops.cost_snapshot, hidden=True, llm=True,
           desc="Chi phí hạ tầng cố định (từ CFO) chia cho số khách đang chạy + ước tính LLM; lưu theo ngày."),
    Action("nguong", "Xem ngưỡng cảnh báo", ops.thresholds, hidden=True),
    Action("dat_nguong", "Đặt ngưỡng cảnh báo", ops.set_threshold, hidden=True, llm=True,
           desc="Ngưỡng: disk_pct (% ổ đĩa), qc_fails (số lượt lỗi QC), cost_per_customer (đ/khách/tháng), tenant_down (có báo tenant dừng).",
           params=[Param("key", "Ngưỡng", required=True), Param("value", "Giá trị", required=True)]),
    Action("canh_bao", "Kiểm tra cảnh báo", ops.check_alerts, hidden=True, llm=True,
           desc="So sánh sức khỏe, chi phí, tenant với ngưỡng; vi phạm thì báo Telegram và đưa đề xuất lên bảng Phòng ban (giao Product).",
           params=[Param("auto_propose", "Tự đưa lên bảng", "bool", default=True)]),
    Action("bao_cao_tuan", "Báo cáo vận hành tuần", ops.weekly_report, hidden=True, long=True, llm=True,
           desc="Báo cáo một trang: uptime, sự cố, chi phí/khách so với tuần trước, bảng tenant, ổ đĩa, 3 khuyến nghị.",
           params=[Param("to_board", "Đưa lên bảng", "bool", default=True)]),
]))


# ================================================================ Khách đăng ký (landing page, Marketplace công khai)
register(Agent("khach", "Khách đăng ký", "📇", "Email khách để lại trên landing page và Marketplace, theo dõi phễu liên hệ", order=59, actions=[
    Action("ds", "Khách đăng ký", leads.overview, hidden=True, llm=True,
           desc="Danh sách khách để lại email trên landing page / Marketplace, trạng thái liên hệ, nguồn đến, số đăng ký theo ngày."),
    Action("trangthai", "Đổi trạng thái khách", leads.set_status, hidden=True,
           params=[Param("email", "Email", required=True), Param("status", "Trạng thái", required=True), Param("note", "Ghi chú", "textarea")]),
]))
