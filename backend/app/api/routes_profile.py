from __future__ import annotations

from fastapi import APIRouter, Depends

from app.schemas.developer_profile import ProfileParseInput, ProfileParseResult
from app.services.profile_llm import ProfileLlmClient, get_llm_client
from app.services.profile_parse_service import parse_profile

router = APIRouter()


@router.post("/profile/parse", response_model=ProfileParseResult)
def parse_profile_endpoint(
    document: ProfileParseInput,
    client: ProfileLlmClient | None = Depends(get_llm_client),
) -> ProfileParseResult:
    return parse_profile(document, client)
