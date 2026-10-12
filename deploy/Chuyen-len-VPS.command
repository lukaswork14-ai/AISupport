#!/bin/bash
# Bấm đúp trên Mac để chuyển superHuy lên VPS. Anh tự gõ mật khẩu VPS vào cửa sổ Terminal này (không ai khác thấy).
# Việc làm: đóng gói khoá + dữ liệu + kho Obsidian trên Mac -> chép lên VPS qua SSH -> cài đặt VPS -> nhập dữ liệu.
set -e
cd "$(dirname "$0")/.."
echo "=== Chuyển superHuy lên VPS ==="
read -r -p "IP của VPS: " IP
read -r -p "User SSH của VPS [root]: " U; U=${U:-root}
read -r -p "Cổng SSH [22]: " P; P=${P:-22}
read -r -p "Tên miền cho app (vd app.sellnity.com): " DOMAIN
read -r -p "Repo Obsidian (vd git@github.com:lukaswork14-ai/superhuy-vault.git, Enter nếu chưa có): " VAULT
[ -n "$IP" ] && [ -n "$DOMAIN" ] || { echo "Thiếu IP hoặc tên miền"; exit 1; }

PKG=/tmp/superhuy-migrate.tar.gz
STAGE=$(mktemp -d)
for f in .env credentials.json targets.json style_guide.md; do [ -f "$f" ] && cp "$f" "$STAGE/"; done
rsync -a --exclude videos --exclude video_tmp --exclude '_git_export.tar' --exclude '*.flag' --exclude 'DISABLED' data "$STAGE/"
VAULT_DIR="${OBSIDIAN_VAULT:-$HOME/SecondBrain}"
[ -d "$VAULT_DIR" ] && rsync -a --exclude '.obsidian/workspace*' --exclude '.trash' "$VAULT_DIR/" "$STAGE/vault/"
tar -czf "$PKG" -C "$STAGE" .
rm -rf "$STAGE"
echo "Đã đóng gói $(du -h "$PKG" | cut -f1). Chép lên VPS (nhập mật khẩu VPS nếu được hỏi)…"
scp -P "$P" deploy/setup_vps.sh deploy/import_data.sh "$PKG" "$U@$IP:/tmp/"
rm -f "$PKG"
echo "Cài đặt VPS (mất vài phút)…"
ssh -t -p "$P" "$U@$IP" "sudo bash /tmp/setup_vps.sh '$DOMAIN' '$VAULT' && sudo bash /tmp/import_data.sh /tmp/superhuy-migrate.tar.gz && sudo rm -f /tmp/superhuy-migrate.tar.gz"
echo
echo "XONG. Làm tiếp theo hướng dẫn in ở trên (DNS, GitHub Secrets, deploy key Obsidian), rồi báo Claude."
read -r -p "Nhấn Enter để đóng cửa sổ…"
