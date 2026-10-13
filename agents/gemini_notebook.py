"""Nguồn tri thức: Gemini Notebook (trước là NotebookLM) của anh Huy.

Google chưa có API chính thức cho tài khoản cá nhân, nên superHuy dùng thư viện mã nguồn mở notebooklm-py
(phiên đăng nhập Google của anh, lưu trên máy chủ ở shared/notebooklm/storage_state.json, quyền 600).
- Đăng nhập: anh chạy deploy/Ket-noi-Gemini-Notebook.command trên Mac (tự đăng nhập Google trong cửa sổ trình duyệt),
  script gửi phiên lên superHuy bằng MÃ KẾT NỐI dùng 1 lần (hiện trong app, hết hạn 20 phút). Không ai khác thấy phiên.
- Đồng bộ (6 giờ/lần + khi anh bấm): mỗi notebook -> tóm tắt, ghi chú (notes), nội dung đầy đủ các nguồn
  -> data/knowledge/gemini/... (superHuy tra cứu khi trả lời) + 1 ghi chú mục lục mỗi notebook trong Obsidian.
- Hỏi trực tiếp 1 notebook (Gemini trả lời dựa trên nguồn của notebook đó, có trích dẫn).
"""
import asyncio
import datetime as dt
import json
import logging
import os
import re
import secrets
import shutil
import threading
import time

from config import DATA_DIR, HOME_DIR, OBSIDIAN_VAULT

log = logging.getLogger("gemini-notebook")
AUTH_DIR = HOME_DIR / "notebooklm"
AUTH = AUTH_DIR / "storage_state.json"
CACHE = DATA_DIR / "knowledge" / "gemini"
STATE = DATA_DIR / "knowledge" / "gemini_state.json"
OBS_FOLDER = "03 Resources/Gemini Notebook"
MAX_NOTEBOOKS = 80
MAX_SOURCES = 60          # mỗi notebook
MAX_CHARS = 80_000        # mỗi nguồn (đủ cho tra cứu, tránh phình ổ đĩa)
_lock = threading.Lock()
_codes: dict[str, float] = {}
_running = {"sync": False}


# ------------------------------------------------------------------ trạng thái
def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(st: dict):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STATE)


def available() -> bool:
    try:
        import notebooklm  # noqa: F401
        return True
    except Exception:
        return False


def connected() -> bool:
    return AUTH.exists()


def status() -> dict:
    st = _state()
    return {"id": "gemini", "name": "Gemini Notebook", "connected": connected(), "library": available(),
            "syncing": _running["sync"], "last_sync": st.get("last_sync", ""), "last_error": st.get("last_error", ""),
            "notebooks": len(st.get("notebooks", {})), "sources": sum(len(n.get("sources", {})) for n in st.get("notebooks", {}).values()),
            "notes": sum(n.get("notes", 0) for n in st.get("notebooks", {}).values()),
            "items": [{"id": k, "title": v.get("title", ""), "sources": len(v.get("sources", {})), "notes": v.get("notes", 0),
                       "emoji": v.get("emoji") or ""} for k, v in sorted(st.get("notebooks", {}).items(), key=lambda kv: kv[1].get("title", ""))]}


# ------------------------------------------------------------------ kết nối bằng mã dùng 1 lần
def new_code() -> dict:
    """Mã 8 ký tự, 20 phút, dùng 1 lần: script trên Mac gửi phiên đăng nhập kèm mã này."""
    now = time.time()
    for k in [k for k, exp in _codes.items() if exp < now]:
        _codes.pop(k, None)
    code = "".join(secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
    _codes[code] = now + 20 * 60
    return {"code": code, "expires_min": 20}


def accept(code: str, payload: bytes) -> str:
    """Nhận storage_state.json từ script trên Mac. Trả về thông báo; lỗi thì ném ValueError."""
    code = (code or "").strip().upper()
    exp = _codes.pop(code, 0)
    if not exp or exp < time.time():
        raise ValueError("Mã kết nối sai hoặc đã hết hạn. Mở app › Second Brain › Gemini Notebook để lấy mã mới.")
    if len(payload) > 2_000_000:
        raise ValueError("Tệp phiên đăng nhập quá lớn")
    data = json.loads(payload.decode("utf-8"))
    names = {c.get("name") for c in data.get("cookies", []) if isinstance(c, dict)}
    if not {"SID", "__Secure-1PSIDTS"} <= names:
        raise ValueError("Phiên đăng nhập Google chưa đủ (thiếu cookie). Chạy lại script và đăng nhập xong mới đóng cửa sổ.")
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(AUTH_DIR, 0o700)
    tmp = AUTH.with_suffix(".tmp")
    tmp.write_bytes(payload)
    os.chmod(tmp, 0o600)
    tmp.replace(AUTH)
    st = _state()
    st.pop("last_error", None)
    st["connected_at"] = dt.datetime.now().isoformat(timespec="seconds")
    _save_state(st)
    sync_async(notify=True)
    return "Đã kết nối Gemini Notebook. superHuy đang nạp các notebook, xong sẽ báo qua Telegram."


def disconnect(keep_data: bool = True) -> dict:
    AUTH.unlink(missing_ok=True)
    shutil.rmtree(AUTH_DIR / "profiles", ignore_errors=True)
    if not keep_data:
        shutil.rmtree(CACHE, ignore_errors=True)
        STATE.unlink(missing_ok=True)
    return {"text": "Đã ngắt Gemini Notebook" + ("" if keep_data else " và xoá dữ liệu đã nạp") + "."}


# ------------------------------------------------------------------ gọi thư viện
def _run(coro_fn, timeout: float = 900):
    """Chạy 1 thao tác async của notebooklm-py trong vòng lặp riêng (client không dùng chung giữa luồng)."""
    if not connected():
        raise RuntimeError("Chưa kết nối Gemini Notebook. Vào app › Second Brain › Gemini Notebook › Kết nối.")
    if not available():
        raise RuntimeError("Máy chủ chưa cài thư viện notebooklm-py.")
    from notebooklm import NotebookLMClient

    async def main():
        async with NotebookLMClient.from_storage(str(AUTH)) as client:
            return await asyncio.wait_for(coro_fn(client), timeout)

    if not _lock.acquire(timeout=90):  # 1 phiên Google: không chạy 2 thao tác cùng lúc
        raise RuntimeError("Gemini Notebook đang đồng bộ, anh thử lại sau ít phút.")
    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(1) as ex:  # vòng lặp asyncio riêng, an toàn cả khi được gọi từ trong bot (đã có event loop)
            return ex.submit(asyncio.run, main()).result()
    except Exception as e:
        msg = str(e)
        if re.search(r"auth|login|cookie|401|403|expired|sign", msg, re.I):
            raise RuntimeError("Phiên đăng nhập Google cho Gemini Notebook đã hết hạn. Chạy lại script Kết nối Gemini Notebook trên Mac.") from e
        raise
    finally:
        _lock.release()


def _slug(s: str) -> str:
    s = re.sub(r'[\\/:*?"<>|#^\[\]]', " ", s or "")
    return re.sub(r"\s+", " ", s).strip()[:70] or "Khong ten"


def _fm(**kw) -> str:
    lines = ["---"]
    for k, v in kw.items():
        v = str(v or "").replace("\n", " ").replace('"', "'")
        lines.append(f'{k}: "{v}"')
    return "\n".join(lines + ["---", ""])


def _iso(x) -> str:
    try:
        return x.isoformat()
    except Exception:
        return ""


def sync(force: bool = False) -> dict:
    """Nạp toàn bộ notebook. Chỉ tải lại nội dung nguồn mới/đổi (so revision/thời điểm cập nhật)."""
    if _running["sync"]:
        return {"text": "Gemini Notebook đang đồng bộ, đợi chút nhé."}
    _running["sync"] = True
    st = _state()
    old = st.get("notebooks", {})
    stats = {"notebooks": 0, "new_sources": 0, "notes": 0}

    async def work(client):
        nbs = (await client.notebooks.list())[:MAX_NOTEBOOKS]
        result = {}
        for nb in nbs:
            prev = old.get(nb.id, {})
            folder = CACHE / f"{_slug(nb.title)} [{nb.id[:8]}]"
            folder.mkdir(parents=True, exist_ok=True)
            entry = {"title": nb.title, "emoji": getattr(nb, "emoji", "") or "", "sources": {}, "folder": folder.name}
            try:
                summary = await client.notebooks.get_summary(nb.id)
            except Exception:
                summary = prev.get("summary", "")
            entry["summary"] = (summary or "")[:4000]
            # ghi chú (notes) của anh trong notebook
            try:
                notes = await client.notes.list(nb.id)
            except Exception:
                notes = []
            entry["notes"] = len(notes)
            stats["notes"] += len(notes)
            body = [f"# {nb.title}", "", "## Tóm tắt notebook", entry["summary"] or "(chưa có)", ""]
            for n in notes:
                body += [f"## Ghi chú: {n.title or 'Không tên'}", (n.content or "").strip()[:20000], ""]
            (folder / "_notebook.md").write_text(_fm(title=nb.title, kb_source="Gemini Notebook", kb_label=nb.title, notebook_id=nb.id)
                                                 + "\n".join(body), encoding="utf-8")
            # nguồn
            try:
                sources = (await client.sources.list(nb.id))[:MAX_SOURCES]
            except Exception:
                sources = []
            keep = {"_notebook.md"}
            for s in sources:
                ver = getattr(s, "revision_id", None) or _iso(getattr(s, "last_modified_at", None)) or _iso(getattr(s, "created_at", None))
                fname = f"{_slug(s.title or s.id)} [{s.id[:6]}].md"
                keep.add(fname)
                p = prev.get("sources", {}).get(s.id, {})
                entry["sources"][s.id] = {"title": s.title or "", "url": s.url or "", "ver": ver, "file": fname,
                                          "kind": str(getattr(s.kind, "value", s.kind) if hasattr(s, "kind") else "")}
                if not force and p.get("ver") == ver and (folder / fname).exists():
                    continue
                if hasattr(s, "is_ready") and not s.is_ready:
                    continue
                try:
                    ft = await client.sources.get_fulltext(nb.id, s.id)
                    text = (getattr(ft, "rendered_content", "") or ft.content or "")[:MAX_CHARS]
                except Exception as e:
                    log.warning("Không lấy được nội dung nguồn %s: %s", s.id, e)
                    continue
                (folder / fname).write_text(_fm(title=s.title or "", kb_source="Gemini Notebook", kb_label=f"{nb.title} › {s.title or 'nguồn'}",
                                                notebook=nb.title, url=s.url or "") + f"# {s.title or ''}\n\n{text}\n", encoding="utf-8")
                stats["new_sources"] += 1
            for f in folder.glob("*.md"):  # nguồn đã xoá trên Gemini Notebook
                if f.name not in keep:
                    f.unlink(missing_ok=True)
            result[nb.id] = entry
            stats["notebooks"] += 1
        return result

    try:
        notebooks = _run(work, timeout=1800)
        # notebook đã xoá
        live = {v["folder"] for v in notebooks.values()}
        if CACHE.exists():
            for d in CACHE.iterdir():
                if d.is_dir() and d.name not in live:
                    shutil.rmtree(d, ignore_errors=True)
        st.update(notebooks=notebooks, last_sync=dt.datetime.now().strftime("%H:%M %d/%m/%Y"))
        st.pop("last_error", None)
        _save_state(st)
        try:
            _to_obsidian(notebooks)
        except Exception:
            log.exception("Không ghi được mục lục Gemini Notebook vào Obsidian")
        return {**stats, "text": f"Đã nạp {stats['notebooks']} notebook từ Gemini Notebook ({stats['new_sources']} nguồn mới/cập nhật, {stats['notes']} ghi chú)."}
    except Exception as e:
        st["last_error"] = str(e)[:300]
        _save_state(st)
        raise
    finally:
        _running["sync"] = False


def sync_async(notify: bool = False):
    def work():
        try:
            r = sync()
            if notify:
                from core import notify as nt
                nt.send(text="📚 " + r["text"] + " Từ giờ superHuy tham chiếu các notebook này khi trả lời anh.")
        except Exception as e:
            log.exception("Đồng bộ Gemini Notebook lỗi")
            if notify:
                from core import notify as nt
                nt.send(text=f"⚠️ Chưa nạp được Gemini Notebook: {e}")
    threading.Thread(target=work, daemon=True, name="gemini-sync").start()


def _to_obsidian(notebooks: dict):
    """Mỗi notebook 1 ghi chú mục lục nhẹ trong Obsidian (tóm tắt + danh sách nguồn); nội dung đầy đủ nằm ở superHuy."""
    base = OBSIDIAN_VAULT / OBS_FOLDER
    base.mkdir(parents=True, exist_ok=True)
    keep = set()
    for nid, nb in notebooks.items():
        name = f"{_slug(nb['title'])}.md"
        keep.add(name)
        src = "\n".join(f"- {v['title'] or 'Nguồn'}" + (f" ({v['url']})" if v.get("url") else "") for v in nb["sources"].values())
        txt = (f"---\ntitle: \"{nb['title'].replace(chr(34), chr(39))}\"\ntype: gemini-notebook\ngenerated_by: superhuy\nnotebook_id: {nid}\n"
               f"tags: [gemini-notebook]\n---\n# {nb.get('emoji', '')} {nb['title']}\n\n"
               f"[Mở trên Gemini Notebook](https://notebooklm.google.com/notebook/{nid})\n\n## Tóm tắt\n{nb.get('summary') or '(chưa có)'}\n\n"
               f"## Nguồn ({len(nb['sources'])})\n{src or '(chưa có)'}\n\n"
               f"> [!info] superHuy tự cập nhật ghi chú này từ Gemini Notebook. Nội dung đầy đủ của các nguồn được superHuy tra cứu khi trả lời anh.\n")
        p = base / name
        if not p.exists() or p.read_text(encoding="utf-8") != txt:
            p.write_text(txt, encoding="utf-8")
    for f in base.glob("*.md"):
        if f.name not in keep:
            f.unlink(missing_ok=True)


# ------------------------------------------------------------------ hỏi 1 notebook
def _match(notebook: str) -> tuple[str, str]:
    nbs = _state().get("notebooks", {})
    if not nbs:
        raise ValueError("Chưa có notebook nào được nạp. Đồng bộ Gemini Notebook trước.")
    if notebook in nbs:
        return notebook, nbs[notebook]["title"]
    from core.kb import fold
    q = fold(notebook)
    best = max(nbs.items(), key=lambda kv: (q in fold(kv[1]["title"])) * 10 + len(set(q.split()) & set(fold(kv[1]["title"]).split())))
    if q and q not in fold(best[1]["title"]) and not set(q.split()) & set(fold(best[1]["title"]).split()):
        raise ValueError(f"Không thấy notebook nào tên giống “{notebook}”. Các notebook: " + ", ".join(v["title"] for v in nbs.values())[:600])
    return best[0], best[1]["title"]


def ask(question: str, notebook: str) -> dict:
    nid, title = _match(notebook)
    srcs = _state()["notebooks"][nid].get("sources", {})

    async def work(client):
        return await client.chat.ask(nid, question)

    r = _run(work, timeout=180)
    refs = []
    for ref in getattr(r, "references", []) or []:
        t = srcs.get(getattr(ref, "source_id", ""), {}).get("title")
        if t and t not in refs:
            refs.append(t)
    ans = (r.answer or "").strip()
    return {"answer": ans, "notebook": title, "sources": refs,
            "text": f"📚 Gemini Notebook «{title}»:\n{ans}" + (f"\n\nNguồn: {'; '.join(refs[:8])}" if refs else "")}


def list_text() -> dict:
    st = status()
    if not st["connected"]:
        return {**st, "text": "Chưa kết nối Gemini Notebook."}
    rows = "\n".join(f"• {i['emoji']} {i['title']} ({i['sources']} nguồn, {i['notes']} ghi chú)" for i in st["items"])
    return {**st, "text": f"Gemini Notebook: {st['notebooks']} notebook, đồng bộ lúc {st['last_sync'] or 'chưa'}\n{rows}"}
