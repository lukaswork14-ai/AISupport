"""Kết nối Google (Gmail + Calendar) bằng OAuth cho ứng dụng máy tính.

Chạy một lần:  python google_auth.py
Trình duyệt sẽ mở ra để BẠN bấm "Cho phép". Token lưu cục bộ trong data/.
Chỉ xin quyền ĐỌC (readonly): bot không thể gửi/xóa email hay sửa lịch.
"""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_TOKEN_FILE

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]


def get_credentials() -> Credentials:
    creds = None
    if GOOGLE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        GOOGLE_TOKEN_FILE.write_text(creds.to_json())
        return creds
    raise RuntimeError("Chưa kết nối Google. Hãy chạy: python google_auth.py")


def run_flow():
    if not GOOGLE_CREDENTIALS_FILE.exists():
        raise SystemExit(
            "Không thấy credentials.json. Làm theo README (mục Google) để tải file này "
            "từ Google Cloud Console và đặt vào thư mục ứng dụng."
        )
    flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")
    GOOGLE_TOKEN_FILE.write_text(creds.to_json())
    print("Đã kết nối Google thành công.")


if __name__ == "__main__":
    run_flow()
