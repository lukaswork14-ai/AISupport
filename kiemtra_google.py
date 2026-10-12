"""Kiểm tra kết nối Google: chỉ ghi số lượng/lỗi vào data/kiemtra.txt (không ghi nội dung)."""
import datetime as dt, time, traceback
from config import DATA_DIR
out = []
try:
    from agents import calendar_agent
    tomorrow = dt.datetime.now(calendar_agent.TZ).date() + dt.timedelta(days=1)
    ev = calendar_agent.get_events(tomorrow)
    errs = [e for e in ev if e["source"] == "system"]
    out.append(f"Lich ngay mai: {len(ev) - len(errs)} su kien, {len(errs)} loi")
    for e in errs: out.append("  LOI: " + e["title"][:200])
except Exception:
    out.append("Calendar LOI: " + traceback.format_exc()[-400:])
try:
    from agents import email_agent
    mails = email_agent.fetch_emails(int(time.time()) - 24 * 3600)
    out.append(f"Gmail 24h qua: {len(mails)} email doc duoc")
except Exception:
    out.append("Gmail LOI: " + traceback.format_exc()[-400:])
(DATA_DIR / "kiemtra.txt").write_text("\n".join(out), encoding="utf-8")
print("\n".join(out))
