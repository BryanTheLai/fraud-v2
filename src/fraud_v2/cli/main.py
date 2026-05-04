from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import jwt
import typer

from fraud_v2.compliance.drafts import write_compliance_draft
from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.domain.retention import RetentionPolicy
from fraud_v2.evaluation.reports import write_monitoring_report
from fraud_v2.infrastructure.redpanda_publisher import RedpandaEventPublisher
from fraud_v2.llm_lab.provider import NoveltyLedger, provider_from_env
from fraud_v2.models.registry import JsonModelRegistry, ModelStatus
from fraud_v2.models.shadow import write_shadow_scores
from fraud_v2.models.train import train_baseline
from fraud_v2.public_data.registry import describe_public_dataset
from fraud_v2.replay.runner import run_replay
from fraud_v2.security.auth import AuthRole
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
def auth_token(
    secret: str = typer.Option(..., help="Local HS256 signing secret. Do not commit it."),
    subject: str = "local-admin",
    roles: str = "admin,analyst,system",
    issuer: str = "fraud-v2-local",
    audience: str = "fraud-v2-api",
    expires_minutes: int = typer.Option(60, min=1, max=1440),
) -> None:
    if len(secret.encode("utf-8")) < 32:
        raise typer.BadParameter("secret must be at least 32 bytes for HS256")
    role_values = _parse_auth_roles(roles)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": subject,
            "roles": role_values,
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(minutes=expires_minutes),
        },
        secret,
        algorithm="HS256",
    )
    _print_json(
        {
            "token": token,
            "auth_mode": "jwt",
            "issuer": issuer,
            "audience": audience,
            "roles": role_values,
            "expires_at": now + timedelta(minutes=expires_minutes),
        }
    )


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
    bootstrap_servers: str = "localhost:19092",
) -> None:
    store = SQLiteStore(db_path)
    publisher = (
        DryRunEventPublisher()
        if dry_run
        else RedpandaEventPublisher(bootstrap_servers=bootstrap_servers)
    )
    report = OutboxWorker(store=store, publisher=publisher, batch_size=batch_size).run_once()
    _print_json({**report.__dict__, "outbox": store.outbox_counts()})


@app.command()
def compliance_draft(
    decision_id: UUID,
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    output_path: Path = Path("data/local/compliance-draft.json"),
) -> None:
    store = SQLiteStore(db_path)
    decision = store.get_decision(decision_id)
    draft = write_compliance_draft(decision, output_path)
    _print_json({"draft": draft.model_dump(mode="json"), "output": str(output_path)})


@app.command()
def retention_report(
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    as_of: str | None = None,
    event_days: int = typer.Option(90, min=1),
    decision_days: int = typer.Option(365, min=1),
    review_days: int = typer.Option(365, min=1),
    outbox_days: int = typer.Option(30, min=1),
    audit_days: int = typer.Option(3650, min=1),
) -> None:
    report_as_of = _parse_as_of(as_of)
    report = SQLiteStore(db_path).retention_report(
        as_of=report_as_of,
        policy=RetentionPolicy(
            event_days=event_days,
            decision_days=decision_days,
            review_days=review_days,
            outbox_days=outbox_days,
            audit_days=audit_days,
        ),
    )
    _print_json(report.model_dump(mode="json"))


@app.command()
def model_register(
    model_path: Path = Path("data/models/baseline/baseline.joblib"),
    report_path: Path = Path("data/models/baseline/baseline-report.json"),
    registry_path: Path = Path("data/models/registry.json"),
    status: ModelStatus = ModelStatus.SHADOW,
    notes: str = "",
) -> None:
    model = JsonModelRegistry(registry_path).register_from_report(
        artifact_path=model_path,
        report_path=report_path,
        status=status,
        notes=notes,
    )
    _print_json({"model": model.model_dump(mode="json"), "registry": str(registry_path)})


@app.command()
def model_list(registry_path: Path = Path("data/models/registry.json")) -> None:
    models = JsonModelRegistry(registry_path).list_models()
    _print_json({"models": [model.model_dump(mode="json") for model in models]})


@app.command()
def model_promote(
    model_version: str,
    registry_path: Path = Path("data/models/registry.json"),
) -> None:
    model = JsonModelRegistry(registry_path).promote(model_version)
    _print_json({"model": model.model_dump(mode="json"), "registry": str(registry_path)})


@app.command()
def shadow_score(
    events_path: Path = Path("data/synthetic/tiny/events.jsonl"),
    registry_path: Path = Path("data/models/registry.json"),
    output_path: Path = Path("data/models/shadow-scores.json"),
    status: ModelStatus = ModelStatus.ACTIVE,
) -> None:
    report = write_shadow_scores(
        events_path=events_path,
        registry_path=registry_path,
        output_path=output_path,
        status=status,
    )
    _print_json(report)


def _parse_as_of(raw_value: str | None) -> datetime:
    if raw_value is None:
        return datetime.now(UTC)
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _parse_auth_roles(raw_roles: str) -> list[str]:
    values: list[str] = []
    for role_name in raw_roles.replace(";", ",").split(","):
        role_name = role_name.strip().lower()
        if not role_name:
            continue
        try:
            values.append(AuthRole(role_name).value)
        except ValueError as exc:
            raise typer.BadParameter(f"unsupported role: {role_name}") from exc
    if not values:
        raise typer.BadParameter("at least one role is required")
    return sorted(set(values))
