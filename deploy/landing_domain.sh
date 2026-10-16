#!/usr/bin/env bash
# Đưa landing page + Marketplace superYou lên tên miền riêng (chạy bằng root, một lần):
#   sudo bash deploy/landing_domain.sh superyou.roimaxxhub.com
# Trước đó thêm bản ghi DNS: A  superyou  -> IP của VPS (cùng IP với app.roimaxxhub.com).
# Tên miền mới: / -> landing, /market -> Marketplace. Link cũ app.roimaxxhub.com/landing vẫn chạy.
set -euo pipefail
DOMAIN="${1:-}"
[ -n "$DOMAIN" ] || { echo "Cách dùng: sudo bash landing_domain.sh <tên-miền>"; exit 1; }
[ "$(id -u)" = 0 ] || { echo "Cần chạy bằng root"; exit 1; }
systemctl is-active --quiet nginx || { echo "Cần nginx"; exit 1; }
cat > /etc/nginx/sites-available/superyou-landing <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;
    location = / { proxy_pass http://127.0.0.1:8787/landing; proxy_set_header Host \$host; proxy_set_header X-Real-IP \$remote_addr; }
    location ~ ^/(landing|market|icons|api/waitlist|api/market|api/creator|favicon.ico|apple-touch-icon.png) {
        proxy_pass http://127.0.0.1:8787;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location / { return 302 /; }
}
NGINX
ln -sfn /etc/nginx/sites-available/superyou-landing /etc/nginx/sites-enabled/superyou-landing
nginx -t && systemctl reload nginx
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --register-unsafely-without-email --redirect \
  || echo "!! Chưa lấy được HTTPS: kiểm tra DNS rồi chạy lại: certbot --nginx -d $DOMAIN"
echo "==> Xong: https://$DOMAIN"
