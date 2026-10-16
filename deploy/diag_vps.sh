#!/usr/bin/env bash
# Chẩn đoán an toàn (KHÔNG in giá trị bí mật, KHÔNG in tên/nội dung ghi chú) — kết quả có thể công khai.
S=/opt/superhuy/shared
echo "time: $(date -Is)"
echo "service: $(systemctl is-active superhuy 2>/dev/null)"
echo "current: $(basename "$(readlink -f /opt/superhuy/current)")"
echo "health: $(curl -fsS -m 5 http://127.0.0.1:8787/health 2>/dev/null || echo FAIL)"
echo "landing_public: $(curl -s -o /dev/null -w "%{http_code} %{size_download}" -m 10 https://app.roimaxxhub.com/landing)"
echo "env_keys: $(grep -oE '^[A-Z_]+=' $S/.env 2>/dev/null | tr -d '=' | tr '\n' ' ')"
echo "vault_remote_set: $(grep -q '^VAULT_GIT_REMOTE=.\+' $S/.env && echo yes || echo no)"
echo "obsidian_vault_env: $(grep '^OBSIDIAN_VAULT=' $S/.env | cut -d= -f2)"
V=$(grep '^OBSIDIAN_VAULT=' $S/.env | cut -d= -f2); V=${V:-$S/vault}
echo "vault_exists: $([ -d "$V" ] && echo yes || echo no)"
echo "vault_md_count: $(find "$V" -name '*.md' 2>/dev/null | wc -l)"
echo "vault_md_today: $(find "$V" -name '*.md' -newermt "$(date +%F)" 2>/dev/null | wc -l)"
echo "vault_top_dirs: $(ls -1 "$V" 2>/dev/null | head -12 | tr '\n' '|')"
echo "vault_git: $([ -d "$V/.git" ] && echo yes || echo no)"
[ -d "$V/.git" ] && echo "vault_git_remote: $(git -C "$V" remote get-url origin 2>/dev/null)" && echo "vault_git_commits: $(git -C "$V" rev-list --count HEAD 2>/dev/null)"
if [ ! -f $S/vault_deploy_key ]; then ssh-keygen -q -t ed25519 -N "" -C "superhuy-vault" -f $S/vault_deploy_key && echo "vault_key: created"; fi
echo "vault_pubkey: $(cat $S/vault_deploy_key.pub 2>/dev/null)"
echo "sync_log: $(grep -h 'vault' $S/data/agent.log 2>/dev/null | tail -3 | cut -c1-160 | tr '\n' '|')"
echo "qc_vault: $(python3 -c "import json;d=json.load(open('$S/data/qc.json'));print(d.get('vault'))" 2>/dev/null)"
# Ép đồng bộ Obsidian một lần (chỉ in tóm tắt/lỗi đã cắt ngắn, không có bí mật)
if grep -q '^VAULT_GIT_REMOTE=.\+' $S/.env; then
  echo "force_sync: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 150 /opt/superhuy/venv/bin/python -c 'from core import vault_sync as v; print(v.sync())' 2>&1 | tail -2 | cut -c1-240 | tr '\n' '|')"
  echo "vault_git_commits_after: $(git -C "$V" rev-list --count HEAD 2>/dev/null)"
  echo "vault_last_commit: $(git -C "$V" log -1 --format='%cI by %an' 2>/dev/null)"
  echo "vault_ahead_behind: $(git -C "$V" rev-list --left-right --count HEAD...origin/main 2>/dev/null)"
fi
echo "vault_mac_commits: $(git -C "$V" log --format=%an 2>/dev/null | grep -c 'Obsidian Mac')"
echo "vault_test_note: $([ -f "$V/00 Inbox/Kiem tra ket noi superHuy.md" ] && echo yes || echo no)"
echo "share_route_unknown: $(curl -s -o /dev/null -w '%{http_code}' -m 5 http://127.0.0.1:8787/s/khongtontai123)"
echo "kb_stats: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from core import kb; print(kb.stats())' 2>&1 | tail -1 | cut -c1-200)"
echo "memory_note: $([ -f "$V/02 Areas/superHuy/superHuy hieu ve anh.md" ] && echo yes || echo no)"
echo "gemini: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from agents import gemini_notebook as g; s=g.status(); print({k: s[k] for k in ("library","connected","syncing","last_sync","last_error","notebooks","sources","notes")})' 2>&1 | tail -1 | cut -c1-300)"
echo "strategy: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from agents import strategy as s; o=s.overview(); print({"insights": o["counts"], "docs": [(d["lens"], d["version"], len(s.doc(d["lens"]).get("md") or "")) for d in o["docs"]]})' 2>&1 | tail -1 | cut -c1-300)"
echo "fonts: $(ls $S/assets/fonts 2>/dev/null | tr '\n' ' ')"
echo "content_log: $(grep -h -E 'newscast|Dựng bản tin|strategy|CAO|Phân tích' $S/data/agent.log 2>/dev/null | tail -4 | cut -c1-160 | tr '\n' '|')"
echo "repos: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from agents import repo_radar as r; o=r.overview(); print({"week": o["week"], "new": [(i["full_name"], i["a"]["phu_hop"], i["a"]["ket_luan"], len(i["a"]["de_xuat"])) for i in o["new"][:8]], "applied": len(o["applied"]), "open_tickets": o["open_tickets"], "rules": len(o["rules"]), "watch": len(o["watch"]), "scanning": o["scanning"]})' 2>&1 | tail -1 | cut -c1-700)"
echo "--- upgrade tickets (open) ---"
(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from agents import repo_radar as r; print(r.open_tickets_markdown()[:6000])' 2>&1 | tail -150)
echo "--- end tickets ---"
echo "learning2: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from agents import learning as l; import os; print([(c["title"][:22], c["id"], [(d["day"], bool(d.get("lesson")), bool((d.get("lesson") or {}).get("audio")) and os.path.exists((d.get("lesson") or {}).get("audio","")), d.get("status")) for d in c["days"][:3]]) for c in l._load()])' 2>&1 | tail -1 | cut -c1-900)"
echo "web_test: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 90 /opt/superhuy/venv/bin/python -c 'from agents import web_tools as w; import time; t=time.time(); r=w.search("Shopify agentic commerce", 5); print(len(r["results"]), r["text"].split(chr(10))[0][:80], round(time.time()-t,1), "s"); u=r["results"][0]["url"] if r["results"] else "https://en.wikipedia.org/wiki/E-commerce"; t=time.time(); d=w.read(u, 3000); print("read", len(d["text"]), round(time.time()-t,1), "s")' 2>&1 | tail -2 | tr '\n' '|' | cut -c1-400)"
(cd /opt/superhuy/current && SUPERHUY_HOME=$S nohup /opt/superhuy/venv/bin/python deploy/maint_leversphere.py > $S/data/strategy/maint_lv.log 2>&1 &)
echo "maint_lv_log: $(tail -2 $S/data/strategy/maint_lv.log 2>/dev/null | cut -c1-300 | tr '\n' '|')"
echo "maint: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 120 /opt/superhuy/venv/bin/python deploy/maint_tickets.py 2>&1 | tail -1 | cut -c1-1500)"
echo "tickets_list: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from agents import repo_radar as r; print([(t["id"], t["status"], t["effort"], t["title"][:70], t["repo"]) for t in r._read(r.TICKETS, [])])' 2>&1 | tail -1 | cut -c1-2500)"
echo "learning: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from agents import learning as l; import json; o=l.overview(); c=l._load(); print([(x["title"][:30], x["total"], x["today"]) for x in o["courses"]], [(d["day"], bool(d.get("lesson")), bool((d.get("lesson") or {}).get("audio")), len((d.get("lesson") or {}).get("md") or "")) for d in (c[0]["days"][:2] if c else [])])' 2>&1 | tail -1 | cut -c1-300)"
echo "videos: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from core import store; import os; print([(r["id"], (r.get("meta") or {}).get("engine"), (r.get("meta") or {}).get("voice_engine"), len((r.get("meta") or {}).get("versions") or []), os.path.basename(r.get("video") or ""), r.get("created","")[5:16]) for r in store.recent(6, "video")])' 2>&1 | tail -1 | cut -c1-600)"
echo "video_log: $(grep -h -E 'edge-tts|Dựng|newscast|dung_lai|rerender|reel' $S/data/agent.log 2>/dev/null | tail -8 | cut -c1-220 | tr '\n' '|')"
echo "jobs_log: $(grep -h -E 'Job noidung|Traceback|Error' $S/data/agent.log 2>/dev/null | tail -6 | cut -c1-220 | tr '\n' '|')"
echo "tts_test: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 90 /opt/superhuy/venv/bin/python -c '
import edge_tts, asyncio, importlib.metadata as m
print("edge-tts", m.version("edge-tts"))
async def go():
    await edge_tts.Communicate("Xin chào, đây là bản tin thử.", "vi-VN-NamMinhNeural").save("/tmp/tts_test.mp3")
try:
    asyncio.run(go()); import os; print("ok", os.path.getsize("/tmp/tts_test.mp3"))
except Exception as e:
    print("ERR", type(e).__name__, str(e)[:200])
' 2>&1 | tail -2 | tr '\n' ' ' | cut -c1-400)"
echo "render_meta: $(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 60 /opt/superhuy/venv/bin/python -c 'from core import store; print([(r["id"], (r.get("meta") or {}).get("render"), [(v.get("id"), v.get("voice_engine") or v.get("engine"), v.get("note","")[:30]) for v in ((r.get("meta") or {}).get("versions") or [])][-3:]) for r in store.recent(3, "video")])' 2>&1 | tail -1 | cut -c1-1500)"
echo "disk: $(df -h /opt /tmp 2>/dev/null | tail -2 | tr -s ' ' | tr '\n' '|')  mem: $(free -m | awk 'NR==2{print $2"MB tổng, "$7"MB trống"}')  swap: $(free -m | awk 'NR==3{print $2"MB"}')"
echo "videos_dir: $(du -sh $S/data/videos 2>/dev/null | cut -f1) / $(ls $S/data/videos 2>/dev/null | wc -l) files"
echo "oom: $(journalctl -k --since -12h 2>/dev/null | grep -i -E 'oom|killed process' | tail -3 | cut -c1-200 | tr '\n' '|')"
echo "--- lark ---"
(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 120 /opt/superhuy/venv/bin/python deploy/lark_diag.py 2>&1 | grep -v -i -E "token=|secret|Bearer" | tail -30 | cut -c1-500)
echo "journal_lark: $(journalctl -u superhuy --since -24h 2>/dev/null | grep -i -E 'lark'  | grep -v -i -E 'token=|secret|Bearer' | tail -12 | cut -c1-260 | tr '\n' '|')"
echo "--- end lark ---"
echo "--- render test ---"
(cd /opt/superhuy/current && SUPERHUY_HOME=$S RT_FROM=7 timeout 300 /opt/superhuy/venv/bin/python deploy/render_test.py 2>&1 | tail -40 | cut -c1-400)
echo "--- end render test ---"
echo "--- journal render errors ---"
journalctl -u superhuy --since -6h 2>/dev/null | grep -i -E -A12 'reel_studio|newscast|Traceback|Error' | grep -v -i -E 'token|key=|secret' | tail -80 | cut -c1-260
echo "--- end journal ---"
echo "journal_tts: $(journalctl -u superhuy --since -3h 2>/dev/null | grep -i -E 'edge-tts|tts|silent' | tail -4 | cut -c1-220 | tr '\n' '|')"
echo "--- QA ---"
(cd /opt/superhuy/current && SUPERHUY_HOME=$S timeout 400 /opt/superhuy/venv/bin/python deploy/qa_vps.py 2>/dev/null | grep '^qa_')
