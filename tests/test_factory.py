"""Xưởng Tài sản số: điểm nguồn, phân loại ngành/vai trò, nguồn không rõ giấy phép bị loại, quét khung làm việc và chợ (không gọi mạng).

Mỗi test chạy trong tiến trình riêng với SUPERHUY_HOME riêng, không có LLM (các bước AI phải rơi về đường dự phòng, không crash).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _run(home: Path, code: str) -> dict:
    env = {k: v for k, v in os.environ.items() if k not in ("TELEGRAM_TOKEN", "OWNER_CHAT_ID", "LLM_API_KEY", "SUPERYOU_TENANT", "GITHUB_TOKEN")}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT), "TELEGRAM_TOKEN": "1:test", "OWNER_CHAT_ID": "1",
                "LLM_API_KEY": "test", "LLM_BASE_URL": "http://127.0.0.1:9/v1"})
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.fixture()
def home(tmp_path):
    h = tmp_path / "xuong"
    h.mkdir()
    return h


# GitHub giả lập: 4 repo với giấy phép khác nhau (không gọi mạng)
GH_STUB = r"""
import json
from agents import factory
def _fake_get(url, ttl=0, params=None):
    assert "api.github.com/search" in url
    mk = lambda n, lic, lang, stars: {"full_name": "org/" + n, "name": n, "owner": {"login": "org", "avatar_url": ""}, "language": lang, "html_url": "https://github.com/org/" + n,
                                     "stargazers_count": stars, "description": n.replace("-", " ") + " prompts and agent skills collection", "license": {"spdx_id": lic} if lic else None,
                                     "topics": ["prompts"], "pushed_at": "2026-10-01T00:00:00Z"}
    return {"items": [mk("awesome-prompts", "MIT", None, 9000), mk("secret-prompts", "", "Markdown", 3000), mk("prompt-cli", "Apache-2.0", "Rust", 800),
                      mk("odd-license", "NOASSERTION", None, 500)]}
factory._get = _fake_get
"""

SCORE = GH_STUB + r"""
ok = factory.score_source({"name": "awesome prompts", "summary": "collection of chatgpt prompts and agent skills", "cat": "Markdown", "license": "MIT", "ratings": 5000, "src": "github"})
nolic = factory.score_source({"name": "awesome prompts", "summary": "collection of chatgpt prompts and agent skills", "cat": "Markdown", "license": "", "ratings": 5000, "src": "github"})
code = factory.score_source({"name": "fast cli", "summary": "a cli tool", "cat": "Go", "license": "MIT", "ratings": 5000, "src": "github"})
print(json.dumps({"ok": ok, "nolic": nolic, "code": code, "cls": factory.classify("Sales playbook for e-commerce POD sellers"),
                  "cls2": factory.classify("gì đó không rõ", "luat", "nhan-su")}))
"""


def test_diem_nguon_va_giay_phep(home):
    r = _run(home, SCORE)
    assert r["ok"]["clone_ok"] and r["ok"]["score"] >= 60 and r["ok"]["parts"]["giay_phep"] == 25
    assert sum(r["ok"]["parts"].values()) == r["ok"]["score"] <= 100
    # cùng nội dung nhưng không rõ giấy phép: 0 điểm giấy phép và bị loại
    assert r["nolic"]["parts"]["giay_phep"] == 0 and not r["nolic"]["clone_ok"]
    assert any("Giấy phép" in x for x in r["nolic"]["reasons"])
    # repo mã nguồn khó cài một chạm -> dưới ngưỡng
    assert r["code"]["score"] < 60 and not r["code"]["clone_ok"]
    assert r["cls"] == ["tmdt-pod", "sales"]
    assert r["cls2"] == ["luat", "nhan-su"]


SCAN = GH_STUB + r"""
gh = factory.scan("github", q="prompts")
fw = factory.scan("framework")
mk = factory.scan("market")
luat = factory.scan("framework", industry="tai-chinh-ke-toan")
print(json.dumps({"fw_n": len(fw["items"]), "fw_ok": sum(1 for i in fw["items"] if i["clone_ok"]), "fw_keys": [i["key"] for i in fw["items"]][:3],
                  "fw_fields": sorted(k for k in fw["items"][0] if k in ("score", "parts", "industry", "role", "kind", "license", "clone_ok")),
                  "sources": list(fw["filters"]["sources"]), "industries": list(fw["filters"]["industries"]), "roles": list(fw["filters"]["roles"]),
                  "mk_n": len(mk["items"]), "mk_lic": sorted({i["license"] for i in mk["items"]}), "luat": [i["industry"] for i in luat["items"]],
                  "sorted": [i["score"] for i in fw["items"]], "detail": factory.detail("framework:okr")["questions"][:2],
                  "legacy": factory.scan("ios")["label"], "gh": [[i["name"], i["clone_ok"], i["license"]] for i in gh["items"]]}))
"""


def test_quet_khung_cho_va_github(home):
    r = _run(home, SCAN)
    assert r["fw_n"] >= 8 and r["fw_ok"] == r["fw_n"]
    assert all(k.startswith("framework:") for k in r["fw_keys"])
    assert r["fw_fields"] == ["clone_ok", "industry", "kind", "license", "parts", "role", "score"]
    assert r["sources"] == ["github", "template", "framework", "market"]  # không còn ios/mac/ph
    assert r["industries"] == ["tmdt-pod", "ban-le", "luat", "tai-chinh-ke-toan", "marketing-agency", "giao-duc", "bat-dong-san", "san-xuat", "dich-vu", "khac"]
    assert r["roles"] == ["ceo-chu-dn", "quan-ly", "sales", "marketing", "van-hanh", "tai-chinh", "nhan-su", "solopreneur", "chuyen-vien"]
    assert r["mk_n"] >= 1 and r["mk_lic"] == ["superyou"]  # sản phẩm chính chủ trên chợ mới được clone
    assert r["luat"] and set(r["luat"]) == {"tai-chinh-ke-toan"}
    assert r["sorted"] == sorted(r["sorted"], reverse=True)
    assert len(r["detail"]) == 2
    assert r["legacy"].startswith("Kho skill")  # nguồn cũ (ios) rơi về nguồn mặc định
    gh = {n: (ok, lic) for n, ok, lic in r["gh"]}
    assert gh["awesome-prompts"] == (True, "MIT")
    assert gh["secret-prompts"][0] is False and gh["secret-prompts"][1] == ""  # không có giấy phép: loại
    assert gh["odd-license"] == (False, "")  # NOASSERTION = không rõ
    assert gh["prompt-cli"][0] is False  # mã nguồn Rust, không cài một chạm


SUGGEST = GH_STUB + r"""
factory._get = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("không có mạng"))
r = factory.weekly_suggest(notify=False)
print(json.dumps({"n": len(r["items"]), "text": r["text"], "saved": len(factory.suggestions()["items"]), "max": max(i["score"] for i in r["items"])}))
"""


def test_goi_y_tuan_khong_mang(home):
    r = _run(home, SUGGEST)
    assert r["n"] == 5 and r["saved"] == 5 and r["max"] >= 60
    assert r["text"].startswith("🏭") and "HQ › Xưởng" in r["text"]
