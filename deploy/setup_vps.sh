#!/usr/bin/env bash
# Cài superHuy lên VPS Ubuntu 22.04/24.04 (chạy 1 lần, quyền root):
#   curl -fsSL https://raw.githubusercontent.com/<tài khoản>/<repo>/main/deploy/setup_vps.sh -o setup_vps.sh   (repo private: chép tay file này)
#   sudo bash setup_vps.sh app.tenmien.com
# Làm gì: cài gói hệ thống, tạo user 'superhuy', thư mục /opt/superhuy, dịch vụ systemd, Caddy (HTTPS tự động cho tên miền),
# tạo khoá SSH cho GitHub Actions triển khai và khoá cho repo Obsidian. KHÔNG khởi động bot (chờ chuyển dữ liệu từ Mac).
set -euo pipefail
DOMAIN="${1:-}"
VAULT_REMOTE="${2:-}"   # tuỳ chọn: git@github.com:<tài khoản>/<repo-vault>.git
[ -n "$DOMAIN" ] || { echo "Cách dùng: sudo bash setup_vps.sh app.tenmien.com [git@github.com:user/vault.git]"; exit 1; }
[ "$(id -u)" = 0 ] || { echo "Cần chạy bằng sudo/root"; exit 1; }
ROOT=/opt/superhuy
APPUSER=superhuy

echo "==> 1/7 Gói hệ thống"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git rsync curl ffmpeg fonts-dejavu-core fonts-noto-core \
  debian-keyring debian-archive-keyring apt-transport-https gnupg tzdata
timedatectl set-timezone Asia/Ho_Chi_Minh || true

echo "==> 2/7 Caddy (HTTPS tự động)"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y && apt-get install -y caddy
fi

echo "==> 3/7 User và thư mục"
id "$APPUSER" >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/$APPUSER --shell /bin/bash "$APPUSER"
mkdir -p $ROOT/releases $ROOT/shared/data $ROOT/shared/vault
python3 -m venv $ROOT/venv
chown -R $APPUSER:$APPUSER $ROOT
chmod 750 $ROOT/shared

echo "==> 4/7 Dịch vụ systemd"
cat > /etc/systemd/system/superhuy.service <<UNIT
[Unit]
Description=superHuy - sieu tro ly ca nhan (Telegram bot + Mini App)
After=network-online.target
Wants=network-online.target

[Service]
User=$APPUSER
WorkingDirectory=$ROOT/current
Environment=SUPERHUY_HOME=$ROOT/shared
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Asia/Ho_Chi_Minh
ExecStart=$ROOT/venv/bin/python main.py
Restart=always
RestartSec=5
# bot tự thoát khi có data/restart.flag -> systemd chạy lại
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable superhuy >/dev/null
# cho phép user superhuy tự khởi động lại dịch vụ khi triển khai (không cần mật khẩu, chỉ đúng các lệnh này)
cat > /etc/sudoers.d/superhuy <<SUDO
$APPUSER ALL=(root) NOPASSWD: /bin/systemctl restart superhuy, /bin/systemctl start superhuy, /bin/systemctl stop superhuy, /bin/systemctl is-active superhuy, /usr/bin/systemctl restart superhuy, /usr/bin/systemctl start superhuy, /usr/bin/systemctl stop superhuy, /usr/bin/systemctl is-active superhuy
SUDO
chmod 440 /etc/sudoers.d/superhuy

echo "==> 5/7 Caddy cho $DOMAIN"
cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
    encode gzip
    request_body {
        max_size 20MB
    }
    reverse_proxy 127.0.0.1:8787
}
CADDY
systemctl enable caddy >/dev/null
systemctl reload caddy || systemctl restart caddy
if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then ufw allow 22/tcp; ufw allow 80/tcp; ufw allow 443/tcp; fi

echo "==> 6/7 Khoá SSH"
H=/home/$APPUSER
sudo -u $APPUSER mkdir -p $H/.ssh && chmod 700 $H/.ssh
if [ ! -f $H/.ssh/gha_deploy ]; then
  sudo -u $APPUSER ssh-keygen -q -t ed25519 -N "" -C "github-actions-deploy" -f $H/.ssh/gha_deploy
  cat $H/.ssh/gha_deploy.pub >> $H/.ssh/authorized_keys
  chown $APPUSER:$APPUSER $H/.ssh/authorized_keys && chmod 600 $H/.ssh/authorized_keys
fi
if [ ! -f $ROOT/shared/vault_deploy_key ]; then
  sudo -u $APPUSER ssh-keygen -q -t ed25519 -N "" -C "superhuy-vault" -f $ROOT/shared/vault_deploy_key
fi

echo "==> 7/7 Cấu hình .env cho VPS"
ENVF=$ROOT/shared/.env
touch $ENVF && chown $APPUSER:$APPUSER $ENVF && chmod 600 $ENVF
setenv(){ grep -q "^$1=" $ENVF && sed -i "s#^$1=.*#$1=$2#" $ENVF || echo "$1=$2" >> $ENVF; }
setenv WEBAPP_URL "https://$DOMAIN"
setenv OBSIDIAN_VAULT "$ROOT/shared/vault"
setenv OBSIDIAN_EMBED_AUDIO 0
setenv VAULT_SSH_KEY "$ROOT/shared/vault_deploy_key"
setenv TIMEZONE Asia/Ho_Chi_Minh
[ -n "$VAULT_REMOTE" ] && setenv VAULT_GIT_REMOTE "$VAULT_REMOTE"

IP=$(curl -fsS -4 https://ifconfig.me || hostname -I | awk '{print $1}')
cat <<DONE

==================== XONG PHẦN CÀI VPS ====================
1) Tên miền: tạo bản ghi DNS loại A:  $DOMAIN  ->  $IP
2) GitHub repo code > Settings > Secrets and variables > Actions > New repository secret:
     VPS_HOST     = $IP
     VPS_USER     = $APPUSER
     VPS_SSH_KEY  = (toàn bộ khoá bên dưới, kể cả dòng BEGIN/END)
--------------------------------------------------------------
$(cat $H/.ssh/gha_deploy)
--------------------------------------------------------------
   và tab Variables > New repository variable:  APP_URL = https://$DOMAIN
3) Repo Obsidian (private) > Settings > Deploy keys > Add deploy key, TICK "Allow write access":
$(cat $ROOT/shared/vault_deploy_key.pub)
4) Báo Claude "xong" để tắt bot trên Mac và chạy lần triển khai đầu tiên (GitHub Actions).
============================================================
DONE
