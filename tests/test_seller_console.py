"""Console người bán (mảng Thương mại): tạo sản phẩm loại "pack" (skill + workflow + ghi chú), xem trước theo loại,
doanh thu theo sản phẩm và lịch chi trả. Mỗi test một SUPERHUY_HOME riêng, không gọi mạng."""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(tmp: Path, code: str) -> dict:
    home = tmp / "home"
    home.mkdir(parents=True, exist_ok=True)
    (home / ".env").write_text("TELEGRAM_TOKEN=1:test\nOWNER_CHAT_ID=1001\nLLM_API_KEY=test\n")
    env = {k: v for k, v in os.environ.items()
           if k not in ("TELEGRAM_TOKEN", "OWNER_CHAT_ID", "LLM_API_KEY", "SUPERYOU_TENANT", "SUPERYOU_PAYMENTS", "APP_PIN_HASH")}
    env.update({"SUPERHUY_HOME": str(home), "OBSIDIAN_VAULT": str(home / "vault"), "PYTHONPATH": str(ROOT), "SUPERYOU_PAYMENTS": "1"})
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=90)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


PRE = r"""
import json
from agents import market, pay
s = market.creator_signup("Lan POD", "lan@shop.vn", "Bán áo POD")
c = market.creator_auth(s["key"])
SKILL = "1. Mỗi sáng đọc đơn mới và tồn kho.\n2. Báo chủ shop đơn trễ quá 2 ngày.\n3. Gợi ý nhập hàng khi tồn dưới 10."
PACK = {"type": "pack", "name": "Phòng vận hành shop POD", "tagline": "Vận hành shop POD mỗi sáng thay bạn, không sót đơn",
        "description": "Dành cho chủ shop POD bán trên Etsy và Shopee. " * 4, "body": SKILL, "category": "ban-hang", "price": 199000,
        "pack_roles": "Điều phối đơn, Kiểm kho", "pack_steps": "lich.ngay: Lịch hôm nay\nlark.tomtat: Tóm tắt Lark",
        "pack_notes": "# Quy trình xử lý đơn trễ\n1. Gọi xưởng in.\n# Mẫu tin nhắn xin lỗi khách\nChào bạn…"}
"""


def test_pack_create_edit_roundtrip(tmp_path):
    r = _run(tmp_path, PRE + r"""
sv = market.creator_save(c, dict(PACK, submit=True))
x = market.get_listing(sv["id"])
g = market.creator_get(c, sv["id"])
print(json.dumps({"status": sv["status"], "type": x["type"], "steps": len(x["content"]["steps"]), "notes": [n["title"] for n in x["content"]["notes"]],
                  "roles": x["content"]["roles"], "skill_ok": x["content"]["skill"].startswith("1."), "g_steps": g["pack_steps"], "g_roles": g["pack_roles"],
                  "g_notes_first": g["pack_notes"].splitlines()[0]}))
""")
    assert r["status"] == "review" and r["type"] == "pack" and r["steps"] == 2 and r["skill_ok"]
    assert r["notes"] == ["Quy trình xử lý đơn trễ", "Mẫu tin nhắn xin lỗi khách"]
    assert r["roles"] == ["Điều phối đơn", "Kiểm kho"] and r["g_roles"] == "Điều phối đơn, Kiểm kho"
    assert r["g_steps"].startswith("lich.ngay: Lịch hôm nay") and r["g_notes_first"] == "# Quy trình xử lý đơn trễ"


def test_pack_rejects_unsafe_step_and_secret(tmp_path):
    r = _run(tmp_path, PRE + r"""
out = {}
for k, extra in (("unsafe", {"pack_steps": "gmail.gui: Gửi thư"}), ("secret", {"pack_notes": "# Cấu hình\napi_key = sk-abcdefghijklmnop"})):
    try:
        market.creator_save(c, dict(PACK, submit=True, **extra)); out[k] = "saved"
    except ValueError as e:
        out[k] = "refused"
print(json.dumps(out))
""")
    assert r == {"unsafe": "refused", "secret": "refused"}


def test_preview_by_type(tmp_path):
    r = _run(tmp_path, PRE + r"""
pk = market.creator_preview(c, PACK)
wf = market.creator_preview(c, {"type": "workflow", "name": "Sáng", "body": "lich.ngay: Lịch hôm nay"})
br = market.creator_preview(c, {"type": "brain", "name": "Kho", "body": "# A\nx\n# B\ny"})
bad = market.creator_preview(c, {"type": "workflow", "name": "X", "body": "không phải bước"})
print(json.dumps({"pk": [pk["spec"]["kind"], pk["spec"]["step_count"], pk["spec"]["note_count"], len(pk["spec"]["roles"])],
                  "wf": [wf["spec"]["kind"], wf["spec"]["step_count"]], "br": [br["spec"]["kind"], br["spec"]["note_count"]], "bad": bool(bad["error"])}))
""")
    assert r == {"pk": ["pack", 2, 2, 2], "wf": ["workflow", 1], "br": ["brain", 2], "bad": True}


def test_revenue_by_product_hold_and_next_payout(tmp_path):
    r = _run(tmp_path, PRE + r"""
sv = market.creator_save(c, dict(PACK, submit=True))
market.approve_publish(sv["id"], 199000)
ids = []
for e in ("a@x.vn", "b@x.vn"):
    o = pay.create_order(sv["id"], e)["order"]; pay.confirm_manual(o["id"]); ids.append(o["id"])
pay.refund(ids[1], "khách đổi ý")
rv = pay.seller_revenue(c["id"])
print(json.dumps({"balance": rv["balance"], "hold": rv["in_refund_window"], "next": rv["next_amount"], "ready": rv["next_ready"], "note": rv["next_note"],
                  "prod": [rv["by_product"][0]["sales"], rv["by_product"][0]["refunds"], rv["by_product"][0]["earned"]], "months": len(rv["months"])}))
""")
    assert r["balance"] == 159200 and r["hold"] == 159200  # 199.000 - 20% ; đơn hoàn không tính vào phần giữ
    assert r["next"] == 0 and r["ready"] is False and "cộng dồn" in r["note"]  # dưới 200.000đ
    assert r["prod"] == [2, 1, 159200] and r["months"] == 6
