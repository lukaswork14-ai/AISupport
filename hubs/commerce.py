"""Đăng ký công cụ mảng Thương mại & Marketplace: Marketplace, Xưởng clone, tài khoản, gói.

Mảng sở hữu: session Thương mại & Marketplace (xem docs/product-ownership.md). hub.py nạp module này; thêm/sửa công cụ của mảng ở đây.
"""
from agents import factory, market, pay  # noqa: F401
from core.registry import Action, Agent, Param, register
from core import accounts as _accounts, plans as _plans  # noqa: E402,F401


# ================================================================ Marketplace: skill, gói Second Brain, workflow
register(Agent("market", "Marketplace", "🛍", "Khám phá, cài và bán skill, gói Second Brain, workflow cho superHuy", order=59, actions=[
    Action("ds", "Khám phá Marketplace", market.catalog, hidden=True, llm=True,
           desc="Xem sản phẩm trên superHuy Marketplace (skill, gói Second Brain, workflow), tìm theo từ khoá, xem anh đã cài gì.",
           params=[Param("q", "Từ khoá"), Param("cat", "Danh mục"), Param("type", "Loại")]),
    Action("xem", "Chi tiết sản phẩm", market.item, hidden=True, params=[Param("lid", "ID", required=True)]),
    Action("cai", "Cài sản phẩm", market.install, hidden=True, long=True, params=[Param("lid", "ID", required=True)]),
    Action("go", "Gỡ sản phẩm", market.uninstall, hidden=True, params=[Param("lid", "ID", required=True)]),
    Action("batat", "Bật/tắt sản phẩm đã cài", market.toggle, hidden=True, params=[Param("lid", "ID", required=True)]),
    Action("chay", "Chạy workflow", market.run_workflow, hidden=True, long=True, llm=True,
           desc="Chạy một workflow đã cài từ Marketplace (ví dụ 'Bàn giao buổi sáng'). Truyền name = tên workflow hoặc lid = ID.",
           params=[Param("lid", "ID"), Param("name", "Tên workflow")]),
    Action("danhgia", "Đánh giá sản phẩm", market.review, hidden=True,
           params=[Param("lid", "ID", required=True), Param("stars", "Số sao", "number", default=5), Param("text", "Nhận xét", "textarea")]),
    Action("tao", "Đăng sản phẩm lên Marketplace", market.create, hidden=True,
           params=[Param("type", "Loại", required=True), Param("name", "Tên", required=True), Param("tagline", "Mô tả ngắn"),
                   Param("description", "Mô tả", "textarea"), Param("body", "Nội dung", "textarea", required=True),
                   Param("category", "Danh mục", default="nang-suat"), Param("price", "Giá (đồng)", "number", default=0),
                   Param("tags", "Thẻ (cách nhau dấu phẩy)"), Param("publish", "Lên kệ ngay", "bool", default=True)]),
    Action("sua", "Cập nhật sản phẩm", market.update, hidden=True,
           params=[Param("lid", "ID", required=True), Param("version", "Phiên bản"), Param("whats_new", "Có gì mới", "textarea"),
                   Param("body", "Nội dung", "textarea"), Param("tagline", "Mô tả ngắn"), Param("description", "Mô tả", "textarea"),
                   Param("price", "Giá", "number"), Param("status", "Trạng thái")]),
    Action("cuatoi", "Sản phẩm của tôi", market.mine, hidden=True),
    # Phòng Phát triển sản phẩm số (chỉ chủ nhân)
    Action("donggoi", "AI đóng gói tài sản số", market.pack, hidden=True, long=True,
           params=[Param("raw", "Nguyên liệu", "textarea"), Param("hint_type", "Loại"), Param("source_url", "Link nguồn"),
                   Param("clone", "Dựng từ nguồn", "bool", default=False)]),
    Action("studio_luu", "Lưu sản phẩm trong Studio", market.studio_save, hidden=True,
           params=[Param("type", "Loại", required=True), Param("name", "Tên", required=True), Param("tagline", "Mô tả ngắn"),
                   Param("description", "Mô tả", "textarea"), Param("body", "Nội dung", "textarea", required=True),
                   Param("category", "Danh mục", default="nang-suat"), Param("price", "Giá", "number", default=0), Param("tags", "Thẻ"),
                   Param("publish", "Lên kệ", "bool", default=False), Param("featured", "Nổi bật", "bool", default=False),
                   Param("source_url", "Nguồn"), Param("lid", "ID")]),
    Action("studio_xem", "Nội dung gốc sản phẩm", market.studio_body, hidden=True, params=[Param("lid", "ID", required=True)]),
    Action("nhanban", "Nhân bản sản phẩm", market.clone, hidden=True, params=[Param("lid", "ID", required=True)]),
    # Quản trị cao nhất (chủ App Store)
    Action("quantri", "Quản trị Marketplace", market.admin_overview, hidden=True, llm=True,
           desc="Bảng quản trị Marketplace (chỉ chủ nhân): số sản phẩm, người tạo, lượt cài, lượt quan tâm, hàng chờ duyệt, nhật ký."),
    Action("qt_sua", "Quản trị: đổi trạng thái/giá/nổi bật", market.admin_set, hidden=True,
           params=[Param("lid", "ID", required=True), Param("field", "Trường", required=True), Param("value", "Giá trị"), Param("note", "Ghi chú", "textarea")]),
    Action("qt_nguoitao", "Quản trị người tạo", market.admin_creator, hidden=True,
           params=[Param("cid", "ID", required=True), Param("action", "Thao tác", required=True)]),
    Action("qt_duyet_gia", "Duyệt lên kệ kèm giá", market.approve_publish, hidden=True,
           params=[Param("lid", "ID", required=True), Param("price", "Giá", "number"), Param("billing", "Chu kỳ"), Param("featured", "Nổi bật", "bool"), Param("note", "Ghi chú", "textarea")]),
    Action("goi_y_gia", "Gợi ý giá", market.price_suggest, hidden=True, params=[Param("lid", "ID", required=True)]),
    # Thanh toán và sổ cái (chỉ chủ nhân)
    Action("gd", "Giao dịch và doanh thu", pay.admin_overview, hidden=True, llm=True,
           desc="Doanh thu Marketplace: tổng bán, phí sàn, đơn chờ thanh toán, số còn nợ người bán, cấu hình thanh toán."),
    Action("gd_nhan", "Xác nhận đã nhận tiền", pay.confirm_manual, hidden=True, params=[Param("oid", "ID đơn", required=True), Param("note", "Ghi chú")]),
    Action("gd_hoan", "Hoàn tiền", pay.refund, hidden=True, params=[Param("oid", "ID đơn", required=True), Param("note", "Lý do", "textarea")]),
    Action("gd_tra", "Ghi trả tiền người bán", pay.payout_mark, hidden=True,
           params=[Param("sid", "ID người bán", required=True), Param("amount", "Số tiền", "number"), Param("ref", "Mã giao dịch")]),
    Action("duyet", "Duyệt sản phẩm gửi lên", market.moderate, hidden=True,
           params=[Param("lid", "ID", required=True), Param("decision", "Quyết định", required=True), Param("note", "Ghi chú", "textarea")]),
]))


# ================================================================ Xưởng sản phẩm số (Clone Factory, chỉ chủ nhân)
register(Agent("xuong", "Xưởng sản phẩm số", "🏭", "Quét app/repo đang thắng thị trường, clone thành sản phẩm của riêng anh", order=59, actions=[
    Action("quet", "Quét thị trường", factory.scan, hidden=True, long=True, llm=True,
           desc="Quét bảng xếp hạng App Store (iPhone/Mac, theo nước và danh mục), GitHub Trending, Product Hunt; hoặc tìm theo từ khoá. src=ios|mac|github|ph.",
           params=[Param("src", "Nguồn", default="ios"), Param("country", "Nước", default="vn"), Param("chart", "Bảng", default="free"),
                   Param("genre", "Danh mục"), Param("q", "Từ khoá"), Param("limit", "Số lượng", "number", default=50)]),
    Action("xem", "Chi tiết sản phẩm gốc", factory.detail, hidden=True, long=True,
           params=[Param("key", "Mã", required=True), Param("country", "Nước", default="vn")]),
    Action("theodoi", "Theo dõi sản phẩm", factory.star, hidden=True, params=[Param("key", "Mã", required=True)]),
    Action("ghichu", "Lưu ghi chú clone", factory.save_note, hidden=True, params=[Param("text", "Ghi chú", "textarea", required=True)]),
    Action("clone", "Clone thành bản thiết kế", factory.clone, hidden=True, long=True,
           params=[Param("key", "Mã", required=True), Param("target", "Nền tảng đích", default="web"), Param("options", "Tuỳ chọn"),
                   Param("notes", "Ghi chú", "textarea"), Param("project", "Tên dự án"), Param("country", "Nước", default="vn")]),
    Action("duan_ds", "Dự án trong xưởng", factory.projects, hidden=True),
    Action("duan", "Chi tiết dự án", factory.project, hidden=True, params=[Param("pid", "ID", required=True)]),
    Action("duan_sua", "Đổi trạng thái dự án", factory.project_set, hidden=True,
           params=[Param("pid", "ID", required=True), Param("status", "Trạng thái"), Param("note", "Ghi chú", "textarea")]),
    Action("duan_xoa", "Xoá dự án", factory.project_delete, hidden=True, params=[Param("pid", "ID", required=True)]),
    Action("len_cho", "Đưa dự án lên Marketplace", factory.to_market, hidden=True,
           params=[Param("pid", "ID", required=True), Param("publish", "Lên kệ", "bool", default=False), Param("price", "Giá", "number", default=0)]),
    Action("goi_y_gia", "Gợi ý giá cho dự án", factory.price_reco, hidden=True, params=[Param("pid", "ID", required=True)]),
]))


# ================================================================ Người dùng, vai trò, gói (chỉ chủ sàn)
register(Agent("nguoidung", "Người dùng & gói", "🪪", "Tài khoản, vai trò, gói, chính sách gói, nhật ký kiểm toán", order=59, actions=[
    Action("ds", "Danh sách người dùng", _accounts.admin_list, hidden=True, llm=True, desc="Người dùng superYou theo vai trò và gói; nhật ký kiểm toán.",
           params=[Param("q", "Tìm"), Param("role", "Vai"), Param("plan", "Gói")]),
    Action("sua", "Đổi gói, trạng thái, vai", _accounts.admin_set, hidden=True,
           params=[Param("uid", "ID", required=True), Param("plan", "Gói"), Param("status", "Trạng thái"), Param("roles", "Vai (phẩy)"), Param("note", "Ghi chú")]),
    Action("goi", "Chính sách gói", _plans.all_plans, hidden=True, llm=True, desc="Ma trận gói: giá, tính năng, giới hạn."),
    Action("goi_sua", "Sửa chính sách gói", _plans.update, hidden=True,
           params=[Param("plan", "Gói", required=True), Param("price", "Giá", "number"), Param("tagline", "Mô tả ngắn"), Param("features", "Tính năng (mỗi dòng)", "textarea"), Param("limits", "Giới hạn (JSON)")]),
]))
