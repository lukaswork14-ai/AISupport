"""Nén gzip có điều kiện + ETag/304 + cache file có phiên bản (Nền tảng & DevOps)."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CODE = r'''
import gzip, http.client, json, socket
from webapp import server
s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
server.serve(port)
def get(path, **h):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
    c.request("GET", path, headers=h); r = c.getresponse(); b = r.read(); c.close()
    return r.status, {k.lower(): v for k, v in r.getheaders()}, b
out = {}
for p in ("/", "/landing", "/brand/tokens.css", "/icons/huy-192.png"):
    st, h, raw = get(p)
    st2, h2, z = get(p, **{"Accept-Encoding": "gzip, deflate, br"})
    body = gzip.decompress(z) if h2.get("content-encoding") == "gzip" else z
    st3, h3, b3 = get(p, **{"If-None-Match": h.get("etag", "x")})
    st4, h4, z4 = get(p, **{"Accept-Encoding": "gzip;q=0"})
    out[p] = {"st": st, "raw": len(raw), "enc_raw": h.get("content-encoding"), "enc": h2.get("content-encoding"),
              "gz": len(z), "same": body == raw, "vary": h2.get("vary"), "etag": h.get("etag"), "inm": st3, "inm_len": len(b3),
              "q0": h4.get("content-encoding")}
st, h, b = get("/brand/tokens.css?v=3"); out["ver_cc"] = h.get("cache-control")
st, h, b = get("/landing", Range="bytes=0-9", **{"Accept-Encoding": "gzip"}); out["range"] = [st, len(b), h.get("content-encoding")]
print("RESULT " + json.dumps(out))
'''


def _run(tmp_path, tenant=False):
    home = tmp_path / ("superyou-tenants/khach" if tenant else "owner")
    home.mkdir(parents=True)
    (home / ".env").write_text("TELEGRAM_TOKEN=1:x\nOWNER_CHAT_ID=1\nLLM_API_KEY=x\n")
    env = {k: v for k, v in os.environ.items() if k != "SUPERYOU_TENANT"}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT)})
    r = subprocess.run([sys.executable, "-c", CODE], cwd=ROOT, env=env, capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stderr[-2000:]
    import json
    return json.loads([l for l in r.stdout.splitlines() if l.startswith("RESULT ")][-1][7:])


def _check(out):
    app = out["/"]
    assert app["st"] == 200 and app["enc_raw"] is None           # không xin nén thì gửi thô
    assert app["enc"] == "gzip" and app["same"] and app["vary"] == "Accept-Encoding"
    assert app["gz"] < app["raw"] * 0.4                            # trang app ~500 KB phải nhỏ đi nhiều
    assert app["etag"] and app["inm"] == 304 and app["inm_len"] == 0
    assert app["q0"] is None                                       # gzip;q=0 = từ chối nén
    assert out["/landing"]["enc"] == "gzip" and out["/landing"]["same"]
    png = out["/icons/huy-192.png"]
    assert png["st"] == 200 and png["enc"] is None and png["same"]  # ảnh đã nén sẵn, không gzip lại
    assert out["ver_cc"] == "public, max-age=31536000, immutable"
    assert out["range"] == [206, 10, None]                         # tua video/Range vẫn như cũ, không nén


def test_owner_app_compressed_and_cached(tmp_path):
    _check(_run(tmp_path))


def test_tenant_app_compressed_and_cached(tmp_path):
    _check(_run(tmp_path, tenant=True))
