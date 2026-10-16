"""superYou: rào chắn an toàn cho instance khách và cho repo.
- Instance khách không được gieo khoá học/chiến lược/Repo radar viết riêng cho anh Huy.
- Script cài khách từ chối slug nguy hiểm và đánh dấu SUPERYOU_TENANT=1.
- Repo không chứa khoá bí mật."""
import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
TENANT_SH = ROOT / "deploy" / "tenant_vps.sh"


def _enclosing_ifs(src: str, needle: str) -> list[str]:
    """Trả về điều kiện các khối if bao quanh dòng chứa `needle` (và nhánh: 'if'/'else')."""
    tree = ast.parse(src)
    found = []

    def walk(node, stack):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.If):
                for branch, body in (("if", child.body), ("else", child.orelse)):
                    for stmt in body:
                        seg = ast.get_source_segment(src, stmt) or ""
                        if needle in seg and needle not in (ast.get_source_segment(src, child.test) or ""):
                            walk_stmt(stmt, stack + [f"{branch}:{ast.unparse(child.test)}"])
            else:
                walk(child, stack)

    def walk_stmt(stmt, stack):
        seg = ast.get_source_segment(src, stmt) or ""
        if needle in seg and not any(needle in (ast.get_source_segment(src, c) or "")
                                     for c in ast.iter_child_nodes(stmt) if isinstance(c, ast.stmt)):
            found.append(stack)
            return
        walk(stmt, stack)

    walk(tree, [])
    return found[0] if found else []


def test_owner_only_bootstraps_are_skipped_on_tenants():
    for name in ("_strategy_bootstrap", "_learning_bootstrap", "_repo_bootstrap"):
        conds = _enclosing_ifs(MAIN, f"target={name}")
        assert "else:IS_TENANT" in conds, f"{name} phải chỉ chạy khi KHÔNG phải instance khách"


def test_owner_only_weekly_jobs_are_skipped_on_tenants():
    for job in ("job_strategy_weekly", "job_repo_weekly"):
        conds = _enclosing_ifs(MAIN, f"add_job({job}")
        assert "if:not IS_TENANT" in conds, f"{job} phải nằm trong `if not IS_TENANT`"


def test_tenant_script_syntax_and_flag():
    subprocess.run(["bash", "-n", str(TENANT_SH)], check=True)
    sh = TENANT_SH.read_text(encoding="utf-8")
    assert "Environment=SUPERYOU_TENANT=1" in sh
    assert "MemoryMax=" in sh and "chmod 600 $H/.env" in sh


def test_tenant_script_rejects_bad_slugs():
    sh = TENANT_SH.read_text(encoding="utf-8")
    m = re.search(r'\[\[ "\$SLUG" =~ (\S+) \]\]', sh)
    assert m, "thiếu kiểm tra slug"
    pattern = re.compile(m.group(1))
    for bad in ("../etc", "a", "A-B", "x;rm", "a b", "very-long-slug-name-over-thirty-chars"):
        assert not pattern.fullmatch(bad), bad
    for good in ("acme", "khach-01"):
        assert pattern.fullmatch(good)


SECRET_PATTERNS = [
    r"sk-or-v1-[0-9a-f]{20,}", r"sk-ant-[A-Za-z0-9_-]{20,}", r"AIza[0-9A-Za-z_-]{35}",
    r"\b\d{8,10}:AA[0-9A-Za-z_-]{33}\b", r"ghp_[A-Za-z0-9]{36}", r"github_pat_[A-Za-z0-9_]{40,}",
    r"xox[bpas]-[A-Za-z0-9-]{20,}", r"EAA[A-Za-z0-9]{60,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----\n[A-Za-z0-9+/=]",
]


def test_no_secrets_in_tracked_files():
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    hits = []
    rx = re.compile("|".join(SECRET_PATTERNS))
    for f in files:
        p = ROOT / f
        if not p.is_file() or p.stat().st_size > 2_000_000:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if rx.search(text):
            hits.append(f)
    assert not hits, f"Có thể lộ khoá bí mật trong: {hits}"
