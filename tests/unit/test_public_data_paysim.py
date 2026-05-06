from __future__ import annotations

import json

import pytest

from fraud_v2.domain.events import EventEnvelope
from fraud_v2.public_data.paysim import convert_paysim_csv


def test_convert_paysim_csv_writes_canonical_events(tmp_path) -> None:  # type: ignore[no-untyped-def]
    input_path = tmp_path / "paysim.csv"
    output_path = tmp_path / "events.jsonl"
    input_path.write_text(
        "\n".join(
            [
                "step,type,amount,nameOrig,oldbalanceOrg,newbalanceOrig,nameDest,oldbalanceDest,newbalanceDest,isFraud,isFlaggedFraud",
                "1,TRANSFER,181.00,C1305486145,181.00,0.00,C553264065,0.00,0.00,1,0",
                "1,PAYMENT,50.25,C840083671,1000.00,949.75,M1979787155,0.00,0.00,0,0",
            ]
        ),
        encoding="utf-8",
    )

    report = convert_paysim_csv(input_path=input_path, output_path=output_path)
    events = [
        EventEnvelope.model_validate_json(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
    ]

    assert report.rows == 2
    assert report.fraud_rows == 1
    assert report.legitimate_rows == 1
    assert report.events == 5
    assert [event.event_type.value for event in events] == [
        "PAYMENT_ATTEMPTED",
        "PAYMENT_ATTEMPTED",
        "PAYMENT_SETTLED",
        "CHARGEBACK_RECEIVED",
        "LABEL_CREATED",
    ]
    assert "C1305486145" not in output_path.read_text(encoding="utf-8")
    assert json.loads(events[0].model_dump_json())["payload"]["amount"] == "181.00"


def test_convert_paysim_csv_respects_limit(tmp_path) -> None:  # type: ignore[no-untyped-def]
    input_path = tmp_path / "paysim.csv"
    input_path.write_text(
        "\n".join(
            [
                "step,type,amount,nameOrig,nameDest,isFraud",
                "1,TRANSFER,100,C1,C2,1",
                "2,TRANSFER,200,C3,C4,1",
            ]
        ),
        encoding="utf-8",
    )

    report = convert_paysim_csv(
        input_path=input_path,
        output_path=tmp_path / "events.jsonl",
        limit_rows=1,
    )

    assert report.rows == 1
    assert report.fraud_rows == 1
    assert report.events == 3


def test_convert_paysim_csv_requires_expected_columns(tmp_path) -> None:  # type: ignore[no-untyped-def]
    input_path = tmp_path / "bad.csv"
    input_path.write_text("step,amount\n1,10\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        convert_paysim_csv(input_path=input_path, output_path=tmp_path / "events.jsonl")
