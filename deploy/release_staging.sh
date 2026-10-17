#!/usr/bin/env bash
# Chạy trên VPS (user superhuy) sau khi workflow "Triển khai staging" chép nhánh vào /opt/superhuy-staging/releases/<sha>.
# Chỉ đụng /opt/superhuy-staging. Không bao giờ chạm /opt/superhuy (bản chính) hay dữ liệu của anh.
set -euo pipefail
SHA="${1:?thiếu sha}"; BRANCH="${2:-?}"
S=/opt/superhuy-staging
REL=$S/releases/$SHA
PY=$S/venv/bin/python
PORT=$(grep -E '^WEBAPP_PORT=' $S/shared/.env | cut -d= -f2); PORT=${PORT:-8790}
export SUPERHUY_HOME=$S/shared
[ -f $S/shared/STAGING ] || { echo "!! Không thấy $S/shared/STAGING: dừng để tránh nhầm dữ liệu thật."; exit 1; }
cd "$REL"

echo "==> Thư viện Python (venv staging)"
REQ_HASH=$(sha256sum requirements.txt | cut -c1-16)
if [ "$(cat $S/venv/.req_hash 2>/dev/null)" != "$REQ_HASH" ]; then
  $PY -m pip install -q --upgrade pip
  $PY -m pip install -q -r requirements.txt
  echo "$REQ_HASH" > $S/venv/.req_hash
fi
$PY -m compileall -q . >/dev/null

if ! grep -qE '^TELEGRAM_TOKEN=.+' $S/shared/.env; then
  echo "!! Chưa điền bot Telegram THỬ vào $S/shared/.env: đã chép code, chưa khởi động staging."; exit 1
fi
ln -sfn "$REL" $S/current.new && mv -Tf $S/current.new $S/current
echo "$BRANCH $SHA $(date -Is)" > $S/shared/DEPLOYED
sudo systemctl restart superhuy-staging
for i in $(seq 1 30); do
  sleep 2
  if curl -fsS -m 3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
    echo "==> Staging chạy nhánh $BRANCH ($SHA)"
    ls -1dt $S/releases/*/ | tail -n +4 | xargs -r rm -rf   # giữ 3 bản
    exit 0
  fi
done
echo "!! Staging không lên được với nhánh $BRANCH:"; journalctl -u superhuy-staging -n 40 --no-pager 2>/dev/null | grep -v -i -E 'token|key=|secret' || true
exit 1
