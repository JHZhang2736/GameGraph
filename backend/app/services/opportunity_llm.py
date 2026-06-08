from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

import httpx
from pydantic import ConfigDict, Field

from app.schemas.artifacts import DeveloperProfile
from app.schemas.common import StrictBaseModel
from app.schemas.opportunity import CandidateOpportunityArea, RiskPosture

TOOL_NAME = "emit_opportunity_judgments"

SYSTEM_PROMPT = (
    "你是独立游戏创意系统的机会匹配判断器。"
    "给你开发者画像和一组『锚点×变形』候选机会区域（每个含图谱证据与稀缺度）。"
    "对每个候选给出判断：尊重硬约束(hard)，违反者 decision=reject 并说明；"
    "强偏好(strong_preference)可保留但 risk_posture=challenging 并在 risk_reason 写明警告；"
    "看似新颖但不自洽/做不出的候选 decision=reject 并说明为何行不通；"
    "尽量让保留的候选覆盖稳妥/平衡/挑战多种风险姿态。"
    "你不得修改候选的锚点、变形或稀缺度，只做判断。"
)


@dataclass(frozen=True)
class LlmSettings:
    base_url: str
    api_key: str
    model: str
    timeout: float

    @classmethod
    def from_env(cls) -> "LlmSettings":
        return cls(
            base_url=os.environ.get("LLM_BASE_URL", "").strip(),
            api_key=os.environ.get("LLM_API_KEY", "").strip(),
            model=os.environ.get("LLM_MODEL", "").strip(),
            timeout=float(os.environ.get("LLM_TIMEOUT", "30")),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


class OpportunityJudgment(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(min_length=1)
    decision: Literal["keep", "reject"]
    risk_posture: RiskPosture | None = None
    fit_reason: str | None = None
    risk_reason: str | None = None
    rejection_reason: str | None = None


class OpportunityJudgmentBatch(StrictBaseModel):
    model_config = ConfigDict(extra="ignore")

    judgments: list[OpportunityJudgment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def build_tool_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": "Return keep/reject judgments for the supplied opportunity candidates.",
                "parameters": OpportunityJudgmentBatch.model_json_schema(),
            },
        }
    ]


def _profile_block(profile: DeveloperProfile) -> str:
    lines = [
        f"团队:{profile.team_size} 时间:{profile.time_budget}",
        f"能力 程序:{profile.programming_ability} 美术:{profile.art_ability} "
        f"音频:{profile.audio_ability} 内容:{profile.content_production_ability}",
        f"喜欢:{', '.join(profile.liked_references)}",
        f"讨厌:{', '.join(profile.disliked_references_or_mechanics)}",
        f"期望体验:{', '.join(profile.desired_player_experiences)}",
        "约束:",
    ]
    for c in profile.constraints:
        lines.append(f"  - [{c.type.value}] {c.statement}")
    return "\n".join(lines)


def _candidate_block(candidates: list[CandidateOpportunityArea]) -> str:
    out = []
    for c in candidates:
        t = c.transformation
        change = f"{t.from_value}->{t.to_value}" if t.from_value else f"+{t.to_value}"
        out.append(
            f"[{c.id}] 锚点={c.anchor_summary} 变形={t.type.value}:{t.dimension}({change}) "
            f"已有相同组合的游戏数={c.existing_combination_count}（越少越新颖）"
        )
    return "\n".join(out)


class OpportunityLlmClient:
    def __init__(self, settings: LlmSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(timeout=settings.timeout)

    def judge(
        self, profile: DeveloperProfile, candidates: list[CandidateOpportunityArea]
    ) -> OpportunityJudgmentBatch:
        user = f"开发者画像：\n{_profile_block(profile)}\n\n候选机会：\n{_candidate_block(candidates)}"
        payload = {
            "model": self._settings.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            "tools": build_tool_schema(),
            "tool_choice": {"type": "function", "function": {"name": TOOL_NAME}},
        }
        response = self._client.post(
            f"{self._settings.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self._settings.api_key}"},
            json=payload,
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise ValueError(
                f"LLM request failed with {error.response.status_code}: {error.response.text}"
            ) from error
        data = response.json()
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise ValueError(f"Unexpected LLM response shape: {data}") from error
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            raise ValueError("LLM response missing tool_call")
        return OpportunityJudgmentBatch.model_validate_json(tool_calls[0]["function"]["arguments"])


def get_opportunity_llm_client() -> OpportunityLlmClient | None:
    settings = LlmSettings.from_env()
    if not settings.is_configured:
        return None
    return OpportunityLlmClient(settings)
