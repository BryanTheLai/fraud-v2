from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from fraud_v2.domain.decisions import DecisionResponse
from fraud_v2.domain.enums import DecisionAction, RiskTier
from fraud_v2.models.thresholds import CostAssumptions
from fraud_v2.policy.thresholds import ThresholdPolicy
from fraud_v2.simulation.workbench import SimulationRequest, SimulationResponse


@dataclass(frozen=True)
class CockpitScenario:
    key: str
    title: str
    blog_category: str
    typology: str
    user_id: str
    amount: float
    as_of: str
    narrative: str
    expected_label: str
    expected_operator_action: str
    simulation: SimulationRequest
    model_probability: float
    graph_evidence: tuple[str, ...]
    timeline: tuple[str, ...]
    missing_data: tuple[str, ...]
    production_blockers: tuple[str, ...]

    def as_of_datetime(self) -> datetime:
        parsed = datetime.fromisoformat(self.as_of.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed


@dataclass(frozen=True)
class DecisionModeComparison:
    name: str
    label: str
    score: int
    tier: RiskTier
    action: DecisionAction
    expected_profit: float
    recommended: bool
    note: str


@dataclass(frozen=True)
class SignalContribution:
    code: str
    points: int
    source: str
    safe_reason: str


def cockpit_scenarios() -> tuple[CockpitScenario, ...]:
    return (
        CockpitScenario(
            key="clean",
            title="Clean applicant",
            blog_category="Gateway / baseline applicant",
            typology="LEGITIMATE_CONTROL",
            user_id="user_00049",
            amount=100,
            as_of="2026-05-01T14:00:00Z",
            narrative=(
                "Normal applicant with no obvious device, behavior, graph, payment, "
                "or chargeback pressure."
            ),
            expected_label="legitimate",
            expected_operator_action="GREEN approve in the local simulator.",
            simulation=SimulationRequest(amount=100),
            model_probability=0.06,
            graph_evidence=(
                "No shared fraud-ring device in the synthetic graph.",
                "No one-hop confirmed-fraud neighbor.",
            ),
            timeline=(
                "Application submitted.",
                "Payment attempt uses normal amount and normal device.",
                "No chargeback or fraud label is available in the local event history.",
            ),
            missing_data=(
                "Real KYC document result",
                "Real bank-account ownership",
                "Real repayment outcome",
            ),
            production_blockers=(
                "No real PII or bureau data",
                "No production KYC/KYB vendor credentials",
                "No real money movement approval",
            ),
        ),
        CockpitScenario(
            key="virtual_camera",
            title="Virtual camera mule",
            blog_category="Camera / liveness / behavioral entropy",
            typology="DEEPFAKE_LIVENESS_OR_MULE",
            user_id="user_00000",
            amount=500,
            as_of="2026-05-01T12:30:00Z",
            narrative=(
                "Camera metadata and behavior look automation-shaped, but no real "
                "liveness vendor is called."
            ),
            expected_label="needs_review",
            expected_operator_action="YELLOW review with simulated step-up friction.",
            simulation=SimulationRequest(
                amount=500,
                virtual_camera=True,
                low_behavior_entropy=True,
            ),
            model_probability=0.64,
            graph_evidence=(
                "Synthetic device metadata contains a virtual-camera-shaped anomaly.",
                "Behavior entropy is low enough to require review but not enough to prove fraud.",
            ),
            timeline=(
                "Device observed before application.",
                "Camera metadata is missing or virtual-driver shaped.",
                "Behavioral signal shows low session variation.",
            ),
            missing_data=(
                "Real selfie/liveness session",
                "Real device attestation",
                "Real historical mule labels",
            ),
            production_blockers=(
                "No liveness vendor contract",
                "No biometric data governance",
                "No real customer step-up rail",
            ),
        ),
        CockpitScenario(
            key="first_party",
            title="First-party default",
            blog_category="Instant Cash / first-party fraud",
            typology="FIRST_PARTY_FRAUD",
            user_id="user_00003",
            amount=1000,
            as_of="2026-05-08T12:27:00Z",
            narrative=(
                "Instant-cash borrower has repayment/default pressure and later "
                "chargeback-style evidence."
            ),
            expected_label="fraud",
            expected_operator_action=(
                "RED block or hold in simulation; human review before any real action."
            ),
            simulation=SimulationRequest(
                amount=1000,
                prior_chargeback=True,
                payment_velocity=True,
            ),
            model_probability=0.83,
            graph_evidence=(
                "Payment timeline contains chargeback/default-shaped evidence.",
                "Benford/income features are available as local fraud-economics signals.",
            ),
            timeline=(
                "Application requested instant cash.",
                "Payment attempt settled locally.",
                "Chargeback/default label arrives later and is treated as delayed ground truth.",
            ),
            missing_data=(
                "Real repayment ledger",
                "Real affordability data",
                "Real chargeback reason codes",
            ),
            production_blockers=(
                "No lending/payment rail integration",
                "No adverse-action legal review",
                "No real collections or recovery workflow",
            ),
        ),
        CockpitScenario(
            key="graph_ring",
            title="Graph ring applicant",
            blog_category="Graph / GNN substitute / consortium",
            typology="MONEY_MULE_RING",
            user_id="user_00006",
            amount=1000,
            as_of="2026-05-08T12:27:00Z",
            narrative=(
                "Applicant sits near a confirmed synthetic fraud cluster through shared "
                "device and network evidence."
            ),
            expected_label="fraud",
            expected_operator_action="RED or high-YELLOW review depending policy threshold.",
            simulation=SimulationRequest(
                amount=1000,
                high_application_velocity=True,
                one_hop_from_fraud=True,
            ),
            model_probability=0.78,
            graph_evidence=(
                "Shared synthetic device links the applicant to confirmed fraud labels.",
                "Network evidence supplies a graph feature without needing a production GNN.",
            ),
            timeline=(
                "Shared device appears across multiple users.",
                "Application enters instant-cash flow.",
                "Neighboring users receive fraud labels later.",
            ),
            missing_data=(
                "Real consortium fraud intel",
                "Real device graph at scale",
                "Real labels for inductive GNN training",
            ),
            production_blockers=(
                "No enterprise consortium access",
                "No production graph database sizing proof",
                "No legal basis for cross-institution graph joins",
            ),
        ),
        CockpitScenario(
            key="app_bec",
            title="APP/BEC victim",
            blog_category="Instant Cash / APP-BEC intervention",
            typology="APP_BEC_INTERVENTION",
            user_id="user_00005",
            amount=750,
            as_of="2026-05-05T13:00:00Z",
            narrative=(
                "Transfer pattern deserves a Break-the-Spell prompt instead of a silent hard block."
            ),
            expected_label="needs_review",
            expected_operator_action="YELLOW with simulated Break-the-Spell prompt only.",
            simulation=SimulationRequest(
                amount=750,
                app_bec_pattern=True,
                payment_velocity=True,
            ),
            model_probability=0.58,
            graph_evidence=(
                "Payment instruction pattern is unusual for the local history.",
                "The recommended action is customer friction, not a fraud accusation.",
            ),
            timeline=(
                "User starts a risky transfer.",
                "Beneficiary/payment behavior looks unusual.",
                "System drafts a local intervention preview.",
            ),
            missing_data=(
                "Real beneficiary risk data",
                "Real scam-report consortium data",
                "Real customer communication consent",
            ),
            production_blockers=(
                "No real customer messaging rail",
                "No legal approval for intervention language",
                "No real beneficiary intelligence vendor",
            ),
        ),
        CockpitScenario(
            key="outage",
            title="Model/graph outage",
            blog_category="Reliability / degraded mode",
            typology="DEPENDENCY_DEGRADED",
            user_id="user_00014",
            amount=250,
            as_of="2026-05-08T12:27:00Z",
            narrative=(
                "A model or graph dependency is degraded, so policy routes to review "
                "instead of pretending certainty."
            ),
            expected_label="needs_review",
            expected_operator_action="YELLOW manual review in degraded mode.",
            simulation=SimulationRequest(
                amount=250,
                model_or_graph_outage=True,
            ),
            model_probability=0.31,
            graph_evidence=(
                "No high-risk graph evidence is trusted while the dependency is degraded.",
                "Policy minimum score forces review to avoid false confidence.",
            ),
            timeline=(
                "Applicant enters normal flow.",
                "Model or graph dependency health check degrades.",
                "Decision engine falls back to review policy.",
            ),
            missing_data=(
                "Live dependency SLO history",
                "Production failover runbook evidence",
                "Real analyst capacity during outage",
            ),
            production_blockers=(
                "No production SLO owner",
                "No real pager/incident process",
                "No cloud deployment target",
            ),
        ),
    )


def cockpit_scenario(key: str) -> CockpitScenario:
    for scenario in cockpit_scenarios():
        if scenario.key == key:
            return scenario
    return cockpit_scenarios()[0]


def compare_decision_modes(
    scenario: CockpitScenario,
    decision: DecisionResponse,
    policy: ThresholdPolicy,
) -> list[DecisionModeComparison]:
    model_score = max(0, min(100, round(scenario.model_probability * 100)))
    hybrid_score = max(0, min(100, round(0.58 * decision.risk_score + 0.42 * model_score)))
    return [
        _comparison(
            name="rules_only",
            label="Rules only",
            score=decision.risk_score,
            scenario=scenario,
            policy=policy,
            recommended=False,
            note=(
                "Deterministic policy, graph features, and safe reasons. Strongest "
                "for auditability."
            ),
        ),
        _comparison(
            name="model_only",
            label="Model only",
            score=model_score,
            scenario=scenario,
            policy=policy,
            recommended=False,
            note="Lightweight tabular model view. Useful ranking signal, weak as final authority.",
        ),
        _comparison(
            name="hybrid",
            label="Hybrid",
            score=hybrid_score,
            scenario=scenario,
            policy=policy,
            recommended=True,
            note=(
                "Recommended local path: rules for guardrails, model for ranking, "
                "human review for uncertain cases."
            ),
        ),
    ]


def signal_contributions(
    decision: DecisionResponse,
    simulation: SimulationResponse,
) -> list[SignalContribution]:
    signals = [*decision.signals, *simulation.signals]
    if not signals:
        return [
            SignalContribution(
                code="NO_MAJOR_SIGNAL",
                points=0,
                source="policy",
                safe_reason="No major risk signals found in this local scenario.",
            )
        ]
    merged: dict[str, SignalContribution] = {}
    for signal in signals:
        existing = merged.get(signal.code)
        if existing is None:
            merged[signal.code] = SignalContribution(
                code=signal.code,
                points=signal.severity,
                source=signal.source,
                safe_reason=signal.safe_reason,
            )
            continue
        merged[signal.code] = SignalContribution(
            code=existing.code,
            points=max(existing.points, signal.severity),
            source=existing.source,
            safe_reason=existing.safe_reason,
        )
    return sorted(merged.values(), key=lambda item: item.points, reverse=True)


def _comparison(
    *,
    name: str,
    label: str,
    score: int,
    scenario: CockpitScenario,
    policy: ThresholdPolicy,
    recommended: bool,
    note: str,
) -> DecisionModeComparison:
    tier, action = policy.tier_action(score, scenario.simulation.model_or_graph_outage)
    return DecisionModeComparison(
        name=name,
        label=label,
        score=score,
        tier=tier,
        action=action,
        expected_profit=_expected_profit(
            expected_label=scenario.expected_label,
            action=action,
            amount=scenario.amount,
        ),
        recommended=recommended,
        note=note,
    )


def _expected_profit(
    *,
    expected_label: str,
    action: DecisionAction,
    amount: float,
    assumptions: CostAssumptions = CostAssumptions(),
) -> float:
    fraud_loss = max(amount, assumptions.fraud_loss)
    if expected_label == "fraud" and action in {
        DecisionAction.BLOCK,
        DecisionAction.HOLD_FUNDS,
        DecisionAction.MANUAL_REVIEW,
        DecisionAction.BREAK_THE_SPELL,
    }:
        return fraud_loss - assumptions.manual_review_cost
    if expected_label == "fraud" and action == DecisionAction.APPROVE:
        return -fraud_loss * (1.0 - assumptions.recovery_rate_on_missed_fraud)
    if expected_label == "legitimate" and action in {
        DecisionAction.BLOCK,
        DecisionAction.HOLD_FUNDS,
        DecisionAction.MANUAL_REVIEW,
        DecisionAction.BREAK_THE_SPELL,
    }:
        return -assumptions.false_positive_cost - assumptions.manual_review_cost
    if expected_label == "needs_review" and action in {
        DecisionAction.MANUAL_REVIEW,
        DecisionAction.BREAK_THE_SPELL,
    }:
        return -assumptions.manual_review_cost
    if expected_label == "needs_review" and action == DecisionAction.APPROVE:
        return -assumptions.false_positive_cost
    return 0.0
