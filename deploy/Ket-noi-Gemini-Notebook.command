#!/bin/bash
# Bấm đúp trên Mac: nối Gemini Notebook (NotebookLM) của anh với superHuy.
# 1) Cài công cụ đăng nhập (lần đầu ~1-2 phút)  2) Chrome mở trang Gemini Notebook: anh tự đăng nhập Google
# 3) Dán MÃ KẾT NỐI lấy trong app superHuy › Second Brain › Gemini Notebook  4) Phiên được gửi thẳng lên superHuy qua HTTPS rồi xoá khỏi Mac.
# Không có mật khẩu nào đi qua script này; phiên đăng nhập chỉ nằm trên máy chủ superHuy (quyền 600).
cd "$(dirname "$0")/.."
APP="${SUPERHUY_URL:-https://app.roimaxxhub.com}"
V="$HOME/.superhuy-notebooklm"
echo "=== Nối Gemini Notebook với superHuy ==="
PY=""
for c in ./.venv/bin/python3 /usr/local/bin/python3 /opt/homebrew/bin/python3 /usr/bin/python3; do [ -x "$c" ] && { PY="$c"; break; }; done
[ -n "$PY" ] || { echo "Máy chưa có Python 3."; read -n 1 -s -r -p "Nhấn phím để thoát"; exit 1; }
if [ ! -x "$V/bin/notebooklm" ]; then
  echo "1/4 Cài công cụ đăng nhập (chỉ lần đầu)..."
  "$PY" -m venv "$V" && "$V/bin/pip" install -q --upgrade pip && "$V/bin/pip" install -q "notebooklm-py[browser]>=0.8.5,<0.9" \
    || { echo "Cài không thành công. Kiểm tra mạng rồi chạy lại."; read -n 1 -s -r -p "Nhấn phím để thoát"; exit 1; }
else
  echo "1/4 Công cụ đã có, cập nhật nhanh..."
  "$V/bin/pip" install -q --upgrade "notebooklm-py[browser]>=0.8.5,<0.9" >/dev/null 2>&1 || true
fi
TMPH="$(mktemp -d)"; chmod 700 "$TMPH"
trap 'rm -rf "$TMPH"' EXIT
export NOTEBOOKLM_HOME="$TMPH"
F="$TMPH/storage_state.json"
echo
echo "2/4 Cửa sổ Chrome sẽ mở trang Gemini Notebook."
echo "    Anh đăng nhập đúng tài khoản Gmail chứa các notebook. Đăng nhập xong cửa sổ tự đóng (tối đa 10 phút)."
BROWSER=chrome; [ -d "/Applications/Google Chrome.app" ] || BROWSER=chromium
if ! "$V/bin/notebooklm" login --browser "$BROWSER" --storage "$F" --browser-timeout 600; then
  echo "Đăng nhập chưa xong. Chạy lại file này để thử lần nữa."; read -n 1 -s -r -p "Nhấn phím để thoát"; exit 1
fi
echo
echo "3/4 Kiểm tra phiên đăng nhập..."
if "$V/bin/notebooklm" --storage "$F" list >/dev/null 2>&1; then echo "    Đọc được danh sách notebook. OK"; else echo "    (Chưa kiểm tra được, vẫn tiếp tục)"; fi
echo
echo "4/4 Mở app superHuy › Second Brain › Gemini Notebook › Kết nối để lấy mã (8 ký tự)."
for i in 1 2 3; do
  read -r -p "    Dán mã kết nối rồi Enter: " CODE
  CODE="$(echo "$CODE" | tr -d ' ' | tr '[:lower:]' '[:upper:]')"
  [ -n "$CODE" ] || continue
  R="$(curl -sS -X POST -H 'Content-Type: application/json' --data-binary @"$F" "$APP/connect/gemini?code=$CODE")"
  if echo "$R" | grep -q '"ok": *true'; then
    echo; echo "XONG. superHuy đang nạp các notebook, kết quả sẽ báo qua Telegram."
    rm -rf "$TMPH"; read -n 1 -s -r -p "Nhấn phím để đóng"; exit 0
  fi
  echo "    Chưa được: $(echo "$R" | sed 's/.*"error": *"\([^"]*\)".*/\1/')"
done
echo "Chưa gửi được phiên. Lấy mã mới trong app rồi chạy lại file này."
read -n 1 -s -r -p "Nhấn phím để thoát"
