#!/usr/bin/env bash
# Staging superHuy: một dịch vụ thứ hai trên cùng VPS để xem trước nhánh PR trước khi gộp vào main.
# Hoàn toàn tách khỏi bản chính: mã, venv, dữ liệu (SUPERHUY_HOME), .env, bot Telegram và cổng riêng.
# Chạy bằng root MỘT lần:
#   sudo bash deploy/staging_vps.sh staging.roimaxxhub.com [cổng=8790]
# Sau đó điền khoá vào /opt/superhuy-staging/shared/.env (bot Telegram THỬ riêng, không dùng token của superHuy),
# rồi chạy workflow "Triển khai staging" trên GitHub với tên nhánh.
set -euo pipefail
DOMAIN="${1:-}"; PORT="${2:-8790}"
[ -n "$DOMAIN" ] || { echo "Cách dùng: sudo bash staging_vps.sh <tên-miền> [cổng 8790-8799]"; exit 1; }
[[ "$PORT" =~ ^879[0-9]$ ]] || { echo "Cổng staging phải trong 8790-8799"; exit 1; }
[ "$(id -u)" = 0 ] || { echo "Cần chạy bằng root"; exit 1; }
APPUSER=superhuy
S=/opt/superhuy-staging
if ! ss -ltn | grep -q ":$PORT " ; then :; elif ! systemctl is-active --quiet superhuy-staging; then echo "Cổng $PORT đang bận"; exit 1; fi

mkdir -p $S/releases $S/shared/data $S/shared/vault
[ -x $S/venv/bin/python ] || python3 -m venv $S/venv   # venv riêng: nhánh thử thư viện mới không làm hỏng bản chính
if [ ! -f $S/shared/.env ]; then
  cat > $S/shared/.env <<ENV
# STAGING: chỉ để xem trước nhánh PR. Dùng bot Telegram THỬ riêng (BotFather), KHÔNG dùng token của superHuy chính.
# Không đặt VAULT_GIT_REMOTE (để staging không đẩy ghi chú vào vault thật của anh).
TELEGRAM_TOKEN=
OWNER_CHAT_ID=
LLM_API_KEY=
WEBAPP_URL=https://$DOMAIN
WEBAPP_PORT=$PORT
OBSIDIAN_VAULT=$S/shared/vault
# 1 = xem trước giao diện superYou của khách; để trống = giao diện superHuy
SUPERYOU_TENANT=
ENV
fi
touch $S/shared/STAGING
chown -R $APPUSER:$APPUSER $S
chmod 750 $S $S/shared
chmod 600 $S/shared/.env

cat > /etc/systemd/system/superhuy-staging.service <<UNIT
[Unit]
Description=superHuy STAGING (xem truoc nhanh PR)
After=network-online.target
Wants=network-online.target

[Service]
User=$APPUSER
WorkingDirectory=$S/current
Environment=SUPERHUY_HOME=$S/shared
EnvironmentFile=$S/shared/.env
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Asia/Ho_Chi_Minh
ExecStart=$S/venv/bin/python main.py
Restart=on-failure
RestartSec=10
TimeoutStopSec=20
MemoryMax=600M
CPUQuota=60%

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable superhuy-staging >/dev/null

# Cho phép bản triển khai staging khởi động lại / dừng staging (chỉ đúng các lệnh này)
cat > /etc/sudoers.d/superhuy-staging <<SUDO
$APPUSER ALL=(root) NOPASSWD: /bin/systemctl restart superhuy-staging, /usr/bin/systemctl restart superhuy-staging, /bin/systemctl stop superhuy-staging, /usr/bin/systemctl stop superhuy-staging, /bin/systemctl is-active superhuy-staging, /usr/bin/systemctl is-active superhuy-staging
SUDO
chmod 440 /etc/sudoers.d/superhuy-staging
visudo -cf /etc/sudoers.d/superhuy-staging >/dev/null

if systemctl is-active --quiet nginx; then
  cat > /etc/nginx/sites-available/superhuy-staging <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    client_max_body_size 20m;
    add_header X-Robots-Tag "noindex, nofollow" always;
    location / {
        proxy_pass http://127.0.0.1:$PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
    }
}
NGINX
  ln -sfn /etc/nginx/sites-available/superhuy-staging /etc/nginx/sites-enabled/superhuy-staging
  nginx -t && systemctl reload nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect \
    || echo "!! Chưa lấy được HTTPS: kiểm tra bản ghi DNS $DOMAIN rồi chạy lại: certbot --nginx -d $DOMAIN"
fi
echo "==> Xong. Điền khoá bot THỬ vào $S/shared/.env, rồi chạy workflow \"Triển khai staging\" với tên nhánh."
