"""Kiểm thử giao diện Xưởng Tài sản số (HQ › Xưởng): nguồn có điểm, chi tiết nguồn, đội clone, thẻ duyệt.
Máy chủ thật + dữ liệu mẫu; GitHub được giả lập (không cần mạng), LLM không có khoá (mọi bước AI phải rơi về đường dự phòng).
Ảnh chụp điện thoại + Mac vào qa_out/factory/. Chạy: python deploy/factory_qa.py"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui_qa  # noqa: E402  (đặt biến môi trường, thư mục tạm, hàm seed/init_data)

OUT = ui_qa.OUT / "factory"


def fake_sources():
    """Hai nguồn GitHub giả: một repo prompt MIT đủ điểm, một repo không rõ giấy phép (phải bị loại)."""
    from agents import factory

    def repo(n, lic, lang, stars, desc, topics):
        return {"full_name": "org/" + n, "name": n, "owner": {"login": "org", "avatar_url": ""}, "language": lang, "html_url": "https://github.com/org/" + n,
                "stargazers_count": stars, "description": desc, "license": {"spdx_id": lic} if lic else None, "topics": topics, "pushed_at": "2026-10-01T00:00:00Z"}

    repos = [repo("sales-prompts", "MIT", None, 12000, "Prompts and agent skills for B2B sales teams: discovery, follow-up, pipeline review", ["prompts", "sales"]),
             repo("mystery-prompts", "", "Markdown", 3000, "A big collection of prompts with no license file", ["prompts"]),
             repo("finance-notes-template", "CC-BY-4.0", None, 900, "Obsidian vault template: cash flow notes, weekly finance review, second brain for small business", ["obsidian-template", "finance"])]

    def g(url, ttl=0, params=None):
        if "api.github.com/search" in url:
            return {"items": repos}
        if "api.github.com/repos/" in url:
            n = url.rsplit("/", 1)[-1]
            return next(r for r in repos if r["name"] == n)
        raise RuntimeError("không có mạng trong QA: " + url)
    factory._get = g


def main():
    ui_qa.seed()
    fake_sources()
    from agents import market
    market.catalog()  # gieo chợ chính chủ (nguồn "Bán chạy trên chợ")
    import main as app_main  # noqa: F401
    from webapp import server
    server.EXTRA_BOOTSTRAP = app_main.bootstrap_extra
    server.serve(8788)
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
                    page.evaluate("$('#sheet').style.visibility=''")
                    page.evaluate(js)
                    if full:  # ảnh cả trang: giấu tấm trượt đã đóng để không in bóng vào ảnh
                        page.evaluate("if(!$('#sheet').classList.contains('on')){ $('#sheetBody').innerHTML=''; $('#sheet').style.visibility='hidden'; }")
                    page.wait_for_timeout(wait)
                    page.screenshot(path=str(OUT / f"{tag}-{name}.png"), full_page=full)
                    report.append(f"shot {tag}-{name}")
                except Exception as e:
                    errs.append(f"[{tag} step {name}] {e}")
            page.goto("http://127.0.0.1:8788/hq")
            page.wait_for_timeout(3000)
            step("01-nguon-github", "go('lab')", 3000, True)
            step("02-nguon-detail", "lbOpen(S.lb.scan.items[0].key)", 2200)
            step("03-nguon-diem", "lbOpen(S.lb.cur.key,'score')", 900)
            step("04-nguon-clone", "lbOpen(S.lb.cur.key,'clone')", 900)
            step("05-nguon-loai", "closeSheet();lbOpen(S.lb.scan.items.find(i=>!i.clone_ok).key,'score')", 2200)
            step("06-nguon-khung", "closeSheet();S.lb.src='framework';lbScan(true)", 3200, True)
            step("07-nguon-cho", "S.lb.src='market';lbScan(true)", 2500, True)
            step("08-duan", "S.lb.view='duan';render()", 1500)
            report.append(f"{tag} scrollWidth {page.evaluate('document.documentElement.scrollWidth')} / {vw['width']}")
            ctx.close()
        b.close()
    (OUT / "report.txt").write_text("\n".join(report + ["--- lỗi ---"] + errs), encoding="utf-8")
    print("\n".join(report))
    print("ERRORS:", len(errs))
    print("\n".join(errs[:30]))


if __name__ == "__main__":
    main()
