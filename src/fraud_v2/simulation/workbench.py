from __future__ import annotations

from pydantic import BaseModel, Field

from fraud_v2.domain.decisions import RiskSignal
from fraud_v2.domain.enums import DecisionAction, RiskTier
from fraud_v2.policy.thresholds import ThresholdPolicy, default_threshold_policy


class SimulationRequest(BaseModel):
    amount: float = Field(default=750.0, ge=0)
    virtual_camera: bool = False
    low_behavior_entropy: bool = False
    high_application_velocity: bool = False
    payment_velocity: bool = False
    prior_chargeback: bool = False
    one_hop_from_fraud: bool = False
    public_kyb_watch: bool = False
    sanctions_hit: bool = False
    app_bec_pattern: bool = False
    model_or_graph_outage: bool = False


class SimulationResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    tier: RiskTier
    action: DecisionAction
    degraded: bool
    signals: list[RiskSignal]
    safe_reasons: list[str]
    policy_version: str
    local_only: bool = True
    no_real_action: bool = True


def run_simulation(
    request: SimulationRequest,
    policy: ThresholdPolicy | None = None,
) -> SimulationResponse:
    active_policy = policy or default_threshold_policy()
    signals = _signals(request, active_policy)
    score = min(100, sum(signal.severity for signal in signals))
    if request.model_or_graph_outage:
        score = max(active_policy.degraded_min_score, score)
    tier, action = active_policy.tier_action(score, request.model_or_graph_outage)
    if action == DecisionAction.MANUAL_REVIEW and request.app_bec_pattern:
        action = DecisionAction.BREAK_THE_SPELL
    return SimulationResponse(
        score=score,
        tier=tier,
        action=action,
        degraded=request.model_or_graph_outage,
        signals=signals,
        safe_reasons=[signal.safe_reason for signal in signals]
        or ["No local workbench risk signals selected."],
        policy_version=active_policy.version,
    )


def _signals(request: SimulationRequest, policy: ThresholdPolicy) -> list[RiskSignal]:
    signals: list[RiskSignal] = []
    _add(
        signals,
        request.amount >= policy.high_request_amount_threshold,
        "HIGH_REQUEST_AMOUNT",
        policy.high_request_amount_severity,
        policy.high_request_amount_reason,
        "policy",
    )
    _add(
        signals,
        request.virtual_camera,
        "CAMERA_METADATA_ANOMALY",
        20,
        "Camera metadata is missing or indicates a virtual camera.",
        "simulation",
    )
    _add(
        signals,
        request.low_behavior_entropy,
        "LOW_BEHAVIOR_ENTROPY",
        25,
        "Session behavior has very low human-like variation.",
        "simulation",
    )
    _add(
        signals,
        request.high_application_velocity,
        "APPLICATIONS_PER_DEVICE_VELOCITY",
        35,
        "Several applications used the same device in a short window.",
        "simulation",
    )
    _add(
        signals,
        request.payment_velocity,
        "PAYMENT_ATTEMPT_VELOCITY",
        25,
        "Several payment attempts happened in a short window.",
        "simulation",
    )
    _add(
        signals,
        request.prior_chargeback,
        "PRIOR_CHARGEBACK",
        45,
        "A prior chargeback or dispute exists for this user.",
        "simulation",
    )
    _add(
        signals,
        request.one_hop_from_fraud,
        "ONE_HOP_FROM_CONFIRMED_FRAUD",
        45,
        "This applicant shares a high-confidence connection with confirmed fraud.",
        "simulation",
    )
    _add(
        signals,
        request.public_kyb_watch,
        "PUBLIC_KYB_WATCH",
        20,
        "Public KYB-style inputs need review before trust is granted.",
        "simulation",
    )
    _add(
        signals,
        request.sanctions_hit,
        "PUBLIC_SANCTIONS_HIT",
        60,
        "A local sanctions-style flag is present and requires human review.",
        "simulation",
    )
    _add(
        signals,
        request.app_bec_pattern,
        "APP_BEC_PATTERN",
        25,
        "Payment instructions look unusual enough to show a Break-the-Spell prompt.",
        "simulation",
    )
    _add(
        signals,
        request.model_or_graph_outage,
        "DEPENDENCY_DEGRADED",
        0,
        "A model or graph dependency is degraded, so the simulator routes to review.",
        "simulation",
    )
    return signals


def _add(
    signals: list[RiskSignal],
    condition: bool,
    code: str,
    severity: int,
    safe_reason: str,
    source: str,
) -> None:
    if condition:
        signals.append(
            RiskSignal(code=code, severity=severity, safe_reason=safe_reason, source=source)
        )
