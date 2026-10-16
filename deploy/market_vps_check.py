"""Chẩn đoán trên VPS (không in bí mật): Marketplace công khai, console người tạo, Xưởng clone quét dữ liệu thật."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def get(u):
    try:
        with urllib.request.urlopen(u, timeout=10) as r:
            return r.status, r.read()
    except Exception as e:
        return 0, str(e).encode()


base = "https://app.roimaxxhub.com"
for path in ("/market", "/market/console", "/landing"):
    st, b = get(base + path)
    print(f"page {path}: {st} {len(b)}")
st, b = get(base + "/api/market/public")
try:
    d = json.loads(b)
    print("market_public:", st, len(d["items"]), [i["name"][:28] for i in d["items"]][:6])
except Exception as e:
    print("market_public lỗi:", st, str(e)[:120])
from agents import pay  # noqa: E402
cfg = pay.config()
print("pay_setup:", {k: cfg[k] for k in ("vietqr_ready", "webhook_ready", "payos_ready", "mail_ready", "fee_pct")})
st, b = get(base + "/api/pay/status?o=khong")
print("pay_status_route:", st)
from agents import factory as f  # noqa: E402
for src, kw in (("ios", {"country": "vn", "chart": "free", "genre": "6007"}), ("mac", {"country": "us", "chart": "free"}), ("github", {}), ("ph", {})):
    try:
        r = f.scan(src, limit=10, **kw)
        print(f"scan {src}:", r["text"], [i["name"][:22] for i in r["items"][:4]])
        if src == "ios" and r["items"]:
            x = f.detail(r["items"][0]["key"])
            print("  detail:", x["name"], len(x["shots"]), "ảnh,", len(x["reviews"]), "đánh giá,", len(x["dev_apps"]), "app cùng nhà phát triển")
    except Exception as e:
        print(f"scan {src} lỗi:", str(e)[:160])
