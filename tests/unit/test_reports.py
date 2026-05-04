from fraud_v2.evaluation.reports import write_monitoring_report
from fraud_v2.replay.runner import run_replay
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_replay_report(tmp_path) -> None:  # type: ignore[no-untyped-def]
    events_path = tmp_path / "events.jsonl"
    SyntheticFraudGenerator(seed=7).generate(users=30).write_jsonl(events_path)

    report = run_replay(events_path, tmp_path / "replay.sqlite", tmp_path / "replay.json")

    assert report["events"] > 0
    assert report["decisions"] == 30
    assert report["red"] > 0


def test_monitoring_report(tmp_path) -> None:  # type: ignore[no-untyped-def]
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
