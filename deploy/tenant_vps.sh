#!/usr/bin/env bash
# superYou thí điểm: cài thêm MỘT khách hàng (tenant) chạy tách biệt trên cùng VPS, dùng chung mã nguồn /opt/superhuy/current.
# Mỗi khách: thư mục dữ liệu riêng, file .env riêng (bot Telegram, LLM, tài khoản riêng), cổng riêng, dịch vụ systemd riêng, tên miền riêng.
# Chạy bằng root (một lần cho mỗi khách):
#   sudo bash deploy/tenant_vps.sh <slug> <tên-miền> <cổng>
#   ví dụ: sudo bash deploy/tenant_vps.sh acme acme.superyou.roimaxxhub.com 8801
# Sau đó điền khoá vào /opt/superyou-tenants/<slug>/.env (KHÔNG đưa khoá vào repo), rồi: systemctl start superyou@<slug>
set -euo pipefail
SLUG="${1:-}"; DOMAIN="${2:-}"; PORT="${3:-}"
[[ "$SLUG" =~ ^[a-z0-9-]{2,30}$ ]] || { echo "slug chỉ gồm a-z, 0-9, dấu gạch (2-30 ký tự)"; exit 1; }
[ -n "$DOMAIN" ] && [[ "$PORT" =~ ^88[0-9]{2}$ ]] || { echo "Cách dùng: sudo bash tenant_vps.sh <slug> <tên-miền> <cổng 8801-8899>"; exit 1; }
[ "$(id -u)" = 0 ] || { echo "Cần chạy bằng root"; exit 1; }
[ "$PORT" != 8787 ] || { echo "Cổng 8787 là của superHuy chính"; exit 1; }
ss -ltn | grep -q ":$PORT " && { echo "Cổng $PORT đang bận"; exit 1; }
APPUSER=superhuy
BASE=/opt/superyou-tenants
H=$BASE/$SLUG
mkdir -p $H/data $H/vault
if [ ! -f $H/.env ]; then
  cat > $H/.env <<ENV
# Khách hàng: $SLUG — điền khoá riêng của khách. Không dùng chung khoá với superHuy của anh Huy.
TELEGRAM_TOKEN=
OWNER_CHAT_ID=
LLM_API_KEY=
WEBAPP_URL=https://$DOMAIN
WEBAPP_PORT=$PORT
OBSIDIAN_VAULT=$H/vault
ENV
fi
chown -R $APPUSER:$APPUSER $BASE
chmod 750 $BASE $H
chmod 600 $H/.env

# Dịch vụ dạng mẫu: superyou@<slug>
cat > /etc/systemd/system/superyou@.service <<'UNIT'
[Unit]
Description=superYou tenant %i
After=network-online.target
Wants=network-online.target

[Service]
User=superhuy
WorkingDirectory=/opt/superhuy/current
Environment=SUPERHUY_HOME=/opt/superyou-tenants/%i
EnvironmentFile=/opt/superyou-tenants/%i/.env
Environment=PYTHONUNBUFFERED=1
Environment=TZ=Asia/Ho_Chi_Minh
ExecStart=/opt/superhuy/venv/bin/python main.py
Restart=always
RestartSec=5
TimeoutStopSec=20
MemoryMax=900M

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable "superyou@$SLUG" >/dev/null

# Cho phép bản triển khai tự khởi động lại các tenant (chỉ đúng lệnh này)
cat > /etc/sudoers.d/superyou-tenants <<SUDO
$APPUSER ALL=(root) NOPASSWD: /bin/systemctl restart superyou@*, /usr/bin/systemctl restart superyou@*, /bin/systemctl is-active superyou@*, /usr/bin/systemctl is-active superyou@*
SUDO
chmod 440 /etc/sudoers.d/superyou-tenants
visudo -cf /etc/sudoers.d/superyou-tenants >/dev/null

# nginx + HTTPS cho tên miền của khách
if systemctl is-active --quiet nginx; then
  cat > /etc/nginx/sites-available/superyou-$SLUG <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    client_max_body_size 20m;
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
  ln -sfn /etc/nginx/sites-available/superyou-$SLUG /etc/nginx/sites-enabled/superyou-$SLUG
  nginx -t && systemctl reload nginx
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect \
    || echo "!! Chưa lấy được HTTPS: kiểm tra bản ghi DNS của $DOMAIN trỏ về VPS rồi chạy lại: certbot --nginx -d $DOMAIN"
fi
echo "==> Xong. Điền khoá vào $H/.env rồi: systemctl start superyou@$SLUG"
