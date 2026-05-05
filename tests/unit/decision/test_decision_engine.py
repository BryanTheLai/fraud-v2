from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import DecisionAction, EntityType, RiskTier
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_decision_engine_scores_high_risk_user(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=1).generate(users=50)
    store.add_events(dataset.events)
    as_of = max(event.occurred_at for event in dataset.events)

    decision = DecisionEngine(store).score(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00000"),
            as_of=as_of,
            amount=1000,
        )
    )

    assert decision.risk_tier == RiskTier.RED
    assert decision.action == DecisionAction.BLOCK
    assert decision.safe_reasons


def test_decision_engine_scores_low_risk_user(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=1).generate(users=50)
    store.add_events(dataset.events)
    early_as_of = dataset.events[20].occurred_at

    decision = DecisionEngine(store).score(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00049"),
            as_of=early_as_of,
            amount=50,
        )
    )

    assert decision.risk_score <= 20
    assert decision.action == DecisionAction.APPROVE


def test_decision_engine_preview_does_not_persist_decision(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=1).generate(users=50)
    store.add_events(dataset.events)
    as_of = max(event.occurred_at for event in dataset.events)

    decision = DecisionEngine(store).preview(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id="user_00000"),
            as_of=as_of,
            amount=1000,
        )
    )

    assert decision.risk_tier == RiskTier.RED
    assert store.list_decisions() == []
