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
