"""Đăng nhập Lark 1 lần (OAuth) để bot TỰ THÊM CHÍNH NÓ vào mọi group có chủ nhân.
Token người dùng chỉ dùng trong bộ nhớ cho lần chạy đó, không lưu, không in ra."""
import json
import logging
import os
import secrets
import time
import urllib.parse

import requests

from config import DATA_DIR

log = logging.getLogger("lark-oauth")
SCOPES = "im:chat:readonly im:chat.members:write_only"
_states: dict[str, float] = {}
RESULT_FILE = DATA_DIR / "lark_join_result.json"


def _api() -> str:
    return os.getenv("LARK_DOMAIN", "https://open.larksuite.com").rstrip("/")


def _accounts() -> str:
    return "https://accounts.feishu.cn" if "feishu" in _api() else "https://accounts.larksuite.com"


def base_url() -> str:
    fixed = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
    if fixed:  # chạy trên VPS có tên miền riêng
        return fixed
    try:
        return json.loads((DATA_DIR / "tunnel.json").read_text())["url"].rstrip("/")
    except Exception:
        return os.getenv("WEBAPP_URL", "").rstrip("/")


def redirect_uri() -> str:
    return base_url() + "/lark/callback"


STATE_FILE = DATA_DIR / "lark_states.json"  # lưu ra file để mọi tiến trình dùng chung


def _load_states() -> dict:
    try:
        raw = json.loads(STATE_FILE.read_text())
    except Exception:
        return {}
    out = {}
    for k, v in raw.items():
        v = v if isinstance(v, dict) else {"exp": v, "p": "join"}
        if v["exp"] > time.time():
            out[k] = v
    return out


def new_state(purpose: str = "join") -> str:
    s = secrets.token_urlsafe(16)
    st = _load_states()
    st[s] = {"exp": time.time() + 900, "p": purpose}
    STATE_FILE.write_text(json.dumps(st))
    return s


LOCAL_REDIRECT = f"http://127.0.0.1:{os.getenv('WEBAPP_PORT', '8787')}/lark/callback"  # cố định, không phụ thuộc đường hầm


def authorize_url(state: str, scope: str = SCOPES, redirect: str | None = None) -> str:
    q = {"client_id": os.getenv("LARK_APP_ID", ""), "app_id": os.getenv("LARK_APP_ID", ""), "response_type": "code",
         "redirect_uri": redirect or redirect_uri(), "scope": scope, "state": state}
    return f"{_accounts()}/open-apis/authen/v1/authorize?" + urllib.parse.urlencode(q)


def check_state(s: str) -> str:
    """Trả về mục đích ('join' | 'calendar') nếu state hợp lệ, '' nếu không."""
    st = _load_states()
    v = st.pop(s, None)
    STATE_FILE.write_text(json.dumps(st))
    return v["p"] if v else ""


def _user_token(code: str) -> str:
    app_id, secret = os.getenv("LARK_APP_ID", ""), os.getenv("LARK_APP_SECRET", "")
    r = requests.post(f"{_api()}/open-apis/authen/v2/oauth/token", timeout=30, json={
        "grant_type": "authorization_code", "client_id": app_id, "client_secret": secret,
        "code": code, "redirect_uri": redirect_uri()})
    d = r.json()
    if d.get("access_token"):
        return d["access_token"]
    # cách cũ (v1)
    from agents import lark_agent
    r = requests.post(f"{_api()}/open-apis/authen/v1/oidc/access_token", timeout=30,
                      headers={"Authorization": f"Bearer {lark_agent._app_token()}"},
                      json={"grant_type": "authorization_code", "code": code})
    d1 = r.json()
    if d1.get("code") == 0:
        return d1["data"]["access_token"]
    raise RuntimeError(f"Lark không cấp quyền: {d.get('error_description') or d.get('msg') or d1.get('msg')}")


def join_all(code: str) -> dict:
    """Đổi code lấy token người dùng, liệt kê mọi group của chủ nhân, thêm bot vào từng group."""
    tok = _user_token(code)
    h = {"Authorization": f"Bearer {tok}"}
    chats, page = [], None
    while True:
        p = {"page_size": 100, **({"page_token": page} if page else {})}
        d = requests.get(f"{_api()}/open-apis/im/v1/chats", headers=h, params=p, timeout=30).json()
        if d.get("code") != 0:
            raise RuntimeError(f"Không lấy được danh sách group: {d.get('msg')}")
        chats += d["data"].get("items", [])
        if not d["data"].get("has_more"):
            break
        page = d["data"].get("page_token")
    app_id = os.getenv("LARK_APP_ID", "")
    ok, fail = [], []
    for c in chats:
        r = requests.post(f"{_api()}/open-apis/im/v1/chats/{c['chat_id']}/members", headers=h, timeout=30,
                          params={"member_id_type": "app_id"}, json={"id_list": [app_id]}).json()
        name = c.get("name") or "(không tên)"
        if r.get("code") == 0 and not (r.get("data", {}).get("invalid_id_list") or []):
            ok.append(name)
        else:
            fail.append({"name": name, "reason": r.get("msg") or "không thêm được"})
        time.sleep(0.2)
    res = {"total": len(chats), "ok": ok, "fail": fail, "at": time.strftime("%Y-%m-%d %H:%M")}
    RESULT_FILE.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def summary(res: dict) -> str:
    lines = [f"✅ Đã thêm bot vào {len(res['ok'])}/{res['total']} group Lark."]
    if res["fail"]:
        lines.append(f"⚠️ {len(res['fail'])} group không thêm được (thường do group chỉ cho chủ/quản trị thêm thành viên):")
        lines += [f"• {f['name']}: {f['reason']}" for f in res["fail"][:20]]
    return "\n".join(lines)
