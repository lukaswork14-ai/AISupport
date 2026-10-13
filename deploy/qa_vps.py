"""Kiểm thử nhanh trên VPS (chạy bởi workflow Chẩn đoán): dựng 1 máy chủ Mini App phụ ở cổng 8799 trong cùng môi trường,
gọi các API chính như app thật. CHỈ in OK/FAIL + số đếm, không in nội dung ghi chú, mã, token hay dữ liệu cá nhân."""
import json
import sys
import time
import traceback
import urllib.request

sys.path.insert(0, ".")
PORT = 8799
res = []


def rec(name, ok, detail=""):
    res.append(f"qa_{name}: {'OK' if ok else 'FAIL'}{(' ' + str(detail)[:160]) if detail else ''}")


def http(path, body=None, tok="", method=None):
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method or ("POST" if body is not None else "GET"),
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", "X-Session": tok})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def run(tok, agent, action, params=None):
    code, b = http("/api/run", {"agent": agent, "action": action, "params": params or {}}, tok)
    d = json.loads(b or b"{}")
    if "job" in d:  # việc chạy nền
        for _ in range(120):
            time.sleep(2)
            _, jb = http(f"/api/job?id={d['job']}", tok=tok)
            j = json.loads(jb)
            if j.get("status") != "running":
                return j.get("result") or {"error": j.get("error")}
    return d.get("result") if "result" in d else {"error": d.get("error", f"HTTP {code}")}


def main():
    from config import OWNER_CHAT_ID
    from webapp import server
    import hub  # noqa: F401  đăng ký agent
    server.serve(PORT)
    time.sleep(1)
    tok = server.make_session(OWNER_CHAT_ID)

    c, b = http("/")
    rec("index", c == 200 and b"superHuy" in b, f"{len(b) // 1024}KB")
    c, b = http("/api/bootstrap", tok=tok)
    d = json.loads(b or b"{}")
    rec("bootstrap", c == 200 and bool(d.get("agents")), f"{len(d.get('agents', []))} agent")
    c, _ = http("/api/bootstrap", tok="sai")
    rec("auth_guard", c == 401)

    r = run(tok, "brain", "tongquan")
    ok = isinstance(r, dict) and "stats" in r and not r.get("error")
    rec("brain_tongquan", ok, f"{r.get('stats')} nguon={[(s['id'], s.get('connected')) for s in r.get('sources', [])]}" if ok else r)
    r = run(tok, "brain", "tim", {"query": "Sellnity"})
    rec("brain_tim", "items" in r, f"{len(r.get('items', []))} kết quả")
    if r.get("items"):
        d2 = run(tok, "brain", "doc", {"path": r["items"][0]["path"]})
        rec("brain_doc", bool(d2.get("body")), f"{len(d2.get('body', ''))} ký tự")
    r = run(tok, "brain", "nguon")
    rec("brain_nguon", len(r.get("items", [])) >= 2)
    r = run(tok, "brain", "gemini_ma")
    rec("gemini_code", len(r.get("code", "")) == 8)
    c, b = http("/connect/gemini?code=SAIMA123", body={"cookies": []})
    rec("gemini_connect_guard", c == 400)
    r = run(tok, "brain", "notebook_ds")
    rec("gemini_list", "text" in r, r.get("text", r.get("error", ""))[:80].split("\n")[0])

    from core import kb, memory
    blk, used = kb.context("Sellnity chiến lược định giá AI Agent")
    rec("kb_context", True, f"{len(used)} nguồn khớp")
    rec("memory_note", memory._note_path().exists(), f"{len(memory.vault_additions())} dòng anh bổ sung")

    r = run(tok, "hop", "danhsach")
    items = r.get("items") or []
    done = [m for m in items if m.get("status") == "done"]
    rec("hop_danhsach", isinstance(items, list), f"{len(items)} cuộc họp, {len(done)} xong")
    if done:
        mid = done[0]["id"]
        m = run(tok, "hop", "xem", {"id": mid})
        rec("hop_xem", bool(m.get("recap")), f"{len(m.get('segments') or [])} đoạn lời thoại")
        s = run(tok, "hop", "chia_se", {"mid": mid, "days": 1, "note": "QA tự động"})
        token = s.get("token", "")
        rec("share_create", bool(token) and bool(s.get("message")), f"tin nhắn {len(s.get('message', ''))} ký tự")
        if token:
            c, b = http(f"/s/{token}")
            rec("share_page", c == 200 and ("Tóm tắt".encode() in b or b"<svg" in b), f"HTTP {c}, {len(b) // 1024}KB")
            c, _ = http(f"/s/{token}/audio")
            rec("share_audio_guard", c == 404)
            ds = run(tok, "hop", "chia_se_ds", {"mid": mid})
            rec("share_list", any(x["token"] == token for x in ds.get("items", [])))
            run(tok, "hop", "thu_hoi", {"token": token})
            c, _ = http(f"/s/{token}")
            rec("share_revoke", c == 404)
    c, _ = http("/s/khongcoma12345")
    rec("share_unknown", c == 404)

    # chat thật (1 lượt) để chắc Second Brain được đưa vào ngữ cảnh. Không học trí nhớ từ câu kiểm thử.
    try:
        import brain
        acts = []
        txt = brain._loop([{"role": "user", "content": "Trong second brain của anh có ghi chú nào về Sellnity không? Trả lời 1 câu."}], acts)
        rec("chat_kb", bool(txt), f"trả lời {len(txt)} ký tự, tham chiếu={any(a['tool'] == 'brain__thamchieu' for a in acts)}, tool={[a['tool'] for a in acts][:4]}")
    except Exception as e:
        rec("chat_kb", False, e)


try:
    main()
except Exception:
    rec("crash", False, traceback.format_exc().splitlines()[-1])
print("\n".join(res))
