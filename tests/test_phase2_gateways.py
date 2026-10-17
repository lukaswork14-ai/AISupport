"""Giai đoạn 2 (CHƯA BẬT): gia hạn qua PayOS, thẻ quốc tế qua Lemon Squeezy. Kiểm: tắt mặc định, cần đủ cờ + cấu hình,
chữ ký đúng/sai, webhook gia hạn gói, chống trùng sự kiện. Không gọi mạng: _http_post được thay. Khoá trong test là giá trị giả."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAKE = {"PAYOS_CLIENT_ID": "test-client", "PAYOS_API_KEY": "test-api", "PAYOS_CHECKSUM_KEY": "test-checksum",
        "LEMONSQUEEZY_API_KEY": "test-ls", "LEMONSQUEEZY_STORE_ID": "1", "LEMONSQUEEZY_WEBHOOK_SECRET": "test-whsec", "LEMONSQUEEZY_VARIANT_PRO": "42"}
CLEAR = ("TELEGRAM_TOKEN", "OWNER_CHAT_ID", "LLM_API_KEY", "SUPERYOU_TENANT", "SUPERYOU_PAYMENTS", "APP_PIN_HASH", "SUPERYOU_AUTORENEW", "SUPERYOU_INTL") + tuple(FAKE)


def _run(tmp: Path, code: str, extra: dict | None = None) -> dict:
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text("TELEGRAM_TOKEN=1:test\nOWNER_CHAT_ID=1001\nLLM_API_KEY=test\n")
    env = {k: v for k, v in os.environ.items() if k not in CLEAR}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT)})
    env.update(extra or {})
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


STATUS = r"""
import json
from agents import pay
print(json.dumps({"renew": pay.autorenew_enabled(), "intl": pay.intl_enabled(), "st": pay.gateways_status()}))
"""


def test_off_by_default_even_with_keys(tmp_path):
    a = _run(tmp_path, STATUS)
    b = _run(tmp_path, STATUS, dict(FAKE, SUPERYOU_PAYMENTS="1"))          # có khoá, chưa bật cờ
    c = _run(tmp_path, STATUS, {"SUPERYOU_PAYMENTS": "1", "SUPERYOU_AUTORENEW": "1", "SUPERYOU_INTL": "1"})  # bật cờ, thiếu khoá
    d = _run(tmp_path, STATUS, dict(FAKE, SUPERYOU_AUTORENEW="1", SUPERYOU_INTL="1"))  # thanh toán còn đóng
    e = _run(tmp_path, STATUS, dict(FAKE, SUPERYOU_PAYMENTS="1", SUPERYOU_AUTORENEW="1", SUPERYOU_INTL="1"))
    assert [x["renew"] for x in (a, b, c, d)] == [False] * 4 and [x["intl"] for x in (a, b, c, d)] == [False] * 4
    assert e["renew"] and e["intl"] and e["st"]["intl"]["plans"] == ["pro"]
    assert "test-" not in json.dumps(e["st"])  # trạng thái không lộ khoá


def test_payos_renewal_link_and_webhook(tmp_path):
    r = _run(tmp_path, r"""
import json, hmac, hashlib
from core import accounts
from agents import pay
u = accounts.signup("lan@shop.vn", "matkhau123", "Lan", agree=True)["user"]
sent = []
def fake(url, body, headers):
    sent.append({"url": url, "body": body, "h": sorted(headers)})
    return {"code": "00", "data": {"checkoutUrl": "https://pay.payos.vn/web/abc"}}
pay._http_post = fake
rn = pay.renewal_order(u["id"], "lan@shop.vn", "pro")
o = pay._load()["orders"][rn["order"]["id"]]
b = sent[0]["body"]
msg = "&".join(f"{k}={b[k]}" for k in ("amount", "cancelUrl", "description", "orderCode", "returnUrl"))
sig_ok = b["signature"] == hmac.new(b"test-checksum", msg.encode(), hashlib.sha256).hexdigest()
data = {"orderCode": o["payos_code"], "amount": o["amount"], "description": "thanh toan", "code": "00", "reference": "FT1"}
wsig = hmac.new(b"test-checksum", "&".join(f"{k}={data[k]}" for k in sorted(data)).encode(), hashlib.sha256).hexdigest()
try:
    pay.payos_webhook({"data": data, "signature": "sai"}); bad = "ok"
except PermissionError:
    bad = "refused"
w = pay.payos_webhook({"data": data, "signature": wsig})
print(json.dumps({"url": rn["url"], "renewal": o.get("renewal"), "desc_len": len(b["description"]), "sig_ok": sig_ok, "bad": bad, "matched": w["matched"],
                  "plan": accounts.get(u["id"])["plan"], "calls": len(sent), "endpoint": sent[0]["url"].endswith("/v2/payment-requests")}))
""", dict(FAKE, SUPERYOU_PAYMENTS="1", SUPERYOU_AUTORENEW="1"))
    assert r["url"].startswith("https://pay.payos.vn/") and r["renewal"] and r["desc_len"] <= 9
    assert r["sig_ok"] and r["bad"] == "refused" and r["matched"] == 1 and r["plan"] == "pro" and r["endpoint"]


def test_lemonsqueezy_webhook_signature_plan_and_dedupe(tmp_path):
    r = _run(tmp_path, r"""
import json, hmac, hashlib
from core import accounts
from agents import pay
u = accounts.signup("tom@intl.com", "matkhau123", "Tom", agree=True)["user"]
ev = {"meta": {"event_name": "subscription_created", "custom_data": {"uid": u["id"], "plan": "pro"}},
      "data": {"id": "sub_1", "attributes": {"status": "active", "renews_at": "2030-01-15T00:00:00Z", "created_at": "2029-12-15", "total": 900, "currency": "USD"}}}
raw = json.dumps(ev).encode()
sig = hmac.new(b"test-whsec", raw, hashlib.sha256).hexdigest()
try:
    pay.ls_webhook(raw, "00" * 32); bad = "ok"
except PermissionError:
    bad = "refused"
a = pay.ls_webhook(raw, sig)
b = pay.ls_webhook(raw, sig)
g = accounts.get(u["id"])
pay._http_post = lambda url, body, headers: {"data": {"attributes": {"url": "https://superyou.lemonsqueezy.com/checkout/x"}}}
co = pay.intl_checkout(u["id"], "tom@intl.com", "pro")
try:
    pay.intl_checkout(u["id"], "tom@intl.com", "business"); biz = "ok"
except ValueError:
    biz = "refused"
print(json.dumps({"bad": bad, "a": a.get("until"), "dup": b.get("dup"), "plan": g["plan"], "until": g["plan_until"], "intl": len(pay._load()["intl"]),
                  "co": co["url"], "biz": biz}))
""", dict(FAKE, SUPERYOU_PAYMENTS="1", SUPERYOU_INTL="1"))
    assert r["bad"] == "refused" and r["dup"] is True and r["intl"] == 1
    assert r["plan"] == "pro" and r["until"] == r["a"] == "2030-01-16"
    assert r["co"].startswith("https://") and r["biz"] == "refused"  # gói chưa có variant thì không bán quốc tế


def test_intl_checkout_refused_when_off(tmp_path):
    r = _run(tmp_path, r"""
import json
from agents import pay
pay._http_post = lambda *a: (_ for _ in ()).throw(AssertionError("không được gọi mạng"))
try:
    pay.intl_checkout("u1", "a@b.com", "pro"); out = "ok"
except ValueError:
    out = "refused"
print(json.dumps({"out": out, "link": pay.payos_link("x")}))
""", dict(FAKE))
    assert r == {"out": "refused", "link": ""}
