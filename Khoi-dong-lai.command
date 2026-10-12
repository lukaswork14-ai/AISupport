#!/bin/bash
# Khởi động lại bot sau khi sửa code.
P="$HOME/Library/LaunchAgents/com.agentarmy.plist"
launchctl unload "$P" 2>/dev/null; launchctl load "$P" && echo "Đã khởi động lại bot."
sleep 3
