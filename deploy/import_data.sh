#!/usr/bin/env bash
# Nhập gói dữ liệu chuyển từ Mac (chạy 1 lần, quyền root): sudo bash import_data.sh superhuy-migrate.tar.gz
# Gói gồm: .env, credentials.json, targets.json, style_guide.md, data/, vault/ (kho Obsidian). Giữ các khoá VPS đã đặt.
set -euo pipefail
PKG="${1:?thiếu đường dẫn gói}"
ROOT=/opt/superhuy; S=$ROOT/shared; TMP=$(mktemp -d)
tar -xzf "$PKG" -C "$TMP"
# .env: lấy khoá từ Mac, giữ các dòng riêng của VPS
if [ -f "$TMP/.env" ]; then
  for k in WEBAPP_URL OBSIDIAN_VAULT OBSIDIAN_EMBED_AUDIO VAULT_SSH_KEY VAULT_GIT_REMOTE TIMEZONE; do
    v=$(grep "^$k=" $S/.env 2>/dev/null | head -1 || true); [ -n "$v" ] && { sed -i "/^$k=/d" "$TMP/.env"; echo "$v" >> "$TMP/.env"; }
  done
  install -m 600 -o superhuy -g superhuy "$TMP/.env" $S/.env
fi
for f in credentials.json targets.json style_guide.md; do [ -f "$TMP/$f" ] && install -m 600 -o superhuy -g superhuy "$TMP/$f" $S/$f; done
[ -d "$TMP/data" ] && rsync -a "$TMP/data/" $S/data/
rm -f $S/data/tunnel.json $S/data/heartbeat.json $S/data/DISABLED $S/data/restart.flag
[ -d "$TMP/vault" ] && rsync -a "$TMP/vault/" $S/vault/
chown -R superhuy:superhuy $S
rm -rf "$TMP"
echo "Đã nhập dữ liệu. Khởi động bot: sudo systemctl restart superhuy ; xem log: journalctl -u superhuy -f"
