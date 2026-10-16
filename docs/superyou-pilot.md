# superYou thí điểm: chạy cho khách hàng thứ hai

Mục tiêu: cài superYou cho 1–3 khách thí điểm (nhà quản lý, solopreneur), mỗi khách tách biệt hoàn toàn với superHuy của anh Huy.

## Kiến trúc thí điểm (đã có)

- **Một bộ mã, nhiều instance.** Mỗi khách là một dịch vụ `superyou@<slug>` chạy chung mã `/opt/superhuy/current`, nên mỗi lần triển khai thì mọi khách cùng lên bản mới. `release.sh` tự khởi động lại các tenant.
- **Dữ liệu tách biệt.** Mỗi khách có thư mục riêng `/opt/superyou-tenants/<slug>/`, gồm `data/`, `vault/` và `.env` (quyền 600). Ba thứ tách riêng:
  - `SUPERHUY_HOME` trỏ vào thư mục của khách, nên lịch sử, trí nhớ, biên bản, Marketplace và khách đăng ký không lẫn với nhau.
  - Mỗi khách dùng bot Telegram riêng (`TELEGRAM_TOKEN`, `OWNER_CHAT_ID`) và mã PIN riêng.
  - Mỗi khách có khoá LLM riêng để tính chi phí theo khách.
- **Cổng và tên miền riêng.** Cổng 8801–8899 (8787 là của superHuy), nginx và HTTPS cho tên miền của khách.
- **Giới hạn tài nguyên.** `MemoryMax=900M` cho mỗi khách, để một khách không làm treo cả VPS.

## Cài một khách (khoảng 15 phút)

1. Tạo bản ghi DNS `A <slug>.superyou.roimaxxhub.com` trỏ về IP của VPS.
2. Khách tạo bot qua BotFather và tự giữ token. Đội Roimaxx nhận token qua kênh riêng, không gửi qua repo hay chat chung.
3. Chạy bằng root: `sudo bash deploy/tenant_vps.sh <slug> <tên-miền> <cổng>`.
4. Điền khoá vào `/opt/superyou-tenants/<slug>/.env`, rồi chạy `systemctl start superyou@<slug>`.
5. Khách mở bot, đặt mã PIN, kết nối Gmail, lịch và Lark trong app › Cài đặt.

## Việc cần làm tiếp để bán rộng (giai đoạn 2)

Mã hiện còn nhiều chỗ viết riêng cho anh Huy:
- 11 tệp nhắc tên Sellnity và Leversphere: `strategy.py`, `learning.py`, `brain.py`, `profile.py`…
- Khoảng 190 chỗ nhắc tên trợ lý "superHuy".

Những chỗ này cần đổi thành cấu hình theo từng khách:
- `ASSISTANT_NAME`: khách đặt tên trợ lý của mình (mặc định "superYou").
- Hồ sơ công ty: tên, ngành, mục tiêu. Các góc nhìn chiến lược và khoá học lấy từ hồ sơ này, không viết cứng Sellnity hay Leversphere.
- Onboarding tự phục vụ: đăng ký trên landing page, nhận bot và thanh toán (VietQR hoặc thẻ), không cần đội Roimaxx cài tay.
- Bảng điều khiển vận hành cho Roimaxx: các tenant, tình trạng, chi phí LLM của từng khách.
