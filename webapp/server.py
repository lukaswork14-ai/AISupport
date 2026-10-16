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
mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("application/x-apple-aspen-config", ".mobileconfig")
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


# ------------------------------------------------------------------ app iPhone (PWA)
APP_FILES = {"/manifest.webmanifest": "manifest.webmanifest", "/sw.js": "sw.js", "/icons/icon-180.png": "icons/icon-180.png",
             "/icons/icon-192.png": "icons/icon-192.png", "/icons/icon-512.png": "icons/icon-512.png",
             "/icons/icon-maskable-512.png": "icons/icon-maskable-512.png", "/apple-touch-icon.png": "icons/huy-180.png",
             "/apple-touch-icon-precomposed.png": "icons/huy-180.png", "/favicon.ico": "icons/huy-128.png",
             **{f"/icons/huy-{n}.png": f"icons/huy-{n}.png" for n in ("128", "180", "192", "512", "maskable-512")},
             "/install": "install/index.html", "/install/": "install/index.html", "/install/superHuy.mobileconfig": "install/superHuy.mobileconfig",
             "/landing": "landing/index.html", "/landing/": "landing/index.html",
             "/market": "market/index.html", "/market/": "market/index.html"}
_HELLO: dict[str, list[float]] = {}


def _hello_ok(ip: str) -> bool:
    now = time.time()
    xs = [t for t in _HELLO.get(ip, []) if t > now - 600]
    xs.append(now)
    _HELLO[ip] = xs[-40:]
    return len(xs) <= 30


def _note_device(dev: str, ua: str):
    """Báo chủ nhân khi app được đăng nhập trên thiết bị mới."""
    try:
        f = DATA_DIR / "app_devices.json"
        known = json.loads(f.read_text()) if f.exists() else []
        if dev and dev not in known:
            known.append(dev)
            f.write_text(json.dumps(known[-20:]))
            kind = "iPhone" if "iPhone" in ua else "iPad" if "iPad" in ua else "Mac" if "Macintosh" in ua else "Android" if "Android" in ua else "trình duyệt"
            security.alert_once(f"dev:{dev}", f"🔐 superHuy vừa được đăng nhập bằng mã PIN trên thiết bị mới ({kind}). "
                                "Nếu không phải anh, hãy đổi PIN ngay (app › Thêm › Đổi mã PIN).", every=10**9)
    except Exception:
        log.exception("Ghi thiết bị app lỗi")


# ------------------------------------------------------------------ tải file (link ký, hết hạn 30 phút, không cần phiên)
def sign_download(path: str, file_name: str, ttl: int = 1800) -> str:
    rel = str(Path(path).resolve().relative_to(DATA_DIR.resolve()))
    exp = int(time.time()) + ttl
    sig = hmac.new(_SECRET, f"dl|{rel}|{exp}|{file_name}".encode(), hashlib.sha256).hexdigest()[:40]
    base = ""
    try:
        from agents import lark_oauth
        base = lark_oauth.base_url()
    except Exception:
        pass
    return f"{base}/dl?f={quote(rel)}&e={exp}&n={quote(file_name)}&s={sig}"


def check_download(rel: str, exp: str, name: str, sig: str) -> Path | None:
    try:
        if int(exp) < time.time():
            return None
    except Exception:
        return None
    good = hmac.new(_SECRET, f"dl|{rel}|{exp}|{name}".encode(), hashlib.sha256).hexdigest()[:40]
    if not hmac.compare_digest(good, sig or ""):
        return None
    p = (DATA_DIR / rel).resolve()
    return p if DATA_DIR.resolve() in p.parents and p.is_file() else None


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
    server_version = "superHuy"
    sys_version = ""

    def end_headers(self):  # header bảo mật cho mọi phản hồi
        self.send_header("Strict-Transport-Security", "max-age=31536000")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), geolocation=(), microphone=(self)")
        super().end_headers()

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
        if u.path in ("/", "/index.html", "/app", "/hq", "/hq/"):
            return self._file(STATIC / "index.html", cache=False)
        if u.path.startswith("/market/") and re.fullmatch(r"/market/[a-z0-9-]{1,80}", u.path):  # trang chi tiết sản phẩm công khai
            return self._file(STATIC / "market/index.html", cache=False)
        if u.path in APP_FILES:  # ứng dụng iPhone (PWA): manifest, service worker, biểu tượng
            return self._file(STATIC / APP_FILES[u.path], cache=u.path.startswith("/icons/"))
        if u.path == "/health":
            return self._json(200, {"ok": True})
        if u.path == "/pay/receipt":  # hoá đơn (link ký)
            from agents import pay
            return self._page("<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
                              "<body style='font:16px/1.5 -apple-system,system-ui,sans-serif;padding:28px;max-width:640px;margin:auto'>" + pay.receipt_html(q.get("o", ""), q.get("s", "")) + "</body>")
        if u.path == "/api/pay/status":
            try:
                from agents import pay
                return self._json(200, pay.order_status(q.get("o", "")[:20], q.get("e", "")[:254]))
            except ValueError as e:
                return self._json(404, {"error": str(e)})
        if u.path == "/api/market/public":  # danh mục Marketplace công khai (không có nội dung skill/gói)
            try:
                from agents import market
                return self._json(200, market.public_catalog())
            except Exception:
                log.exception("Marketplace công khai lỗi")
                return self._json(500, {"error": "Marketplace tạm lỗi"})
        if u.path == "/lark/callback":  # Lark chuyển về sau khi chủ nhân bấm Cho phép
            return self._lark_callback(q)
        if u.path == "/dl":  # tải file bằng link ký (Telegram downloadFile / trình duyệt)
            p = check_download(q.get("f", ""), q.get("e", ""), q.get("n", ""), q.get("s", ""))
            if not p:
                return self._json(403, {"error": "Link tải đã hết hạn, mở lại app để lấy link mới."})
            return self._file(p, cache=False, download=q.get("n") or p.name)
        if u.path.startswith("/s/"):  # trang chia sẻ biên bản họp (công khai qua liên kết bí mật)
            return self._share(u.path)
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
        if u.path == "/connect/gemini":  # script trên Mac gửi phiên đăng nhập Gemini Notebook kèm mã dùng 1 lần
            return self._connect_gemini(u)
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
        if u.path.startswith("/api/creator/"):  # console người tạo Marketplace (khoá truy cập riêng, không dùng phiên của chủ nhân)
            return self._creator(u.path, data if isinstance(data, dict) else {})
        if u.path in ("/api/pay/webhook", "/api/pay/webhook/payos"):  # đối soát tự động (Casso/SePay/PayOS)
            from agents import pay
            try:
                if u.path.endswith("/payos"):
                    return self._json(200, pay.payos_webhook(data if isinstance(data, dict) else {}))
                tok = self.headers.get("Authorization", "").replace("Apikey ", "").replace("Bearer ", "").strip() or self.headers.get("Secure-Token", "") or self.headers.get("X-Webhook-Token", "")
                return self._json(200, pay.webhook_bank(data if isinstance(data, dict) else {}, tok))
            except PermissionError as e:
                return self._json(401, {"error": str(e)})
            except Exception:
                log.exception("Webhook thanh toán lỗi")
                return self._json(500, {"error": "webhook error"})
        if u.path in ("/api/pay/order", "/api/pay/resend", "/api/pay/mine"):  # khách mua trên trang công khai
            ip = self.headers.get("X-Real-IP") or self.client_address[0]
            if not _hello_ok("pay:" + ip):
                return self._json(429, {"error": "Thao tác quá nhanh, thử lại sau ít phút nhé."})
            try:
                from agents import pay
                if u.path == "/api/pay/order":
                    return self._json(200, pay.create_order(str(data.get("lid", ""))[:20], str(data.get("email", "")), "public"))
                if u.path == "/api/pay/resend":
                    return self._json(200, pay.resend(str(data.get("email", ""))))
                return self._json(200, pay.entitlements(str(data.get("email", ""))))
            except ValueError as e:
                return self._json(400, {"error": str(e)[:200]})
            except Exception:
                log.exception("Đặt mua lỗi")
                return self._json(500, {"error": "Chưa tạo được đơn, bạn thử lại sau nhé."})
        if u.path in ("/api/waitlist", "/api/market/interest"):  # form công khai (giới hạn tần suất)
            ip = self.headers.get("X-Real-IP") or self.client_address[0]
            if not _hello_ok("wl:" + ip):
                return self._json(429, {"error": "Anh/chị thử lại sau ít phút nhé."})
            try:
                from agents import leads, market
                if u.path == "/api/waitlist":
                    leads.add(str(data.get("email", "")), str(data.get("src", ""))[:120])
                elif u.path == "/api/market/interest":
                    market.public_interest(str(data.get("lid", ""))[:20], str(data.get("email", "")))
            except ValueError as e:
                return self._json(400, {"error": str(e)[:200]})
            except Exception:
                log.exception("Form công khai lỗi")
                return self._json(500, {"error": "Chưa ghi được, anh/chị thử lại sau nhé."})
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
        if u.path == "/api/app/hello":  # mở app iPhone (không qua Telegram): chỉ cho nhập PIN
            if not OWNER_CHAT_ID or not security.pin_enabled():
                return self._json(403, {"error": "Chưa đặt mã PIN cho superHuy. Mở app trong Telegram › Thêm › Đổi mã PIN để đặt, rồi đăng nhập lại."})
            ip = self.headers.get("X-Forwarded-For", self.client_address[0]).split(",")[0].strip()
            if not _hello_ok(ip):
                return self._json(429, {"error": "Thử lại sau ít phút."})
            return self._json(200, {"need_pin": True, "pre": make_pre(OWNER_CHAT_ID), "pin_len": security.pin_length(),
                                    "wait": security.locked_out(), "user": {"first_name": "Huy"}})
        if u.path == "/api/pin":
            if not check_pre(data.get("pre", "")):
                return self._json(401, {"error": "Phiên đăng nhập hết hạn, hãy mở lại app.", "expired": True})
            app = bool(data.get("app"))
            ok, msg = security.verify(str(data.get("pin", ""))[:12], "App iPhone" if app else "Mini App")
            if not ok:
                if app:
                    security.alert_once("app-fail", "⚠️ Có lượt nhập sai mã PIN trên app superHuy (ngoài Telegram). Nếu không phải anh, hãy đổi PIN (app › Thêm › Đổi mã PIN).")
                return self._json(200, {"ok": False, "msg": msg, "wait": security.locked_out()})
            if app:
                _note_device(str(data.get("device", ""))[:40], self.headers.get("User-Agent", ""))
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

    _cg_fails: list = []

    def _connect_gemini(self, u):
        from agents import gemini_notebook
        now = time.time()
        Handler._cg_fails = [t for t in Handler._cg_fails if t > now - 600]
        if len(Handler._cg_fails) >= 20:
            return self._json(429, {"error": "Thử sai quá nhiều lần, đợi 10 phút rồi chạy lại."})
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > 2_000_000:
            return self._json(400, {"error": "Thiếu dữ liệu phiên đăng nhập"})
        body = self.rfile.read(n)
        try:
            msg = gemini_notebook.accept(dict(parse_qsl(u.query)).get("code", ""), body)
        except Exception as e:
            Handler._cg_fails.append(now)
            return self._json(400, {"error": str(e)[:300]})
        return self._json(200, {"ok": True, "message": msg})

    def _share(self, path: str):
        from agents import meeting, meeting_share
        m = re.fullmatch(r"/s/([A-Za-z0-9_-]{8,40})(/audio)?", path)
        rec = meeting_share.get(m.group(1)) if m else None
        if not rec:
            return self._page(meeting_share.dead_page(), 404)
        if m.group(2):
            if "audio" not in rec["parts"]:
                return self._json(404, {"error": "not found"})
            return self._file(meeting._dir(rec["mid"]) / "audio.mp3", cache=False)
        meeting_share.hit(rec["token"])
        return self._page(meeting_share.render(rec))

    def _creator(self, path: str, data: dict):
        from agents import market
        ip = self.headers.get("X-Real-IP") or self.client_address[0]
        if not _hello_ok("cr:" + ip):
            return self._json(429, {"error": "Thao tác quá nhanh, thử lại sau ít phút nhé."})
        try:
            if path == "/api/creator/signup":
                return self._json(200, market.creator_signup(str(data.get("name", "")), str(data.get("email", "")), str(data.get("bio", ""))))
            c = market.creator_auth(self.headers.get("X-Creator-Key", ""))
            if path == "/api/creator/console":
                return self._json(200, market.creator_console(c))
            if path == "/api/creator/get":
                return self._json(200, market.creator_get(c, str(data.get("lid", ""))[:20]))
            if path == "/api/creator/save":
                return self._json(200, market.creator_save(c, data))
            if path == "/api/creator/revenue":
                from agents import pay
                return self._json(200, pay.seller_revenue(c["id"]))
            if path == "/api/creator/bank":
                from agents import pay
                return self._json(200, pay.seller_bank(c["id"], str(data.get("bank", "")), str(data.get("account", "")), str(data.get("name", ""))))
            if path == "/api/creator/pack":
                market.creator_ai_ok(c)
                return self._json(200, market.pack(str(data.get("raw", ""))[:20000], str(data.get("hint_type", "")),
                                                   str(data.get("source_url", ""))[:500], bool(data.get("clone"))))
            return self._json(404, {"error": "not found"})
        except PermissionError as e:
            return self._json(401, {"error": str(e)})
        except ValueError as e:
            return self._json(400, {"error": str(e)[:300]})
        except Exception:
            log.exception("Console người tạo lỗi")
            return self._json(500, {"error": "Có lỗi, thử lại sau ít phút nhé."})

    def _page(self, body: str, code: int = 200):
        b = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
                         "font-src https://fonts.gstatic.com; img-src 'self' data:; media-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(b)

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

    def _file(self, path: Path, cache: bool, download: str = ""):
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
        if download:
            self.send_header("Content-Disposition", f"attachment; filename=\"video.mp4\"; filename*=UTF-8''{quote(download)}")
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
