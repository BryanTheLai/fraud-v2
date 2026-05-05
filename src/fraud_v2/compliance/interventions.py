from __future__ import annotations

from pydantic import BaseModel, Field

from fraud_v2.domain.decisions import DecisionResponse


class BreakSpellDraft(BaseModel):
    channel: str = "demo_only"
    title: str = "Break-the-Spell intervention"
    message: str = Field(min_length=40)
    checklist: list[str]
    risk_reasons: list[str]
    no_real_message_sent: bool = True


def build_break_spell_draft(decision: DecisionResponse) -> BreakSpellDraft:
    reasons = decision.safe_reasons[:3]
    return BreakSpellDraft(
        message=(
            "Pause before continuing. Confirm you personally know the recipient, "
            "the payment instructions came through a trusted channel, and nobody is "
            "pressuring you to keep this transfer secret."
        ),
        checklist=[
            "Call the known recipient using a saved number, not a number from the new message.",
            "Check whether the payee or bank account changed recently.",
            "Stop if the sender claims urgency, secrecy, or law-enforcement involvement.",
        ],
        risk_reasons=reasons or ["Local policy routed this payment for extra confirmation."],
    )
