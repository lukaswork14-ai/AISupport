"""superHuy Marketplace: nơi tạo, chia sẻ và bán tài sản trí tuệ (skill, gói Second Brain, workflow).

Tham khảo Apple App Store (nổi bật, bảng xếp hạng, trang chi tiết, có gì mới, đánh giá) và
Shopify App Store (danh mục, giá rõ ràng, huy hiệu "Chính chủ superHuy", người bán, kiểm duyệt trước khi lên kệ).

Giai đoạn 1 (bản này): khám phá, xem chi tiết, cài/gỡ/bật tắt, chạy workflow, đánh giá, người tạo đăng sản phẩm,
người ngoài gửi sản phẩm qua trang công khai -> chờ chủ nhân duyệt. Thanh toán và chia doanh thu: giai đoạn sau
(phòng GTM chốt mô hình). Sản phẩm có giá thì khách để lại email "Nhận sớm".

Loại tài sản:
- skill:    hướng dẫn superHuy làm theo khi gặp đúng việc (chèn vào system prompt khi đang bật).
- brain:    gói ghi chú tri thức, khi cài sẽ ghi vào Second Brain (Obsidian) ở 03 Resources/Marketplace/<tên>.
- workflow: chuỗi công cụ superHuy chạy liền mạch bằng một chạm (chỉ công cụ đọc/tổng hợp, không gửi/đăng/xoá).
"""
import datetime as dt
import json
import re
import secrets
import threading

from config import DATA_DIR

FILE = DATA_DIR / "market.json"
_LOCK = threading.Lock()
TYPES = {"skill": "Skill", "brain": "Gói Second Brain", "workflow": "Workflow"}
CATS = {"dieu-hanh": "Điều hành", "hop": "Họp & quyết định", "noi-dung": "Nội dung & marketing", "ban-hang": "Bán hàng & e-commerce",
        "hoc": "Học tập", "nang-suat": "Năng suất cá nhân"}
COLORS = ["#5B3FD9", "#0E7C6B", "#C2410C", "#B4236B", "#2457C5", "#7A5A00"]
OFFICIAL = {"name": "superHuy", "handle": "superhuy", "official": True}
# Workflow chỉ được gọi công cụ đọc/tổng hợp. Không gửi thư, không đăng bài, không xoá, không thanh toán.
_DENY = re.compile(r"(gui|dang|xoa|send|post|delete|pay|traloi|doipin|ketnoi|ket_noi|join|apdung|luu_khoa)", re.I)
SKILL_MAX = 4000


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("listings", {})
    d.setdefault("installs", {})
    d.setdefault("seeded", 0)
    d.setdefault("creators", {})
    d.setdefault("log", [])
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def _slug(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFD", (s or "").replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60] or "san-pham"


def _clean(s, n: int) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(s or "")).strip()[:n]


# ------------------------------------------------------------------ hàng chính chủ (khởi tạo một lần)
def _official_seed() -> list[dict]:
    out = []
    out.append({
        "type": "skill", "name": "Biên bản họp kiểu CEO", "category": "hop", "price": 0, "color": COLORS[0],
        "tagline": "Biên bản gọn một trang: quyết định, đầu việc có người và hạn, rủi ro cần theo dõi.",
        "description": ("Skill này dạy superHuy viết biên bản họp theo cách một CEO cần đọc: quyết định lên đầu, việc nào cũng có người "
                        "chịu trách nhiệm và hạn chót, câu hỏi còn treo được tách riêng. Dùng cho mọi cuộc họp ghi âm trong app hoặc file gửi qua Telegram."),
        "tags": ["họp", "biên bản", "giao việc"], "examples": ["Tóm tắt cuộc họp sáng nay và giao việc cho team", "Viết biên bản cuộc họp vừa ghi âm, gửi vào nhóm Lark"],
        "content": {"skill": (
            "Khi viết hoặc tóm tắt biên bản họp:\n"
            "1. Mở đầu bằng 'Quyết định' (đánh số, mỗi dòng một quyết định, ghi ai chốt).\n"
            "2. 'Đầu việc': mỗi việc có người phụ trách, hạn chót cụ thể (ngày), tiêu chí xong. Thiếu người hoặc hạn thì ghi rõ 'CẦN CHỐT'.\n"
            "3. 'Câu hỏi còn treo' và 'Rủi ro cần theo dõi' tách riêng, mỗi mục kèm người theo dõi.\n"
            "4. Tối đa một trang. Bỏ phần kể lại diễn biến, chỉ giữ số liệu và lập luận dẫn tới quyết định.\n"
            "5. Kết thúc bằng 1 câu: việc quan trọng nhất trong 48 giờ tới.")}})
    out.append({
        "type": "skill", "name": "Ra quyết định: tư duy bậc hai + pre-mortem", "category": "hop", "price": 0, "color": COLORS[1],
        "tagline": "Mỗi khi anh hỏi nên hay không, superHuy chạy pre-mortem và soi hệ quả bậc hai trước khi khuyên.",
        "description": ("Rút từ khoá 'Ra quyết định đỉnh cao 30 ngày' trong superHuy. Khi anh cân nhắc một quyết định, superHuy không trả lời "
                        "có hoặc không ngay mà đi qua checklist: điều gì làm nó thất bại, hệ quả của hệ quả, có đảo ngược được không, cần thêm dữ liệu gì."),
        "tags": ["ra quyết định", "mental models", "CEO"], "examples": ["Có nên mở thêm kho ở Hà Nội không?", "Chọn chạy quảng cáo TikTok hay Facebook quý này?"],
        "content": {"skill": (
            "Khi anh hỏi về một quyết định (nên/không nên, chọn A hay B, có làm không):\n"
            "1. Phân loại: quyết định đảo ngược được (cửa hai chiều) hay không (cửa một chiều). Cửa hai chiều thì khuyến khích quyết nhanh.\n"
            "2. Pre-mortem: giả sử 6 tháng sau quyết định này thất bại, liệt kê 3 lý do khả dĩ nhất.\n"
            "3. Tư duy bậc hai: hệ quả trực tiếp, rồi 'và rồi sao nữa' với khách hàng, đội ngũ, dòng tiền.\n"
            "4. Ước độ tin cậy (%) cho khuyến nghị và dữ liệu nào sẽ làm thay đổi kết luận.\n"
            "5. Đề xuất ghi vào nhật ký quyết định: bối cảnh, lựa chọn, kỳ vọng, ngày xem lại.")}})
    out.append({
        "type": "workflow", "name": "Bàn giao buổi sáng", "category": "dieu-hanh", "price": 0, "color": COLORS[2],
        "tagline": "Một chạm: lịch hôm nay, tóm tắt Lark, tóm tắt email, tin AI và e-commerce nổi bật.",
        "description": ("Chuỗi bốn bước superHuy chạy liền nhau mỗi khi anh bấm, gom thành một bản tin buổi sáng. Workflow chỉ đọc và tổng hợp, "
                        "không gửi hay đăng gì ra ngoài."),
        "tags": ["buổi sáng", "tổng hợp", "Lark", "email"],
        "content": {"steps": [{"agent": "lich", "action": "ngay", "params": {"date": "hôm nay"}, "label": "Lịch hôm nay"},
                              {"agent": "lark", "action": "tomtat", "params": {}, "label": "Tóm tắt Lark"},
                              {"agent": "email", "action": "tomtat", "params": {}, "label": "Tóm tắt email"},
                              {"agent": "tin", "action": "top", "params": {}, "label": "Tin nổi bật"}]}})
    try:
        from agents import learning
        for key, cat, col, price in (("agentic-commerce-30", "ban-hang", COLORS[3], 299000), ("ra-quyet-dinh-30", "hoc", COLORS[4], 0)):
            T = learning.TEMPLATES.get(key)
            if not T:
                continue
            notes = []
            for d in T["days"]:
                n, title = d[0], d[1]
                focus = d[5] if len(d) > 5 else ""
                ref = d[6] if len(d) > 6 else ""
                body = f"# Ngày {n}: {title}\n\n{focus}\n" + (f"\nTham khảo: {ref}\n" if ref else "")
                notes.append({"title": f"Ngày {n:02d} - {title}", "md": body})
            out.append({
                "type": "brain", "name": T["title"], "category": cat, "price": price, "color": col,
                "tagline": f"30 ghi chú theo ngày cho Second Brain: {T['topic'][:110]}",
                "description": (T.get("goal") or "") + "\n\nKhi cài, 30 ghi chú được thêm vào Second Brain (Obsidian) để superHuy tra cứu khi trả lời.",
                "tags": ["khoá học", "30 ngày"], "content": {"notes": notes}})
    except Exception:
        pass
    return out


def _mk(src: dict, creator: dict, status: str) -> dict:
    lid = secrets.token_hex(5)
    t = src.get("type") if src.get("type") in TYPES else "skill"
    return {"id": lid, "slug": _slug(src.get("name", "")) + "-" + lid[:4], "type": t, "name": _clean(src.get("name"), 80),
            "tagline": _clean(src.get("tagline"), 160), "description": _clean(src.get("description"), 4000),
            "category": src.get("category") if src.get("category") in CATS else "nang-suat",
            "tags": [_clean(x, 30) for x in (src.get("tags") or [])][:6], "price": max(0, int(src.get("price") or 0)),
            "color": src.get("color") or COLORS[sum(map(ord, lid)) % len(COLORS)], "creator": creator, "status": status,
            "version": "1.0", "whats_new": _clean(src.get("whats_new") or "Phát hành lần đầu.", 600),
            "content": src.get("content") or {}, "reviews": [], "installs": 0, "interest": 0,
            "examples": [_clean(e, 120) for e in (src.get("examples") or [])][:3], "billing": "monthly" if src.get("billing") == "monthly" else "once",
            "created": _now(), "updated": _now()}


def _ensure(d: dict) -> dict:
    if d.get("seeded", 0) < 1:
        for s in _official_seed():
            x = _mk(s, OFFICIAL, "published")
            d["listings"][x["id"]] = x
        d["seeded"] = 1
        _save(d)
    return d


# ------------------------------------------------------------------ hiển thị
def _summary(x: dict, d: dict | None = None) -> dict:
    rv = x.get("reviews") or []
    avg = round(sum(r["stars"] for r in rv) / len(rv), 1) if rv else 0
    c = x.get("content") or {}
    size = len(c.get("notes") or []) if x["type"] == "brain" else len(c.get("steps") or []) if x["type"] == "workflow" else len(c.get("skill") or "")
    inst = (d or {}).get("installs", {}).get(x["id"]) if d else None
    return {k: x.get(k) for k in ("id", "slug", "type", "name", "tagline", "category", "tags", "price", "color", "creator", "status",
                                  "version", "installs", "interest", "created", "updated")} | {
        "rating": avg, "rating_n": len(rv), "featured": bool(x.get("featured")), "type_label": TYPES[x["type"]], "cat_label": CATS.get(x["category"], ""),
        "size": size, "installed": bool(inst), "enabled": bool(inst and inst.get("enabled", True))}


def _contents_preview(x: dict) -> list[str]:
    c = x.get("content") or {}
    if x["type"] == "brain":
        return [n["title"] for n in (c.get("notes") or [])]
    if x["type"] == "workflow":
        return [s.get("label") or f"{s.get('agent')}.{s.get('action')}" for s in (c.get("steps") or [])]
    return [ln.strip() for ln in (c.get("skill") or "").split("\n") if ln.strip()][:12]


# ------------------------------------------------------------------ cấu phần hiển thị theo loại (App Store / Shopify / Zapier / Notion)
CONNECT_LABEL = {"lich": ("Lịch", "Google Calendar hoặc lịch Lark"), "email": ("Gmail", "Hộp thư Gmail"), "lark": ("Lark", "Nhóm chat Lark"),
                 "tin": ("Săn tin", "Không cần kết nối"), "brain": ("Second Brain", "Obsidian"), "hop": ("Họp", "Ghi âm trong app"),
                 "viec": ("Việc", "Lark Task, Google Tasks"), "taichinh": ("Tài chính", "Sổ thu chi trong app"), "web": ("Web", "Không cần kết nối")}
STEP_SECONDS = {"lich": 3, "email": 25, "lark": 20, "tin": 15, "web": 8}


def _tool_label(agent: str, action: str) -> str:
    try:
        from core import registry
        return registry.get_action(agent, action).label
    except Exception:
        return f"{agent}.{action}"


def _skill_spec(x: dict) -> dict:
    txt = (x.get("content") or {}).get("skill") or ""
    lines = [ln.strip() for ln in txt.split("\n") if ln.strip()]
    rules = [re.sub(r"^\d+[.)]\s*", "", ln) for ln in lines if re.match(r"^\d+[.)]", ln)]
    trigger = next((ln for ln in lines if re.match(r"^(khi|mỗi khi|nếu|when)", ln, re.I)), "") or ("Khi bạn giao việc thuộc loại: " + ", ".join(x.get("tags") or [])[:120] if x.get("tags") else "Khi câu hỏi của bạn khớp với nội dung skill")
    ex = x.get("examples") or []
    if not ex:
        ex = {"hop": ["Tóm tắt cuộc họp sáng nay và giao việc", "Viết biên bản cuộc họp vừa ghi âm"],
              "ban-hang": ["Viết listing cho mẫu áo mới", "Phân tích đơn hàng tuần này"],
              "noi-dung": ["Viết bài đăng cho fanpage về sản phẩm mới", "Lên kịch bản video 60 giây"],
              "dieu-hanh": ["Có gì cần tôi quyết hôm nay?", "Nên mở thêm kho ở Hà Nội không?"],
              "hoc": ["Hôm nay học gì?", "Ôn lại bài hôm qua"], "nang-suat": ["Lên lịch trình hôm nay giúp tôi", "Tôi nên làm gì trước?"]}.get(x.get("category"), ["Hỏi bất cứ việc gì thuộc chủ đề này"])
    return {"kind": "skill", "trigger": trigger.rstrip(":"), "rules": rules[:8], "rule_count": len(rules), "examples": ex[:3],
            "preview": lines[:6], "chars": len(txt), "permissions": ["Chỉ thay đổi cách trợ lý trả lời", "Không gửi, đăng hay xoá gì khi bạn chưa đồng ý"],
            "compat": ["Trò chuyện trong app và Telegram", "Áp dụng ngay sau khi cài, tắt được bất cứ lúc nào"]}


def _workflow_spec(x: dict) -> dict:
    steps = (x.get("content") or {}).get("steps") or []
    out, conns, secs = [], [], 0
    for st in steps:
        ag = st.get("agent", "")
        out.append({"agent": ag, "action": st.get("action", ""), "label": st.get("label") or _tool_label(ag, st.get("action", "")),
                    "tool": _tool_label(ag, st.get("action", "")), "connect": CONNECT_LABEL.get(ag, (ag, ""))[0]})
        c = CONNECT_LABEL.get(ag)
        if c and c[1] and "Không cần" not in c[1] and c[0] not in conns:
            conns.append(c[0])
        secs += STEP_SECONDS.get(ag, 10)
    return {"kind": "workflow", "steps": out, "step_count": len(out), "connects": conns, "runtime": f"khoảng {max(5, secs)} giây" if secs < 60 else f"khoảng {round(secs / 60)} phút",
            "how": "Bấm Chạy trong Marketplace › Đã cài, hoặc nhắn trợ lý: “chạy " + (x.get("name") or "workflow") + "”",
            "output": "Một bản tổng hợp theo từng bước, đọc trong app hoặc sao chép.",
            "permissions": ["Chỉ đọc và tổng hợp dữ liệu của bạn", "Không gửi thư, không đăng bài, không xoá"],
            "compat": ["Cần đã kết nối: " + (", ".join(conns) if conns else "không cần kết nối thêm")]}


def _brain_spec(x: dict) -> dict:
    notes = (x.get("content") or {}).get("notes") or []
    toc = [n["title"] for n in notes]
    sample = notes[0]["md"][:700] if notes else ""
    words = sum(len((n.get("md") or "").split()) for n in notes)
    return {"kind": "brain", "toc": toc[:60], "note_count": len(notes), "words": words, "read_min": max(1, round(words / 200)),
            "sample_title": notes[0]["title"] if notes else "", "sample": sample,
            "where": "Second Brain (Obsidian) › 03 Resources › Marketplace › " + (x.get("name") or "")[:40],
            "permissions": ["Ghi thêm ghi chú vào Second Brain của bạn", "Không sửa hay xoá ghi chú sẵn có"],
            "compat": ["Trợ lý tra cứu được ngay khi trả lời", "Gỡ sản phẩm vẫn giữ ghi chú, bạn tự xoá trong Obsidian"]}


def spec(x: dict) -> dict:
    """Cấu phần hiển thị theo loại, kèm phần Thông tin chung (như App Store)."""
    sp = {"skill": _skill_spec, "workflow": _workflow_spec, "brain": _brain_spec}[x["type"]](x)
    sp["info"] = [("Phiên bản", x.get("version", "1.0")), ("Cập nhật", (x.get("updated") or "")[:10]), ("Phát hành", (x.get("created") or "")[:10]),
                  ("Người tạo", (x.get("creator") or {}).get("name", "")), ("Danh mục", CATS.get(x.get("category"), "")),
                  ("Giá", "Miễn phí" if not x.get("price") else f"{x['price']:,}đ".replace(",", ".") + (" một lần" if x.get("billing", "once") == "once" else "/tháng"))]
    sp["billing"] = x.get("billing", "once")
    sp["buy_label"] = ("Nhận miễn phí" if not x.get("price") else ("Mua " + f"{x['price']:,}đ".replace(",", ".")) + ("" if x.get("billing", "once") == "once" else "/tháng"))
    return sp


def catalog(q: str = "", cat: str = "", type: str = "") -> dict:
    with _LOCK:
        d = _ensure(_load())
    pub = [x for x in d["listings"].values() if x["status"] == "published"]
    items = [_summary(x, d) for x in pub]
    ql = (q or "").strip().lower()
    if ql:
        items = [i for i in items if ql in (i["name"] + " " + (i["tagline"] or "") + " " + " ".join(i["tags"] or [])).lower()]
    if cat in CATS:
        items = [i for i in items if i["category"] == cat]
    if type in TYPES:
        items = [i for i in items if i["type"] == type]
    top = sorted(items, key=lambda i: (i["installs"] + i["interest"], i["rating"]), reverse=True)
    new = sorted(items, key=lambda i: i["created"], reverse=True)
    feat_ids = {x["id"] for x in pub if x.get("featured")}
    featured = ([i for i in items if i["id"] in feat_ids] or sorted([i for i in items if i["creator"].get("official")],
                key=lambda i: i["installs"], reverse=True) or top)[:5]
    mine_installed = [_summary(d["listings"][k], d) for k in d["installs"] if k in d["listings"]]
    pending = sum(1 for x in d["listings"].values() if x["status"] == "review")
    return {"text": f"Marketplace có {len(pub)} sản phẩm, anh đã cài {len(mine_installed)}.", "items": items, "top": top[:10],
            "new": new[:10], "featured": featured, "installed": mine_installed, "cats": CATS, "types": TYPES, "pending": pending}


def item(lid: str) -> dict:
    with _LOCK:
        d = _ensure(_load())
    x = d["listings"].get(lid) or next((v for v in d["listings"].values() if v["slug"] == lid), None)
    if not x:
        raise ValueError("Không tìm thấy sản phẩm")
    s = _summary(x, d)
    rv = x.get("reviews") or []
    dist = {str(k): sum(1 for r in rv if r["stars"] == k) for k in range(5, 0, -1)}
    c = x.get("content") or {}
    return s | {"description": x.get("description", ""), "whats_new": x.get("whats_new", ""), "reviews": rv[-30:][::-1], "dist": dist,
                "contents": _contents_preview(x), "skill_text": c.get("skill", "") if x["type"] == "skill" else "",
                "submitter": x.get("submitter", {}), "review_note": x.get("review_note", ""),
                "install": d["installs"].get(x["id"]), "spec": spec(x), "cloned_from": x.get("cloned_from"), "source_url": x.get("source_url", "")}


# ------------------------------------------------------------------ cài / gỡ / bật tắt / chạy
def install(lid: str) -> dict:
    with _LOCK:
        d = _ensure(_load())
        x = d["listings"].get(lid)
        if not x or x["status"] != "published":
            raise ValueError("Sản phẩm chưa lên kệ")
        if lid in d["installs"]:
            return {"text": f"“{x['name']}” đã được cài rồi."}
        extra = ""
        if x["type"] == "brain":
            from agents import second_brain
            folder = "03 Resources/Marketplace/" + second_brain._slug(x["name"])[:60]
            n = 0
            for note in (x["content"].get("notes") or [])[:200]:
                second_brain._write(folder, note["title"], {"source": "superHuy Marketplace", "topic": "marketplace",
                                                            "tags": ["marketplace", _slug(x["name"])[:30]]}, note["md"])
                n += 1
            extra = f" Đã thêm {n} ghi chú vào Second Brain ({folder})."
        d["installs"][lid] = {"at": _now(), "enabled": True, "version": x["version"]}
        x["installs"] = x.get("installs", 0) + 1
        _save(d)
    hint = {"skill": " superHuy sẽ áp dụng skill này từ câu trả lời tiếp theo.",
            "workflow": " Bấm “Chạy” trong mục Đã cài hoặc nhờ superHuy chạy workflow này."}.get(x["type"], "")
    return {"text": f"Đã cài “{x['name']}”.{extra}{hint}"}


def uninstall(lid: str) -> dict:
    with _LOCK:
        d = _load()
        x = d["listings"].get(lid)
        if lid not in d["installs"]:
            return {"text": "Sản phẩm chưa được cài."}
        d["installs"].pop(lid, None)
        if x:
            x["installs"] = max(0, x.get("installs", 1) - 1)
        _save(d)
    note = " Ghi chú đã thêm vào Second Brain vẫn được giữ, anh có thể xoá trong Obsidian." if x and x["type"] == "brain" else ""
    return {"text": f"Đã gỡ “{x['name'] if x else lid}”.{note}"}


def toggle(lid: str) -> dict:
    with _LOCK:
        d = _load()
        i = d["installs"].get(lid)
        if not i:
            raise ValueError("Sản phẩm chưa được cài")
        i["enabled"] = not i.get("enabled", True)
        _save(d)
        name = d["listings"].get(lid, {}).get("name", lid)
    return {"text": f"{'Đã bật' if i['enabled'] else 'Đã tắt'} “{name}”.", "enabled": i["enabled"]}


def _step_ok(st: dict) -> bool:
    return bool(st.get("agent")) and bool(st.get("action")) and not _DENY.search(f"{st['agent']}.{st['action']}")


def run_workflow(lid: str = "", name: str = "") -> dict:
    """Chạy một workflow đã cài (theo ID hoặc tên)."""
    from core import registry
    with _LOCK:
        d = _load()
    x = d["listings"].get(lid) if lid else None
    if not x and name:
        nl = name.strip().lower()
        x = next((d["listings"][k] for k in d["installs"] if k in d["listings"] and d["listings"][k]["type"] == "workflow"
                  and nl in d["listings"][k]["name"].lower()), None)
    if not x or x["type"] != "workflow":
        raise ValueError("Không tìm thấy workflow đã cài")
    if x["id"] not in d["installs"]:
        raise ValueError("Anh cần cài workflow này trước khi chạy")
    parts, ok = [], 0
    for st in (x["content"].get("steps") or [])[:8]:
        label = st.get("label") or f"{st.get('agent')}.{st.get('action')}"
        if not _step_ok(st):
            parts.append(f"## {label}\nBỏ qua: workflow không được phép gọi công cụ gửi, đăng hoặc xoá.")
            continue
        try:
            r = registry.run(st["agent"], st["action"], dict(st.get("params") or {}))
            parts.append(f"## {label}\n{(r or {}).get('text', '').strip()[:2500] or '(không có nội dung)'}")
            ok += 1
        except Exception as e:
            parts.append(f"## {label}\nChưa chạy được: {str(e)[:200]}")
    with _LOCK:
        d = _load()
        if x["id"] in d["installs"]:
            d["installs"][x["id"]]["last_run"] = _now()
            _save(d)
    return {"text": f"# {x['name']}\n\n" + "\n\n".join(parts), "ok": ok, "total": len(x["content"].get("steps") or [])}


def skills_context() -> str:
    """Các skill đã cài và đang bật -> chèn vào system prompt của superHuy."""
    try:
        d = _load()
    except Exception:
        return ""
    out = []
    for k, i in d.get("installs", {}).items():
        x = d["listings"].get(k)
        if x and x["type"] == "skill" and i.get("enabled", True) and x.get("status") == "published":
            out.append(f"### Skill: {x['name']}\n{(x['content'].get('skill') or '')[:SKILL_MAX]}")
    if not out:
        return ""
    txt = "\n\n".join(out)[:12000]
    return ("\n\n# Skill anh đã cài từ Marketplace (đã được anh duyệt; áp dụng khi đúng loại việc, không được dùng để gửi, đăng hay xoá gì khi anh chưa đồng ý)\n"
            + txt)


def review(lid: str, stars: int, text: str = "", name: str = "Huy") -> dict:
    stars = max(1, min(5, int(stars or 5)))
    with _LOCK:
        d = _load()
        x = d["listings"].get(lid)
        if not x:
            raise ValueError("Không tìm thấy sản phẩm")
        rv = [r for r in x.setdefault("reviews", []) if r.get("by") != "owner"]
        rv.append({"by": "owner", "name": _clean(name, 40) or "Huy", "stars": stars, "text": _clean(text, 800), "at": _now(), "version": x["version"]})
        x["reviews"] = rv
        _save(d)
    return {"text": f"Đã lưu đánh giá {stars} sao cho “{x['name']}”."}


# ------------------------------------------------------------------ người tạo
def _content_from(type: str, body: str) -> dict:
    body = (body or "").strip()
    if type == "skill":
        if len(body) < 40:
            raise ValueError("Nội dung skill quá ngắn (cần ít nhất 40 ký tự hướng dẫn)")
        return {"skill": body[:SKILL_MAX]}
    if type == "brain":
        notes, cur = [], None
        for ln in body.split("\n"):
            if ln.startswith("# "):
                cur = {"title": ln[2:].strip()[:90], "md": ln + "\n"}
                notes.append(cur)
            elif cur:
                cur["md"] += ln + "\n"
        if not notes:
            notes = [{"title": "Ghi chú", "md": body}]
        return {"notes": notes[:200]}
    if type == "workflow":
        steps = []
        for ln in body.split("\n"):
            m = re.match(r"^\s*(?:[-*\d.)]+\s*)?([a-z_]+)\.([a-z_]+)\s*(?:[:|-]\s*(.+))?$", ln.strip())
            if m:
                st = {"agent": m.group(1), "action": m.group(2), "params": {}, "label": (m.group(3) or "").strip()[:60]}
                if not _step_ok(st):
                    raise ValueError(f"Bước {m.group(1)}.{m.group(2)} gửi, đăng hoặc xoá dữ liệu nên không dùng được trong workflow")
                steps.append(st)
        if not steps:
            raise ValueError("Workflow cần ít nhất 1 bước, mỗi dòng dạng agent.hanh_dong: Tên bước (ví dụ lark.tomtat: Tóm tắt Lark)")
        return {"steps": steps[:8]}
    raise ValueError("Loại sản phẩm không hợp lệ")


def create(type: str, name: str, tagline: str, description: str, body: str, category: str = "nang-suat", price: int = 0,
           tags: str = "", publish: bool = True) -> dict:
    """Chủ nhân tạo sản phẩm của mình (lên kệ ngay hoặc lưu nháp)."""
    if not (name or "").strip():
        raise ValueError("Cần tên sản phẩm")
    x = _mk({"type": type, "name": name, "tagline": tagline, "description": description, "category": category, "price": price,
             "tags": [t.strip() for t in (tags or "").split(",") if t.strip()], "content": _content_from(type, body)},
            {"name": "Huy", "handle": "huy", "owner": True}, "published" if publish else "draft")
    with _LOCK:
        d = _ensure(_load())
        d["listings"][x["id"]] = x
        _save(d)
    return {"text": f"Đã {'đăng' if publish else 'lưu nháp'} “{x['name']}”.", "id": x["id"]}


def update(lid: str, version: str = "", whats_new: str = "", body: str = "", tagline: str = "", description: str = "",
           price: int | None = None, status: str = "") -> dict:
    with _LOCK:
        d = _load()
        x = d["listings"].get(lid)
        if not x:
            raise ValueError("Không tìm thấy sản phẩm")
        if not (x["creator"].get("owner") or x["creator"].get("official")):
            raise ValueError("Chỉ sửa được sản phẩm của anh")
        if body:
            x["content"] = _content_from(x["type"], body)
        if tagline:
            x["tagline"] = _clean(tagline, 160)
        if description:
            x["description"] = _clean(description, 4000)
        if price is not None and price != "":
            x["price"] = max(0, int(price))
        if version:
            x["version"] = _clean(version, 12)
            x["whats_new"] = _clean(whats_new, 600) or x.get("whats_new", "")
        if status in ("published", "draft", "archived"):
            x["status"] = status
        x["updated"] = _now()
        _save(d)
    return {"text": f"Đã cập nhật “{x['name']}”."}


def mine() -> dict:
    with _LOCK:
        d = _ensure(_load())
    own = [x for x in d["listings"].values() if x["creator"].get("owner") or x["creator"].get("official")]
    queue = [x for x in d["listings"].values() if x["status"] == "review"]
    return {"mine": [_summary(x, d) for x in sorted(own, key=lambda x: x["updated"], reverse=True)],
            "queue": [_summary(x, d) | {"submitter": x.get("submitter", {}), "description": x.get("description", ""),
                                        "contents": _contents_preview(x)} for x in queue],
            "stats": {"products": len(own), "installs": sum(x.get("installs", 0) for x in own),
                      "interest": sum(x.get("interest", 0) for x in own)}}


def moderate(lid: str, decision: str, note: str = "") -> dict:
    with _LOCK:
        d = _load()
        x = d["listings"].get(lid)
        if not x or x["status"] != "review":
            raise ValueError("Không có sản phẩm này trong hàng chờ duyệt")
        x["status"] = "published" if decision == "duyet" else "rejected"
        x["review_note"] = _clean(note, 600)
        x["updated"] = _now()
        _save(d)
    return {"text": f"{'Đã cho lên kệ' if x['status'] == 'published' else 'Đã từ chối'} “{x['name']}”."}


# ------------------------------------------------------------------ trang công khai
def public_catalog() -> dict:
    with _LOCK:
        d = _ensure(_load())
    items = []
    for x in d["listings"].values():
        if x["status"] != "published":
            continue
        s = _summary(x)
        s.pop("installed", None)
        s.pop("enabled", None)
        s["description"] = x.get("description", "")
        s["contents"] = _contents_preview(x)[:12] if x["type"] != "skill" else []
        s["whats_new"] = x.get("whats_new", "")
        s["reviews"] = [{k: r[k] for k in ("name", "stars", "text", "at")} for r in (x.get("reviews") or [])[-5:]][::-1]
        sp = spec(x)
        if sp["kind"] == "skill":
            sp["preview"] = sp["preview"][:4]
            sp["rules"] = sp["rules"][:3]
        s["spec"] = sp
        items.append(s)
    items.sort(key=lambda i: (i["installs"] + i["interest"], i["rating"]), reverse=True)
    return {"items": items, "cats": CATS, "types": TYPES}


def public_interest(lid: str, email: str) -> dict:
    """Khách ngoài bấm Nhận/Nhận sớm: lưu vào Khách đăng ký kèm sản phẩm quan tâm."""
    from agents import leads
    with _LOCK:
        d = _load()
        x = d["listings"].get(lid)
        if not x or x["status"] != "published":
            raise ValueError("Sản phẩm không tồn tại")
    leads.add(email, f"market:{x['slug']}", x["name"])
    with _LOCK:
        d = _load()
        if lid in d["listings"]:
            d["listings"][lid]["interest"] = d["listings"][lid].get("interest", 0) + 1
            _save(d)
    return {"ok": True}


# ------------------------------------------------------------------ nhật ký quản trị
def _log(d: dict, who: str, what: str):
    d["log"].append({"at": _now(), "who": who, "what": what[:200]})
    d["log"] = d["log"][-500:]


# ------------------------------------------------------------------ AI đóng gói: dán gì cũng được -> trang sản phẩm hoàn chỉnh
PACK = """Bạn là biên tập viên của superHuy Marketplace (giống App Store cho trợ lý AI điều hành doanh nghiệp).
Người tạo dán nguyên liệu dưới đây (có thể là SKILL.md theo chuẩn Agent Skills, ghi chú markdown, quy trình, prompt, hoặc nội dung một trang web).
Hãy đóng gói thành MỘT sản phẩm, viết tiếng Việt tự nhiên, cụ thể, không thổi phồng.

Loại sản phẩm (chọn 1):
- skill: hướng dẫn trợ lý làm theo khi gặp đúng loại việc (quy tắc, checklist, khung trả lời).
- brain: gói ghi chú tri thức (nhiều chủ đề/bài), sẽ được thêm vào Second Brain.
- workflow: chuỗi công cụ chạy liền nhau. Chỉ dùng các công cụ: {tools}.

Danh mục (category): {cats}

{extra}
Trả về JSON:
{{"type": "...", "name": "tên ngắn ≤ 60 ký tự", "tagline": "1 câu ≤ 140 ký tự nói lợi ích", "description": "2-4 đoạn: dành cho ai, làm được gì, dùng thế nào",
  "category": "mã danh mục", "tags": ["≤ 5 thẻ"], "whats_new": "1 câu",
  "body": "NỘI DUNG SẢN PHẨM. skill: hướng dẫn đánh số rõ ràng. brain: nhiều ghi chú, mỗi ghi chú bắt đầu bằng dòng '# Tiêu đề'. workflow: mỗi dòng 'agent.hanh_dong: Tên bước'",
  "checks": ["các điểm người tạo nên sửa trước khi gửi duyệt, có thể rỗng"]}}

NGUYÊN LIỆU:
<<<
{raw}
>>>"""

CLONE_NOTE = ("Đây là bản DỰNG MỚI lấy cảm hứng từ nguồn: giữ ý tưởng, cấu trúc và cách giải quyết vấn đề, nhưng viết lại hoàn toàn bằng lời của mình, "
              "điều chỉnh cho doanh nghiệp Việt Nam dùng superHuy; tuyệt đối không chép nguyên văn câu chữ của nguồn. ")


def _workflow_tools() -> str:
    try:
        from core import registry
        out = []
        for ag in registry.REGISTRY.values():
            for a in ag.actions:
                if a.llm and not _DENY.search(f"{ag.id}.{a.id}") and ag.id not in ("market", "khach"):
                    out.append(f"{ag.id}.{a.id} ({a.label})")
        return ", ".join(out[:60])
    except Exception:
        return "lich.ngay, lark.tomtat, email.tomtat, tin.top"


def _parse_skill_md(raw: str) -> dict:
    """Nhận SKILL.md chuẩn Agent Skills (frontmatter name/description) -> gợi ý sẵn tên, mô tả."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw.strip(), re.S)
    if not m:
        return {}
    meta = dict(re.findall(r"^([a-zA-Z_-]+):\s*(.+)$", m.group(1), re.M))
    return {"name": meta.get("name", "").strip().strip('"'), "description": meta.get("description", "").strip().strip('"'), "body": m.group(2).strip()}


def _validate(p: dict) -> list[str]:
    """Kiểm tra tự động như vòng review của App Store, trước khi gửi duyệt."""
    issues = []
    if len(p.get("name", "")) < 4:
        issues.append("Tên quá ngắn.")
    if len(p.get("tagline", "")) < 20:
        issues.append("Câu giới thiệu ngắn nên nói rõ lợi ích (từ 20 ký tự).")
    if len(p.get("description", "")) < 120:
        issues.append("Mô tả nên có ít nhất 120 ký tự: dành cho ai, làm được gì, dùng thế nào.")
    try:
        _content_from(p.get("type", ""), p.get("body", ""))
    except ValueError as e:
        issues.append(str(e))
    if re.search(r"(api[_-]?key|password|mật khẩu|token)\s*[:=]\s*\S{8,}", p.get("body", ""), re.I):
        issues.append("Nội dung có vẻ chứa khoá hoặc mật khẩu. Hãy xoá trước khi gửi.")
    return issues


def pack(raw: str, hint_type: str = "", source_url: str = "", clone: bool = False) -> dict:
    """Dán SKILL.md / ghi chú / quy trình / link -> AI đóng gói thành bản nháp sản phẩm (chưa lưu)."""
    raw = (raw or "").strip()
    src_txt = ""
    if source_url:
        from agents import web_tools
        r = web_tools.read(source_url, 9000)
        src_txt = r.get("text", "")
    if not raw and not src_txt:
        raise ValueError("Dán nội dung hoặc một link để đóng gói")
    pre = _parse_skill_md(raw) if raw.startswith("---") else {}
    extra = ""
    if hint_type in TYPES:
        extra += f"Người tạo muốn loại: {hint_type}.\n"
    if clone or source_url:
        extra += CLONE_NOTE + (f"Nguồn: {source_url}\n" if source_url else "")
    if pre:
        extra += f"Đây là SKILL.md chuẩn Agent Skills: name={pre.get('name')}, description={pre.get('description')}. Giữ nguyên ý nghĩa phần hướng dẫn.\n"
    import llm
    res = llm.ask_json(PACK.format(tools=_workflow_tools(), cats=", ".join(f"{k} ({v})" for k, v in CATS.items()), extra=extra,
                                   raw=(raw + ("\n\n" + src_txt if src_txt else ""))[:14000]),
                       max_tokens=5000, tag="market_pack", ok=lambda r: isinstance(r, dict) and r.get("body"))
    if not res:
        if pre:
            res = {"type": "skill", "name": pre.get("name") or "Skill mới", "tagline": pre.get("description", "")[:140],
                   "description": pre.get("description", ""), "body": pre.get("body", ""), "category": "nang-suat", "tags": []}
        else:
            raise ValueError("AI chưa đóng gói được lúc này, anh/chị thử lại sau ít phút")
    p = {"type": res.get("type") if res.get("type") in TYPES else (hint_type if hint_type in TYPES else "skill"),
         "name": _clean(res.get("name"), 80), "tagline": _clean(res.get("tagline"), 160), "description": _clean(res.get("description"), 4000),
         "category": res.get("category") if res.get("category") in CATS else "nang-suat",
         "tags": [_clean(t, 30) for t in (res.get("tags") or [])][:5], "whats_new": _clean(res.get("whats_new") or "Phát hành lần đầu.", 300),
         "body": str(res.get("body") or "")[:20000], "source_url": source_url}
    p["issues"] = _validate(p) + [_clean(c, 200) for c in (res.get("checks") or [])][:4]
    return p


# ------------------------------------------------------------------ PHÒNG PHÁT TRIỂN SẢN PHẨM SỐ (chỉ chủ nhân)
def studio_save(type: str, name: str, tagline: str = "", description: str = "", body: str = "", category: str = "nang-suat", price: int = 0,
                tags: str = "", publish: bool = False, featured: bool = False, source_url: str = "", lid: str = "") -> dict:
    """Chủ nhân tạo mới hoặc lưu sản phẩm trong Studio (nháp hoặc lên kệ ngay, có thể đưa lên nổi bật)."""
    content = _content_from(type, body)
    with _LOCK:
        d = _ensure(_load())
        if lid and lid in d["listings"]:
            x = d["listings"][lid]
            if not (x["creator"].get("owner") or x["creator"].get("official")):
                raise ValueError("Sản phẩm này thuộc người tạo khác; dùng Quản trị để chỉnh")
            x.update({"name": _clean(name, 80) or x["name"], "tagline": _clean(tagline, 160), "description": _clean(description, 4000),
                      "category": category if category in CATS else x["category"], "price": max(0, int(price or 0)),
                      "tags": [t.strip()[:30] for t in (tags or "").split(",") if t.strip()][:6], "content": content, "updated": _now()})
            if publish:
                x["status"] = "published"
        else:
            x = _mk({"type": type, "name": name, "tagline": tagline, "description": description, "category": category, "price": price,
                     "tags": [t.strip() for t in (tags or "").split(",") if t.strip()], "content": content},
                    {"name": "Huy", "handle": "huy", "owner": True}, "published" if publish else "draft")
            d["listings"][x["id"]] = x
        if source_url:
            x["source_url"] = _clean(source_url, 400)
        x["featured"] = bool(featured)
        _log(d, "Huy", f"Studio lưu “{x['name']}” ({x['status']})")
        _save(d)
    return {"text": f"Đã {'đăng' if x['status'] == 'published' else 'lưu nháp'} “{x['name']}”.", "id": x["id"]}


def studio_body(lid: str) -> dict:
    """Nội dung gốc của sản phẩm (để sửa trong Studio)."""
    with _LOCK:
        d = _load()
    x = d["listings"].get(lid)
    if not x:
        raise ValueError("Không tìm thấy sản phẩm")
    c = x.get("content") or {}
    body = c.get("skill") if x["type"] == "skill" else "\n".join(n["md"].strip() for n in c.get("notes") or []) if x["type"] == "brain" \
        else "\n".join(f"{s['agent']}.{s['action']}: {s.get('label', '')}" for s in c.get("steps") or [])
    return {"id": lid, "type": x["type"], "name": x["name"], "tagline": x.get("tagline", ""), "description": x.get("description", ""),
            "category": x["category"], "price": x.get("price", 0), "tags": ", ".join(x.get("tags") or []), "body": body or "",
            "status": x["status"], "featured": bool(x.get("featured")), "source_url": x.get("source_url", ""),
            "own": bool(x["creator"].get("owner") or x["creator"].get("official"))}


def clone(lid: str) -> dict:
    """Nhân bản 1 sản phẩm thành bản nháp của anh để phát triển tiếp (sản phẩm của người tạo khác: chỉ khi miễn phí)."""
    with _LOCK:
        d = _load()
        x = d["listings"].get(lid)
        if not x:
            raise ValueError("Không tìm thấy sản phẩm")
        mine_ = x["creator"].get("owner") or x["creator"].get("official")
        if not mine_ and x.get("price", 0) > 0:
            raise ValueError("Không nhân bản sản phẩm trả phí của người tạo khác. Hãy dùng “Dựng từ nguồn” để làm bản của riêng anh.")
        y = json.loads(json.dumps(x))
        y.update({"id": secrets.token_hex(5), "status": "draft", "installs": 0, "interest": 0, "reviews": [], "featured": False,
                  "creator": {"name": "Huy", "handle": "huy", "owner": True}, "version": "1.0", "created": _now(), "updated": _now(),
                  "name": (x["name"] + " (bản sao)")[:80], "cloned_from": {"id": x["id"], "name": x["name"], "creator": x["creator"].get("name")}})
        y["slug"] = _slug(y["name"]) + "-" + y["id"][:4]
        d["listings"][y["id"]] = y
        _log(d, "Huy", f"Nhân bản “{x['name']}”")
        _save(d)
    return {"text": f"Đã nhân bản thành bản nháp “{y['name']}”.", "id": y["id"]}


# ------------------------------------------------------------------ SUPER ADMIN (chủ App Store: chỉ chủ nhân)
def admin_overview() -> dict:
    with _LOCK:
        d = _ensure(_load())
    L = list(d["listings"].values())
    by_status = {}
    for x in L:
        by_status[x["status"]] = by_status.get(x["status"], 0) + 1
    rv = [r for x in L for r in (x.get("reviews") or [])]
    creators = []
    for c in d["creators"].values():
        mine_ = [x for x in L if x["creator"].get("id") == c["id"]]
        creators.append({k: c.get(k) for k in ("id", "name", "handle", "email", "status", "created", "bio")} |
                        {"products": len(mine_), "published": sum(1 for x in mine_ if x["status"] == "published"),
                         "installs": sum(x.get("installs", 0) for x in mine_), "interest": sum(x.get("interest", 0) for x in mine_)})
    rows = []
    for x in sorted(L, key=lambda x: x["updated"], reverse=True):
        rows.append(_summary(x, d) | {"submitter": x.get("submitter", {}), "review_note": x.get("review_note", ""),
                                      "pipeline_value": x.get("price", 0) * x.get("interest", 0)})
    return {"kpi": {"listings": len(L), "published": by_status.get("published", 0), "review": by_status.get("review", 0),
                    "creators": len(d["creators"]), "installs": sum(x.get("installs", 0) for x in L),
                    "interest": sum(x.get("interest", 0) for x in L), "reviews": len(rv),
                    "rating": round(sum(r["stars"] for r in rv) / len(rv), 1) if rv else 0,
                    "pipeline": sum(x.get("price", 0) * x.get("interest", 0) for x in L)},
            "by_status": by_status, "listings": rows, "creators": sorted(creators, key=lambda c: c["created"] or "", reverse=True),
            "log": d["log"][-40:][::-1], "cats": CATS, "types": TYPES}


def admin_set(lid: str, field: str, value: str = "", note: str = "") -> dict:
    """Quyền cao nhất trên mọi sản phẩm: nổi bật, gỡ khỏi kệ, khôi phục, duyệt/từ chối, đổi giá, danh mục."""
    with _LOCK:
        d = _load()
        x = d["listings"].get(lid)
        if not x:
            raise ValueError("Không tìm thấy sản phẩm")
        if field == "featured":
            x["featured"] = str(value).lower() in ("1", "true", "on", "yes")
            msg = ("Đã đưa lên nổi bật" if x["featured"] else "Đã bỏ khỏi nổi bật")
        elif field == "status" and value in ("published", "rejected", "archived", "draft", "review"):
            x["status"] = value
            if note:
                x["review_note"] = _clean(note, 600)
            msg = {"published": "Đã cho lên kệ", "rejected": "Đã từ chối", "archived": "Đã gỡ khỏi kệ", "draft": "Đã chuyển về nháp",
                   "review": "Đã chuyển về chờ duyệt"}[value]
        elif field == "price":
            x["price"] = max(0, int(float(value or 0)))
            msg = f"Đã đổi giá thành {x['price']:,}đ".replace(",", ".")
        elif field == "category" and value in CATS:
            x["category"] = value
            msg = f"Đã chuyển sang danh mục {CATS[value]}"
        else:
            raise ValueError("Thao tác không hợp lệ")
        x["updated"] = _now()
        _log(d, "Huy (quản trị)", f"{msg}: “{x['name']}”" + (f" — {note}" if note else ""))
        _save(d)
    return {"text": f"{msg}: “{x['name']}”."}


def admin_creator(cid: str, action: str) -> dict:
    """Khoá / mở khoá người tạo, cấp lại khoá truy cập console."""
    with _LOCK:
        d = _load()
        c = d["creators"].get(cid)
        if not c:
            raise ValueError("Không tìm thấy người tạo")
        key = ""
        if action == "khoa":
            c["status"] = "suspended"
            for x in d["listings"].values():
                if x["creator"].get("id") == cid and x["status"] == "published":
                    x["status"] = "archived"
                    x["review_note"] = "Gỡ do tài khoản người tạo bị khoá"
            msg = f"Đã khoá {c['name']} và gỡ các sản phẩm đang bán"
        elif action == "mo":
            c["status"] = "active"
            msg = f"Đã mở khoá {c['name']}"
        elif action == "capkhoa":
            key = "shc_" + secrets.token_urlsafe(24)
            c["key_hash"] = _h(key)
            msg = f"Đã cấp khoá mới cho {c['name']}. Gửi khoá này cho họ qua kênh riêng; khoá cũ hết hiệu lực"
        else:
            raise ValueError("Thao tác không hợp lệ")
        _log(d, "Huy (quản trị)", msg)
        _save(d)
    return {"text": msg + ".", "key": key}


# ------------------------------------------------------------------ CONSOLE NGƯỜI TẠO (người dùng khác)
import hashlib as _hashlib  # noqa: E402


def _h(key: str) -> str:
    return _hashlib.sha256(("superhuy-creator|" + key).encode()).hexdigest()


def creator_auth(key: str) -> dict:
    key = (key or "").strip()
    if not key.startswith("shc_") or len(key) > 80:
        raise PermissionError("Khoá truy cập không đúng")
    hh = _h(key)
    with _LOCK:
        d = _load()
    c = next((c for c in d["creators"].values() if c.get("key_hash") == hh), None)
    if not c:
        raise PermissionError("Khoá truy cập không đúng")
    if c.get("status") == "suspended":
        raise PermissionError("Tài khoản người tạo đang bị tạm khoá. Liên hệ superHuy để được hỗ trợ.")
    return c


def creator_signup(name: str, email: str, bio: str = "") -> dict:
    from agents import leads
    name, email = _clean(name, 60), _clean(email, 254).lower()
    if len(name) < 2:
        raise ValueError("Cần tên hiển thị (ít nhất 2 ký tự)")
    if not leads.EMAIL_RE.match(email):
        raise ValueError("Email chưa đúng")
    key = "shc_" + secrets.token_urlsafe(24)
    with _LOCK:
        d = _ensure(_load())
        if any(c.get("email") == email for c in d["creators"].values()):
            raise ValueError("Email này đã có tài khoản người tạo. Dùng khoá truy cập đã lưu, hoặc liên hệ superHuy để cấp lại.")
        if len(d["creators"]) >= 2000:
            raise ValueError("Đang tạm dừng nhận người tạo mới")
        cid = "c" + secrets.token_hex(5)
        d["creators"][cid] = {"id": cid, "name": name, "handle": _slug(name)[:30], "email": email, "bio": _clean(bio, 300),
                              "key_hash": _h(key), "status": "active", "created": _now(), "ai_uses": {}}
        _log(d, name, "Đăng ký người tạo")
        _save(d)
    try:
        leads.add(email, "market:nguoi-tao", "Người tạo Marketplace")
    except Exception:
        pass
    return {"key": key, "creator": {"id": cid, "name": name}}


def creator_ai_ok(c: dict, limit: int = 30) -> None:
    """Giới hạn số lần dùng AI đóng gói mỗi ngày cho mỗi người tạo."""
    today = dt.date.today().isoformat()
    with _LOCK:
        d = _load()
        cc = d["creators"].get(c["id"])
        u = cc.setdefault("ai_uses", {})
        n = u.get(today, 0)
        if n >= limit:
            raise ValueError("Hôm nay đã dùng hết lượt AI đóng gói, mai thử lại nhé")
        cc["ai_uses"] = {today: n + 1}
        _save(d)


def creator_console(c: dict) -> dict:
    with _LOCK:
        d = _load()
    own = [x for x in d["listings"].values() if x["creator"].get("id") == c["id"]]
    items = []
    for x in sorted(own, key=lambda x: x["updated"], reverse=True):
        rv = x.get("reviews") or []
        items.append(_summary(x) | {"review_note": x.get("review_note", ""), "reviews": rv[-5:][::-1]})
    return {"creator": {k: c.get(k) for k in ("name", "handle", "email", "bio", "created")},
            "stats": {"products": len(own), "published": sum(1 for x in own if x["status"] == "published"),
                      "review": sum(1 for x in own if x["status"] == "review"), "installs": sum(x.get("installs", 0) for x in own),
                      "interest": sum(x.get("interest", 0) for x in own)},
            "items": items, "cats": CATS, "types": TYPES}


def creator_get(c: dict, lid: str) -> dict:
    with _LOCK:
        d = _load()
    x = d["listings"].get(lid)
    if not x or x["creator"].get("id") != c["id"]:
        raise ValueError("Không tìm thấy sản phẩm")
    r = studio_body(lid)
    r["own"] = True
    r["review_note"] = x.get("review_note", "")
    return r


def creator_save(c: dict, data: dict) -> dict:
    """Người tạo lưu nháp hoặc gửi duyệt (mọi bản gửi đều qua chủ nhân duyệt trước khi lên kệ)."""
    t = data.get("type") if data.get("type") in TYPES else ""
    if not t:
        raise ValueError("Chọn loại sản phẩm")
    p = {"type": t, "name": _clean(data.get("name"), 80), "tagline": _clean(data.get("tagline"), 160),
         "description": _clean(data.get("description"), 4000), "body": str(data.get("body") or "")[:20000]}
    submit = bool(data.get("submit"))
    if submit:
        issues = _validate(p)
        if issues:
            raise ValueError("Chưa gửi duyệt được: " + " ".join(issues))
    content = _content_from(t, p["body"]) if p["body"].strip() else {}
    status = "review" if submit else "draft"
    lid = _clean(data.get("lid"), 20)
    with _LOCK:
        d = _load()
        if lid:
            x = d["listings"].get(lid)
            if not x or x["creator"].get("id") != c["id"]:
                raise ValueError("Không tìm thấy sản phẩm")
            was_pub = x["status"] == "published"
            x.update({k: p[k] for k in ("name", "tagline", "description")})
            x["category"] = data.get("category") if data.get("category") in CATS else x["category"]
            x["price"] = max(0, int(data.get("price") or 0))
            x["tags"] = [t2.strip()[:30] for t2 in str(data.get("tags") or "").split(",") if t2.strip()][:6]
            if content:
                x["content"] = content
            if submit:
                x["status"] = "review"
                if was_pub:
                    x["version"] = _clean(data.get("version"), 12) or x["version"]
                    x["whats_new"] = _clean(data.get("whats_new"), 600) or x.get("whats_new", "")
            x["updated"] = _now()
        else:
            if sum(1 for v in d["listings"].values() if v["creator"].get("id") == c["id"]) >= 50:
                raise ValueError("Mỗi người tạo tối đa 50 sản phẩm")
            x = _mk({"type": t, "name": p["name"] or "Sản phẩm chưa đặt tên", "tagline": p["tagline"], "description": p["description"],
                     "category": data.get("category"), "price": data.get("price") or 0, "content": content,
                     "tags": [t2.strip() for t2 in str(data.get("tags") or "").split(",") if t2.strip()]},
                    {"id": c["id"], "name": c["name"], "handle": c["handle"]}, status)
            d["listings"][x["id"]] = x
        x["submitter"] = {"email": c["email"], "name": c["name"]}
        _log(d, c["name"], ("Gửi duyệt" if submit else "Lưu nháp") + f" “{x['name']}”")
        _save(d)
    if submit:
        try:
            from core import security
            security.alert_once(f"mk:{x['id']}:{x['updated']}", f"🛍 Marketplace có sản phẩm chờ duyệt: “{x['name']}” của {c['name']}. "
                                "Duyệt trong app › Marketplace › Quản trị.", every=10**9)
        except Exception:
            pass
    return {"ok": True, "id": x["id"], "status": status,
            "text": "Đã gửi duyệt. superHuy sẽ xem và phản hồi trong console." if submit else "Đã lưu nháp."}
