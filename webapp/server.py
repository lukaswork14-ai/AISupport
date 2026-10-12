"""Server cho Telegram Mini App, chỉ dùng thư viện chuẩn (không cần cài thêm).
- Xác thực: Telegram initData (HMAC với token bot) + chỉ chủ nhân (OWNER_CHAT_ID) được dùng.
- API: /api/auth, /api/bootstrap, /api/run, /api/job, /media (ảnh/video trong data/)."""
import hashlib
import html
import hmac
import json
import re
import logging
import mimetypes
import secrets
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, quote, urlparse

from config import DATA_DIR, OWNER_CHAT_ID, TELEGRAM_TOKEN
from core import registry, security

log = logging.getLogger("webapp")
STATIC = Path(__file__).parent / "static"
SESSION_TTL = 8 * 3600
_SECRET = secrets.token_bytes(32)  # đổi mỗi lần khởi động
JOBS: dict[str, dict] = {}
EXTRA_BOOTSTRAP = None  # main.py có thể gắn hàm trả thêm dữ liệu cho màn hình chính


# ------------------------------------------------------------------ xác thực
def check_init_data(init_data: str, max_age: int = 86400) -> dict | None:
    """Kiểm tra chữ ký Telegram WebApp. Trả về user dict nếu hợp lệ."""
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    their_hash = pairs.pop("hash", "")
    if not their_hash:
        return None
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", TELEGRAM_TOKEN.encode(), hashlib.sha256).digest()
    ours = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(ours, their_hash):
        return None
    if time.time() - int(pairs.get("auth_date", 0)) > max_age:
        return None
    try:
        return json.loads(pairs.get("user", "{}"))
    except Exception:
        return None


SESSIONS: dict[str, dict] = {}  # phiên chỉ nằm trong bộ nhớ: khởi động lại bot = phải nhập PIN lại
IDLE_SEC = 20 * 60  # không thao tác 20 phút -> khóa
PRE_TTL = 300


def make_session(uid: int) -> str:
    tok = secrets.token_urlsafe(32)
    now = time.time()
    for k in [k for k, v in SESSIONS.items() if v["exp"] < now or v["last"] < now - IDLE_SEC]:
        SESSIONS.pop(k, None)
    SESSIONS[tok] = {"uid": uid, "exp": now + SESSION_TTL, "last": now}
    return tok


def check_session(tok: str) -> bool:
    v = SESSIONS.get(tok or "")
    now = time.time()
    if not v or v["uid"] != OWNER_CHAT_ID or v["exp"] < now or v["last"] < now - IDLE_SEC:
        SESSIONS.pop(tok or "", None)
        return False
    v["last"] = now
    return True


def end_all_sessions():
    SESSIONS.clear()


def make_pre(uid: int) -> str:
    """Vé tạm (5 phút) sau khi xác thực Telegram, chờ nhập PIN."""
    exp = int(time.time()) + PRE_TTL
    sig = hmac.new(_SECRET, f"pre.{uid}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
    return f"{uid}.{exp}.{sig}"


def check_pre(pre: str) -> bool:
    try:
        uid, exp, sig = pre.split(".")
        good = hmac.new(_SECRET, f"pre.{uid}.{exp}".encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(good, sig) and int(exp) > time.time() and int(uid) == OWNER_CHAT_ID
    except Exception:
        return False


# ------------------------------------------------------------------ tiện ích
def media_url(path: str | None, tok: str) -> str | None:
    if not path:
        return None
    try:
        rel = Path(path).resolve().relative_to(DATA_DIR.resolve())
    except Exception:
        return None
    return f"/media?f={quote(str(rel))}&s={quote(tok)}&v={int(Path(path).stat().st_mtime) if Path(path).exists() else 0}"


def present(obj, tok: str):
    """Đổi các đường dẫn file (image/video/audio) thành URL xem được trong Mini App."""
    if isinstance(obj, list):
        return [present(x, tok) for x in obj]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("image", "video", "audio") and isinstance(v, str):
                out[k] = media_url(v, tok)
            else:
                out[k] = present(v, tok)
        return out
    return obj


def _qc_fail(agent, action, e):
    try:
        from core import qc
        qc.job_failed(agent, action, e)
    except Exception:
        pass


def start_job(agent: str, action: str, params: dict) -> str:
    jid = uuid.uuid4().hex[:10]
    JOBS[jid] = {"id": jid, "agent": agent, "action": action, "status": "running", "started": time.time()}

    def work():
        try:
            JOBS[jid]["result"] = registry.run(agent, action, params)
            JOBS[jid]["status"] = "done"
        except Exception as e:
            log.exception("Job %s.%s lỗi", agent, action)
            _qc_fail(agent, action, e)
            JOBS[jid]["status"] = "error"
            JOBS[jid]["error"] = str(e)
        JOBS[jid]["ended"] = time.time()
        for k in [k for k, j in JOBS.items() if j.get("ended", time.time()) < time.time() - 3600]:
            JOBS.pop(k, None)

    threading.Thread(target=work, daemon=True).start()
    return jid


CHAT: list[dict] = []  # lịch sử trò chuyện trong app (giữ 16 lượt gần nhất)


CHAT_ACTS: dict[str, list] = {}  # câu trả lời -> các hành động superHuy đã làm (để hiện chip trong app)


def start_chat(text: str) -> str:
    jid = uuid.uuid4().hex[:10]
    JOBS[jid] = {"id": jid, "agent": "chat", "action": "chat", "status": "running", "started": time.time()}

    def work():
        import brain
        CHAT.append({"role": "user", "content": text})
        try:
            r = brain.chat_ex(CHAT[-16:])
            ans = r["text"]
            if r.get("actions"):
                CHAT_ACTS[ans] = r["actions"]
            JOBS[jid].update(status="done", result={"text": ans, "actions": r["actions"]})
        except Exception as e:
            log.exception("Chat lỗi")
            _qc_fail("chat", "chat", e)
            ans = f"⚠️ Có lỗi khi xử lý: {e}"
            JOBS[jid].update(status="error", error=str(e))
        CHAT.append({"role": "assistant", "content": ans})
        del CHAT[:-16]
        JOBS[jid]["ended"] = time.time()

    threading.Thread(target=work, daemon=True).start()
    return jid


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "AgentArmy/1.0"

    def log_message(self, fmt, *args):  # không ghi log mỗi request (tránh lộ query)
        pass

    def _json(self, code: int, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if n > 2_000_000:
            raise ValueError("payload too large")
        return json.loads(self.rfile.read(n) or b"{}")

    def _tok(self, q: dict) -> str:
        return self.headers.get("X-Session") or q.get("s", "")

    def do_GET(self):
        u = urlparse(self.path)
        q = dict(parse_qsl(u.query))
        if u.path in ("/", "/index.html"):
            return self._file(STATIC / "index.html", cache=False)
        if u.path == "/health":
            return self._json(200, {"ok": True})
        if u.path == "/lark/callback":  # Lark chuyển về sau khi chủ nhân bấm Cho phép
            return self._lark_callback(q)
        tok = self._tok(q)
        if not check_session(tok):
            return self._json(401, {"error": "Phiên hết hạn, hãy mở lại app từ Telegram."})
        if u.path == "/api/bootstrap":
            return self._json(200, self._bootstrap(tok))
        if u.path == "/api/job":
            j = JOBS.get(q.get("id", ""))
            if not j:
                return self._json(404, {"error": "Không tìm thấy job"})
            return self._json(200, present(j, tok))
        if u.path == "/media":
            p = (DATA_DIR / q.get("f", "")).resolve()
            if DATA_DIR.resolve() not in p.parents or not p.is_file():
                return self._json(404, {"error": "not found"})
            return self._file(p, cache=True)
        return self._json(404, {"error": "not found"})

    def _upload(self, u):
        """Nhận file âm thanh theo từng phần (≤ 8 MB/phần, vượt giới hạn 100 MB/request của đường hầm):
        POST /api/upload?id=<mã>&seq=<n> thân = dữ liệu nhị phân. Ghi nối vào data/meetings/_inbox/<mã>.part"""
        q = dict(parse_qsl(u.query))
        if not check_session(self._tok(q)):
            return self._json(401, {"error": "Phiên hết hạn, hãy mở lại app từ Telegram."})
        uid = q.get("id", "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{6,40}", uid):
            return self._json(400, {"error": "Mã tải lên không hợp lệ"})
        n = int(self.headers.get("Content-Length") or 0)
        if n > 9_000_000:
            return self._json(413, {"error": "Phần tải lên quá lớn"})
        from agents import meeting
        meeting.INBOX.mkdir(parents=True, exist_ok=True)
        part = meeting.INBOX / f"{uid}.part"
        seq = int(q.get("seq", "0"))
        size = part.stat().st_size if part.exists() else 0
        if seq == 0 and size:
            part.unlink()
            size = 0
        if size + n > 900_000_000:
            return self._json(413, {"error": "File quá lớn (tối đa ~900 MB)"})
        left = n
        with open(part, "ab") as f:
            while left > 0:
                chunk = self.rfile.read(min(65536, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        return self._json(200, {"ok": True, "size": part.stat().st_size})

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/api/upload":
            try:
                return self._upload(u)
            except Exception as e:
                log.exception("Tải lên lỗi")
                return self._json(500, {"error": str(e)[:200]})
        try:
            data = self._body()
        except Exception:
            return self._json(400, {"error": "Dữ liệu không hợp lệ"})
        if u.path == "/api/clienterror":  # lỗi giao diện Mini App -> QC (không chứa dữ liệu nhạy cảm)
            try:
                from core import qc
                qc.client_error({k: str(data.get(k, ""))[:300] for k in ("msg", "src", "line")})
            except Exception:
                pass
            return self._json(200, {"ok": True})
        if u.path == "/api/auth":
            user = check_init_data(data.get("initData", ""))
            if not user or not OWNER_CHAT_ID or int(user.get("id", 0)) != OWNER_CHAT_ID:
                if user:  # người thật trên Telegram nhưng không phải chủ nhân: chặn + báo động
                    who = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()
                    uname = f" @{user['username']}" if user.get("username") else ""
                    security.alert_once(f"app:{user.get('id')}", f"🚨 Có người lạ ({who}{uname}, ID {user.get('id')}) "
                                        "vừa mở Mini App của bạn. Đã chặn, họ không thấy dữ liệu gì.")
                return self._json(403, {"error": "Ứng dụng riêng tư. Bạn không có quyền truy cập."})
            info = {"first_name": user.get("first_name", "")}
            if security.pin_enabled():
                return self._json(200, {"need_pin": True, "pre": make_pre(int(user["id"])), "pin_len": security.pin_length(),
                                        "wait": security.locked_out(), "user": info})
            return self._json(200, {"session": make_session(int(user["id"])), "user": info})
        if u.path == "/api/pin":
            if not check_pre(data.get("pre", "")):
                return self._json(401, {"error": "Phiên đăng nhập hết hạn, hãy mở lại app.", "expired": True})
            ok, msg = security.verify(str(data.get("pin", ""))[:12], "Mini App")
            if not ok:
                return self._json(200, {"ok": False, "msg": msg, "wait": security.locked_out()})
            security.unlock_bot()
            return self._json(200, {"ok": True, "session": make_session(OWNER_CHAT_ID)})
        tok = self._tok({})
        if not check_session(tok):
            return self._json(401, {"error": "Phiên hết hạn, hãy mở lại app từ Telegram."})
        if u.path == "/api/chat":  # trò chuyện với super bot ngay trong app
            text = (data.get("text") or "").strip()[:2000]
            if not text:
                return self._json(400, {"error": "Tin nhắn trống"})
            return self._json(200, {"job": start_chat(text)})
        if u.path == "/api/lock":  # khóa ngay: đăng xuất mọi phiên + khóa bot
            end_all_sessions()
            security.lock_bot()
            return self._json(200, {"ok": True})
        if u.path == "/api/chat/reset":
            CHAT.clear()
            return self._json(200, {"ok": True})
        if u.path == "/api/run":
            agent, action, params = data.get("agent", ""), data.get("action", ""), data.get("params") or {}
            try:
                act = registry.get_action(agent, action)
            except KeyError as e:
                return self._json(404, {"error": e.args[0] if e.args else str(e)})
            if act.long:
                return self._json(200, {"job": start_job(agent, action, params)})
            try:
                return self._json(200, {"result": present(registry.run(agent, action, params), tok)})
            except Exception as e:
                log.exception("Lỗi chạy %s.%s", agent, action)
                _qc_fail(agent, action, e)
                return self._json(200, {"error": str(e)})
        return self._json(404, {"error": "not found"})

    def _lark_callback(self, q):
        from agents import lark_oauth
        from core import notify
        purpose = lark_oauth.check_state(q.get("state", ""))
        if not purpose or not q.get("code"):
            return self._html("⚠️ Liên kết đã hết hạn hoặc không hợp lệ. Hãy bấm lại nút trong Mini App.")
        if purpose == "calendar":
            from agents import lark_calendar
            try:
                host = (self.headers.get("Host") or "").strip()
                local = host.split(":")[0] in ("127.0.0.1", "localhost")
                # đổi code bằng đúng địa chỉ trình duyệt vừa được chuyển về (địa chỉ máy hoặc đường hầm)
                redir = f"http://{host}/lark/callback" if local else lark_oauth.redirect_uri()
                name = lark_calendar.exchange(q["code"], redir)
                notify.send(text=f"📅 Đã kết nối lịch Lark ({name}). Lịch và lời mời họp Lark sẽ hiện trong Mini App.")
                return self._html(f"✅ Đã kết nối lịch Lark ({name}). Bạn có thể đóng trang này và quay lại Mini App.")
            except Exception as e:
                log.exception("Lark calendar lỗi")
                return self._html(f"⚠️ Chưa kết nối được lịch Lark: {e}")

        def work(code=q["code"]):
            try:
                res = lark_oauth.join_all(code)
                notify.send(text="💬 Lark: " + lark_oauth.summary(res))
            except Exception as e:
                log.exception("Lark join lỗi")
                notify.send(text=f"⚠️ Không thêm được bot vào group Lark: {e}")
        threading.Thread(target=work, daemon=True).start()
        return self._html("✅ Đã nhận quyền. Bot đang tự thêm vào các group Lark của bạn, kết quả sẽ gửi vào Telegram trong ít phút. Bạn có thể đóng trang này.")

    def _html(self, msg: str):
        body = (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                f"<body style='font:17px -apple-system,sans-serif;padding:32px;max-width:560px;margin:auto'>{html.escape(msg)}</body>").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _bootstrap(self, tok):
        out = {"agents": registry.describe(), "chat": [({**m, "actions": CHAT_ACTS[m["content"]]} if m.get("role") == "assistant" and m.get("content") in CHAT_ACTS else m) for m in CHAT[-16:]],
               "jobs": [present(j, tok) for j in JOBS.values() if j["status"] == "running"]}
        if EXTRA_BOOTSTRAP:
            try:
                out.update(present(EXTRA_BOOTSTRAP(), tok))
            except Exception:
                log.exception("bootstrap extra lỗi")
        return out

    def _file(self, path: Path, cache: bool):
        if not path.is_file():
            return self._json(404, {"error": "not found"})
        size = path.stat().st_size
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):  # cho phép tua video
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else 0
            end = int(b) if b else size - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "private, max-age=86400" if cache else "no-cache")
        self.end_headers()
        with open(path, "rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(65536, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)


def serve(port: int) -> ThreadingHTTPServer:
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True, name="webapp").start()
    log.info("Mini App server chạy tại http://127.0.0.1:%s", port)
    return httpd
