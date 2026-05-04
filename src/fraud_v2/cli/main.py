from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.evaluation.reports import write_monitoring_report
from fraud_v2.infrastructure.redpanda_publisher import RedpandaEventPublisher
from fraud_v2.llm_lab.provider import NoveltyLedger, provider_from_env
from fraud_v2.models.train import train_baseline
from fraud_v2.public_data.registry import describe_public_dataset
from fraud_v2.replay.runner import run_replay
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator, load_events_jsonl
from fraud_v2.workers.outbox import DryRunEventPublisher, OutboxWorker

app = typer.Typer(no_args_is_help=True)


SCENARIO_SCHEMA: dict[str, Any] = {
    "title": "scenario_spec",
    "type": "object",
    "properties": {
        "scenario_id": {"type": "string", "minLength": 6},
        "schema_title": {"type": "string"},
        "typology": {"type": "string"},
        "signals": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "expected_label": {"type": "string", "enum": ["fraud", "legitimate", "needs_review"]},
        "narrative": {"type": "string", "minLength": 20},
    },
    "required": [
        "scenario_id",
        "schema_title",
        "typology",
        "signals",
        "expected_label",
        "narrative",
    ],
    "additionalProperties": False,
}


def _print_json(payload: Any) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True, default=str))


@app.command()
def generate(
    users: int = typer.Option(120, min=10),
    output: Path = Path("data/synthetic/tiny/events.jsonl"),
) -> None:
    dataset = SyntheticFraudGenerator().generate(users=users)
    dataset.write_jsonl(output)
    _print_json({"events": len(dataset.events), "output": str(output)})


@app.command()
def load(
    input_path: Path = typer.Argument(...),
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
) -> None:
    events = load_events_jsonl(input_path)
    store = SQLiteStore(db_path)
    inserted = store.add_events(events)
    _print_json({"inserted": inserted, "db": str(db_path), "outbox": store.outbox_counts()})


@app.command()
def score(
    user_id: str,
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
) -> None:
    store = SQLiteStore(db_path)
    events = store.list_events()
    if not events:
        raise typer.BadParameter("database has no events; run generate and load first")
    request = DecisionRequest(
        target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
        as_of=max(event.occurred_at for event in events),
    )
    decision = DecisionEngine(store).score(request)
    _print_json(decision.model_dump(mode="json"))


@app.command()
def train(
    events_path: Path = Path("data/synthetic/tiny/events.jsonl"),
    output_dir: Path = Path("data/models/baseline"),
) -> None:
    report = train_baseline(events_path, output_dir)
    _print_json(report)


@app.command()
def replay(
    events_path: Path = Path("data/synthetic/tiny/events.jsonl"),
    db_path: Path = Path("data/local/replay.sqlite"),
    report_path: Path = Path("data/local/replay-report.json"),
) -> None:
    report = run_replay(events_path, db_path, report_path)
    _print_json(report)


@app.command()
def monitor(
    events_path: Path = Path("data/synthetic/tiny/events.jsonl"),
    db_path: Path = Path("data/local/monitor.sqlite"),
    output_path: Path = Path("data/local/monitoring-report.json"),
) -> None:
    report = write_monitoring_report(events_path, db_path, output_path)
    _print_json(report)


@app.command()
def llm_stub(
    prompt: str = "Generate a synthetic account takeover false positive scenario.",
    ledger_path: Path = Path("data/synthetic/manifests/generation-manifest.jsonl"),
) -> None:
    payload = provider_from_env("offline").generate_structured(prompt, SCENARIO_SCHEMA)
    ledger = NoveltyLedger(ledger_path)
    duplicate = ledger.seen(payload)
    if not duplicate:
        ledger.append(
            payload, schema_name="scenario_spec", model="offline-stub", prompt_pack_version="v1"
        )
    _print_json({"duplicate": duplicate, "payload": payload})


@app.command()
def llm_generate(
    prompt: str = "Generate one novel synthetic fraud edge case.",
    ledger_path: Path = Path("data/synthetic/manifests/generation-manifest.jsonl"),
    provider_name: str = typer.Option("offline", "--provider"),
    prompt_pack_version: str = "v1",
) -> None:
    provider = provider_from_env(provider_name)
    payload = provider.generate_structured(prompt, SCENARIO_SCHEMA)
    ledger = NoveltyLedger(ledger_path)
    duplicate = ledger.seen(payload)
    if not duplicate:
        ledger.append(
            payload,
            schema_name="scenario_spec",
            model=provider_name,
            prompt_pack_version=prompt_pack_version,
        )
    _print_json({"duplicate": duplicate, "payload": payload})


@app.command()
def public_dataset(name: str) -> None:
    dataset = describe_public_dataset(name)
    _print_json(dataset.__dict__)


@app.command()
def outbox_drain(
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    batch_size: int = typer.Option(100, min=1, max=1000),
    dry_run: bool = typer.Option(True, "--dry-run/--publish"),
    bootstrap_servers: str = "localhost:9092",
) -> None:
    store = SQLiteStore(db_path)
    publisher = (
        DryRunEventPublisher()
        if dry_run
        else RedpandaEventPublisher(bootstrap_servers=bootstrap_servers)
    )
    report = OutboxWorker(store=store, publisher=publisher, batch_size=batch_size).run_once()
    _print_json({**report.__dict__, "outbox": store.outbox_counts()})
