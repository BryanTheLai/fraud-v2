from __future__ import annotations

from dataclasses import dataclass


class DatasetUnavailableError(RuntimeError):
    """Raised when a public dataset requires manual download or terms."""


@dataclass(frozen=True)
class PublicDataset:
    name: str
    purpose: str
    access_note: str


PUBLIC_DATASETS = {
    "ieee-cis": PublicDataset(
        name="ieee-cis",
        purpose="Tabular ecommerce fraud benchmark.",
        access_note="Requires Kaggle access and accepted competition terms.",
    ),
    "paysim": PublicDataset(
        name="paysim",
        purpose="Synthetic mobile-money transaction fraud benchmark.",
        access_note="Download manually from an approved public mirror before loading.",
    ),
    "banksim": PublicDataset(
        name="banksim",
        purpose="Synthetic bank payment fraud benchmark.",
        access_note="Download manually from an approved public mirror before loading.",
    ),
    "elliptic": PublicDataset(
        name="elliptic",
        purpose="Crypto transaction graph benchmark.",
        access_note="Requires manual dataset download and terms review.",
    ),
}


def describe_public_dataset(name: str) -> PublicDataset:
    try:
        return PUBLIC_DATASETS[name]
    except KeyError as exc:
        raise DatasetUnavailableError(f"unknown public dataset: {name}") from exc
