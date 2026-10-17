# Phòng Product superYou: ai sở hữu file nào, làm việc và phát hành ra sao

Anh Huy duyệt ngày 17/10/2026. Mục tiêu: nhiều session cùng phát triển mà không chồng chéo, superYou luôn chạy ổn định, nhanh, mượt.

## Các session trong phòng Product

| Session | Phụ trách |
|---|---|
| **Product Lead** | Lộ trình, bảng đề xuất, gộp code vào `main`, phát hành, báo cáo anh Huy. Trợ lý cá nhân superHuy, superYou HQ và các phòng ban AI (CFO, CSO, Vận hành). Chủ các file dùng chung. |
| **Trải nghiệm & Giao diện** | Hệ thống thiết kế và nhận diện, landing, chuẩn hoá UI/UX trên mọi màn hình (điện thoại, iPad, Mac, Telegram Mini App giữ màu Telegram), chuyển động, trợ năng. |
| **Thương mại & Marketplace** | Marketplace (danh mục, xếp hạng, đánh giá, mua bán), thanh toán và sổ cái, tài khoản, vai trò, gói, console người bán, trang công khai của Marketplace. Làm trọn từ backend tới giao diện của mảng. |
| **Xưởng Tài sản số** | Tìm nguồn, chấm điểm, clone có cải tiến (đội BA/PO/Dev/Designer/Tester/Kiểm duyệt) thành skill, Second Brain, OS theo vai trò; bàn giao cho chợ bản sẵn sàng để anh bấm Publish. Xem `docs/xuong-tai-san-so.md`. |
| **Nền tảng & DevOps** | CI/CD, VPS, tenant cho khách, sao lưu, giám sát, hiệu năng, bảo mật hạ tầng. |

Ngoài phòng Product, giữ nguyên và độc lập: **QA & Bảo mật** (kiểm thử chéo, không sửa tính năng), **GTM**.

## Bảng sở hữu file

Chủ file là người duy nhất sửa trực tiếp. Mảng khác cần thay đổi thì mở PR có tag chủ file trong mô tả, hoặc ghi đề xuất lên bảng điều phối.

| Đường dẫn | Chủ |
|---|---|
| `hub.py`, `main.py`, `brain.py`, `llm.py`, `core/registry.py`, phần định tuyến trong `webapp/server.py` | Product Lead |
| `hubs/hq.py`, `agents/board.py, cfo.py, sales.py, ops.py, leads.py, workspace.py`, `core/flags.py, private_llm.py, activation.py` | Product Lead |
| Các agent trợ lý cá nhân: `agents/` còn lại (lịch, email, họp, nội dung, Studio, học, game, tài chính cá nhân, Second Brain...) | Product Lead |
| `webapp/app/js/00-core.js, 10-assistant.js, 30-leads.js, 40-me.js, 50-hq.js, 60-life.js, 90-shell.js`, `webapp/app/css/50-hq-me.css` | Product Lead |
| `webapp/app/shell.html`, `webapp/app/css/00-base.css, 10-aura.css, 20-motion.css, 30-responsive.css`, `webapp/static/brand/`, `webapp/static/landing/`, `webapp/static/legal/` (trình bày), `docs/superyou-brand.md` | Trải nghiệm & Giao diện |
| `agents/factory.py, factory_team.py`, `webapp/app/js/25-factory.js`, `webapp/app/css/45-factory.css`, `deploy/factory_qa.py`, khối `register(Agent("xuong"...` trong `hubs/commerce.py`, `docs/xuong-tai-san-so.md` | Xưởng Tài sản số |
| `hubs/commerce.py` (trừ khối xuong), `agents/market.py, pay.py, trial_minutes.py`, `core/accounts.py, plans.py, passkey.py`, `webapp/app/js/20-market.js, 35-roles.js`, `webapp/app/css/40-market.css`, `webapp/static/market/`, `webapp/static/account/`, các route `/api/market, /api/pay, /api/creator, /api/account` trong `server.py`, `docs/superyou-thanh-toan.md` | Thương mại & Marketplace |
| `.github/workflows/`, `deploy/` (trừ QA của từng mảng), `config.py`, `requirements.txt`, `deploy/vps_defaults.env`, `docs/superyou-pilot.md` | Nền tảng & DevOps |
| `tests/` | Mảng nào viết test cho mảng đó; QA & Bảo mật được thêm test ở mọi mảng |
| Nội dung pháp lý trong `webapp/static/legal/` (điều khoản, hoàn tiền) | GTM viết, Giao diện trình bày, Thương mại nối luồng khiếu nại |

Giao diện app được ráp từ `webapp/app/` (xem `webapp/appbuild.py`): `shell.html` + `css/*.css` + `js/*.js` theo thứ tự tên file, thành một trang duy nhất y như trước. Mảng mới cần JS/CSS riêng thì tạo file mới `NN-ten.js` / `NN-ten.css`, không chèn vào file của mảng khác. Mọi file JS dùng chung một phạm vi toàn cục, nên đặt tên hàm có tiền tố mảng (`mk…`, `hq…`, `sales…`).

## Luật làm việc

1. **Không ai đẩy thẳng lên `main`, trừ Product Lead khi phát hành.** Mỗi session làm trên nhánh riêng `product/<mang>-<viec>` (ví dụ `product/thuongmai-payos`, `product/giaodien-hq`), mở PR vào `main`.
2. **Product Lead gộp PR** sau khi: test xanh (`python -m pytest -q tests`, `python -m webapp.appbuild --js /tmp/app.js && node --check /tmp/app.js`), có ảnh chụp màn hình điện thoại + Mac cho thay đổi giao diện, không sửa file của mảng khác mà không báo. Gộp xong, deploy tự chạy; Product Lead chạy diag xác nhận.
3. **Trước khi bắt đầu việc: kéo `main` mới nhất. Trước khi mở PR: rebase lên `main`.** Xung đột ở file của mảng mình thì tự giải; ở file mảng khác thì hỏi chủ file.
4. **Việc anh Huy duyệt mới làm.** Đề xuất ghi lên bảng điều phối (phòng `product`, ghi mảng trong tiêu đề, ví dụ "[Thương mại] Thuê bao PayOS"). Việc nhỏ trong mảng mình, không đổi hành vi người dùng, thì làm luôn.
5. **Bí mật:** không bao giờ gõ, in hay commit khoá, mật khẩu, token, giá trị `.env`. Repo công khai. Không dùng mật khẩu root VPS.
6. **Ổn định trước:** "superHuy phải luôn được chạy ổn định, nhanh, mượt mà". Tính năng mới bật "Chỉ anh" trước (core/flags), rồi mới mở rộng.

## Bảng điều phối

- Bảng của anh Huy (artifact Claude): https://claude.ai/artifact/JbP2uuvxHW1TKPZTSQKnw4, collection `de_xuat`.
- Bảng trong app: superYou HQ › Phòng ban (`agents/board.py`).
