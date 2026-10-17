"""Phòng Vận hành (AI) của superYou: theo dõi tenant, sức khỏe hệ thống, chi phí hạ tầng trên mỗi khách và cảnh báo theo ngưỡng.

- tenants():        danh sách instance khách (systemd superyou@<slug>) + instance chính "chu_san".
- system_health():  gom kết quả QC (core/qc.py) + ổ đĩa, tải CPU, bộ nhớ tiến trình.
- cost_snapshot():  ảnh chụp chi phí/khách mỗi ngày (chi phí cố định từ CFO ÷ (1 + số tenant đang chạy) + ước tính LLM).
- check_alerts():   so với ngưỡng -> security.alert_once + đề xuất lên bảng Phòng ban (dept ops -> giao Product).
- weekly_report():  báo cáo một trang sáng thứ Hai, kèm 3 khuyến nghị theo luật đơn giản (không cần LLM).
Dữ liệu: DATA_DIR/ops.json {thresholds, snapshots{date}, llm{date}, llm_price, reports[], issues_last[]}. Mọi hàm công khai trả dict có `text`.
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any

from config import DATA_DIR, HOME_DIR, IS_TENANT

FILE = DATA_DIR / "ops.json"
_LOCK = threading.Lock()
TENANT_BASES = [Path("/superyou-tenants"), Path("/opt/superyou-tenants")]
DEFAULT_THRESHOLDS: dict[str, Any] = {"disk_pct": 85, "qc_fails": 2, "cost_per_customer": 500000, "tenant_down": True}
KEEP_DAYS = 90


def _today() -> str:
    return dt.date.today().isoformat()


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8")) if FILE.exists() else {}
    except Exception:
        d = {}
    for k, v in (("thresholds", {}), ("snapshots", {}), ("llm", {}), ("llm_price", {}), ("reports", []), ("issues_last", [])):
        d.setdefault(k, v)
    return d


def _save(d: dict) -> None:
    try:
        tmp = FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(FILE)
    except Exception:
        pass


def _vnd(v) -> str:
    try:
        from agents.cfo import vnd
        return vnd(v)
    except Exception:
        return f"{int(v or 0):,}đ".replace(",", ".")


# ------------------------------------------------------------------ 1. tenant
def _dir_size(p: Path, limit: int = 20000) -> int:
    """Tổng dung lượng thư mục (duyệt rẻ, dừng sau `limit` file)."""
    total, n = 0, 0
    try:
        for root, _dirs, files in os.walk(p):
            for f in files:
                try:
                    total += os.lstat(os.path.join(root, f)).st_size
                except OSError:
                    pass
                n += 1
                if n >= limit:
                    return total
    except Exception:
        pass
    return total


def _service_state(slug: str) -> str:
    try:
        r = subprocess.run(["systemctl", "is-active", f"superyou@{slug}"], capture_output=True, text=True, timeout=5)
        return (r.stdout or r.stderr or "unknown").strip().splitlines()[0][:20] or "unknown"
    except Exception:
        return "unknown"


def _last_log(home: Path) -> str:
    try:
        p = home / "data" / "agent.log"
        if p.exists():
            with p.open("rb") as f:
                f.seek(max(0, p.stat().st_size - 4000))
                lines = [ln for ln in f.read().decode("utf-8", "ignore").splitlines() if ln.strip()]
            return lines[-1][:200] if lines else ""
        hb = home / "data" / "heartbeat.json"
        if hb.exists():
            ts = json.loads(hb.read_text()).get("ts", 0)
            return "heartbeat " + dt.datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")
    except Exception:
        pass
    return ""


def tenants() -> dict:
    """Danh sách tenant (instance khách) và instance chính. Không bao giờ raise."""
    rows: list[dict] = []
    try:
        rows.append({"slug": "chu_san", "name": "Instance chính" + (" (tenant)" if IS_TENANT else ""), "exists": True, "home": str(HOME_DIR),
                     "size_mb": round(_dir_size(DATA_DIR) / 1e6, 1), "state": "active", "last_log": _last_log(HOME_DIR), "main": True})
        for base in TENANT_BASES:
            if not base.is_dir():
                continue
            for h in sorted(base.iterdir()):
                if not h.is_dir() or h.name.startswith("."):
                    continue
                rows.append({"slug": h.name, "name": h.name, "exists": True, "home": str(h), "size_mb": round(_dir_size(h) / 1e6, 1),
                             "state": _service_state(h.name), "last_log": _last_log(h), "main": False})
            break
    except Exception as e:
        rows.append({"slug": "?", "name": "Lỗi quét tenant", "exists": False, "state": "unknown", "last_log": str(e)[:120], "size_mb": 0, "main": False})
    cust = [r for r in rows if not r.get("main")]
    active = sum(1 for r in cust if r["state"] == "active")
    lines = [f"🏢 Tenant: {len(cust)} khách, {active} đang chạy."] + [
        f"{'🟢' if r['state'] == 'active' else '⚪' if r['state'] == 'unknown' else '🔴'} {r['slug']} · {r['state']} · {r['size_mb']} MB" for r in rows]
    return {"text": "\n".join(lines), "items": rows, "count": len(cust), "active": active}


# ------------------------------------------------------------------ 2. sức khỏe hệ thống
def system_health() -> dict:
    """Tóm tắt QC + ổ đĩa, tải CPU, bộ nhớ tiến trình. Mọi phần đều được bảo vệ."""
    checks: list[dict] = []
    try:
        from core import qc
        for k, v in qc._load().items():
            if isinstance(v, dict):
                checks.append({"id": k, "name": v.get("name", k), "ok": bool(v.get("ok", True)), "fails": int(v.get("fails", 0) or 0), "detail": str(v.get("detail", ""))[:200]})
    except Exception:
        pass
    failing = [c for c in checks if not c["ok"]]
    disk = {"pct": 0, "free_gb": 0.0, "total_gb": 0.0}
    try:
        u = shutil.disk_usage(str(DATA_DIR))
        disk = {"pct": round(u.used / u.total * 100, 1) if u.total else 0, "free_gb": round(u.free / 1e9, 1), "total_gb": round(u.total / 1e9, 1)}
    except Exception:
        pass
    try:
        load = [round(x, 2) for x in os.getloadavg()]
    except Exception:
        load = []
    mem_mb = 0.0
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        mem_mb = round(rss / 1024 if os.uname().sysname != "Darwin" else rss / 1e6, 1)
    except Exception:
        pass
    text = (f"🩺 Sức khỏe: {len(checks) - len(failing)}/{len(checks)} kiểm tra QC ổn" + (" · lỗi: " + ", ".join(c["name"] for c in failing) if failing else "")
            + f"\nỔ đĩa {disk['pct']}% đã dùng (trống {disk['free_gb']} GB) · tải {'/'.join(map(str, load)) or '?'} · bộ nhớ bot {mem_mb} MB")
    return {"text": text, "checks": checks, "failing": len(failing), "disk": disk, "load": load, "mem_mb": mem_mb}


# ------------------------------------------------------------------ 3. chi phí
def record_llm(tokens_in: int = 0, tokens_out: int = 0, model: str = "", cost_usd: float | None = None) -> dict:
    """Cộng dồn token LLM theo ngày; llm.make_client() gọi hàm này sau mỗi lượt.
    Chi phí: ưu tiên chi phí thật OpenRouter trả về (cost_usd) quy đổi bằng biến USD_VND (anh đặt trên VPS);
    chưa có USD_VND thì chỉ cộng cost_usd, còn 'cost' (đ) theo bảng ops.json.llm_price[model] = {in, out} đ/1k token."""
    rate = float(os.getenv("USD_VND", "0") or 0)
    with _LOCK:
        d = _load()
        day = d["llm"].setdefault(_today(), {"calls": 0, "in": 0, "out": 0, "cost": 0})
        day.setdefault("cost_usd", 0.0)
        price = d["llm_price"].get(model) or d["llm_price"].get("default") or {}
        day["calls"] += 1
        day["in"] += int(tokens_in or 0)
        day["out"] += int(tokens_out or 0)
        if cost_usd is not None:
            day["cost_usd"] = round(day["cost_usd"] + float(cost_usd), 6)
        if cost_usd is not None and rate > 0:
            day["cost"] += float(cost_usd) * rate
        else:
            day["cost"] += int(tokens_in or 0) / 1000 * float(price.get("in", 0)) + int(tokens_out or 0) / 1000 * float(price.get("out", 0))
        for k in sorted(d["llm"])[:-KEEP_DAYS]:
            d["llm"].pop(k, None)
        _save(d)
    return {"text": f"Đã ghi {tokens_in}+{tokens_out} token ({model or 'mặc định'})."}


def _llm_estimate(d: dict) -> tuple[int, int]:
    """(số lượt gọi LLM, chi phí ước tính theo tháng) từ llm_usage.json nếu có, cộng bộ đếm ops.json."""
    calls, cost = 0, 0.0
    try:
        p = DATA_DIR / "llm_usage.json"
        if p.exists():
            calls += sum(1 for ln in p.read_text(encoding="utf-8", errors="ignore").splitlines() if ln.strip())
    except Exception:
        pass
    month = dt.date.today().strftime("%Y-%m")
    for day, v in d["llm"].items():
        if day.startswith(month):
            calls += int(v.get("calls", 0))
            cost += float(v.get("cost", 0))
    return calls, int(cost)


def llm_month() -> dict:
    """Tổng LLM tháng này của instance: lượt gọi, token, chi phí thật (USD) và quy đổi (đ)."""
    d = _load()
    month = dt.date.today().strftime("%Y-%m")
    out = {"month": month, "calls": 0, "in": 0, "out": 0, "cost_usd": 0.0, "cost": 0}
    for day, v in d["llm"].items():
        if day.startswith(month):
            for k in ("calls", "in", "out"):
                out[k] += int(v.get(k, 0))
            out["cost_usd"] += float(v.get("cost_usd", 0) or 0)
            out["cost"] += float(v.get("cost", 0) or 0)
    out["cost_usd"] = round(out["cost_usd"], 4)
    out["cost"] = int(out["cost"])
    out["text"] = (f"LLM tháng {month}: {out['calls']} lượt · {out['in'] + out['out']:,} token · ${out['cost_usd']:.2f}"
                   + (f" ≈ {_vnd(out['cost'])}" if out["cost"] else " (đặt USD_VND để quy đổi)"))
    return out


def cost_snapshot() -> dict:
    """Ảnh chụp chi phí hạ tầng mỗi ngày: chi phí cố định/tháng ÷ (1 + tenant đang chạy) + LLM. Giữ 90 ngày."""
    fixed = 0
    try:
        from agents import cfo
        fixed = int(cfo._monthly_costs(cfo._load()))
    except Exception:
        pass
    t = tenants()
    customers = 1 + t["active"]
    with _LOCK:
        d = _load()
        calls, llm_cost = _llm_estimate(d)
        per = round((fixed + llm_cost) / customers)
        snap = {"date": _today(), "fixed": fixed, "llm_cost": llm_cost, "llm_calls": calls, "tenants": t["count"], "active": t["active"], "per_customer": per}
        d["snapshots"][snap["date"]] = snap
        for k in sorted(d["snapshots"])[:-KEEP_DAYS]:
            d["snapshots"].pop(k, None)
        _save(d)
    text = f"💸 Chi phí hạ tầng: {_vnd(fixed)}/tháng cố định + LLM ~{_vnd(llm_cost)} ({calls} lượt) ÷ {customers} khách = {_vnd(per)}/khách/tháng."
    return {"text": text, **snap}


# ------------------------------------------------------------------ 4. ngưỡng
def thresholds() -> dict:
    """Ngưỡng cảnh báo hiện tại (mặc định + anh chỉnh)."""
    th = {**DEFAULT_THRESHOLDS, **_load()["thresholds"]}
    return {"text": f"Ngưỡng: ổ đĩa {th['disk_pct']}% · QC lỗi ≥{th['qc_fails']} · chi phí/khách {_vnd(th['cost_per_customer'])} · báo tenant dừng: {'có' if th['tenant_down'] else 'không'}.",
            "thresholds": th, "defaults": DEFAULT_THRESHOLDS}


def set_threshold(key: str, value) -> dict:
    """Đặt một ngưỡng: disk_pct | qc_fails | cost_per_customer | tenant_down."""
    if key not in DEFAULT_THRESHOLDS:
        raise ValueError("Ngưỡng không hợp lệ: " + ", ".join(DEFAULT_THRESHOLDS))
    if key == "tenant_down":
        val: Any = str(value).strip().lower() in ("1", "true", "yes", "có", "co", "on")
    else:
        val = int(float(str(value).replace(".", "").replace(",", "") or 0))
    with _LOCK:
        d = _load()
        d["thresholds"][key] = val
        _save(d)
    return {"text": f"Đã đặt ngưỡng {key} = {val}.", **thresholds()}


# ------------------------------------------------------------------ 5. cảnh báo
def check_alerts(auto_propose: bool = True) -> dict:
    """So sánh sức khỏe, chi phí, tenant với ngưỡng; mỗi vi phạm -> alert_once (6 giờ) và đề xuất lên bảng Phòng ban."""
    issues: list[dict] = []
    try:
        th = thresholds()["thresholds"]
        h, c, t = system_health(), cost_snapshot(), tenants()
        if h["disk"]["pct"] >= th["disk_pct"]:
            issues.append({"key": "disk", "title": f"Ổ đĩa đã dùng {h['disk']['pct']}% (ngưỡng {th['disk_pct']}%)", "why": f"Chỉ còn {h['disk']['free_gb']} GB trống.",
                           "impact": "Hết đĩa thì bot và tenant ngừng ghi dữ liệu.", "prio": "cao"})
        bad = [x for x in h["checks"] if not x["ok"] and x["fails"] >= th["qc_fails"]]
        if bad:
            issues.append({"key": "qc", "title": f"{len(bad)} kiểm tra QC lỗi kéo dài: " + ", ".join(x["name"] for x in bad)[:100],
                           "why": "; ".join(f"{x['name']}: {x['detail']}" for x in bad)[:600], "impact": "Tính năng liên quan không hoạt động với khách.", "prio": "cao"})
        if c["per_customer"] > th["cost_per_customer"]:
            issues.append({"key": "cost", "title": f"Chi phí hạ tầng {_vnd(c['per_customer'])}/khách vượt ngưỡng {_vnd(th['cost_per_customer'])}",
                           "why": f"Cố định {_vnd(c['fixed'])}/tháng, LLM {_vnd(c['llm_cost'])}, chia cho {1 + c['active']} khách.", "impact": "Biên lợi nhuận mỗi khách giảm.", "prio": "vua"})
        if th["tenant_down"]:
            down = [x["slug"] for x in t["items"] if not x.get("main") and x["state"] not in ("active", "unknown")]
            if down:
                issues.append({"key": "tenant", "title": "Tenant dừng: " + ", ".join(down)[:120], "why": "systemctl is-active không trả về active.",
                               "impact": "Khách không dùng được superYou.", "prio": "cao"})
        for it in issues:
            try:
                from core import security
                security.alert_once(f"ops:{it['key']}", f"🛠 Vận hành: {it['title']}\n{it['why'][:300]}", every=6 * 3600)
            except Exception:
                pass
            if auto_propose:
                try:
                    from agents import board
                    board.propose("ops", it["title"], it["why"], why=it["why"], impact=it["impact"], priority=it["prio"], by="Vận hành (AI)",
                                  auto_assign_to="product", key=f"ops:{it['key']}:{_today()}")
                except Exception:
                    pass
        with _LOCK:
            d = _load()
            d["issues_last"] = [{"key": i["key"], "title": i["title"], "at": _today()} for i in issues]
            _save(d)
    except Exception as e:
        issues.append({"key": "internal", "title": "Lỗi khi kiểm tra cảnh báo", "why": str(e)[:200], "impact": "", "prio": "thap"})
    text = "✅ Vận hành: không có vi phạm ngưỡng." if not issues else "⚠️ Vận hành phát hiện:\n" + "\n".join(f"• {i['title']}" for i in issues)
    return {"text": text, "issues": issues}


# ------------------------------------------------------------------ 6. báo cáo tuần
def weekly_report(to_board: bool = True) -> dict:
    """Báo cáo một trang sáng thứ Hai: uptime (QC), sự cố, chi phí/khách so với tuần trước, bảng tenant, ổ đĩa, 3 khuyến nghị."""
    try:
        d = _load()
        today = dt.date.today()
        wk = today.isocalendar()
        snaps = sorted(d["snapshots"].values(), key=lambda s: s["date"])
        this_w = [s for s in snaps if (today - dt.date.fromisoformat(s["date"])).days < 7]
        last_w = [s for s in snaps if 7 <= (today - dt.date.fromisoformat(s["date"])).days < 14]
        avg = lambda xs: round(sum(s["per_customer"] for s in xs) / len(xs)) if xs else 0  # noqa: E731
        cur, prev = avg(this_w), avg(last_w)
        trend = "" if not prev else f" ({'+' if cur >= prev else ''}{round((cur - prev) / prev * 100)}% so với tuần trước)"
        h, t = system_health(), tenants()
        fails = sum(c["fails"] for c in h["checks"])
        uptime = max(0.0, round(100 - min(100.0, fails * 5 / 2016 * 100), 2))  # mỗi lượt lỗi ≈ 5 phút trên 2016 lượt/tuần
        incidents = [c for c in h["checks"] if not c["ok"]] + [{"name": i["title"]} for i in d["issues_last"]]
        recs: list[str] = []
        if h["disk"]["pct"] >= 70:
            recs.append(f"Dọn data/videos, data/video_tmp hoặc nâng ổ đĩa (đang dùng {h['disk']['pct']}%).")
        if prev and cur > prev * 1.1:
            recs.append("Chi phí/khách tăng >10%: rà thuê bao ít dùng trong CFO › chi phí cố định, hoặc đẩy thêm khách để chia đều.")
        if t["count"] and t["active"] < t["count"]:
            recs.append("Có tenant không chạy: kiểm tra systemctl status superyou@<slug> và .env của khách.")
        if fails:
            recs.append("Xem chi tiết lỗi QC trong Mini App › Tình trạng hệ thống; lỗi lặp nên có việc sửa gốc trên bảng Phòng ban.")
        if t["count"] == 0:
            recs.append("Chưa có tenant: mời 1–2 khách thí điểm để đo chi phí thật trên mỗi khách.")
        recs += ["Giữ ảnh chụp chi phí mỗi ngày (23:40) để tuần sau có xu hướng.", "Đặt ngưỡng cảnh báo phù hợp trong Vận hành › Ngưỡng."]
        lines = [f"🛠 Vận hành superYou · tuần {wk[1]}/{wk[0]}",
                 f"Uptime (ước từ QC): {uptime}% · {fails} lượt kiểm tra lỗi · {len(incidents)} sự cố/cảnh báo",
                 f"Chi phí/khách: {_vnd(cur)}/tháng{trend} · cố định {_vnd(snaps[-1]['fixed']) if snaps else '?'}",
                 f"Tenant: {t['count']} khách, {t['active']} đang chạy · ổ đĩa {h['disk']['pct']}% (trống {h['disk']['free_gb']} GB)"]
        lines += [f"  {'🟢' if r['state'] == 'active' else '🔴'} {r['slug']} · {r['state']} · {r['size_mb']} MB" for r in t["items"]]
        if incidents:
            lines.append("Sự cố: " + "; ".join(i["name"] for i in incidents[:5]))
        lines.append("Khuyến nghị:\n" + "\n".join(f"{i + 1}. {r}" for i, r in enumerate(recs[:3])))
        text = "\n".join(lines)
        rep = {"week": f"{wk[0]}-W{wk[1]:02d}", "at": dt.datetime.now().strftime("%Y-%m-%dT%H:%M"), "text": text, "uptime": uptime, "per_customer": cur, "recs": recs[:3]}
        with _LOCK:
            d = _load()
            d["reports"] = [r for r in d["reports"] if r.get("week") != rep["week"]] + [rep]
            d["reports"] = d["reports"][-26:]
            _save(d)
        if to_board:
            try:
                from agents import board
                board.propose("ops", f"Báo cáo vận hành tuần {wk[1]}", text, why="Báo cáo định kỳ của phòng Vận hành (AI).", impact=f"Uptime {uptime}%, {_vnd(cur)}/khách",
                              priority="thap", by="Vận hành (AI)", auto_assign_to="product", key=f"ops:week:{rep['week']}")
            except Exception:
                pass
        return {"text": text, **rep}
    except Exception as e:
        return {"text": f"Không lập được báo cáo tuần: {e}", "error": str(e)[:200]}


# ------------------------------------------------------------------ 7. tổng quan
def _activation() -> dict:
    try:
        from core import activation
        return activation.summary(prefix="" if IS_TENANT else "acc:")
    except Exception as e:
        return {"text": f"Chưa đọc được số liệu kích hoạt: {e}"}


def overview() -> dict:
    """Số liệu cho thẻ dashboard Vận hành."""
    try:
        d = _load()
        h, t = system_health(), tenants()
        snaps = sorted(d["snapshots"].values(), key=lambda s: s["date"])
        last = snaps[-1] if snaps else {}
        rep = d["reports"][-1] if d["reports"] else {}
        return {"text": f"Vận hành: {h['failing']} kiểm tra lỗi · ổ đĩa {h['disk']['pct']}% · {t['active']}/{t['count']} tenant chạy · {_vnd(last.get('per_customer', 0))}/khách · {len(d['issues_last'])} vấn đề mở.",
                "health": {"total": len(h["checks"]), "failing": h["failing"], "checks": h["checks"]}, "disk": h["disk"], "load": h["load"], "mem_mb": h["mem_mb"],
                "tenants": {"count": t["count"], "active": t["active"], "items": t["items"]}, "cost": last, "cost_history": snaps[-30:],
                "issues": d["issues_last"], "llm_month": llm_month(), "activation": _activation(), "thresholds": thresholds()["thresholds"], "last_report": rep, "reports": d["reports"][-4:][::-1]}
    except Exception as e:
        return {"text": f"Không tải được tổng quan vận hành: {e}", "error": str(e)[:200]}
