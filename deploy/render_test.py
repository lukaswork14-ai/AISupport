"""Chẩn đoán: dựng thử video bản tin có giọng + nhạc trên VPS từ video bị lỗi gần nhất (không ghi đè dữ liệu)."""
import os
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import store  # noqa: E402
from agents import newscast, reel_studio as rs  # noqa: E402

recs = store.recent(8, "video")
rec = next((r for r in recs if ((r.get("meta") or {}).get("render") or {}).get("status") == "error"), None) or (recs[0] if recs else None)
if not rec:
    print("render_test: không có video"); sys.exit()
m = rec.get("meta") or {}
sc = m.get("newscast")
print("render_test_cid:", rec["id"], "has_script:", bool(sc), "scenes:", len((sc or {}).get("scenes") or []), "settings:", m.get("settings"))
if not sc:
    print("render_test: video này chưa có kịch bản bản tin (bản cũ) -> dựng lại cần viết kịch bản mới"); sys.exit()
sc = {**sc, "scenes": sc["scenes"][int(os.environ.get("RT_FROM", "0")):]}
it = rs._item_for(m, rec["title"])
t0 = time.time()
try:
    out = newscast.make(sc, it, name="diagtest", voice="NamMinh", brand=rs.CARD_HANDLE, rate="+12%", music=True, music_vol=0.55,
                        progress=lambda msg, pct=None: print(f"  {pct}% {msg}"))
    print("render_test: OK", round(time.time() - t0), "giây", out["duration"], out["engine"])
    for k in ("video", "poster"):
        if out.get(k):
            os.remove(out[k])
except Exception as e:
    print("render_test: LỖI", type(e).__name__, str(e)[:1500])
    traceback.print_exc(limit=6)
