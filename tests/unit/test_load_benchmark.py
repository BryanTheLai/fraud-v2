from __future__ import annotations

import pytest

from fraud_v2.evaluation.load_benchmark import run_load_benchmark


def test_load_benchmark_writes_local_performance_report(tmp_path) -> None:  # type: ignore[no-untyped-def]
    report = run_load_benchmark(
        users=12,
        score_users=3,
        db_path=tmp_path / "benchmark.sqlite",
        output_path=tmp_path / "benchmark-report.json",
        seed=31,
    )

    assert report["users"] == 12
    assert report["events"] == report["inserted_events"]
    assert report["score_users"] == 3
    assert report["load_events_per_second"] > 0
    assert report["score_decisions_per_second"] > 0
    assert report["risk_tiers"]
    assert (tmp_path / "benchmark-report.json").exists()


def test_load_benchmark_refuses_existing_database_without_overwrite(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "benchmark.sqlite"
    run_load_benchmark(
        users=10,
        score_users=1,
        db_path=db_path,
        output_path=tmp_path / "first.json",
    )

    with pytest.raises(FileExistsError, match="benchmark database already exists"):
        run_load_benchmark(
            users=10,
            score_users=1,
            db_path=db_path,
            output_path=tmp_path / "second.json",
        )


def test_load_benchmark_overwrite_replaces_existing_database(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_path = tmp_path / "benchmark.sqlite"
    run_load_benchmark(
        users=10,
        score_users=1,
        db_path=db_path,
        output_path=tmp_path / "first.json",
    )

    report = run_load_benchmark(
        users=11,
        score_users=2,
        db_path=db_path,
        output_path=tmp_path / "second.json",
        overwrite=True,
    )

    assert report["users"] == 11
    assert report["score_users"] == 2
