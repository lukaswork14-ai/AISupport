"""Phòng Bán hàng superYou (CSO ảo). Ba vai, anh giữ quyền duyệt cuối, không bao giờ tự gửi thư:

- Nghiên cứu (research): chấm điểm ICP cho một khách tiềm năng từ những gì đã biết (tên miền email, nguồn, sở thích,
             tài khoản, gói, đơn đã mua, số ngày từ khi đăng ký) -> phân khúc + điểm 0–100 + bước tiếp theo.
- Theo đuổi (draft/approve/reject): soạn thư tiếng Việt theo phân khúc (chào mừng, nhắc dùng thử, sắp hết hạn, nâng cấp,
             hỏi thăm) -> nháp chờ duyệt -> anh duyệt thì gửi qua Lark Mail/Gmail và cập nhật trạng thái khách.
- RevOps (pipeline/weekly_report): phễu từ khách đăng ký + tài khoản + đơn hàng, tỷ lệ chuyển đổi, dùng thử sắp hết hạn,
             khách bị bỏ quên, doanh thu; thứ Hai đề xuất 3 việc lên bảng Phòng ban.

Dữ liệu: DATA_DIR/sales.json {research: {email: ...}, drafts: [...], reports: [...]}.
"""
import datetime as dt
import json
import secrets
import threading

from config import DATA_DIR

FILE = DATA_DIR / "sales.json"
_LOCK = threading.Lock()
APP_LOGIN = "https://app.roimaxxhub.com/login"
APP_MARKET = "https://app.roimaxxhub.com/market"
SEGMENTS = {"solopreneur": "Cá nhân kinh doanh", "quan_ly": "Quản lý / trưởng nhóm", "doanh_nghiep": "Doanh nghiệp", "khac": "Khác"}
KINDS = {"chao_mung": "Chào mừng", "nhac_dung_thu": "Nhắc dùng thử", "sap_het_han": "Sắp hết hạn dùng thử", "nang_cap": "Mời nâng cấp", "hoi_tham": "Hỏi thăm"}
DRAFT_STATUS = {"cho_duyet": "Chờ anh duyệt", "da_gui": "Đã gửi", "tu_choi": "Từ chối"}
STAGES = ("moi", "da_lien_he", "dang_trao_doi", "dung_thu", "khach")
FREE_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "yahoo.com.vn", "live.com", "proton.me", "protonmail.com"}


def _now() -> dt.datetime:
    return dt.datetime.now()


def _iso(t: dt.datetime | None = None) -> str:
    return (t or _now()).strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("research", {})
    d.setdefault("drafts", [])
    d.setdefault("reports", [])
    return d


def _save(d: dict) -> None:
    d["drafts"] = d["drafts"][-2000:]
    d["reports"] = d["reports"][-30:]
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def _n(v) -> str:
    return f"{int(v or 0):,}".replace(",", ".")


def _days_since(s: str) -> int | None:
    try:
        return (_now() - dt.datetime.fromisoformat((s or "")[:19])).days
    except Exception:
        return None


# ------------------------------------------------------------------ gom dữ liệu về một khách
def _facts(email: str) -> dict:
    """Tất cả những gì hệ thống biết về một email (khách đăng ký, tài khoản, đơn đã mua). Mỗi nguồn bọc try riêng."""
    email = (email or "").strip().lower()
    f: dict = {"email": email, "domain": email.split("@")[-1] if "@" in email else "", "lead": None, "account": None, "orders": [], "spent": 0}
    f["company_guess"] = "" if f["domain"] in FREE_DOMAINS or not f["domain"] else f["domain"].split(".")[0]
    try:
        from agents import leads
        f["lead"] = next((r for r in leads._load() if r.get("email") == email), None)
    except Exception:
        pass
    try:
        from core import accounts
        u = accounts.by_email(email)
        if u:
            f["account"] = {k: u.get(k) for k in ("id", "name", "company", "plan", "trial_until", "created", "last_login", "roles")}
    except Exception:
        pass
    try:
        from agents import pay
        f["orders"] = [{"name": o.get("name"), "amount": o.get("amount"), "status": o.get("status"), "at": o.get("paid_at") or o.get("created")}
                       for o in pay._load()["orders"].values() if (o.get("email") or "").lower() == email and o.get("status") in ("paid", "delivered")]
        f["spent"] = sum(int(o["amount"] or 0) for o in f["orders"])
    except Exception:
        pass
    ld = f["lead"] or {}
    f.update(days_since_signup=_days_since(ld.get("at") or (f["account"] or {}).get("created") or ""), interests=ld.get("interests", []),
             src=ld.get("src", ""), status=ld.get("status", "moi"))
    return f


def _heuristic(f: dict) -> dict:
    """Chấm điểm khi không có AI: minh bạch, cộng điểm theo tín hiệu."""
    acc = f["account"] or {}
    seg = "doanh_nghiep" if f["company_guess"] else ("quan_ly" if (acc.get("company") or "").strip() else "solopreneur")
    signals = [(bool(f["company_guess"]), 20, f"Email công ty ({f['domain']}): khả năng là tổ chức."),
               (not f["company_guess"], 0, "Email cá nhân: thiên về cá nhân kinh doanh."),
               (bool(acc), 20, f"Đã có tài khoản (gói {acc.get('plan') or 'free'})."),
               (bool(f["orders"]), 25, f"Đã mua {len(f['orders'])} lần, tổng {_n(f['spent'])}đ."),
               (bool(f["interests"]), 10, "Có quan tâm: " + ", ".join(f["interests"][:3]) + "."),
               ("market:" in (f["src"] or ""), 5, ""), (f["status"] in ("dung_thu", "khach"), 10, "")]
    score = 20 + sum(pt for on, pt, _ in signals if on)
    nxt = ("Mời nâng cấp gói trả phí" if f["orders"] or f["status"] == "dung_thu" else
           "Gửi thư chào mừng, mời đăng nhập dùng thử" if not acc else "Nhắc dùng thử và hỏi nhu cầu")
    return {"segment": seg, "score": max(0, min(100, score)), "reasons": [r for on, _, r in signals if on and r], "next_step": nxt}


RESEARCH_PROMPT = """Bạn là Giám đốc bán hàng (CSO) của superYou, siêu trợ lý AI của Roimaxx (Việt Nam), bán qua Marketplace và gói thuê bao.
Dữ liệu về một khách tiềm năng (JSON): {data}
Hãy chấm điểm phù hợp khách hàng lý tưởng (ICP). Không bịa thông tin ngoài dữ liệu.
Trả về JSON: {{"segment": "solopreneur|quan_ly|doanh_nghiep|khac", "score": 0-100, "reasons": ["..."], "next_step": "1 câu tiếng Việt"}}"""


def research(email: str, refresh: bool = False) -> dict:
    """Nghiên cứu: điểm ICP + phân khúc cho một khách, cache theo email (AI, lỗi thì dùng heuristic)."""
    email = (email or "").strip().lower()
    if "@" not in email:
        raise ValueError("Cần một địa chỉ email.")
    d = _load()
    c = d["research"].get(email)
    if c and not refresh and (_days_since(c.get("at", "")) or 0) < 7:
        return {"text": c["text"], **c}
    f = _facts(email)
    res = None
    try:
        import llm
        slim = {k: f[k] for k in ("email", "domain", "company_guess", "src", "status", "interests", "account", "orders", "spent", "days_since_signup")}
        res = llm.ask_json(RESEARCH_PROMPT.format(data=json.dumps(slim, ensure_ascii=False)), max_tokens=800, tag="cso_research",
                           ok=lambda r: isinstance(r, dict) and r.get("segment") in SEGMENTS and isinstance(r.get("reasons"), list))
    except Exception:
        res = None
    src, h = ("ai" if res else "heuristic"), _heuristic(f)
    res = res or h
    score = max(0, min(100, int(res.get("score", h["score"])))) if str(res.get("score", "")).lstrip("-").isdigit() else h["score"]
    item = {"email": email, "segment": res["segment"], "score": score, "reasons": [str(x)[:200] for x in res["reasons"][:5]],
            "next_step": str(res.get("next_step", ""))[:200], "company": f["company_guess"], "has_account": bool(f["account"]),
            "plan": (f["account"] or {}).get("plan", ""), "spent": f["spent"], "days": f["days_since_signup"], "by": src, "at": _iso()}
    item["text"] = (f"{email}: {SEGMENTS[item['segment']]}, điểm ICP {score}/100. " + " ".join(item["reasons"]) +
                    (f" Bước tiếp: {item['next_step']}" if item["next_step"] else ""))
    with _LOCK:
        d = _load()
        d["research"][email] = item
        _save(d)
    return dict(item)


# ------------------------------------------------------------------ Theo đuổi: soạn thư, duyệt, gửi
def _template(kind: str, seg: str, name: str, f: dict) -> tuple[str, str]:
    who = {"solopreneur": "người kinh doanh độc lập", "quan_ly": "người quản lý đội nhóm", "doanh_nghiep": "doanh nghiệp", "khac": "người bận rộn"}[seg]
    hi = f"Chào {name}," if name else "Chào anh/chị,"
    until = (f["account"] or {}).get("trial_until") or ""
    body = {
        "chao_mung": f"{hi}\n\nCảm ơn anh/chị đã quan tâm đến superYou, siêu trợ lý AI dành cho {who}: lịch, email, nội dung, tài chính và khách hàng gom về một chỗ, nói một câu là xong việc.\n\nAnh/chị có thể đăng nhập dùng ngay tại {APP_LOGIN} và xem các gói, workflow sẵn có ở {APP_MARKET}.\n\nNếu cần em hướng dẫn nhanh 15 phút, chỉ cần trả lời thư này.",
        "nhac_dung_thu": f"{hi}\n\nEm thấy anh/chị đã đăng ký superYou nhưng chưa dùng nhiều. Với {who}, ba việc nên thử đầu tiên: bản tin sáng, hộp thư AI và kế hoạch ngày.\n\nĐăng nhập tại {APP_LOGIN}; có gì vướng anh/chị cứ trả lời thư này, em hỗ trợ ngay.",
        "sap_het_han": f"{hi}\n\nBản dùng thử superYou của anh/chị sắp hết hạn{(' (' + until + ')') if until else ''}. Để không gián đoạn dữ liệu và workflow đã thiết lập, anh/chị có thể chọn gói phù hợp tại {APP_MARKET}.\n\nNếu còn băn khoăn về gói nào hợp với {who}, em sẵn sàng tư vấn.",
        "nang_cap": f"{hi}\n\nAnh/chị đang dùng gói {((f['account'] or {}).get('plan') or 'miễn phí')} của superYou. Với nhu cầu của {who}, gói cao hơn mở thêm giới hạn AI, workflow riêng và hỗ trợ ưu tiên.\n\nXem và nâng cấp tại {APP_MARKET}; đăng nhập ở {APP_LOGIN}.",
        "hoi_tham": f"{hi}\n\nEm là trợ lý bán hàng của superYou, muốn hỏi thăm anh/chị dùng sản phẩm thế nào, có điểm nào chưa ổn hoặc muốn thêm tính năng gì không. Mỗi góp ý đều được chuyển thẳng tới đội phát triển.\n\nAnh/chị có thể trả lời thư này hoặc vào {APP_LOGIN}.",
    }[kind]
    subj = {"chao_mung": "Chào mừng anh/chị đến với superYou", "nhac_dung_thu": "Ba việc nên thử đầu tiên với superYou",
            "sap_het_han": "Bản dùng thử superYou sắp hết hạn", "nang_cap": "Mở rộng superYou cho công việc của anh/chị", "hoi_tham": "superYou có đang giúp được anh/chị?"}[kind]
    return subj, body + "\n\nTrân trọng,\nĐội superYou · Roimaxx"


DRAFT_PROMPT = """Bạn là nhân viên bán hàng tận tâm của superYou (siêu trợ lý AI của Roimaxx, Việt Nam). Viết một email tiếng Việt ngắn (120–180 chữ),
giọng thân thiện, không hô hào, không bịa tính năng. Loại thư: {kind_label}. Khách: {data}
Bắt buộc có link đăng nhập {login} và link xem gói {market}. Ký tên "Đội superYou · Roimaxx".
Trả về JSON: {{"subject": "...", "body": "..."}}"""


def draft(email: str, kind: str = "chao_mung", note: str = "") -> dict:
    """Soạn nháp thư theo phân khúc; lưu trạng thái chờ duyệt, không gửi."""
    if kind not in KINDS:
        raise ValueError("Loại thư không hợp lệ")
    r = research(email)
    f = _facts(r["email"])
    name = (f["account"] or {}).get("name") or ""
    subj, body = _template(kind, r["segment"], name, f)
    by = "mau"
    try:
        import llm
        data = {"name": name, "segment": SEGMENTS[r["segment"]], "company": r["company"], "plan": r["plan"], "interests": f["interests"],
                "trial_until": (f["account"] or {}).get("trial_until", ""), "note": note[:300]}
        res = llm.ask_json(DRAFT_PROMPT.format(kind_label=KINDS[kind], data=json.dumps(data, ensure_ascii=False), login=APP_LOGIN, market=APP_MARKET),
                           max_tokens=900, tag="cso_draft", ok=lambda x: isinstance(x, dict) and len(str(x.get("body", ""))) > 60 and x.get("subject"))
        if res and not llm.degenerate(str(res["body"])) and APP_LOGIN in res["body"]:
            subj, body, by = str(res["subject"])[:160], str(res["body"])[:4000], "ai"
    except Exception:
        pass
    x = {"id": secrets.token_hex(3), "email": r["email"], "kind": kind, "segment": r["segment"], "subject": subj, "body": body, "by": by,
         "status": "cho_duyet", "at": _iso(), "note": note[:300]}
    with _LOCK:
        d = _load()
        d["drafts"].append(x)
        _save(d)
    return {"text": f"Đã soạn nháp “{KINDS[kind]}” cho {x['email']} (chờ anh duyệt).\n\nTiêu đề: {subj}\n\n{body}", "item": x}


def approve(did: str, send: bool = True, platform: str = "") -> dict:
    """Anh duyệt nháp: gửi qua Lark Mail (ưu tiên) hoặc Gmail, cập nhật khách sang 'Đã liên hệ'."""
    from agents import mailbox
    with _LOCK:
        d = _load()
        x = next((y for y in d["drafts"] if y["id"] == did), None)
        if not x:
            raise ValueError("Không tìm thấy nháp")
        if x["status"] != "cho_duyet":
            raise ValueError("Nháp này đã xử lý rồi")
        x["approved_at"] = _iso()
        if not send:
            _save(d)
            return {"text": f"Đã duyệt nháp cho {x['email']} (chưa gửi).", "item": x}
        platform = platform if platform in ("lark", "gmail") else ("lark" if mailbox.lark_mail_ready() else "gmail")
        mailbox.send(platform, x["email"], x["subject"], x["body"])
        x.update({"status": "da_gui", "sent_at": _iso(), "platform": platform})
        _save(d)
    try:
        from agents import leads
        cur = next((r for r in leads._load() if r.get("email") == x["email"]), None)
        if cur and cur.get("status", "moi") == "moi":
            leads.set_status(x["email"], "da_lien_he", f"CSO gửi thư {KINDS[x['kind']]} ({_now():%d/%m})")
    except Exception:
        pass
    return {"text": f"Đã gửi “{x['subject']}” tới {x['email']} qua {platform}.", "item": x}


def reject(did: str, note: str = "") -> dict:
    """Từ chối một nháp."""
    with _LOCK:
        d = _load()
        x = next((y for y in d["drafts"] if y["id"] == did), None)
        if not x:
            raise ValueError("Không tìm thấy nháp")
        x.update({"status": "tu_choi", "note": (note or x.get("note", ""))[:300], "updated": _iso()})
        _save(d)
    return {"text": f"Đã bỏ nháp gửi {x['email']}.", "item": x}


def drafts(status: str = "cho_duyet") -> dict:
    """Danh sách nháp theo trạng thái (bỏ trống = tất cả)."""
    rows = [x for x in _load()["drafts"] if not status or x["status"] == status][::-1]
    return {"text": f"Có {len(rows)} nháp" + (f" {DRAFT_STATUS[status].lower()}" if status in DRAFT_STATUS else "") + ".", "items": rows[:200],
            "kinds": KINDS, "statuses": DRAFT_STATUS}


# ------------------------------------------------------------------ RevOps
def pipeline() -> dict:
    """Phễu bán hàng: khách đăng ký + tài khoản + đơn hàng; chuyển đổi, dùng thử sắp hết, khách bị bỏ quên, doanh thu."""
    today = dt.date.today()
    rows: list[dict] = []
    try:
        from agents import leads
        rows = leads._load()
    except Exception:
        pass
    stages = {k: 0 for k in STAGES}
    for r in rows:
        s = r.get("status", "moi")
        if s in stages:
            stages[s] += 1
    total = sum(stages.values())
    stale = [{"email": r["email"], "days": _days_since(r.get("at", "")) or 0, "src": r.get("src", "")} for r in rows
             if r.get("status", "moi") == "moi" and (_days_since(r.get("at", "")) or 0) > 3]
    expiring, accounts_n, trials = [], 0, 0
    try:
        from core import accounts
        for u in accounts.admin_list()["items"]:
            accounts_n += 1
            if u.get("plan") == "trial":
                trials += 1
                tu = u.get("trial_until") or ""
                left = (dt.date.fromisoformat(tu[:10]) - today).days if len(tu) >= 10 else 99
                if left <= 3:
                    expiring.append({"email": u.get("email"), "name": u.get("name", ""), "trial_until": tu, "days_left": left})
    except Exception:
        pass
    revenue = {"month": 0, "total": 0, "buyers": 0}
    try:
        from agents import pay
        pd = pay._load()
        ym = today.strftime("%Y-%m")
        sales = [e for e in pd["ledger"] if e.get("kind") == "sale"]
        revenue = {"month": sum(e["amount"] for e in sales if e["at"][:7] == ym), "total": sum(e["amount"] for e in sales),
                   "buyers": len({(o.get("email") or "").lower() for o in pd["orders"].values() if o.get("status") in ("paid", "delivered")})}
    except Exception:
        pass
    contacted = total - stages["moi"]
    conv = {"lien_he": round(contacted / total * 100) if total else 0, "dung_thu": round((stages["dung_thu"] + stages["khach"]) / total * 100) if total else 0,
            "khach": round(stages["khach"] / total * 100) if total else 0}
    text = (f"Phễu: {total} khách ({stages['moi']} mới, {stages['da_lien_he']} đã liên hệ, {stages['dang_trao_doi']} đang trao đổi, {stages['dung_thu']} dùng thử, "
            f"{stages['khach']} khách hàng); chuyển đổi liên hệ {conv['lien_he']}%, thành khách {conv['khach']}%. "
            f"Tài khoản: {accounts_n} ({trials} dùng thử, {len(expiring)} sắp hết hạn ≤3 ngày). {len(stale)} khách mới chưa ai liên hệ quá 3 ngày. "
            f"Doanh thu tháng {_n(revenue['month'])}đ, tổng {_n(revenue['total'])}đ, {revenue['buyers']} người mua.")
    return {"text": text, "stages": stages, "total": total, "conversion": conv, "expiring": sorted(expiring, key=lambda x: x["days_left"]),
            "stale": sorted(stale, key=lambda x: -x["days"])[:50], "accounts": accounts_n, "trials": trials, "revenue": revenue}


def auto_followups() -> dict:
    """Việc hằng ngày: soạn nháp chào mừng cho khách mới >1 ngày chưa có nháp, nháp sắp hết hạn cho dùng thử ≤3 ngày; báo anh số nháp chờ duyệt."""
    p = pipeline()
    have = {(x["email"], x["kind"]) for x in _load()["drafts"]}
    made: list[str] = []
    todo = [(u["email"], "sap_het_han") for u in p["expiring"] if u.get("email")]
    try:
        from agents import leads
        todo += [(r["email"], "chao_mung") for r in leads._load() if r.get("status", "moi") == "moi" and (_days_since(r.get("at", "")) or 0) >= 1]
    except Exception:
        pass
    for email, kind in todo:
        if (email, kind) not in have:
            try:
                draft(email, kind)
                made.append(f"{email} ({KINDS[kind].lower()})")
            except Exception:
                pass
    pending = len(drafts("cho_duyet")["items"])
    if pending:
        try:
            from core import security
            security.alert_once("cso:drafts:" + dt.date.today().isoformat(), f"📨 CSO superYou: {pending} thư chờ anh duyệt gửi khách ({len(made)} nháp mới hôm nay). Mở app › Bán hàng.", every=86400)
        except Exception:
            pass
    return {"text": f"Đã soạn {len(made)} nháp mới" + (": " + ", ".join(made[:10]) if made else "") + f". Tổng {pending} nháp chờ anh duyệt.", "made": made, "pending": pending}


REPORT_PROMPT = """Bạn là Giám đốc bán hàng (CSO) của superYou (siêu trợ lý AI của Roimaxx, Việt Nam). Số liệu phễu tuần này (JSON): {data}
Đề xuất đúng 3 hành động bán hàng cụ thể cho 7 ngày tới, dựa trên số liệu, không bịa. Mỗi hành động: title ngắn, why (dẫn số), impact ước tính.
Trả về JSON: {{"headline": "1 câu tình hình", "actions": [{{"title": "...", "why": "...", "impact": "..."}}]}}"""


def _fallback_actions(p: dict) -> list[dict]:
    acts = []
    if p["stale"]:
        acts.append({"title": f"Liên hệ {len(p['stale'])} khách mới bị bỏ quên", "why": "Khách đăng ký quá 3 ngày chưa ai liên hệ; càng để lâu càng nguội.", "impact": "Tăng tỷ lệ liên hệ"})
    if p["expiring"]:
        acts.append({"title": f"Chốt {len(p['expiring'])} tài khoản dùng thử sắp hết hạn", "why": "Hết hạn trong ≤3 ngày, thời điểm quyết định mua.", "impact": "Thêm khách trả phí"})
    if p["total"] and p["conversion"]["khach"] < 10:
        acts.append({"title": "Hỏi thăm khách đang trao đổi/dùng thử để gỡ vướng", "why": f"Chuyển đổi thành khách chỉ {p['conversion']['khach']}%.", "impact": "Tăng chuyển đổi"})
    if not p["total"]:
        acts.append({"title": "Đẩy landing page/Marketplace để có khách đăng ký", "why": "Phễu chưa có khách nào.", "impact": "Có dữ liệu để bán"})
    acts.append({"title": "Duyệt các thư CSO đã soạn", "why": "Thư chỉ gửi khi anh duyệt.", "impact": "Giữ nhịp theo đuổi"})
    return acts[:3]


def weekly_report(to_board: bool = True) -> dict:
    """Báo cáo tuần (thứ Hai): tóm tắt phễu + 3 hành động đề xuất; đưa lên bảng Phòng ban nếu to_board."""
    p = pipeline()
    res = None
    try:
        import llm
        slim = {k: p[k] for k in ("stages", "total", "conversion", "accounts", "trials", "revenue")} | {"expiring": len(p["expiring"]), "stale": len(p["stale"])}
        res = llm.ask_json(REPORT_PROMPT.format(data=json.dumps(slim, ensure_ascii=False)), max_tokens=1200, tag="cso_week",
                           ok=lambda r: isinstance(r, dict) and isinstance(r.get("actions"), list) and r["actions"])
    except Exception:
        pass
    acts = [{"title": str(a.get("title", ""))[:120], "why": str(a.get("why", ""))[:400], "impact": str(a.get("impact", ""))[:160]} for a in (res or {}).get("actions", [])[:3]] or _fallback_actions(p)
    headline = str((res or {}).get("headline") or f"{p['total']} khách trong phễu, {p['stages']['khach']} đã mua, {len(p['expiring'])} dùng thử sắp hết hạn, {len(p['stale'])} khách bị bỏ quên.")[:300]
    week = _now().strftime("%G-W%V")
    text = f"📈 CSO superYou · tuần {week}\n{headline}\n{p['text']}\nNên làm: " + " · ".join(f"{i + 1}) {a['title']}" for i, a in enumerate(acts))
    rep = {"week": week, "at": _iso(), "headline": headline, "actions": acts, "text": text, "pipeline": {k: p[k] for k in ("stages", "conversion", "revenue")}}
    with _LOCK:
        d = _load()
        d["reports"] = [r for r in d["reports"] if r.get("week") != week] + [rep]
        _save(d)
    if to_board:
        try:
            from agents import board
            board.propose("sales", f"Kế hoạch bán hàng tuần {week}", text, why=headline, impact="; ".join(a["impact"] for a in acts if a["impact"])[:600],
                          needs="Anh duyệt thư CSO đã soạn và chọn hành động ưu tiên", priority="vua", by="CSO (AI)", key=f"cso:week:{week}")
        except Exception:
            pass
    return rep


def overview() -> dict:
    """Thẻ tổng quan cho dashboard: phễu, nháp chờ duyệt, báo cáo gần nhất."""
    p = pipeline()
    d = _load()
    pend = [x for x in d["drafts"] if x["status"] == "cho_duyet"][::-1]
    last = d["reports"][-1] if d["reports"] else None
    top = sorted(d["research"].values(), key=lambda x: -x.get("score", 0))[:10]
    return {"text": p["text"] + f" {len(pend)} thư chờ anh duyệt.", "pipeline": p, "drafts_pending": len(pend), "drafts": pend[:50],
            "last_report": last, "top_leads": top, "segments": SEGMENTS, "kinds": KINDS, "draft_statuses": DRAFT_STATUS}
