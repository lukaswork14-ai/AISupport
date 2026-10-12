"""Đồng bộ kho ghi chú Obsidian qua một repo git riêng (khi bot chạy trên VPS).
Bật bằng .env: VAULT_GIT_REMOTE=git@github.com:<tài khoản>/<repo-vault>.git
(tuỳ chọn VAULT_SSH_KEY=/opt/superhuy/shared/vault_deploy_key). Mỗi 10 phút: commit thay đổi của bot -> kéo thay đổi
từ Mac về (rebase) -> đẩy lên. Trên Mac, Obsidian dùng plugin "Obsidian Git" để kéo/đẩy cùng repo đó."""
import datetime as dt
import logging
import os
import subprocess

from config import OBSIDIAN_VAULT

log = logging.getLogger("vault-sync")


def enabled() -> bool:
    return bool(os.getenv("VAULT_GIT_REMOTE", "").strip())


def _git(*args, check=True) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    key = os.getenv("VAULT_SSH_KEY", "").strip()
    if key:
        env["GIT_SSH_COMMAND"] = f"ssh -i {key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
    r = subprocess.run(["git", "-C", str(OBSIDIAN_VAULT), *args], capture_output=True, text=True, env=env, timeout=120)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args[:2])}: {(r.stderr or r.stdout).strip()[-300:]}")
    return r


def ensure_repo():
    OBSIDIAN_VAULT.mkdir(parents=True, exist_ok=True)
    if not (OBSIDIAN_VAULT / ".git").exists():
        _git("init", "-b", "main")
        _git("config", "user.name", "superHuy")
        _git("config", "user.email", "superhuy@localhost")
        gi = OBSIDIAN_VAULT / ".gitignore"
        if not gi.exists():
            gi.write_text(".obsidian/workspace*.json\n.trash/\n.DS_Store\n", encoding="utf-8")
    remote = os.getenv("VAULT_GIT_REMOTE", "").strip()
    cur = _git("remote", "get-url", "origin", check=False)
    if cur.returncode != 0:
        _git("remote", "add", "origin", remote)
    elif cur.stdout.strip() != remote:
        _git("remote", "set-url", "origin", remote)


def sync() -> str:
    """Trả về mô tả ngắn; lỗi thì ném ngoại lệ (QC sẽ báo)."""
    if not enabled():
        return "tắt"
    ensure_repo()
    _git("add", "-A")
    changed = _git("diff", "--cached", "--quiet", check=False).returncode != 0
    if changed:
        _git("commit", "-m", f"superHuy {dt.datetime.now():%Y-%m-%d %H:%M}")
    has_remote_main = _git("ls-remote", "--heads", "origin", "main", check=False).stdout.strip() != ""
    if has_remote_main:
        _git("pull", "--rebase", "--autostash", "origin", "main")
    _git("push", "-u", "origin", "main")
    return "đã đẩy thay đổi" if changed else "không có gì mới"
