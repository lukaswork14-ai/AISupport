# Nhận diện superYou v1 (anh Huy duyệt ngày 17/10/2026)

Mọi giao diện, nội dung và tính năng mới của superYou dùng đúng bộ này. Tài sản nằm ở `webapp/static/brand/` và được phục vụ tại `/brand/...`.

## Cốt lõi
- **Tên:** superYou (s thường, Y hoa). Khi cần giải thích: "superYou — trợ lý AI làm việc".
- **Khẩu hiệu:** Nói là xong. / Say it. Done.
- **Ý tưởng:** người dùng là siêu anh hùng, superYou là trợ thủ.
- **Logo:** "Bong bóng xong việc": bong bóng chat vàng, dấu tích mực vượt ra ngoài viền (`mark.svg`, nền tối: `mark-ink.svg`).
- **Linh vật:** Su, bong bóng chat có mắt (`su.svg`). Có 5 sticker trong `stickers/`: chào, đang nghe, đang làm, xong rồi, hỏi trước khi gửi.

## Màu (`tokens.css`)
| Tên | Mã | Dùng cho |
| --- | --- | --- |
| Vàng nắng | #FFD23F | Màu chủ đạo, nút chính. Chữ trên nền vàng luôn là màu mực |
| Mực | #14111A (landing dùng #0E0B14) | Chữ, nền tối, nét logo |
| Kem giấy | #FFF8E7 | Nền sáng |
| Cát | #6B5F45 | Chữ phụ trên nền kem |
| San hô | #FF6B4A | Điểm nhấn; không dùng cho chữ nhỏ |
| Xanh xong | #17784B | Trạng thái đã xong |

**Không dùng:**
- tím-xanh gradient;
- tia lấp lánh (✦), dấu sao hay mặt robot làm biểu tượng;
- emoji thay icon.

## Chữ
Dùng Be Vietnam Pro:
- 800 cho tiêu đề;
- 500 cho chữ "super" trong logo chữ;
- 400/500 cho chữ thân, cỡ 17 px.

## Giọng văn
Nói như một đồng nghiệp giỏi việc: câu ngắn, động từ đứng trước, không dùng thuật ngữ, luôn hỏi trước khi gửi. Ví dụ:
- Viết: "Xong rồi anh. 3 việc cần anh xem."
- Không viết: "Hệ thống đã xử lý thành công yêu cầu."

## Tài sản
- `icon-128/180/192/512.png` và `icon-maskable-512.png`: icon app và PWA. Instance khách tự dùng các icon này qua `manifest-superyou.webmanifest`.
- `bot-avatar-512.png`: ảnh đại diện bot Telegram/Zalo của superYou. Đặt bằng BotFather › /setuserpic; việc này anh Huy làm.
- `og.png`: ảnh xem trước khi chia sẻ link.
- `stickers/*.png` (512×512, nền trong suốt): đúng chuẩn sticker Telegram. Tạo bộ sticker bằng @Stickers; việc này anh Huy làm.

Tạo lại PNG từ SVG: render bằng Playwright/Chromium (miễn phí), font Be Vietnam Pro từ gói npm `@fontsource/be-vietnam-pro` (giấy phép OFL).

Logo là bản thiết kế nội bộ. Trước khi nộp nhãn hiệu kèm logo, nên nhờ designer tinh chỉnh đường nét.
