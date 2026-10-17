# superYou Marketplace: thu phí và thanh toán

Anh Huy duyệt ngày 17/10/2026.

## Cơ chế thu phí
- Sàn giữ **20%** mỗi lượt bán của người tạo khác (`PLATFORM_FEE_PCT`), sản phẩm chính chủ 100% về sàn.
- Miễn phí đăng bán. Giá sàn tối thiểu 29.000đ; bậc giá gợi ý 0 / 29k / 49k / 99k / 199k / 299k.
- Mua đứt (skill, gói tri thức) hoặc thuê bao tháng (workflow có chi phí AI khi chạy).
- Hoàn tiền trong 7 ngày nếu chưa cài hoặc cài dưới 2 lần. Trả người bán ngày 10 hằng tháng khi số dư từ 200.000đ.

## Luồng mua (giai đoạn 1, đang chạy)
1. Khách bấm Mua trên app.roimaxxhub.com/market, nhập email → đơn có mã `SYXXXXXX`, mã VietQR với nội dung chuyển khoản là mã đơn, hết hạn sau 24 giờ.
2. Tiền về tài khoản của anh. Xác nhận bằng một trong hai cách:
   - **Tự động:** Casso hoặc SePay gọi `POST /api/pay/webhook` kèm token (`PAY_WEBHOOK_TOKEN`) trong header `Authorization: Apikey …` (Casso) hoặc `Secure-Token`/`X-Webhook-Token`. superYou tìm mã đơn trong nội dung chuyển khoản, khớp số tiền thì ghi đã trả.
   - **Tay:** app › Marketplace › Quản trị › Giao dịch › **Đã nhận tiền**.
3. Giao hàng: đóng gói SKILL.md / zip ghi chú / workflow.json, link tải ký 7 ngày, hoá đơn `/pay/receipt`, email cho khách (cần Gmail hoặc Lark Mail đã kết nối), ghi quyền sở hữu theo email, báo anh qua Telegram.
4. Khách xem lại ở **Tài khoản › Sản phẩm đã mua** (đơn gắn với tài khoản: mua khi đã đăng nhập, hoặc mua bằng đúng email tài khoản): tải lại (link mới ngay trên trang), gửi lại email (tối đa 3 lần/ngày/đơn, khi mail đã kết nối), xem hoá đơn, khiếu nại một chạm (chọn lý do có sẵn). Trang công khai **Đơn của tôi** chỉ hiện tên và mã đơn theo email, không lộ link tải; link mới chỉ đi qua email.

## Gói trả phí: hạn dùng và gia hạn
- Đơn gói Pro/Doanh nghiệp đã trả ghi `plan_until` (31 ngày) vào đơn và tài khoản. Gia hạn sớm cùng gói thì cộng nối tiếp từ ngày hết hạn cũ; đổi gói hoặc đã quá hạn thì tính từ hôm nay (chưa tính tiền chênh lệch).
- Quá `plan_until` (hết ngày đó) tài khoản tự về Miễn phí, giữ nguyên dữ liệu, sản phẩm đã mua, workflow; ghi nhật ký kiểm toán và báo anh qua Telegram. Dùng thử hết hạn cũng về Miễn phí; mỗi tài khoản dùng thử một lần.
- Gói anh đặt tay trong HQ › Người dùng không có hạn (không tự hết hạn).
- Nhắc gia hạn qua email khi còn ≤ 3 ngày, một lần mỗi kỳ hạn, chỉ khi Gmail/Lark Mail đã kết nối (chưa có thì không gửi, lần quét sau gửi khi đã cấu hình).
- Quét: `pay.plan_sweep()` chạy hằng ngày (job trong `main.py`, Product Lead nối) và tự chạy tối đa 1 lần/giờ khi có người mở Tài khoản.
- Tài khoản hiện ngày hết hạn, cảnh báo khi còn ≤ 3 ngày và nút Gia hạn (khi thanh toán mở).

## Sổ cái và trả người bán
- Mỗi đơn đã trả ghi một dòng: tổng, phí sàn, phần người bán. Hoàn tiền ghi dòng âm.
- Quản trị › Giao dịch: tổng bán, về sàn, tháng này, đơn chờ, nợ người bán, hoàn tiền, ghi đã trả (kèm mã giao dịch ngân hàng).
- Console người bán › Doanh thu: số dư, tháng này, lượt bán, lịch sử, tài khoản nhận tiền, kỳ trả tiếp theo.

## Khiếu nại và hoàn tiền
- Khách khiếu nại từ Tài khoản › Sản phẩm đã mua (lý do có sẵn) hoặc trang công khai (email + mã đơn). Người bán bị 3 khiếu nại/30 ngày tự bị khoá.
- Anh xử lý ở HQ › Marketplace › Quản trị › **Khiếu nại**: chấp nhận (ghi hoàn tiền, sổ cái ghi dòng âm, gỡ quyền sở hữu; đơn gói thì tài khoản về Miễn phí) hoặc từ chối (bắt buộc ghi lý do, khách nhận được). Mở/khoá người bán, khoá/mở email mua ngay trên thẻ khiếu nại.
- Phản hồi gửi email cho khách khi mail đã kết nối; luôn hiện trong Tài khoản của khách. Tiền hoàn anh chuyển khoản thủ công.

## Anh cần làm (không ai làm thay được)
1. Điền vào `/opt/superhuy/shared/.env` trên VPS: `BANK_ID` (mã ngân hàng VietQR, ví dụ MB, VCB, TCB), `BANK_ACCOUNT`, `BANK_ACCOUNT_NAME`, rồi khởi động lại superHuy.
2. Đăng ký Casso (casso.vn) hoặc SePay (sepay.vn), nối tài khoản ngân hàng, tạo webhook trỏ về `https://app.roimaxxhub.com/api/pay/webhook`, đặt token và điền `PAY_WEBHOOK_TOKEN`.
3. Kết nối Gmail hoặc Lark Mail trong app để gửi email hoá đơn.
4. Giai đoạn 2: đăng ký PayOS (payos.vn), điền `PAYOS_CLIENT_ID`, `PAYOS_API_KEY`, `PAYOS_CHECKSUM_KEY`; webhook trỏ về `/api/pay/webhook/payos`. Bán quốc tế: Lemon Squeezy (làm sau khi anh chốt).

Tình trạng từng mục hiện ở Quản trị › Giao dịch › Thiết lập thanh toán.
