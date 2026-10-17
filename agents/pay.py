"""Thanh toán và sổ cái superYou Marketplace.

Mô hình (anh Huy duyệt 17/10):
- Sàn giữ PLATFORM_FEE_PCT (20%) mỗi lượt bán; sản phẩm chính chủ: 100% về sàn.
- Giá sàn tối thiểu 29.000đ; bậc giá gợi ý 29k/49k/99k/199k/299k. Mua đứt hoặc thuê bao tháng (workflow).
- Hoàn tiền 7 ngày nếu chưa cài hoặc cài dưới 2 lần. Trả người bán ngày 10 hằng tháng khi số dư >= 200.000đ.

Giai đoạn 1 (bản này): VietQR chuyển khoản + đối soát.
- Khách bấm Mua -> đơn hàng có mã riêng (SY-XXXXXX) -> mã QR (img.vietqr.io) với nội dung chuyển khoản = mã đơn.
- Tiền về tài khoản của anh. Đối soát: webhook từ Casso/SePay (POST /api/pay/webhook, token bí mật trong header),
  hoặc anh bấm "Đã nhận tiền" trong Quản trị › Giao dịch.
- Đơn đã trả -> giao hàng: gói tải (SKILL.md / zip ghi chú / workflow.json) qua link ký 7 ngày + email hoá đơn;
  quyền sở hữu ghi theo email để sau này khách có tài khoản superYou thì tự mở.
Giai đoạn 2: PayOS (cổng VietQR tự động, webhook có chữ ký) -> adapter payos_* bên dưới, bật khi có PAYOS_* trong .env.

Biến môi trường (anh tự điền trên VPS, không đưa vào repo): BANK_ID (vd VCB, MB, TCB), BANK_ACCOUNT, BANK_ACCOUNT_NAME,
PAY_WEBHOOK_TOKEN (Casso/SePay), PAYOS_CLIENT_ID, PAYOS_API_KEY, PAYOS_CHECKSUM_KEY, PLATFORM_FEE_PCT (mặc định 20).
"""
import datetime as dt
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import threading
import zipfile
from urllib.parse import quote

from config import DATA_DIR

FILE = DATA_DIR / "pay.json"
PKG_DIR = DATA_DIR / "market_pkg"
_LOCK = threading.Lock()
FEE_PCT = int(os.getenv("PLATFORM_FEE_PCT", "20") or 20)
MIN_PRICE = 29000
TIERS = [0, 29000, 49000, 99000, 199000, 299000]
REFUND_DAYS = 7
PAYOUT_MIN = 200000
PAYOUT_DAY = 10
ORDER_TTL_H = 24
# Thẻ 14 (họp 17/10, anh duyệt): tạm khoá thu tiền cho tới khi có pháp nhân nhận tiền, luật sư rà chính sách và đo được chi phí LLM.
# Mở lại: đặt SUPERYOU_PAYMENTS=1 trong .env trên VPS (việc của anh). Sản phẩm miễn phí vẫn nhận bình thường.
PAYMENTS_CLOSED_TEXT = "Thanh toán đang tạm đóng trong giai đoạn thử nghiệm. superYou sẽ báo bạn qua email khi mở bán."


def payments_open() -> bool:
    return os.getenv("SUPERYOU_PAYMENTS", "0").strip() == "1"
STATUS = {"pending": "Chờ thanh toán", "paid": "Đã thanh toán", "delivered": "Đã giao", "refunded": "Đã hoàn tiền", "expired": "Hết hạn", "cancelled": "Đã huỷ"}


def _now() -> dt.datetime:
    return dt.datetime.now()


def _iso(t: dt.datetime | None = None) -> str:
    return (t or _now()).strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("orders", {})
    d.setdefault("ledger", [])
    d.setdefault("payouts", [])
    d.setdefault("entitlements", {})
    d.setdefault("bank_info", {})
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def vnd(v: int) -> str:
    return f"{int(v or 0):,}đ".replace(",", ".")


# ------------------------------------------------------------------ cấu hình
def config() -> dict:
    bank = {"id": (os.getenv("BANK_ID") or "").strip().upper(), "account": (os.getenv("BANK_ACCOUNT") or "").strip(),
            "name": (os.getenv("BANK_ACCOUNT_NAME") or "").strip()}
    return {"fee_pct": FEE_PCT, "min_price": MIN_PRICE, "tiers": TIERS, "refund_days": REFUND_DAYS, "payout_min": PAYOUT_MIN, "payout_day": PAYOUT_DAY, "payments_open": payments_open(),
            "bank": bank, "vietqr_ready": all(bank.values()), "webhook_ready": bool(os.getenv("PAY_WEBHOOK_TOKEN")),
            "payos_ready": all(os.getenv(k) for k in ("PAYOS_CLIENT_ID", "PAYOS_API_KEY", "PAYOS_CHECKSUM_KEY")),
            "mail_ready": _mail_ready()}


def _mail_ready() -> bool:
    try:
        from agents import mailbox
        return bool(mailbox.gmail_ready() or mailbox.lark_mail_ready())
    except Exception:
        return False


def qr_url(amount: int, code: str) -> str:
    b = config()["bank"]
    if not all(b.values()):
        return ""
    return (f"https://img.vietqr.io/image/{b['id']}-{b['account']}-compact2.png?amount={int(amount)}"
            f"&addInfo={quote(code)}&accountName={quote(b['name'])}")


# ------------------------------------------------------------------ đơn hàng
ORDER_PER_DAY = 10
DL_PER_DAY = 10
DL_TOTAL = 60
COMPLAINTS_TO_SUSPEND = 3


def download_allowed(oid: str) -> bool:
    """Chống chia sẻ link: mỗi đơn tối đa DL_PER_DAY lượt tải/ngày và DL_TOTAL lượt tổng."""
    if not oid:
        return True
    with _LOCK:
        d = _load()
        o = d["orders"].get(oid)
        if not o or o["status"] not in ("paid", "delivered"):
            return False
        today = _iso()[:10]
        dl = o.setdefault("dl", {"total": 0, "day": today, "n": 0})
        if dl["day"] != today:
            dl.update({"day": today, "n": 0})
        if dl["n"] >= DL_PER_DAY or dl["total"] >= DL_TOTAL:
            return False
        dl["n"] += 1
        dl["total"] += 1
        _save(d)
    return True


def complain(oid: str, email: str, reason: str) -> dict:
    """Người mua khiếu nại một đơn (xác thực bằng email đặt mua). 3 khiếu nại/30 ngày -> tự khoá người bán, báo chủ sàn."""
    from agents import market
    email = (email or "").strip().lower()
    reason = (reason or "").strip()[:500]
    if len(reason) < 10:
        raise ValueError("Bạn mô tả vấn đề cụ thể hơn (ít nhất 10 ký tự).")
    with _LOCK:
        d = _load()
        o = d["orders"].get(oid) or next((q for q in d["orders"].values() if q.get("code", "").upper() == oid.strip().upper()), None)
        if not o or o["email"] != email:
            raise ValueError("Không tìm thấy đơn với email này.")
        oid = o["id"]
        if o.get("complaint"):
            return {"text": "Đơn này đã có khiếu nại, chủ sàn đang xử lý."}
        o["complaint"] = {"reason": reason, "at": _iso(), "status": "moi"}
        cid = (o.get("seller") or {}).get("id") or ""
        since = _iso(_now() - dt.timedelta(days=30))
        n = sum(1 for q in d["orders"].values() if (q.get("seller") or {}).get("id") == cid and q.get("complaint") and q["complaint"]["at"] >= since)
        _save(d)
    suspended = False
    if cid and not (o.get("seller") or {}).get("official") and n >= COMPLAINTS_TO_SUSPEND:
        try:
            market.admin_creator(cid, "khoa")
            suspended = True
        except Exception:
            pass
    try:
        from core import security
        security.alert_once(f"complaint:{oid}", f"⚠️ Khiếu nại đơn {o['code']} ({o['name']}) từ {email}: {reason[:160]}"
                            + (f"\nNgười bán {o['seller'].get('name')} đã bị tạm khoá ({n} khiếu nại/30 ngày)." if suspended else ""), every=10**9)
    except Exception:
        pass
    try:
        from agents import board
        board.propose("ops", f"Khiếu nại đơn {o['code']}: {o['name'][:50]}", f"{email}: {reason}", why="Người mua khiếu nại trên Marketplace.",
                      impact="Hoàn tiền hoặc khoá người bán", priority="cao", by="Marketplace", auto_assign_to="product", key=f"complaint:{oid}")
    except Exception:
        pass
    return {"text": "Đã ghi nhận khiếu nại. Chủ sàn sẽ phản hồi qua email trong 2 ngày làm việc; nếu đúng, bạn được hoàn tiền theo Chính sách hoàn tiền."}


def block_buyer(email: str, on: bool = True, note: str = "") -> dict:
    """Chủ sàn khoá / mở khoá một email mua hàng."""
    email = (email or "").strip().lower()
    with _LOCK:
        d = _load()
        b = d.setdefault("blocked", {})
        if on:
            b[email] = {"at": _iso(), "note": note[:200]}
        else:
            b.pop(email, None)
        _save(d)
    return {"text": f"Đã {'khoá' if on else 'mở khoá'} {email}."}


def _code() -> str:
    return "SY" + "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(6))


def create_order(lid: str, email: str, channel: str = "public") -> dict:
    from agents import leads, market
    email = (email or "").strip().lower()[:254]
    if not leads.EMAIL_RE.match(email):
        raise ValueError("Email chưa đúng, bạn kiểm tra lại nhé.")
    x = market.get_listing(lid)
    if not x or x["status"] != "published":
        raise ValueError("Sản phẩm chưa lên kệ")
    price = int(x.get("price") or 0)
    if price > 0 and not payments_open():
        raise ValueError(PAYMENTS_CLOSED_TEXT)
    with _LOCK:
        d = _load()
        # chống lạm dụng: tối đa ORDER_PER_DAY đơn mỗi email mỗi ngày, người bán bị khoá thì không bán
        today = _iso()[:10]
        if sum(1 for o in d["orders"].values() if o["email"] == email and o["created"][:10] == today) >= ORDER_PER_DAY:
            raise ValueError("Bạn đã tạo quá nhiều đơn hôm nay, thử lại vào ngày mai hoặc liên hệ hỗ trợ.")
        if email in d.get("blocked", {}):
            raise ValueError("Tài khoản mua hàng này đang bị tạm khoá, liên hệ hỗ trợ.")
        # đã mua rồi -> trả về quyền sở hữu
        ent = d["entitlements"].get(email, {})
        if lid in ent:
            oo = d["orders"].get(ent[lid]["order"]) or {}
            return {"owned": True, "text": "Bạn đã mua sản phẩm này. Link tải ở dưới.", "order": _public_order(oo) if oo else None}
        # dùng lại đơn đang chờ
        for o in d["orders"].values():
            if o["email"] == email and o["lid"] == lid and o["status"] == "pending" and o["expires"] > _iso():
                return {"owned": False, "order": _public_order(o)}
        if price == 0:
            o = {"id": secrets.token_hex(6), "code": _code(), "lid": lid, "name": x["name"], "type": x["type"], "email": email, "amount": 0,
                 "seller": _seller(x), "status": "paid", "channel": channel, "created": _iso(), "paid_at": _iso(), "expires": _iso(_now() + dt.timedelta(days=1))}
            d["orders"][o["id"]] = o
            _save(d)
        else:
            if price < MIN_PRICE:
                price = MIN_PRICE
            o = {"id": secrets.token_hex(6), "code": _code(), "lid": lid, "name": x["name"], "type": x["type"], "email": email, "amount": price,
                 "billing": x.get("billing", "once"), "seller": _seller(x), "status": "pending", "channel": channel, "created": _iso(),
                 "expires": _iso(_now() + dt.timedelta(hours=ORDER_TTL_H)), "method": "vietqr"}
            d["orders"][o["id"]] = o
            _save(d)
    if o["status"] == "paid":
        deliver(o["id"])
        return {"owned": True, "text": "Sản phẩm miễn phí, link tải ở dưới" + (" và đã gửi qua email." if _mail_ready() else "."), "order": _public_order(_load()["orders"][o["id"]])}
    try:
        leads.add(email, f"market:order:{x['slug']}", "Đặt mua: " + x["name"])
    except Exception:
        pass
    return {"owned": False, "order": _public_order(o)}


def _seller(x: dict) -> dict:
    c = x.get("creator") or {}
    return {"id": c.get("id", ""), "name": c.get("name", ""), "official": bool(c.get("official") or c.get("owner"))}


def _public_order(o: dict) -> dict:
    cfg = config()
    return {"id": o["id"], "code": o["code"], "name": o["name"], "amount": o["amount"], "amount_text": vnd(o["amount"]), "status": o["status"],
            "status_text": STATUS.get(o["status"], o["status"]), "expires": o.get("expires"), "qr": qr_url(o["amount"], o["code"]) if o["status"] == "pending" else "",
            "bank": cfg["bank"] if o["status"] == "pending" else {}, "manual": not cfg["webhook_ready"] and not cfg["payos_ready"],
            "downloads": o.get("downloads") or [], "receipt": o.get("receipt", "")}


def order_status(oid: str, email: str = "") -> dict:
    d = _load()
    o = d["orders"].get(oid)
    if not o or (email and o["email"] != (email or "").strip().lower()):
        raise ValueError("Không tìm thấy đơn hàng")
    if o["status"] == "pending" and o["expires"] < _iso():
        with _LOCK:
            d = _load()
            d["orders"][oid]["status"] = "expired"
            _save(d)
            o = d["orders"][oid]
    return _public_order(o)


# ------------------------------------------------------------------ xác nhận thanh toán
def _mark_paid(d: dict, o: dict, method: str, ref: str = "") -> None:
    o["status"] = "paid"
    o["paid_at"] = _iso()
    o["method"] = method
    o["ref"] = ref[:120]
    amount = int(o["amount"])
    fee = amount if o["seller"].get("official") else round(amount * FEE_PCT / 100)
    o["fee"] = fee
    o["seller_amount"] = amount - fee
    d["ledger"].append({"at": o["paid_at"], "order": o["id"], "code": o["code"], "kind": "sale", "amount": amount, "fee": fee,
                        "seller_amount": amount - fee, "seller": o["seller"], "lid": o["lid"], "name": o["name"]})


def confirm_manual(oid: str, note: str = "") -> dict:
    """Anh bấm 'Đã nhận tiền' trong Quản trị."""
    with _LOCK:
        d = _load()
        o = d["orders"].get(oid)
        if not o:
            raise ValueError("Không tìm thấy đơn")
        if o["status"] != "pending":
            return {"text": f"Đơn {o['code']} đang ở trạng thái {STATUS.get(o['status'])}."}
        _mark_paid(d, o, "manual", note)
        _save(d)
    deliver(oid)
    return {"text": f"Đã xác nhận đơn {o['code']} ({vnd(o['amount'])}) và giao hàng cho {o['email']}."}


def webhook_bank(payload: dict, token: str) -> dict:
    """Webhook Casso / SePay: tìm mã đơn SYXXXXXX trong nội dung chuyển khoản, khớp số tiền thì xác nhận."""
    want = os.getenv("PAY_WEBHOOK_TOKEN", "")
    if not want or not hmac.compare_digest(token or "", want):
        raise PermissionError("Sai token webhook")
    txs = payload.get("data") if isinstance(payload.get("data"), list) else [payload.get("data") or payload]
    done = []
    with _LOCK:
        d = _load()
        by_code = {o["code"]: o for o in d["orders"].values() if o["status"] == "pending"}
        for t in txs:
            if not isinstance(t, dict):
                continue
            content = str(t.get("description") or t.get("content") or t.get("transferContent") or "")
            amount = int(float(t.get("amount") or t.get("transferAmount") or t.get("creditAmount") or 0))
            m = re.search(r"SY[A-Z2-9]{6}", content.upper().replace("-", "").replace(" ", ""))
            if not m or m.group(0) not in by_code:
                continue
            o = by_code[m.group(0)]
            if amount < int(o["amount"]):
                o.setdefault("notes", []).append(f"Chuyển thiếu: nhận {amount}")
                continue
            _mark_paid(d, o, "bank_webhook", str(t.get("id") or t.get("tid") or t.get("reference") or ""))
            done.append(o["id"])
        _save(d)
    for oid in done:
        deliver(oid)
    return {"ok": True, "matched": len(done)}


def payos_webhook(payload: dict) -> dict:
    """PayOS (giai đoạn 2): kiểm chữ ký HMAC-SHA256 trên data theo thứ tự khoá, rồi khớp orderCode."""
    key = os.getenv("PAYOS_CHECKSUM_KEY", "")
    data = payload.get("data") or {}
    if not key or not isinstance(data, dict):
        raise PermissionError("PayOS chưa cấu hình")
    msg = "&".join(f"{k}={'' if data[k] is None else data[k]}" for k in sorted(data))
    sig = hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, str(payload.get("signature") or "")):
        raise PermissionError("Sai chữ ký PayOS")
    code = str(data.get("description") or "")
    m = re.search(r"SY[A-Z2-9]{6}", code.upper())
    with _LOCK:
        d = _load()
        o = next((o for o in d["orders"].values() if m and o["code"] == m.group(0) and o["status"] == "pending"), None)
        if not o:
            return {"ok": True, "matched": 0}
        _mark_paid(d, o, "payos", str(data.get("reference") or data.get("paymentLinkId") or ""))
        _save(d)
    deliver(o["id"])
    return {"ok": True, "matched": 1}


# ------------------------------------------------------------------ giao hàng
def _package(x: dict) -> tuple[str, bytes]:
    """Đóng gói sản phẩm thành file tải: SKILL.md / zip ghi chú / workflow.json."""
    from agents import market
    c = x.get("content") or {}
    slug = x["slug"]
    if x["type"] == "skill":
        md = f"---\nname: {slug}\ndescription: {x.get('tagline', '')}\nversion: {x.get('version', '1.0')}\nsource: superYou Marketplace\n---\n\n# {x['name']}\n\n{c.get('skill', '')}\n"
        return f"{slug}-SKILL.md", md.encode("utf-8")
    if x["type"] == "brain":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(f"{slug}/README.md", f"# {x['name']}\n\n{x.get('description', '')}\n\nMở thư mục này bằng Obsidian hoặc chép vào Second Brain của superYou.\n")
            for i, n in enumerate(c.get("notes") or [], 1):
                z.writestr(f"{slug}/{i:02d} {market._slug(n['title'])[:60]}.md", n["md"])
        return f"{slug}.zip", buf.getvalue()
    return f"{slug}-workflow.json", json.dumps({"name": x["name"], "version": x.get("version"), "steps": c.get("steps") or []}, ensure_ascii=False, indent=1).encode("utf-8")


def create_plan_order(email: str, plan: str, uid: str = "") -> dict:
    """Đơn nâng cấp gói (pro / business): thanh toán VietQR như sản phẩm; khi tiền về, tài khoản được chuyển gói ngay."""
    from agents import leads
    from core import plans
    email = (email or "").strip().lower()[:254]
    if not leads.EMAIL_RE.match(email):
        raise ValueError("Email chưa đúng.")
    if not payments_open():
        raise ValueError(PAYMENTS_CLOSED_TEXT)
    P = plans.all_plans()["plans"]
    if plan not in ("pro", "business") or not int(P[plan].get("price") or 0):
        raise ValueError("Gói này liên hệ superYou để kích hoạt.")
    with _LOCK:
        d = _load()
        for o in d["orders"].values():
            if o["email"] == email and o.get("kind") == "plan" and o.get("plan") == plan and o["status"] == "pending" and o["expires"] > _iso():
                return {"owned": False, "order": _public_order(o)}
        o = {"id": secrets.token_hex(6), "code": _code(), "lid": "plan:" + plan, "kind": "plan", "plan": plan, "uid": uid, "name": f"Gói {P[plan]['name']} · 1 tháng",
             "type": "plan", "email": email, "amount": int(P[plan]["price"]), "billing": "monthly", "seller": {"id": "", "name": "superYou", "official": True},
             "status": "pending", "channel": "account", "created": _iso(), "expires": _iso(_now() + dt.timedelta(hours=ORDER_TTL_H)), "method": "vietqr"}
        d["orders"][o["id"]] = o
        _save(d)
    return {"owned": False, "order": _public_order(o)}


PLAN_DAYS = 31


def plan_until_for(cur: dict | None, plan: str, today: dt.date | None = None) -> str:
    """Ngày hết hạn sau khi trả 1 tháng. Gia hạn đúng gói còn hiệu lực -> cộng nối tiếp từ ngày hết hạn cũ;
    đổi gói hoặc đã hết hạn -> tính từ hôm nay (chưa tính tiền chênh lệch, chờ chính sách)."""
    today = today or _now().date()
    start = today
    if cur and cur.get("plan") == plan and cur.get("plan_until"):
        try:
            old = dt.date.fromisoformat(cur["plan_until"])
            if old >= today:
                start = old
        except ValueError:
            pass
    return (start + dt.timedelta(days=PLAN_DAYS)).isoformat()


def _deliver_plan(o: dict) -> dict:
    from core import accounts
    u = accounts.by_email(o["email"]) if not o.get("uid") else accounts.get(o["uid"])
    until = o.get("plan_until") or plan_until_for(u, o["plan"])
    if u and not o.get("plan_until"):
        accounts.set_paid_plan(u["id"], o["plan"], until, note=f"thanh toán đơn {o['code']}")
    with _LOCK:
        d = _load()
        oo = d["orders"][o["id"]]
        oo["status"] = "delivered"
        oo["delivered_at"] = oo.get("delivered_at") or _iso()
        oo["receipt"] = receipt_url(oo)
        oo["plan_until"] = until
        _save(d)
        o = oo
    try:
        from core import security
        security.alert_once(f"sale:{o['id']}", f"💎 Nâng cấp gói: {o['email']} đã trả {vnd(o['amount'])} cho {o['name']} (đến {until}).", every=10**9)
    except Exception:
        pass
    return {"text": f"Đã kích hoạt gói đến {until}", "downloads": [], "plan_until": until}


def _remind_email(r: dict) -> bool:
    """Email nhắc gia hạn. Chỉ gửi khi Gmail/Lark Mail đã kết nối; chưa có thì bỏ qua (lần quét sau gửi khi đã cấu hình)."""
    if not _mail_ready():
        return False
    from core import plans
    try:
        from agents import mailbox
        name = (plans.PLANS.get(r["plan"]) or {}).get("name", r["plan"])
        when = "hôm nay" if r["left"] == 0 else f"sau {r['left']} ngày"
        until = dt.date.fromisoformat(r["until"]).strftime("%d/%m/%Y")
        body = (f"Chào {r['name'] or 'bạn'},\n\nGói {name} của bạn trên superYou hết hạn {when} (hết ngày {until}).\n\n"
                f"Gia hạn tại: https://app.roimaxxhub.com/account#plans (Tài khoản › Gói và nâng cấp › Gia hạn).\n\n"
                "Nếu không gia hạn, tài khoản tự về gói Miễn phí; dữ liệu, sản phẩm đã mua và workflow của bạn vẫn được giữ nguyên.\n\nsuperYou · Roimaxx")
        platform = "gmail" if mailbox.gmail_ready() else "lark"
        mailbox.send(platform, r["email"], f"[superYou] Gói {name} hết hạn {when}", body)
        return True
    except Exception:
        import logging
        logging.getLogger("pay").exception("Gửi email nhắc gia hạn lỗi")
        return False


def plan_sweep() -> dict:
    """Chạy hằng ngày (và tự chạy khi có người mở Tài khoản, tối đa 1 lần/giờ): hạ gói hết hạn về Free, nhắc gia hạn trước 3 ngày."""
    from core import accounts
    expired = accounts.expire_plans()
    sent, skipped = [], []
    for r in accounts.due_reminders():
        if _remind_email(r):
            accounts.mark_reminded(r["id"], r["until"])
            sent.append(r["email"])
        else:
            skipped.append(r["email"])
    if expired:
        try:
            from core import security
            security.alert_once(f"plan-exp:{_iso()[:10]}:{len(expired)}", "⏳ Gói hết hạn, đã về Miễn phí: "
                                + ", ".join(f"{x['email']} ({x['plan']})" for x in expired[:10]) + ".", every=10**9)
        except Exception:
            pass
    return {"expired": expired, "reminded": sent, "remind_pending": skipped, "mail_ready": _mail_ready()}


_SWEPT = {"at": 0.0}


def maybe_sweep(every: int = 3600) -> None:
    import time
    if time.time() - _SWEPT["at"] < every:
        return
    _SWEPT["at"] = time.time()
    try:
        plan_sweep()
    except Exception:
        import logging
        logging.getLogger("pay").exception("Quét hết hạn gói lỗi")


def deliver(oid: str) -> dict:
    from agents import market
    from webapp import server
    with _LOCK:
        d = _load()
        o = d["orders"].get(oid)
        if not o or o["status"] not in ("paid", "delivered"):
            raise ValueError("Đơn chưa thanh toán")
        if o.get("kind") == "plan":
            o = dict(o)
    if o.get("kind") == "plan":
        return _deliver_plan(o)
    with _LOCK:
        d = _load()
        o = d["orders"][oid]
        x = market.get_listing(o["lid"])
        if not x:
            raise ValueError("Sản phẩm không còn")
        PKG_DIR.mkdir(parents=True, exist_ok=True)
        fname, data = _package(x)
        p = PKG_DIR / f"{x['id']}-{x.get('version', '1')}-{fname}"
        p.write_bytes(data)
        link = server.sign_download(str(p), fname, ttl=7 * 86400) + "&o=" + o["id"]
        o["downloads"] = [{"name": fname, "url": link, "expires": _iso(_now() + dt.timedelta(days=7))}]
        o["receipt"] = receipt_url(o)
        o["status"] = "delivered"
        o["delivered_at"] = _iso()
        d["entitlements"].setdefault(o["email"], {})[o["lid"]] = {"order": o["id"], "at": o["delivered_at"], "version": x.get("version")}
        market.count_sale(o["lid"])
        _save(d)
    _email_receipt(o, x)
    try:
        from core import security
        security.alert_once(f"sale:{o['id']}", f"💰 Marketplace: {o['email']} đã mua “{o['name']}” {vnd(o['amount'])}"
                            + ("" if o["seller"].get("official") else f" (người bán {o['seller']['name']} nhận {vnd(o.get('seller_amount', 0))})") + ".", every=10**9)
    except Exception:
        pass
    return {"text": "Đã giao hàng", "downloads": o["downloads"]}


def receipt_url(o: dict) -> str:
    from webapp import server
    sig = hmac.new(server._SECRET, f"rc|{o['id']}".encode(), hashlib.sha256).hexdigest()[:24]
    base = ""
    try:
        from agents import lark_oauth
        base = lark_oauth.base_url()
    except Exception:
        pass
    return f"{base}/pay/receipt?o={o['id']}&s={sig}"


def receipt_html(oid: str, sig: str) -> str:
    from webapp import server
    import html as H
    good = hmac.new(server._SECRET, f"rc|{oid}".encode(), hashlib.sha256).hexdigest()[:24]
    o = _load()["orders"].get(oid)
    if not o or not hmac.compare_digest(good, sig or ""):
        return "<p>Không tìm thấy hoá đơn.</p>"
    rows = [("Mã đơn", o["code"]), ("Sản phẩm", o["name"]), ("Email", o["email"]), ("Số tiền", vnd(o["amount"])),
            ("Thanh toán", (o.get("paid_at") or "")[:16].replace("T", " ") + " · " + {"vietqr": "VietQR", "bank_webhook": "Chuyển khoản", "manual": "Chuyển khoản", "payos": "PayOS"}.get(o.get("method", ""), o.get("method", ""))),
            ("Trạng thái", STATUS.get(o["status"], o["status"]))]
    dl = "".join(f'<p><a href="{H.escape(x["url"])}">Tải {H.escape(x["name"])}</a> (hết hạn {x["expires"][:10]})</p>' for x in o.get("downloads") or [])
    return (f"<h1 style='font-size:22px'>Hoá đơn superYou Marketplace</h1><table style='border-collapse:collapse'>"
            + "".join(f"<tr><td style='padding:6px 14px 6px 0;color:#666'>{H.escape(k)}</td><td style='padding:6px 0'><b>{H.escape(str(v))}</b></td></tr>" for k, v in rows)
            + f"</table>{dl}<p style='color:#666;font-size:14px'>Hoàn tiền trong {REFUND_DAYS} ngày nếu chưa cài hoặc cài dưới 2 lần. Liên hệ: trả lời email hoá đơn.</p>")


def _email_receipt(o: dict, x: dict):
    if not _mail_ready():
        return
    try:
        from agents import mailbox
        platform = "gmail" if mailbox.gmail_ready() else "lark"
        dl = "\n".join(f"- {d['name']}: {d['url']}" for d in o.get("downloads") or [])
        body = (f"Cảm ơn bạn đã mua “{x['name']}” trên superYou Marketplace.\n\nMã đơn: {o['code']}\nSố tiền: {vnd(o['amount'])}\n\n"
                f"Tải sản phẩm (link dùng trong 7 ngày):\n{dl}\n\nHoá đơn: {o.get('receipt', '')}\n\n"
                f"Cách dùng: {_howto(x)}\n\nHoàn tiền trong {REFUND_DAYS} ngày nếu chưa cài hoặc cài dưới 2 lần, chỉ cần trả lời email này.\n\nsuperYou · Roimaxx")
        mailbox.send(platform, o["email"], f"[superYou] Đơn {o['code']}: {x['name']}", body)
    except Exception:
        import logging
        logging.getLogger("pay").exception("Gửi email hoá đơn lỗi")


def _howto(x: dict) -> str:
    return {"skill": "Mở superYou › Marketplace › Đã cài để bật, hoặc chép SKILL.md vào thư mục skills của trợ lý AI bạn đang dùng (Claude Code, Cursor…).",
            "brain": "Giải nén và mở bằng Obsidian, hoặc chép vào Second Brain của superYou để trợ lý tra cứu khi trả lời.",
            "workflow": "Mở superYou › Marketplace › Đã cài › Chạy. File JSON mô tả các bước để bạn tự dựng ở công cụ khác."}.get(x["type"], "")


# ------------------------------------------------------------------ hoàn tiền, sổ cái, trả người bán
def refund(oid: str, note: str = "") -> dict:
    with _LOCK:
        d = _load()
        o = d["orders"].get(oid)
        if not o or o["status"] not in ("paid", "delivered"):
            raise ValueError("Đơn chưa thanh toán nên không hoàn được")
        o["status"] = "refunded"
        o["refunded_at"] = _iso()
        o["refund_note"] = note[:300]
        d["ledger"].append({"at": o["refunded_at"], "order": o["id"], "code": o["code"], "kind": "refund", "amount": -int(o["amount"]),
                            "fee": -int(o.get("fee", 0)), "seller_amount": -int(o.get("seller_amount", 0)), "seller": o["seller"], "lid": o["lid"], "name": o["name"]})
        d["entitlements"].get(o["email"], {}).pop(o["lid"], None)
        _save(d)
    return {"text": f"Đã ghi hoàn tiền đơn {o['code']} ({vnd(o['amount'])}). Anh chuyển khoản trả khách theo tài khoản họ cung cấp."}


def seller_balance(d: dict, sid: str) -> dict:
    earned = sum(e["seller_amount"] for e in d["ledger"] if e["seller"].get("id") == sid)
    paid = sum(p["amount"] for p in d["payouts"] if p["seller"] == sid and p["status"] == "paid")
    return {"earned": earned, "paid": paid, "balance": earned - paid}


def seller_revenue(sid: str) -> dict:
    d = _load()
    sales = [e for e in d["ledger"] if e["seller"].get("id") == sid]
    b = seller_balance(d, sid)
    month = _now().strftime("%Y-%m")
    return {"balance": b["balance"], "earned": b["earned"], "paid": b["paid"], "sales": len([e for e in sales if e["kind"] == "sale"]),
            "this_month": sum(e["seller_amount"] for e in sales if e["at"][:7] == month),
            "recent": [{"at": e["at"], "name": e["name"], "amount": e["amount"], "seller_amount": e["seller_amount"], "kind": e["kind"]} for e in sales[-20:]][::-1],
            "payouts": [p for p in d["payouts"] if p["seller"] == sid][-12:][::-1], "bank": d["bank_info"].get(sid, {}),
            "fee_pct": FEE_PCT, "payout_min": PAYOUT_MIN, "payout_day": PAYOUT_DAY, "next_payout": _next_payout()}


def _next_payout() -> str:
    t = _now()
    nxt = t.replace(day=PAYOUT_DAY) if t.day < PAYOUT_DAY else (t.replace(day=1) + dt.timedelta(days=32)).replace(day=PAYOUT_DAY)
    return nxt.strftime("%d/%m/%Y")


def seller_bank(sid: str, bank: str, account: str, name: str) -> dict:
    with _LOCK:
        d = _load()
        d["bank_info"][sid] = {"bank": bank.strip()[:40], "account": re.sub(r"\D", "", account)[:30], "name": name.strip()[:80], "updated": _iso()}
        _save(d)
    return {"text": "Đã lưu tài khoản nhận tiền."}


def admin_overview() -> dict:
    d = _load()
    orders = sorted(d["orders"].values(), key=lambda o: o["created"], reverse=True)
    month = _now().strftime("%Y-%m")
    sales = [e for e in d["ledger"] if e["kind"] == "sale"]
    refunds = [e for e in d["ledger"] if e["kind"] == "refund"]
    gross = sum(e["amount"] for e in d["ledger"])
    fee = sum(e["fee"] for e in d["ledger"])
    owed = {}
    for e in d["ledger"]:
        sid = e["seller"].get("id")
        if sid and not e["seller"].get("official"):
            owed.setdefault(sid, {"id": sid, "name": e["seller"].get("name", ""), "earned": 0})["earned"] += e["seller_amount"]
    for sid, v in owed.items():
        v["paid"] = sum(p["amount"] for p in d["payouts"] if p["seller"] == sid and p["status"] == "paid")
        v["balance"] = v["earned"] - v["paid"]
        v["bank"] = d["bank_info"].get(sid, {})
        v["due"] = v["balance"] >= PAYOUT_MIN
    cfg = config()
    return {"kpi": {"gross": gross, "fee": fee, "net_sellers": gross - fee, "month": sum(e["amount"] for e in d["ledger"] if e["at"][:7] == month),
                    "orders": len(orders), "pending": sum(1 for o in orders if o["status"] == "pending"), "sales": len(sales), "refunds": len(refunds),
                    "owed": sum(v["balance"] for v in owed.values())},
            "orders": [{k: o.get(k) for k in ("id", "code", "name", "email", "amount", "status", "created", "paid_at", "method", "seller", "fee", "seller_amount")}
                       | {"status_text": STATUS.get(o["status"], o["status"])} for o in orders[:200]],
            "owed": sorted(owed.values(), key=lambda v: -v["balance"]), "payouts": d["payouts"][-30:][::-1], "config": cfg, "statuses": STATUS}


def payout_mark(sid: str, amount: int, ref: str = "") -> dict:
    with _LOCK:
        d = _load()
        b = seller_balance(d, sid)
        amount = int(amount or b["balance"])
        if amount <= 0 or amount > b["balance"]:
            raise ValueError(f"Số tiền không hợp lệ (số dư {vnd(b['balance'])})")
        name = next((e["seller"].get("name") for e in d["ledger"] if e["seller"].get("id") == sid), sid)
        d["payouts"].append({"id": secrets.token_hex(4), "seller": sid, "name": name, "amount": amount, "ref": ref[:120], "status": "paid", "at": _iso()})
        _save(d)
    return {"text": f"Đã ghi trả {vnd(amount)} cho {name}."}


def entitlements(email: str) -> dict:
    d = _load()
    email = (email or "").strip().lower()
    ent = d["entitlements"].get(email, {})
    out = []
    for lid, e in ent.items():
        o = d["orders"].get(e["order"]) or {}
        out.append({"lid": lid, "name": o.get("name", ""), "at": e["at"], "downloads": o.get("downloads") or [], "receipt": o.get("receipt", "")})
    return {"items": out}


def resend(email: str) -> dict:
    """Khách bấm 'Gửi lại link tải' (giới hạn tần suất ở server)."""
    from agents import market
    d = _load()
    email = (email or "").strip().lower()
    ids = [e["order"] for e in d["entitlements"].get(email, {}).values()]
    n = 0
    for oid in ids:
        try:
            deliver(oid)
            n += 1
        except Exception:
            pass
    return {"ok": True, "sent": n}


def price_reco(x: dict) -> dict:
    """Gợi ý bậc giá cho một sản phẩm theo loại, nội dung và đối tượng (dùng khi anh duyệt lên kệ)."""
    sp = None
    try:
        from agents import market
        sp = market.spec(x)
    except Exception:
        pass
    size = (sp or {}).get("rule_count") or (sp or {}).get("step_count") or (sp or {}).get("note_count") or 0
    t = x["type"]
    if t == "skill":
        tier = 0 if size <= 3 else 29000 if size <= 6 else 49000
    elif t == "workflow":
        tier = 29000 if size <= 3 else 49000
    else:
        tier = 49000 if size < 10 else 99000 if size < 25 else 199000
    cat = x.get("category", "")
    if cat in ("ban-hang", "dieu-hanh") and tier:
        tier = TIERS[min(len(TIERS) - 1, TIERS.index(tier) + 1)]
    why = {"skill": f"Skill {size} quy tắc; skill ngắn nên miễn phí để kéo người dùng, skill đủ sâu bán 29–49k.",
           "workflow": f"Workflow {size} bước có chi phí AI khi chạy, nên thu 29–49k hoặc thuê bao tháng.",
           "brain": f"Gói {size} ghi chú, giá theo độ dày: dưới 10 ghi chú 49k, 10–25 ghi chú 99k, trọn khoá 30 ngày 199k."}[t]
    if cat in ("ban-hang", "dieu-hanh"):
        why += " Danh mục bán hàng/điều hành có người trả cao hơn (chủ shop, quản lý) nên nâng một bậc."
    return {"tier": tier, "tiers": TIERS, "why": why, "billing": "monthly" if t == "workflow" and size >= 4 else "once",
            "audience": {"ban-hang": "chủ shop, người bán POD/e-commerce", "dieu-hanh": "nhà quản lý, founder", "hop": "quản lý và trưởng nhóm",
                         "noi-dung": "người làm nội dung, marketer", "hoc": "người tự học", "nang-suat": "solopreneur và nhân viên văn phòng"}.get(cat, "người làm việc tri thức")}
