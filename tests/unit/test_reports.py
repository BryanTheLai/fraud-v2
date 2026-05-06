from pathlib import Path

from fraud_v2.evaluation.mlops import cohen_kappa, population_stability_index, write_mlops_report
from fraud_v2.evaluation.reports import write_monitoring_report
from fraud_v2.replay.runner import run_replay
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_replay_report(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    SyntheticFraudGenerator(seed=7).generate(users=30).write_jsonl(events_path)

    report = run_replay(events_path, tmp_path / "replay.sqlite", tmp_path / "replay.json")

    assert isinstance(report["events"], int)
    assert report["events"] > 0
    assert report["decisions"] == 30
    assert isinstance(report["red"], int)
    assert report["red"] > 0


def test_replay_report_handles_empty_event_file(tmp_path: Path) -> None:
    events_path = tmp_path / "empty.jsonl"
    events_path.write_text("", encoding="utf-8")

    report = run_replay(events_path, tmp_path / "empty.sqlite", tmp_path / "replay.json")

    assert report == {
        "events": 0,
        "users": 0,
        "decisions": 0,
        "green": 0,
        "yellow": 0,
        "red": 0,
    }


def test_monitoring_report(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    SyntheticFraudGenerator(seed=7).generate(users=30).write_jsonl(events_path)

    report = write_monitoring_report(
        events_path,
        tmp_path / "monitor.sqlite",
        tmp_path / "monitoring.json",
    )

    assert report["rows"] == 30
    assert "psi_first_half_vs_second_half" in report
    assert "fairness_proxy" in report


def test_monitoring_report_handles_empty_event_file(tmp_path: Path) -> None:
    events_path = tmp_path / "empty.jsonl"
    events_path.write_text("", encoding="utf-8")

    report = write_monitoring_report(
        events_path,
        tmp_path / "empty-monitor.sqlite",
        tmp_path / "monitoring.json",
    )

    assert report["rows"] == 0
    assert report["score_summary"] == {"min": 0.0, "p50": 0.0, "max": 0.0, "mean": 0.0}
    assert report["fairness_proxy"] == {}


def test_mlops_report_includes_drift_and_kappa(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    SyntheticFraudGenerator(seed=7).generate(users=30).write_jsonl(events_path)

    report = write_mlops_report(
        events_path=events_path,
        db_path=tmp_path / "mlops.sqlite",
        output_path=tmp_path / "mlops.json",
        simulate_score_shift_points=12,
    )

    assert report["rows"] == 30
    assert "score_drift" in report
    assert "analyst_consistency" in report
    assert report["simulation"] == {
        "current_score_shift_points": 12,
        "note": "Current population shift is synthetic and local-only.",
    }


def test_mlops_math_helpers() -> None:
    assert population_stability_index([1, 2, 90], [1, 2, 90]) == 0.0
    assert cohen_kappa(["fraud", "legit", "review"], ["fraud", "legit", "review"]) == 1.0
