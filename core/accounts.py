"""Tài khoản, vai trò và gói của superYou (một cửa đăng nhập, chuyển vai như Facebook).

Vai trò (một tài khoản có thể có nhiều vai, chọn vai đang dùng):
- owner   : chủ sàn (anh Huy): HQ, superHuy, Marketplace quản trị, Xưởng clone. Đăng nhập bằng PIN hoặc passkey (không mật khẩu).
- seller  : người bán trên Marketplace: console người bán.
- member  : người dùng thường (free/trial/pro/business): trung tâm tài khoản, mua và tải sản phẩm, hồ sơ, gói; khi có superYou riêng thì mở app.

Gói (plan): free | trial | pro | business | enterprise — ma trận quyền ở core/plans.py.

Mật khẩu băm scrypt (hashlib), không lưu mật khẩu thô; đăng nhập sai nhiều lần bị khoá tạm; phiên tách theo vai.
Dữ liệu: DATA_DIR/accounts.json {users: {uid: {...}}, by_email: {}, audit: []}.
"""
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time

from config import DATA_DIR, OWNER_CHAT_ID

FILE = DATA_DIR / "accounts.json"
_LOCK = threading.Lock()
ROLES = {"owner": "Chủ sàn", "seller": "Người bán", "member": "Người dùng"}
EMAIL_RE = re.compile(r"^[^@\s<>]{1,64}@[^@\s<>]{1,190}\.[A-Za-z]{2,24}$")
_FAILS: dict[str, list[float]] = {}


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("users", {})
    d.setdefault("audit", [])
    oid = f"u{OWNER_CHAT_ID}"
    if oid not in d["users"]:
        d["users"][oid] = {"id": oid, "email": "", "name": "Huy", "roles": ["owner", "seller", "member"], "plan": "enterprise", "status": "active",
                           "created": _now(), "last_login": "", "last_role": "owner", "owner": True}
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)
    try:
        os.chmod(FILE, 0o600)
    except Exception:
        pass


def _hash(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return salt.hex() + "$" + h.hex()


def _check(pw: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
        return hmac.compare_digest(hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt), n=2 ** 14, r=8, p=1, dklen=32).hex(), h)
    except Exception:
        return False


def audit(d: dict, who: str, what: str, meta: str = ""):
    d["audit"].append({"at": _now(), "who": who, "what": what[:160], "meta": meta[:200]})
    d["audit"] = d["audit"][-2000:]


def _pub(u: dict) -> dict:
    return {k: u.get(k) for k in ("id", "email", "name", "roles", "plan", "status", "created", "last_login", "last_role", "company", "title", "trial_until")}


# ------------------------------------------------------------------ đăng ký, đăng nhập
def _throttle(key: str) -> bool:
    now = time.time()
    xs = [t for t in _FAILS.get(key, []) if t > now - 900]
    _FAILS[key] = xs
    return len(xs) >= 8


def _fail(key: str):
    _FAILS.setdefault(key, []).append(time.time())


def signup(email: str, password: str, name: str, role: str = "member", company: str = "", plan: str = "free") -> dict:
    from core import plans
    email = (email or "").strip().lower()[:254]
    if not EMAIL_RE.match(email):
        raise ValueError("Email chưa đúng")
    if len(password or "") < 8:
        raise ValueError("Mật khẩu cần ít nhất 8 ký tự")
    name = (name or "").strip()[:60]
    if len(name) < 2:
        raise ValueError("Cần tên hiển thị")
    role = role if role in ("member", "seller") else "member"
    with _LOCK:
        d = _load()
        if any(u.get("email") == email for u in d["users"].values()):
            raise ValueError("Email này đã có tài khoản. Hãy đăng nhập.")
        if len(d["users"]) >= 50000:
            raise ValueError("Tạm dừng nhận đăng ký mới")
        uid = "m" + secrets.token_hex(5)
        plan = plan if plan in plans.PLANS and plan not in ("enterprise",) else "free"
        u = {"id": uid, "email": email, "name": name, "pw": _hash(password), "roles": list(dict.fromkeys(["member", role])), "plan": plan,
             "status": "active", "created": _now(), "last_login": "", "last_role": role, "company": (company or "").strip()[:80]}
        if plan == "trial":
            u["trial_until"] = (dt.date.today() + dt.timedelta(days=plans.TRIAL_DAYS)).isoformat()
        d["users"][uid] = u
        audit(d, email, "Đăng ký", role)
        _save(d)
    if role == "seller":
        _link_seller(u)
    try:
        from agents import leads
        leads.add(email, "account:signup", "Tài khoản " + ROLES[role])
    except Exception:
        pass
    try:
        from core import security
        security.alert_once(f"acc:{uid}", f"👤 Tài khoản mới: {name} ({email}) · {ROLES[role]} · gói {plan}.", every=10**9)
    except Exception:
        pass
    return {"user": _pub(u)}


def _link_seller(u: dict):
    """Người bán đăng ký bằng tài khoản -> tạo hồ sơ người tạo trong Marketplace (không cần khoá riêng)."""
    try:
        from agents import market
        with market._LOCK:
            d = market._ensure(market._load())
            if not any(c.get("email") == u["email"] for c in d["creators"].values()):
                cid = "c" + secrets.token_hex(5)
                d["creators"][cid] = {"id": cid, "name": u["name"], "handle": market._slug(u["name"])[:30], "email": u["email"], "bio": "",
                                      "key_hash": "", "status": "active", "created": _now(), "ai_uses": {}, "account": u["id"]}
                market._save(d)
    except Exception:
        pass


def login(email: str, password: str, ip: str = "") -> dict:
    email = (email or "").strip().lower()
    key = f"{ip}|{email}"
    if _throttle(key):
        raise PermissionError("Sai quá nhiều lần. Thử lại sau 15 phút.")
    with _LOCK:
        d = _load()
        u = next((x for x in d["users"].values() if x.get("email") == email), None)
        if not u or not u.get("pw") or not _check(password or "", u["pw"]):
            _fail(key)
            raise PermissionError("Email hoặc mật khẩu không đúng")
        if u.get("status") == "suspended":
            raise PermissionError("Tài khoản đang bị tạm khoá. Liên hệ superYou.")
        u["last_login"] = _now()
        audit(d, email, "Đăng nhập")
        _save(d)
    return {"user": _pub(u)}


def owner_user() -> dict:
    d = _load()
    return _pub(d["users"][f"u{OWNER_CHAT_ID}"])


def get(uid: str) -> dict | None:
    u = _load()["users"].get(uid)
    return _pub(u) if u else None


def by_email(email: str) -> dict | None:
    u = next((x for x in _load()["users"].values() if x.get("email") == (email or "").strip().lower()), None)
    return _pub(u) if u else None


def set_password(uid: str, old: str, new: str) -> dict:
    if len(new or "") < 8:
        raise ValueError("Mật khẩu mới cần ít nhất 8 ký tự")
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if not u:
            raise ValueError("Không tìm thấy tài khoản")
        if u.get("pw") and not _check(old or "", u["pw"]):
            raise ValueError("Mật khẩu hiện tại không đúng")
        u["pw"] = _hash(new)
        audit(d, u.get("email") or uid, "Đổi mật khẩu")
        _save(d)
    return {"text": "Đã đổi mật khẩu."}


def update_profile(uid: str, name: str = "", company: str = "", title: str = "") -> dict:
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if not u:
            raise ValueError("Không tìm thấy tài khoản")
        if name:
            u["name"] = name.strip()[:60]
        if company:
            u["company"] = company.strip()[:80]
        if title:
            u["title"] = title.strip()[:60]
        _save(d)
    return {"text": "Đã lưu.", "user": _pub(u)}


def set_last_role(uid: str, role: str):
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if u and role in u.get("roles", []):
            u["last_role"] = role
            _save(d)


def add_role(uid: str, role: str) -> dict:
    """Người dùng tự thêm vai Người bán (như Facebook tạo Page)."""
    if role != "seller":
        raise ValueError("Chỉ tự thêm được vai Người bán")
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if not u:
            raise ValueError("Không tìm thấy tài khoản")
        if role not in u["roles"]:
            u["roles"].append(role)
            audit(d, u.get("email") or uid, "Thêm vai", role)
            _save(d)
    _link_seller(u)
    return {"text": "Đã mở vai Người bán. Chuyển vai ở góc trên để vào console.", "user": _pub(u)}


def seller_creator(uid: str) -> dict | None:
    """Hồ sơ người tạo Marketplace gắn với tài khoản (để console dùng phiên tài khoản thay khoá)."""
    u = _load()["users"].get(uid)
    if not u or "seller" not in u.get("roles", []):
        return None
    try:
        from agents import market
        d = market._load()
        c = next((c for c in d["creators"].values() if c.get("account") == uid or (u.get("email") and c.get("email") == u["email"])), None)
        if c and c.get("status") == "suspended":
            return None
        return c
    except Exception:
        return None


# ------------------------------------------------------------------ quản trị (chủ sàn)
def admin_list(q: str = "", role: str = "", plan: str = "") -> dict:
    from core import plans
    d = _load()
    rows = []
    ql = (q or "").strip().lower()
    for u in d["users"].values():
        if ql and ql not in (u.get("email", "") + " " + u.get("name", "") + " " + u.get("company", "")).lower():
            continue
        if role and role not in u.get("roles", []):
            continue
        if plan and u.get("plan") != plan:
            continue
        rows.append(_pub(u))
    rows.sort(key=lambda u: u.get("created") or "", reverse=True)
    by_plan = {p: sum(1 for u in d["users"].values() if u.get("plan") == p) for p in plans.PLANS}
    by_role = {r: sum(1 for u in d["users"].values() if r in u.get("roles", [])) for r in ROLES}
    return {"items": rows[:500], "total": len(d["users"]), "by_plan": by_plan, "by_role": by_role, "roles": ROLES, "plans": {k: v["name"] for k, v in plans.PLANS.items()},
            "audit": d["audit"][-50:][::-1]}


def admin_set(uid: str, plan: str = "", status: str = "", roles: str = "", note: str = "") -> dict:
    from core import plans
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if not u:
            raise ValueError("Không tìm thấy tài khoản")
        if u.get("owner") and status == "suspended":
            raise ValueError("Không khoá tài khoản chủ sàn")
        what = []
        if plan in plans.PLANS:
            u["plan"] = plan
            if plan == "trial":
                u["trial_until"] = (dt.date.today() + dt.timedelta(days=plans.TRIAL_DAYS)).isoformat()
            what.append(f"gói {plan}")
        if status in ("active", "suspended"):
            u["status"] = status
            what.append(status)
        if roles:
            rs = [r for r in roles.split(",") if r in ROLES and r != "owner"]
            if u.get("owner"):
                rs = ["owner"] + rs
            if rs:
                u["roles"] = list(dict.fromkeys(rs))
                what.append("vai " + ",".join(rs))
        audit(d, "Huy (quản trị)", f"Cập nhật {u.get('email') or uid}: " + ", ".join(what), note)
        _save(d)
    return {"text": f"Đã cập nhật {u.get('name')}: {', '.join(what) or 'không đổi'}.", "user": _pub(u)}
