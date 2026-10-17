"""Thông tin xuất hoá đơn VAT khi mua (mảng Thương mại): kiểm tra MST, lưu vào đơn, ghi nhớ cho tài khoản, hoá đơn hiển thị,
chủ sàn ghi đã xuất. Chưa phát hành hoá đơn điện tử. Mỗi test một SUPERHUY_HOME riêng, không gọi mạng."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp: Path, code: str) -> dict:
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text("TELEGRAM_TOKEN=1:test\nOWNER_CHAT_ID=1001\nLLM_API_KEY=test\n")
    env = {k: v for k, v in os.environ.items()
           if k not in ("TELEGRAM_TOKEN", "OWNER_CHAT_ID", "LLM_API_KEY", "SUPERYOU_TENANT", "SUPERYOU_PAYMENTS", "APP_PIN_HASH")}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT), "SUPERYOU_PAYMENTS": "1"})
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_vat_validation(tmp_path):
    r = _run(tmp_path, r"""
import json
from agents import pay
out = {}
for k, v in {"none": {}, "blank": {"company": " ", "tax_code": "", "address": ""}, "ok": {"company": "Công ty TNHH Lan", "tax_code": "0101234567", "address": "12 Lý Thường Kiệt, Hà Nội"},
             "branch": {"company": "Công ty CP Minh", "tax_code": "0101234567-001", "address": "5 Lê Lợi, Quận 1, TP.HCM"},
             "bad_mst": {"company": "Công ty X", "tax_code": "12345", "address": "5 Lê Lợi, Quận 1"},
             "no_addr": {"company": "Công ty X", "tax_code": "0101234567", "address": ""}}.items():
    try:
        r = pay.clean_vat(v); out[k] = r["tax_code"] if r else None
    except ValueError:
        out[k] = "refused"
print(json.dumps(out))
""")
    assert r == {"none": None, "blank": None, "ok": "0101234567", "branch": "0101234567-001", "bad_mst": "refused", "no_addr": "refused"}


def test_vat_saved_on_orders_receipt_and_mark(tmp_path):
    r = _run(tmp_path, r"""
import json
from core import accounts
from agents import market, pay
d = market._ensure(market._load())
d["listings"]["L1"] = {"id": "L1", "slug": "s1", "type": "skill", "name": "Skill A", "tagline": "", "description": "", "status": "published", "price": 99000,
                       "version": "1.0", "creator": {"id": "c1", "name": "Bán A"}, "content": {"skill_md": "# A"}, "installs": 0, "sales": 0}
market._save(d)
u = accounts.signup("lan@shop.vn", "matkhau123", "Lan", agree=True)["user"]
V = {"company": "Công ty TNHH Lan", "tax_code": "0101234567", "address": "12 Lý Thường Kiệt, Hà Nội", "email": "ketoan@lan.vn"}
o = pay.create_order("L1", "lan@shop.vn", "public", uid=u["id"], vat=V)["order"]
p = pay.create_plan_order("lan@shop.vn", "pro", u["id"], vat=V)["order"]
pay.confirm_manual(o["id"])
oo = pay._load()["orders"][o["id"]]
import webapp.server as server, hmac, hashlib
sig = hmac.new(server._SECRET, f"rc|{o['id']}".encode(), hashlib.sha256).hexdigest()[:24]
html = pay.receipt_html(o["id"], sig)
k = pay.admin_overview()["kpi"]["vat_pending"]
t = pay.vat_mark(o["id"], "0000123")["text"]
try:
    pay.vat_mark(p["id"] + "x"); nf = "ok"
except ValueError:
    nf = "refused"
mine = pay.account_orders(u["id"], "lan@shop.vn")["items"]
print(json.dumps({"vat": oo["vat"]["tax_code"], "plan_vat": pay._load()["orders"][p["id"]]["vat"]["company"], "remember": accounts.get(u["id"])["vat"]["tax_code"],
                  "receipt": "0101234567" in html and "Công ty TNHH Lan" in html, "pending": k, "t": t, "nf": nf,
                  "acc_vat": mine[0]["vat"]["status"], "num": mine[0]["vat"]["number"]}))
""")
    assert r["vat"] == "0101234567" and r["plan_vat"] == "Công ty TNHH Lan" and r["remember"] == "0101234567"
    assert r["receipt"] and r["pending"] == 1 and "0000123" in r["t"] and r["nf"] == "refused"
    assert r["acc_vat"] == "da_xuat" and r["num"] == "0000123"
