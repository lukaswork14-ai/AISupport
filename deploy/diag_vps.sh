#!/usr/bin/env bash
# Chẩn đoán an toàn (KHÔNG in giá trị bí mật, KHÔNG in tên/nội dung ghi chú) — kết quả có thể công khai.
S=/opt/superhuy/shared
echo "time: $(date -Is)"
echo "service: $(systemctl is-active superhuy 2>/dev/null)"
echo "current: $(basename "$(readlink -f /opt/superhuy/current)")"
echo "health: $(curl -fsS -m 5 http://127.0.0.1:8787/health 2>/dev/null || echo FAIL)"
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
