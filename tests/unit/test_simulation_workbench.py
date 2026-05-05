from fraud_v2.domain.enums import DecisionAction, RiskTier
from fraud_v2.simulation.workbench import SimulationRequest, run_simulation


def test_clean_simulation_approves_with_no_selected_signals() -> None:
    result = run_simulation(SimulationRequest(amount=100))

    assert result.score == 0
    assert result.tier == RiskTier.GREEN
    assert result.action == DecisionAction.APPROVE
    assert result.safe_reasons == ["No local workbench risk signals selected."]
    assert result.local_only is True
    assert result.no_real_action is True


def test_combined_high_risk_simulation_blocks_locally() -> None:
    result = run_simulation(
        SimulationRequest(
            amount=1000,
            virtual_camera=True,
            prior_chargeback=True,
            one_hop_from_fraud=True,
        )
    )

    assert result.score == 100
    assert result.tier == RiskTier.RED
    assert result.action == DecisionAction.BLOCK
    assert "PRIOR_CHARGEBACK" in {signal.code for signal in result.signals}
    assert "ONE_HOP_FROM_CONFIRMED_FRAUD" in {signal.code for signal in result.signals}


def test_app_bec_yellow_band_routes_to_break_the_spell_preview() -> None:
    result = run_simulation(SimulationRequest(amount=100, app_bec_pattern=True))

    assert result.score == 25
    assert result.tier == RiskTier.YELLOW
    assert result.action == DecisionAction.BREAK_THE_SPELL


def test_dependency_outage_forces_degraded_manual_review() -> None:
    result = run_simulation(SimulationRequest(amount=100, model_or_graph_outage=True))

    assert result.score == 21
    assert result.tier == RiskTier.YELLOW
    assert result.action == DecisionAction.MANUAL_REVIEW
    assert result.degraded is True
    assert "DEPENDENCY_DEGRADED" in {signal.code for signal in result.signals}
