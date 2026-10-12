#!/bin/bash
# Nhấp đúp để kết nối Google (Gmail + Calendar, chỉ quyền ĐỌC).
cd "$(dirname "$0")"
echo "=== KẾT NỐI GOOGLE ==="
echo "Trình duyệt sẽ mở ra. Hãy chọn tài khoản và bấm Tiếp tục/Cho phép."
.venv/bin/python google_auth.py
echo
read -n 1 -s -r -p "Nhấn phím bất kỳ để thoát..."
