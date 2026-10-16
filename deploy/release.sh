#!/usr/bin/env bash
# Chạy trên VPS (user superhuy) sau khi GitHub Actions chép code vào /opt/superhuy/releases/<sha>.
# Kiểm tra -> chuyển 'current' sang bản mới -> khởi động lại -> nếu không lên được thì quay về bản cũ.
set -euo pipefail
SHA="${1:?thiếu sha}"
ROOT=/opt/superhuy
REL=$ROOT/releases/$SHA
PY=$ROOT/venv/bin/python
export SUPERHUY_HOME=$ROOT/shared
cd "$REL"

echo "==> Thư viện Python"
REQ_HASH=$(sha256sum requirements.txt | cut -c1-16)
if [ "$(cat $ROOT/venv/.req_hash 2>/dev/null)" != "$REQ_HASH" ]; then
  $PY -m pip install -q --upgrade pip
  $PY -m pip install -q -r requirements.txt
  echo "$REQ_HASH" > $ROOT/venv/.req_hash
fi

echo "==> Kiểm tra mã"
$PY -m compileall -q . >/dev/null
$PY - <<'PY'
import importlib
for m in ("config", "hub", "brain", "agents.meeting", "agents.content_hub", "core.qc", "webapp.server"):
    importlib.import_module(m)
print("import OK")
PY

echo "==> Chuyển sang bản $SHA"
PREV=$(readlink -f $ROOT/current 2>/dev/null || true)
ln -sfn "$REL" $ROOT/current.new && mv -Tf $ROOT/current.new $ROOT/current

if [ ! -f $ROOT/shared/.env ] || ! grep -q "^TELEGRAM_TOKEN=" $ROOT/shared/.env; then
  echo "Chưa có dữ liệu/khoá (chưa chạy import_data.sh): đã cài code, chưa khởi động bot."
  exit 0
fi

# cấu hình mặc định không bí mật (vd repo Obsidian): chỉ thêm khoá còn thiếu
if [ -f "$REL/deploy/vps_defaults.env" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|\#*) continue;; esac
    k="${line%%=*}"
    grep -q "^$k=" $ROOT/shared/.env || { echo "$line" >> $ROOT/shared/.env; echo "  + $k"; }
  done < "$REL/deploy/vps_defaults.env"
fi

sudo systemctl restart superhuy
ok=0
for i in $(seq 1 30); do
  sleep 2
  if curl -fsS -m 3 http://127.0.0.1:8787/health >/dev/null 2>&1; then ok=1; break; fi
done
if [ $ok != 1 ]; then
  echo "!! Bản mới không chạy được, quay về bản trước: $PREV"
  journalctl -u superhuy -n 40 --no-pager || true
  if [ -n "$PREV" ] && [ -d "$PREV" ]; then
    ln -sfn "$PREV" $ROOT/current.new && mv -Tf $ROOT/current.new $ROOT/current
    sudo systemctl restart superhuy
  fi
  exit 1
fi
echo "==> Bot đã chạy bản $SHA"
# superYou thí điểm: khởi động lại các tenant để dùng bản mới (nếu có)
for u in $(systemctl list-units --type=service --state=running --no-legend 'superyou@*' 2>/dev/null | awk '{print $1}'); do
  sudo systemctl restart "$u" && echo "  ↻ $u" || echo "  !! không khởi động lại được $u"
done
# giữ 5 bản gần nhất để quay lại khi cần
ls -1dt $ROOT/releases/*/ | tail -n +6 | xargs -r rm -rf
