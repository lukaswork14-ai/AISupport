"""Kiểm tra kết nối Lịch Lark + Lark Mail trên VPS (kết quả được mã hoá trước khi ghi ra)."""
import os, socket, sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa
from agents import lark_oauth, lark_calendar, lark_agent  # noqa
print("lark_app_ready:", lark_agent.ready())
print("redirect_uri:", lark_oauth.redirect_uri())
print("base_url:", lark_oauth.base_url())
print("accounts:", lark_oauth._accounts(), "api:", lark_oauth._api())
print("authorize_url:", lark_oauth.authorize_url(lark_oauth.new_state("calendar"), lark_calendar.SCOPES, lark_oauth.redirect_uri()))
for host, port in (("smtp.larksuite.com", 465), ("smtp.larksuite.com", 587), ("imap.larksuite.com", 993), ("smtp.gmail.com", 465), ("imap.gmail.com", 993)):
    try:
        s = socket.create_connection((host, port), timeout=8); s.close(); print("tcp", host, port, "OK")
    except Exception as e:
        print("tcp", host, port, "FAIL", type(e).__name__, e)
print("lark_mail_address_set:", bool(os.getenv("LARK_MAIL_ADDRESS")), "pw_set:", bool(os.getenv("LARK_MAIL_PASSWORD")))
try:
    import requests
    r = requests.post(f"{lark_oauth._api()}/open-apis/auth/v3/app_access_token/internal",
                      json={"app_id": os.getenv("LARK_APP_ID", ""), "app_secret": os.getenv("LARK_APP_SECRET", "")}, timeout=15).json()
    tok = r.get("app_access_token", "")
    # thông tin ứng dụng: redirect đã đăng ký (nếu API cho phép)
    a = requests.get(f"{lark_oauth._api()}/open-apis/application/v6/applications/{os.getenv('LARK_APP_ID','')}",
                     params={"lang": "en_us"}, headers={"Authorization": f"Bearer {tok}"}, timeout=15).json()
    app = (a.get("data") or {}).get("app") or {}
    print("app_info_code:", a.get("code"), a.get("msg"), "| name:", app.get("app_name"), "| scopes:", [s.get("scope") for s in (app.get("scopes") or [])][:40])
except Exception as e:
    print("app_info err", e)
