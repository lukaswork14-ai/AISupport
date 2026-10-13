#!/bin/bash
# Bấm đúp trên Mac: nối kho Obsidian trên Mac với superHuy (2 chiều) qua repo riêng tư lukaswork14-ai/superhuy-vault.
# - Sao lưu kho hiện tại -> gộp ghi chú trên Mac với ghi chú superHuy đã lưu trên VPS -> đẩy lên repo
# - Cài plugin Obsidian Git để Obsidian tự kéo/đẩy mỗi 5 phút. Không cần mật khẩu: dùng khoá riêng data/obsidian_mac_key.
set -e
cd "$(dirname "$0")/.."
ARMY="$(pwd)"
REMOTE="${VAULT_REMOTE:-git@github.com:lukaswork14-ai/superhuy-vault.git}"
KEY="$ARMY/data/obsidian_mac_key"
[ -f "$KEY" ] || { echo "Thiếu khoá $KEY"; exit 1; }
chmod 600 "$KEY"
SSHCMD="ssh -i \"$KEY\" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

# kho Obsidian đang dùng: lấy kho mở gần nhất trong cấu hình Obsidian, mặc định ~/SecondBrain
VAULT="${OBSIDIAN_VAULT:-}"
# ưu tiên kho superHuy vẫn dùng (~/SecondBrain) nếu có
[ -z "$VAULT" ] && [ -d "$HOME/SecondBrain" ] && VAULT="$HOME/SecondBrain"
if [ -z "$VAULT" ] && [ -f "$HOME/Library/Application Support/obsidian/obsidian.json" ]; then
  VAULT=$(/usr/bin/python3 - <<'PY' 2>/dev/null || true
import json, os
d = json.load(open(os.path.expanduser("~/Library/Application Support/obsidian/obsidian.json")))
vs = sorted(d.get("vaults", {}).values(), key=lambda v: -v.get("ts", 0))
print(vs[0]["path"] if vs else "")
PY
)
fi
VAULT="${VAULT:-$HOME/SecondBrain}"
echo "=== Nối Obsidian với superHuy ==="
echo "Kho Obsidian: $VAULT"
echo "Repo:         $REMOTE"
command -v git >/dev/null && git --version >/dev/null 2>&1 || { echo "Máy chưa có git: macOS sẽ hỏi cài Command Line Tools, bấm Cài đặt rồi chạy lại file này."; xcode-select --install || true; exit 1; }
mkdir -p "$VAULT"

STAMP=$(date +%Y%m%d-%H%M)
if [ ! -d "$VAULT/.git" ]; then
  BACKUP="$VAULT-sao-luu-$STAMP"
  echo "1/5 Sao lưu kho hiện tại -> $BACKUP"
  cp -R "$VAULT" "$BACKUP"
  echo "2/5 Tải ghi chú superHuy từ repo"
  TMP=$(mktemp -d)
  if GIT_SSH_COMMAND="$SSHCMD" git clone -q "$REMOTE" "$TMP/v" 2>/tmp/obsidian-clone.err; then :; else
    if grep -qi "empty repository" /tmp/obsidian-clone.err; then mkdir -p "$TMP/v" && git -C "$TMP/v" init -q -b main && git -C "$TMP/v" remote add origin "$REMOTE"
    else cat /tmp/obsidian-clone.err; echo "Không tải được repo (kiểm tra deploy key của Mac trên GitHub)."; exit 1; fi
  fi
  echo "3/5 Gộp: giữ mọi ghi chú trên Mac, thêm ghi chú superHuy chưa có"
  rsync -a --ignore-existing --exclude .git "$TMP/v/" "$VAULT/"
  mv "$TMP/v/.git" "$VAULT/.git"
  rm -rf "$TMP"
fi
cd "$VAULT"
git config core.sshCommand "$SSHCMD"
git config user.name "Huy (Obsidian Mac)"
git config user.email "obsidian-mac@superhuy.local"
git config pull.rebase true
[ -f .gitignore ] || printf '.obsidian/workspace*.json\n.obsidian/plugins/*/data.json.bak\n.trash/\n.DS_Store\n' > .gitignore

echo "4/5 Cài plugin Obsidian Git (tự kéo/đẩy mỗi 5 phút)"
P=".obsidian/plugins/obsidian-git"; mkdir -p "$P"
for f in main.js manifest.json styles.css; do
  curl -fsSL "https://github.com/Vinzent03/obsidian-git/releases/latest/download/$f" -o "$P/$f" || echo "  (không tải được $f)"
done
[ -f "$P/data.json" ] || cat > "$P/data.json" <<'JSON'
{"commitMessage":"Obsidian Mac {{date}}","autoSaveInterval":5,"autoPushInterval":0,"autoPullInterval":5,"autoPullOnBoot":true,"disablePush":false,"pullBeforePush":true,"syncMethod":"rebase","disablePopups":false,"showStatusBar":true,"differentIntervalCommitAndPush":false}
JSON
/usr/bin/python3 - <<'PY'
import json, os
f = ".obsidian/community-plugins.json"
try: l = json.load(open(f))
except Exception: l = []
if "obsidian-git" not in l: l.append("obsidian-git")
json.dump(l, open(f, "w"))
PY

echo "5/5 Đẩy lên repo"
git add -A
git commit -qm "Obsidian Mac: nối với superHuy $STAMP" || true
git fetch -q origin main 2>/dev/null && git pull -q --rebase --allow-unrelated-histories origin main || true
git push -q -u origin HEAD:main
echo
echo "XONG. Mở Obsidian › Settings › Community plugins › bật 'Turn on community plugins' và bật 'Git' nếu chưa bật."
echo "Từ giờ: ghi chú superHuy tự về Obsidian, ghi chú anh viết trong Obsidian tự lên superHuy (5–10 phút)."
