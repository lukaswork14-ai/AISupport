"""Biên bản thử ngay sau khi đăng ký (thẻ 15, họp liên phòng ban 17/10/2026).

Mục tiêu: người mới có kết quả đầu tiên trong <= 3 phút, không phải chờ dựng máy chủ riêng.
- Người dùng dán ghi chú cuộc họp (hoặc bấm "Dùng ví dụ mẫu") -> nhận biên bản: tóm tắt, quyết định, ai làm gì.
- Chỉ nhận VĂN BẢN (không ghi âm), nên không cần màn đồng ý ghi âm; giao diện vẫn báo rõ văn bản được xử lý bởi AI qua OpenRouter.
- Không lưu nội dung: chỉ trả kết quả về trình duyệt. Chỉ ghi sự kiện first_result (id + giờ) để đo kích hoạt.
- Tiết kiệm: tối đa PER_DAY lượt/tài khoản/ngày, GLOBAL_PER_DAY lượt/ngày toàn hệ thống, văn bản <= MAX_CHARS, đầu ra <= 1.500 token.
"""
import datetime as dt
import threading

from llm import ask_json

MAX_CHARS = 8000
MIN_CHARS = 60
PER_DAY = 5
GLOBAL_PER_DAY = 300
_LOCK = threading.Lock()
_COUNT: dict[str, int] = {}

SAMPLE = """Họp giao ban sáng thứ Hai, shop áo in theo yêu cầu. Có chị Lan (chủ shop), anh Minh (thiết kế), bạn Hoa (chăm sóc khách).
Chị Lan: tuần trước đơn giảm 15% so với tuần trước nữa, chủ yếu do mẫu Tết chưa lên. Minh nói mất 3 ngày nữa mới xong 10 mẫu Tết.
Hoa báo có 6 khách phàn nàn giao chậm, đều qua đơn vị vận chuyển A. Chị Lan quyết chuyển các đơn nội thành sang đơn vị B từ thứ Tư.
Chốt: Minh xong 10 mẫu Tết trước thứ Năm. Hoa gọi lại 6 khách phàn nàn trong hôm nay và tặng mã giảm 10%. Chị Lan làm việc với đơn vị B về giá.
Chưa chốt: có chạy quảng cáo cho mẫu Tết hay không, để họp thứ Sáu quyết."""

PROMPT = """Bạn là thư ký cuộc họp nói tiếng Việt, viết cho người không rành công nghệ.
Từ ghi chú dưới đây, trả về JSON đúng dạng:
{{"title": "tiêu đề ngắn", "summary": "2-3 câu tóm tắt", "decisions": ["quyết định đã chốt"],
  "next_steps": [{{"text": "việc cần làm", "owner": "ai làm (nếu có)", "due": "hạn (nếu có)"}}], "open_questions": ["việc chưa chốt"]}}
Chỉ dùng thông tin có trong ghi chú, không bịa tên, số hay hạn. Câu ngắn, lời đời thường.

GHI CHÚ:
{text}"""


def _quota(uid: str) -> None:
    today = dt.date.today().isoformat()
    with _LOCK:
        for k in [k for k in _COUNT if not k.startswith(today)]:
            _COUNT.pop(k, None)
        if _COUNT.get(f"{today}|*", 0) >= GLOBAL_PER_DAY:
            raise ValueError("Hôm nay lượt thử đã hết, bạn quay lại vào ngày mai nhé.")
        if _COUNT.get(f"{today}|{uid}", 0) >= PER_DAY:
            raise ValueError(f"Mỗi ngày bạn thử được {PER_DAY} biên bản. Quay lại vào ngày mai nhé.")
        _COUNT[f"{today}|{uid}"] = _COUNT.get(f"{today}|{uid}", 0) + 1
        _COUNT[f"{today}|*"] = _COUNT.get(f"{today}|*", 0) + 1


def make(uid: str, text: str = "", sample: bool = False) -> dict:
    text = SAMPLE if sample else (text or "").strip()
    if len(text) < MIN_CHARS:
        raise ValueError("Bạn dán thêm nội dung cuộc họp (ít nhất vài câu), hoặc bấm Dùng ví dụ mẫu.")
    text = text[:MAX_CHARS]
    _quota(uid)
    res = ask_json(PROMPT.format(text=text), max_tokens=1500, tag="trial_minutes",
                   ok=lambda r: isinstance(r, dict) and bool(r.get("summary")))
    if not res:
        raise ValueError("Trợ lý đang bận, bạn thử lại sau ít phút nhé.")
    out = {"title": str(res.get("title") or "Biên bản cuộc họp")[:120], "summary": str(res.get("summary") or "")[:800],
           "decisions": [str(x)[:240] for x in (res.get("decisions") or [])][:8],
           "next_steps": [{"text": str(x.get("text", ""))[:240], "owner": str(x.get("owner", "") or "")[:60], "due": str(x.get("due", "") or "")[:40]}
                          for x in (res.get("next_steps") or []) if isinstance(x, dict) and x.get("text")][:10],
           "open_questions": [str(x)[:240] for x in (res.get("open_questions") or [])][:6], "sample": bool(sample)}
    try:
        from core import activation
        activation.first_result(uid, "bien_ban_thu")
    except Exception:
        pass
    return out
