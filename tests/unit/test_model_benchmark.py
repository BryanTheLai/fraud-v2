from fraud_v2.models.benchmark import benchmark_model_families
from fraud_v2.synthetic.generator import SyntheticFraudGenerator


def test_model_benchmark_compares_lightweight_local_models(tmp_path) -> None:  # type: ignore[no-untyped-def]
    events_path = tmp_path / "events.jsonl"
    output_path = tmp_path / "benchmark.json"
    SyntheticFraudGenerator(seed=7).generate(users=80).write_jsonl(events_path)

    report = benchmark_model_families(events_path=events_path, output_path=output_path)

    assert output_path.exists()
    assert report["rows"] == 80
    assert {row["model_family"] for row in report["models"]} >= {
        "sklearn_logistic_regression",
        "sklearn_random_forest",
    }
    assert report["recommended_model_family"] in {
        "sklearn_logistic_regression",
        "sklearn_random_forest",
    }
    assert all(0 <= row["average_precision"] <= 1 for row in report["models"])
