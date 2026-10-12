# Đội quân agents cá nhân (giai đoạn 1)

Chạy trên máy của bạn, điều khiển qua một bot Telegram duy nhất.

**Đã có:** super bot (hiểu tiếng Việt tự nhiên) · nhắc lịch 21h hằng ngày · tổng hợp email mỗi giờ.
**Sắp tới:** săn tin Top 5 · soạn content theo văn phong của bạn.

## Cài đặt (khoảng 15 phút)

1. Cài Python 3.10+ từ python.org (Windows: tick "Add python.exe to PATH").
2. Giải nén thư mục này ở nơi cố định (ví dụ `Documents/agent-army`).
3. **Chuẩn bị Google (làm trước khi cài, chỉ một lần):**
   1. Vào https://console.cloud.google.com, tạo project mới.
   2. Bật 2 API: *Gmail API* và *Google Calendar API*.
   3. *OAuth consent screen* → loại External → điền thông tin cơ bản, thêm email của bạn.
      **Chuyển trạng thái sang "In production"** (nếu để "Testing", quyền hết hạn sau 7 ngày và agent sẽ tự ngừng).
   4. *Credentials* → Create credentials → OAuth client ID → loại **Desktop app**.
   5. Tải file JSON về, đổi tên thành `credentials.json`, đặt vào thư mục này.
4. Chạy trình cài đặt:
   - **Windows:** mở PowerShell trong thư mục → `Set-ExecutionPolicy -Scope Process Bypass; .\install_windows.ps1`
   - **macOS:** mở Terminal trong thư mục → `bash install_mac.sh`
5. Trình cài sẽ hỏi: token BotFather, API key Claude (đặt giới hạn chi tiêu hàng tháng!), link ICS (tùy chọn). Sau đó trình duyệt mở ra để bạn bấm "Cho phép" quyền Google (chỉ quyền ĐỌC).
6. Nhắn thử cho bot: `Mai mình có lịch gì?`

## Lark và Apple Calendar
Dùng link ICS (đăng ký/xuất lịch) dán vào bước 5, hoặc thêm vào `ICS_URLS` trong file `.env` (ngăn cách bằng dấu phẩy). Link ICS là bí mật, đừng chia sẻ.

## Lưu ý quan trọng
- Máy phải **bật, có mạng và không ngủ** thì agent mới chạy. Laptop gập nắp = agent dừng.
- Bot chỉ trả lời đúng chat ID của bạn.
- Khóa nằm trong `.env` và `data/`: không gửi hai thứ này cho ai.
- Nhật ký lỗi (macOS): `data/agent.log`. Dừng bot: Windows `Stop-ScheduledTask AgentArmy`; macOS `launchctl unload ~/Library/LaunchAgents/com.agentarmy.plist`.
- Chạy thử thủ công để xem lỗi: `.venv/bin/python main.py` (Windows: `.venv\Scripts\python main.py`).

## Kiến trúc (Mini App + Super bot + Agents)

```
Telegram ──┬── Chat tự nhiên ──> Super bot (brain.py) ──┐
           └── Nút "Mở app" ──> Mini App (webapp/)  ───┤──> core/registry.py ──> các agent trong hub.py
Lịch hẹn (APScheduler, main.py) ────────────────────────┘          │
                                                           core/store.py (Studio: mọi nội dung)
                                                           targets.json (nơi đăng: page/group/cá nhân)
```

- `hub.py`: nơi khai báo MỌI agent và công cụ. Thêm công cụ mới = viết 1 hàm trả về
  `{"text": ..., "image": ..., "video": ..., "content_id": ...}` rồi thêm `Action(...)` vào agent (hoặc `register(Agent(...))` mới).
  Công cụ tự xuất hiện trong tab "Công cụ" của Mini App (form tự sinh từ `params`) và super bot gọi được nếu `llm=True`.
- `core/store.py`: kho nội dung chung (tab Studio). Agent nào tạo nội dung thì `store.add(...)`.
- `targets.json`: nơi đăng. Page có token trong `.env` (`FB_PAGES=Tên|PAGE_ID|TOKEN`) sẽ đăng tự động;
  group và trang cá nhân: app sao chép nội dung và mở đúng trang để dán (Facebook không cho API đăng vào đó).
- `webapp/`: server Mini App (thư viện chuẩn Python) + đường hầm Cloudflare (`bin/cloudflared`).
  URL đổi mỗi lần khởi động, bot tự cập nhật nút "Mở app". Có tên miền riêng thì đặt `WEBAPP_URL=` trong `.env`.
- Bảo mật: Mini App chỉ mở được bởi tài khoản chủ (kiểm tra chữ ký Telegram + OWNER_CHAT_ID).

## Chuyển sang máy chạy 24/7
1. Copy cả thư mục (bỏ `.venv`, `bin`), chạy `Cai-dat.command`, `Cai-them-video.command`, `Cai-dat-miniapp.command`.
2. Tắt bot ở máy cũ (không chạy 2 nơi cùng lúc). Tắt chế độ ngủ của máy mới.
