"""Kiểm thử giao diện đầu-cuối (chạy trên GitHub Actions): máy chủ Mini App THẬT + dữ liệu mẫu + trình duyệt Chromium cỡ điện thoại.
Bấm qua mọi trang, mở cuộc họp, chia sẻ, Second Brain, chat; ghi lỗi JavaScript / API và chụp màn hình vào qa_out/.
Không dùng khoá thật nào: token Telegram giả, không có LLM (các thao tác cần AI sẽ báo lỗi có kiểm soát)."""
import hashlib
import hmac
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "qa_out"
H = Path(tempfile.mkdtemp(prefix="superhuy-qa-"))
TOKEN, OWNER = "123456:QA-TEST-TOKEN", 777
os.environ.update(SUPERHUY_HOME=str(H), OBSIDIAN_VAULT=str(H / "vault"), TELEGRAM_TOKEN=TOKEN, OWNER_CHAT_ID=str(OWNER),
                  LLM_API_KEY="qa-khong-co-khoa", LLM_BASE_URL="http://127.0.0.1:9/v1", WEBAPP_URL="http://127.0.0.1:8787")
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def seed():
    v = H / "vault"
    (v / "01 Projects/AI Agent Factory").mkdir(parents=True)
    (v / "01 Projects/AI Agent Factory/Chiến lược định giá.md").write_text(
        "# Chiến lược định giá dịch vụ AI Agent\nSellnity định giá gói AI Agent theo giá trị: setup 2.000 USD + 300 USD/tháng.\n"
        "## Bài học\nKhách Etsy quan tâm tiết kiệm thời gian làm mô tả sản phẩm.\n", encoding="utf-8")
    (v / "00 Inbox").mkdir()
    (v / "00 Inbox/Ý tưởng tuyển dụng.md").write_text("Tuyển 2 kỹ sư AI cho Leversphere trong quý 4, ưu tiên người làm RAG.\n", encoding="utf-8")
    kg = H / "data/knowledge/gemini/Chiến lược Sellnity [abcd1234]"
    kg.mkdir(parents=True)
    (kg / "Báo cáo POD [x1].md").write_text('---\ntitle: "Báo cáo POD"\nkb_source: "Gemini Notebook"\nkb_label: "Chiến lược Sellnity › Báo cáo POD"\n---\n'
                                            "# Báo cáo\nThị trường print on demand 2026 tăng 18%, biên lợi nhuận trung bình 32%.\n", encoding="utf-8")
    from agents import meeting
    m = {"id": "demo01", "title": "Tiến độ AI Agent Factory", "status": "done", "started": "2026-10-12T09:05:00", "duration": 2460, "source": "Ghi âm",
         "labels": {"org": "sellnity", "project": "AI Agent Factory", "type": "Họp nội bộ"},
         "speakers": {"S1": {"name": "Anh Huy"}, "S2": {"name": "Lan"}},
         "segments": [{"s": 0, "spk": "S1", "text": "Chào cả nhà, họp nhanh về AI Agent Factory."}, {"s": 35, "spk": "S2", "text": "Tuần này team AI hoá xong 3 quy trình."}],
         "recap": {"title": "Tiến độ AI Agent Factory", "summary": "Team AI hoá xong 3 quy trình, chốt giá gói Agent và kế hoạch tuyển dụng.",
                   "decisions": [{"text": "Chốt giá setup 2.000 USD + 300 USD/tháng", "owner": "Anh Huy", "t": 610}],
                   "next_steps": [{"text": "Hoàn thiện tài liệu chào bán", "owner": "Lan", "due": "2026-10-17", "t": 700}],
                   "suggestions": [{"text": "Thử giá theo kết quả", "t": 800}], "open_questions": [{"text": "Thuê ngoài UI dashboard?", "t": 2100}],
                   "sections": [{"title": "Cập nhật tiến độ", "t": 0, "points": [{"text": "3 quy trình đã AI hoá", "t": 35}]},
                                {"title": "Định giá", "t": 540, "points": [{"text": "So sánh 3 phương án", "t": 560}]}],
                   "mindmap": {"label": "AI Agent Factory", "children": [{"label": "Tiến độ", "t": 0, "children": [{"label": "3 quy trình", "t": 35}]},
                                                                          {"label": "Định giá", "t": 540, "children": [{"label": "2.000 USD", "t": 610}]}]}}}
    meeting.save(m)
    from core import memory
    memory.add("Anh Huy chạy bộ mỗi sáng", "routine")
    # Nội dung: tin chiến lược có phân tích CAO + tài liệu sống + 1 video bản tin
    cao = {"loai": "case_study", "tom_tat": "Shopify mở cho AI agent thanh toán trực tiếp trên hàng triệu cửa hàng.",
           "dieu_moi": "Agent mua hàng thay người dùng, không cần vào web shop.",
           "phan_tich": ["Dữ liệu sản phẩm trở thành mặt tiền mới", "Biên lợi nhuận dịch chuyển sang ai sở hữu agent", "Cần sẵn sàng giao thức thanh toán"],
           "roimaxx": {"lien_quan": 9, "y_nghia": "Cơ hội gói dịch vụ 'sẵn sàng agentic'", "goi_y": ["Gói audit dữ liệu sản phẩm", "Phí theo đơn từ agent"]},
           "leversphere": {"lien_quan": 8, "y_nghia": "POD cần feed sản phẩm chuẩn", "ung_dung": ["Chuẩn hoá thuộc tính áo in"], "kpi": "% đơn từ AI agent"},
           "hanh_dong": [{"viec": "Audit feed sản phẩm Leversphere", "ai": "anh Huy", "khi": "7 ngày"}],
           "rui_ro": ["Phụ thuộc nền tảng"], "do_tin_cay": "cao — thông báo chính thức", "cau_hoi": "Ai sở hữu khách hàng khi agent mua hàng?"}
    import json as _j, subprocess as _sp, datetime as _dt
    from agents import content_hub, strategy
    strategy.DIR.mkdir(parents=True, exist_ok=True)
    strategy.INS.write_text(_j.dumps([{"id": "ins1", "item": "c1", "lens": "roimaxx", "at": _dt.datetime.now().isoformat(timespec="seconds"),
                                         "headline": "Shopify cho AI agent thanh toán trực tiếp", "url": "https://example.com", "source": "TechCrunch", "cao": cao}],
                                       ensure_ascii=False), encoding="utf-8")
    (strategy.DIR / "leversphere.json").write_text(_j.dumps({"version": 1, "updated": _dt.datetime.now().isoformat(timespec="seconds"),
        "summary": "Ưu tiên 30 ngày: chuẩn hoá dữ liệu sản phẩm và agent CSKH.", "changes": ["Bản đầu"],
        "md": "## 0. Tóm tắt điều hành\nMục tiêu 6 tháng: 30% quy trình chạy bằng agent.\n## 4. Kế hoạch 30 ngày\n| Tuần | Việc | Người | Đầu ra |\n|---|---|---|---|\n| 1 | Audit dữ liệu | Huy | Báo cáo |\n| 2 | Agent CSKH | Team CS | Bản thử |\n## 9. Việc tuần này\n- [ ] Họp kick-off\n- [ ] Chọn 3 quy trình"},
        ensure_ascii=False), encoding="utf-8")
    content_hub._save([{"id": "c1", "track": "roimaxx", "status": "new", "at": _dt.datetime.now().isoformat(timespec="seconds"), "topic": "Agentic",
                        "headline_vi": "Shopify cho AI agent thanh toán trực tiếp", "summary_vi": cao["tom_tat"], "why_hot": "", "score": 9,
                        "title_en": "", "url": "https://example.com", "source": "TechCrunch", "cao": cao, "insight": "ins1",
                        "chat": [{"role": "user", "content": "Bối cảnh và ai đứng sau chuyện này?"},
                                 {"role": "assistant", "content": "## Bối cảnh\n- [Bài viết] Shopify mở checkout cho AI agent.\n- [Nhận định] Đây là bước giành vị trí hạ tầng.\n## Ý tưởng cho anh\n- Leversphere: chuẩn hoá feed sản phẩm.",
                                  "followups": ["Đối thủ phản ứng ra sao?", "Chi phí triển khai?"], "sources": [{"title": "Stripe ra giao thức mới", "source": "Stripe", "url": "https://stripe.com"}]}]}])
    vdir = H / "data/videos"
    vdir.mkdir(parents=True, exist_ok=True)
    vid = vdir / "qa.mp4"
    _sp.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=540x960:d=4", "-f", "lavfi", "-i", "sine=d=4",
             "-shortest", "-pix_fmt", "yuv420p", str(vid)])
    from core import store
    cid = store.add("video", "Reels: Shopify cho AI agent thanh toán", "Caption thử", video=str(vid), image=None,
                    meta={"item": "c2", "variant": "reel", "engine": "newscast", "duration": 4, "len": 60, "voice_engine": "edge-tts",
                          "settings": {"voice": "NamMinh", "speed": "nhanh", "music": "vua", "len": 60}, "current_version": "v2",
                          "newscast": {"title": "Shopify", "scenes": [{"type": "hook", "voiceover": "Khách hàng mới là AI?", "on_screen": {"text": "Khách hàng mới là AI?"}},
                                                                      {"type": "stat", "voiceover": "Tăng 7 lần.", "on_screen": {"value": "7 lần", "label": "lưu lượng"}}]},
                          "chapters": [{"t": 0, "type": "hook", "label": "Khách hàng mới là AI?"}, {"t": 2, "type": "stat", "label": "7 lần"}],
                          "reel": "1. [hook] ...", "versions": [{"id": "v1", "video": str(vid), "at": "2026-10-15T09:00:00", "duration": 4, "settings": {"voice": "NamMinh"}, "note": "Bản đầu", "voice_engine": "silent"},
                                                         {"id": "v2", "video": str(vid), "at": "2026-10-15T09:10:00", "duration": 4, "settings": {"voice": "HoaiMy"}, "note": "Giọng nữ, đọc chậm", "voice_engine": "edge-tts"}]})
    items = content_hub._load()
    items.append({"id": "c2", "track": "tin", "status": "done", "at": _dt.datetime.now().isoformat(timespec="seconds"), "done_at": _dt.datetime.now().isoformat(timespec="seconds"),
                  "topic": "AI", "headline_vi": "Shopify cho AI agent thanh toán", "summary_vi": "", "url": "", "source": "TechCrunch",
                  "pack": {"id": "p1", "ids": {"reel": cid}, "image": None}})
    content_hub._save(items)
    # Học tập: khoá Claude Code 30 ngày với bài ngày 1 soạn sẵn
    from agents import learning
    T = learning.TEMPLATES["claude-code-30"]
    lesson = {"objectives": ["Hiểu Claude Code là gì", "Cài đặt và chạy phiên đầu tiên", "Áp dụng cho Leversphere"],
              "md": "## Claude Code là gì?\nClaude Code là trợ lý lập trình dạng agent chạy trong terminal.\n\n## Cài đặt\n```bash\nnpm install -g @anthropic-ai/claude-code\nclaude\n```\n\n## Ví dụ cho Leversphere\n- Tự viết script đổi tên file thiết kế theo SKU\n| Việc | Trước | Sau |\n|---|---|---|\n| Đổi tên 500 file | 2 giờ | 2 phút |",
              "key_points": ["Agent đọc và sửa file thay anh", "Luôn bắt đầu bằng mục tiêu rõ"],
              "quiz": [{"id": "q1", "q": "Claude Code chạy ở đâu?", "options": ["Terminal", "Excel", "Photoshop", "Zalo"], "answer": 0, "explain": "Claude Code là công cụ dòng lệnh."},
                       {"id": "q2", "q": "Lệnh khởi động?", "options": ["start", "claude", "run-ai", "go"], "answer": 1, "explain": "Gõ claude."}],
              "practice": {"task": "Dùng Claude Code viết script đổi tên file thiết kế theo SKU cho Leversphere", "context": "Leversphere",
                           "steps": ["Chuẩn bị 10 file mẫu", "Yêu cầu Claude viết script", "Chạy thử"], "deliverable": "Script + ảnh chụp kết quả",
                           "rubric": ["Chạy đúng", "Xử lý lỗi", "Dễ dùng lại"], "submit": True},
              "reflection": "Việc lặp lại nào ở Leversphere nên tự động hoá đầu tiên?",
              "resources": [{"type": "doc", "title": "Tài liệu chính thức Claude Code", "url": "https://code.claude.com/docs/en/overview"},
                            {"type": "video", "title": "Video: Claude Code là gì", "url": "https://www.youtube.com/results?search_query=claude+code"}]}
    learning._put({"id": "lc1", "template": "claude-code-30", "title": T["title"], "topic": T["topic"], "goal": T["goal"], "level": T["level"],
                   "sources": T["sources"], "outcomes": [], "created": "2026-10-16T00:00:00", "start": learning._today().isoformat(),
                   "status": "active", "review": [], "streak": 0,
                   "days": [{"day": n, "title": t, "module": m, "doc": dp, "kind": k, "focus": "", "status": "todo", **({"lesson": lesson} if n == 1 else {})}
                            for n, t, m, dp, k in T["days"]]})
    from agents import repo_radar as rr
    A1 = {"ten_vi": "Bộ nhớ dài hạn cho agent", "la_gi": "Thư viện lưu và truy xuất trí nhớ dài hạn cho agent LLM, chạy được với SQLite.",
          "diem_noi_bat": ["Gộp trí nhớ trùng lặp tự động", "Truy xuất lai: từ khoá + vector", "Chạy nhẹ trên VPS 1 GB RAM"],
          "chat_luong": "Cập nhật hằng tuần, 140 người đóng góp, license MIT.",
          "nhan_dinh": "Hợp với Second Brain của superHuy: thay phần ghi nhớ thủ công bằng gộp trùng tự động, giảm 30-40% token đưa vào prompt.",
          "phu_hop": 8, "mang": ["Second Brain", "Chat agent"], "ket_luan": "ap_dung",
          "de_xuat": [{"loai": "nang_cap", "tieu_de": "Gộp trí nhớ trùng lặp trước khi đưa vào prompt", "mo_ta": "Thêm bước gộp trùng ở core/memory.py.",
                       "loi_ich": ["tiet_kiem", "nhanh"], "cong_suc": "M", "rui_ro": "Gộp nhầm 2 ý khác nhau", "noi_dung": ""},
                      {"loai": "kien_thuc", "tieu_de": "Mẫu truy xuất lai từ khoá + vector", "mo_ta": "Lưu best practice vào Second Brain.",
                       "loi_ich": ["nhanh"], "cong_suc": "S", "rui_ro": "Không", "noi_dung": "- Dùng BM25 trước, vector sau"},
                      {"loai": "quy_tac", "tieu_de": "Nêu nguồn khi dùng trí nhớ", "mo_ta": "", "loi_ich": ["an_toan"], "cong_suc": "S", "rui_ro": "",
                       "noi_dung": "Khi trả lời dựa trên trí nhớ cũ, nói rõ ghi nhớ từ lúc nào"},
                      {"loai": "nguon", "tieu_de": "Theo dõi bản phát hành", "mo_ta": "", "loi_ich": ["on_dinh"], "cong_suc": "S", "rui_ro": "", "noi_dung": ""}]}
    A2 = {**A1, "ten_vi": "Máy dựng video bằng code", "ket_luan": "thu_nghiem", "phu_hop": 6, "nhan_dinh": "Có thể thay một phần ffmpeg cho hiệu ứng chữ, nhưng nặng Node."}
    rr._write(rr.ITEMS, [
        {"id": "r1", "full_name": "mem-labs/agent-memory", "url": "https://github.com/mem-labs/agent-memory", "desc": "", "lang": "Python", "stars": 18400,
         "stars_week": 2300, "license": "MIT", "pushed": "2026-10-14", "via": "Trending tuần", "week": rr._week(), "status": "new", "at": "2026-10-16T06:40:00", "a": A1},
        {"id": "r2", "full_name": "motion-dev/codevideo", "url": "https://github.com/motion-dev/codevideo", "desc": "", "lang": "TypeScript", "stars": 9200,
         "stars_week": 900, "license": "Apache-2.0", "via": "Chủ đề video-generation", "week": rr._week(), "status": "new", "at": "2026-10-16T06:40:00", "a": A2},
        {"id": "r3", "full_name": "ops/healthcheck", "url": "https://github.com/ops/healthcheck", "lang": "Go", "stars": 4000, "week": rr._week(), "status": "applied",
         "at": "2026-10-15T06:40:00", "a": A2, "applied": {"at": "2026-10-15T08:00:00", "done": ["Lưu best practice: Kiểm tra sức khoẻ dịch vụ"], "tickets": ["t1"]}}])
    rr._write(rr.TICKETS, [{"id": "t1", "title": "Tự khởi động lại khi bot treo", "desc": "Thêm watchdog systemd.", "repo": "ops/healthcheck",
                            "url": "https://github.com/ops/healthcheck", "benefits": ["on_dinh"], "effort": "S", "risk": "", "status": "moi", "at": "2026-10-15T08:00:00",
                            "item": "r3", "plan": {"muc_tieu": "Bot tự hồi phục trong 60 giây", "pham_vi": ["deploy/superhuy.service", "main.py"],
                                                   "buoc": ["Thêm WatchdogSec=120", "Gửi sd_notify mỗi 30 giây", "Thử treo giả lập"], "phu_thuoc": [],
                                                   "kiem_thu": ["Chạy QA giao diện", "Treo giả lập trên VPS"], "rui_ro": ["Khởi động lại liên tục"],
                                                   "lui_lai": "Bỏ WatchdogSec", "chi_phi": "không đáng kể", "uoc_luong": "2 giờ"}}])
    rr._write(rr.RULES, [{"id": "q1", "text": "Khi trả lời dựa trên trí nhớ cũ, nói rõ ghi nhớ từ lúc nào", "repo": "mem-labs/agent-memory", "at": "2026-10-15T08:00:00", "on": True}])
    rr._write(rr.WATCH, [{"full_name": "ops/healthcheck", "url": "https://github.com/ops/healthcheck", "at": "2026-10-15T08:00:00", "last": "v2.1.0", "new": "v2.2.0"}])
    from agents import game
    for ev, ref in [("lesson", "lc1-d1"), ("quiz_perfect", "lc1-d1"), ("task", "t1"), ("habit", "h1"), ("practice_great", "lc1-d1")]:
        game.award(ev, ref, "QA")


def init_data() -> str:
    user = json.dumps({"id": OWNER, "first_name": "Huy"}, separators=(",", ":"))
    pairs = {"auth_date": str(int(time.time())), "query_id": "QA", "user": user}
    check = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


TG_STUB = """window.Telegram={WebApp:{initData:%s,initDataUnsafe:{},colorScheme:'light',ready(){},expand(){},setHeaderColor(){},setBackgroundColor(){},
setBottomBarColor(){},onEvent(){},openLink(u){window.__opened=u},openTelegramLink(u){window.__opened=u},BackButton:{show(){},hide(){},onClick(){}},
HapticFeedback:{impactOccurred(){},notificationOccurred(){},selectionChanged(){}},MainButton:{show(){},hide(){}}}};"""


def main():
    seed()
    import main as app_main  # noqa: F401  (đăng ký agent + dữ liệu màn hình chính, KHÔNG chạy bot)
    from webapp import server
    server.EXTRA_BOOTSTRAP = app_main.bootstrap_extra
    server.serve(8787)
    time.sleep(1)
    from playwright.sync_api import sync_playwright
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    errs, apierr, report = [], [], []
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="vi-VN")
        page = ctx.new_page()
        page.route("https://telegram.org/js/telegram-web-app.js",
                   lambda r: r.fulfill(status=200, content_type="text/javascript", body=TG_STUB % json.dumps(init_data())))
        page.on("pageerror", lambda e: errs.append(f"[pageerror] {e}"))
        page.on("console", lambda m: errs.append(f"[console.{m.type}] {m.text}") if m.type == "error" else None)

        def on_resp(r):
            if "/api/" in r.url:
                try:
                    j = r.json()
                    e = j.get("error") or (j.get("result") or {}).get("error") if isinstance(j, dict) else None
                    if e:
                        apierr.append(f"{r.url.split('/api/')[1][:40]} -> {str(e)[:140]}")
                except Exception:
                    pass
        page.on("response", on_resp)
        page.on("request", lambda rq: report.append(f"POST {json.loads(rq.post_data or '{}').get('agent')}.{json.loads(rq.post_data or '{}').get('action')}")
                if rq.url.endswith("/api/run") else None)

        def shot(name, full=False):
            page.wait_for_timeout(900)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
            report.append(f"shot {name}")

        def step(name, js, wait=1200, full=False):
            try:
                page.evaluate(js)
                page.wait_for_timeout(wait)
                shot(name, full)
            except Exception as e:
                errs.append(f"[step {name}] {e}")

        page.goto("http://127.0.0.1:8787/")
        page.wait_for_timeout(3000)
        shot("01-home", True)
        for i, tab in enumerate(["tasks", "meet", "growth", "content", "money", "mail", "more", "chat"]):
            step(f"{i + 2:02d}-{tab}", f"go('{tab}')", 1800)
        step("10-meet-detail", "go('meet');setTimeout(()=>meetOpen('demo01'),400)", 2500, True)
        step("11-meet-map", "S.mt.view='map';$('#mbody').innerHTML=meetBody();meetBindBody()", 800)
        step("12-share-sheet", "meetShare()", 1500)
        step("13-share-web", "shGo('web')", 2000)
        url = page.evaluate("S.sh&&S.sh.last&&S.sh.last.url||''")
        report.append(f"share url ok={bool(url)}")
        step("14-share-email-form", "shEmail()", 600)
        step("15-share-links", "$('#sheet').scrollTop=99999", 600)
        step("16-brain", "closeSheet();openBrain()", 2500)
        step("17-brain-search", "brSearch('dinh gia agent')", 1500)
        step("18-brain-gemini-code", "brGemConnect()", 1500)
        step("19-brain-note", "brOpen('01 Projects/AI Agent Factory/Chiến lược định giá.md')", 1500)
        step("20-dock", "closeSheet();go('home');S.dockOpen=true;dock()", 1000)
        step("24-content-swipe", "S.dockOpen=false;dock();go('content');S.cview='duyet';render()", 1800)
        step("25-cao-sheet", "cCao('c1')", 1500)
        step("25b-reporter", "closeSheet();rptOpen('c1')", 1800)
        step("26-strategy", "closeSheet();S.cview='cl';S.cl=null;render()", 2500, True)
        step("27-strategy-doc", "clDoc('leversphere')", 1800)
        step("28-insight", "closeSheet();clInsight('ins1')", 1500)
        step("29-pack-video", "closeSheet();S.cview='tao';render();setTimeout(()=>cPack('c2','reel'),300)", 2500)
        step("30-studio-preview", "stPreview('v1');$('.stvers').scrollIntoView()", 1200)
        step("30b-studio-progress", "S.st.d.render={status:'running',pct:46,step:'Giọng đọc và đồ hoạ cảnh 4/8',note:'Giọng nam, đọc vừa phải',started:new Date(Date.now()-42000).toISOString()};S.st.preview=null;stPaint();$('#stProg').scrollIntoView()", 900)
        step("30c-studio-script", "S.st.d.render={};S.st.tab='script';stPaint();$('#stTab').scrollIntoView()", 900)
        step("30d-studio-recipe", "S.st.tab='recipe';S.st.rc={items:[{id:'r1',name:'Bản tin 60s giọng nam',summary:'Mở bằng con số, nhịp vừa',default:true}],skill:''};stPaint();$('#stTab').scrollIntoView()", 900)
        step("31-learn", "closeSheet();go('growth');S.gr.view='learn';S.lr=null;render()", 2500, True)
        step("32-learn-day", "lrDay('lc1',1)", 2500)
        step("33-learn-quiz", "S.ld.ans={q1:0,q2:0};lrQuiz()", 1800)
        step("34-learn-practice", "$('#sheet').scrollTop=$('#sheet').scrollHeight", 800)
        step("35-learn-course", "lrCourse('lc1')", 1800)
        step("36-game-head", "closeSheet();go('growth');S.gr.view='today';render()", 2000)
        step("37-game-quest", "gmOpen('quest')", 1800)
        step("38-game-badge", "gmOpen('badge')", 1200)
        step("39-game-shop", "gmOpen('shop')", 1200)
        step("40-game-bag", "gmOpen('bag')", 1200)
        step("42-repo", "closeSheet();go('content');S.cview='repo';S.rp=null;render()", 2500)
        step("43-repo-detail", "rpOpen('r1')", 1500)
        step("43b-repo-detail-more", "$('#sheet').scrollTop=$('#sheet').scrollHeight", 700)
        step("44-repo-upgrades", "closeSheet();S.rpView='up';render()", 1200, True)
        step("45-ticket", "rpTicket('t1')", 1500)
        step("46-repo-add", "closeSheet();rpAdd()", 800)
        step("41-xp-pop", "closeSheet();xpPop({xp:40,gold:20,note:'Học xong ngày 1',extra:['Nhiệm vụ: Học 1 bài'],level_up:{level:2,title:'Người học việc'}})", 500)
        try:
            dl = page.evaluate("run('noidung','tai_video',{cid:S.st.cid},'',true).then(r=>r.url)")
            import urllib.request
            u = dl if dl.startswith("http") else "http://127.0.0.1:8787" + dl
            with urllib.request.urlopen(u) as rr:
                report.append(f"download ok: HTTP {rr.status}, {rr.headers.get('Content-Disposition', '')[:60]}, {len(rr.read())} bytes")
        except Exception as e:
            errs.append(f"[download] {e}")
        if url:
            sp = ctx.new_page()
            sp.goto(url)
            sp.wait_for_timeout(1500)
            sp.screenshot(path=str(OUT / "21-share-page.png"), full_page=True)
            report.append(f"share page title: {sp.title()}")
            sp.close()
        # chế độ tối
        page.emulate_media(color_scheme="dark")
        page.evaluate("document.documentElement.dataset.scheme='dark'")
        step("22-dark-meet", "closeSheet();meetOpen('demo01')", 2000)
        step("23-dark-brain", "openBrain()", 2000)
        # ---- App iPhone (PWA, ngoài Telegram): đăng nhập bằng PIN
        try:
            from core import security
            security.set_pin("246810")
            ip = b.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, locale="vi-VN", has_touch=True, is_mobile=True,
                               user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
            ap = ip.new_page()
            ap.route("https://telegram.org/js/telegram-web-app.js", lambda r: r.fulfill(status=200, content_type="text/javascript",
                     body="window.Telegram={WebApp:{initData:'',initDataUnsafe:{},ready(){},expand(){},onEvent(){},HapticFeedback:{impactOccurred(){},notificationOccurred(){}}}};"))
            ap.on("pageerror", lambda e: errs.append(f"[app pageerror] {e}"))
            for r_ in ("/manifest.webmanifest", "/sw.js", "/apple-touch-icon.png", "/install", "/install/superHuy.mobileconfig"):
                import urllib.request
                with urllib.request.urlopen("http://127.0.0.1:8787" + r_) as rr:
                    report.append(f"app file {r_}: {rr.status} {rr.headers.get('Content-Type')}")
            ap.goto("http://127.0.0.1:8787/install")
            ap.wait_for_timeout(1200)
            ap.screenshot(path=str(OUT / "49-install-page.png"))
            ap.goto("http://127.0.0.1:8787/app")
            ap.wait_for_timeout(2500)
            ap.screenshot(path=str(OUT / "50-app-lock.png"))
            for k in "1234":
                ap.keyboard.press(k)
                ap.wait_for_timeout(120)
            ap.screenshot(path=str(OUT / "51-app-typing.png"))
            for k in "56":
                ap.keyboard.press(k)
            ap.wait_for_timeout(1500)
            ap.screenshot(path=str(OUT / "52-app-wrong.png"))
            for k in "246810":
                ap.keyboard.press(k)
                ap.wait_for_timeout(80)
            ap.wait_for_timeout(3000)
            ap.screenshot(path=str(OUT / "53-app-home.png"))
            ap.evaluate("go('growth')")
            ap.wait_for_timeout(250)
            ap.screenshot(path=str(OUT / "54-app-tab-anim.png"))
            ap.wait_for_timeout(1500)
            ap.evaluate("go('content');S.cview='repo';render();setTimeout(()=>rpOpen('r1'),300)")
            ap.wait_for_timeout(2000)
            ap.screenshot(path=str(OUT / "55-app-sheet.png"))
            report.append("app unlocked: " + str(ap.evaluate("!!S.tok && !document.body.classList.contains('locked')")))
            ip.close()
        except Exception as e:
            errs.append(f"[app] {e}")
        b.close()
    lines = ["# UI QA", f"time: {time.strftime('%Y-%m-%d %H:%M:%S')}", "", f"## Lỗi JS ({len(errs)})"] + errs[:80] + \
            ["", f"## API trả lỗi ({len(apierr)})"] + apierr[:80] + ["", "## Nhật ký"] + report
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:60]))


if __name__ == "__main__":
    main()
