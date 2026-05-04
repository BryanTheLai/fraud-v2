from __future__ import annotations

from fraud_v2.domain.decisions import DecisionRequest, DecisionResponse, FeatureVector, RiskSignal
from fraud_v2.domain.enums import DecisionAction, FeatureFreshnessStatus, RiskTier
from fraud_v2.features.builder import FeatureBuilder
from fraud_v2.graph.service import GraphService
from fraud_v2.rules.engine import RuleEngine
from fraud_v2.storage.sqlite_store import SQLiteStore


class DecisionEngine:
    policy_version = "local-policy-20260505-001"

    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self.rules = RuleEngine()

    def score(self, request: DecisionRequest) -> DecisionResponse:
        events = self.store.list_events()
        features = FeatureBuilder(events).build(request.target_entity, request.as_of)
        graph = GraphService(events)
        graph_distance = graph.distance_to_confirmed_fraud(request.target_entity)
        signals = self.rules.evaluate(features, graph_distance)
        if request.amount >= 750:
            signals.append(
                RiskSignal(
                    code="HIGH_REQUEST_AMOUNT",
                    severity=15,
                    safe_reason="The requested amount is high for the local policy.",
                    source="policy",
                )
            )
        score = self._score(signals, features)
        tier, action = self._tier_action(score, features)
        response = DecisionResponse(
            target_entity=request.target_entity,
            risk_score=score,
            risk_tier=tier,
            action=action,
            signals=signals,
            feature_vector=features,
            policy_version=self.policy_version,
            model_version="rules-graph-local-v1",
            degraded=self._is_degraded(features),
            safe_reasons=[signal.safe_reason for signal in signals]
            or ["No major risk signals found."],
        )
        self.store.save_decision(response)
        return response

    def _score(self, signals: list[RiskSignal], features: FeatureVector) -> int:
        if self._is_degraded(features):
            return max(21, min(100, sum(signal.severity for signal in signals)))
        return min(100, sum(signal.severity for signal in signals))

    def _tier_action(self, score: int, features: FeatureVector) -> tuple[RiskTier, DecisionAction]:
        if self._is_degraded(features):
            return RiskTier.YELLOW, DecisionAction.MANUAL_REVIEW
        if score <= 20:
            return RiskTier.GREEN, DecisionAction.APPROVE
        if score < 80:
            return RiskTier.YELLOW, DecisionAction.MANUAL_REVIEW
        return RiskTier.RED, DecisionAction.BLOCK

    def _is_degraded(self, features: FeatureVector) -> bool:
        return any(
            status == FeatureFreshnessStatus.DEGRADED for status in features.freshness.values()
        )
