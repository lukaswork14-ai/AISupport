"""Kiểm thử video bản tin trên GitHub Actions (có mạng): giọng edge-tts thật, phông Be Vietnam Pro, ảnh Wikipedia,
kiểm tra nguồn tin chiến lược. Kết quả (video, khung hình, báo cáo) ghi vào qa_out/."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "qa_out"
H = Path(tempfile.mkdtemp(prefix="superhuy-vqa-"))
os.environ.update(SUPERHUY_HOME=str(H), OBSIDIAN_VAULT=str(H / "vault"), TELEGRAM_TOKEN="1:QA", OWNER_CHAT_ID="1", LLM_API_KEY="qa")
sys.path.insert(0, str(ROOT))
OUT.mkdir(exist_ok=True)
rep = ["# Video QA", time.strftime("%Y-%m-%d %H:%M:%S")]

from agents import newscast as nc  # noqa: E402
from agents import news_agent, strategy  # noqa: E402

rep.append(f"fonts_ok: {nc.ensure_fonts()} family={nc._family('Bold')[0]}")
rep.append(f"ffmpeg: {nc.ffmpeg()}")
words = nc.tts("Shopify vừa công bố cho phép trợ lý AI thanh toán trực tiếp.", str(H / "t.mp3"), "vi-VN-NamMinhNeural", "+10%")
rep.append(f"tts_words: {len(words)} sample={words[:4]}")
rep.append(f"wiki_image(Shopify): {bool(nc.wiki_image('Shopify', H))}")
try:
    import requests as _rq
    _r = _rq.get("https://en.wikipedia.org/w/api.php", headers=nc.WIKI_UA, timeout=15,
                 params={"action": "query", "format": "json", "list": "search", "srsearch": "Shopify", "srlimit": 1})
    rep.append(f"wiki_api: {_r.status_code} {_r.text[:160]}")
    _s = _rq.get("https://en.wikipedia.org/api/rest_v1/page/summary/Shopify", headers=nc.WIKI_UA, timeout=15)
    rep.append(f"wiki_summary: {_s.status_code} {str(_s.json().get('thumbnail'))[:200]}")
except Exception as _e:
    rep.append(f"wiki_debug_error: {_e}")
script = json.loads((ROOT / "deploy/qa/newscast_sample.json").read_text(encoding="utf-8"))
t = time.time()
r = nc.make(script, {"source": "TechCrunch", "topic": "AI Commerce", "url": "https://techcrunch.com/"}, name="qa", brand="@superhuy",
            progress=lambda m: None)
rep.append(f"render: {round(time.time() - t, 1)}s duration={r['duration']} engine={r['engine']} chapters={len(r['chapters'])}")
v = r["video"]
subprocess.run(["cp", v, str(OUT / "newscast.mp4")])
for k, x in enumerate([1.0, 6.0, 10.0, 17.0, 24.0, 30.0, 37.0, r["duration"] - 1.5]):
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{x:.2f}", "-i", v, "-frames:v", "1", "-vf", "scale=540:-1",
                    str(OUT / f"frame{k}.jpg")])
ln = subprocess.run(["ffmpeg", "-i", v, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
rep.append("loudness: " + " ".join(l.strip() for l in ln.splitlines()[-12:] if "I:" in l or "LRA:" in l))
# nguồn tin chiến lược
for lens, L in strategy.LENSES.items():
    for name, url in L["sources"]:
        n, items, err = news_agent._fetch_one((name, url))
        rep.append(f"src[{lens}] {name}: {len(items)} bài{' LỖI ' + str(err)[:80] if err else ''}")
(OUT / "video_report.md").write_text("\n".join(rep), encoding="utf-8")
print("\n".join(rep))
