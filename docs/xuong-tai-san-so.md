# Xưởng Tài sản số superYou (thay Xưởng clone)

Anh Huy duyệt ngày 17/10/2026. Chủ mảng: session "Xưởng Tài sản số" (phòng Product). Chợ, xếp hạng, mua bán thuộc session Thương mại & Marketplace.

## 1. Chỉ làm tài sản giúp người dùng giỏi lên theo thời gian

Bỏ quét app iOS/Mac/web/Product Hunt. Xưởng chỉ làm 3 loại, xếp theo hai trục **ngành** và **vai trò**:

| Loại | Là gì | Cài vào superYou |
|---|---|---|
| **Skill** | Cách làm một việc cụ thể (`content.skill`) | Trợ lý áp dụng ngay khi trả lời |
| **Second Brain** | Gói tri thức chuyên ngành (`content.notes`) | Ghi chú vào Obsidian, trợ lý tra cứu khi trả lời |
| **OS theo vai trò** | Skill + workflow + tri thức đóng thành một bộ (`type="pack"`, ví dụ "OS Trưởng phòng Kinh doanh", "OS Chủ shop TMĐT") | Một chạm: skill áp dụng, workflow chạy theo lịch, ghi chú vào Second Brain |

Ngành (`industry`): tmdt-pod, ban-le, luat, tai-chinh-ke-toan, marketing-agency, giao-duc, bat-dong-san, san-xuat, dich-vu, khac.
Vai trò (`role`): ceo-chu-dn, quan-ly, sales, marketing, van-hanh, tai-chinh, nhan-su, solopreneur, chuyen-vien.

**Điểm nguồn (0–100), dưới 60 không vào xưởng:** tăng năng suất ngay (30) · làm Second Brain thông minh dần (25) · cài một chạm vào superYou (20) · giấy phép cho phép làm lại (25, giấy phép không rõ = 0 và loại ngay).

**Nguồn:** kho skill/prompt mã nguồn mở (GitHub, Hugging Face), kho template Obsidian/Notion công khai, khung làm việc nổi tiếng theo vai trò (OKR, EOS, 4DX, sales playbook...), sản phẩm đang bán chạy trên chính chợ (để làm bản theo ngành khác), tri thức nội bộ anh Huy cho phép dùng.

Cách hiện thực (`agents/factory.py`, 17/10/2026): bốn nguồn trong giao diện `github` (tìm theo topic prompts / agent-skills / system-prompts, đọc trường `license` từ API), `template` (topic obsidian-template / obsidian-vault / notion-template / second-brain), `framework` (danh sách khung công khai cài sẵn, có cờ `trademark` để Kiểm duyệt chặn dùng tên nhãn hiệu làm tên sản phẩm), `market` (sản phẩm chính chủ đã bán trên chợ; sản phẩm của người tạo khác coi là không rõ giấy phép). Giấy phép cho phép làm lại: MIT, Apache-2.0, CC-BY-4.0, CC0-1.0, BSD-2/3-Clause, Unlicense; `NOASSERTION` hoặc trống = loại. Điểm 4 tiêu chí chấm bằng luật (từ khoá, ngôn ngữ repo, độ phổ biến), không gọi AI nên quét nhanh và không tốn phí; ngành/vai trò đoán bằng từ khoá, PO sẽ chốt lại ở bước 2. Repo mã nguồn (ngôn ngữ lập trình) bị trừ ở "cài một chạm" vì phải rút văn bản ra rồi viết lại. Tuỳ chọn `GITHUB_TOKEN` trong `.env` nâng hạn mức tìm kiếm GitHub (không bắt buộc).

## 2. Quy trình clone có cải tiến: anh bấm 2 lần

Anh bấm **Clone** trên một nguồn đã chấm điểm. Đội AI chạy tuần tự, mỗi vai giao kết quả cho vai sau; kết quả từng vai lưu trong dự án (`data/factory/projects`), anh xem được từng bước và bấm **Sửa** để gửi lại đúng vai đó.

| Bước | Vai | Đầu ra bắt buộc |
|---|---|---|
| 1 | **BA** | Tính năng, tình huống dùng, ai cần, điểm yếu của bản gốc, 5 câu hỏi mẫu người dùng sẽ hỏi |
| 2 | **PO** | Định vị 1 câu, ngành + vai trò, 3–5 cải tiến so với bản gốc và 2 sản phẩm tương tự, giá đề xuất (`pay.price_reco`), gói tối thiểu |
| 3 | **Dev** | Viết lại hoàn toàn theo chuẩn superYou (`market._validate`), không chép nguyên văn, workflow chỉ đọc và tổng hợp (`market._step_ok`), có `examples` |
| 4 | **Designer** | Tên, tagline, mô tả theo mẫu chợ, icon màu, thumbnail, 3–5 ảnh chụp sản phẩm đang chạy thật trong superYou (Playwright, bản QA) |
| 5 | **Tester** | Đóng vai 2–3 người dùng thật của ngành, hỏi 5 câu mẫu của BA, chấm 0–100 theo: đúng việc, dễ hiểu, có số liệu/hành động, không bịa. Dưới 75 → trả về Dev kèm lý do, tối đa 2 vòng |
| 6 | **Kiểm duyệt** | Giấy phép nguồn, độ trùng với bản gốc (<30% câu trùng), không mang thương hiệu/tên người khác, không lộ dữ liệu riêng của anh Huy, không hành động gửi/đăng/xoá |

Kết thúc: **thẻ duyệt** trong HQ › Xưởng: điểm test, danh sách cải tiến, giá đề xuất, ảnh, kết luận kiểm duyệt. Anh bấm **Publish** → `market.approve_publish` → lên chợ đúng loại, ngành, vai trò. Mọi thứ trước nút Publish là bản nháp, chưa ai thấy.

## 3. Xếp hạng trên chợ (session Thương mại làm)

Điểm xếp hạng mỗi sản phẩm, tính lại mỗi giờ và lưu vào listing (`rank_score`, `rank_parts`):

- **Đánh giá:** trung bình Bayes `(C·m + Σsao) / (C + n)` với m = trung bình toàn chợ, C = 5; chỉ tính đánh giá của người đã mua hoặc đã cài (`reviews[].verified`).
- **Tăng trưởng:** lượt cài 7 ngày và 30 ngày (log để sản phẩm lớn không át hết).
- **Giữ chân:** tỷ lệ còn bật sau 7 ngày (`installs` còn `enabled`), trọng số cao nhất.
- **Trừ:** hoàn tiền, khiếu nại trong 30 ngày.
- **Cộng:** mới lên kệ trong 14 ngày.

Bảng sinh ra: Nổi bật (chủ sàn ghim + điểm), Bán chạy (30 ngày), Đang lên (7 ngày), Mới, Top theo ngành / vai trò. Hiển thị trên /market, trong app và HQ.

## Sở hữu file

| Đường dẫn | Chủ |
|---|---|
| `agents/factory.py`, `agents/factory_team.py` (đội BA/PO/Dev/Designer/Tester/Kiểm duyệt), `webapp/app/js/25-factory.js`, `webapp/app/css/45-factory.css`, `deploy/factory_qa.py`, mục Xưởng trong `hubs/commerce.py` (khối `register(Agent("xuong"...`), tài liệu này | Xưởng Tài sản số |
| `agents/market.py` (xếp hạng, danh mục ngành/vai trò, `approve_publish`), `agents/pay.py`, giao diện chợ | Thương mại & Marketplace |

Xưởng bàn giao cho chợ bằng đúng cấu trúc listing hiện có (`market._mk`), thêm các trường `industry`, `role`, `shots` (ảnh), `cloned_from`, `source_url`, `license`.
