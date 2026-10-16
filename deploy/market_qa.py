"""Kiểm thử giao diện Marketplace, phòng Phát triển sản phẩm số, Quản trị, Khách đăng ký và trang công khai /market.
Máy chủ thật + dữ liệu mẫu, nguồn App Store được giả lập (không cần mạng, không cần khoá LLM). Ảnh chụp vào qa_out/market/."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui_qa  # noqa: E402  (đặt biến môi trường, thư mục tạm, hàm seed/init_data)

OUT = ui_qa.OUT / "market"


def fake_sources():
    from agents import factory
    chart = {"feed": {"entry": [{"id": {"attributes": {"im:id": str(100 + i)}}, "im:name": {"label": n}, "im:artist": {"label": dev},
                                 "im:image": [{"label": ""}], "category": {"attributes": {"label": cat}}, "im:price": {"label": "Nhận"},
                                 "summary": {"label": f"{n}: ứng dụng {cat.lower()} được nhiều người dùng."}}
                                for i, (n, dev, cat) in enumerate([("Todo Pro", "Acme", "Năng suất"), ("Meeting Notes AI", "NoteCo", "Kinh doanh"),
                                                                   ("Budget Buddy", "FinLab", "Tài chính"), ("Habit Coach", "Well", "Sức khoẻ"),
                                                                   ("Shop Analytics", "Merch", "Kinh doanh"), ("Focus Timer", "Calm", "Năng suất")])]}}
    look = {"results": [{"trackId": 101, "trackName": "Meeting Notes AI", "artistName": "NoteCo", "artistId": 9, "artworkUrl100": "",
                         "primaryGenreName": "Kinh doanh", "formattedPrice": "Miễn phí", "averageUserRating": 4.6, "userRatingCount": 18200,
                         "description": "Ghi âm cuộc họp, chép lời, tóm tắt, giao việc.\nGói Pro 9,99 USD/tháng.", "screenshotUrls": [], "version": "3.2",
                         "currentVersionReleaseDate": "2026-10-01T00:00:00Z"}]}
    rev = {"feed": {"entry": [{"im:rating": {"label": "1"}, "title": {"label": "Không hỗ trợ tiếng Việt"}, "content": {"label": "Chép lời tiếng Việt sai nhiều."},
                               "author": {"name": {"label": "Minh"}}},
                              {"im:rating": {"label": "2"}, "title": {"label": "Đắt"}, "content": {"label": "Bắt trả phí mới xuất được biên bản."},
                               "author": {"name": {"label": "Lan"}}},
                              {"im:rating": {"label": "5"}, "title": {"label": "Tốt"}, "content": {"label": "Tóm tắt nhanh."}, "author": {"name": {"label": "An"}}}]}}
    dev = {"results": [{"wrapperType": "artist"}, {"wrapperType": "software", "trackId": 107, "trackName": "NoteCo Calendar", "artistName": "NoteCo",
                                                    "formattedPrice": "Miễn phí", "averageUserRating": 4.2}]}

    def g(url, ttl=0, params=None):
        if "/rss/top" in url:
            return chart
        if "customerreviews" in url:
            return rev
        if "lookup" in url:
            return dev if params and params.get("entity") else look
        if "search" in url:
            return {"results": look["results"]}
        raise RuntimeError("không có mạng trong QA: " + url)
    factory._get = g
    # một dự án mẫu (không gọi AI)
    d = factory._load()
    d["projects"]["p1"] = {"id": "p1", "key": "ios:101", "source": {"name": "Meeting Notes AI", "dev": "NoteCo", "src": "ios", "url": "", "icon": ""},
                           "target": "web", "options": ["feature_clone", "vn_local"], "notes": "", "project": "BienBanViet", "name": "Biên Bản Việt",
                           "pitch": "Biên bản họp tiếng Việt chuẩn, giao việc thẳng vào Lark.", "opportunity": "Bản gốc chép lời tiếng Việt kém và khoá xuất biên bản sau paywall.",
                           "features": ["Ghi âm và chép lời tiếng Việt", "Tách người nói", "Giao việc vào Lark"], "improvements": ["Chép lời tiếng Việt tốt hơn"],
                           "monetization": "Miễn phí 3 biên bản/tháng, Pro 99.000đ.", "mvp_days": 10, "build_prompt": "# Dựng Biên Bản Việt\n1. ...",
                           "metadata": {}, "status": "y_tuong", "created": "2026-10-16T10:00:00", "updated": "2026-10-16T10:00:00"}
    d["cloned"]["ios:101"] = "p1"
    factory._save(d)


def seed_market():
    from agents import leads, market
    market.catalog()
    s = market.creator_signup("Lan Nguyễn", "lan@shop.vn", "Bán áo POD")
    c = market.creator_auth(s["key"])
    market.creator_save(c, {"type": "skill", "name": "Viết listing POD chuẩn SEO", "tagline": "Listing Etsy và Amazon chuẩn SEO cho áo POD trong một phút",
                             "description": "Dành cho người bán POD. " * 8, "body": "1. Hỏi chủ đề áo và khách mục tiêu.\n2. Viết tiêu đề 140 ký tự có từ khoá.\n3. Viết 13 thẻ.",
                             "category": "ban-hang", "price": 49000, "submit": True})
    for i, e in enumerate(["minh@congty.vn", "an@startup.io", "thu@agency.vn"]):
        leads.add(e, "?utm_source=facebook" if i == 1 else "", "")
    lid = next(x["id"] for x in market.catalog()["items"] if x["type"] == "skill")
    market.install(lid)
    market.review(lid, 5, "Biên bản gọn, đúng kiểu anh cần.")
    return s["key"]


def main():
    ui_qa.seed()
    fake_sources()
    key = seed_market()
    import main as app_main  # noqa: F401
    from webapp import server
    server.EXTRA_BOOTSTRAP = app_main.bootstrap_extra
    server.serve(8787)
    time.sleep(1)
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    errs, report = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for tag, vw in (("phone", {"width": 390, "height": 844}), ("mac", {"width": 1440, "height": 900})):
            ctx = b.new_context(viewport=vw, device_scale_factor=1 if tag == "mac" else 2, locale="vi-VN")
            page = ctx.new_page()
            page.route("https://telegram.org/js/telegram-web-app.js",
                       lambda r: r.fulfill(status=200, content_type="text/javascript", body=ui_qa.TG_STUB % json.dumps(ui_qa.init_data())))
            page.on("pageerror", lambda e, t=tag: errs.append(f"[{t} pageerror] {e}"))
            page.on("console", lambda m, t=tag: errs.append(f"[{t} console] {m.text}") if m.type == "error" else None)

            def step(name, js, wait=1500, full=False, page=page, tag=tag):
                try:
                    page.evaluate(js)
                    page.wait_for_timeout(wait)
                    page.screenshot(path=str(OUT / f"{tag}-{name}.png"), full_page=full)
                    report.append(f"shot {tag}-{name}")
                except Exception as e:
                    errs.append(f"[{tag} step {name}] {e}")
            page.goto("http://127.0.0.1:8787/")
            page.wait_for_timeout(3000)
            step("01-mkt", "go('mkt')", 2500, True)
            step("02-mkt-detail", "mkOpen(S.mk.data.top[0].id)", 1800)
            step("03-mkt-installed", "closeSheet();S.mk.view='cai';render()", 1200)
            step("04-admin", "S.mk.view='qt';S.mk.adm=null;render()", 2200, True)
            step("05-admin-products", "S.mk.admTab='sp';render()", 1200)
            step("06-lab-factory", "go('lab')", 2800, True)
            step("07-lab-detail", "lbOpen(S.lb.scan.items[1].key)", 2200)
            step("08-lab-clone", "lbOpen(S.lb.cur.key,'clone')", 1200)
            step("09-lab-reviews", "lbOpen(S.lb.cur.key,'reviews')", 1000)
            step("10-lab-projects", "closeSheet();S.lb.view='duan';render()", 1500)
            step("11-lab-project", "lbProject('p1')", 1500)
            step("12-lab-assets", "closeSheet();S.lb.view='taisan';render()", 1500)
            step("13-lab-new", "lbNew()", 1000)
            step("14-lab-editor", "lbEdit(S.lb.mine.mine[0].id)", 1500)
            step("15-leads", "closeSheet();go('leads')", 2200, True)
            if tag == "phone":
                page.emulate_media(color_scheme="dark")
                page.evaluate("document.documentElement.dataset.scheme='dark'")
                step("16-dark-mkt", "go('mkt');S.mk.view='kham';render()", 1800)
            ow = page.evaluate("document.documentElement.scrollWidth")
            report.append(f"{tag} scrollWidth {ow} / {vw['width']}")
            # trang công khai + console người tạo
            pub = ctx.new_page()
            pub.on("pageerror", lambda e, t=tag: errs.append(f"[{t} public pageerror] {e}"))
            pub.goto("http://127.0.0.1:8787/market")
            pub.wait_for_timeout(2000)
            pub.screenshot(path=str(OUT / f"{tag}-20-public.png"), full_page=True)
            try:
                pub.click("#grid .card-p >> nth=0")
                pub.wait_for_timeout(900)
                pub.screenshot(path=str(OUT / f"{tag}-21-public-detail.png"))
            except Exception as e:
                errs.append(f"[{tag} public detail] {e}")
            pub.goto("http://127.0.0.1:8787/market/console")
            pub.wait_for_timeout(1500)
            pub.screenshot(path=str(OUT / f"{tag}-22-console-login.png"), full_page=True)
            pub.evaluate(f"localStorage.setItem('sy-key', {json.dumps(key)})")
            pub.goto("http://127.0.0.1:8787/market/console")
            pub.wait_for_timeout(2000)
            pub.screenshot(path=str(OUT / f"{tag}-23-console.png"), full_page=True)
            pw = pub.evaluate("document.documentElement.scrollWidth")
            report.append(f"{tag} public scrollWidth {pw}")
            ctx.close()
        b.close()
    (OUT / "report.txt").write_text("\n".join(report + ["--- lỗi ---"] + errs), encoding="utf-8")
    print("\n".join(report[-6:]))
    print("ERRORS:", len(errs))
    print("\n".join(errs[:30]))


if __name__ == "__main__":
    main()
