"""Sản phẩm đã mua gắn với tài khoản (mảng Thương mại): danh sách đơn, tải lại, gửi lại, hoá đơn, khiếu nại một chạm,
và trang công khai không còn lộ link tải theo email. Mỗi test một SUPERHUY_HOME riêng, không gọi mạng, không gửi email thật."""
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


PRE = r"""
import json
from core import accounts
from agents import market, pay
d = market._ensure(market._load())
lid = "L1"
d["listings"][lid] = {"id": lid, "slug": "skill-a", "type": "skill", "name": "Skill A", "tagline": "", "description": "", "status": "published",
                      "price": 49000, "version": "1.0", "creator": {"id": "c1", "name": "Bán A"}, "content": {"skill_md": "# A"}, "installs": 0, "sales": 0}
market._save(d)
market.get_listing = lambda i: market._load()["listings"].get(i)
u = accounts.signup("lan@shop.vn", "matkhau123", "Lan", agree=True)["user"]
def buy(email, uid=""):
    o = pay.create_order(lid, email, "public", uid=uid)["order"]
    pay.confirm_manual(o["id"])
    return o["id"]
"""


def test_orders_by_uid_and_email_and_links_hidden_publicly(tmp_path):
    r = _run(tmp_path, PRE + r"""
a = buy("lan@shop.vn")                 # mua trước khi đăng nhập, cùng email tài khoản
b = buy("lan.khac@gmail.com", u["id"])  # mua khi đã đăng nhập, email khác
c = buy("nguoila@shop.vn")              # của người khác
items = pay.account_orders(u["id"], "lan@shop.vn")["items"]
pub = pay.entitlements("lan@shop.vn")
print(json.dumps({"ids": sorted(i["id"] for i in items), "want": sorted([a, b]), "uid_linked": pay._load()["orders"][a].get("uid") == u["id"],
                  "has_dl": all(i["downloads"] and i["receipt"] for i in items), "refundable": all(i["refundable"] for i in items),
                  "pub_keys": sorted(pub["items"][0].keys()), "sales": market._load()["listings"][lid]["sales"]}))
""")
    assert r["ids"] == r["want"] and r["uid_linked"] and r["has_dl"] and r["refundable"]
    assert r["pub_keys"] == ["at", "code", "lid", "name"]  # công khai: không link tải, không hoá đơn


def test_redownload_new_link_no_double_sale_and_ownership(tmp_path):
    r = _run(tmp_path, PRE + r"""
a = buy("lan@shop.vn")
first = pay._load()["orders"][a]["downloads"][0]["url"]
import time; time.sleep(1.1)
sent = []
pay._email_receipt = lambda o, x: sent.append(o["id"])
rd = pay.account_redownload(u["id"], "lan@shop.vn", a)
sales = market._load()["listings"][lid]["sales"]
other = accounts.signup("ke@shop.vn", "matkhau123", "Kẻ", agree=True)["user"]
try:
    pay.account_redownload(other["id"], "ke@shop.vn", a); denied = False
except ValueError:
    denied = True
print(json.dumps({"new": rd["downloads"][0]["url"] != first, "emailed": len(sent), "sales": sales, "denied": denied,
                  "ent_at_kept": pay._load()["entitlements"]["lan@shop.vn"][lid]["at"] == pay._load()["orders"][a]["delivered_at"]}))
""")
    assert r == {"new": True, "emailed": 0, "sales": 1, "denied": True, "ent_at_kept": True}


def test_resend_needs_mail_and_is_rate_limited(tmp_path):
    r = _run(tmp_path, PRE + r"""
a = buy("lan@shop.vn")
try:
    pay.account_resend(u["id"], "lan@shop.vn", a); no_mail = "sent"
except ValueError as e:
    no_mail = "refused"
pub_no_mail = pay.resend("lan@shop.vn")["ok"]
pay._mail_ready = lambda: True
sent = []
pay._email_receipt = lambda o, x: sent.append(o["id"])
ok = 0
for i in range(5):
    try:
        pay.account_resend(u["id"], "lan@shop.vn", a); ok += 1
    except ValueError:
        pass
print(json.dumps({"no_mail": no_mail, "pub_no_mail": pub_no_mail, "ok": ok, "sent": len(sent)}))
""")
    assert r == {"no_mail": "refused", "pub_no_mail": False, "ok": 3, "sent": 3}


def test_one_tap_complaint(tmp_path):
    r = _run(tmp_path, PRE + r"""
import agents.board as board
board.propose = lambda *a, **k: None
a = buy("lan@shop.vn")
try:
    pay.account_complain(u["id"], "lan@shop.vn", a, "khac", ""); khac = "ok"
except ValueError:
    khac = "need_detail"
t = pay.account_complain(u["id"], "lan@shop.vn", a, "hoan_tien")["text"]
it = pay.account_orders(u["id"], "lan@shop.vn")["items"][0]
again = pay.account_complain(u["id"], "lan@shop.vn", a, "sai_mo_ta")["text"]
print(json.dumps({"khac": khac, "saved": it["complaint"]["status"], "reason": it["complaint"]["reason"], "can": it["can_complain"], "again": "đã có khiếu nại" in again}))
""")
    assert r["khac"] == "need_detail" and r["saved"] == "moi" and r["can"] is False and r["again"]
    assert r["reason"].startswith("Tôi muốn hoàn tiền")
