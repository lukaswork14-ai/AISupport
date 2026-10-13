# Triển khai superHuy lên VPS (CI/CD)

Mỗi lần đẩy code lên nhánh `main`, GitHub Actions sẽ:

1. **Kiểm tra** trên Python 3.10 và 3.12: cài thư viện, biên dịch, import các module, kiểm tra JavaScript của Mini App và các script triển khai.
2. **Triển khai**:
   - chép code lên VPS vào `/opt/superhuy/releases/<commit>`;
   - cài thêm thư viện nếu `requirements.txt` đổi;
   - chuyển `current` sang bản mới và khởi động lại;
   - chờ `/health` trả lời. Nếu bản mới không chạy, **tự quay về bản cũ**.
3. **Giám sát** (`monitor.yml`): 30 phút một lần gọi `https://<tên miền>/health`. Nếu VPS không phản hồi thì nhắn Telegram.

Dữ liệu và khoá **không bao giờ** nằm trong repo. Chúng ở `/opt/superhuy/shared` trên VPS: `.env`, `credentials.json`, `data/`, `vault/`, và mỗi lần triển khai đều giữ nguyên.

```
/opt/superhuy
├── current -> releases/<commit>   # code đang chạy
├── releases/                      # 5 bản gần nhất (để quay lại)
├── venv/                          # thư viện Python
└── shared/                        # SUPERHUY_HOME: .env, credentials.json, data/, vault/, khoá vault
```

## Cài lần đầu (khoảng 10 phút)

**Cần có:** VPS Ubuntu 22.04/24.04, một tên miền (ví dụ `app.sellnity.com`), và repo GitHub private cho Obsidian (ví dụ `superhuy-vault`). Repo Obsidian có thể làm sau.

1. **Trên Mac**, bấm đúp `deploy/Chuyen-len-VPS.command`, rồi nhập IP, user, tên miền và repo Obsidian.
   - Mật khẩu VPS anh tự gõ trong Terminal; không đi qua đâu khác.
   - Script đóng gói `.env`, `credentials.json`, `data/` và kho Obsidian, chép lên VPS qua SSH, chạy `setup_vps.sh`, rồi nhập dữ liệu.
2. **DNS:** tạo bản ghi `A`: `<tên miền>` → `<IP VPS>`. Caddy tự lấy chứng chỉ HTTPS.
3. **GitHub › repo code › Settings › Secrets and variables › Actions:**
   - Secrets:
     - `VPS_HOST`: IP của VPS
     - `VPS_USER`: `superhuy`
     - `VPS_SSH_KEY`: khoá riêng do `setup_vps.sh` in ra
     - `VPS_PORT`: chỉ cần khi cổng SSH khác 22
   - Secrets cho giám sát: `TELEGRAM_TOKEN`, `OWNER_CHAT_ID` (giống trong `.env`)
   - Variables: `APP_URL` = `https://<tên miền>`
4. **Repo Obsidian › Settings › Deploy keys › Add:** dán khoá công khai do script in ra, tick **Allow write access**.
5. **Lark Developer Console › Security › Redirect URLs:** thêm `https://<tên miền>/lark/callback`. Chỉ cần khi kết nối lại Lark.
6. **Tắt bot trên Mac** để không tranh tin nhắn Telegram với VPS. Tạo file `data/DISABLED` trong thư mục bot trên Mac, rồi khởi động lại bot (`touch data/restart.flag`). Bot trên Mac sẽ đứng yên. Bật lại thì xoá file đó.
7. **Chạy triển khai:** GitHub › Actions › "Kiểm tra & triển khai" › Run workflow (hoặc đẩy một commit lên `main`).

## Vận hành

| Việc | Lệnh trên VPS |
|---|---|
| Trạng thái | `sudo systemctl status superhuy` |
| Xem log trực tiếp | `journalctl -u superhuy -f` (hoặc `tail -f /opt/superhuy/shared/data/agent.log`) |
| Khởi động lại | `sudo systemctl restart superhuy` (hoặc `touch /opt/superhuy/shared/data/restart.flag`) |
| Quay về bản trước | `ls -dt /opt/superhuy/releases/*` rồi `ln -sfn <thư mục> /opt/superhuy/current && sudo systemctl restart superhuy` |
| Sửa khoá | `sudo -u superhuy nano /opt/superhuy/shared/.env` rồi khởi động lại |

## Obsidian khi bot chạy trên VPS

- Bot ghi ghi chú vào `/opt/superhuy/shared/vault`. Cứ 10 phút, bot commit, kéo thay đổi mới về rồi đẩy lên repo vault (`VAULT_GIT_REMOTE`).
- Trên VPS, file âm thanh cuộc họp **không** đẩy vào vault (`OBSIDIAN_EMBED_AUDIO=0`); nghe lại trong superHuy › Họp.
- **Trên Mac:**
  - đổi tên thư mục `~/SecondBrain` cũ để giữ làm bản lưu;
  - `git clone <repo vault> ~/SecondBrain`, mở bằng Obsidian;
  - cài plugin cộng đồng **Obsidian Git** và bật tự động pull/push, ví dụ 10 phút một lần.

## Second Brain và chia sẻ biên bản họp

- **Second Brain:** mỗi khi trả lời (Telegram hoặc app), superHuy tra các ghi chú Obsidian liên quan và đưa vào ngữ cảnh. Tìm kiếm không phân biệt dấu, ưu tiên ghi chú anh tự viết.
- **Ghi chú `02 Areas/superHuy/superHuy hieu ve anh.md`:** superHuy tự cập nhật. Những dòng anh viết dưới mục **Anh bổ sung** được superHuy đọc ngược lại mỗi lần trả lời.
- **`02 Areas/<Tổ chức>/Nhat ky quyet dinh.md`:** nhật ký quyết định, tích luỹ qua mọi cuộc họp.
- **Chia sẻ biên bản họp:** trang công khai `https://<tên miền>/s/<mã>` là bản chụp lúc tạo.
  - Có hạn dùng và thu hồi được. Dữ liệu lưu ở `shared/data/meetings/shares.json`.
  - Nginx/Caddy chỉ cần chuyển mọi đường dẫn về cổng 8787, như hiện tại.
