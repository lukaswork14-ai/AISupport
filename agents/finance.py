"""Tài chính cá nhân của superHuy: thu, chi, phải thu, phải trả, ngân sách theo danh mục,
báo cáo tháng (so với tháng trước, so với ngân sách) + phân tích và gợi ý tối ưu như trợ lý tài chính cá nhân.
Dữ liệu lưu cục bộ trên máy: data/finance.json (quyền 600). Đơn vị: VND.
Lưu ý: gợi ý chỉ mang tính quản lý chi tiêu/ngân sách, không phải tư vấn đầu tư."""
import datetime as dt
import json
import os
import re
import threading
import uuid

from config import DATA_DIR, LLM_MODEL
from core import profile
from llm import ANTI_REPEAT, LLM_EXTRA, PRECISE, degenerate, fix_vi, make_client

FILE = DATA_DIR / "finance.json"
_lock = threading.Lock()

EXPENSE_CATS = {
    "food": ("Ăn uống", "🍜"), "transport": ("Di chuyển", "🚗"), "housing": ("Nhà ở", "🏠"),
    "bills": ("Hoá đơn & tiện ích", "💡"), "shopping": ("Mua sắm", "🛍"), "health": ("Sức khoẻ", "💪"),
    "learning": ("Học tập & phát triển", "📚"), "fun": ("Giải trí & du lịch", "🎉"), "relations": ("Quan hệ & quà tặng", "🎁"),
    "family": ("Gia đình", "👨‍👩‍👧"), "work": ("Công việc & kinh doanh", "💼"), "invest": ("Tiết kiệm & đầu tư", "📈"),
    "other": ("Khác", "•"),
}
INCOME_CATS = {
    "salary": ("Lương & thù lao", "💵"), "business": ("Kinh doanh", "🏢"), "invest": ("Đầu tư", "📈"),
    "bonus": ("Thưởng", "🎯"), "other_in": ("Thu khác", "➕"),
}
ACCOUNTS = {"cash": "Tiền mặt", "bank": "Ngân hàng", "card": "Thẻ tín dụng", "ewallet": "Ví điện tử"}


def _tz():
    from agents.calendar_agent import TZ
    return TZ


def _today() -> dt.date:
    return dt.datetime.now(_tz()).date()


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    d.setdefault("tx", [])
    d.setdefault("debts", [])
    d.setdefault("budgets", {})
    return d


def _save(d: dict):
    FILE.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(FILE, 0o600)
    except Exception:
        pass


# ------------------------------------------------------------------ số tiền tiếng Việt
def parse_amount(s) -> int:
    """'45k' -> 45000; '1tr2' -> 1200000; '2,5 triệu' -> 2500000; '80tr' -> 80000000; '1.250.000' -> 1250000."""
    if isinstance(s, (int, float)):
        return int(s)
    t = str(s).lower().replace(" ", "").replace("đ", "").replace("vnd", "").replace("vnđ", "")
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(tr|triệu|trieu|m)(\d{1,3})?", t)
    if m:
        base = float(m.group(1).replace(",", "."))
        extra = m.group(3)
        v = base * 1_000_000 + (int(extra.ljust(3, "0")) * 1000 if extra else 0)
        return int(round(v))
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(k|nghìn|nghin|ngàn|ngan)", t)
    if m:
        return int(round(float(m.group(1).replace(",", ".")) * 1000))
    m = re.fullmatch(r"(\d+(?:[.,]\d+)?)(tỷ|ty|tỉ|b)", t)
    if m:
        return int(round(float(m.group(1).replace(",", ".")) * 1_000_000_000))
    digits = re.sub(r"[.,](?=\d{3}(\D|$))", "", t)
    try:
        return int(float(digits.replace(",", ".")))
    except ValueError:
        raise ValueError(f"Không hiểu số tiền “{s}”")


def fmt(v: int) -> str:
    v = int(v or 0)
    a = abs(v)
    trim = lambda x: (x.rstrip("0").rstrip(".") if "." in x else x).replace(".", ",")
    if a >= 1_000_000_000:
        s = trim(f"{a / 1e9:.2f}") + " tỷ"
    elif a >= 1_000_000:
        s = trim(f"{a / 1e6:.2f}" if a < 10_000_000 else f"{a / 1e6:.1f}") + " tr"
    elif a >= 1000:
        s = trim(f"{a / 1000:.1f}" if a < 100_000 else f"{a / 1000:.0f}") + "k"
    else:
        s = f"{a}đ"
    return ("-" if v < 0 else "") + s


# ------------------------------------------------------------------ ghi nhận
def add_tx(kind: str, amount, category: str = "", note: str = "", date: str = "", account: str = "bank") -> dict:
    kind = "income" if kind == "income" else "expense"
    amt = parse_amount(amount)
    if amt <= 0:
        raise ValueError("Số tiền phải lớn hơn 0")
    cats = INCOME_CATS if kind == "income" else EXPENSE_CATS
    category = category if category in cats else ("other_in" if kind == "income" else "other")
    day = date[:10] if date else _today().isoformat()
    dt.date.fromisoformat(day)
    tx = {"id": uuid.uuid4().hex[:10], "kind": kind, "amount": amt, "category": category, "note": (note or "").strip()[:200],
          "date": day, "account": account if account in ACCOUNTS else "bank", "created": dt.datetime.now(_tz()).isoformat()}
    with _lock:
        d = _load()
        d["tx"].append(tx)
        _save(d)
    alert = _budget_alert(category) if kind == "expense" else ""
    sign = "+" if kind == "income" else "−"
    return {"tx": tx, "alert": alert,
            "text": f"Đã ghi {sign}{fmt(amt)} · {cats[category][0]}" + (f" · {tx['note']}" if tx["note"] else "") + (f"\n{alert}" if alert else "")}


def delete_tx(tx_id: str) -> dict:
    with _lock:
        d = _load()
        d["tx"] = [t for t in d["tx"] if t["id"] != tx_id]
        _save(d)
    return {"text": "Đã xoá giao dịch"}


def add_debt(kind: str, party: str, amount, due: str = "", note: str = "") -> dict:
    """kind: receivable (người khác nợ mình) | payable (mình phải trả)."""
    kind = "receivable" if kind == "receivable" else "payable"
    amt = parse_amount(amount)
    if not party.strip():
        raise ValueError("Cần tên người/đơn vị")
    debt = {"id": uuid.uuid4().hex[:10], "kind": kind, "party": party.strip()[:80], "amount": amt, "paid": 0,
            "due": due[:10] if due else "", "note": (note or "").strip()[:200], "status": "open",
            "created": dt.datetime.now(_tz()).isoformat()}
    with _lock:
        d = _load()
        d["debts"].append(debt)
        _save(d)
    label = "Phải thu từ" if kind == "receivable" else "Phải trả cho"
    return {"debt": debt, "text": f"Đã ghi {label} {debt['party']}: {fmt(amt)}" + (f", hạn {debt['due'][8:10]}/{debt['due'][5:7]}" if debt["due"] else "")}


def settle_debt(debt_id: str, amount=None, record: bool = True) -> dict:
    """Thu/trả (một phần hoặc toàn bộ). Tự ghi thành giao dịch thu/chi tương ứng."""
    with _lock:
        d = _load()
        debt = next((x for x in d["debts"] if x["id"] == debt_id), None)
        if not debt:
            raise ValueError("Không tìm thấy khoản này")
        left = debt["amount"] - debt.get("paid", 0)
        pay = min(parse_amount(amount), left) if amount not in (None, "", 0) else left
        debt["paid"] = debt.get("paid", 0) + pay
        if debt["paid"] >= debt["amount"]:
            debt["status"] = "done"
        _save(d)
    if record and pay > 0:
        if debt["kind"] == "receivable":
            add_tx("income", pay, "other_in", f"Thu nợ: {debt['party']}")
        else:
            add_tx("expense", pay, "other", f"Trả nợ: {debt['party']}")
    return {"text": f"Đã ghi nhận {fmt(pay)}" + (" · đã tất toán ✓" if debt["status"] == "done" else f" · còn {fmt(debt['amount'] - debt['paid'])}")}


def set_budget(category: str, amount) -> dict:
    if category not in EXPENSE_CATS:
        raise ValueError("Danh mục không hợp lệ")
    amt = parse_amount(amount) if amount not in (None, "") else 0
    with _lock:
        d = _load()
        if amt > 0:
            d["budgets"][category] = amt
        else:
            d["budgets"].pop(category, None)
        _save(d)
    return {"text": f"Ngân sách {EXPENSE_CATS[category][0]}: {fmt(amt)}/tháng" if amt else "Đã bỏ ngân sách"}


def _month_tx(d: dict, ym: str) -> list[dict]:
    return [t for t in d["tx"] if t["date"].startswith(ym)]


def _budget_alert(category: str) -> str:
    d = _load()
    b = d["budgets"].get(category)
    if not b:
        return ""
    ym = _today().strftime("%Y-%m")
    spent = sum(t["amount"] for t in _month_tx(d, ym) if t["kind"] == "expense" and t["category"] == category)
    pct = spent / b
    name = EXPENSE_CATS[category][0]
    if pct >= 1:
        return f"⚠️ {name} đã vượt ngân sách tháng ({fmt(spent)} / {fmt(b)})."
    if pct >= 0.8:
        return f"🟠 {name} đã dùng {pct:.0%} ngân sách tháng ({fmt(spent)} / {fmt(b)})."
    return ""


# ------------------------------------------------------------------ báo cáo
def _prev_ym(ym: str) -> str:
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def month_report(ym: str = "") -> dict:
    ym = ym or _today().strftime("%Y-%m")
    d = _load()
    cur, prev = _month_tx(d, ym), _month_tx(d, _prev_ym(ym))
    inc = sum(t["amount"] for t in cur if t["kind"] == "income")
    exp = sum(t["amount"] for t in cur if t["kind"] == "expense")
    pexp = sum(t["amount"] for t in prev if t["kind"] == "expense")
    pinc = sum(t["amount"] for t in prev if t["kind"] == "income")
    by_cat = {}
    for t in cur:
        if t["kind"] == "expense":
            by_cat[t["category"]] = by_cat.get(t["category"], 0) + t["amount"]
    prev_cat = {}
    for t in prev:
        if t["kind"] == "expense":
            prev_cat[t["category"]] = prev_cat.get(t["category"], 0) + t["amount"]
    inc_cat = {}
    for t in cur:
        if t["kind"] == "income":
            inc_cat[t["category"]] = inc_cat.get(t["category"], 0) + t["amount"]
    y, m = int(ym[:4]), int(ym[5:7])
    ndays = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
    is_cur = ym == _today().strftime("%Y-%m")
    elapsed = _today().day if is_cur else ndays
    daily = [0] * ndays
    for t in cur:
        if t["kind"] == "expense":
            daily[int(t["date"][8:10]) - 1] += t["amount"]
    cats = [{"id": k, "name": EXPENSE_CATS[k][0], "icon": EXPENSE_CATS[k][1], "spent": v, "prev": prev_cat.get(k, 0),
             "budget": d["budgets"].get(k, 0)} for k, v in sorted(by_cat.items(), key=lambda x: -x[1])]
    for k, b in d["budgets"].items():
        if k not in by_cat and k in EXPENSE_CATS:
            cats.append({"id": k, "name": EXPENSE_CATS[k][0], "icon": EXPENSE_CATS[k][1], "spent": 0, "prev": prev_cat.get(k, 0), "budget": b})
    debts = [x for x in d["debts"] if x["status"] == "open"]
    today = _today().isoformat()
    return {
        "month": ym, "income": inc, "expense": exp, "net": inc - exp, "prev_income": pinc, "prev_expense": pexp,
        "savings_rate": round((inc - exp) / inc, 3) if inc else None,
        "forecast_expense": int(exp / max(elapsed, 1) * ndays) if is_cur and elapsed < ndays else exp,
        "days": ndays, "elapsed": elapsed, "daily": daily, "categories": cats,
        "income_cats": [{"id": k, "name": INCOME_CATS[k][0], "amount": v} for k, v in sorted(inc_cat.items(), key=lambda x: -x[1])],
        "budget_total": sum(d["budgets"].values()),
        "budget_spent": sum(v for k, v in by_cat.items() if k in d["budgets"]),  # chỉ các danh mục đã đặt ngân sách
        "receivable": sum(x["amount"] - x.get("paid", 0) for x in debts if x["kind"] == "receivable"),
        "payable": sum(x["amount"] - x.get("paid", 0) for x in debts if x["kind"] == "payable"),
        "overdue_debts": sum(1 for x in debts if x["due"] and x["due"] < today),
        "top": sorted([t for t in cur if t["kind"] == "expense"], key=lambda t: -t["amount"])[:5],
    }


def months_trend(n: int = 6) -> list[dict]:
    d = _load()
    ym = _today().strftime("%Y-%m")
    out = []
    for _ in range(n):
        tx = _month_tx(d, ym)
        out.append({"month": ym, "income": sum(t["amount"] for t in tx if t["kind"] == "income"),
                    "expense": sum(t["amount"] for t in tx if t["kind"] == "expense")})
        ym = _prev_ym(ym)
    return list(reversed(out))


def overview(ym: str = "") -> dict:
    d = _load()
    ym = ym or _today().strftime("%Y-%m")
    tx = sorted(_month_tx(d, ym), key=lambda t: (t["date"], t["created"]), reverse=True)
    return {"report": month_report(ym), "trend": months_trend(6), "tx": tx[:200],
            "debts": sorted(d["debts"], key=lambda x: (x["status"] != "open", x["due"] or "9999")),
            "budgets": d["budgets"], "analysis": d.get("analysis", {}).get(ym),
            "cats": {"expense": {k: {"name": v[0], "icon": v[1]} for k, v in EXPENSE_CATS.items()},
                     "income": {k: {"name": v[0], "icon": v[1]} for k, v in INCOME_CATS.items()}},
            "accounts": ACCOUNTS}


# ------------------------------------------------------------------ AI
PARSE = """Chuyển câu ghi chép tài chính tiếng Việt thành JSON. Hôm nay {today}.
Trả về DUY NHẤT JSON: {{"type": "expense"|"income"|"receivable"|"payable", "amount": số nguyên VND,
"category": mã danh mục, "note": mô tả ngắn, "date": "YYYY-MM-DD", "party": tên người/đơn vị nếu là nợ, "due": "YYYY-MM-DD" hoặc ""}}.
Danh mục chi: {exp}. Danh mục thu: {inc}.
"45k" = 45000, "1tr2" = 1200000, "80tr" = 80000000. "hôm qua" = ngày trước hôm nay.
receivable = người khác nợ/sẽ trả cho tôi; payable = tôi nợ/phải trả người khác.
Câu: {text}"""


def parse(text: str) -> dict:
    exp = ", ".join(f"{k} ({v[0]})" for k, v in EXPENSE_CATS.items())
    inc = ", ".join(f"{k} ({v[0]})" for k, v in INCOME_CATS.items())
    prompt = PARSE.format(today=_today().isoformat(), exp=exp, inc=inc, text=text)
    for _ in range(2):
        r = make_client().chat.completions.create(model=LLM_MODEL, extra_body=LLM_EXTRA, max_tokens=800, **PRECISE,
                                                  messages=[{"role": "user", "content": prompt}])
        m = re.search(r"\{.*\}", fix_vi(r.choices[0].message.content), re.S)
        try:
            d = json.loads(m.group(0))
            d["amount"] = parse_amount(d.get("amount", 0))
            if d.get("type") not in ("expense", "income", "receivable", "payable"):
                d["type"] = "expense"
            return d
        except Exception:
            continue
    raise RuntimeError("AI chưa hiểu, thử ghi rõ hơn, ví dụ: “cafe 45k”, “nhận lương 80tr”, “Linh nợ 5tr trả cuối tháng”.")


def quick(text: str) -> dict:
    """Ghi nhanh bằng 1 câu (dùng cho chat và ô nhập nhanh)."""
    d = parse(text)
    if d["type"] in ("receivable", "payable"):
        return add_debt(d["type"], d.get("party") or d.get("note") or "Không rõ", d["amount"], d.get("due") or "", d.get("note") or "")
    return add_tx(d["type"], d["amount"], d.get("category", ""), d.get("note", ""), d.get("date") or "")


ANALYZE = """Bạn là trợ lý tài chính cá nhân của anh Huy. {profile}
Phân tích báo cáo tháng {month} dưới đây và viết bằng tiếng Việt, văn bản thuần (không markdown, không bảng):
1) Tổng quan 2-3 câu: thu, chi, dòng tiền ròng, tỷ lệ tiết kiệm, so với tháng trước.
2) 3 điểm đáng chú ý (danh mục tăng mạnh, vượt ngân sách, khoản chi lớn bất thường, phải thu/phải trả quá hạn).
3) 3-5 đề xuất tối ưu CỤ THỂ, có con số (ví dụ đặt ngân sách X cho danh mục Y, cắt giảm Z/tháng, thu hồi khoản nợ nào trước),
   ưu tiên quản lý chi tiêu, quỹ dự phòng, tỷ lệ tiết kiệm. Không khuyến nghị mua bán cổ phiếu/tiền số cụ thể.
Ngắn gọn, mỗi ý 1 dòng, bắt đầu bằng "•". Đơn vị: dùng "tr" (triệu) và "k" (nghìn).
DỮ LIỆU: {data}"""


def analyze(ym: str = "") -> dict:
    rep = month_report(ym)
    if not rep["income"] and not rep["expense"]:
        return {"text": "Tháng này chưa có giao dịch nào để phân tích. Hãy ghi vài khoản thu chi trước nhé."}
    slim = {k: rep[k] for k in ("month", "income", "expense", "net", "prev_income", "prev_expense", "savings_rate",
                                "forecast_expense", "receivable", "payable", "overdue_debts", "budget_total")}
    slim["categories"] = [{k: c[k] for k in ("name", "spent", "prev", "budget")} for c in rep["categories"]]
    slim["top"] = [{"amount": t["amount"], "note": t["note"], "category": EXPENSE_CATS.get(t["category"], ("Khác",))[0]} for t in rep["top"]]
    prompt = ANALYZE.format(profile=profile.brief(), month=rep["month"], data=json.dumps(slim, ensure_ascii=False))
    text = ""
    for _ in range(2):
        r = make_client().chat.completions.create(model=LLM_MODEL, extra_body=LLM_EXTRA, max_tokens=3000, **ANTI_REPEAT,
                                                  messages=[{"role": "user", "content": prompt}])
        text = fix_vi(r.choices[0].message.content).strip()
        if not degenerate(text):
            break
    text += "\n\nLưu ý: đây là gợi ý quản lý chi tiêu, không phải tư vấn đầu tư."
    with _lock:
        d = _load()
        d.setdefault("analysis", {})[rep["month"]] = {"text": text, "at": dt.datetime.now(_tz()).isoformat()}
        _save(d)
    return {"text": text}


def digest_line() -> str:
    try:
        r = month_report()
        if not r["expense"] and not r["income"]:
            return ""
        return f"💰 Tháng này: chi {fmt(r['expense'])}, thu {fmt(r['income'])}" + \
            (f"; các danh mục có ngân sách đã dùng {r['budget_spent'] / r['budget_total']:.0%}." if r["budget_total"] else ".")
    except Exception:
        return ""
