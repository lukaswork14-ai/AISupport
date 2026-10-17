"""Cấu hình trung tâm: đọc từ file .env (không bao giờ ghi khóa vào code)."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
# Trên VPS: code nằm ở /opt/superhuy/current (đổi mỗi lần triển khai), còn .env + data ở SUPERHUY_HOME (giữ nguyên).
HOME_DIR = Path(os.getenv("SUPERHUY_HOME", str(BASE_DIR))).expanduser()
load_dotenv(HOME_DIR / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OWNER_CHAT_ID = int(os.getenv("OWNER_CHAT_ID", "0") or 0)
# Khóa LLM qua OpenRouter (giao thức OpenAI-compatible)
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "~deepseek/deepseek-v4-flash-latest")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Ho_Chi_Minh")

# Link ICS của Lark / Apple (iCloud) / bất kỳ lịch nào, ngăn cách bằng dấu phẩy
ICS_URLS = [u.strip() for u in os.getenv("ICS_URLS", "").split(",") if u.strip()]

# Giờ gửi nhắc lịch (mặc định 21:00) và chu kỳ tổng hợp email (giờ)
REMINDER_HOUR = int(os.getenv("REMINDER_HOUR", "21"))
NEWS_HOUR = int(os.getenv("NEWS_HOUR", "8"))          # giờ gửi Top 5 tin mỗi sáng
CARD_HANDLE = os.getenv("CARD_HANDLE", "")             # tên/handle in góc thẻ ảnh, ví dụ @tencuaban
EMAIL_DIGEST_EVERY_HOURS = int(os.getenv("EMAIL_DIGEST_EVERY_HOURS", "1"))  # (cũ, không còn dùng)
# Lịch tự động (khi không bấm): Lark theo các khung giờ, email 1 phiên buổi tối. Bấm trong app = cập nhật ngay.
LARK_DIGEST_HOURS = os.getenv("LARK_DIGEST_HOURS", "9,11,14,16,18,21")
EMAIL_DIGEST_HOURS = os.getenv("EMAIL_DIGEST_HOURS", "21")

DATA_DIR = HOME_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# superYou: instance của khách (tenant, xem deploy/tenant_vps.sh). Trên instance khách, KHÔNG gieo dữ liệu/khoá học/chiến lược
# viết riêng cho anh Huy (Roimaxx, Leversphere, Sellnity). Nhận diện bằng SUPERYOU_TENANT=1 hoặc thư mục /superyou-tenants/.
# Gói của instance này (tenant: pro|business|enterprise do chủ sàn cài; instance chính: enterprise). Xem core/plans.py.
SUPERYOU_PLAN = (os.getenv("SUPERYOU_PLAN", "").strip().lower() or "")
IS_TENANT = (os.getenv("SUPERYOU_TENANT", "").strip().lower() in ("1", "true", "yes")
             or "/superyou-tenants/" in HOME_DIR.as_posix())
GOOGLE_CREDENTIALS_FILE = HOME_DIR / "credentials.json"   # tải từ Google Cloud
GOOGLE_TOKEN_FILE = DATA_DIR / "google_token.json"        # tự sinh sau khi cấp quyền
STATE_FILE = DATA_DIR / "state.json"


def home_file(name: str) -> Path:
    """File cấu hình người dùng sửa được (targets.json, style_guide.md): nằm ở SUPERHUY_HOME để không mất khi triển khai bản mới.
    Lần đầu chưa có thì chép bản mặc định từ thư mục code."""
    p = HOME_DIR / name
    if not p.exists() and (BASE_DIR / name).exists() and HOME_DIR != BASE_DIR:
        import shutil
        shutil.copy2(BASE_DIR / name, p)
    return p


def require_config():
    missing = [k for k, v in {
        "TELEGRAM_TOKEN": TELEGRAM_TOKEN,
        "OWNER_CHAT_ID": OWNER_CHAT_ID,
        "LLM_API_KEY": LLM_API_KEY,
    }.items() if not v]
    if missing:
        raise SystemExit(
            "Thiếu cấu hình: " + ", ".join(missing) +
            ". Hãy chạy lại trình cài đặt: python setup.py"
        )

# Obsidian second brain: thư mục vault (tự tạo). Mở Obsidian > "Open folder as vault" > chọn thư mục này.
OBSIDIAN_VAULT = Path(os.getenv("OBSIDIAN_VAULT", str(Path.home() / "SecondBrain"))).expanduser()
