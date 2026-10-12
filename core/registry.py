"""Sổ đăng ký trung tâm: mọi agent/công cụ khai báo ở đây MỘT LẦN, rồi tự xuất hiện ở 3 nơi:
1) Super bot (LLM tool calling)  2) Mini App (tab Agents tự sinh form)  3) API cho các tích hợp sau này.

Thêm công cụ mới = viết 1 hàm Python trả về dict kết quả + register(Agent(...)) trong hub.py. Không cần sửa UI hay super bot."""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

log = logging.getLogger("registry")


@dataclass
class Param:
    name: str
    label: str
    type: str = "text"          # text | textarea | number | select | bool
    options: list | None = None  # cho select: [{"value":..., "label":...}] hoặc list chuỗi
    default: Any = None
    required: bool = False
    hint: str = ""


@dataclass
class Action:
    id: str
    label: str
    fn: Callable[..., dict]       # hàm đồng bộ, nhận **params, trả dict kết quả (xem RESULT)
    icon: str = "▶️"
    desc: str = ""
    params: list[Param] = field(default_factory=list)
    llm: bool = False             # cho super bot gọi như một tool
    long: bool = False            # chạy nền (job) vì tốn thời gian: video, viết bài...
    hidden: bool = False          # không hiện trong tab Agents (chỉ dùng nội bộ / tab riêng)


@dataclass
class Agent:
    id: str
    name: str
    icon: str
    desc: str
    actions: list[Action]
    order: int = 100


# RESULT (dict trả về của mọi action), các khóa đều tùy chọn:
#   text: str          văn bản thuần (super bot đọc cái này)
#   image / video: str đường dẫn file trong thư mục data/ (Mini App tự hiển thị)
#   items: list        dữ liệu có cấu trúc cho UI (tin, nội dung...)
#   content_id: str    nếu action tạo ra một nội dung trong Studio
#   open_url: str      link nên mở (ví dụ group để dán bài)

REGISTRY: dict[str, Agent] = {}


def register(agent: Agent):
    REGISTRY[agent.id] = agent


def get_action(agent_id: str, action_id: str) -> Action:
    ag = REGISTRY.get(agent_id)
    act = next((a for a in (ag.actions if ag else []) if a.id == action_id), None)
    if not act:
        raise KeyError(f"Không có công cụ {agent_id}.{action_id}")
    return act


def _coerce(p: Param, v):
    if v is None or v == "":
        return p.default
    if p.type == "number":
        return int(v) if float(v).is_integer() else float(v)
    if p.type == "bool":
        return v in (True, "true", "1", 1, "on")
    return v


def run(agent_id: str, action_id: str, params: dict | None = None) -> dict:
    act = get_action(agent_id, action_id)
    params = params or {}
    kwargs = {}
    for p in act.params:
        v = _coerce(p, params.get(p.name))
        if p.required and v in (None, ""):
            raise ValueError(f"Thiếu thông tin: {p.label}")
        if v is not None:
            kwargs[p.name] = v
    out = act.fn(**kwargs)
    return out if isinstance(out, dict) else {"text": str(out)}


def describe() -> list[dict]:
    """Danh mục cho Mini App."""
    res = []
    for ag in sorted(REGISTRY.values(), key=lambda a: a.order):
        res.append({
            "id": ag.id, "name": ag.name, "icon": ag.icon, "desc": ag.desc,
            "actions": [{"id": a.id, "label": a.label, "icon": a.icon, "desc": a.desc, "long": a.long,
                         "params": [asdict(p) for p in a.params]} for a in ag.actions if not a.hidden],
        })
    return res


# ------------------------------------------------------------ super bot tools
_TYPE = {"number": "number", "bool": "boolean"}


def llm_tools() -> list[dict]:
    tools = []
    for ag in REGISTRY.values():
        for a in ag.actions:
            if not a.llm:
                continue
            props, req = {}, []
            for p in a.params:
                sch = {"type": _TYPE.get(p.type, "string"), "description": p.label + (f" ({p.hint})" if p.hint else "")}
                if p.type == "select" and p.options:
                    sch["enum"] = [o["value"] if isinstance(o, dict) else o for o in p.options]
                props[p.name] = sch
                if p.required:
                    req.append(p.name)
            tools.append({"type": "function", "function": {
                "name": f"{ag.id}__{a.id}", "description": f"[{ag.name}] {a.label}. {a.desc}".strip(),
                "parameters": {"type": "object", "properties": props, "required": req}}})
    return tools


def run_tool(name: str, args: dict) -> dict:
    agent_id, _, action_id = name.partition("__")
    return run(agent_id, action_id, args)
