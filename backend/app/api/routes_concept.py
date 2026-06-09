from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.sse import SSE_HEADERS, sse_with_heartbeat
from app.schemas.artifacts import OpportunityFrame
from app.schemas.common import StrictBaseModel
from app.services.concept_llm import ConceptLlmClient, get_concept_llm_client
from app.services.concept_service import generate_concepts
from app.services.llm_client import LlmError

router = APIRouter()
logger = logging.getLogger(__name__)


class ConceptGenerateRequest(StrictBaseModel):
    frame: OpportunityFrame


def get_concept_llm() -> ConceptLlmClient | None:
    # 默认 provider：返回可选概念生成 LLM 客户端。测试通过 dependency_overrides 覆盖。
    return get_concept_llm_client()


@router.post("/concept/generate")
async def generate_endpoint(
    request: ConceptGenerateRequest,
    llm_client: ConceptLlmClient | None = Depends(get_concept_llm),
) -> StreamingResponse:
    # 硬依赖 LLM：未配置 → 开流前 503（HTTP 状态保留）。
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 LLM，概念生成不可用。")

    def work():
        try:
            return generate_concepts(request.frame, llm_client)
        except (LlmError, ValueError) as error:
            logger.warning("concept generation failed: %s", error)
            raise LlmError("概念生成失败，请稍后重试。") from error

    def to_event(cards) -> str:
        return json.dumps([c.model_dump(mode="json") for c in cards], ensure_ascii=False)

    return StreamingResponse(
        sse_with_heartbeat(
            work, to_event, error_types=(LlmError, ValueError), error_code=502
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
