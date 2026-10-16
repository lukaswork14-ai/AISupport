"""Chẩn đoán Lark trên VPS (không in khoá/token)."""
import json, sys, time, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import DATA_DIR  # noqa: E402
def step(name, fn):
    t = time.time()
    try:
        r = fn()
        print(f"lark_{name}: OK ({time.time()-t:.1f}s) {str(r)[:200]}")
    except Exception as e:
        print(f"lark_{name}: LỖI ({time.time()-t:.1f}s) {type(e).__name__}: {str(e)[:400]}")
from agents import lark_agent, lark_calendar  # noqa: E402
print("lark_ready:", lark_agent.ready(), "base:", lark_agent._base())
step("app_token", lambda: bool(lark_agent._app_token()))
step("tenant_token", lambda: bool(lark_agent._token()))
step("chats", lambda: len(lark_agent.chats()))
step("fetch_6h", lambda: len(lark_agent.fetch(int(time.time()) - 6 * 3600)))
print("larkcal_token_file:", lark_calendar.TOKEN_FILE.exists(), "ready:", getattr(lark_calendar, "ready", lambda: "?")())
step("cal_token", lambda: bool(lark_calendar._token()))
step("cal_events", lambda: len(lark_calendar.events(__import__("datetime").date.today(), "Asia/Ho_Chi_Minh")))
step("cal_invites", lambda: len(lark_calendar.invites(21, "Asia/Ho_Chi_Minh")))
try:
    from agents import tasks_hub
    step("tasks_ready", lambda: tasks_hub.lark_ready())
except Exception as e:
    print("tasks_hub:", e)
q = DATA_DIR / "qc.json"
if q.exists():
    d = json.loads(q.read_text())
    for k, v in d.items():
        if "lark" in k.lower() or (isinstance(v, dict) and "lark" in str(v.get("name", "")).lower()):
            print("qc", k, {x: v.get(x) for x in ("ok", "fails", "detail", "name")} if isinstance(v, dict) else v)
