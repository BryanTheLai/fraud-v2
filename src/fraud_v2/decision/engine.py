from __future__ import annotations

from fraud_v2.domain.decisions import DecisionRequest, DecisionResponse, FeatureVector, RiskSignal
from fraud_v2.domain.enums import FeatureFreshnessStatus
from fraud_v2.features.builder import FeatureBuilder
from fraud_v2.graph.service import GraphService
from fraud_v2.policy.thresholds import ThresholdPolicy, default_threshold_policy
from fraud_v2.rules.engine import RuleEngine
from fraud_v2.storage.ports import FraudStore


class DecisionEngine:
    def __init__(self, store: FraudStore, policy: ThresholdPolicy | None = None) -> None:
        self.store = store
        self.policy = policy or default_threshold_policy()
        self.rules = RuleEngine()

    def score(self, request: DecisionRequest) -> DecisionResponse:
        events = self.store.list_events()
        features = FeatureBuilder(events).build(request.target_entity, request.as_of)
        graph = GraphService(events)
        graph_distance = graph.distance_to_confirmed_fraud(request.target_entity)
        signals = self.rules.evaluate(features, graph_distance)
        if request.amount >= self.policy.high_request_amount_threshold:
            signals.append(
                RiskSignal(
                    code="HIGH_REQUEST_AMOUNT",
                    severity=self.policy.high_request_amount_severity,
                    safe_reason=self.policy.high_request_amount_reason,
                    source="policy",
                )
            )
        score = self._score(signals, features)
        degraded = self._is_degraded(features)
        tier, action = self.policy.tier_action(score, degraded)
        response = DecisionResponse(
            target_entity=request.target_entity,
            risk_score=score,
            risk_tier=tier,
            action=action,
            signals=signals,
            feature_vector=features,
            policy_version=self.policy.version,
            model_version="rules-graph-local-v1",
            degraded=degraded,
            safe_reasons=[signal.safe_reason for signal in signals]
            or ["No major risk signals found."],
        )
        self.store.save_decision(response)
        return response

    def _score(self, signals: list[RiskSignal], features: FeatureVector) -> int:
        if self._is_degraded(features):
            raw_score = min(100, sum(signal.severity for signal in signals))
            return max(self.policy.degraded_min_score, raw_score)
        return min(100, sum(signal.severity for signal in signals))

    def _is_degraded(self, features: FeatureVector) -> bool:
        return any(
            status == FeatureFreshnessStatus.DEGRADED for status in features.freshness.values()
        )
