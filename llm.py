"""Client gọi mô hình qua OpenRouter (giao thức OpenAI-compatible)."""
from openai import OpenAI

from config import LLM_API_KEY, LLM_BASE_URL


def make_client() -> OpenAI:
    return OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY, timeout=90)


# Model suy luận (DeepSeek...) dễ "nghĩ" hết ngân sách token và trả lời rỗng: giới hạn mức suy luận.
LLM_EXTRA = {"reasoning": {"effort": "low"}}

# Tham số chống lặp từ cho các bản tóm tắt dài (DeepSeek Flash đôi khi lặp "truy truy truy...")
# Lưu ý: phạt lặp cao làm hỏng dấu tiếng Việt ("Cả nh bá o") vì dấu là token lặp nhiều -> giữ mức nhẹ.
ANTI_REPEAT = {"temperature": 0.5, "frequency_penalty": 0.1}
# Cho đầu ra ngắn, có cấu trúc (phân loại, JSON): không phạt lặp.
PRECISE = {"temperature": 0.2}


def fix_vi(text: str) -> str:
    """Chuẩn hoá Unicode (NFC) để dấu tiếng Việt hiển thị đúng."""
    import unicodedata
    return unicodedata.normalize("NFC", text or "")


def garbled(text: str) -> bool:
    """True nếu tiếng Việt bị vỡ dấu: còn dấu rời sau NFC, hoặc quá nhiều mảnh chữ 1-2 ký tự có dấu."""
    import re
    import unicodedata
    t = fix_vi(text)
    if re.search(r"[\u0300-\u036f\u02b9-\u02ff]", t) or re.search(r"[\u2018\u2019]\S", t):
        return True
    words = re.findall(r"\w+", t)
    if len(words) < 6:
        return False
    if sum(1 for w in words if not w.isascii()) / len(words) < 0.15:  # không phải tiếng Việt
        return False
    # mảnh vỡ: chỉ có phụ âm ("nh", "p", "cc") hoặc nguyên âm trơ ("i", "o") đứng riêng
    frag = sum(1 for w in words if re.fullmatch(r"[bcdđghklmnpqrstvx]{1,3}|[ieou]", w))
    return frag >= 3 and frag / len(words) > 0.04


def degenerate(text: str) -> bool:
    """True nếu văn bản bị lặp từ bất thường, vỡ dấu hoặc rỗng."""
    import re
    if not text or len(text.strip()) < 20:
        return True
    return bool(re.search(r"\b(\S{1,12})(\s+\1\b){5,}", text)) or garbled(text)


# ------------------------------------------------------------------ JSON bền vững
def parse_json(text: str, kind: str = "{"):
    """Bóc JSON từ câu trả lời của model: bỏ ```fences```, sửa dấu phẩy thừa, cứu phần còn dùng được nếu bị cắt cụt."""
    import json
    import re
    t = fix_vi(text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.M)
    close = "}" if kind == "{" else "]"
    i = t.find(kind)
    if i < 0:
        return None
    t = t[i:]
    j = t.rfind(close)
    cand = [t[:j + 1]] if j > 0 else []
    for c in cand:
        for s in (c, re.sub(r",\s*([}\]])", r"\1", c)):
            try:
                return json.loads(s)
            except Exception:
                pass
    # bị cắt cụt: thử cắt dần tới object con hoàn chỉnh cuối cùng rồi đóng ngoặc
    stack, last_ok = [], []
    instr = esc = False
    for k, ch in enumerate(t):
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
            continue
        if ch == '"':
            instr = True
        elif ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()
            last_ok.append((k, list(stack)))
    for k, st in reversed(last_ok[-60:]):
        s = t[:k + 1] + "".join("}" if x == "{" else "]" for x in reversed(st))
        try:
            return json.loads(re.sub(r",\s*([}\]])", r"\1", s))
        except Exception:
            continue
    return None


def _local_pick(task: str, tools: bool = False):
    """superYou Private: chạy tại chỗ nếu chế độ hybrid/strict cho phép (xem core/private_llm)."""
    try:
        from core import private_llm
        return private_llm.pick(task, tools)
    except Exception:
        return False, ""


def _local_client():
    from core import private_llm
    return private_llm.client()


def ask_json(prompt: str, max_tokens: int = 6000, tries: int = 2, ok=None, tag: str = "json", kind: str = "{"):
    """Gọi model lấy JSON; ok(res)->bool để kiểm tra. Lỗi thì ghi nguyên văn vào data/llm_fail.log để chẩn đoán."""
    import datetime as _dt
    from config import DATA_DIR, LLM_MODEL
    last = ""
    for n in range(tries):
        # Lượt 1: tắt suy luận (model hay "nghĩ" hết ngân sách rồi trả rỗng với prompt dài); lượt sau: suy luận nhẹ.
        kw = {"response_format": {"type": "json_object"}} if kind == "{" and n == 0 else {}
        extra = {"reasoning": {"enabled": False}} if n == 0 else {"reasoning": {"effort": "low", "max_tokens": 1500}}
        try:
            local, lmodel = _local_pick("json" if max_tokens <= 2500 else "long")
            if local:
                r = _local_client().chat.completions.create(model=lmodel, max_tokens=max_tokens, **PRECISE,
                                                            messages=[{"role": "user", "content": prompt}], **kw)
            else:
                r = make_client().chat.completions.create(model=LLM_MODEL, extra_body=extra, max_tokens=max_tokens, **PRECISE,
                                                          messages=[{"role": "user", "content": prompt}], **kw)
            last += f"\n--- lượt {n + 1}\n" + (r.choices[0].message.content or "")[-1800:] + f"\n[finish={r.choices[0].finish_reason} usage={getattr(r, 'usage', '')}]"
            res = parse_json(r.choices[0].message.content, kind)
            if res is not None and (ok is None or ok(res)):
                return res
        except Exception as e:  # noqa: BLE001
            last += f"\n--- lượt {n + 1} [lỗi gọi model] {e}"
    try:
        with open(DATA_DIR / "llm_fail.log", "a", encoding="utf-8") as f:
            f.write(f"\n===== {_dt.datetime.now():%Y-%m-%d %H:%M} {tag}\n{last[-4000:]}\n")
    except Exception:
        pass
    return None
