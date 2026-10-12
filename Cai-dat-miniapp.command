#!/bin/bash
# Cài Cloudflare Tunnel (miễn phí, chính chủ Cloudflare) để Telegram mở được Mini App chạy trên máy này.
cd "$(dirname "$0")"
mkdir -p bin
if [ "$(uname -m)" = "arm64" ]; then A=arm64; else A=amd64; fi
echo "Đang tải cloudflared ($A) từ github.com/cloudflare/cloudflared ..."
curl -fL --progress-bar -o bin/cloudflared.tgz "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-$A.tgz" \
  && tar -xzf bin/cloudflared.tgz -C bin && rm -f bin/cloudflared.tgz && chmod +x bin/cloudflared
bin/cloudflared --version > data/cai_miniapp.txt 2>&1
cat data/cai_miniapp.txt
launchctl unload ~/Library/LaunchAgents/com.agentarmy.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/com.agentarmy.plist
echo "Xong. Bot đã khởi động lại, nút 'Mở app' sẽ xuất hiện trong chat với bot sau ~30 giây."
sleep 3
exit 0
