from __future__ import annotations

from fraud_v2.domain.decisions import FeatureVector, RiskSignal


class RuleEngine:
    def evaluate(self, features: FeatureVector, graph_distance: int | None) -> list[RiskSignal]:
        values = features.values
        signals: list[RiskSignal] = []
        self._add_if(
            signals,
            self._number(values["failed_login_count_3m"]) >= 5,
            "FAILED_LOGIN_VELOCITY",
            30,
            "Many failed login attempts happened recently.",
        )
        self._add_if(
            signals,
            self._number(values["applications_per_device_1h"]) >= 3,
            "APPLICATIONS_PER_DEVICE_VELOCITY",
            35,
            "Several applications used the same device in a short window.",
        )
        self._add_if(
            signals,
            self._number(values["distinct_users_on_device_1h"]) >= 3,
            "DEVICE_SHARED_BY_USERS",
            40,
            "Multiple users shared the same device recently.",
        )
        self._add_if(
            signals,
            self._number(values["payment_attempt_count_10m"]) >= 3,
            "PAYMENT_ATTEMPT_VELOCITY",
            25,
            "Several payment attempts happened in a short window.",
        )
        self._add_if(
            signals,
            self._number(values["payment_amount_24h"]) >= 1000,
            "HIGH_24H_PAYMENT_AMOUNT",
            15,
            "Recent payment amount is high for the local policy.",
        )
        self._add_if(
            signals,
            self._truthy(values["virtual_camera_flag"]),
            "CAMERA_METADATA_ANOMALY",
            20,
            "Camera metadata is missing or indicates a virtual camera.",
        )
        self._add_if(
            signals,
            self._truthy(values["low_behavior_entropy"]),
            "LOW_BEHAVIOR_ENTROPY",
            25,
            "Session behavior has very low human-like variation.",
        )
        self._add_if(
            signals,
            self._number(values["chargebacks_total"]) >= 1,
            "PRIOR_CHARGEBACK",
            45,
            "A prior chargeback or dispute exists for this user.",
        )
        self._add_if(
            signals,
            self._truthy(values["confirmed_fraud_label"]),
            "CONFIRMED_FRAUD_LABEL",
            100,
            "This user already has a confirmed fraud label.",
        )
        if graph_distance == 1:
            signals.append(
                RiskSignal(
                    code="ONE_HOP_FROM_CONFIRMED_FRAUD",
                    severity=45,
                    safe_reason=(
                        "This user shares a high-confidence connection with confirmed fraud."
                    ),
                    source="graph",
                )
            )
        if graph_distance is not None and 1 < graph_distance <= 3:
            signals.append(
                RiskSignal(
                    code="NEAR_CONFIRMED_FRAUD_CLUSTER",
                    severity=30,
                    safe_reason="This user is near a confirmed fraud cluster in the entity graph.",
                    source="graph",
                )
            )
        return signals

    def _add_if(
        self,
        signals: list[RiskSignal],
        condition: bool,
        code: str,
        severity: int,
        safe_reason: str,
    ) -> None:
        if condition:
            signals.append(
                RiskSignal(code=code, severity=severity, safe_reason=safe_reason, source="rules")
            )

    def _number(self, value: float | int | str | bool) -> float:
        if isinstance(value, bool):
            return float(int(value))
        if isinstance(value, int | float):
            return float(value)
        return 0.0

    def _truthy(self, value: float | int | str | bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int | float):
            return value != 0
        return value.lower() in {"true", "yes", "1"}
