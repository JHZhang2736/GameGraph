from __future__ import annotations

from typing import Protocol

from app.schemas.artifacts import ConceptCard, OpportunityFrame
from app.services.concept_llm import ConceptGenerationBatch


class SupportsConceptGeneration(Protocol):
    def generate(self, frame: OpportunityFrame) -> ConceptGenerationBatch: ...


def generate_concepts(
    frame: OpportunityFrame,
    llm_client: SupportsConceptGeneration,
) -> list[ConceptCard]:
    # llm_client 非 None（None 由路由前置拦成 503）。generate 失败抛 LlmError；
    # ConceptCard(...) 对非法草稿抛 ValidationError（ValueError 子类）；路由把两者都映射 502。
    batch = llm_client.generate(frame)
    return [
        ConceptCard(
            id=f"concept|{frame.id}|{i}",
            opportunity_frame_id=frame.id,
            **draft.model_dump(),
        )
        for i, draft in enumerate(batch.concepts, start=1)
    ]
