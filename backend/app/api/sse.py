from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from typing import TypeVar

from app.services.llm_client import LlmError

logger = logging.getLogger(__name__)

SSE_HEADERS = {"X-Accel-Buffering": "no", "Cache-Control": "no-cache"}

T = TypeVar("T")

_HEARTBEAT = b"event: heartbeat\ndata: {}\n\n"


def _frame(event: str, data: str) -> bytes:
    return f"event: {event}\ndata: {data}\n\n".encode("utf-8")


async def sse_with_heartbeat(
    work: Callable[[], T],
    to_event: Callable[[T], str],
    *,
    interval: float = 10.0,
    error_types: tuple[type[BaseException], ...] = (LlmError,),
    error_code: int | None = None,
) -> AsyncIterator[bytes]:
    """在工作线程跑阻塞的 `work`；等待期间每 `interval` 秒发心跳；
    完成发 result 事件（`to_event` 返回已序列化的 JSON 字符串）；
    `work` 抛 `error_types` 之一时发 error 事件（可带 `code`）。其他异常向上传播（响亮失败）。"""
    task = asyncio.create_task(asyncio.to_thread(work))
    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=interval)
            if done:
                break
            yield _HEARTBEAT
    except asyncio.CancelledError:
        task.cancel()
        raise
    try:
        result = task.result()
    except error_types as error:
        logger.warning("sse work failed: %s", error)
        payload: dict[str, object] = {"detail": str(error)}
        if error_code is not None:
            payload["code"] = error_code
        yield _frame("error", json.dumps(payload, ensure_ascii=False))
        return
    yield _frame("result", to_event(result))
