"""Bộ nhớ dài hạn của superHuy: những điều superHuy biết về anh Huy (sức khoẻ, mục tiêu, sở thích, công việc,
các mối quan hệ, cách làm việc). Dùng làm ngữ cảnh cho MỌI câu trả lời, lịch trình và gợi ý, để ngày càng hiểu anh hơn.
- Tự học: sau mỗi lượt chat, AI trích ra điều đáng nhớ lâu dài (nếu có) và lưu lại.
- Anh xem, thêm, xoá trong Mini App (Phát triển › superHuy hiểu về anh) hoặc nói "nhớ giúp...", "quên ..." trong chat.
Lưu cục bộ: data/memory.json (quyền 600)."""
import datetime as dt
import json
import logging
import os
import re
import threading
import uuid

from config import DATA_DIR

log = logging.getLogger("memory")
FILE = DATA_DIR / "memory.json"
KINDS = {"profile": "Bản thân", "health": "Sức khoẻ", "goal": "Mục tiêu", "work": "Công việc", "preference": "Sở thích & cách làm việc",
         "relation": "Gia đình & quan hệ", "finance": "Tài chính", "routine": "Nếp sinh hoạt"}
MAX_FACTS = 300
_lock = threading.Lock()


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _load() -> list[dict]:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(items: list[dict]):
    FILE.write_text(json.dumps(items[-MAX_FACTS:], ensure_ascii=False, indent=1), encoding="utf-8")
    try:
        os.chmod(FILE, 0o600)
    except Exception:
        pass
    try:
        export_to_vault(items[-MAX_FACTS:])
    except Exception:
        log.debug("Không ghi được trí nhớ sang Obsidian", exc_info=True)


# ------------------------------------------------------------------ hai chiều với Obsidian
VAULT_NOTE = "02 Areas/superHuy/superHuy hieu ve anh.md"
EXTRA_HEAD = "## Anh bổ sung"


def _note_path():
    from config import OBSIDIAN_VAULT
    return OBSIDIAN_VAULT / VAULT_NOTE


def vault_additions() -> list[str]:
    """Những dòng anh tự viết trong Obsidian dưới mục "Anh bổ sung" của ghi chú trí nhớ -> superHuy coi như điều đã biết."""
    try:
        text = _note_path().read_text(encoding="utf-8")
    except Exception:
        return []
    if EXTRA_HEAD not in text:
        return []
    sec = text.split(EXTRA_HEAD, 1)[1]
    sec = re.split(r"\n## ", sec, 1)[0]
    out = []
    for ln in sec.splitlines():
        ln = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[.\]\s*)?", "", ln).strip()
        if len(ln) > 3 and not ln.startswith(("<!--", ">")) and not SECRET.search(ln):
            out.append(ln[:300])
    return out[:80]


def export_to_vault(items: list[dict] | None = None):
    """Ghi bản đọc được của trí nhớ sang Obsidian (giữ nguyên mục "Anh bổ sung" anh tự viết)."""
    p = _note_path()
    items = _load() if items is None else items
    keep = ""
    if p.exists():
        old = p.read_text(encoding="utf-8")
        if EXTRA_HEAD in old:
            keep = old.split(EXTRA_HEAD, 1)[1]
            keep = re.split(r"\n## ", keep, 1)[0].strip("\n")
    by: dict[str, list[dict]] = {}
    for it in items:
        by.setdefault(it.get("kind", "profile"), []).append(it)
    lines = ["---", "type: superhuy-memory", "generated_by: superhuy", f"updated: {_now()}", "tags: [superhuy, second-brain]", "---", "",
             "# superHuy hiểu về anh", "",
             "> [!info] superHuy tự cập nhật phần dưới từ các cuộc trò chuyện. Muốn superHuy biết thêm hoặc sửa điều chưa đúng, "
             "viết vào mục **Anh bổ sung** ở cuối (mỗi ý 1 dòng gạch đầu dòng). superHuy đọc lại mục đó mỗi lần trả lời.", ""]
    for k, label in KINDS.items():
        if by.get(k):
            lines += [f"## {label}"] + [f"- {it['text']}" for it in by[k]] + [""]
    lines += [EXTRA_HEAD, keep or "<!-- Ví dụ: - Ưu tiên quý này: đưa Sellnity đạt 1 triệu USD doanh thu -->", ""]
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines), encoding="utf-8")


def _norm(s: str) -> str:
    return re.sub(r"\W+", " ", (s or "").lower()).strip()


def facts() -> list[dict]:
    return _load()


def add(text: str, kind: str = "profile", source: str = "anh") -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("Nội dung trống")
    kind = kind if kind in KINDS else "profile"
    with _lock:
        items = _load()
        n = _norm(text)
        for it in items:
            if _norm(it["text"]) == n:
                return it
        it = {"id": uuid.uuid4().hex[:8], "text": text[:300], "kind": kind, "source": source, "at": _now()}
        items.append(it)
        _save(items)
    return it


def update(fid: str, text: str) -> dict:
    with _lock:
        items = _load()
        for it in items:
            if it["id"] == fid:
                it["text"], it["at"] = text.strip()[:300], _now()
        _save(items)
    return {"text": "Đã cập nhật"}


def remove(fid: str) -> dict:
    with _lock:
        _save([it for it in _load() if it["id"] != fid])
    return {"text": "Đã quên điều này"}


def forget_matching(query: str) -> int:
    q = _norm(query)
    with _lock:
        items = _load()
        keep = [it for it in items if q not in _norm(it["text"])]
        _save(keep)
    return len(items) - len(keep)


def context(max_chars: int = 3500) -> str:
    """Khối văn bản ngắn gọn đưa vào prompt."""
    items = _load()
    if not items and not vault_additions():
        return ""
    by: dict[str, list[str]] = {}
    for it in items[::-1]:
        by.setdefault(it["kind"], []).append(it["text"])
    out, n = ["NHỮNG ĐIỀU superHuy ĐÃ BIẾT VỀ ANH (dùng để cá nhân hoá, không nhắc lại nguyên văn nếu không cần):"], 0
    for k in KINDS:
        if k in by:
            line = f"- {KINDS[k]}: " + "; ".join(by[k][:25])
            n += len(line)
            if n > max_chars:
                break
            out.append(line)
    extra = vault_additions()
    if extra:
        out.append("- Anh tự ghi trong Obsidian: " + "; ".join(extra)[:1500])
    return "\n".join(out)


# ------------------------------------------------------------------ tự học từ hội thoại
EXTRACT = """Bạn trích xuất TRÍ NHỚ DÀI HẠN về người dùng (anh Huy) từ lượt hội thoại dưới đây.
Chỉ lấy điều bền vững, hữu ích cho việc hỗ trợ sau này: thông tin cá nhân, sức khoẻ, mục tiêu, sở thích, cách làm việc,
nếp sinh hoạt, người quan trọng, bối cảnh công ty. KHÔNG lấy việc vặt một lần, số liệu tạm thời, nội dung email/tin nhắn của người khác,
mật khẩu, số tài khoản, mã bí mật.
Các điều ĐÃ BIẾT (đừng lặp lại, nhưng nếu có thông tin MỚI thay thế thì ghi bản mới):
{known}
Trả về DUY NHẤT mảng JSON (có thể rỗng []): [{{"text": "câu ngắn ở ngôi thứ ba, ví dụ 'Anh Huy 37 tuổi, cao 1m75'", "kind": "{kinds}"}}]
HỘI THOẠI:
Anh: {user}
superHuy: {assistant}"""

SECRET = re.compile(r"(mật khẩu|password|pin|otp|token|secret|số thẻ|stk|\b\d{9,}\b)", re.I)


def learn_from(user: str, assistant: str):
    """Chạy nền sau mỗi lượt chat. Lỗi thì bỏ qua."""
    if len((user or "").strip()) < 12:
        return

    def work():
        try:
            from config import LLM_MODEL
            from llm import LLM_EXTRA, PRECISE, fix_vi, make_client
            known = "\n".join("- " + it["text"] for it in _load()[-80:]) or "(chưa có)"
            prompt = EXTRACT.format(known=known, kinds="|".join(KINDS), user=user[:2000], assistant=(assistant or "")[:1500])
            r = make_client().chat.completions.create(model=LLM_MODEL, extra_body=LLM_EXTRA, max_tokens=800, **PRECISE,
                                                      messages=[{"role": "user", "content": prompt}])
            m = re.search(r"\[.*\]", fix_vi(r.choices[0].message.content), re.S)
            for f in json.loads(m.group(0)) if m else []:
                t = str(f.get("text", "")).strip()
                if t and not SECRET.search(t) and len(t) < 300:
                    add(t, f.get("kind", "profile"), "tự học")
        except Exception:
            log.debug("Không trích được trí nhớ", exc_info=True)

    threading.Thread(target=work, daemon=True).start()


def seed_once(lines: list[tuple[str, str]]):
    """Thêm các điều nền tảng (chỉ thêm nếu chưa có)."""
    for kind, text in lines:
        add(text, kind, "thiết lập")
