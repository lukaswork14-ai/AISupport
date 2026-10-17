"""Xưởng Tài sản số superYou (chỉ chủ sàn). Đặc tả: docs/xuong-tai-san-so.md (anh Huy duyệt 17/10/2026).

Xưởng chỉ làm tài sản giúp người dùng giỏi lên theo thời gian: Skill, Second Brain, OS theo vai trò; xếp theo hai trục ngành
(industry) và vai trò (role). Nguồn: kho skill/prompt mã nguồn mở trên GitHub (chỉ repo có giấy phép rõ), kho template
Obsidian/Notion công khai, khung làm việc theo vai trò, sản phẩm đang bán chạy trên chính chợ.

Mỗi nguồn có điểm nguồn 0–100 theo 4 tiêu chí: tăng năng suất ngay (30) · làm Second Brain thông minh dần (25) ·
cài một chạm vào superYou (20) · giấy phép cho phép làm lại (25; không rõ = 0 và loại). Dưới 60 không hiện nút Clone.

Mã quét app iOS/Mac/Product Hunt cũ giữ sau cờ LEGACY_APP_SCAN (tắt), không còn trong giao diện.
"""
import datetime as dt
import html
import json
import os
import re
import threading
import time

import requests

from config import DATA_DIR

FILE = DATA_DIR / "factory.json"
_LOCK = threading.Lock()
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
_cache: dict[str, tuple[float, object]] = {}
LEGACY_APP_SCAN = False  # quét App Store / Product Hunt: bỏ khỏi Xưởng theo đặc tả, mã giữ lại phía dưới

SOURCES = {"github": "Kho skill & prompt mở", "template": "Template Obsidian / Notion", "framework": "Khung làm việc theo vai trò", "market": "Bán chạy trên chợ"}
INDUSTRIES = {"tmdt-pod": "TMĐT & POD", "ban-le": "Bán lẻ", "luat": "Luật", "tai-chinh-ke-toan": "Tài chính & kế toán", "marketing-agency": "Marketing agency",
              "giao-duc": "Giáo dục", "bat-dong-san": "Bất động sản", "san-xuat": "Sản xuất", "dich-vu": "Dịch vụ", "khac": "Khác"}
ROLES = {"ceo-chu-dn": "CEO / chủ doanh nghiệp", "quan-ly": "Quản lý", "sales": "Sales", "marketing": "Marketing", "van-hanh": "Vận hành",
         "tai-chinh": "Tài chính", "nhan-su": "Nhân sự", "solopreneur": "Solopreneur", "chuyen-vien": "Chuyên viên"}
KINDS = {"skill": "Skill", "brain": "Second Brain", "pack": "OS theo vai trò"}
# Giấy phép cho phép làm lại (viết lại hoàn toàn, ghi nguồn). Không có trong danh sách = không rõ = loại.
LICENSE_OK = {"MIT": "MIT", "Apache-2.0": "Apache 2.0", "CC-BY-4.0": "CC BY 4.0", "CC0-1.0": "CC0", "BSD-2-Clause": "BSD 2", "BSD-3-Clause": "BSD 3",
              "Unlicense": "Unlicense", "khung-cong-khai": "Khung công khai",
              "superyou": "Chính chủ superYou"}
MIN_SCORE = 60

# Khung làm việc nổi tiếng theo vai trò: ý tưởng/phương pháp là tri thức công khai; sản phẩm phải viết lại bằng lời mình,
# không dùng tên đã đăng ký nhãn hiệu làm tên sản phẩm (trademark=True -> Kiểm duyệt kiểm tra tên).
FRAMEWORKS = [
    {"id": "okr", "name": "OKR: mục tiêu và kết quả then chốt", "role": "ceo-chu-dn", "industry": "khac", "kind": "pack", "trademark": False,
     "summary": "Đặt 3 mục tiêu quý, mỗi mục tiêu 3 kết quả đo được; check-in hằng tuần, chấm 0–1 cuối quý.",
     "body": "Mục tiêu (Objective) là đích định tính truyền cảm hứng. Kết quả then chốt (Key Result) là số đo được, 3 cái mỗi mục tiêu. "
             "Check-in tuần: tự tin 1–10 cho từng KR, việc cản trở, việc tuần tới. Cuối quý chấm 0–1, 0,7 là tốt.",
     "questions": ["Tuần này KR nào đang chậm?", "Viết OKR quý cho đội bán hàng 5 người", "OKR của tôi có đo được không?"]},
    {"id": "4dx", "name": "4 kỷ luật thực thi (4DX)", "role": "quan-ly", "industry": "khac", "kind": "skill", "trademark": True,
     "summary": "Tập trung một mục tiêu tối quan trọng, đo chỉ số dẫn dắt, bảng điểm hấp dẫn, họp trách nhiệm tuần.",
     "body": "Chọn một mục tiêu tối quan trọng (WIG). Đo chỉ số dẫn dắt (lead) thay vì chỉ số kết quả (lag). Bảng điểm ai cũng thấy. "
             "Họp 20 phút mỗi tuần: cam kết tuần trước, bảng điểm, cam kết tuần này.",
     "questions": ["Chỉ số dẫn dắt cho mục tiêu tăng doanh thu 20% là gì?", "Soạn kịch bản họp trách nhiệm 20 phút", "Mục tiêu tối quan trọng quý này nên là gì?"]},
    {"id": "eos", "name": "Hệ điều hành doanh nghiệp (EOS)", "role": "ceo-chu-dn", "industry": "dich-vu", "kind": "pack", "trademark": True,
     "summary": "Tầm nhìn, con người, dữ liệu, vấn đề, quy trình, lực kéo: họp cấp 10 (L10) mỗi tuần, đá tảng 90 ngày.",
     "body": "Sáu thành phần: Tầm nhìn (1 trang), Con người (đúng người đúng ghế), Dữ liệu (bảng điểm 5–15 số), Vấn đề (danh sách và giải quyết), "
             "Quy trình (ghi 20% quy trình tạo 80% giá trị), Lực kéo (đá tảng 90 ngày, họp tuần 90 phút).",
     "questions": ["Soạn bảng điểm tuần cho công ty dịch vụ 15 người", "Đá tảng 90 ngày của tôi nên là gì?", "Họp tuần nên theo khung nào?"]},
    {"id": "sales-playbook", "name": "Sổ tay bán hàng tư vấn (SPIN + MEDDIC)", "role": "sales", "industry": "dich-vu", "kind": "pack", "trademark": True,
     "summary": "Khám phá nhu cầu bằng câu hỏi tình huống, vấn đề, hệ quả, lợi ích; chấm cơ hội theo số liệu, người quyết, tiêu chí, quy trình.",
     "body": "Khám phá: hỏi tình huống, vấn đề, hệ quả, lợi ích thay vì chào hàng. Chấm cơ hội: số liệu lợi ích, người ký, tiêu chí mua, quy trình mua, "
             "nỗi đau, người ủng hộ. Theo đuổi: tối đa 120 từ, một lợi ích, một câu hỏi, một bước tiếp theo.",
     "questions": ["Khách này có đáng theo đuổi không?", "Soạn 5 câu hỏi khám phá cho khách chủ shop", "Viết thư theo đuổi sau buổi demo"]},
    {"id": "para", "name": "Second Brain theo PARA", "role": "solopreneur", "industry": "khac", "kind": "brain", "trademark": False,
     "summary": "Sắp xếp ghi chú theo Dự án, Lĩnh vực, Tài nguyên, Lưu trữ; chưng cất tiến dần; xem lại tuần.",
     "body": "Bốn ngăn: Dự án (có hạn), Lĩnh vực (trách nhiệm dài hạn), Tài nguyên (chủ đề quan tâm), Lưu trữ. Ghi chú mới vào Inbox, "
             "xem lại tuần để phân ngăn. Chưng cất: tô đậm, tóm tắt, viết lại bằng lời mình.",
     "questions": ["Ghi chú này nên vào ngăn nào?", "Xem lại tuần nên hỏi gì?", "Tóm tắt dự án X từ ghi chú của tôi"]},
    {"id": "cash13", "name": "Dự báo dòng tiền 13 tuần", "role": "tai-chinh", "industry": "tai-chinh-ke-toan", "kind": "skill", "trademark": False,
     "summary": "Bảng thu chi theo tuần 13 tuần tới, đánh dấu tuần âm, hành động trước 2 tuần.",
     "body": "Mỗi tuần: tiền đầu kỳ + thu dự kiến − chi cố định − chi biến đổi − thuế = tiền cuối kỳ. Tuần âm cần hành động trước 2 tuần: giục công nợ, "
             "lùi chi, vay ngắn.",
     "questions": ["Tuần nào tôi sắp âm tiền?", "Nếu mất khách lớn nhất thì sao?", "Runway còn mấy tháng?"]},
    {"id": "sop-ops", "name": "Viết SOP và checklist vận hành", "role": "van-hanh", "industry": "san-xuat", "kind": "skill", "trademark": False,
     "summary": "Mẫu SOP một trang: mục đích, ai làm, bước, tiêu chí đạt, lỗi hay gặp; checklist ca.",
     "body": "SOP một trang: mục đích, người làm, điều kiện bắt đầu, các bước đánh số có tiêu chí đạt, lỗi hay gặp và cách xử lý, ai kiểm tra. "
             "Checklist ca: 5–12 mục, tick được, có ô ghi chú bất thường.",
     "questions": ["Viết SOP đóng gói đơn cho kho 3 người", "Checklist mở ca cho cửa hàng", "Lỗi nào hay gặp khi giao ca?"]},
    {"id": "hr-onboard", "name": "Onboarding 30-60-90 ngày", "role": "nhan-su", "industry": "dich-vu", "kind": "pack", "trademark": False,
     "summary": "Kế hoạch 30-60-90 cho nhân sự mới: học, làm, dẫn dắt; mốc kiểm tra và câu hỏi 1:1.",
     "body": "30 ngày: học sản phẩm, gặp 5 người, làm 1 việc nhỏ có người kèm. 60 ngày: tự làm việc chính, nhận phản hồi tuần. 90 ngày: đề xuất 1 cải tiến. "
             "1:1 mỗi 2 tuần: điều gì ổn, điều gì khó, cần gì.",
     "questions": ["Soạn kế hoạch 30-60-90 cho nhân viên sales mới", "Câu hỏi 1:1 tuần đầu nên hỏi gì?", "Dấu hiệu nhân sự mới không hợp?"]},
    {"id": "content-calendar", "name": "Lịch nội dung tuần cho agency", "role": "marketing", "industry": "marketing-agency", "kind": "skill", "trademark": False,
     "summary": "Trụ nội dung, lịch 7 ngày, mẫu brief, đo 3 số: tiếp cận, tương tác, chuyển đổi.",
     "body": "3–4 trụ nội dung theo mục tiêu khách. Lịch tuần: mỗi ngày 1 kênh chính. Brief: mục tiêu, khán giả, thông điệp, CTA, định dạng. "
             "Tuần sau xem 3 số: tiếp cận, tương tác, chuyển đổi; giữ 1 bỏ 1 thử 1.",
     "questions": ["Lập lịch nội dung tuần cho khách bán mỹ phẩm", "Brief video 30 giây cho shop giày", "Bài nào tuần trước đáng nhân rộng?"]},
    {"id": "pod-listing", "name": "Quy trình ra mắt sản phẩm POD", "role": "solopreneur", "industry": "tmdt-pod", "kind": "pack", "trademark": False,
     "summary": "Nghiên cứu ngách, thiết kế, listing chuẩn SEO, giá, quảng cáo thử 7 ngày, quyết định giữ hay bỏ.",
     "body": "Ngách: từ khoá có nhu cầu, cạnh tranh thấp. Thiết kế 5 mẫu. Listing: tiêu đề có từ khoá, 13 thẻ, mô tả lợi ích. Giá: biên gộp sau phí sàn tối thiểu 30%. "
             "Quảng cáo thử 7 ngày, ROAS tối thiểu để không lỗ; giữ mẫu có đơn, bỏ mẫu không.",
     "questions": ["Viết listing cho áo chủ đề cà phê", "Giá bán để biên gộp 30% là bao nhiêu?", "Mẫu nào nên bỏ sau 7 ngày?"]},
]

# Từ khoá phân loại ngành / vai trò (tiếng Việt và tiếng Anh, không dấu)
_IND_KW = {"tmdt-pod": ["pod", "print on demand", "etsy", "shopee", "amazon", "ecommerce", "e-commerce", "tmdt", "listing", "dropship"],
           "ban-le": ["retail", "ban le", "cua hang", "store", "pos", "ton kho", "inventory"],
           "luat": ["legal", "law", "luat", "hop dong", "contract", "lawyer"],
           "tai-chinh-ke-toan": ["finance", "accounting", "ke toan", "tai chinh", "cash", "dong tien", "budget", "invoice", "tax", "thue"],
           "marketing-agency": ["agency", "marketing", "content", "seo", "ads", "quang cao", "social", "brand", "copywriting"],
           "giao-duc": ["education", "giao duc", "teacher", "course", "khoa hoc", "student", "learning", "hoc sinh", "giang vien"],
           "bat-dong-san": ["real estate", "bat dong san", "property", "landlord", "nha dat"],
           "san-xuat": ["manufactur", "san xuat", "factory", "production", "nha may", "supply chain", "sop"],
           "dich-vu": ["service", "dich vu", "consult", "tu van", "agency", "client"]}
_ROLE_KW = {"ceo-chu-dn": ["ceo", "founder", "chu doanh nghiep", "owner", "strategy", "chien luoc", "okr", "board"],
            "quan-ly": ["manager", "quan ly", "team lead", "leadership", "1:1", "one-on-one", "meeting", "hop"],
            "sales": ["sales", "ban hang", "crm", "pipeline", "lead", "deal", "khach hang", "outreach"],
            "marketing": ["marketing", "content", "seo", "campaign", "social media", "brand", "ads"],
            "van-hanh": ["operations", "van hanh", "sop", "process", "quy trinh", "checklist", "logistics"],
            "tai-chinh": ["finance", "cfo", "tai chinh", "cash", "budget", "ke toan", "accounting"],
            "nhan-su": ["hr", "nhan su", "hiring", "recruit", "onboarding", "tuyen dung", "performance review"],
            "solopreneur": ["solopreneur", "freelance", "indie", "creator", "one person", "personal", "second brain", "pkm", "productivity"],
            "chuyen-vien": ["analyst", "engineer", "developer", "chuyen vien", "specialist", "research", "coding", "data"]}


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    d.setdefault("projects", {})
    d.setdefault("cloned", {})
    d.setdefault("notes", [])
    d.setdefault("stars", [])
    d.setdefault("suggest", {})
    return d


def _save(d: dict):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(FILE)


def _get(url: str, ttl: int = 1800, params: dict | None = None):
    key = url + json.dumps(params or {}, sort_keys=True)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < ttl:
        return hit[1]
    h = dict(UA)
    if "api.github.com" in url and os.environ.get("GITHUB_TOKEN"):  # tuỳ chọn: nâng hạn mức tìm kiếm; không bao giờ in giá trị
        h["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    r = requests.get(url, params=params, headers=h, timeout=20)
    r.raise_for_status()
    try:
        v = r.json()
    except ValueError:
        v = r.text
    _cache[key] = (time.time(), v)
    if len(_cache) > 300:
        for k in sorted(_cache, key=lambda k: _cache[k][0])[:80]:
            _cache.pop(k, None)
    return v


def _clean(s) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(s or "")))).strip()


def _fold(s: str) -> str:
    """Bỏ dấu tiếng Việt, thường hoá để so khớp từ khoá."""
    import unicodedata
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return s.replace("đ", "d")


# ------------------------------------------------------------------ phân loại và chấm điểm nguồn
def classify(text: str, industry: str = "", role: str = "") -> tuple[str, str]:
    """Đoán ngành và vai trò từ văn bản (tên + mô tả + chủ đề). Giá trị truyền vào hợp lệ thì giữ nguyên."""
    t = _fold(text)
    hit = lambda ws: sum(1 for w in ws if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t))  # noqa: E731  khớp nguyên từ
    if industry not in INDUSTRIES:
        best = max(_IND_KW, key=lambda k: hit(_IND_KW[k]))
        industry = best if hit(_IND_KW[best]) else "khac"
    if role not in ROLES:
        best = max(_ROLE_KW, key=lambda k: hit(_ROLE_KW[k]))
        role = best if hit(_ROLE_KW[best]) else "chuyen-vien"
    return industry, role


_PROD_KW = ["skill", "prompt", "playbook", "workflow", "checklist", "sop", "template", "framework", "guide", "how to", "huong dan", "quy trinh",
            "agent", "assistant", "automation", "system prompt", "instructions"]
_BRAIN_KW = ["knowledge", "notes", "note", "second brain", "pkm", "obsidian", "notion", "wiki", "zettelkasten", "vault", "docs", "tri thuc", "ghi chu",
             "handbook", "library", "collection", "awesome"]
_INSTALL_KW = ["skill.md", "markdown", ".md", "prompt", "text", "template", "checklist", "notes", "agent skills", "claude", "chatgpt", "cursor"]


def score_source(x: dict) -> dict:
    """Điểm nguồn 0–100 theo 4 tiêu chí của đặc tả. Trả về {score, parts, reasons, clone_ok}."""
    t = _fold(" ".join(str(x.get(k) or "") for k in ("name", "summary", "cat", "topics", "kind")))
    lic = str(x.get("license") or "")
    # 1. Tăng năng suất ngay (30): có hướng dẫn/prompt/checklist dùng được ngay; nguồn được nhiều người dùng.
    hits = sum(1 for w in _PROD_KW if w in t)
    pop = x.get("ratings") or x.get("installs") or 0
    p1 = min(30, 8 * min(hits, 3) + (6 if pop >= 1000 else 3 if pop >= 100 else 0))
    if x.get("src") == "framework":
        p1 = max(p1, 24)
    if x.get("src") == "market":  # đã bán được trên chợ: năng suất đã được người mua kiểm chứng
        p1 = max(p1, 20 + (6 if (x.get("sales") or 0) >= 3 else 3 if (x.get("installs") or 0) >= 1 else 0))
    # 2. Làm Second Brain thông minh dần (25): có tri thức/ghi chú/template để tích luỹ.
    bh = sum(1 for w in _BRAIN_KW if w in t)
    p2 = min(25, 9 * min(bh, 2) + (7 if x.get("kind") in ("brain", "pack") else 0))
    # 3. Cài một chạm (20): nội dung dạng văn bản/markdown/prompt -> thành skill/notes/pack không cần code.
    ih = sum(1 for w in _INSTALL_KW if w in t)
    p3 = 20 if x.get("src") in ("framework", "market") else min(20, 7 * min(ih, 2) + (6 if (x.get("cat") or "").lower() in ("markdown", "repo", "") else 0))
    if x.get("src") in ("github", "template") and (x.get("cat") or "").lower() not in ("markdown", "repo", "", "jupyter notebook", "html", "text"):
        p3, p1, p2 = min(p3, 6), min(p1, 15), min(p2, 12)  # repo mã nguồn: phải rút văn bản ra rồi viết lại, khó cài một chạm và khó dùng ngay
    # 4. Giấy phép (25): không rõ = 0 và loại.
    p4 = 25 if lic in LICENSE_OK else 0
    parts = {"nang_suat": p1, "brain": p2, "cai_mot_cham": p3, "giay_phep": p4}
    score = sum(parts.values())
    reasons = []
    if not p4:
        reasons.append("Giấy phép không rõ hoặc không cho phép làm lại: loại.")
    if p1 < 15:
        reasons.append("Chưa thấy hướng dẫn/prompt dùng được ngay.")
    if p2 < 9:
        reasons.append("Ít tri thức để tích luỹ vào Second Brain.")
    if p3 < 10:
        reasons.append("Khó cài một chạm (cần viết lại từ mã nguồn).")
    return {"score": score, "parts": parts, "reasons": reasons, "clone_ok": bool(p4) and score >= MIN_SCORE, "license_label": LICENSE_OK.get(lic, "Không rõ")}


def _finish(items: list[dict], d: dict | None = None) -> list[dict]:
    d = d or _load()
    for it in items:
        it["industry"], it["role"] = classify(" ".join(str(it.get(k) or "") for k in ("name", "summary", "topics", "cat")), it.get("industry", ""), it.get("role", ""))
        it["kind"] = it.get("kind") if it.get("kind") in KINDS else _guess_kind(it)
        it.update(score_source(it))
        it["cloned"] = it["key"] in d["cloned"]
        it["project"] = d["cloned"].get(it["key"], "")
        it["starred"] = it["key"] in d["stars"]
    return items


def _guess_kind(it: dict) -> str:
    t = _fold(f"{it.get('name', '')} {it.get('summary', '')} {it.get('topics', '')}")
    if any(w in t for w in ("os ", "operating system", "playbook", "pack", "bo cong cu", "toolkit", "system")):
        return "pack"
    if any(w in t for w in _BRAIN_KW):
        return "brain"
    return "skill"


# ------------------------------------------------------------------ nguồn
def _gh_row(r: dict, i: int, src: str) -> dict:
    lic = (r.get("license") or {}).get("spdx_id") or ""
    return {"key": f"{src}:{r['full_name']}", "src": src, "id": r["full_name"], "name": r["name"], "dev": r["owner"]["login"],
            "icon": r["owner"].get("avatar_url", ""), "cat": r.get("language") or "Markdown", "price": LICENSE_OK.get(lic, lic or "Không rõ"),
            "rating": 0, "ratings": r.get("stargazers_count", 0), "summary": _clean(r.get("description") or "")[:240], "url": r["html_url"],
            "rank": i + 1, "license": lic if lic != "NOASSERTION" else "", "topics": " ".join(r.get("topics") or []), "updated": (r.get("pushed_at") or "")[:10]}


def _gh_search(query: str, limit: int, src: str) -> list[dict]:
    j = _get("https://api.github.com/search/repositories", params={"q": query, "sort": "stars", "order": "desc", "per_page": min(limit, 50)}, ttl=3600)
    if isinstance(j, str):
        j = json.loads(j)
    return [_gh_row(r, i, src) for i, r in enumerate(j.get("items") or [])]


def _gh_multi(q: str, topics: list[str], extra: str, limit: int, src: str, stars: int) -> list[dict]:
    """q có: tìm theo từ khoá. q trống: gom theo từng topic (GitHub không OR được giữa các qualifier), bỏ trùng."""
    if q:
        return _gh_search(f"{q} {extra} in:name,description,topics stars:>{stars}", limit, src)
    out, seen = [], set()
    for t in topics:
        for r in _gh_search(f"topic:{t} stars:>{stars}", max(10, limit // len(topics) + 5), src):
            if r["key"] not in seen:
                seen.add(r["key"])
                out.append(r)
    out.sort(key=lambda r: -r["ratings"])
    for i, r in enumerate(out):
        r["rank"] = i + 1
    return out[:limit]


def _github(q: str, limit: int) -> list[dict]:
    return _gh_multi(q, ["prompts", "agent-skills", "system-prompts", "prompt-engineering"], "prompts", limit, "github", 50)


def _templates(q: str, limit: int) -> list[dict]:
    return _gh_multi(q, ["obsidian-template", "obsidian-vault", "notion-template", "second-brain"], "template", limit, "template", 20)


def _frameworks(q: str, industry: str, role: str) -> list[dict]:
    out = []
    fq = _fold(q)
    for i, f in enumerate(FRAMEWORKS):
        if fq and fq not in _fold(f["name"] + " " + f["summary"]):
            continue
        out.append({"key": f"framework:{f['id']}", "src": "framework", "id": f["id"], "name": f["name"], "dev": "Tri thức công khai", "icon": "", "cat": "Khung làm việc",
                    "price": LICENSE_OK["khung-cong-khai"], "rating": 0, "ratings": 0, "summary": f["summary"], "url": "", "rank": i + 1, "license": "khung-cong-khai",
                    "industry": f["industry"], "role": f["role"], "kind": f["kind"], "trademark": f.get("trademark", False), "topics": "framework playbook checklist"})
    return out


def _market_best(q: str, limit: int) -> list[dict]:
    from agents import market
    rows = []
    for x in market.catalog(q=q)["items"]:
        if x.get("status") not in (None, "published"):
            continue
        own = bool((x.get("creator") or {}).get("official") or (x.get("creator") or {}).get("owner"))
        rows.append({"key": f"market:{x['id']}", "src": "market", "id": x["id"], "name": x["name"], "dev": (x.get("creator") or {}).get("name", ""), "icon": "",
                     "cat": x.get("type_label", ""), "price": "Chính chủ" if own else "Của người tạo khác", "rating": x.get("rating", 0), "ratings": x.get("installs", 0),
                     "installs": x.get("installs", 0), "sales": x.get("sales", 0), "summary": x.get("tagline", ""), "url": f"/market?q={x['slug']}", "rank": 0,
                     "license": "superyou" if own else "", "kind": "pack" if x.get("type") == "pack" else "brain" if x.get("type") == "brain" else "skill",
                     "topics": f"{x.get('cat_label', '')} {' '.join(x.get('tags') or [])}", "color": x.get("color"), "industry": x.get("industry", ""), "role": x.get("role", "")})
    rows.sort(key=lambda r: (r["sales"], r["installs"], r["rating"]), reverse=True)
    for i, r in enumerate(rows):
        r["rank"] = i + 1
    return rows[:limit]


def scan(src: str = "github", q: str = "", industry: str = "", role: str = "", limit: int = 30, min_score: int = 0, **_legacy) -> dict:
    """Quét một nguồn, chấm điểm, phân loại ngành/vai trò. Tham số cũ (country, chart, genre) được bỏ qua."""
    src = src if src in SOURCES else "github"
    limit = max(5, min(int(limit or 30), 50))
    q = (q or "").strip()[:80]
    try:
        if src == "github":
            items = _github(q, limit)
        elif src == "template":
            items = _templates(q, limit)
        elif src == "framework":
            items = _frameworks(q, industry, role)
        else:
            items = _market_best(q, limit)
    except requests.RequestException as e:
        raise ValueError(f"Chưa lấy được dữ liệu từ {SOURCES[src]}: {str(e)[:120]}")
    items = _finish(items)
    if industry in INDUSTRIES:
        items = [i for i in items if i["industry"] == industry]
    if role in ROLES:
        items = [i for i in items if i["role"] == role]
    if min_score:
        items = [i for i in items if i["score"] >= int(min_score)]
    items.sort(key=lambda i: (-i["score"], i.get("rank") or 0))
    label = SOURCES[src] + (f" · tìm “{q}”" if q else "") + (f" · {INDUSTRIES[industry]}" if industry in INDUSTRIES else "") + (f" · {ROLES[role]}" if role in ROLES else "")
    ok = sum(1 for i in items if i["clone_ok"])
    return {"text": f"{label}: {len(items)} nguồn, {ok} đủ điểm vào xưởng.", "items": items, "label": label, "min_score": MIN_SCORE,
            "filters": {"sources": SOURCES, "industries": INDUSTRIES, "roles": ROLES, "kinds": KINDS}}


def detail(key: str, **_legacy) -> dict:
    """Chi tiết một nguồn: mô tả, giấy phép, điểm từng tiêu chí, ngành/vai trò, câu hỏi mẫu."""
    src, _, ident = (key or "").partition(":")
    if src in ("github", "template"):
        j = _get(f"https://api.github.com/repos/{ident}", ttl=3600)
        if isinstance(j, str):
            j = json.loads(j)
        readme = ""
        try:
            from agents import web_tools
            readme = web_tools.read(f"https://github.com/{ident}", 6000).get("text", "")
        except Exception:
            pass
        row = _gh_row(j | {"full_name": ident, "name": j.get("name", ident), "owner": j.get("owner") or {"login": ""}, "html_url": j.get("html_url", "")}, 0, src)
        row.update({"description": readme[:6000], "shots": [], "reviews": [], "dev_apps": []})
    elif src == "framework":
        f = next((f for f in FRAMEWORKS if f["id"] == ident), None)
        if not f:
            raise ValueError("Không tìm thấy khung làm việc")
        row = _frameworks("", "", "")[FRAMEWORKS.index(f)] | {"description": f["body"], "questions": f["questions"], "shots": [], "reviews": [], "dev_apps": []}
    elif src == "market":
        from agents import market
        x = market.get_listing(ident)
        if not x:
            raise ValueError("Không tìm thấy sản phẩm trên chợ")
        row = next((r for r in _market_best("", 500) if r["id"] == ident), None) or {"key": key, "src": "market", "id": ident, "name": x["name"], "license": ""}
        c = x.get("content") or {}
        body = c.get("skill") or "\n\n".join(n.get("md", "") for n in c.get("notes") or []) or "\n".join(f"{s.get('agent')}.{s.get('action')}: {s.get('label', '')}" for s in c.get("steps") or [])
        row.update({"description": (x.get("description", "") + "\n\n" + body)[:6000], "shots": x.get("shots") or [], "reviews": x.get("reviews") or [], "dev_apps": [],
                    "examples": x.get("examples") or [], "listing_type": x.get("type")})
    elif LEGACY_APP_SCAN and src in ("ios", "mac", "ph"):
        row = _legacy_detail(src, ident, key)
    else:
        raise ValueError("Nguồn không hợp lệ")
    row = _finish([row])[0]
    d = _load()
    return row | {"kinds": KINDS, "industries": INDUSTRIES, "roles": ROLES, "license_ok": list(LICENSE_OK), "notes": d["notes"][-20:], "min_score": MIN_SCORE}


def star(key: str) -> dict:
    with _LOCK:
        d = _load()
        if key in d["stars"]:
            d["stars"].remove(key)
            on = False
        else:
            d["stars"].append(key)
            on = True
        _save(d)
    return {"text": "Đã lưu vào danh sách theo dõi." if on else "Đã bỏ theo dõi.", "starred": on}


def save_note(text: str) -> dict:
    text = (text or "").strip()[:600]
    if not text:
        raise ValueError("Ghi chú trống")
    with _LOCK:
        d = _load()
        if text not in d["notes"]:
            d["notes"].append(text)
            d["notes"] = d["notes"][-40:]
        _save(d)
    return {"text": "Đã lưu ghi chú để dùng lại.", "notes": d["notes"][-20:]}


# ------------------------------------------------------------------ gợi ý tuần (thứ Ba 06:30, Product Lead gắn job trong main.py)
def weekly_suggest(notify: bool = True) -> dict:
    """Quét các nguồn, chọn 5 nguồn điểm cao nhất chưa clone, lưu để hiện ở HQ › Xưởng và nhắn Telegram một dòng."""
    pool = []
    for src in SOURCES:
        try:
            pool += [i for i in scan(src, limit=30)["items"] if i["clone_ok"] and not i["cloned"]]
        except Exception:
            continue
    seen, top = set(), []
    for it in sorted(pool, key=lambda i: -i["score"]):
        if it["key"] in seen:
            continue
        seen.add(it["key"])
        top.append({k: it.get(k) for k in ("key", "src", "name", "summary", "score", "industry", "role", "kind", "url", "license_label")})
        if len(top) == 5:
            break
    with _LOCK:
        d = _load()
        d["suggest"] = {"at": _now(), "items": top}
        _save(d)
    line = "🏭 Xưởng tuần này gợi ý: " + "; ".join(f"{t['name']} ({t['score']}đ)" for t in top) + ". Mở HQ › Xưởng để clone." if top else "🏭 Xưởng tuần này chưa tìm được nguồn đủ điểm."
    if notify:
        try:
            from core import notify as _n
            _n.send(text=line)
        except Exception:
            pass
    return {"text": line, "items": top}


def suggestions() -> dict:
    d = _load()
    return d.get("suggest") or {"at": "", "items": []}


# ------------------------------------------------------------------ dự án (đội clone ghi vào đây; xem agents/factory_team.py)
PSTATUS = {"nhap": "Nháp", "dang_chay": "Đội đang làm", "cho_duyet": "Chờ anh duyệt", "da_len_cho": "Đã lên chợ", "bo": "Bỏ",
           "y_tuong": "Ý tưởng", "dang_dung": "Đang dựng", "da_ra_mat": "Đã ra mắt"}


def projects() -> dict:
    d = _load()
    rows = sorted(d["projects"].values(), key=lambda p: p.get("updated", ""), reverse=True)
    return {"items": [{k: p.get(k) for k in ("id", "name", "pitch", "kind", "industry", "role", "status", "source", "created", "updated", "listing", "step", "test_score", "verdict")}
                      for p in rows], "statuses": PSTATUS, "kinds": KINDS, "industries": INDUSTRIES, "roles": ROLES, "stars": d["stars"][-50:], "suggest": d.get("suggest") or {}}


def project(pid: str) -> dict:
    d = _load()
    p = d["projects"].get(pid)
    if not p:
        raise ValueError("Không tìm thấy dự án")
    return p | {"statuses": PSTATUS, "kinds": KINDS, "industries": INDUSTRIES, "roles": ROLES}


def project_set(pid: str, status: str = "", note: str = "") -> dict:
    with _LOCK:
        d = _load()
        p = d["projects"].get(pid)
        if not p:
            raise ValueError("Không tìm thấy dự án")
        if status in PSTATUS:
            p["status"] = status
        if note:
            p["notes"] = (p.get("notes", "") + "\n" + note.strip()[:800]).strip()
        p["updated"] = _now()
        _save(d)
    return {"text": f"Đã cập nhật “{p['name']}”: {PSTATUS.get(p['status'])}."}


def project_delete(pid: str) -> dict:
    with _LOCK:
        d = _load()
        p = d["projects"].pop(pid, None)
        if p:
            d["cloned"] = {k: v for k, v in d["cloned"].items() if v != pid}
        _save(d)
    return {"text": "Đã xoá dự án." if p else "Không có dự án này."}


def clone(key: str, notes: str = "", **_legacy) -> dict:
    """Anh bấm Clone: giao cho đội BA → PO → Dev → Designer → Tester → Kiểm duyệt (agents/factory_team.py)."""
    try:
        from agents import factory_team
    except ImportError:
        raise ValueError("Đội clone chưa được lắp vào bản này (agents/factory_team.py). Chờ bản phát hành tiếp theo.")
    return factory_team.start(key, notes)


def price_reco(pid: str) -> dict:
    """Gợi ý bậc giá cho dự án (pay.price_reco trên nội dung Dev đã viết)."""
    from agents import pay
    d = _load()
    p = d["projects"].get(pid)
    if not p:
        raise ValueError("Không tìm thấy dự án")
    dev = (p.get("steps") or {}).get("dev", {}).get("out") or {}
    typ = {"skill": "skill", "brain": "brain", "pack": "pack"}.get(p.get("kind"), "skill")
    content = dev.get("content") or {"skill": dev.get("body", "")}
    fake = {"type": typ, "name": p["name"], "category": dev.get("category", "nang-suat"), "content": content}
    r = pay.price_reco(fake)
    r["category"] = fake["category"]
    return r


# ------------------------------------------------------------------ mã cũ: App Store / Product Hunt (tắt, giữ để tham khảo)
COUNTRIES = {"vn": "Việt Nam", "us": "Mỹ"}


def _apple_row(store: str, x: dict, rank: int = 0) -> dict:
    return {"key": f"{store}:{x.get('trackId')}", "src": store, "id": str(x.get("trackId")), "name": x.get("trackName", ""),
            "dev": x.get("artistName", ""), "icon": x.get("artworkUrl100") or x.get("artworkUrl60", ""), "cat": x.get("primaryGenreName", ""),
            "price": x.get("formattedPrice", ""), "rating": round(x.get("averageUserRating") or 0, 1), "ratings": x.get("userRatingCount") or 0,
            "summary": _clean(x.get("description", ""))[:240], "url": x.get("trackViewUrl", ""), "rank": rank, "license": ""}


def _legacy_detail(src: str, ident: str, key: str) -> dict:
    if src in ("ios", "mac"):
        j = _get("https://itunes.apple.com/lookup", params={"id": ident, "country": "vn"})
        if isinstance(j, str):
            j = json.loads(j)
        res = j.get("results") or []
        if not res:
            raise ValueError("Không tìm thấy app")
        return _apple_row(src, res[0]) | {"description": res[0].get("description", "")[:6000], "shots": (res[0].get("screenshotUrls") or [])[:12], "reviews": [], "dev_apps": []}
    from agents import web_tools
    r = web_tools.read(ident, 6000)
    return {"key": key, "src": "ph", "id": ident, "name": r.get("title", ""), "dev": "", "icon": "", "cat": "Product Hunt", "url": ident, "license": "",
            "summary": "", "description": r.get("text", "")[:6000], "shots": [], "reviews": [], "dev_apps": []}
