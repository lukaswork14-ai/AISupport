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
    pulled = False
    if has_remote_main:
        _git("fetch", "origin", "main")
        before = _git("rev-parse", "HEAD", check=False).stdout.strip()
        r = _git("pull", "--rebase", "--autostash", "--allow-unrelated-histories", "origin", "main", check=False)
        if r.returncode != 0:
            # xung đột (cùng một ghi chú sửa ở cả Mac và VPS): huỷ rebase, gộp và giữ cả hai phía, bản của Mac thắng ở dòng trùng
            _git("rebase", "--abort", check=False)
            _git("pull", "--no-rebase", "--no-edit", "--allow-unrelated-histories", "-X", "theirs", "origin", "main")
            log.warning("Vault: có xung đột, đã gộp (ưu tiên bản trên repo/Mac)")
        pulled = before != _git("rev-parse", "HEAD", check=False).stdout.strip()
    _git("push", "-u", "origin", "main")
    parts = (["đẩy ghi chú mới"] if changed else []) + (["nhận ghi chú từ Obsidian"] if pulled else [])
    return ", ".join(parts) or "không có gì mới"


def status() -> dict:
    """Tình trạng đồng bộ để hiển thị trong app / trả lời trong chat."""
    info = {"enabled": enabled(), "vault": str(OBSIDIAN_VAULT), "remote": os.getenv("VAULT_GIT_REMOTE", "")}
    try:
        info["notes"] = sum(1 for _ in OBSIDIAN_VAULT.rglob("*.md"))
    except Exception:
        info["notes"] = 0
    if (OBSIDIAN_VAULT / ".git").exists():
        r = _git("log", "-1", "--format=%cd", "--date=format:%H:%M %d/%m", check=False)
        info["last_commit"] = r.stdout.strip()
    key = os.getenv("VAULT_SSH_KEY", "").strip()
    if key and os.path.exists(key + ".pub"):
        info["public_key"] = open(key + ".pub").read().strip()
    return info


def search(query: str, limit: int = 8) -> list[dict]:
    """Tìm trong kho Obsidian (cả ghi chú anh viết trên Mac): khớp từ khoá theo tiêu đề và nội dung."""
    import re
    words = [w for w in re.findall(r"\w+", (query or "").lower()) if len(w) > 1]
    if not words or not OBSIDIAN_VAULT.exists():
        return []
    hits = []
    for p in OBSIDIAN_VAULT.rglob("*.md"):
        if ".git" in p.parts or ".obsidian" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low, title = text.lower(), p.stem.lower()
        score = sum(low.count(w) + 5 * title.count(w) for w in words)
        if score and all(w in low or w in title for w in words[:3]):
            i = min((low.find(w) for w in words if w in low), default=0)
            hits.append({"score": score, "title": p.stem, "path": str(p.relative_to(OBSIDIAN_VAULT)),
                         "snippet": re.sub(r"\s+", " ", text[max(0, i - 120): i + 280]).strip()})
    hits.sort(key=lambda h: -h["score"])
    return hits[:limit]


def recent_by(author: str, limit: int = 12, days: int = 30) -> list[dict]:
    """Ghi chú do một bên (vd "Obsidian Mac" = anh tự viết/sửa trên Mac) đổi gần đây, mới nhất trước."""
    if not (OBSIDIAN_VAULT / ".git").exists():
        return []
    r = _git("-c", "core.quotepath=false", "log", f"--author={author}", f"--since={days}.days", "--name-only", "--format=@@%cd", "--date=format:%H:%M %d/%m",
             check=False)
    out, seen, when = [], set(), ""
    for ln in r.stdout.splitlines():
        if ln.startswith("@@"):
            when = ln[2:]
            continue
        ln = ln.strip().strip('"')
        if not ln.endswith(".md") or ln in seen or ln.startswith(".obsidian"):
            continue
        seen.add(ln)
        if (OBSIDIAN_VAULT / ln).exists():
            out.append({"path": ln, "title": ln.rsplit("/", 1)[-1][:-3], "folder": ln.rsplit("/", 1)[0] if "/" in ln else "", "when": when})
        if len(out) >= limit:
            break
    return out
