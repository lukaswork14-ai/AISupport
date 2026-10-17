"""Kiểm thử các quyết định 13–17 (họp liên phòng ban 17/10/2026, anh Huy duyệt).

Mỗi test chạy trong một tiến trình riêng với SUPERHUY_HOME riêng (giống một instance thật), không gọi mạng.
- Thẻ 14: đăng ký không lấy được gói trả phí; bắt buộc tích đồng ý; thanh toán tạm đóng; đường dẫn nâng cấp đúng.
- Thẻ 15: bản của khách không chép lời khi thiếu đồng ý / khi chưa mở ghi âm; trợ lý không chia sẻ được lời thoại/âm thanh.
- Thẻ 16: sự kiện kích hoạt chỉ gồm id + giờ; mọi lượt gọi LLM được đo token và chi phí.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(home: Path, code: str, extra_env: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("TELEGRAM_TOKEN", "OWNER_CHAT_ID", "LLM_API_KEY", "SUPERYOU_TENANT", "APP_PIN_HASH",
                        "SUPERYOU_PAYMENTS", "SUPERYOU_RECORDING", "USD_VND")}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT)})
    env.update(extra_env or {})
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _home(base: Path, name: str, chat: str = "1001") -> Path:
    home = base / name
    home.mkdir(parents=True)
    (home / ".env").write_text(f"TELEGRAM_TOKEN=1:{name}\nOWNER_CHAT_ID={chat}\nLLM_API_KEY=test\n")
    return home


@pytest.fixture()
def owner(tmp_path):
    return _home(tmp_path, "owner")


@pytest.fixture()
def tenant(tmp_path):
    return _home(tmp_path / "superyou-tenants", "khach-a", "2002")


# ------------------------------------------------------------------ thẻ 14
SIGNUP = r"""
import json
from core import accounts
out = {}
try:
    accounts.signup("a@shop.vn", "matkhau123", "Lan", plan="pro")
    out["no_agree"] = "created"
except ValueError as e:
    out["no_agree"] = "refused"
r = accounts.signup("b@shop.vn", "matkhau123", "Minh", plan="pro", agree=True, ip="1.2.3.4")
out["plan_pro"] = r["user"]["plan"]
r2 = accounts.signup("c@shop.vn", "matkhau123", "Hoa", plan="business", agree=True)
out["plan_business"] = r2["user"]["plan"]
r3 = accounts.signup("d@shop.vn", "matkhau123", "Tú", plan="trial", agree=True)
out["plan_trial"] = r3["user"]["plan"]
d = accounts._load()
u = next(x for x in d["users"].values() if x["email"] == "b@shop.vn")
out["consent"] = u.get("consent", {})
print(json.dumps(out))
"""


def test_signup_needs_consent_and_never_grants_paid_plan(owner):
    r = _run(owner, SIGNUP)
    assert r["no_agree"] == "refused"
    assert r["plan_pro"] == "free" and r["plan_business"] == "free"
    assert r["plan_trial"] == "trial"
    assert r["consent"]["terms"] and r["consent"]["at"] and r["consent"]["ip"] == "1.2.3.4"


PAY = r"""
import json
from agents import pay
out = {"open": pay.payments_open(), "cfg": pay.config()["payments_open"]}
try:
    pay.create_plan_order("a@shop.vn", "pro", "m1")
    out["plan_order"] = "created"
except ValueError as e:
    out["plan_order"] = str(e)
print(json.dumps(out))
"""


def test_payments_closed_by_default(owner):
    r = _run(owner, PAY)
    assert r["open"] is False and r["cfg"] is False
    assert "tạm đóng" in r["plan_order"]


def test_payments_can_be_reopened_by_owner_env(owner):
    r = _run(owner, PAY, {"SUPERYOU_PAYMENTS": "1"})
    assert r["open"] is True


def test_upgrade_route_matches_frontend():
    srv = (ROOT / "webapp" / "server.py").read_text(encoding="utf-8")
    page = (ROOT / "webapp" / "static" / "account" / "index.html").read_text(encoding="utf-8")
    assert "'/api/account/upgrade'" in page
    assert 'path == "/api/account/upgrade"' in srv
    assert 'path == "upgrade"' not in srv


def test_policy_pages_are_marked_draft_and_match_code():
    legal = (ROOT / "webapp" / "static" / "legal" / "index.html").read_text(encoding="utf-8")
    pay_src = (ROOT / "agents" / "pay.py").read_text(encoding="utf-8")
    assert "Bản nháp, chưa áp dụng" in legal
    day = re.search(r"^PAYOUT_DAY = (\d+)", pay_src, re.M).group(1)
    assert f"ngày {day} hằng tháng" in legal
    assert "OpenRouter" in legal and "âm thanh" in legal


# ------------------------------------------------------------------ thẻ 15
MEET = r"""
import json, pathlib
from config import DATA_DIR
from agents import meeting
f = DATA_DIR / "rec.m4a"; f.parent.mkdir(parents=True, exist_ok=True); f.write_bytes(b"0" * 4000)
out = {"policy": meeting.rec_policy()}
try:
    meeting.create(str(f), "Tải file")
    out["no_consent"] = "queued"
except ValueError as e:
    out["no_consent"] = "refused"
out["file_left"] = f.exists()
out["meetings"] = len(meeting.all_meetings())
print(json.dumps(out))
"""


def test_tenant_recording_closed_until_dpia(tenant):
    r = _run(tenant, MEET)
    assert r["policy"]["enabled"] is False and r["policy"]["consent"] is True
    assert r["no_consent"] == "refused" and r["file_left"] is False and r["meetings"] == 0


def test_tenant_recording_needs_consent_even_when_open(tenant):
    r = _run(tenant, MEET, {"SUPERYOU_RECORDING": "1"})
    assert r["policy"]["enabled"] is True
    assert r["no_consent"] == "refused" and r["meetings"] == 0


PROCESS_GUARD = r"""
import json
from agents import meeting
m = {"id": "261017-abcde", "title": "", "source": "x", "status": "queued", "raw": "/nonexistent"}
meeting.save(m)
meeting.process(m["id"])   # thiếu consent -> phải dừng trước khi chuẩn hoá/chép lời (không gọi mạng)
print(json.dumps(meeting.load(m["id"])))
"""


def test_tenant_process_refuses_without_consent_log(tenant):
    r = _run(tenant, PROCESS_GUARD, {"SUPERYOU_RECORDING": "1"})
    assert r["status"] == "error" and "đồng ý" in r["err"]


def test_owner_instance_recording_unchanged(owner):
    r = _run(owner, "import json; from agents import meeting; print(json.dumps(meeting.rec_policy()))")
    assert r["enabled"] is True and r["consent"] is False


SHARE = r"""
import json, hub
out = {"llm": hub._share_parts("summary,transcript,audio", False), "ui": hub._share_parts("summary,transcript", True)}
try:
    hub.hop_chia_se_ui("x", parts="summary,audio")
    out["ui_no_confirm"] = "shared"
except ValueError as e:
    out["ui_no_confirm"] = "refused"
print(json.dumps(out))
"""


def test_assistant_cannot_share_transcript_or_audio(owner):
    r = _run(owner, SHARE)
    assert r["llm"] == ["summary", True]
    assert r["ui"] == ["summary,transcript", False]
    assert r["ui_no_confirm"] == "refused"
    import ast
    src = (ROOT / "hub.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for call in ast.walk(tree):
        if isinstance(call, ast.Call) and getattr(call.func, "id", "") == "Action" and len(call.args) > 2 and getattr(call.args[2], "id", "") in ("hop_chia_se_ui", "hop_tao"):
            kws = {k.arg: getattr(k.value, "value", None) for k in call.keywords}
            assert not kws.get("llm"), "hop_chia_se_ui và hop_tao không được mở cho trợ lý tự gọi"


def test_tenant_app_shows_three_features_only():
    page = (ROOT / "webapp" / "static" / "index.html").read_text(encoding="utf-8")
    assert "const TENANT_TABS = ['home','meet','chat','me','more'];" in page
    srv = (ROOT / "webapp" / "server.py").read_text(encoding="utf-8")
    assert "window.SUPERYOU_TENANT=true" in srv


# ------------------------------------------------------------------ thẻ 16
ACT = r"""
import json
from core import activation
activation.signup("acc:m1"); activation.first_result("acc:m1", "bien_ban_thu"); activation.active_day("acc:m1")
activation.signup("acc:m2")
s = activation.summary(prefix="acc:")
raw = activation.FILE.read_text(encoding="utf-8")
print(json.dumps({"users": s["users"], "median": s["median_minutes_to_first"], "raw": raw}))
"""


def test_activation_events_hold_no_content(owner):
    r = _run(owner, ACT)
    assert r["users"] == 2 and r["median"] is not None
    data = json.loads(r["raw"])
    for u in data["users"].values():
        assert set(u) <= {"signup", "first_result", "first_kind", "days"}


METER = r"""
import json, llm
from agents import ops

class U:  # giống usage OpenRouter trả về
    prompt_tokens = 1200; completion_tokens = 300; cost = 0.0021
class R:
    usage = U(); model = "x"
class Inner:
    def __init__(self): self.kw = None
    def create(self, **kw):
        self.kw = kw; return R()
class Chat:
    def __init__(self): self.completions = Inner()
class Raw:
    def __init__(self): self.chat = Chat()

raw = Raw()
c = llm._MeteredClient(raw)
c.chat.completions.create(model="m", messages=[], extra_body={"reasoning": {"effort": "low"}})
m = ops.llm_month()
print(json.dumps({"sent": raw.chat.completions.kw["extra_body"], "calls": m["calls"], "tok": m["in"] + m["out"], "usd": m["cost_usd"], "vnd": m["cost"]}))
"""


def test_every_llm_call_is_metered(owner):
    r = _run(owner, METER, {"USD_VND": "25000"})
    assert r["sent"]["usage"] == {"include": True} and r["sent"]["reasoning"] == {"effort": "low"}
    assert r["calls"] == 1 and r["tok"] == 1500 and abs(r["usd"] - 0.0021) < 1e-9
    assert r["vnd"] == 52


def test_deploy_runs_gitleaks_before_release():
    wf = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    assert "needs: [test, secrets]" in wf and "gitleaks" in wf
