"""Finance OS của superYou (phòng Tài chính, CFO ảo). Mô hình bốn vai, mỗi vai một việc, anh giữ quyền duyệt cuối:

- Analyst:   gom doanh thu Marketplace (sổ cái), thu chi của anh (agents/finance), chi phí vận hành cố định -> một bức tranh,
             đánh dấu bất thường (chi phí cố định tăng, hoàn tiền tăng, khách tập trung, thuê bao quên).
- Forecaster: dự báo tiền mặt, lãi/lỗ và runway 3–6 tháng; kịch bản what-if (mất khách lớn, tăng giá, thêm chi phí).
- Strategist: xếp hạng hành động nên làm (đòi nợ, cắt công cụ, tăng giá, đẩy sản phẩm bán chạy); anh duyệt thì thành việc trên bảng Phòng ban.
- CFO:       bản tin một trang mỗi sáng: tiền mặt, thay đổi, nghĩa vụ sắp đến, 3 việc nên làm.

Tham khảo mô hình "AI finance team" (Analyst/Forecaster/Strategist/CFO) và "AI Financial Operating System" của ReStructure AI.
Dữ liệu: DATA_DIR/cfo.json {costs: [chi phí cố định], cash: số dư khai báo, scenarios, briefs}.
"""
import datetime as dt
import json
import secrets
import threading

from config import DATA_DIR

FILE = DATA_DIR / "cfo.json"
_LOCK = threading.Lock()
PERIOD = {"monthly": "mỗi tháng", "yearly": "mỗi năm", "once": "một lần"}


def _now() -> dt.datetime:
    return dt.datetime.now()


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("costs", [])
    d.setdefault("cash", {"amount": 0, "at": ""})
    d.setdefault("briefs", [])
    d.setdefault("actions", {})
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def vnd(v) -> str:
    v = int(v or 0)
    a = abs(v)
    s = f"{a / 1e9:.2f} tỷ" if a >= 1e9 else f"{a / 1e6:.1f} tr" if a >= 1e6 else f"{a:,}đ".replace(",", ".")
    return ("-" if v < 0 else "") + s.replace(".0 tr", " tr")


# ------------------------------------------------------------------ chi phí cố định và tiền mặt
def add_cost(name: str, amount, period: str = "monthly", category: str = "ha_tang", note: str = "") -> dict:
    from agents.finance import parse_amount
    with _LOCK:
        d = _load()
        c = {"id": secrets.token_hex(3), "name": name.strip()[:80], "amount": parse_amount(amount), "period": period if period in PERIOD else "monthly",
             "category": category[:30], "note": note[:200], "added": _now().strftime("%Y-%m-%d"), "on": True}
        d["costs"].append(c)
        _save(d)
    return {"text": f"Đã thêm chi phí {c['name']} {vnd(c['amount'])} {PERIOD[c['period']]}."}


def remove_cost(cid: str) -> dict:
    with _LOCK:
        d = _load()
        d["costs"] = [c for c in d["costs"] if c["id"] != cid]
        _save(d)
    return {"text": "Đã xoá chi phí."}


def set_cash(amount) -> dict:
    from agents.finance import parse_amount
    with _LOCK:
        d = _load()
        d["cash"] = {"amount": parse_amount(amount), "at": _now().strftime("%Y-%m-%d")}
        _save(d)
    return {"text": f"Đã ghi tiền mặt hiện có: {vnd(d['cash']['amount'])}."}


def _monthly_costs(d: dict) -> int:
    return sum(c["amount"] if c["period"] == "monthly" else round(c["amount"] / 12) if c["period"] == "yearly" else 0 for c in d["costs"] if c.get("on", True))


# ------------------------------------------------------------------ Analyst
def analyst() -> dict:
    from agents import pay, finance, leads, market
    d = _load()
    led = pay._load()["ledger"]
    ym = _now().strftime("%Y-%m")
    pm = (_now().replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    rev = {"month": sum(e["amount"] for e in led if e["at"][:7] == ym), "prev": sum(e["amount"] for e in led if e["at"][:7] == pm),
           "fee_month": sum(e["fee"] for e in led if e["at"][:7] == ym), "total": sum(e["amount"] for e in led)}
    sales = [e for e in led if e["kind"] == "sale"]
    refunds = [e for e in led if e["kind"] == "refund"]
    # tập trung doanh thu theo sản phẩm
    by_prod = {}
    for e in sales:
        by_prod[e["name"]] = by_prod.get(e["name"], 0) + e["amount"]
    top = sorted(by_prod.items(), key=lambda x: -x[1])[:5]
    gross_sales = sum(e["amount"] for e in sales)
    conc = round(top[0][1] / gross_sales * 100) if top and gross_sales else 0
    personal = finance.month_report(ym)
    costs = _monthly_costs(d)
    flags = []
    if refunds and len(refunds) / max(1, len(sales)) > 0.1:
        flags.append(f"Tỷ lệ hoàn tiền {len(refunds)}/{len(sales)} lượt bán, trên 10%: xem lại mô tả sản phẩm hay chất lượng.")
    if conc >= 60 and len(sales) >= 5:
        flags.append(f"{conc}% doanh thu đến từ một sản phẩm ({top[0][0][:40]}): rủi ro tập trung, nên có sản phẩm thứ hai.")
    if costs and rev["month"] and costs > rev["month"] * 2:
        flags.append(f"Chi phí cố định {vnd(costs)}/tháng gấp hơn 2 lần doanh thu tháng này ({vnd(rev['month'])}).")
    if rev["prev"] and rev["month"] < rev["prev"] * 0.7 and _now().day > 20:
        flags.append(f"Doanh thu tháng này {vnd(rev['month'])} thấp hơn 30% so với tháng trước ({vnd(rev['prev'])}).")
    for c in d["costs"]:
        if c.get("on", True) and c["period"] == "monthly" and c["amount"] >= 500000 and "note" in c and "dùng" in (c.get("note") or "").lower() and "không" in (c.get("note") or "").lower():
            flags.append(f"Thuê bao {c['name']} ({vnd(c['amount'])}/tháng) có ghi chú chưa dùng: cân nhắc huỷ.")
    pend = sum(1 for o in pay._load()["orders"].values() if o["status"] == "pending")
    if pend >= 3:
        flags.append(f"{pend} đơn đang chờ thanh toán: kiểm tra đối soát hoặc nhắc khách.")
    ld = leads.overview()
    mk = market.catalog()
    return {"revenue": rev, "sales": len(sales), "refunds": len(refunds), "top_products": [{"name": n, "amount": a} for n, a in top],
            "concentration": conc, "fixed_costs": costs, "costs": d["costs"], "cash": d["cash"], "personal": {"income": personal["income"], "expense": personal["expense"], "net": personal["net"]},
            "leads": {"total": ld["total"], "new": ld["by_status"].get("moi", 0)}, "listings": len(mk["items"]), "pending_orders": pend, "flags": flags}


# ------------------------------------------------------------------ Forecaster
def forecast(months: int = 6, scenario: str = "") -> dict:
    """Dự báo đơn giản, minh bạch: doanh thu theo xu hướng 3 tháng gần nhất, chi phí cố định, kịch bản what-if."""
    from agents import pay
    d = _load()
    led = pay._load()["ledger"]
    months = max(3, min(int(months or 6), 12))
    hist = []
    t = _now().replace(day=1)
    for i in range(3):
        ym = t.strftime("%Y-%m")
        hist.append(sum(e["amount"] for e in led if e["at"][:7] == ym))
        t = (t - dt.timedelta(days=1)).replace(day=1)
    hist = list(reversed(hist))
    base = hist[-1] if hist[-1] else (sum(hist) / max(1, sum(1 for h in hist if h)) if any(hist) else 0)
    growth = 0.0
    if hist[-2] and hist[-1]:
        growth = max(-0.5, min(0.5, (hist[-1] - hist[-2]) / hist[-2]))
    costs = _monthly_costs(d)
    cash = d["cash"]["amount"]
    sc = (scenario or "").lower()
    adj_rev, adj_cost, label = 1.0, 0, "Cơ sở"
    if "mất" in sc or "lose" in sc:
        adj_rev, label = 0.6, "Mất khách lớn (doanh thu -40%)"
    elif "tăng giá" in sc or "price" in sc:
        adj_rev, label = 1.15, "Tăng giá 15%"
    elif "thuê" in sc or "hire" in sc:
        adj_cost, label = 15000000, "Thuê thêm 1 người (15 tr/tháng)"
    elif "quảng cáo" in sc or "ads" in sc:
        adj_rev, adj_cost, label = 1.3, 5000000, "Chạy quảng cáo 5 tr/tháng, doanh thu +30%"
    rows, r, c = [], base, cash
    for i in range(1, months + 1):
        r = r * (1 + growth * 0.5) * (adj_rev if i == 1 else 1)
        m = (_now().replace(day=1) + dt.timedelta(days=32 * i)).strftime("%Y-%m")
        net = r - costs - adj_cost
        c += net
        rows.append({"month": m, "revenue": round(r), "cost": costs + adj_cost, "net": round(net), "cash": round(c)})
    runway = None
    if costs + adj_cost > 0:
        burn = (costs + adj_cost) - base * adj_rev
        runway = round(cash / burn, 1) if burn > 0 else None
    return {"history": hist, "growth": round(growth * 100), "fixed_costs": costs, "cash_now": cash, "scenario": label, "rows": rows,
            "runway_months": runway, "note": "Dự báo tuyến tính từ 3 tháng gần nhất; chỉ để định hướng, không phải tư vấn tài chính."}


# ------------------------------------------------------------------ Strategist
STRAT = """Bạn là Giám đốc tài chính (CFO) của superYou, sản phẩm siêu trợ lý AI của Roimaxx (Việt Nam), đang thương mại hoá qua Marketplace.
Dữ liệu tài chính (JSON): {data}
Hãy xếp hạng 3–5 HÀNH ĐỘNG cụ thể nên làm trong 2 tuần tới để tăng tiền mặt, tăng doanh thu hoặc cắt chi phí không cần thiết.
Mỗi hành động: tiêu đề ngắn, vì sao (dựa vào số liệu), tác động ước tính (đồng/tháng hoặc %), phòng phụ trách (finance|sales|gtm|product|so).
Không bịa số liệu không có trong dữ liệu; nếu thiếu dữ liệu thì hành động đầu tiên là "bổ sung dữ liệu X".
Trả về JSON: {{"actions": [{{"title": "...", "why": "...", "impact": "...", "dept": "..."}}], "headline": "1 câu tình hình tài chính"}}"""


def strategist(auto_propose: bool = False) -> dict:
    import llm
    a = analyst()
    f = forecast(6)
    slim = {"revenue": a["revenue"], "sales": a["sales"], "refunds": a["refunds"], "top_products": a["top_products"], "concentration_pct": a["concentration"],
            "fixed_costs_month": a["fixed_costs"], "costs": [{"name": c["name"], "amount": c["amount"], "period": c["period"]} for c in a["costs"]],
            "cash": a["cash"], "leads_total": a["leads"]["total"], "leads_new": a["leads"]["new"], "listings": a["listings"], "pending_orders": a["pending_orders"],
            "flags": a["flags"], "forecast_6m": [{"month": r["month"], "net": r["net"], "cash": r["cash"]} for r in f["rows"]], "runway_months": f["runway_months"]}
    res = llm.ask_json(STRAT.format(data=json.dumps(slim, ensure_ascii=False)), max_tokens=2500, tag="cfo_strat",
                       ok=lambda r: isinstance(r, dict) and isinstance(r.get("actions"), list))
    if not res:
        res = {"headline": "Chưa đủ dữ liệu để AI đề xuất; dưới đây là việc rút từ cảnh báo.", "actions": [{"title": fl[:80], "why": fl, "impact": "", "dept": "finance"} for fl in a["flags"][:3]]
               or [{"title": "Ghi tiền mặt hiện có và chi phí cố định", "why": "CFO cần số dư và chi phí để dự báo runway.", "impact": "Có dự báo 6 tháng", "dept": "finance"}]}
    acts = []
    for x in res["actions"][:5]:
        acts.append({"id": secrets.token_hex(3), "title": str(x.get("title", ""))[:120], "why": str(x.get("why", ""))[:500], "impact": str(x.get("impact", ""))[:160],
                     "dept": x.get("dept") if x.get("dept") in ("finance", "sales", "gtm", "product", "so") else "finance", "at": _now().strftime("%Y-%m-%dT%H:%M")})
    with _LOCK:
        d = _load()
        d["actions"] = {"headline": str(res.get("headline", ""))[:300], "items": acts, "at": _now().strftime("%Y-%m-%dT%H:%M")}
        _save(d)
    if auto_propose:
        from agents import board
        for x in acts[:3]:
            board.propose("finance", x["title"], x["why"], why=x["why"], impact=x["impact"], priority="vua", by="CFO (AI)", auto_assign_to=x["dept"], key="cfo:" + x["title"][:40])
    return {"text": d["actions"]["headline"] + "\n" + "\n".join(f"{i + 1}. {x['title']} ({x['impact']})" for i, x in enumerate(acts)), "headline": d["actions"]["headline"], "actions": acts}


def to_board(action_id: str) -> dict:
    """Anh bấm 'Đưa lên bảng' một hành động -> thành đề xuất chờ duyệt (hoặc duyệt luôn)."""
    from agents import board
    d = _load()
    x = next((a for a in d["actions"].get("items", []) if a["id"] == action_id), None)
    if not x:
        raise ValueError("Không tìm thấy hành động")
    return board.propose("finance", x["title"], x["why"], why=x["why"], impact=x["impact"], priority="cao", by="CFO (AI)", auto_assign_to=x["dept"], key="cfo:" + x["title"][:40])


# ------------------------------------------------------------------ CFO brief
def brief(save: bool = True) -> dict:
    """Bản tin một trang: tiền mặt, thay đổi, nghĩa vụ sắp đến, 3 việc nên làm."""
    from agents import pay, finance, board
    a = analyst()
    f = forecast(3)
    d = _load()
    pending = [o for o in pay._load()["orders"].values() if o["status"] == "pending"]
    owed = pay.admin_overview()["kpi"]["owed"]
    debts = finance.overview()["report"]
    lines = [f"💼 CFO superYou · {_now():%d/%m}",
             f"Tiền mặt khai báo: {vnd(a['cash']['amount']) if a['cash']['amount'] else 'chưa ghi'}" + (f" (runway ~{f['runway_months']} tháng)" if f["runway_months"] else ""),
             f"Doanh thu tháng: {vnd(a['revenue']['month'])} (tháng trước {vnd(a['revenue']['prev'])}) · về sàn {vnd(a['revenue']['fee_month'])} · {a['sales']} lượt bán, {a['refunds']} hoàn",
             f"Chi phí cố định: {vnd(a['fixed_costs'])}/tháng · nợ người bán {vnd(owed)}" + (f" · {len(pending)} đơn chờ tiền" if pending else ""),
             f"Khách đăng ký: {a['leads']['total']} (mới {a['leads']['new']}) · {a['listings']} sản phẩm trên kệ"]
    if debts["payable"] or debts["receivable"]:
        lines.append(f"Thu chi cá nhân tháng này: thu {vnd(debts['income'])}, chi {vnd(debts['expense'])}; phải thu {vnd(debts['receivable'])}, phải trả {vnd(debts['payable'])}")
    if a["flags"]:
        lines.append("⚠️ " + " | ".join(a["flags"][:3]))
    acts = d.get("actions", {}).get("items", [])[:3]
    if acts:
        lines.append("Nên làm: " + " · ".join(f"{i + 1}) {x['title']}" for i, x in enumerate(acts)))
    bb = board.brief()
    if bb:
        lines.append(bb)
    text = "\n".join(lines)
    if save:
        with _LOCK:
            d = _load()
            d["briefs"].append({"at": _now().strftime("%Y-%m-%dT%H:%M"), "text": text})
            d["briefs"] = d["briefs"][-60:]
            _save(d)
    return {"text": text}


def overview() -> dict:
    d = _load()
    return {"analyst": analyst(), "forecast": forecast(6), "actions": d.get("actions", {}), "briefs": d["briefs"][-7:][::-1], "periods": PERIOD}
