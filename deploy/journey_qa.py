"""Hành trình người dùng đa thiết bị (phòng QA): máy chủ cục bộ thật + dữ liệu mẫu + 5 thiết bị giả lập bằng Playwright.
Ba hành trình:
  (a) người ngoài: landing → Marketplace → xem 3 loại sản phẩm → Mua (email mẫu) → QR/đơn → Đơn của tôi
  (b) người bán: /market/console → tạo tài khoản → nhận khoá → đóng gói 3 bước (tự điền) → gửi duyệt
  (c) chủ nhân: /app → PIN mẫu → Hồ sơ (sáng/tối, màu nhấn) → Workflow (dựng 2 bước, lưu, chạy) → Marketplace (cài, chạy)
      → HQ (Tổng quan, Phòng ban duyệt 1 phiếu, Giao dịch xác nhận 1 đơn, Thử nghiệm đổi phạm vi 1 tính năng)
Mỗi bước: ảnh qa_out/journey/<thiết bị>/NN-thietbi-buoc.png, lỗi JS, API trả lỗi, thời gian, tràn ngang (scrollWidth),
chữ nhỏ (< 11px) và cặp màu tương phản thấp (heuristic). Kết quả: qa_out/journey/report.json + report.txt.
Không dùng khoá thật: không có LLM (bước cần AI báo lỗi có kiểm soát), PIN mẫu 246810, khoá người bán mẫu."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui_qa  # noqa: E402  (đặt biến môi trường, thư mục tạm, seed)
import market_qa  # noqa: E402

OUT = ui_qa.OUT / "journey"
PORT = 8789
BASE = f"http://127.0.0.1:{PORT}"
PIN = "246810"
UA_IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
UA_IPAD = "Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
UA_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15"
UA_WIN = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
UA_ANDROID = "Mozilla/5.0 (Linux; Android 15; Pixel 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36"
DEVICES = [
    ("iphone", "iPhone 15", dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=UA_IPHONE)),
    ("ipad", "iPad", dict(viewport={"width": 1024, "height": 1366}, device_scale_factor=2, is_mobile=True, has_touch=True, user_agent=UA_IPAD)),
    ("mac", "Mac Safari", dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1, user_agent=UA_MAC)),
    ("windows", "Windows laptop", dict(viewport={"width": 1366, "height": 768}, device_scale_factor=1, user_agent=UA_WIN)),
    ("android", "Android", dict(viewport={"width": 412, "height": 915}, device_scale_factor=2.6, is_mobile=True, has_touch=True, user_agent=UA_ANDROID)),
]
TG_OFF = "window.Telegram={WebApp:{initData:'',initDataUnsafe:{},ready(){},expand(){},onEvent(){},HapticFeedback:{impactOccurred(){},notificationOccurred(){},selectionChanged(){}}}};"

# Kiểm tra trong trang: tràn ngang, chữ nhỏ, tương phản thấp (heuristic WCAG, bỏ qua chữ mờ/ẩn)
AUDIT_JS = r"""
() => {
  const vw = document.documentElement.clientWidth;
  const sw = Math.max(document.documentElement.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const lum = (r,g,b) => { const f = c => { c/=255; return c<=0.03928 ? c/12.92 : Math.pow((c+0.055)/1.055, 2.4); }; return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b); };
  const parse = s => { const m = (s||'').match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/); return m ? [+m[1],+m[2],+m[3], m[4]===undefined?1:+m[4]] : null; };
  const bgOf = el => { let e = el; while(e){ const c = parse(getComputedStyle(e).backgroundColor); if(c && c[3] > 0.9) return c; e = e.parentElement; } return [255,255,255,1]; };
  const small = [], low = []; let n = 0;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let node; const seen = new Set();
  while((node = walker.nextNode()) && n < 1500){
    const t = node.textContent.trim(); if(t.length < 3) continue;
    const el = node.parentElement; if(!el || seen.has(el)) continue; seen.add(el); n++;
    const cs = getComputedStyle(el); if(cs.visibility==='hidden' || cs.display==='none' || +cs.opacity < 0.5) continue;
    const r = el.getBoundingClientRect(); if(r.width < 2 || r.height < 2 || r.bottom < 0 || r.top > innerHeight*3) continue;
    const fs = parseFloat(cs.fontSize);
    const desc = (el.tagName.toLowerCase() + (el.className && typeof el.className==='string' ? '.'+el.className.split(' ')[0] : '') + ' “' + t.slice(0,40) + '”');
    if(fs < 11) small.push(desc + ' ' + fs.toFixed(1) + 'px');
    const fg = parse(cs.color); if(!fg || fg[3] < 0.9) continue;
    const bg = bgOf(el);
    const L1 = lum(fg[0],fg[1],fg[2]), L2 = lum(bg[0],bg[1],bg[2]);
    const ratio = (Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
    const big = fs >= 18 || (fs >= 14 && +cs.fontWeight >= 700);
    if(ratio < (big ? 3 : 4.5)) low.push(desc + ' ' + ratio.toFixed(2) + ':1');
  }
  return {vw, sw, overflow: sw > vw + 2, small: small.slice(0, 12), small_n: small.length, low: low.slice(0, 12), low_n: low.length};
}
"""


def _short(e) -> str:
    """Dòng đầu lỗi + lý do Playwright (vd. phần tử nào che nút bấm)."""
    lines = [x.strip() for x in str(e).splitlines() if x.strip()]
    why = [x for x in lines if "intercepts pointer" in x or "outside of the viewport" in x or "not visible" in x]
    return (lines[0] if lines else "lỗi")[:200] + (f" ({why[-1][:160]})" if why else "")


class Journey:
    def __init__(self, dev, label, ctx, results):
        self.dev, self.label, self.ctx, self.results = dev, label, ctx, results
        self.n = 0
        self.dir = OUT / dev
        self.dir.mkdir(parents=True, exist_ok=True)
        self.errs, self.apierr = [], []

    def page(self):
        p = self.ctx.new_page()
        p.route("https://telegram.org/js/telegram-web-app.js", lambda r: r.fulfill(status=200, content_type="text/javascript", body=TG_OFF))
        p.on("pageerror", lambda e: self.errs.append(f"pageerror: {str(e)[:200]}"))
        p.on("console", lambda m: self.errs.append(f"console: {m.text[:200]}") if m.type == "error" and "ERR_TUNNEL" not in m.text else None)

        def on_resp(r):
            if "/api/" in r.url:
                try:
                    if r.status >= 400:
                        self.apierr.append(f"HTTP {r.status} {r.url.split('/api/')[1][:50]}")
                        return
                    j = r.json()
                    e = (j.get("error") or (j.get("result") or {}).get("error")) if isinstance(j, dict) else None
                    if e:
                        self.apierr.append(f"{r.url.split('/api/')[1][:40]} -> {str(e)[:140]}")
                except Exception:
                    pass
        p.on("response", on_resp)
        return p

    def step(self, journey, name, page, fn=None, wait=1200, full=False, nav_url=None):
        """Chạy một bước, chụp ảnh, đo thời gian và kiểm tra trang."""
        self.n += 1
        fname = f"{self.n:02d}-{self.dev}-{name}.png"
        e0, a0 = len(self.errs), len(self.apierr)
        t0 = time.time()
        err, load = "", None
        try:
            if nav_url:
                page.goto(BASE + nav_url, wait_until="load")
                load = page.evaluate("(() => { const n = performance.getEntriesByType('navigation')[0]; return n ? {dom: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd), ttfb: Math.round(n.responseStart)} : null; })()")
            if fn:
                fn()
            page.wait_for_timeout(wait)
        except Exception as e:
            err = _short(e)
        dt = round((time.time() - t0) * 1000)
        audit = {}
        try:
            audit = page.evaluate(AUDIT_JS)
            page.screenshot(path=str(self.dir / fname), full_page=full)
        except Exception as e:
            err = err or f"screenshot: {str(e)[:120]}"
        rec = {"n": self.n, "device": self.dev, "journey": journey, "step": name, "file": f"{self.dev}/{fname}", "ms": dt, "load": load,
               "error": err, "js_errors": self.errs[e0:], "api_errors": self.apierr[a0:], "audit": audit, "url": page.url}
        self.results.append(rec)
        flag = "LỖI " if err else ""
        print(f"  {flag}{fname} {dt}ms" + (f" tràn {audit.get('sw')}/{audit.get('vw')}" if audit.get("overflow") else ""))
        return rec

    # ------------------------------------------------------------ (a) người ngoài
    def visitor(self):
        p = self.page()
        J = "khach"
        self.step(J, "landing", p, nav_url="/landing", wait=1800, full=True)
        self.step(J, "landing-marketplace", p, lambda: p.evaluate("document.getElementById('marketplace').scrollIntoView()"), 800)
        self.step(J, "market", p, nav_url="/market", wait=2200, full=True)
        for typ, nm, rx in (("skill", "skill", "skill"), ("workflow", "workflow", "workflow"), ("brain", "goi-tri-thuc", "gói|tri thức|brain")):
            def open_type(typ=typ, rx=rx):
                ok = p.evaluate("""(rx) => { const cards = [...document.querySelectorAll('#grid .card-p')];
                    const c = cards.find(c => c.querySelector('.typ') && new RegExp(rx, 'i').test(c.querySelector('.typ').textContent));
                    if(!c) return false; c.click(); return true; }""", rx)
                if not ok:
                    raise RuntimeError(f"không thấy sản phẩm loại {typ} trên lưới")
            self.step(J, f"xem-{nm}", p, open_type, 1300)
            if typ != "brain":
                p.evaluate("document.getElementById('dlg').close()")
        # mua sản phẩm đang mở (gói tri thức) bằng email mẫu
        def buy():
            p.fill("#ge", "khach-qa@congty.vn")
            p.click("#gf button")
            p.wait_for_selector("#getbox .payqr, #getbox .okbox, #getbox .msg.err", timeout=8000)
        self.step(J, "mua-qr", p, buy, 1500)
        p.evaluate("document.getElementById('dlg').close()")

        def my_orders():
            p.click("#myo")
            p.fill("#me", "khach@congty.vn")
            p.click("#mf button")
        self.step(J, "don-cua-toi", p, my_orders, 1500)
        p.close()

    # ------------------------------------------------------------ (b) người bán
    def seller(self):
        p = self.page()
        J = "nguoi-ban"
        self.step(J, "console-dang-ky", p, nav_url="/market/console", wait=1500, full=True)

        def signup():
            p.fill("#sn", "Minh QA")
            p.fill("#se", f"minh-qa-{self.dev}@congty.vn")
            p.fill("#sb", "Chuyên checklist vận hành cho đội bán hàng.")
            p.click("#su button")
            p.wait_for_selector("#kb", timeout=8000)
        self.step(J, "nhan-khoa", p, signup, 900)
        self.step(J, "console-trong", p, lambda: p.click("#kg"), 1800, full=True)
        self.step(J, "buoc1-nguyen-lieu", p, lambda: p.click("#nw"), 900, full=True)

        def fill1():
            p.select_option("#wt", "skill")
            p.fill("#wr", "1. Hỏi tên khách và sản phẩm đang bán.\n2. Liệt kê 5 câu hỏi khách hay hỏi.\n3. Soạn câu trả lời mẫu dưới 60 chữ mỗi câu.\n4. Nhắc kiểm tra tồn kho trước khi hứa giao.")
            p.click("#wm")
        self.step(J, "buoc2-trang-san-pham", p, fill1, 1000, full=True)

        def fill2():
            p.fill("#fn", "FAQ bán hàng 60 giây")
            p.fill("#fg", "Trả lời 5 câu khách hay hỏi, ngắn gọn và đúng tồn kho")
            p.fill("#fd", "Dành cho chủ shop và nhân viên tư vấn. Skill hỏi tên khách, sản phẩm, rồi soạn 5 câu trả lời mẫu dưới 60 chữ, nhắc kiểm tra tồn kho trước khi hứa giao. Dùng khi trả lời inbox Facebook, Zalo hoặc Shopee.")
            p.select_option("#fc", index=0)
            p.fill("#fp", "29000")
            p.click("#fn2")
        self.step(J, "buoc3-kiem-tra", p, fill2, 1000, full=True)

        def submit():
            p.click("#go")
            p.wait_for_selector("#gmsg:not(:empty)", timeout=8000)
        self.step(J, "gui-duyet", p, submit, 1200)
        self.step(J, "console-sau-gui", p, nav_url="/market/console", wait=1800, full=True)
        p.close()

    # ------------------------------------------------------------ (c) chủ nhân
    def unlock(self, page, J, name):
        def enter():
            page.wait_for_selector("#keys button", timeout=8000)
            for k in PIN:
                page.click(f"#keys button[data-k='{k}']")
                page.wait_for_timeout(90)
            page.wait_for_function("!document.body.classList.contains('locked')", timeout=10000)
        return self.step(J, name, page, enter, 2200)

    def owner(self):
        p = self.page()
        J = "chu-nhan"
        self.step(J, "app-khoa", p, nav_url="/app", wait=1800)
        self.unlock(p, J, "app-mo-khoa")
        self.step(J, "ho-so", p, lambda: p.evaluate("go('me')"), 2200, full=True)
        self.step(J, "ho-so-toi", p, lambda: p.evaluate("mePref({theme:'dark'})"), 1500, full=True)
        self.step(J, "ho-so-mau-nhan", p, lambda: p.evaluate("mePref({accent:'rose'})"), 1200)
        p.evaluate("mePref({theme:'light', accent:'violet'})")
        p.wait_for_timeout(800)
        self.step(J, "workflow-danh-sach", p, lambda: p.evaluate("go('wf')"), 2000)
        self.step(J, "workflow-dung-2-buoc", p, lambda: p.evaluate(
            "S.wf.cur={id:'',name:'Bàn giao buổi sáng (QA)',desc:'',steps:[{agent:'lich',action:'ngay',params:{date:'hôm nay'},label:'Lịch hôm nay'},"
            "{agent:'viec',action:'tongquan',params:{},label:'Việc đang mở'}],schedule:'morning'};render()"), 1200, full=True)
        self.step(J, "workflow-luu", p, lambda: p.evaluate("wfSave()"), 2200)

        def run_wf():
            wid = p.evaluate("(S.wf.list&&S.wf.list.items&&S.wf.list.items[0]||{}).id||''")
            if not wid:
                raise RuntimeError("chưa có workflow để chạy")
            p.evaluate(f"wfRun('{wid}')")
        self.step(J, "workflow-chay", p, run_wf, 4000)
        p.evaluate("closeSheet()")
        self.step(J, "marketplace", p, lambda: p.evaluate("go('mkt')"), 2200, full=True)

        def install():
            lid = p.evaluate("(S.mk.data.items.find(i=>i.type==='skill'&&!i.installed)||{}).id||''")
            if not lid:
                raise RuntimeError("không còn skill chưa cài")
            p.evaluate(f"mkOpen('{lid}')")
            p.wait_for_timeout(900)
            p.evaluate(f"mkInstall('{lid}')")
        self.step(J, "marketplace-cai-skill", p, install, 2500)

        def run_mk():
            lid = p.evaluate("(S.mk.data.items.find(i=>i.type==='workflow')||{}).id||''")
            if not lid:
                raise RuntimeError("không có workflow trên kệ")
            p.evaluate(f"(async()=>{{ try{{ await run('market','cai',{{lid:'{lid}'}},'',true); }}catch(e){{}} mkRun('{lid}'); }})()")
        self.step(J, "marketplace-chay-workflow", p, run_mk, 4000)
        p.evaluate("closeSheet()")
        p.close()
        # superYou HQ: phiên riêng (token chỉ trong bộ nhớ trang) → nhập PIN lại
        hq = self.page()
        self.step(J, "hq-khoa", hq, nav_url="/hq", wait=1500)
        self.unlock(hq, J, "hq-tong-quan")
        hq.wait_for_timeout(1500)
        self.step(J, "hq-tong-quan-day-du", hq, None, 800, full=True)
        self.step(J, "hq-phong-ban", hq, lambda: hq.evaluate("go('board')"), 2200, full=True)

        def approve():
            iid = hq.evaluate("((S.bd&&S.bd.items||[]).find(x=>x.status==='cho_duyet')||{}).id||''")
            if not iid:
                raise RuntimeError("không có phiếu chờ duyệt")
            hq.evaluate(f"bdDecide('{iid}','duyet')")
        self.step(J, "hq-duyet-phieu", hq, approve, 2200, full=True)
        self.step(J, "hq-giao-dich", hq, lambda: hq.evaluate("S.mk.view='qt';S.mk.admTab='gd';go('mkt')"), 2500, full=True)

        def confirm():
            oid = hq.evaluate("((S.mk.gd&&S.mk.gd.orders||[]).find(o=>o.status==='pending')||{}).id||''")
            if not oid:
                raise RuntimeError("không có đơn chờ xác nhận")
            hq.evaluate(f"gdConfirm('{oid}')")
        self.step(J, "hq-xac-nhan-don", hq, confirm, 2500, full=True)
        self.step(J, "hq-thu-nghiem", hq, lambda: hq.evaluate("go('ex')"), 2200, full=True)
        self.step(J, "hq-doi-pham-vi", hq, lambda: hq.evaluate(
            "run('thunghiem','bat',{key:'cfo_brief',scope:'tier',tiers:'pro,business'},'',true).then(r=>{toast(r.text);S.ex=null;exLoad()})"), 2500, full=True)
        hq.close()


def fresh_data(dev: str):
    """Mỗi thiết bị một bộ việc riêng: 1 phiếu chờ duyệt, 1 đơn chờ xác nhận, 1 skill chưa cài (thiết bị trước đã dùng hết)."""
    from agents import board, market, pay
    board.propose("qa", f"Phiếu thử của QA ({dev})", "Phiếu mẫu để kiểm thử nút Duyệt.", priority="thap", by="QA")
    paid = next(x["id"] for x in market.catalog()["items"] if x["price"] > 0)
    pay.create_order(paid, f"khach-{dev}@congty.vn")
    for x in market.catalog()["items"]:
        if x["type"] == "skill" and x.get("installed"):
            market.uninstall(x["id"])


def main():
    ui_qa.seed()
    market_qa.fake_sources()
    market_qa.seed_market()
    from core import security
    security.set_pin(PIN)
    import main as app_main  # noqa: F401
    from webapp import server
    server.EXTRA_BOOTSTRAP = app_main.bootstrap_extra
    server.serve(PORT)
    time.sleep(1)
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    results, summary = [], {}
    t_all = time.time()
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        for dev, label, opts in DEVICES:
            print(f"== {label}")
            fresh_data(dev)
            server._HELLO.clear()  # mọi thiết bị giả lập cùng IP 127.0.0.1: xoá bộ đếm tần suất để thiết bị sau không bị 429 oan
            ctx = b.new_context(locale="vi-VN", **opts)
            j = Journey(dev, label, ctx, results)
            for name, fn in (("khach", j.visitor), ("nguoi-ban", j.seller), ("chu-nhan", j.owner)):
                try:
                    fn()
                except Exception as e:  # hành trình đứt giữa chừng
                    results.append({"n": j.n + 1, "device": dev, "journey": name, "step": "dut-hanh-trinh", "file": "", "ms": 0, "load": None,
                                    "error": f"Hành trình dừng: {str(e).splitlines()[0][:220]}", "js_errors": [], "api_errors": [], "audit": {}, "url": ""})
                    print(f"  DỪNG {name}: {str(e).splitlines()[0][:160]}")
            # mở khoá PIN 2 lần/thiết bị: xoá bộ đếm sai để thiết bị sau không bị khoá 15 phút oan
            security._save({**security._load(), "fails": 0})
            summary[dev] = {"label": label, "viewport": opts["viewport"], "steps": len([r for r in results if r["device"] == dev]),
                            "errors": len([r for r in results if r["device"] == dev and r["error"]]),
                            "js_errors": len(j.errs), "api_errors": len(j.apierr)}
            ctx.close()
        b.close()
    data = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "seconds": round(time.time() - t_all), "devices": summary, "steps": results}
    (OUT / "report.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# Hành trình người dùng (QA)", f"time: {data['time']} · {data['seconds']}s", ""]
    for dev, s in summary.items():
        lines.append(f"{s['label']}: {s['steps']} bước, {s['errors']} bước lỗi, {s['js_errors']} lỗi JS, {s['api_errors']} API lỗi")
    lines += ["", "## Bước lỗi"] + [f"{r['file'] or r['device']}: {r['error']}" for r in results if r["error"]]
    lines += ["", "## Tràn ngang"] + [f"{r['file']}: {r['audit']['sw']} / {r['audit']['vw']}" for r in results if r.get("audit", {}).get("overflow")]
    lines += ["", "## Chữ nhỏ (< 11px)"] + [f"{r['file']}: {x}" for r in results for x in r.get("audit", {}).get("small", [])]
    lines += ["", "## Tương phản thấp (heuristic)"] + [f"{r['file']}: {x}" for r in results for x in r.get("audit", {}).get("low", [])]
    lines += ["", "## Lỗi JS"] + [f"{r['file']}: {x}" for r in results for x in r["js_errors"]]
    lines += ["", "## API trả lỗi"] + [f"{r['file']}: {x}" for r in results for x in r["api_errors"]]
    (OUT / "report.txt").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:40]))
    bad = [r for r in results if r["error"]]
    print(f"\nBƯỚC LỖI: {len(bad)} / {len(results)}")


if __name__ == "__main__":
    main()
