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

from config import DATA_DIR, IS_TENANT, OWNER_CHAT_ID, SUPERYOU_PLAN

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
        d["users"][oid] = {"id": oid, "email": "", "name": "Huy" if not IS_TENANT else "Chủ nhân", "roles": ["owner", "seller", "member"] if not IS_TENANT else ["owner", "member"],
                           "plan": _instance_plan(), "status": "active", "created": _now(), "last_login": "", "last_role": "owner", "owner": True}
    if IS_TENANT and SUPERYOU_PLAN in ("free", "trial", "pro", "business", "enterprise") and d["users"][oid].get("plan") != SUPERYOU_PLAN:
        d["users"][oid]["plan"] = SUPERYOU_PLAN  # chủ sàn đổi gói trong .env của tenant
    return d


def _instance_plan() -> str:
    from core import plans
    if IS_TENANT:
        return SUPERYOU_PLAN if SUPERYOU_PLAN in plans.PLANS else "pro"
    return "enterprise"


def current_plan() -> dict:
    """Gói đang áp dụng cho chủ nhân instance này + giới hạn và mức dùng (để UI hiện 'Gói Pro · 3/20 workflow' và nút nâng cấp)."""
    from core import plans
    u = _load()["users"][f"u{OWNER_CHAT_ID}"]
    plan = effective_plan(u)
    plan = plan if plan in plans.PLANS else "free"
    P = plans.all_plans()["plans"][plan]
    used = {}
    try:
        from agents import workspace
        used["workflows"] = len(workspace._load().get("workflows") or {})
    except Exception:
        used["workflows"] = 0
    nxt = {"free": "pro", "trial": "pro", "pro": "business", "business": "enterprise"}.get(plan)
    return {"plan": plan, "name": P["name"], "color": P["color"], "limits": P["limits"], "features": P["features"], "used": used,
            "trial_until": u.get("trial_until", ""), "plan_until": u.get("plan_until", "") if plan in PAID_PLANS else "", "next": nxt, "next_name": plans.all_plans()["plans"][nxt]["name"] if nxt else "",
            "upgrade_url": "https://app.roimaxxhub.com/account#plans"}


def check_limit(key: str, current: int) -> None:
    """Chặn khi vượt giới hạn gói (0 = không giới hạn). Ném ValueError có hướng dẫn nâng cấp."""
    cp = current_plan()
    lim = int((cp["limits"] or {}).get(key, 0))
    if lim and current >= lim:
        raise ValueError(f"Gói {cp['name']} cho tối đa {lim} {LIMIT_LABEL.get(key, key)}. Nâng cấp lên {cp['next_name'] or 'gói cao hơn'} tại Tài khoản › Gói và nâng cấp.")


LIMIT_LABEL = {"workflows": "workflow riêng", "meetings_month": "cuộc họp mỗi tháng", "seats": "người dùng"}


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
    out = {k: u.get(k) for k in ("id", "email", "name", "roles", "plan", "status", "created", "last_login", "last_role", "company", "title", "trial_until", "plan_until", "vat")}
    out["plan"] = effective_plan(u)
    if out["plan"] != u.get("plan"):  # vừa hết hạn, chưa được quét: hiện như Free ngay, dữ liệu giữ nguyên
        out["plan_expired"] = {"plan": u.get("plan"), "until": u.get("plan_until") or u.get("trial_until") or ""}
    elif out["plan"] == "free" and u.get("plan_expired"):
        out["plan_expired"] = {k: u["plan_expired"].get(k, "") for k in ("plan", "until")}
    return out


# ------------------------------------------------------------------ hết hạn gói
PAID_PLANS = ("pro", "business")
REMIND_DAYS = 3


def _today() -> str:
    return dt.date.today().isoformat()


def effective_plan(u: dict) -> str:
    """Gói đang có hiệu lực: gói trả phí quá plan_until hoặc dùng thử quá trial_until -> free.
    Gói chủ sàn đặt tay (không có plan_until) và gói của chủ instance không bao giờ tự hết hạn."""
    plan = u.get("plan") or "free"
    if u.get("owner"):
        return plan
    today = _today()
    if plan in PAID_PLANS and u.get("plan_until") and u["plan_until"] < today:
        return "free"
    if plan == "trial" and u.get("trial_until") and u["trial_until"] < today:
        return "free"
    return plan


def set_paid_plan(uid: str, plan: str, until: str, note: str = "") -> dict:
    """Gói trả phí kích hoạt qua thanh toán (pay._deliver_plan): ghi gói và ngày hết hạn (YYYY-MM-DD, còn hiệu lực hết ngày đó)."""
    if plan not in PAID_PLANS:
        raise ValueError("Gói không hợp lệ")
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if not u:
            raise ValueError("Không tìm thấy tài khoản")
        u["plan"] = plan
        u["plan_until"] = until
        u.pop("plan_reminded", None)
        u.pop("plan_expired", None)
        audit(d, "superYou (thanh toán)", f"Gói {plan} của {u.get('email') or uid} đến {until}", note)
        _save(d)
    return _pub(u)


def expire_plans() -> list[dict]:
    """Quét định kỳ: chuyển các tài khoản hết hạn về Free (giữ nguyên dữ liệu, ghi nhật ký). Trả về danh sách vừa chuyển."""
    out = []
    with _LOCK:
        d = _load()
        for u in d["users"].values():
            eff = effective_plan(u)
            if eff != (u.get("plan") or "free"):
                old = u.get("plan")
                u["plan"] = eff
                u["plan_expired"] = {"plan": old, "until": u.get("plan_until") or u.get("trial_until") or "", "at": _now()}
                u.pop("plan_reminded", None)
                audit(d, "superYou (hết hạn)", f"Gói {old} của {u.get('email') or u['id']} hết hạn, về Miễn phí", u["plan_expired"]["until"])
                out.append({"id": u["id"], "email": u.get("email", ""), "name": u.get("name", ""), "plan": old, "until": u["plan_expired"]["until"]})
        if out:
            _save(d)
    return out


def due_reminders(days: int = REMIND_DAYS) -> list[dict]:
    """Tài khoản gói trả phí còn <= days ngày, chưa được nhắc cho kỳ hạn hiện tại."""
    today = dt.date.today()
    out = []
    for u in _load()["users"].values():
        if u.get("owner") or u.get("plan") not in PAID_PLANS or not u.get("plan_until") or not u.get("email"):
            continue
        try:
            left = (dt.date.fromisoformat(u["plan_until"]) - today).days
        except ValueError:
            continue
        if 0 <= left <= days and u.get("plan_reminded") != u["plan_until"]:
            out.append({"id": u["id"], "email": u["email"], "name": u.get("name", ""), "plan": u["plan"], "until": u["plan_until"], "left": left})
    return out


def mark_reminded(uid: str, until: str):
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if u:
            u["plan_reminded"] = until
            audit(d, "superYou (nhắc gia hạn)", f"Đã nhắc gia hạn {u.get('email') or uid}", until)
            _save(d)


# ------------------------------------------------------------------ đăng ký, đăng nhập
def _throttle(key: str) -> bool:
    now = time.time()
    xs = [t for t in _FAILS.get(key, []) if t > now - 900]
    _FAILS[key] = xs
    return len(xs) >= 8


def _fail(key: str):
    _FAILS.setdefault(key, []).append(time.time())


TERMS_VERSION = "2026-10-17-nhap"  # đổi khi điều khoản/chính sách có bản mới (sau khi luật sư rà)


def signup(email: str, password: str, name: str, role: str = "member", company: str = "", plan: str = "free",
           agree: bool = False, ip: str = "") -> dict:
    """agree: người dùng tự tích ô đồng ý (không tích sẵn). Lưu phiên bản điều khoản, thời điểm, IP vào tài khoản và nhật ký."""
    from core import plans
    if not agree:
        raise ValueError("Bạn cần đọc và đồng ý Điều khoản và Quyền riêng tư để tạo tài khoản.")
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
        # Gói trả phí chỉ có sau khi thanh toán (pay._deliver_plan) hoặc chủ sàn đặt trong HQ; đăng ký chỉ nhận free/trial.
        plan = plan if plan in ("free", "trial") and plan in plans.PLANS else "free"
        u = {"id": uid, "email": email, "name": name, "pw": _hash(password), "roles": list(dict.fromkeys(["member", role])), "plan": plan,
             "status": "active", "created": _now(), "last_login": "", "last_role": role, "company": (company or "").strip()[:80],
             "consent": {"terms": TERMS_VERSION, "at": _now(), "ip": (ip or "")[:45]}}
        if plan == "trial":
            u["trial_until"] = (dt.date.today() + dt.timedelta(days=plans.TRIAL_DAYS)).isoformat()
        d["users"][uid] = u
        audit(d, email, "Đăng ký", role)
        audit(d, email, "Đồng ý điều khoản", TERMS_VERSION)
        _save(d)
    try:
        from core import activation
        activation.signup("acc:" + uid)
    except Exception:
        pass
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


def set_vat(uid: str, vat: dict):
    """Ghi nhớ thông tin xuất hoá đơn VAT lần gần nhất để điền sẵn ở lần mua sau."""
    with _LOCK:
        d = _load()
        u = d["users"].get(uid)
        if u:
            u["vat"] = {k: vat.get(k, "") for k in ("company", "tax_code", "address", "email")}
            _save(d)


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
        if plan and effective_plan(u) != plan:
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
            u.pop("plan_until", None)  # chủ sàn đặt tay = không tự hết hạn; gói qua thanh toán dùng set_paid_plan
            u.pop("plan_reminded", None)
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
