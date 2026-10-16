"""QC: bot tự giám sát và nhắn ngay cho chủ nhân qua Telegram khi có bất thường (và khi đã ổn lại).

- Kiểm tra nhanh mỗi 5 phút: server Mini App, đường hầm (link app), dung lượng ổ đĩa.
- Kiểm tra kết nối mỗi 60 phút: Gmail, AI (OpenRouter), Lark, cầu nối lịch Google, lịch Lark.
- Lỗi phát sinh: job tự động lỗi/bị lỡ, lỗi khi bấm trong app, lỗi giao diện Mini App.
- Ghi data/heartbeat.json để bộ giám sát bên ngoài biết bot còn sống.
Chống spam: chỉ báo khi trạng thái ĐỔI (ổn -> lỗi, lỗi -> ổn), lỗi lặp lại tối đa 1 lần/30 phút."""
import json
import logging
import os
import shutil
import threading
import time

import requests

from config import DATA_DIR

log = logging.getLogger("qc")
STATE_FILE = DATA_DIR / "qc.json"
HEARTBEAT = DATA_DIR / "heartbeat.json"
_lock = threading.Lock()
_last_incident: dict[str, float] = {}
FAILS_BEFORE_ALERT = {"tunnel": 2, "server": 2}  # chờ 2 lượt (10 phút) để đường hầm tự sửa trước khi báo


def _load() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _save(d: dict):
    try:
        STATE_FILE.write_text(json.dumps(d, ensure_ascii=False))
    except Exception:
        pass


def _send(text: str):
    try:
        from core import notify
        threading.Thread(target=lambda: notify.send(text=text), daemon=True).start()
    except Exception:
        pass


def _plain(detail: str) -> str:
    """Đổi thông báo kỹ thuật thành câu dễ hiểu."""
    d = detail or ""
    low = d.lower()
    if "max retries" in low or "connectionerror" in low or "name or service not known" in low or "nodename nor servname" in low \
            or "timed out" in low or "timeout" in low or "temporary failure in name resolution" in low:
        pre = d.split(":")[0] if d.startswith("Không") else ""
        return (pre + ": " if pre else "") + "không kết nối được (mất mạng hoặc dịch vụ đang gián đoạn)."
    if "authenticationfailed" in low or "invalid credentials" in low:
        return "sai mật khẩu ứng dụng (App Password) hoặc đã bị thu hồi."
    return d[:240]


def report(key: str, name: str, ok: bool, detail: str = "", fix: str = ""):
    """Ghi kết quả 1 kiểm tra; nhắn khi chuyển trạng thái."""
    detail = _plain(detail)
    with _lock:
        st = _load()
        c = st.get(key, {"ok": True, "fails": 0})
        prev_ok, alerted = c.get("ok", True), c.get("alerted", False)
        if ok:
            c.update(ok=True, fails=0, detail="", at=time.time())
            if alerted:
                c["alerted"] = False
                _send(f"✅ QC: {name} đã hoạt động lại bình thường.")
        else:
            c.update(ok=False, fails=c.get("fails", 0) + 1, detail=detail[:300], at=time.time())
            if not alerted and c["fails"] >= FAILS_BEFORE_ALERT.get(key, 1):
                c["alerted"] = True
                _send(f"⚠️ QC: {name} đang lỗi.\n{detail[:300]}" + (f"\n👉 {fix}" if fix else ""))
        st[key] = {**c, "name": name}
        _save(st)
        if prev_ok != ok:
            log.info("QC %s: %s %s", key, "OK" if ok else "LỖI", detail[:200])


def incident(key: str, text: str, every: int = 1800):
    """Sự cố đơn lẻ (job lỗi, lỗi trong app): nhắn ngay, cùng một loại tối đa 1 lần / `every` giây."""
    now = time.time()
    if now - _last_incident.get(key, 0) < every:
        return
    _last_incident[key] = now
    log.warning("QC sự cố %s: %s", key, text[:300])
    _send("⚠️ QC: " + text[:900])


# ------------------------------------------------------------------ các kiểm tra
def _http_ok(url: str, timeout: int = 15) -> tuple[bool, str]:
    try:
        r = requests.get(url, timeout=timeout)
        return r.ok, f"HTTP {r.status_code}"
    except Exception as e:
        return False, type(e).__name__


def tunnel_url() -> str:
    fixed = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
    if fixed:
        return fixed
    try:
        return json.loads((DATA_DIR / "tunnel.json").read_text())["url"].rstrip("/")
    except Exception:
        return ""


def quick_checks(port: int):
    ok, d = _http_ok(f"http://127.0.0.1:{port}/health", 10)
    report("server", "Máy chủ Mini App", ok, f"Không phản hồi ({d}).", "Bot sẽ được khởi động lại nếu lỗi kéo dài.")
    url = tunnel_url()
    if url:
        ok, d = _http_ok(url + "/health", 20)
        report("tunnel", "Link Mini App", ok, f"Link {url} không mở được ({d}).",
               "Trên VPS: kiểm tra Caddy (sudo systemctl status caddy) và tên miền trỏ đúng IP." if os.getenv("WEBAPP_URL")
               else "Bot đang tự mở link mới; khi xong sẽ gửi nút “Mở app” mới.")
    else:
        report("tunnel", "Link Mini App (đường hầm)", False, "Chưa có link Mini App.", "Kiểm tra cloudflared (Cai-dat-miniapp.command).")
    free = shutil.disk_usage(str(DATA_DIR)).free / 1e9
    report("disk", "Dung lượng ổ đĩa", free > 2, f"Chỉ còn {free:.1f} GB trống.", "Xóa bớt file trong data/videos, data/video_tmp.")
    heartbeat()


def connection_checks():
    """Kiểm tra các kết nối (chậm hơn, chạy mỗi giờ)."""
    from agents import gcal_bridge, lark_agent, mailbox
    ok, _ = _http_ok("https://api.telegram.org", 15)
    if not ok:
        ok, _ = _http_ok("https://www.google.com/generate_204", 15)
    report("net", "Mạng internet của máy chủ", ok, "Máy chủ bot đang mất mạng.", "Kiểm tra mạng của VPS / máy Mac.")
    if not ok:
        return  # mất mạng: không báo lỗi lan tràn từng dịch vụ
    if mailbox.gmail_ready():
        try:
            box = mailbox._imap()
            box.logout()
            report("gmail", "Gmail", True)
        except Exception as e:
            report("gmail", "Gmail", False, f"Không đăng nhập được: {e}", "Tạo App Password mới rồi dán vào Thêm › Kết nối › Gmail.")
    try:
        from config import LLM_MODEL
        from llm import make_client
        r = make_client().chat.completions.create(model=LLM_MODEL, max_tokens=5, timeout=60,
                                                  messages=[{"role": "user", "content": "ping"}])
        report("llm", "AI (OpenRouter)", r is not None)
    except Exception as e:
        msg = str(e)
        fix = "Nạp thêm credit OpenRouter." if "402" in msg or "credit" in msg.lower() else "Kiểm tra khóa OpenRouter / mạng."
        report("llm", "AI (OpenRouter)", False, msg[:250], fix)
    if lark_agent.ready():
        try:
            lark_agent._app_token()
            report("lark", "Lark", True)
        except Exception as e:
            report("lark", "Lark", False, str(e), "Kiểm tra App ID/Secret trong Thêm › Kết nối › Lark.")
    if gcal_bridge.ready():
        try:
            gcal_bridge._post({"action": "ping"}, timeout=40)
            report("gcal", "Cầu nối lịch Google", True)
        except Exception as e:
            report("gcal", "Cầu nối lịch Google", False, str(e), "Mở lại Apps Script và kiểm tra bản triển khai Web app.")
    try:
        from agents import lark_calendar
        if lark_calendar.TOKEN_FILE.exists():
            lark_calendar._token()
            report("larkcal", "Lịch Lark", True)
    except Exception as e:
        report("larkcal", "Lịch Lark", False, str(e), "Thêm › Kết nối › Lịch Lark rồi bấm Cho phép.")


def heartbeat():
    st = _load()
    bad = [v.get("name", k) for k, v in st.items() if isinstance(v, dict) and not v.get("ok", True)]
    try:
        HEARTBEAT.write_text(json.dumps({"ts": time.time(), "pid": os.getpid(), "url": tunnel_url(), "problems": bad},
                                        ensure_ascii=False))
    except Exception:
        pass


def status_text() -> str:
    st = _load()
    if not st:
        return "QC chưa chạy lượt kiểm tra nào."
    lines = []
    for k, v in st.items():
        if not isinstance(v, dict):
            continue
        when = time.strftime("%H:%M", time.localtime(v.get("at", 0)))
        lines.append(("✅ " if v.get("ok", True) else "⚠️ ") + v.get("name", k) + f" ({when})"
                     + ("" if v.get("ok", True) else f": {v.get('detail', '')}"))
    return "🩺 Tình trạng hệ thống\n\n" + "\n".join(lines)


def status_items() -> list[dict]:
    return [{"id": k, "name": v.get("name", k), "ok": v.get("ok", True), "detail": v.get("detail", ""), "at": v.get("at", 0)}
            for k, v in _load().items() if isinstance(v, dict)]


# ------------------------------------------------------------------ lỗi phát sinh
EXPECTED = (ValueError, PermissionError, KeyError)  # lỗi do người dùng nhập, không phải hỏng hệ thống


def job_failed(agent: str, action: str, err: Exception):
    if isinstance(err, EXPECTED):
        return
    msg = str(err)
    if msg.startswith("Chưa ") or "chưa kết nối" in msg.lower():  # chưa cài đặt, không phải lỗi
        return
    incident(f"run:{agent}.{action}:{type(err).__name__}", f"Lỗi khi chạy “{agent}.{action}” trong app: {msg[:300]}")


def client_error(data: dict):
    msg = str(data.get("msg", ""))[:300]
    where = f"{str(data.get('src', ''))[-60:]}:{data.get('line', '')}"
    incident("ui:" + msg[:80], f"Mini App gặp lỗi giao diện: {msg} ({where}). Mình sẽ kiểm tra và sửa.", every=3600)


# ------------------------------------------------------------------ tự kiểm tra sâu (theo yêu cầu QC)
SELFTEST_FLAG = DATA_DIR / "selftest.flag"
SELFTEST_OUT = DATA_DIR / "selftest.json"
DEEP_FLAG = DATA_DIR / "selftest_deep.flag"
CONTENT_FLAG = DATA_DIR / "selftest_content.flag"
MEETING_FLAG = DATA_DIR / "selftest_meeting.flag"
MEETING_E2E = DATA_DIR / "selftest_meeting_e2e.flag"


def selftest() -> dict:
    """Chạy thử từng tính năng chính, chỉ ghi số lượng + lỗi (không ghi nội dung riêng tư)."""
    import datetime as dt
    out = {"at": time.time()}

    def t(name, fn):
        t0 = time.time()
        try:
            r = fn()
            out[name] = {"ok": True, "n": r, "s": round(time.time() - t0, 1)}
        except Exception as e:
            out[name] = {"ok": False, "err": _plain(str(e))[:200], "s": round(time.time() - t0, 1)}

    from agents import calendar_agent, gcal_bridge, lark_agent, mailbox
    today = dt.datetime.now(calendar_agent.TZ).date()
    t("lich_hom_nay", lambda: len(calendar_agent.get_events(today)))
    t("lich_ngay_mai", lambda: len(calendar_agent.get_events(today + dt.timedelta(days=1))))
    try:
        from agents import lark_calendar
        if lark_calendar.ready():
            t("lark_lich_hom_nay", lambda: len(lark_calendar.events(today, calendar_agent.TZ)))
            t("lark_loi_moi", lambda: len(lark_calendar.invites(21, calendar_agent.TZ)))
    except Exception as e:
        out["lark_lich"] = {"ok": False, "err": str(e)[:200]}
    if gcal_bridge.ready():
        t("google_loi_moi", lambda: len(gcal_bridge.invites(21)))
    if mailbox.gmail_ready():
        t("hop_thu", lambda: len(mailbox.inbox()))
    if lark_agent.ready():
        t("lark_nhom", lambda: len(lark_agent.chats()))
    try:
        from agents import finance, tasks_hub
        d = tasks_hub.collect(refresh=True)
        for src in ("lark", "google", "local"):
            if src in d["errors"]:
                out["viec_" + src] = {"ok": False, "err": d["errors"][src][:200]}
            else:
                out["viec_" + src] = {"ok": True, "n": sum(1 for x in d["items"] if x["source"] == src)}
        t("viec_danh_ba", lambda: len(tasks_hub.people_list(refresh=True)))
        if tasks_hub.lark_ready():
            t("viec_lark_danhsach", lambda: len(tasks_hub._lark_lists()))
            def _lark_any():
                tot = 0
                for c in ("false", "true"):
                    d2 = tasks_hub._lark("GET", "/open-apis/task/v2/tasks", params={"type": "my_tasks", "completed": c, "page_size": 50})
                    tot += len(d2.get("items") or [])
                return tot
            t("viec_lark_api", _lark_any)
        t("tai_chinh", lambda: len(finance.overview()["tx"]))
    except Exception as e:
        out["viec_tai_chinh"] = {"ok": False, "err": str(e)[:200]}
    try:
        from agents import growth
        from core import memory as _m
        t("phat_trien", lambda: {"muc_tieu": len(growth.overview()["goals"]), "thoi_quen": len(growth.overview()["habits"])})
        t("tri_nho", lambda: len(_m.facts()))
        if DEEP_FLAG.exists():  # kiểm tra sâu: gọi AI thật cho lịch trình + huấn luyện viên
            DEEP_FLAG.unlink()
            from agents import planner
            t("ai_lich_trinh", lambda: len(planner.plan()["blocks"]))
            gs = growth.overview()["goals"]
            for g in gs:
                t("ai_hlv_" + g["id"], lambda g=g: len(growth.coach(g["id"]).get("habits", [])))
    except Exception as e:
        out["phat_trien"] = {"ok": False, "err": str(e)[:200]}
    try:
        from agents import content_hub
        t("noi_dung", lambda: {"cho_duyet": len(content_hub.queue_view()["new"]), "chu_de": len(content_hub.cfg()["topics"])})
        if CONTENT_FLAG.exists():  # kiểm tra sâu trang Nội dung: săn tin thật (+ tạo 1 bộ nội dung nếu flag có bài)
            try:
                job = json.loads(CONTENT_FLAG.read_text(encoding="utf-8") or "{}")
            except Exception:
                job = {}
            CONTENT_FLAG.unlink()
            if not job.get("no_scan"):
                t("noi_dung_san_tin", lambda: content_hub.scan().get("added", 0))
            if job.get("gnews"):
                t("noi_dung_gnews", lambda: content_hub.resolve_gnews(next(i["url"] for i in content_hub._load() if "news.google.com" in i.get("url", "")))[:80] or 1 / 0)
            if job.get("approve_track"):
                first = next((i for i in content_hub.queue_view()["new"] if i["track"] == job["approve_track"]), None)
                if first:
                    t("noi_dung_duyet", lambda: content_hub.approve(first["id"]).get("text"))
            if job.get("text") or job.get("url"):
                t("noi_dung_tao_bo", lambda: content_hub.add_manual(job.get("text", ""), job.get("url", ""), True).get("id"))
    except Exception as e:
        out["noi_dung"] = {"ok": False, "err": str(e)[:200]}
    try:
        from agents import meeting as _mt
        t("hop", lambda: len(_mt.all_meetings()))
        if MEETING_FLAG.exists():  # kiểm tra sâu Meeting Studio: hội thoại giọng AI -> chép lời -> biên bản -> Obsidian -> hỏi lại
            MEETING_FLAG.unlink()
            t("hop_quy_trinh", lambda: _mt.selftest())
            t("hop_hoi_lai", lambda: _mt.ask("Ai phụ trách kết nối API Etsy và hạn khi nào?")["answer"][:160])
        if MEETING_E2E.exists():  # đầu-cuối qua máy chủ Mini App: tải lên theo phần, họp dài nhiều đoạn, phát lại, hỏi lại
            MEETING_E2E.unlink()
            t("hop_dau_cuoi", lambda: _mt.selftest_http(int(os.getenv("WEBAPP_PORT", "8787"))))
    except Exception as e:
        out["hop"] = {"ok": False, "err": str(e)[:200]}
    SELFTEST_OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1))
    bad = [k for k, v in out.items() if isinstance(v, dict) and not v.get("ok")]
    if bad:
        incident("selftest:" + ",".join(bad), "Tự kiểm tra phát hiện lỗi ở: " + ", ".join(bad), every=3600)
    return out
