from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.sse import SSE_HEADERS, sse_with_heartbeat
from app.schemas.developer_profile import ProfileParseInput
from app.services.profile_llm import ProfileLlmClient, get_llm_client
from app.services.profile_parse_service import parse_profile

router = APIRouter()

@router.post("/profile/parse")
async def parse_profile_endpoint(
    document: ProfileParseInput,
    client: ProfileLlmClient | None = Depends(get_llm_client),
) -> StreamingResponse:
    def work():
        return parse_profile(document, client)

    return StreamingResponse(
        sse_with_heartbeat(work, lambda r: r.model_dump_json()),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
