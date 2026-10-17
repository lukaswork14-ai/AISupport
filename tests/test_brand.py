"""Nhận diện superYou v1: mọi file được phục vụ đều tồn tại, manifest của khách dùng icon superYou,
landing không còn màu tím cũ / logo cá nhân ở vị trí logo."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "webapp" / "static"


def _app_files(tenant: bool, tmp_path) -> dict:
    home = tmp_path / ("superyou-tenants/khach" if tenant else "owner")
    home.mkdir(parents=True)
    (home / ".env").write_text("TELEGRAM_TOKEN=1:x\nOWNER_CHAT_ID=1\nLLM_API_KEY=x\n")
    env = {k: v for k, v in os.environ.items() if k not in ("SUPERYOU_TENANT",)}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT)})
    code = "import json; from webapp import server; print(json.dumps(server.APP_FILES))"
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_every_served_file_exists(tmp_path):
    files = _app_files(False, tmp_path)
    missing = [rel for rel in files.values() if not (STATIC / rel).is_file()]
    assert not missing, missing
    assert "/brand/og.png" in files and "/brand/stickers/su-xong-roi.png" in files


def test_tenant_gets_superyou_manifest_and_icons(tmp_path):
    owner = _app_files(False, tmp_path / "o")
    tenant = _app_files(True, tmp_path / "t")
    assert owner["/manifest.webmanifest"] == "manifest.webmanifest"          # superHuy của anh Huy giữ nguyên
    assert tenant["/manifest.webmanifest"] == "manifest-superyou.webmanifest"
    assert tenant["/favicon.ico"].startswith("brand/") and tenant["/apple-touch-icon.png"].startswith("brand/")
    m = json.loads((STATIC / "manifest-superyou.webmanifest").read_text(encoding="utf-8"))
    assert m["name"] == "superYou"
    for icon in m["icons"]:
        assert (STATIC / icon["src"].lstrip("/").split("?")[0]).is_file(), icon


def test_landing_uses_brand():
    html = (STATIC / "landing" / "index.html").read_text(encoding="utf-8")
    assert "#6A3DF0" not in html and "#FF5AA8" not in html
    assert "/brand/og.png" in html and "/brand/icon-128.png" in html
    assert "Nói là xong." in html
