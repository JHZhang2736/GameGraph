from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.artifacts import ConceptCard, OpportunityFrame
from app.schemas.common import StrictBaseModel
from app.services.concept_llm import ConceptLlmClient, get_concept_llm_client
from app.services.concept_service import generate_concepts
from app.services.llm_client import LlmError

router = APIRouter()


class ConceptGenerateRequest(StrictBaseModel):
    frame: OpportunityFrame


def get_concept_llm() -> ConceptLlmClient | None:
    # 默认 provider：返回可选概念生成 LLM 客户端。测试通过 dependency_overrides 覆盖。
    return get_concept_llm_client()


@router.post("/concept/generate", response_model=list[ConceptCard])
def generate_endpoint(
    request: ConceptGenerateRequest,
    llm_client: ConceptLlmClient | None = Depends(get_concept_llm),
) -> list[ConceptCard]:
    # 强依赖 LLM：未配置 → 503；调用失败/产物非法（ValueError，含 ValidationError 子类）→ 502。
    if llm_client is None:
        raise HTTPException(status_code=503, detail="未配置 LLM，概念生成不可用。")
    try:
        return generate_concepts(request.frame, llm_client)
    except (LlmError, ValueError) as error:
        raise HTTPException(status_code=502, detail=f"LLM 概念生成失败：{error}") from error
