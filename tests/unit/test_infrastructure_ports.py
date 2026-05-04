import pytest

from fraud_v2.infrastructure.optional_imports import optional_module
from fraud_v2.public_data.registry import describe_public_dataset


def test_optional_module_error_names_extra() -> None:
    with pytest.raises(RuntimeError, match="uv sync --extra infra"):
        optional_module("not_a_real_module_for_fraud_v2", "infra")


def test_public_dataset_registry_describes_known_dataset() -> None:
    dataset = describe_public_dataset("paysim")

    assert dataset.name == "paysim"
    assert "fraud" in dataset.purpose.lower()
