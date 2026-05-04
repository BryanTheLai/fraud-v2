import json

import numpy as np

from fraud_v2.compliance.drafts import build_compliance_draft, write_compliance_draft
from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.models.thresholds import cost_weighted_threshold_report
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_compliance_draft_is_human_review_only(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=1).generate(users=30)
    store.add_events(dataset.events)
    decision = DecisionEngine(store).score(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00000"),
            as_of=max(event.occurred_at for event in dataset.events),
            amount=1000,
        )
    )

    draft = build_compliance_draft(decision)

    assert draft.human_review_required is True
    assert "not a regulatory filing" in draft.legal_disclaimer
    assert draft.safe_reasons


def test_write_compliance_draft_outputs_json(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=1).generate(users=30)
    store.add_events(dataset.events)
    decision = DecisionEngine(store).score(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00000"),
            as_of=max(event.occurred_at for event in dataset.events),
            amount=1000,
        )
    )
    output = tmp_path / "draft.json"

    draft = write_compliance_draft(decision, output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["draft_id"] == str(draft.draft_id)
    assert payload["decision_id"] == str(decision.decision_id)


def test_cost_weighted_threshold_report_prefers_profitable_threshold() -> None:
    labels = np.array([1, 1, 0, 0, 0, 0])
    probabilities = np.array([0.95, 0.8, 0.7, 0.2, 0.1, 0.05])

    report = cost_weighted_threshold_report(labels, probabilities)

    assert report["best_profit_threshold"]["profit"] > 0
    assert report["best_recall_under_1pct_fpr"]["fpr"] <= 0.01
    assert len(report["candidates"]) == 19
