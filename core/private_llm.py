"""superYou Private: chạy AI tại chỗ (Ollama / LM Studio / vLLM, giao thức OpenAI) để dữ liệu không rời máy chủ khách.

Cấu hình trong .env của từng máy chủ:
  LOCAL_LLM_BASE_URL = http://127.0.0.1:11434/v1   (Ollama mặc định)
  LOCAL_LLM_MODEL    = qwen2.5:14b                   (model đã `ollama pull`)
  PRIVATE_MODE       = off | hybrid | strict
    off    : chỉ dùng mô hình đám mây (mặc định).
    hybrid : việc thường ngày (phân loại, tóm tắt ngắn, JSON) chạy tại chỗ; việc khó và trò chuyện có công cụ dùng đám mây.
    strict : mọi thứ chạy tại chỗ, không gọi ra ngoài (gói Doanh nghiệp Private).
Chế độ có thể đổi lúc chạy trong HQ › Hệ thống (lưu DATA_DIR/private_llm.json, ưu tiên hơn .env).
"""
import json
import os
import threading
import time

from config import DATA_DIR

FILE = DATA_DIR / "private_llm.json"
_LOCK = threading.Lock()
MODES = {"off": "Đám mây", "hybrid": "Kết hợp: việc thường tại chỗ", "strict": "Riêng tư tuyệt đối: tất cả tại chỗ"}
_client = None
_client_key = ""
_ping: dict = {"at": 0.0, "ok": False, "detail": "", "models": []}


def _cfg() -> dict:
    d = {}
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    base = (d.get("base_url") or os.getenv("LOCAL_LLM_BASE_URL", "")).strip().rstrip("/")
    model = (d.get("model") or os.getenv("LOCAL_LLM_MODEL", "")).strip()
    mode = (d.get("mode") or os.getenv("PRIVATE_MODE", "off")).strip().lower()
    if mode not in MODES or not base or not model:
        mode = "off" if (mode not in MODES or not base or not model) else mode
    return {"base_url": base, "model": model, "mode": mode}


def mode() -> str:
    return _cfg()["mode"]


def client():
    """Client OpenAI-compatible trỏ vào máy chủ AI tại chỗ (không cần khoá thật)."""
    global _client, _client_key
    c = _cfg()
    key = c["base_url"]
    if _client is None or _client_key != key:
        from openai import OpenAI
        _client = OpenAI(base_url=c["base_url"], api_key=os.getenv("LOCAL_LLM_API_KEY", "ollama"), timeout=120)
        _client_key = key
    return _client


def pick(task: str = "chat", tools: bool = False) -> tuple[bool, str]:
    """Chọn nơi chạy cho một tác vụ. Trả (local, model). task: chat|json|classify|summarize|long."""
    c = _cfg()
    if c["mode"] == "off":
        return False, ""
    if c["mode"] == "strict":
        return True, c["model"]
    # hybrid: tại chỗ cho việc ngắn, không công cụ
    if tools or task in ("long",):
        return False, ""
    return True, c["model"]


def ping(force: bool = False) -> dict:
    """Kiểm tra máy chủ AI tại chỗ (cache 60 giây)."""
    c = _cfg()
    if not c["base_url"]:
        return {"ok": False, "detail": "Chưa đặt LOCAL_LLM_BASE_URL", "models": [], "configured": False}
    if not force and time.time() - _ping["at"] < 60:
        return {**_ping, "configured": True}
    try:
        ms = client().models.list()
        names = [m.id for m in ms.data][:40]
        ok = not c["model"] or c["model"] in names or any(n.startswith(c["model"]) for n in names)
        _ping.update({"at": time.time(), "ok": ok, "models": names,
                      "detail": "Sẵn sàng" if ok else f"Máy chủ chạy nhưng chưa có model {c['model']} (ollama pull {c['model']})"})
    except Exception as e:
        _ping.update({"at": time.time(), "ok": False, "models": [], "detail": f"Không kết nối được: {str(e)[:120]}"})
    return {**_ping, "configured": True}


def status() -> dict:
    c = _cfg()
    p = ping()
    txt = f"Chế độ: {MODES[c['mode']]}. Máy chủ tại chỗ: {p['detail']}" if c["base_url"] else "Chưa cấu hình AI tại chỗ (gói Doanh nghiệp Private)."
    return {"text": txt, "mode": c["mode"], "modes": MODES, "base_url": c["base_url"], "model": c["model"], "ping": p}


def set_mode(mode: str, base_url: str = "", model: str = "") -> dict:
    """Đổi chế độ riêng tư lúc chạy (chủ sàn / quản trị khách)."""
    mode = (mode or "").strip().lower()
    if mode not in MODES:
        raise ValueError("Chế độ phải là off, hybrid hoặc strict")
    with _LOCK:
        try:
            d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
        except Exception:
            d = {}
        d["mode"] = mode
        if base_url:
            d["base_url"] = base_url.strip().rstrip("/")[:200]
        if model:
            d["model"] = model.strip()[:80]
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(FILE)
    c = _cfg()
    if mode != "off" and c["mode"] == "off":
        return {"text": "Đã lưu nhưng chưa bật được: cần LOCAL_LLM_BASE_URL và LOCAL_LLM_MODEL (hoặc nhập ở đây).", **status()}
    return {"text": f"Đã chuyển sang: {MODES[mode]}.", **status()}


def test(prompt: str = "Trả lời đúng một từ: xin chào") -> dict:
    """Gửi một câu thử tới AI tại chỗ để kiểm tra tốc độ."""
    c = _cfg()
    if not c["base_url"] or not c["model"]:
        raise RuntimeError("Chưa cấu hình AI tại chỗ.")
    t = time.time()
    r = client().chat.completions.create(model=c["model"], messages=[{"role": "user", "content": prompt[:500]}], max_tokens=60)
    out = (r.choices[0].message.content or "").strip()
    return {"text": f"AI tại chỗ trả lời trong {time.time() - t:.1f}s: {out[:200]}", "reply": out, "seconds": round(time.time() - t, 1)}
