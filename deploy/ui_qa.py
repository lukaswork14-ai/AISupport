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
        b.close()
    lines = ["# UI QA", f"time: {time.strftime('%Y-%m-%d %H:%M:%S')}", "", f"## Lỗi JS ({len(errs)})"] + errs[:80] + \
            ["", f"## API trả lỗi ({len(apierr)})"] + apierr[:80] + ["", "## Nhật ký"] + report
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines[:60]))


if __name__ == "__main__":
    main()
