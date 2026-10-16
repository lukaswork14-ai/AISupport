"""Xưởng sản phẩm số (Clone Factory) của phòng Phát triển sản phẩm số. Chỉ chủ nhân dùng.

Ý tưởng từ "app clone factory": quét sản phẩm đang thắng trên thị trường (bảng xếp hạng App Store iPhone/Mac,
GitHub Trending, Product Hunt), xem chi tiết (mô tả, ảnh, đánh giá, các app khác của nhà phát triển), rồi chọn
"Clone": AI viết bản thiết kế + prompt dựng sản phẩm của riêng anh, cho nền tảng anh chọn (skill/workflow/gói tri thức
trên superYou Marketplace, web app, app iPhone/Mac, Telegram Mini App).

Nguyên tắc clone: giữ ý tưởng và tính năng đã được thị trường kiểm chứng, làm tốt hơn ở những điểm người dùng phàn nàn,
nhưng giao diện, tên, thương hiệu, câu chữ và hình ảnh phải là của mình (không chép tài sản có bản quyền).
"""
import datetime as dt
import html
import json
import re
import secrets
import threading
import time

import requests

from config import DATA_DIR

FILE = DATA_DIR / "factory.json"
_LOCK = threading.Lock()
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"}
_cache: dict[str, tuple[float, object]] = {}

SOURCES = {"ios": "App Store iPhone", "mac": "Mac App Store", "github": "GitHub Trending", "ph": "Product Hunt"}
COUNTRIES = {"vn": "Việt Nam", "us": "Mỹ", "gb": "Anh", "jp": "Nhật", "kr": "Hàn Quốc", "sg": "Singapore", "th": "Thái Lan", "id": "Indonesia"}
CHARTS = {"free": "Miễn phí hàng đầu", "paid": "Trả phí hàng đầu", "grossing": "Doanh thu cao nhất"}
GENRES = {"": "Mọi danh mục", "6000": "Kinh doanh", "6007": "Năng suất", "6017": "Giáo dục", "6024": "Mua sắm", "6015": "Tài chính",
          "6002": "Tiện ích", "6012": "Phong cách sống", "6013": "Sức khoẻ", "6016": "Giải trí", "6005": "Mạng xã hội", "6008": "Ảnh và video"}
TARGETS = {
    "skill": "Skill trên superYou Marketplace",
    "workflow": "Workflow trên superYou Marketplace",
    "brain": "Gói tri thức (Second Brain) trên superYou Marketplace",
    "web": "Web app (PWA, chạy trên mọi máy)",
    "tma": "Telegram Mini App",
    "ios": "App iPhone (SwiftUI)",
    "mac": "App Mac (SwiftUI)",
}
OPTIONS = {
    "feature_clone": "Clone đủ tính năng và luồng dùng, giao diện hiện đại của riêng mình",
    "free_open": "Bản miễn phí, mở: bỏ gói thuê bao, mua trong app và khoá tính năng",
    "metadata": "Kèm metadata cửa hàng (mô tả, tính năng, thông số) dạng JSON",
    "vn_local": "Bản địa hoá cho thị trường Việt Nam (ngôn ngữ, thanh toán, thói quen)",
    "fix_pain": "Sửa các điểm người dùng phàn nàn trong đánh giá thấp",
    "ai_native": "AI-native: thêm trợ lý AI làm thay việc lặp lại",
}
CHIPS = ["Giao diện sáng/tối", "Lưu offline", "Phím tắt", "Nhập/xuất dữ liệu", "Bố cục chia đôi màn hình", "Đồng bộ Lark", "Đăng nhập bằng Telegram",
         "Thanh toán VietQR"]


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
    r = requests.get(url, params=params, headers=UA, timeout=20)
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


# ------------------------------------------------------------------ nguồn
def _apple_chart(store: str, cc: str, chart: str, genre: str, limit: int) -> list[dict]:
    kind = {"free": "topfree", "paid": "toppaid", "grossing": "topgrossing"}[chart]
    feed = f"{kind}{'macapps' if store == 'mac' else 'applications'}"
    g = f"/genre={genre}" if genre else ""
    j = _get(f"https://itunes.apple.com/{cc}/rss/{feed}/limit={limit}{g}/json")
    if isinstance(j, str):
        j = json.loads(j)
    out = []
    for i, e in enumerate((j.get("feed") or {}).get("entry") or []):
        imgs = e.get("im:image") or []
        out.append({"key": f"{store}:{e['id']['attributes']['im:id']}", "src": store, "id": e["id"]["attributes"]["im:id"],
                    "name": e["im:name"]["label"], "dev": (e.get("im:artist") or {}).get("label", ""),
                    "icon": imgs[-1]["label"] if imgs else "", "cat": (e.get("category") or {}).get("attributes", {}).get("label", ""),
                    "price": (e.get("im:price") or {}).get("label", ""), "summary": _clean((e.get("summary") or {}).get("label", ""))[:240],
                    "url": (e.get("link") or {}).get("attributes", {}).get("href", "") if isinstance(e.get("link"), dict) else "", "rank": i + 1})
    return out


def _apple_search(store: str, cc: str, q: str, limit: int) -> list[dict]:
    j = _get("https://itunes.apple.com/search", params={"term": q, "country": cc, "limit": limit,
                                                           "entity": "macSoftware" if store == "mac" else "software"})
    if isinstance(j, str):
        j = json.loads(j)
    return [_apple_row(store, x, i + 1) for i, x in enumerate(j.get("results") or [])]


def _apple_row(store: str, x: dict, rank: int = 0) -> dict:
    return {"key": f"{store}:{x.get('trackId')}", "src": store, "id": str(x.get("trackId")), "name": x.get("trackName", ""),
            "dev": x.get("artistName", ""), "icon": x.get("artworkUrl100") or x.get("artworkUrl60", ""), "cat": x.get("primaryGenreName", ""),
            "price": x.get("formattedPrice", ""), "rating": round(x.get("averageUserRating") or 0, 1), "ratings": x.get("userRatingCount") or 0,
            "summary": _clean(x.get("description", ""))[:240], "url": x.get("trackViewUrl", ""), "rank": rank}


def _github(q: str, limit: int) -> list[dict]:
    since = (dt.date.today() - dt.timedelta(days=21)).isoformat()
    query = f"{q} created:>{since}" if q else f"created:>{since} stars:>80"
    j = _get("https://api.github.com/search/repositories", params={"q": query, "sort": "stars", "order": "desc", "per_page": limit}, ttl=3600)
    if isinstance(j, str):
        j = json.loads(j)
    out = []
    for i, r in enumerate(j.get("items") or []):
        out.append({"key": f"github:{r['full_name']}", "src": "github", "id": r["full_name"], "name": r["name"], "dev": r["owner"]["login"],
                    "icon": r["owner"].get("avatar_url", ""), "cat": r.get("language") or "Repo", "price": r.get("license", {}).get("spdx_id", "") if r.get("license") else "",
                    "rating": 0, "ratings": r.get("stargazers_count", 0), "summary": (r.get("description") or "")[:240], "url": r["html_url"],
                    "rank": i + 1, "license": (r.get("license") or {}).get("spdx_id", "")})
    return out


def _producthunt(limit: int) -> list[dict]:
    txt = _get("https://www.producthunt.com/feed", ttl=3600)
    out = []
    for i, it in enumerate(re.findall(r"(?s)<entry>(.*?)</entry>", txt or "")[:limit]):
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        lk = re.search(r'<link[^>]*href="([^"]+)"', it)
        c = re.search(r"<content[^>]*>(.*?)</content>", it, re.S)
        au = re.search(r"<name>(.*?)</name>", it, re.S)
        out.append({"key": f"ph:{(lk.group(1) if lk else str(i)).rsplit('/', 1)[-1]}", "src": "ph", "id": lk.group(1) if lk else "",
                    "name": _clean(t.group(1) if t else ""), "dev": _clean(au.group(1) if au else ""), "icon": "", "cat": "Product Hunt", "price": "",
                    "summary": _clean(html.unescape(c.group(1)) if c else "")[:240], "url": lk.group(1) if lk else "", "rank": i + 1})
    return out


def scan(src: str = "ios", country: str = "vn", chart: str = "free", genre: str = "", q: str = "", limit: int = 50) -> dict:
    """Quét sản phẩm đang thắng trên thị trường."""
    src = src if src in SOURCES else "ios"
    country = country if country in COUNTRIES else "vn"
    chart = chart if chart in CHARTS else "free"
    genre = genre if genre in GENRES else ""
    limit = max(10, min(int(limit or 50), 100))
    q = (q or "").strip()[:80]
    try:
        if src in ("ios", "mac"):
            items = _apple_search(src, country, q, limit) if q else _apple_chart(src, country, chart, genre, limit)
        elif src == "github":
            items = _github(q, min(limit, 50))
        else:
            items = _producthunt(min(limit, 50))
    except requests.RequestException as e:
        raise ValueError(f"Chưa lấy được dữ liệu từ {SOURCES[src]}: {str(e)[:120]}")
    d = _load()
    for it in items:
        it["cloned"] = it["key"] in d["cloned"]
        it["starred"] = it["key"] in d["stars"]
    if src in ("ios", "mac"):
        label = f"{SOURCES[src]} · {COUNTRIES[country]}" + (f" · tìm “{q}”" if q else f" · {CHARTS[chart]}" + (f" · {GENRES[genre]}" if genre else ""))
    else:
        label = SOURCES[src] + (f" · tìm “{q}”" if q else "")
    return {"text": f"{label}: {len(items)} sản phẩm.", "items": items, "label": label,
            "filters": {"sources": SOURCES, "countries": COUNTRIES, "charts": CHARTS, "genres": GENRES}}


def detail(key: str, country: str = "vn") -> dict:
    """Chi tiết 1 sản phẩm: thông tin, ảnh, đánh giá gần đây, sản phẩm khác của nhà phát triển."""
    src, _, ident = (key or "").partition(":")
    if src in ("ios", "mac"):
        j = _get("https://itunes.apple.com/lookup", params={"id": ident, "country": country})
        if isinstance(j, str):
            j = json.loads(j)
        res = (j.get("results") or [])
        if not res:
            raise ValueError("Không tìm thấy app")
        x = res[0]
        row = _apple_row(src, x)
        shots = (x.get("screenshotUrls") or []) + (x.get("ipadScreenshotUrls") or [])
        reviews = []
        try:
            rj = _get(f"https://itunes.apple.com/{country}/rss/customerreviews/id={ident}/sortby=mostrecent/json", ttl=3600)
            if isinstance(rj, str):
                rj = json.loads(rj)
            for e in ((rj.get("feed") or {}).get("entry") or [])[:40]:
                if "im:rating" not in e:
                    continue
                reviews.append({"stars": int(e["im:rating"]["label"]), "title": e.get("title", {}).get("label", ""),
                                "text": (e.get("content") or {}).get("label", "")[:600], "author": (e.get("author") or {}).get("name", {}).get("label", "")})
        except Exception:
            pass
        dev_apps = []
        try:
            dj = _get("https://itunes.apple.com/lookup", params={"id": x.get("artistId"), "entity": "macSoftware" if src == "mac" else "software",
                                                                  "country": country, "limit": 30})
            if isinstance(dj, str):
                dj = json.loads(dj)
            dev_apps = [_apple_row(src, a) for a in (dj.get("results") or []) if a.get("wrapperType") == "software" and a.get("trackId") != x.get("trackId")][:20]
        except Exception:
            pass
        row.update({"description": x.get("description", "")[:6000], "shots": shots[:12], "reviews": reviews, "dev_apps": dev_apps,
                    "version": x.get("version", ""), "release_notes": (x.get("releaseNotes") or "")[:1500], "genres": x.get("genres") or [],
                    "size_mb": round(int(x.get("fileSizeBytes") or 0) / 1e6, 1), "min_os": x.get("minimumOsVersion", ""),
                    "released": (x.get("releaseDate") or "")[:10], "updated": (x.get("currentVersionReleaseDate") or "")[:10],
                    "content_rating": x.get("contentAdvisoryRating", "")})
    elif src == "github":
        j = _get(f"https://api.github.com/repos/{ident}", ttl=3600)
        if isinstance(j, str):
            j = json.loads(j)
        readme = ""
        try:
            from agents import web_tools
            readme = web_tools.read(f"https://github.com/{ident}", 6000).get("text", "")
        except Exception:
            pass
        row = {"key": key, "src": "github", "id": ident, "name": j.get("name", ident), "dev": (j.get("owner") or {}).get("login", ""),
               "icon": (j.get("owner") or {}).get("avatar_url", ""), "cat": j.get("language") or "Repo", "url": j.get("html_url", ""),
               "ratings": j.get("stargazers_count", 0), "rating": 0, "price": (j.get("license") or {}).get("spdx_id", ""),
               "license": (j.get("license") or {}).get("spdx_id", ""), "summary": j.get("description") or "",
               "description": readme[:6000], "shots": [], "reviews": [], "dev_apps": [], "updated": (j.get("pushed_at") or "")[:10]}
    elif src == "ph":
        from agents import web_tools
        r = web_tools.read(ident, 6000)
        row = {"key": key, "src": "ph", "id": ident, "name": r.get("title", ""), "dev": "", "icon": "", "cat": "Product Hunt", "url": ident,
               "summary": "", "description": r.get("text", "")[:6000], "shots": [], "reviews": [], "dev_apps": []}
    else:
        raise ValueError("Nguồn không hợp lệ")
    d = _load()
    row["cloned"] = key in d["cloned"]
    row["project"] = d["cloned"].get(key, "")
    row["starred"] = key in d["stars"]
    stars = [r["stars"] for r in row.get("reviews") or []]
    row["pain"] = [r for r in row.get("reviews") or [] if r["stars"] <= 2][:8]
    row["review_avg"] = round(sum(stars) / len(stars), 1) if stars else 0
    return row | {"targets": TARGETS, "options": OPTIONS, "chips": CHIPS, "notes": d["notes"][-20:]}


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


# ------------------------------------------------------------------ clone -> bản thiết kế + prompt dựng
BLUEPRINT = """Bạn là trưởng phòng Phát triển sản phẩm số của superYou (trợ lý AI điều hành doanh nghiệp, có Marketplace bán skill/workflow/gói tri thức).
Chủ nhân muốn "clone" một sản phẩm đang thắng trên thị trường thành sản phẩm CỦA RIÊNG MÌNH.

Nguyên tắc bắt buộc: giữ ý tưởng, nhu cầu và các tính năng đã được thị trường kiểm chứng; làm tốt hơn ở những điểm người dùng phàn nàn;
tên, thương hiệu, giao diện, câu chữ, hình ảnh, biểu tượng phải mới hoàn toàn. Không chép mã, nội dung hay ảnh có bản quyền của sản phẩm gốc.
Nếu là repo GitHub: tôn trọng giấy phép ({license}); chỉ tái sử dụng mã khi giấy phép cho phép và phải ghi công.

SẢN PHẨM GỐC ({src}): {name} — {dev}
Danh mục: {cat} · Giá: {price} · Đánh giá: {rating} ({ratings} lượt)
Mô tả:
{description}

Những gì người dùng phàn nàn (đánh giá thấp):
{pain}

NỀN TẢNG ĐÍCH: {target}
TUỲ CHỌN CLONE: {options}
GHI CHÚ THÊM CỦA CHỦ NHÂN: {notes}
TÊN DỰ ÁN: {project}

Trả về JSON:
{{"name": "tên sản phẩm mới (tiếng Việt hoặc tiếng Anh, không trùng thương hiệu gốc)",
  "pitch": "1 câu định vị",
  "opportunity": "3-5 câu: vì sao đáng làm, khác biệt so với bản gốc, ai trả tiền ở Việt Nam/Đông Nam Á",
  "features": ["tính năng cốt lõi, theo thứ tự ưu tiên, 6-12 mục"],
  "improvements": ["điểm làm tốt hơn bản gốc, dựa trên phàn nàn"],
  "monetization": "cách kiếm tiền phù hợp (hoặc miễn phí nếu tuỳ chọn yêu cầu)",
  "mvp_days": số ngày ước tính làm bản đầu,
  "build_prompt": "PROMPT DỰNG HOÀN CHỈNH (markdown, tiếng Việt) để giao cho một AI coding agent như Claude Code: bối cảnh, mục tiêu, người dùng, danh sách tính năng có tiêu chí nghiệm thu, cấu trúc màn hình, mô hình dữ liệu, công nghệ cho nền tảng đích, hướng dẫn thiết kế giao diện riêng, quy tắc không sao chép tài sản gốc, các bước kiểm thử. Nếu nền tảng đích là skill/workflow/brain của Marketplace thì đây là NỘI DUNG sản phẩm theo đúng định dạng: skill = hướng dẫn đánh số; brain = nhiều ghi chú bắt đầu '# Tiêu đề'; workflow = mỗi dòng 'agent.hanh_dong: Tên bước' chỉ dùng: {tools}",
  "metadata": {{"short_description": "...", "keywords": ["..."], "category": "..."}}}}"""


def clone(key: str, target: str = "web", options: str = "", notes: str = "", project: str = "", country: str = "vn") -> dict:
    """Clone 1 sản phẩm -> bản thiết kế + prompt dựng (lưu thành dự án trong Xưởng)."""
    target = target if target in TARGETS else "web"
    opts = [o for o in (options or "").split(",") if o in OPTIONS]
    x = detail(key, country)
    pain = "\n".join(f"- ({r['stars']}★) {r['title']}: {r['text'][:220]}" for r in x.get("pain") or []) or "(chưa có dữ liệu)"
    tools = "lich.ngay, lark.tomtat, email.tomtat, tin.top"
    try:
        from agents import market
        tools = market._workflow_tools()
    except Exception:
        pass
    import llm
    res = llm.ask_json(BLUEPRINT.format(src=SOURCES.get(x["src"], x["src"]), name=x["name"], dev=x.get("dev", ""), cat=x.get("cat", ""),
                                        price=x.get("price") or "?", rating=x.get("rating") or "?", ratings=x.get("ratings") or "?",
                                        license=x.get("license") or "không rõ", description=(x.get("description") or x.get("summary") or "")[:5000],
                                        pain=pain, target=TARGETS[target], options="; ".join(OPTIONS[o] for o in opts) or "mặc định",
                                        notes=(notes or "").strip()[:1500] or "(không có)", project=(project or "").strip()[:60] or "(tự đặt)", tools=tools),
                       max_tokens=9000, tag="factory_clone", ok=lambda r: isinstance(r, dict) and r.get("build_prompt"))
    if not res:
        raise ValueError("AI chưa dựng được bản thiết kế lúc này, anh thử lại sau ít phút")
    pid = secrets.token_hex(5)
    proj = {"id": pid, "key": key, "source": {k: x.get(k) for k in ("name", "dev", "src", "url", "icon", "cat", "rating", "ratings", "price")},
            "target": target, "options": opts, "notes": (notes or "")[:1500], "project": (project or "").strip()[:60] or res.get("name", ""),
            "name": str(res.get("name") or "")[:80], "pitch": str(res.get("pitch") or "")[:200], "opportunity": str(res.get("opportunity") or "")[:2000],
            "features": [str(f)[:200] for f in (res.get("features") or [])][:14], "improvements": [str(f)[:200] for f in (res.get("improvements") or [])][:10],
            "monetization": str(res.get("monetization") or "")[:600], "mvp_days": res.get("mvp_days"), "build_prompt": str(res.get("build_prompt") or "")[:30000],
            "metadata": res.get("metadata") or {}, "status": "y_tuong", "created": _now(), "updated": _now()}
    with _LOCK:
        d = _load()
        d["projects"][pid] = proj
        d["cloned"][key] = pid
        _save(d)
    return {"text": f"Đã dựng bản thiết kế “{proj['name']}” từ {x['name']}.", "project": proj}


PSTATUS = {"y_tuong": "Ý tưởng", "dang_dung": "Đang dựng", "da_ra_mat": "Đã ra mắt", "bo": "Bỏ"}


def projects() -> dict:
    d = _load()
    rows = sorted(d["projects"].values(), key=lambda p: p["updated"], reverse=True)
    return {"items": [{k: p.get(k) for k in ("id", "name", "pitch", "target", "status", "source", "created", "updated", "mvp_days", "listing")} for p in rows],
            "statuses": PSTATUS, "targets": TARGETS, "stars": d["stars"][-50:]}


def project(pid: str) -> dict:
    d = _load()
    p = d["projects"].get(pid)
    if not p:
        raise ValueError("Không tìm thấy dự án")
    return p | {"statuses": PSTATUS, "targets": TARGETS}


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


def to_market(pid: str, publish: bool = False, price: int = 0) -> dict:
    """Dự án nhắm skill/workflow/brain -> đưa thẳng thành sản phẩm trong Studio (nháp hoặc lên kệ)."""
    from agents import market
    d = _load()
    p = d["projects"].get(pid)
    if not p:
        raise ValueError("Không tìm thấy dự án")
    if p["target"] not in ("skill", "workflow", "brain"):
        raise ValueError("Dự án này dựng app, không phải sản phẩm Marketplace. Dùng prompt dựng với Claude Code.")
    meta = p.get("metadata") or {}
    desc = (p.get("opportunity") or "") + "\n\nTính năng:\n" + "\n".join(f"- {f}" for f in p.get("features") or [])
    r = market.studio_save(p["target"], p["name"], p.get("pitch") or meta.get("short_description", ""), desc, p["build_prompt"],
                           "nang-suat", price, ", ".join((meta.get("keywords") or [])[:5]), publish, False, p["source"].get("url", ""))
    with _LOCK:
        d = _load()
        if pid in d["projects"]:
            d["projects"][pid]["listing"] = r["id"]
            d["projects"][pid]["status"] = "da_ra_mat" if publish else "dang_dung"
            d["projects"][pid]["updated"] = _now()
            _save(d)
    return r
