from fraud_v2.cockpit import cockpit_scenario, compare_decision_modes, signal_contributions
from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.policy.thresholds import default_threshold_policy
from fraud_v2.simulation.workbench import run_simulation
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_cockpit_scenario_comparison_explains_rules_model_and_hybrid(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = SQLiteStore(tmp_path / "fraud.sqlite")
    dataset = SyntheticFraudGenerator(seed=1).generate(users=80)
    store.add_events(dataset.events)
    scenario = cockpit_scenario("graph_ring")
    as_of = scenario.as_of_datetime()
    decision = DecisionEngine(store).preview(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id=scenario.user_id),
            as_of=as_of,
            amount=scenario.amount,
        )
    )
    simulation = run_simulation(scenario.simulation, policy=default_threshold_policy())

    modes = compare_decision_modes(scenario, decision, default_threshold_policy())
    contributions = signal_contributions(decision, simulation)

    assert {mode.name for mode in modes} == {"rules_only", "model_only", "hybrid"}
    assert any(mode.recommended for mode in modes)
    assert modes[-1].name == "hybrid"
    assert contributions
    assert sum(item.points for item in contributions) >= decision.risk_score


def test_cockpit_scenario_carries_blockers_and_missing_data() -> None:
    scenario = cockpit_scenario("app_bec")

    assert scenario.blog_category == "Instant Cash / APP-BEC intervention"
    assert "No real customer messaging rail" in scenario.production_blockers
    assert "Real beneficiary risk data" in scenario.missing_data
