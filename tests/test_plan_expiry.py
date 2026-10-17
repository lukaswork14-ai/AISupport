"""Hết hạn gói trả phí (mảng Thương mại): plan_until, tự về Free giữ dữ liệu, nhắc gia hạn trước 3 ngày.

Mỗi test chạy trong tiến trình riêng với SUPERHUY_HOME riêng, không gọi mạng, không gửi email thật.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp: Path, code: str, payments: str = "1") -> dict:
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text("TELEGRAM_TOKEN=1:test\nOWNER_CHAT_ID=1001\nLLM_API_KEY=test\n")
    env = {k: v for k, v in os.environ.items()
           if k not in ("TELEGRAM_TOKEN", "OWNER_CHAT_ID", "LLM_API_KEY", "SUPERYOU_TENANT", "SUPERYOU_PAYMENTS", "APP_PIN_HASH")}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT), "SUPERYOU_PAYMENTS": payments})
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


PRE = r"""
import json, datetime as dt
from core import accounts
from agents import pay
today = dt.date.today()
def iso(n): return (today + dt.timedelta(days=n)).isoformat()
def force(uid, **kw):
    with accounts._LOCK:
        d = accounts._load(); d["users"][uid].update(kw); accounts._save(d)
u = accounts.signup("lan@shop.vn", "matkhau123", "Lan", agree=True)["user"]
"""


def test_paid_plan_sets_until_and_renewal_stacks(tmp_path):
    r = _run(tmp_path, PRE + r"""
o = pay.create_plan_order("lan@shop.vn", "pro", u["id"])["order"]
pay.confirm_manual(o["id"])
a = accounts.get(u["id"])
o2 = pay.create_plan_order("lan@shop.vn", "pro", u["id"])["order"]
pay.confirm_manual(o2["id"])
b = accounts.get(u["id"])
order = pay._load()["orders"][o2["id"]]
cp = None
print(json.dumps({"plan": a["plan"], "until1": a["plan_until"], "until2": b["plan_until"], "order_until": order["plan_until"],
                  "exp1": iso(pay.PLAN_DAYS), "exp2": iso(2 * pay.PLAN_DAYS)}))
""")
    assert r["plan"] == "pro"
    assert r["until1"] == r["exp1"]
    assert r["until2"] == r["exp2"] == r["order_until"]  # gia hạn sớm cộng nối tiếp, không mất ngày đã trả


def test_switch_plan_or_lapsed_starts_today(tmp_path):
    r = _run(tmp_path, r"""
import json, datetime as dt
from agents import pay
t = dt.date(2026, 10, 17)
print(json.dumps({
  "switch": pay.plan_until_for({"plan": "pro", "plan_until": "2026-11-01"}, "business", t),
  "lapsed": pay.plan_until_for({"plan": "pro", "plan_until": "2026-10-01"}, "pro", t),
  "same": pay.plan_until_for({"plan": "pro", "plan_until": "2026-10-20"}, "pro", t),
  "new": pay.plan_until_for(None, "pro", t)}))
""")
    assert r == {"switch": "2026-11-17", "lapsed": "2026-11-17", "same": "2026-11-20", "new": "2026-11-17"}


def test_expired_plan_falls_back_to_free_and_keeps_data(tmp_path):
    r = _run(tmp_path, PRE + r"""
force(u["id"], plan="pro", plan_until=iso(-1), company="Shop Lan")
lazy = accounts.get(u["id"])
with pay._LOCK:
    d = pay._load(); d["entitlements"]["lan@shop.vn"] = {"L1": {"order": "x", "at": "2026-10-01"}}; pay._save(d)
s = pay.plan_sweep()
after = accounts.get(u["id"])
again = pay.plan_sweep()
raw = accounts._load()["users"][u["id"]]
print(json.dumps({"lazy": lazy["plan"], "lazy_exp": lazy.get("plan_expired"), "expired": [x["email"] for x in s["expired"]],
                  "after": after["plan"], "after_exp": after.get("plan_expired"), "again": len(again["expired"]),
                  "company": raw.get("company"), "ent": list(pay.entitlements("lan@shop.vn")["items"][0].keys()) and True,
                  "audit": any("hết hạn" in a["what"] for a in accounts._load()["audit"])}))
""")
    assert r["lazy"] == "free" and r["lazy_exp"]["plan"] == "pro"  # chưa quét vẫn hiện Free ngay
    assert r["expired"] == ["lan@shop.vn"] and r["again"] == 0
    assert r["after"] == "free" and r["after_exp"]["plan"] == "pro"
    assert r["company"] == "Shop Lan" and r["ent"] and r["audit"]


def test_still_valid_on_last_day(tmp_path):
    r = _run(tmp_path, PRE + r"""
force(u["id"], plan="business", plan_until=iso(0))
s = pay.plan_sweep()
print(json.dumps({"plan": accounts.get(u["id"])["plan"], "expired": len(s["expired"])}))
""")
    assert r == {"plan": "business", "expired": 0}


def test_reminder_needs_mail_and_sends_once(tmp_path):
    r = _run(tmp_path, PRE + r"""
force(u["id"], plan="pro", plan_until=iso(3))
no_mail = pay.plan_sweep()
sent = []
pay._mail_ready = lambda: True
from agents import mailbox
mailbox.gmail_ready = lambda: True
mailbox.send = lambda platform, to, subject, body, **kw: sent.append({"to": to, "subject": subject, "body": body}) or "ok"
first = pay.plan_sweep()
second = pay.plan_sweep()
force(u["id"], plan="pro", plan_until=iso(10))
far = accounts.due_reminders()
print(json.dumps({"no_mail_sent": no_mail["reminded"], "pending": no_mail["remind_pending"], "first": first["reminded"], "second": second["reminded"],
                  "n": len(sent), "subject": sent[0]["subject"] if sent else "", "body_keeps_data": "giữ nguyên" in (sent[0]["body"] if sent else ""), "far": len(far)}))
""")
    assert r["no_mail_sent"] == [] and r["pending"] == ["lan@shop.vn"]  # chưa cấu hình mail: không gửi, không đánh dấu
    assert r["first"] == ["lan@shop.vn"] and r["second"] == [] and r["n"] == 1
    assert "sau 3 ngày" in r["subject"] and r["body_keeps_data"]
    assert r["far"] == 0


def test_owner_manual_grant_never_expires_and_owner_untouched(tmp_path):
    r = _run(tmp_path, PRE + r"""
force(u["id"], plan="pro", plan_until=iso(-5))
accounts.admin_set(u["id"], plan="pro", note="tặng")
s = pay.plan_sweep()
o = accounts.owner_user()
print(json.dumps({"plan": accounts.get(u["id"])["plan"], "until": accounts.get(u["id"]).get("plan_until"), "expired": len(s["expired"]), "owner": o["plan"]}))
""")
    assert r == {"plan": "pro", "until": None, "expired": 0, "owner": "enterprise"}


def test_expired_trial_cannot_restart_and_reads_free(tmp_path):
    r = _run(tmp_path, PRE + r"""
force(u["id"], plan="trial", trial_until=iso(-1))
g = accounts.get(u["id"])
print(json.dumps({"plan": g["plan"], "had_trial": bool(g.get("trial_until"))}))
""")
    assert r == {"plan": "free", "had_trial": True}
