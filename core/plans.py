"""Ma trận gói và quyền của superYou (nguồn sự thật duy nhất cho landing, trung tâm tài khoản, Marketplace, HQ).

Chính sách khởi điểm (phòng Product đề xuất, chờ phòng GTM chốt giá và điều khoản; chủ sàn sửa trong HQ › Chính sách):
- free       : trải nghiệm Marketplace, mua sản phẩm, 1 workflow riêng, tải sản phẩm đã mua.
- trial      : 14 ngày dùng đủ tính năng Pro trên superYou riêng (khi có máy chủ), không cần thẻ.
- pro        : 199.000đ/tháng: superYou riêng, họp không giới hạn, Studio bản tin, Second Brain, khoá học, 20 workflow, tín dụng Marketplace 100k/tháng.
- business   : từ 15 triệu/khách (cài máy chủ riêng, Lark, đào tạo), 5 người dùng, SLA, AI tại chỗ (tuỳ chọn).
- enterprise : theo hợp đồng: nhiều máy chủ, SSO, hỗ trợ riêng.
"""
import json
import threading

from config import DATA_DIR

FILE = DATA_DIR / "plans.json"
_LOCK = threading.Lock()
TRIAL_DAYS = 14
DEFAULT = {
    "free": {"name": "Miễn phí", "price": 0, "period": "", "tagline": "Bắt đầu với Marketplace", "color": "#5E5670", "order": 1,
             "limits": {"workflows": 1, "meetings_month": 3, "seats": 1, "market_credit": 0},
             "features": ["Mua và tải sản phẩm Marketplace", "1 workflow riêng", "Trung tâm tài khoản, hồ sơ, bảo mật", "Đăng ký bán trên Marketplace"]},
    "trial": {"name": "Dùng thử Pro", "price": 0, "period": "14 ngày", "tagline": "Đủ tính năng Pro, không cần thẻ", "color": "#C98205", "order": 2,
              "limits": {"workflows": 20, "meetings_month": 30, "seats": 1, "market_credit": 0},
              "features": ["Mọi tính năng Pro trong 14 ngày", "superYou riêng trên Telegram và web", "Hết hạn tự về Miễn phí, không mất dữ liệu"]},
    "pro": {"name": "Pro", "price": 199000, "period": "/tháng", "tagline": "Một người làm việc như một đội", "color": "#6A3DF0", "order": 3,
            "limits": {"workflows": 20, "meetings_month": 0, "seats": 1, "market_credit": 100000},
            "features": ["superYou riêng: họp không giới hạn, email và Lark, lịch", "Studio bản tin, Second Brain, khoá học 30 ngày", "20 workflow riêng, chạy theo lịch",
                         "Tín dụng Marketplace 100.000đ/tháng", "Đăng nhập Face ID / vân tay"]},
    "business": {"name": "Doanh nghiệp", "price": 15000000, "period": "/khách, từ", "tagline": "Máy chủ riêng, cài trong 7 ngày", "color": "#0E7C6B", "order": 4,
                 "limits": {"workflows": 100, "meetings_month": 0, "seats": 5, "market_credit": 500000},
                 "features": ["Máy chủ riêng, dữ liệu tách biệt", "Kết nối Lark, đào tạo đội ngũ", "5 người dùng, quản trị tập trung", "AI tại chỗ (Ollama) tuỳ chọn", "Hỗ trợ ưu tiên, SLA"]},
    "enterprise": {"name": "Enterprise", "price": 0, "period": "theo hợp đồng", "tagline": "Nhiều máy chủ, SSO, hỗ trợ riêng", "color": "#15171A", "order": 5,
                   "limits": {"workflows": 0, "meetings_month": 0, "seats": 0, "market_credit": 0},
                   "features": ["Không giới hạn", "SSO, nhật ký kiểm toán", "Đội hỗ trợ riêng"]},
}


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    out = json.loads(json.dumps(DEFAULT))
    for k, v in (d.get("plans") or {}).items():
        if k in out:
            out[k].update(v)
    return out


PLANS = _load()


def all_plans() -> dict:
    global PLANS
    PLANS = _load()
    return {"plans": PLANS, "trial_days": TRIAL_DAYS, "order": sorted(PLANS, key=lambda k: PLANS[k]["order"])}


def update(plan: str, price=None, tagline: str = "", features: str = "", limits: str = "") -> dict:
    """Chủ sàn sửa chính sách gói trong HQ (giá, mô tả, tính năng, giới hạn)."""
    global PLANS
    if plan not in DEFAULT:
        raise ValueError("Gói không hợp lệ")
    with _LOCK:
        try:
            d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
        except Exception:
            d = {}
        p = d.setdefault("plans", {}).setdefault(plan, {})
        if price is not None and price != "":
            p["price"] = max(0, int(float(price)))
        if tagline:
            p["tagline"] = tagline[:120]
        if features:
            p["features"] = [f.strip()[:120] for f in features.split("\n") if f.strip()][:10]
        if limits:
            try:
                lm = json.loads(limits)
                p["limits"] = {k: int(v) for k, v in lm.items() if k in DEFAULT[plan]["limits"]}
            except Exception:
                raise ValueError("Giới hạn phải là JSON, ví dụ {\"workflows\": 20}")
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(FILE)
    PLANS = _load()
    return {"text": f"Đã cập nhật gói {PLANS[plan]['name']}."}


def limit(plan: str, key: str) -> int:
    """0 = không giới hạn."""
    return int((PLANS.get(plan) or PLANS["free"])["limits"].get(key, 0))


def can(plan: str, feature: str) -> bool:
    """Quyền theo gói cho các tính năng chính (dùng kèm core/flags theo phạm vi)."""
    order = {k: v["order"] for k, v in PLANS.items()}
    need = {"own_assistant": 2, "studio": 2, "second_brain": 2, "courses": 2, "scheduled_workflows": 2, "team": 4, "private_llm": 4, "sso": 5}
    return order.get(plan, 1) >= need.get(feature, 1)
