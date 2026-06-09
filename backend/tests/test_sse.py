import asyncio
import json
import time

from app.api.sse import sse_with_heartbeat
from app.services.llm_client import LlmError


def _run(work, to_event, **kw) -> list[tuple[str, str]]:
    async def drain() -> list[tuple[str, str]]:
        events: list[tuple[str, str]] = []
        async for raw in sse_with_heartbeat(work, to_event, **kw):
            block = raw.decode("utf-8").strip()
            event = data = None
            for line in block.split("\n"):
                if line.startswith("event:"):
                    event = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data = line[len("data:"):].strip()
            events.append((event or "", data or ""))
        return events

    return asyncio.run(drain())


def test_emits_heartbeats_then_result() -> None:
    def work() -> dict:
        time.sleep(0.25)  # 阻塞，跨过两次 interval
        return {"value": "done"}

    events = _run(work, lambda r: json.dumps(r), interval=0.1)
    assert ("heartbeat", "{}") in events
    assert events[-1][0] == "result"
    assert json.loads(events[-1][1]) == {"value": "done"}


def test_emits_error_event_on_llm_error() -> None:
    def work() -> dict:
        raise LlmError("boom")

    events = _run(work, lambda r: json.dumps(r), interval=0.1)
    assert events[-1][0] == "error"
    assert json.loads(events[-1][1])["detail"] == "boom"


def test_error_event_includes_code_when_configured() -> None:
    def work() -> dict:
        raise ValueError("bad")

    events = _run(
        work, lambda r: json.dumps(r),
        interval=0.1, error_types=(LlmError, ValueError), error_code=502,
    )
    payload = json.loads(events[-1][1])
    assert events[-1][0] == "error"
    assert payload["code"] == 502
    assert payload["detail"] == "bad"
