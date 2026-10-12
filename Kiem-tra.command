#!/bin/bash
cd "$(dirname "$0")"
.venv/bin/python kiemtra_google.py
echo; read -n 1 -s -r -p "Xong. Nhấn phím bất kỳ để thoát..."
