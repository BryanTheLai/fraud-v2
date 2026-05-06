from __future__ import annotations

from fraud_v2.evaluation.capacity import (
    resolve_capacity_profile,
    run_capacity_profile,
)


def test_capacity_profile_writes_json_html_and_passes_targets(tmp_path) -> None:  # type: ignore[no-untyped-def]
    profile = resolve_capacity_profile(
        "smoke",
        users=12,
        score_users=3,
        min_load_events_per_second=0.1,
        min_score_decisions_per_second=0.1,
    )

    report = run_capacity_profile(profile=profile, output_dir=tmp_path, seed=41)

    assert report["status"] == "pass"
    assert report["production_capacity_claim"] is False
    assert report["benchmark"]["users"] == 12
    assert (tmp_path / "smoke-capacity-report.json").exists()
    assert (tmp_path / "smoke-capacity-report.html").exists()


def test_capacity_profile_warns_when_targets_are_missed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    profile = resolve_capacity_profile(
        "smoke",
        users=12,
        score_users=3,
        min_load_events_per_second=1_000_000.0,
        min_score_decisions_per_second=1_000_000.0,
    )

    report = run_capacity_profile(profile=profile, output_dir=tmp_path, seed=41)

    assert report["status"] == "warn"
    assert {check["passed"] for check in report["checks"]} == {False}


def test_capacity_profile_overrides_named_profile() -> None:
    profile = resolve_capacity_profile("laptop", users=123, score_users=7)

    assert profile.name == "laptop"
    assert profile.users == 123
    assert profile.score_users == 7
