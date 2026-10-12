"""Kết nối Facebook Page: nhận User Access Token (bạn dán vào bot / Mini App), tự đổi sang token dài hạn
(nếu có FB_APP_ID + FB_APP_SECRET), lấy Page token của các page bạn quản lý và ghi vào .env (FB_PAGES).
Token không bao giờ được in ra log hay gửi lại chat."""
import json
import os
import re

import requests

from config import HOME_DIR, home_file

GRAPH = "https://graph.facebook.com/v21.0"
ENV = HOME_DIR / ".env"
TARGETS = home_file("targets.json")


def _get(path, **params):
    r = requests.get(f"{GRAPH}/{path}", params=params, timeout=30)
    d = r.json() if r.content else {}
    if r.status_code >= 400 or "error" in d:
        raise RuntimeError(d.get("error", {}).get("message", f"HTTP {r.status_code}"))
    return d


def _set_env(key: str, value: str):
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    lines = [l for l in lines if not l.startswith(key + "=")]
    lines.append(f"{key}={value}")
    ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(ENV, 0o600)
    os.environ[key] = value


def connect(user_token: str) -> dict:
    tok = user_token.strip()
    if not re.fullmatch(r"[A-Za-z0-9_\-|.]{40,}", tok):
        raise ValueError("Token không đúng định dạng (cần User Access Token từ Graph API Explorer).")
    long_lived = False
    app_id, secret = os.getenv("FB_APP_ID", ""), os.getenv("FB_APP_SECRET", "")
    if app_id and secret:
        d = _get("oauth/access_token", grant_type="fb_exchange_token", client_id=app_id,
                 client_secret=secret, fb_exchange_token=tok)
        tok, long_lived = d["access_token"], True
    pages = _get("me/accounts", fields="name,id,access_token,username,link", limit=100, access_token=tok).get("data", [])
    if not pages:
        raise RuntimeError("Token hợp lệ nhưng không thấy Page nào. Khi lấy token cần tick quyền pages_show_list, "
                           "pages_manage_posts, pages_read_engagement và chọn Page EFE Network.")
    clean = [p for p in pages if p.get("access_token")]
    _set_env("FB_PAGES", ";".join(f"{p['name'].replace('|', ' ').replace(';', ' ')}|{p['id']}|{p['access_token']}" for p in clean))
    # khớp nơi đăng loại page trong targets.json với page thật (theo username trong URL hoặc tên)
    matched = []
    try:
        targets = json.loads(TARGETS.read_text(encoding="utf-8"))
        for t in targets:
            if t.get("type") != "page":
                continue
            slug = t.get("url", "").rstrip("/").rsplit("/", 1)[-1].lower()
            for p in clean:
                if slug and (slug == (p.get("username") or "").lower() or slug in (p.get("link") or "").lower()
                             or slug == p["name"].replace(" ", "").lower()) or t.get("fb_page", "").lower() == p["name"].lower():
                    t["fb_page"] = p["name"]
                    matched.append(f"{t['name']} → {p['name']}")
                    break
        TARGETS.write_text(json.dumps(targets, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass
    names = ", ".join(p["name"] for p in clean)
    note = ("Token Page dài hạn (không hết hạn trừ khi bạn đổi mật khẩu/gỡ quyền)." if long_lived else
            "Token Page này hết hạn sau ~1-2 giờ. Muốn dài hạn: thêm FB_APP_ID và FB_APP_SECRET vào .env rồi kết nối lại.")
    return {"text": f"✅ Đã kết nối {len(clean)} Page: {names}\n" +
                    ("Nơi đăng tự động: " + "; ".join(matched) + "\n" if matched else "⚠️ Chưa khớp được Page EFE Network trong targets.json.\n") + note}
