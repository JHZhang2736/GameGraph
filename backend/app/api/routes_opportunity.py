from __future__ import annotations

from fastapi import APIRouter, Depends

from app.graph.connection import create_driver
from app.graph.opportunity_repository import OpportunityRepository
from app.schemas.artifacts import DeveloperProfile
from app.schemas.opportunity import OpportunityMatchResult
from app.services.opportunity_llm import (
    OpportunityLlmClient,
    get_opportunity_llm_client,
)
from app.services.opportunity_service import match_opportunities

router = APIRouter()

_driver = None


def get_opportunity_repository() -> OpportunityRepository:
    global _driver
    if _driver is None:
        _driver = create_driver()
    return OpportunityRepository(_driver)


def get_opportunity_llm() -> OpportunityLlmClient | None:
    return get_opportunity_llm_client()


@router.post("/opportunity/match", response_model=OpportunityMatchResult)
def match_endpoint(
    profile: DeveloperProfile,
    repository: OpportunityRepository = Depends(get_opportunity_repository),
    llm_client: OpportunityLlmClient | None = Depends(get_opportunity_llm),
) -> OpportunityMatchResult:
    return match_opportunities(profile, repository, llm_client)
