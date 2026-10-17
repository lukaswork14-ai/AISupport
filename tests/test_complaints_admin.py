"""Quản trị khiếu nại và hoàn tiền (mảng Thương mại): chấp nhận hoàn ghi sổ âm, từ chối bắt buộc lý do, khoá email mua,
hoàn tiền gói đưa tài khoản về Miễn phí. Mỗi test một SUPERHUY_HOME riêng, không gọi mạng, không gửi email thật."""
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
from agents import market, pay, board
board.propose = lambda *a, **k: None
d = market._ensure(market._load())
d["creators"]["c1"] = {"id": "c1", "name": "Bán A", "email": "ban@a.vn", "status": "active", "created": "2026-10-01T00:00:00"}
for i in (1, 2):
    d["listings"][f"L{i}"] = {"id": f"L{i}", "slug": f"s{i}", "type": "skill", "name": f"Skill {i}", "tagline": "", "description": "", "status": "published",
                             "price": 100000, "version": "1.0", "creator": {"id": "c1", "name": "Bán A"}, "content": {"skill_md": "# A"}, "installs": 0, "sales": 0}
market._save(d)
def buy(lid, email):
    o = pay.create_order(lid, email)["order"]; pay.confirm_manual(o["id"]); return o["id"]
"""


def test_accept_refunds_and_reject_needs_reason(tmp_path):
    r = _run(tmp_path, PRE + r"""
a = buy("L1", "khach@x.vn"); b = buy("L2", "khach@x.vn")
pay.complain(a, "khach@x.vn", "Không tải được sản phẩm"); pay.complain(b, "khach@x.vn", "Không đúng mô tả gì cả")
ov = pay.complaints_overview()
t = pay.complaint_resolve(a, "hoan", "")["text"]
try:
    pay.complaint_resolve(b, "tu_choi", ""); rej_empty = "ok"
except ValueError:
    rej_empty = "need_reason"
pay.complaint_resolve(b, "tu_choi", "Sản phẩm đúng mô tả, đã gửi hướng dẫn cài")
try:
    pay.complaint_resolve(b, "hoan"); twice = "ok"
except ValueError:
    twice = "refused"
dd = pay._load()
ledger = [e for e in dd["ledger"] if e["order"] == a]
ov2 = pay.complaints_overview()
mine = pay.account_orders("", "khach@x.vn")["items"]
print(json.dumps({"new_before": ov["kpi"]["new"], "seller_30d": ov["items"][0]["seller"]["complaints_30d"], "t": t, "rej_empty": rej_empty, "twice": twice,
                  "a_status": dd["orders"][a]["status"], "b_status": dd["orders"][b]["status"], "ledger": [e["seller_amount"] for e in ledger],
                  "kpi": ov2["kpi"], "ent": sorted(dd["entitlements"]["khach@x.vn"].keys()),
                  "reply_b": next(i for i in mine if i["id"] == b)["complaint"]["reply"]}))
""")
    assert r["new_before"] == 2 and r["seller_30d"] == 2
    assert "Đã hoàn tiền" in r["t"] and "chuyển khoản" in r["t"]
    assert r["rej_empty"] == "need_reason" and r["twice"] == "refused"
    assert r["a_status"] == "refunded" and r["b_status"] == "delivered"
    assert r["ledger"] == [80000, -80000]  # phần người bán bị trừ lại khi hoàn
    assert r["kpi"] == {"new": 0, "refunded": 1, "rejected": 1, "blocked": 0}
    assert r["ent"] == ["L2"] and r["reply_b"].startswith("Sản phẩm đúng mô tả")


def test_block_buyer_and_unblock(tmp_path):
    r = _run(tmp_path, PRE + r"""
pay.admin_block_buyer("xau@x.vn", "1", "spam")
try:
    pay.create_order("L1", "xau@x.vn"); blocked = False
except ValueError:
    blocked = True
k = pay.complaints_overview()["kpi"]["blocked"]
pay.admin_block_buyer("xau@x.vn", "0")
ok = bool(pay.create_order("L1", "xau@x.vn")["order"])
print(json.dumps({"blocked": blocked, "k": k, "ok": ok}))
""")
    assert r == {"blocked": True, "k": 1, "ok": True}


def test_plan_refund_downgrades_account(tmp_path):
    r = _run(tmp_path, PRE + r"""
u = accounts.signup("lan@shop.vn", "matkhau123", "Lan", agree=True)["user"]
o = pay.create_plan_order("lan@shop.vn", "pro", u["id"])["order"]; pay.confirm_manual(o["id"])
before = accounts.get(u["id"])["plan"]
pay.complain(o["id"], "lan@shop.vn", "Tôi muốn hoàn tiền gói Pro")
pay.complaint_resolve(o["id"], "hoan")
print(json.dumps({"before": before, "after": accounts.get(u["id"])["plan"]}))
""")
    assert r == {"before": "pro", "after": "free"}
