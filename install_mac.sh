#!/bin/bash
# Cài đặt trên macOS. Mở Terminal trong thư mục này rồi chạy:  bash install_mac.sh
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"

if ! command -v python3 >/dev/null; then
  echo "Chưa có Python 3. Cài từ https://www.python.org/downloads/ rồi chạy lại."; exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install --only-binary=:all: -r requirements.txt

[ -f .env ] || .venv/bin/python setup.py

if [ -f data/google_token.json ]; then
  echo "Google đã được kết nối trước đó."
elif [ -f credentials.json ]; then
  .venv/bin/python google_auth.py
else
  echo "Chưa có credentials.json nên bỏ qua kết nối Google. Làm theo README rồi chạy: .venv/bin/python google_auth.py"
fi

# Tự chạy ngầm khi đăng nhập, tự khởi động lại nếu lỗi; caffeinate giữ máy không ngủ khi cắm điện
PLIST="$HOME/Library/LaunchAgents/com.agentarmy.plist"
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.agentarmy</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/caffeinate</string><string>-i</string>
    <string>$DIR/.venv/bin/python</string><string>$DIR/main.py</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$DIR/data/agent.log</string>
  <key>StandardErrorPath</key><string>$DIR/data/agent.log</string>
</dict></plist>
EOF
mkdir -p data
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Xong. Bot đang chạy ngầm. Hãy nhắn thử cho bot trên Telegram."
echo "Mẹo: System Settings > Battery > tắt 'Put hard disks to sleep' và bật 'Prevent automatic sleeping' nếu dùng máy bàn."
