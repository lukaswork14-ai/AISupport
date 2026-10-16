#!/bin/bash
# Bấm đúp trên Mac để chuyển superHuy lên VPS. Anh tự gõ mật khẩu VPS vào cửa sổ Terminal này (không ai khác thấy).
# Việc làm: đóng gói khoá + dữ liệu + kho Obsidian trên Mac -> chép lên VPS qua SSH -> cài đặt VPS -> nhập dữ liệu.
set -e
cd "$(dirname "$0")/.."
echo "=== Chuyển superHuy lên VPS ==="
# Giá trị mặc định (Enter để dùng). Có thể đặt sẵn bằng biến môi trường VPS_IP, VPS_USER, VPS_PORT, APP_DOMAIN, VAULT_REMOTE.
D_IP="${VPS_IP:-}"; D_U="${VPS_USER:-root}"; D_P="${VPS_PORT:-22}"; D_DOMAIN="${APP_DOMAIN:-app.roimaxxhub.com}"
IP=$D_IP; U=$D_U; P=$D_P; DOMAIN=$D_DOMAIN; VAULT="${VAULT_REMOTE:-}"
[ -z "$D_IP" ] && read -r -p "IP của VPS: " D_IP && IP=$D_IP
if [ "${ASK:-0}" = 1 ]; then  # ASK=1 để nhập tay các giá trị khác mặc định
  read -r -p "IP của VPS [$D_IP]: " x; IP=${x:-$IP}
  read -r -p "User SSH [$D_U]: " x; U=${x:-$U}
  read -r -p "Cổng SSH [$D_P]: " x; P=${x:-$P}
  read -r -p "Tên miền [$D_DOMAIN]: " x; DOMAIN=${x:-$DOMAIN}
  read -r -p "Repo Obsidian (Enter nếu chưa có): " x; VAULT=${x:-$VAULT}
fi
echo "VPS: $U@$IP:$P  ·  Tên miền: https://$DOMAIN  ·  Repo Obsidian: ${VAULT:-(làm sau)}"
[ -n "$IP" ] && [ -n "$DOMAIN" ] || { echo "Thiếu IP hoặc tên miền"; exit 1; }

PKG=/tmp/superhuy-migrate.tar.gz
STAGE=$(mktemp -d)
for f in .env credentials.json targets.json style_guide.md; do [ -f "$f" ] && cp "$f" "$STAGE/"; done
rsync -a --exclude videos --exclude video_tmp --exclude '_git_export.tar' --exclude '*.flag' --exclude 'DISABLED' data "$STAGE/"
VAULT_DIR="${OBSIDIAN_VAULT:-$HOME/SecondBrain}"
[ -d "$VAULT_DIR" ] && rsync -a --exclude '.obsidian/workspace*' --exclude '.trash' "$VAULT_DIR/" "$STAGE/vault/"
tar -czf "$PKG" -C "$STAGE" .
rm -rf "$STAGE"
# Có khoá data/vps_admin_key (khoá công khai đã thêm vào VPS) thì đăng nhập bằng khoá, không cần mật khẩu.
KEYO=(); [ -f data/vps_admin_key ] && KEYO=(-i data/vps_admin_key)
SSHO=("${KEYO[@]}" -o ControlMaster=auto -o ControlPath=/tmp/superhuy-ssh-%r@%h:%p -o ControlPersist=600 -o StrictHostKeyChecking=accept-new)
echo "Đã đóng gói $(du -h "$PKG" | cut -f1). Kết nối VPS: gõ MẬT KHẨU VPS khi được hỏi (chỉ 1 lần, chữ không hiện khi gõ)…"
ssh "${SSHO[@]}" -p "$P" "$U@$IP" true
scp "${SSHO[@]}" -P "$P" deploy/setup_vps.sh deploy/import_data.sh "$PKG" "$U@$IP:/tmp/"
rm -f "$PKG"
echo "Cài đặt VPS (mất vài phút)…"
ssh "${SSHO[@]}" -t -p "$P" "$U@$IP" "sudo bash /tmp/setup_vps.sh '$DOMAIN' '$VAULT' && sudo bash /tmp/import_data.sh /tmp/superhuy-migrate.tar.gz && sudo rm -f /tmp/superhuy-migrate.tar.gz"
echo
# chép khoá triển khai vào clipboard để dán thẳng vào GitHub secret VPS_SSH_KEY (không lưu ra file)
if ssh "${SSHO[@]}" -p "$P" "$U@$IP" "sudo cat /home/superhuy/.ssh/gha_deploy" | pbcopy; then
  echo; echo ">>> KHOÁ VPS_SSH_KEY ĐÃ NẰM TRONG CLIPBOARD: vào GitHub › Settings › Secrets › Actions › New secret, đặt tên VPS_SSH_KEY rồi Cmd+V."
fi
open "https://github.com/lukaswork14-ai/AISupport/settings/secrets/actions/new" 2>/dev/null || true
ssh -O exit "${SSHO[@]}" -p "$P" "$U@$IP" 2>/dev/null || true
echo "XONG. Làm tiếp theo hướng dẫn in ở trên (DNS, GitHub Secrets, deploy key Obsidian), rồi báo Claude."
echo "(Có thể đóng cửa sổ này.)"; sleep 86400
