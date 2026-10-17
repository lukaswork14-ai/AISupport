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

## Nguồn tri thức: Gemini Notebook

- Google chưa có API chính thức cho tài khoản cá nhân. superHuy dùng thư viện mã nguồn mở `notebooklm-py` với phiên đăng nhập Google của anh.
- **Kết nối:**
  1. Vào app › Second Brain › Gemini Notebook › **Kết nối** để lấy mã 8 ký tự.
  2. Trên Mac, bấm đúp `deploy/Ket-noi-Gemini-Notebook.command`, đăng nhập Google trong Chrome, rồi dán mã.
  3. Phiên được lưu ở `shared/notebooklm/storage_state.json` (quyền 600). Nếu phiên hết hạn, superHuy báo; anh chạy lại script.
- **Dữ liệu nạp về:**
  - Mỗi 6 giờ superHuy nạp tóm tắt, ghi chú và toàn văn các nguồn vào `shared/data/knowledge/gemini/`. superHuy tra cứu ở đây khi trả lời.
  - Mỗi notebook có thêm một ghi chú mục lục trong Obsidian: `03 Resources/Gemini Notebook/`.
- **Thêm nguồn mới:** khai báo trong `agents/knowledge_sources.py` và ghi `.md` vào `data/knowledge/<nguồn>/`.

## Staging: xem trước nhánh PR trước khi gộp

Staging là một dịch vụ thứ hai `superhuy-staging` trên cùng VPS. Nó tách hẳn khỏi bản chính: mã, venv, dữ liệu (`/opt/superhuy-staging/shared`), `.env`, bot Telegram và cổng (8790) đều riêng. Staging không đẩy ghi chú vào vault thật và không đụng `/opt/superhuy`.

**Cài một lần (root):**

1. DNS: bản ghi `A staging.roimaxxhub.com` → IP VPS.
2. `sudo bash deploy/staging_vps.sh staging.roimaxxhub.com`
3. Tạo một bot Telegram **thử** qua BotFather. Anh tự điền token của bot đó vào `/opt/superhuy-staging/shared/.env` (cùng `OWNER_CHAT_ID`, `LLM_API_KEY`). Không dùng chung token với superHuy chính, nếu không hai bot sẽ tranh tin nhắn. Muốn xem giao diện khách superYou thì đặt `SUPERYOU_TENANT=1`.

**Mỗi lần xem trước:** GitHub › Actions › **Triển khai staging** › Run workflow, nhập tên nhánh. Workflow chạy test + gitleaks, chép nhánh lên, khởi động lại staging và chờ `/health`. Diag hiện dòng `staging:` (trạng thái + nhánh đang chạy).

| Việc | Lệnh trên VPS |
|---|---|
| Trạng thái | `systemctl status superhuy-staging` |
| Tạm tắt (đỡ RAM) | `sudo systemctl stop superhuy-staging` |
| Log | `journalctl -u superhuy-staging -f` |

Giới hạn: `MemoryMax=600M`, `CPUQuota=60%`, nên staging không làm chậm bản chính.
