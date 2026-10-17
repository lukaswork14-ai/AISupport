"""Kiểm toán giao diện (mảng Trải nghiệm & Giao diện): mọi bề mặt × điện thoại / iPad / Mac × sáng / tối.
Dựng máy chủ thật với dữ liệu mẫu như market_qa.py (không cần mạng, không khoá thật), chụp ảnh vào qa_out/giaodien/
và đo tự động: tràn ngang, vùng chạm < 44px (điện thoại), chữ có thể bị cắt dấu (line-height thấp + overflow ẩn),
độ tương phản chữ < 4.5:1 (chữ thường) / 3:1 (chữ lớn). Kết quả: qa_out/giaodien/audit.json + report.md.

Chạy: python deploy/giaodien_qa.py [--only app,hq,pub] [--views phone,ipad,mac]"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui_qa  # noqa: E402
import market_qa  # noqa: E402

OUT = ui_qa.OUT / "giaodien"
# Google Fonts có thể bị chặn trong máy QA: phục vụ Be Vietnam Pro từ gói npm @fontsource/be-vietnam-pro (OFL) nếu có.
FONTS = Path(__import__("os").environ.get("BVP_FONTS", "/tmp/claude-0/fonts/package/files"))


def font_routes(ctx):
    if not FONTS.exists():
        return
    css = "".join(f"@font-face{{font-family:'Be Vietnam Pro';font-style:normal;font-weight:{w};font-display:swap;src:url(https://fonts.gstatic.com/bvp/{sub}-{w}.woff2) format('woff2')}}"
                  for w in (400, 500, 600, 700, 800) for sub in ("latin", "vietnamese"))
    ctx.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(status=200, content_type="text/css", body=css))

    def gs(r):
        n = r.request.url.rsplit("/", 1)[-1].replace(".woff2", "")
        f = FONTS / f"be-vietnam-pro-{n.split('-')[0]}-{n.split('-')[1]}-normal.woff2" if "-" in n else None
        r.fulfill(status=200, content_type="font/woff2", body=f.read_bytes()) if f and f.exists() else r.abort()
    ctx.route("https://fonts.gstatic.com/**", gs)
VIEWS = {"phone": ({"width": 390, "height": 844}, 2), "ipad": ({"width": 820, "height": 1180}, 2), "mac": ({"width": 1440, "height": 900}, 1)}

# Đo trong trang: trả về danh sách vấn đề (giới hạn để báo cáo gọn).
PROBE = r"""(phone) => {
  const vw = document.documentElement.clientWidth, out = {overflow: [], tap: [], clip: [], contrast: []};
  const vis = el => { const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity !== 0 && !el.closest('[hidden],[aria-hidden="true"]'); };
  const name = el => (el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).slice(0,2).join('.') : '')).slice(0, 60);
  const txt = el => (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  out.scrollWidth = document.documentElement.scrollWidth; out.vw = vw;
  // tràn ngang: phần tử vượt mép phải mà không nằm trong vùng cuộn ngang
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el)) continue; const r = el.getBoundingClientRect();
    if (r.right > vw + 1 && r.left < vw) {
      let p = el.parentElement, scroller = false;
      while (p && p !== document.body) { const o = getComputedStyle(p).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') { scroller = true; break; } p = p.parentElement; }
      if (!scroller && getComputedStyle(el).position !== 'fixed') out.overflow.push({el: name(el), right: Math.round(r.right), text: txt(el)});
    }
  }
  if (phone) for (const el of document.querySelectorAll('button, a[href], [role=button], input:not([type=hidden]), select, textarea, summary, [onclick]')) {
    if (!vis(el)) continue; const r0 = el.getBoundingClientRect();
    if (r0.bottom < 0 || r0.top > innerHeight * 3) continue;
    const ps = getComputedStyle(el, '::after'), hit = ps.content !== 'none' && ps.position === 'absolute';
    const r = {width: Math.max(r0.width, hit ? parseFloat(ps.width) || 0 : 0), height: Math.max(r0.height, hit ? parseFloat(ps.height) || 0 : 0)};
    if ((r.width < 44 || r.height < 44) && !(el.tagName === 'A' && getComputedStyle(el).display === 'inline'))
      out.tap.push({el: name(el), w: Math.round(r.width), h: Math.round(r.height), text: txt(el)});
  }
  const lum = c => { const m = c.match(/[\d.]+/g); if (!m) return null; const k = /^color\(/.test(c) ? 1 : 255; const [r,g,b] = m.slice(0,3).map(v => { v = v / k; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }); return .2126*r + .7152*g + .0722*b; };
  const alpha = c => { const m = c.match(/[\d.]+/g); return m && m.length > 3 ? +m[3] : 1; };
  const bgOf = el => { for (let p = el; p; p = p.parentElement) { const s = getComputedStyle(p); if (s.backgroundImage !== 'none' && !/url\(/.test(s.backgroundImage)) return null; if (alpha(s.backgroundColor) > .5) return s.backgroundColor; } return getComputedStyle(document.body).backgroundColor; };
  const seen = new Set();
  for (const el of document.querySelectorAll('body *')) {
    if (!vis(el)) continue;
    const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()); if (!own) continue;
    const s = getComputedStyle(el), fs = parseFloat(s.fontSize), lh = s.lineHeight === 'normal' ? fs * 1.2 : parseFloat(s.lineHeight);
    // cắt dấu: line-height < 1.25 × cỡ chữ trên phần tử ẩn tràn (dấu tiếng Việt như Ở, Ỗ, ặ cần chỗ trên/dưới)
    if ((s.overflow === 'hidden' || s.overflowY === 'hidden' || s.webkitLineClamp !== 'none') && lh < fs * 1.25 && /[ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐặậẹệịọộợụựỵ]/.test(el.textContent))
      out.clip.push({el: name(el), fs: Math.round(fs), lh: +(lh / fs).toFixed(2), text: txt(el)});
    if (alpha(s.color) < .3) continue;
    const bg = bgOf(el); if (!bg) continue;
    const a = lum(s.color), b = lum(bg); if (a == null || b == null) continue;
    const ratio = (Math.max(a, b) + .05) / (Math.min(a, b) + .05), big = fs >= 24 || (fs >= 18.66 && +s.fontWeight >= 700);
    if (ratio < (big ? 3 : 4.5)) { const k = name(el) + s.color + bg; if (seen.has(k)) continue; seen.add(k);
      out.contrast.push({el: name(el), ratio: +ratio.toFixed(2), fg: s.color, bg, fs: Math.round(fs), text: txt(el)}); }
  }
  for (const k of ['overflow','tap','clip','contrast']) { out[k + 'N'] = out[k].length; out[k] = out[k].slice(0, 25); }
  return out;
}"""

APP = [("home", "go('home')"), ("tasks", "go('tasks')"), ("meet", "go('meet')"), ("growth", "go('growth')"), ("chat", "go('chat')"),
       ("content", "go('content')"), ("money", "go('money')"), ("mkt", "go('mkt')"), ("me", "go('me')"), ("more", "go('more')")]
HQ = [("hq", "go('hq')"), ("board", "go('board')"), ("cfo", "go('cfo')"), ("users", "go('users')"), ("sales", "go('sales')"), ("ops", "go('ops')")]
PUB = [("landing", "/landing"), ("market", "/market"), ("console", "/market/console"), ("login", "/login"), ("signup", "/login?mode=signup"),
       ("terms", "/dieu-khoan"), ("refund", "/hoan-tien")]


def main():
    only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
    views = sys.argv[sys.argv.index("--views") + 1].split(",") if "--views" in sys.argv else list(VIEWS)
    ui_qa.seed()
    market_qa.fake_sources()
    market_qa.seed_market()
    import main as app_main  # noqa: F401
    from webapp import server
    server.EXTRA_BOOTSTRAP = app_main.bootstrap_extra
    server.serve(8787)
    time.sleep(1)
    from playwright.sync_api import sync_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    res, errs = [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        for scheme in ("light", "dark"):
            for tag, (vw, dpr) in ((t, VIEWS[t]) for t in views):
                ctx = b.new_context(viewport=vw, device_scale_factor=dpr, locale="vi-VN", color_scheme=scheme, has_touch=tag != "mac", is_mobile=tag == "phone")
                stub = ui_qa.TG_STUB.replace("colorScheme:'light'", f"colorScheme:'{scheme}'") % json.dumps(ui_qa.init_data())
                font_routes(ctx)
                ctx.route("https://telegram.org/js/telegram-web-app.js", (lambda body: lambda r: r.fulfill(status=200, content_type="text/javascript", body=body))(stub))

                def probe(page, surface, screen):
                    fn = f"{tag}-{scheme}-{surface}-{screen}.png"
                    r = page.evaluate(PROBE, tag == "phone")  # đo trước khi chụp: chụp toàn trang làm Chromium tắt giả lập cảm ứng
                    page.screenshot(path=str(OUT / fn), full_page=True)
                    if tag != "mac":
                        ctx.new_cdp_session(page).send("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
                    r.update(view=tag, scheme=scheme, surface=surface, screen=screen, shot=fn)
                    res.append(r)

                for surface, path, screens in (("app", "/app", APP), ("hq", "/hq", HQ)):
                    if only and surface not in only:
                        continue
                    pg = ctx.new_page()
                    pg.on("pageerror", lambda e, t=f"{tag}/{scheme}/{surface}": errs.append(f"[{t}] {e}"))
                    pg.goto("http://127.0.0.1:8787" + path, wait_until="domcontentloaded")
                    pg.wait_for_timeout(2500)
                    for screen, js in screens:
                        try:
                            pg.evaluate(js)
                            pg.wait_for_timeout(1300)
                            probe(pg, surface, screen)
                        except Exception as e:
                            errs.append(f"[{tag}/{scheme}/{surface}/{screen}] {str(e)[:200]}")
                    pg.close()
                if not only or "pub" in only:
                    pg = ctx.new_page()
                    pg.on("pageerror", lambda e, t=f"{tag}/{scheme}/pub": errs.append(f"[{t}] {e}"))
                    for screen, path in PUB:
                        try:
                            pg.goto("http://127.0.0.1:8787" + path, wait_until="domcontentloaded")
                            pg.wait_for_timeout(1300)
                            probe(pg, "pub", screen)
                        except Exception as e:
                            errs.append(f"[{tag}/{scheme}/pub/{screen}] {str(e)[:200]}")
                    pg.close()
                ctx.close()
        b.close()
    (OUT / "audit.json").write_text(json.dumps({"results": res, "errors": errs}, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["| Màn | Cỡ | Nền | scrollW | Tràn | Chạm<44 | Cắt dấu | Tương phản |", "|---|---|---|---|---|---|---|---|"]
    for r in res:
        lines.append(f"| {r['surface']}/{r['screen']} | {r['view']} | {r['scheme']} | {r['scrollWidth']}/{r['vw']} | {r['overflowN']} | {r.get('tapN', 0)} | {r['clipN']} | {r['contrastN']} |")
    (OUT / "report.md").write_text("\n".join(lines + ["", "## Lỗi JS"] + errs), encoding="utf-8")
    print(f"{len(res)} màn, {len(errs)} lỗi JS")


if __name__ == "__main__":
    main()
