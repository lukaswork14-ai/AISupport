"""Đường hầm HTTPS miễn phí (Cloudflare Quick Tunnel) để Telegram mở được Mini App chạy trên máy này.
- Không cần tên miền, không cần mở port router. URL đổi mỗi lần khởi động, bot tự cập nhật nút menu.
- Khi có tên miền riêng: đặt WEBAPP_URL=https://app.tenmien.com trong .env (dùng Cloudflare named tunnel)."""
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import threading
import time

import requests

from config import BASE_DIR, DATA_DIR

STATE = DATA_DIR / "tunnel.json"

log = logging.getLogger("tunnel")
URL_RE = re.compile(r"https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com")  # bỏ qua api.trycloudflare.com (dòng báo lỗi)


def binary() -> str | None:
    local = BASE_DIR / "bin" / "cloudflared"
    if local.exists():
        return str(local)
    return shutil.which("cloudflared")


class Tunnel:
    def __init__(self, port: int, on_url):
        self.port, self.on_url = port, on_url
        self.url = None
        self.proc = None
        self._stop = False

    def start(self):
        fixed = os.getenv("WEBAPP_URL", "").strip()
        if fixed:
            self.url = fixed.rstrip("/")
            # chạy ở thread riêng: on_url chờ coroutine trên event loop, gọi thẳng từ post_init sẽ treo loop (TimeoutError)
            threading.Thread(target=self.on_url, args=(self.url,), daemon=True, name="tunnel").start()
            return
        threading.Thread(target=self._loop, daemon=True, name="tunnel").start()

    def _reuse(self) -> bool:
        """Dùng lại đường hầm đang chạy từ lần trước (để địa chỉ app không đổi khi bot khởi động lại)."""
        try:
            st = json.loads(STATE.read_text())
            os.kill(int(st["pid"]), 0)  # tiến trình còn sống?
            r = requests.get(st["url"] + "/health", timeout=10)
            if r.ok:
                self.url = st["url"]
                log.info("Dùng lại đường hầm cũ: %s", self.url)
                self.on_url(self.url)
                self._watch_pid = int(st["pid"])
                return True
            self._kill_old(int(st["pid"]))
        except Exception:
            pass
        return False

    @staticmethod
    def _kill_old(pid: int):
        """Dọn tiến trình cloudflared cũ đã hỏng để không chạy ngầm mãi."""
        try:
            import signal
            os.kill(pid, signal.SIGTERM)
            log.info("Đã đóng tiến trình đường hầm cũ (pid %s)", pid)
        except Exception:
            pass

    def _loop(self):
        if self._reuse():
            while not self._stop:  # theo dõi, nếu đường hầm chết thì mở cái mới
                time.sleep(30)
                try:
                    os.kill(self._watch_pid, 0)
                    if requests.get(self.url + "/health", timeout=15).ok:
                        continue
                except Exception:
                    pass
                log.warning("Đường hầm cũ không còn hoạt động, mở đường hầm mới")
                self._kill_old(self._watch_pid)
                break
        backoff = 5
        while not self._stop:
            exe = binary()
            if not exe:
                log.error("Chưa có cloudflared. Chạy Cai-dat-miniapp.command để cài.")
                return
            log.info("Mở đường hầm Cloudflare...")
            logf = DATA_DIR / "tunnel.log"
            # ghi ra file (không dùng pipe) + phiên riêng: đường hầm sống tiếp khi bot khởi động lại,
            # nên địa chỉ Mini App giữ nguyên, Telegram không bị giữ địa chỉ cũ
            with open(logf, "w") as out:
                self.proc = subprocess.Popen([exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{self.port}"],
                                             stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
            found = None
            for _ in range(120):  # tối đa 60 giây chờ URL
                time.sleep(0.5)
                m = URL_RE.search(logf.read_text(errors="ignore"))
                if m:
                    found = m.group(0)
                    break
                if self.proc.poll() is not None:
                    break
            if found:
                self.url = found
                log.info("Mini App URL: %s", self.url)
                STATE.write_text(json.dumps({"pid": self.proc.pid, "url": self.url}))
                time.sleep(3)  # chờ DNS của trycloudflare sẵn sàng
                try:
                    self.on_url(self.url)
                except Exception:
                    log.exception("Không cập nhật được nút menu")
                backoff = 5
            fails = 0
            while not self._stop and self.proc.poll() is None:
                time.sleep(30)
                if not found:
                    break
                try:  # cloudflared còn chạy nhưng Cloudflare đã hủy đường hầm ("Tunnel not found") -> mở lại
                    ok = requests.get(self.url + "/health", timeout=15).ok
                except Exception:
                    ok = False
                fails = 0 if ok else fails + 1
                if fails >= 3:
                    log.warning("Đường hầm không phản hồi 3 lần liên tiếp, đóng để mở lại")
                    try:
                        self.proc.kill()
                    except Exception:
                        pass
                    break
            log.warning("Đường hầm đã đóng, mở lại sau %ss", backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)

    def stop(self):
        self._stop = True


def arch() -> str:
    m = platform.machine().lower()
    return "arm64" if m in ("arm64", "aarch64") else "amd64"
