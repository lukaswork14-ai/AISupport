"""superYou: mỗi khách (tenant) là một instance với SUPERHUY_HOME riêng.
Các test này chạy mỗi instance trong một tiến trình riêng (đúng như systemd superyou@<slug>) và kiểm tra:
- cấu hình (.env) và thư mục dữ liệu không lẫn giữa các instance,
- dữ liệu ghi ở instance A không nhìn thấy được từ instance B,
- instance khách được nhận diện là tenant, instance của anh Huy thì không."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(home: Path, code: str, extra_env: dict | None = None) -> dict:
    env = {k: v for k, v in os.environ.items()
           if k not in ("TELEGRAM_TOKEN", "OWNER_CHAT_ID", "LLM_API_KEY", "SUPERYOU_TENANT", "APP_PIN_HASH")}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT)})
    env.update(extra_env or {})
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def _make_home(base: Path, name: str, token: str, chat: str) -> Path:
    home = base / name
    home.mkdir(parents=True)
    (home / ".env").write_text(f"TELEGRAM_TOKEN={token}\nOWNER_CHAT_ID={chat}\nLLM_API_KEY=key-{name}\n")
    return home


CONFIG_PROBE = (
    "import json, config;"
    "print(json.dumps({'data': str(config.DATA_DIR), 'token': config.TELEGRAM_TOKEN,"
    " 'owner': config.OWNER_CHAT_ID, 'llm': config.LLM_API_KEY, 'tenant': config.IS_TENANT}))"
)


@pytest.fixture()
def homes(tmp_path):
    owner = _make_home(tmp_path, "owner", "111:owner", "1001")
    a = _make_home(tmp_path / "superyou-tenants", "khach-a", "222:a", "2002")
    b = _make_home(tmp_path / "superyou-tenants", "khach-b", "333:b", "3003")
    return owner, a, b


def test_config_is_per_instance(homes):
    owner, a, b = homes
    ra, rb, ro = _run(a, CONFIG_PROBE), _run(b, CONFIG_PROBE), _run(owner, CONFIG_PROBE)
    assert ra["data"] == str(a / "data") and rb["data"] == str(b / "data")
    assert (ra["token"], ra["owner"], ra["llm"]) == ("222:a", 2002, "key-khach-a")
    assert (rb["token"], rb["owner"], rb["llm"]) == ("333:b", 3003, "key-khach-b")
    assert ro["owner"] == 1001


def test_tenant_flag(homes):
    owner, a, _ = homes
    assert _run(a, CONFIG_PROBE)["tenant"] is True            # nhận ra qua thư mục /superyou-tenants/
    assert _run(owner, CONFIG_PROBE)["tenant"] is False       # superHuy của anh Huy không bị coi là khách
    assert _run(owner, CONFIG_PROBE, {"SUPERYOU_TENANT": "1"})["tenant"] is True  # hoặc qua biến môi trường


def test_data_written_in_a_is_invisible_in_b(homes):
    _, a, b = homes
    write = (
        "import json; from core import security;"
        "security.set_pin('246810'); security.unlock_bot();"
        "print(json.dumps({'file': str(security.STATE_FILE), 'exists': security.STATE_FILE.exists()}))"
    )
    read = (
        "import json; from core import security;"
        "print(json.dumps({'file': str(security.STATE_FILE), 'exists': security.STATE_FILE.exists(),"
        " 'state': security._load()}))"
    )
    wa = _run(a, write)
    rb = _run(b, read)
    assert wa["exists"] and wa["file"].startswith(str(a))
    assert rb["file"].startswith(str(b))
    assert not rb["exists"] and rb["state"] == {}
    # mã PIN đặt ở A chỉ nằm trong .env của A
    assert "APP_PIN_HASH=pbkdf2:" in (a / ".env").read_text()
    assert "APP_PIN_HASH" not in (b / ".env").read_text()
    # không file nào của B nằm trong thư mục A và ngược lại
    assert not any(str(b) in str(p) for p in a.rglob("*"))


def test_no_path_escape_between_tenants(homes):
    _, a, b = homes
    probe = "import json, config; print(json.dumps({'data': str(config.DATA_DIR.resolve())}))"
    da = Path(_run(a, probe)["data"])
    assert b.resolve() not in da.parents and da != b.resolve()
