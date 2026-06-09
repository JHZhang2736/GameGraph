from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import Field

from app.graph.connection import create_driver
from app.graph.opportunity_repository import OpportunityRepository
from app.schemas.artifacts import DeveloperProfile, OpportunityFrame
from app.schemas.common import NonEmptyStr, StrictBaseModel
from app.schemas.opportunity import OpportunityArea, OpportunityMatchResult
from app.services.opportunity_frame_llm import (
    OpportunityFrameLlmClient,
    get_opportunity_frame_llm_client,
)
from app.services.opportunity_frame_service import build_frame
from app.services.opportunity_llm import (
    OpportunityLlmClient,
    get_opportunity_llm_client,
)
from app.services.opportunity_service import match_opportunities

router = APIRouter()

_driver = None


def get_opportunity_repository() -> OpportunityRepository:
    # 默认 provider：惰性创建单例 driver。测试通过 dependency_overrides 覆盖本函数。
    global _driver
    if _driver is None:
        _driver = create_driver()
    return OpportunityRepository(_driver)


def get_opportunity_llm() -> OpportunityLlmClient | None:
    # 默认 provider：返回可选 LLM 客户端。测试通过 dependency_overrides 覆盖本函数。
    return get_opportunity_llm_client()


class OpportunityMatchRequest(StrictBaseModel):
    profile: DeveloperProfile
    seen_ids: list[NonEmptyStr] = Field(default_factory=list)


@router.post("/opportunity/match", response_model=OpportunityMatchResult)
def match_endpoint(
    request: OpportunityMatchRequest,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityLlmClient | None = Depends(get_opportunity_llm),
) -> OpportunityMatchResult:
    return match_opportunities(
        request.profile, repository, llm_client, seen_ids=request.seen_ids
    )


class OpportunityFrameRequest(StrictBaseModel):
    profile: DeveloperProfile
    area: OpportunityArea


def get_opportunity_frame_llm() -> OpportunityFrameLlmClient | None:
    # 默认 provider：返回可选 frame LLM 客户端。测试通过 dependency_overrides 覆盖。
    return get_opportunity_frame_llm_client()


@router.post("/opportunity/frame", response_model=OpportunityFrame)
def frame_endpoint(
    request: OpportunityFrameRequest,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityFrameLlmClient | None = Depends(get_opportunity_frame_llm),
) -> OpportunityFrame:
    return build_frame(request.profile, request.area, repository, llm_client)
