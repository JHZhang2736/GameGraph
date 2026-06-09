"""api 测试共用：把 SSE 响应体解析出 result/error。"""
from __future__ import annotations

import json


def sse_events(response) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    for block in response.text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event = data = None
        for line in block.split("\n"):
            if line.startswith("event:"):
                event = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data = line[len("data:"):].strip()
        if event is not None:
            events.append((event, data or ""))
    return events


def sse_result(response) -> object:
    """返回 result 事件解析后的 JSON；遇 error 事件则断言失败。"""
    for event, data in sse_events(response):
        if event == "result":
            return json.loads(data)
        if event == "error":
            raise AssertionError(f"unexpected SSE error event: {data}")
    raise AssertionError("no result event in SSE stream")


def sse_error(response) -> dict:
    """返回 error 事件解析后的 dict；无则断言失败。"""
    for event, data in sse_events(response):
        if event == "error":
            return json.loads(data)
    raise AssertionError("no error event in SSE stream")
