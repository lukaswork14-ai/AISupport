#!/bin/bash
# Nhấp đúp file này để cài đặt đội quân agents.
cd "$(dirname "$0")"
export PATH="/Library/Frameworks/Python.framework/Versions/3.14/bin:/usr/local/bin:$PATH"
clear
echo "=== CÀI ĐẶT ĐỘI QUÂN AGENTS ==="
echo "Python: $(python3 --version 2>&1)"
echo
bash install_mac.sh
echo
echo "Hoàn tất. Bạn có thể đóng cửa sổ này."
read -n 1 -s -r -p "Nhấn phím bất kỳ để thoát..."
