from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from fraud_v2.compliance.reasons import adverse_action_style_reasons
from fraud_v2.domain.decisions import DecisionResponse
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import DecisionAction, RiskTier


class ComplianceDraft(BaseModel):
    draft_id: UUID = Field(default_factory=uuid4)
    draft_type: str = "adverse_action_summary"
    decision_id: UUID
    target_entity: EntityRef
    risk_tier: RiskTier
    simulated_action: DecisionAction
    safe_reasons: list[str]
    human_review_required: bool = True
    legal_disclaimer: str = (
        "Local synthetic draft only. This is not legal advice, not a regulatory filing, "
        "and not an automated adverse action notice."
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def build_compliance_draft(decision: DecisionResponse) -> ComplianceDraft:
    return ComplianceDraft(
        decision_id=decision.decision_id,
        target_entity=decision.target_entity,
        risk_tier=decision.risk_tier,
        simulated_action=decision.action,
        safe_reasons=adverse_action_style_reasons(decision),
    )


def write_compliance_draft(decision: DecisionResponse, output_path: Path) -> ComplianceDraft:
    draft = build_compliance_draft(decision)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(draft.model_dump(mode="json"), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return draft
