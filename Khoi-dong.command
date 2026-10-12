#!/bin/bash
# Nhấp đúp sau khi đã dán khóa vào Dien-khoa.txt và lưu lại.
cd "$(dirname "$0")"
if [ ! -f .env ]; then
  if [ ! -f Dien-khoa.txt ]; then echo "Không thấy Dien-khoa.txt"; read -n 1 -s -r -p "Nhấn phím để thoát"; exit 1; fi
  if grep -qE '^(TELEGRAM_TOKEN|LLM_API_KEY)=\s*$' Dien-khoa.txt; then
    echo "Chưa điền đủ TELEGRAM_TOKEN và LLM_API_KEY trong Dien-khoa.txt. Hãy điền, lưu (Cmd+S) rồi chạy lại."
    read -n 1 -s -r -p "Nhấn phím để thoát"; exit 1
  fi
  grep -v '^\s*#' Dien-khoa.txt | grep -v '^\s*$' > .env
  chmod 600 .env
  rm -f Dien-khoa.txt
  echo "Đã tạo .env và xóa file mẫu."
fi
bash install_mac.sh
echo
echo "Bot đã được cài chạy ngầm. Hãy nhắn thử cho bot trên Telegram."
read -n 1 -s -r -p "Nhấn phím bất kỳ để thoát..."
