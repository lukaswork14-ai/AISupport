# superYou / superHuy: quy tắc cho mọi session

Đọc `docs/product-ownership.md` trước khi sửa code. Tóm tắt:

- Phòng Product chia 4 session: Product Lead, Trải nghiệm & Giao diện, Thương mại & Marketplace, Nền tảng & DevOps. QA & Bảo mật và GTM độc lập.
- Chỉ sửa file thuộc mảng của mình (bảng sở hữu trong `docs/product-ownership.md`). Cần sửa file mảng khác: mở PR và báo chủ file, hoặc ghi đề xuất lên bảng.
- Làm trên nhánh `product/<mang>-<viec>`, mở PR vào `main`. Chỉ Product Lead gộp vào `main` và phát hành.
- Trước PR: rebase lên `main`, chạy `python -m pytest -q tests` và `python -m webapp.appbuild --js /tmp/app.js && node --check /tmp/app.js`. Thay đổi giao diện kèm ảnh điện thoại + Mac.
- Giao diện app ráp từ `webapp/app/` (shell + css/*.css + js/*.js theo thứ tự tên). Không còn `webapp/static/index.html`.
- Không bao giờ gõ, in, commit khoá, mật khẩu, token hay giá trị `.env`. Repo công khai.
- Tính năng mới bật "Chỉ anh" trước (`core/flags.py`). Ưu tiên số một: chạy ổn định, nhanh, mượt.
- Viết giao diện và thông báo bằng tiếng Việt, xưng "anh" với chủ nhân (anh Huy).
