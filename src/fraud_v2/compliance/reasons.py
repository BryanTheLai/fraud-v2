from fraud_v2.domain.decisions import DecisionResponse


def adverse_action_style_reasons(decision: DecisionResponse) -> list[str]:
    reasons = [reason for reason in decision.safe_reasons if "risk score" not in reason.lower()]
    return reasons or [
        "Application requires manual review due to incomplete or stale risk evidence."
    ]
