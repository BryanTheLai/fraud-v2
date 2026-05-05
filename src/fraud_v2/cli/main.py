from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import jwt
import typer

from fraud_v2.compliance.drafts import write_compliance_draft
from fraud_v2.compliance.evidence import (
    EVIDENCE_PASSPHRASE_ENV,
    write_encrypted_decision_evidence,
)
from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.domain.retention import RetentionPolicy
from fraud_v2.evaluation.load_benchmark import run_load_benchmark
from fraud_v2.evaluation.reports import write_monitoring_report
from fraud_v2.infrastructure.redpanda_dead_letter_publisher import RedpandaDeadLetterPublisher
from fraud_v2.infrastructure.redpanda_lag import RedpandaLagProbe
from fraud_v2.infrastructure.redpanda_publisher import RedpandaEventPublisher
from fraud_v2.llm_lab.provider import NoveltyLedger, provider_from_env
from fraud_v2.models.eval_dashboard import write_model_eval_dashboard
from fraud_v2.models.registry import JsonModelRegistry, ModelStatus
from fraud_v2.models.shadow import write_shadow_scores
from fraud_v2.models.train import train_baseline
from fraud_v2.observability.stream_health import (
    StreamHealthStatus,
    StreamHealthThresholds,
    build_stream_health_report,
    load_json_mapping,
    write_stream_health_artifacts,
)
from fraud_v2.policy.approvals import (
    JsonPolicyApprovalStore,
    create_policy_approval,
    generate_policy_signing_keypair,
)
from fraud_v2.policy.registry import (
    JsonThresholdPolicyRegistry,
    PolicyStatus,
    RegisteredThresholdPolicy,
    write_active_policy,
)
from fraud_v2.policy.thresholds import load_threshold_policy
from fraud_v2.public_data.paysim import convert_paysim_csv
from fraud_v2.public_data.registry import describe_public_dataset
from fraud_v2.replay.runner import run_replay
from fraud_v2.security.auth import AuthRole
from fraud_v2.storage.ports import FraudStore
from fraud_v2.storage.postgres_store import PostgresStore
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator, load_events_jsonl
from fraud_v2.workers.outbox import DryRunEventPublisher, OutboxWorker
from fraud_v2.workers.stream_consumer import RedpandaConsumerFactory, StreamIngestionWorker
from fraud_v2.workers.stream_supervisor import StreamSupervisor

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


def _write_json_payload(payload: Any, output_path: Path | None) -> None:
    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )


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
    policy_path: Path | None = None,
) -> None:
    store = SQLiteStore(db_path)
    events = store.list_events()
    if not events:
        raise typer.BadParameter("database has no events; run generate and load first")
    request = DecisionRequest(
        target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
        as_of=max(event.occurred_at for event in events),
    )
    decision = DecisionEngine(store, policy=load_threshold_policy(policy_path)).score(request)
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
def load_benchmark(
    users: int = typer.Option(1000, min=10, max=100000),
    score_users: int = typer.Option(50, min=1, max=10000),
    db_path: Path = Path("data/local/load-benchmark.sqlite"),
    output_path: Path = Path("data/local/load-benchmark-report.json"),
    seed: int = 20260531,
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    report = run_load_benchmark(
        users=users,
        score_users=score_users,
        db_path=db_path,
        output_path=output_path,
        seed=seed,
        overwrite=overwrite,
    )
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
def public_dataset_convert(
    name: str,
    input_path: Path,
    output_path: Path = Path("data/public/converted/events.jsonl"),
    limit_rows: int | None = typer.Option(None, min=1),
) -> None:
    if name != "paysim":
        raise typer.BadParameter("only 'paysim' conversion is implemented locally")
    report = convert_paysim_csv(
        input_path=input_path,
        output_path=output_path,
        limit_rows=limit_rows,
    )
    _print_json(report.__dict__)


@app.command()
def policy_show(policy_path: Path | None = None) -> None:
    _print_json(load_threshold_policy(policy_path).model_dump(mode="json"))


@app.command()
def policy_register(
    policy_path: Path,
    registry_path: Path = Path("data/policies/registry.json"),
    status: PolicyStatus = PolicyStatus.CANDIDATE,
    notes: str = "",
) -> None:
    registered = JsonThresholdPolicyRegistry(registry_path).register(
        policy_path=policy_path,
        status=status,
        notes=notes,
    )
    _print_json({"policy": registered.model_dump(mode="json"), "registry": str(registry_path)})


@app.command()
def policy_list(registry_path: Path = Path("data/policies/registry.json")) -> None:
    policies = JsonThresholdPolicyRegistry(registry_path).list_policies()
    _print_json({"policies": [policy.model_dump(mode="json") for policy in policies]})


@app.command()
def policy_promote(
    policy_version: str,
    registry_path: Path = Path("data/policies/registry.json"),
    active_policy_path: Path = Path("data/policies/active-threshold-policy.json"),
) -> None:
    promoted = JsonThresholdPolicyRegistry(registry_path).promote(policy_version)
    write_active_policy(promoted.policy, active_policy_path)
    _print_json(
        {
            "policy": promoted.model_dump(mode="json"),
            "registry": str(registry_path),
            "active_policy_path": str(active_policy_path),
        }
    )


@app.command()
def policy_keygen(
    private_key_path: Path = Path("data/policies/local-policy-approval-ed25519.pem"),
    public_key_path: Path = Path("data/policies/local-policy-approval-ed25519.pub.pem"),
    overwrite: bool = typer.Option(False, "--overwrite"),
) -> None:
    _print_json(
        generate_policy_signing_keypair(
            private_key_path=private_key_path,
            public_key_path=public_key_path,
            overwrite=overwrite,
        )
    )


@app.command()
def policy_approve(
    policy_version: str,
    approver_id: str = typer.Option(..., "--approver-id"),
    private_key_path: Path = typer.Option(..., "--private-key-path"),
    approver_role: str = "policy_approver",
    registry_path: Path = Path("data/policies/registry.json"),
    approvals_path: Path = Path("data/policies/approvals.json"),
    notes: str = "",
) -> None:
    policy = _registered_policy(registry_path, policy_version)
    approval = create_policy_approval(
        policy_version=policy.version,
        policy_sha256=policy.policy_sha256,
        approver_id=approver_id,
        approver_role=approver_role,
        private_key_path=private_key_path,
        notes=notes,
    )
    saved = JsonPolicyApprovalStore(approvals_path).add(approval)
    _print_json({"approval": saved.model_dump(mode="json"), "approvals_path": str(approvals_path)})


@app.command()
def policy_approval_status(
    policy_version: str,
    registry_path: Path = Path("data/policies/registry.json"),
    approvals_path: Path = Path("data/policies/approvals.json"),
    required_approvals: int = typer.Option(2, min=1, max=10),
) -> None:
    policy = _registered_policy(registry_path, policy_version)
    status = JsonPolicyApprovalStore(approvals_path).status(
        policy_version=policy.version,
        policy_sha256=policy.policy_sha256,
        required_approvals=required_approvals,
    )
    _print_json(status.model_dump(mode="json"))


@app.command()
def policy_promote_approved(
    policy_version: str,
    registry_path: Path = Path("data/policies/registry.json"),
    approvals_path: Path = Path("data/policies/approvals.json"),
    active_policy_path: Path = Path("data/policies/active-threshold-policy.json"),
    required_approvals: int = typer.Option(2, min=1, max=10),
) -> None:
    policy = _registered_policy(registry_path, policy_version)
    approval_status = JsonPolicyApprovalStore(approvals_path).status(
        policy_version=policy.version,
        policy_sha256=policy.policy_sha256,
        required_approvals=required_approvals,
    )
    if not approval_status.approved:
        _print_json(approval_status.model_dump(mode="json"))
        raise typer.Exit(code=2)
    promoted = JsonThresholdPolicyRegistry(registry_path).promote(policy_version)
    write_active_policy(promoted.policy, active_policy_path)
    _print_json(
        {
            "policy": promoted.model_dump(mode="json"),
            "approval_status": approval_status.model_dump(mode="json"),
            "registry": str(registry_path),
            "active_policy_path": str(active_policy_path),
        }
    )


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
def stream_consume(
    bootstrap_servers: str = "localhost:19092",
    topic: str = "fraud.events",
    group_id: str = "fraud-v2-local",
    max_messages: int = typer.Option(100, min=1, max=100000),
    max_empty_polls: int = typer.Option(3, min=1, max=100),
    poll_timeout_seconds: float = typer.Option(1.0, min=0.1, max=30.0),
    store_backend: str = typer.Option("sqlite", "--store-backend"),
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    postgres_dsn: str = "postgresql://fraud:fraud@localhost:5432/fraud_v2",
    publish_dead_letters: bool = typer.Option(
        False, "--publish-dead-letters/--db-dead-letters-only"
    ),
    dead_letter_topic: str = "fraud.dead_letters",
    fail_on_error: bool = typer.Option(True, "--fail-on-error/--allow-errors"),
) -> None:
    store = _store_from_cli(
        store_backend=store_backend,
        db_path=db_path,
        postgres_dsn=postgres_dsn,
    )
    consumer = RedpandaConsumerFactory(
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
    ).create()
    report = StreamIngestionWorker(
        store=store,
        consumer=consumer,
        topic=topic,
        group_id=group_id,
        dead_letter_publisher=(
            RedpandaDeadLetterPublisher(bootstrap_servers=bootstrap_servers)
            if publish_dead_letters
            else None
        ),
        dead_letter_topic=dead_letter_topic,
        poll_timeout_seconds=poll_timeout_seconds,
        max_empty_polls=max_empty_polls,
    ).run(max_messages=max_messages)
    _print_json(report.__dict__)
    if report.failed > 0 and fail_on_error:
        raise typer.Exit(code=2)


@app.command()
def stream_supervise(
    bootstrap_servers: str = "localhost:19092",
    topic: str = "fraud.events",
    group_id: str = "fraud-v2-local",
    max_batches: int = typer.Option(1, min=1, max=100000),
    batch_size: int = typer.Option(100, min=1, max=100000),
    max_empty_polls: int = typer.Option(3, min=1, max=100),
    poll_timeout_seconds: float = typer.Option(1.0, min=0.1, max=30.0),
    restart_backoff_seconds: float = typer.Option(5.0, min=0.0, max=300.0),
    idle_sleep_seconds: float = typer.Option(1.0, min=0.0, max=300.0),
    max_consecutive_failures: int = typer.Option(3, min=1, max=100),
    store_backend: str = typer.Option("sqlite", "--store-backend"),
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    postgres_dsn: str = "postgresql://fraud:fraud@localhost:5432/fraud_v2",
    publish_dead_letters: bool = typer.Option(
        False, "--publish-dead-letters/--db-dead-letters-only"
    ),
    dead_letter_topic: str = "fraud.dead_letters",
    fail_on_unhealthy: bool = typer.Option(True, "--fail-on-unhealthy/--allow-unhealthy"),
    output_path: Path | None = None,
) -> None:
    store = _store_from_cli(
        store_backend=store_backend,
        db_path=db_path,
        postgres_dsn=postgres_dsn,
    )
    report = StreamSupervisor(
        store=store,
        consumer_factory=RedpandaConsumerFactory(
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
        ),
        topic=topic,
        group_id=group_id,
        batch_size=batch_size,
        max_empty_polls=max_empty_polls,
        poll_timeout_seconds=poll_timeout_seconds,
        restart_backoff_seconds=restart_backoff_seconds,
        idle_sleep_seconds=idle_sleep_seconds,
        max_consecutive_failures=max_consecutive_failures,
        dead_letter_publisher=(
            RedpandaDeadLetterPublisher(bootstrap_servers=bootstrap_servers)
            if publish_dead_letters
            else None
        ),
        dead_letter_topic=dead_letter_topic,
    ).run(max_batches=max_batches)
    payload = report.__dict__
    _write_json_payload(payload, output_path)
    _print_json(payload)
    if report.status == "failed" and fail_on_unhealthy:
        raise typer.Exit(code=2)


@app.command()
def stream_dead_letters(
    store_backend: str = typer.Option("sqlite", "--store-backend"),
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    postgres_dsn: str = "postgresql://fraud:fraud@localhost:5432/fraud_v2",
    limit: int = typer.Option(100, min=1, max=1000),
) -> None:
    store = _store_from_cli(
        store_backend=store_backend,
        db_path=db_path,
        postgres_dsn=postgres_dsn,
    )
    _print_json(
        {
            "dead_letters": [
                dead_letter.model_dump(mode="json")
                for dead_letter in store.list_stream_dead_letters(limit=limit)
            ]
        }
    )


@app.command()
def stream_lag(
    bootstrap_servers: str = "localhost:19092",
    topic: str = "fraud.events",
    group_id: str = "fraud-v2-local",
    timeout_seconds: float = typer.Option(10.0, min=1.0, max=60.0),
    output_path: Path | None = None,
) -> None:
    report = RedpandaLagProbe(bootstrap_servers=bootstrap_servers).report(
        topic=topic,
        group_id=group_id,
        timeout_seconds=timeout_seconds,
    )
    payload = asdict(report)
    _write_json_payload(payload, output_path)
    _print_json(payload)


@app.command()
def stream_health(
    bootstrap_servers: str = "localhost:19092",
    topic: str = "fraud.events",
    group_id: str = "fraud-v2-local",
    live_lag: bool = typer.Option(False, "--live-lag/--skip-live-lag"),
    lag_report_path: Path | None = None,
    supervision_report_path: Path | None = None,
    store_backend: str = typer.Option("sqlite", "--store-backend"),
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    postgres_dsn: str = "postgresql://fraud:fraud@localhost:5432/fraud_v2",
    dead_letter_limit: int = typer.Option(100, min=1, max=1000),
    warning_lag: int = typer.Option(100, min=1),
    critical_lag: int = typer.Option(1000, min=1),
    warning_dead_letters: int = typer.Option(1, min=1),
    critical_dead_letters: int = typer.Option(10, min=1),
    warning_failed_batches: int = typer.Option(1, min=1),
    critical_failed_batches: int = typer.Option(3, min=1),
    output_path: Path = Path("data/local/stream-health-report.json"),
    dashboard_path: Path = Path("data/local/stream-health-dashboard.html"),
    fail_on_critical: bool = typer.Option(True, "--fail-on-critical/--allow-critical"),
) -> None:
    store = _store_from_cli(
        store_backend=store_backend,
        db_path=db_path,
        postgres_dsn=postgres_dsn,
    )
    lag_payload: dict[str, Any] | None = None
    lag_source = "not_checked"
    lag_error: str | None = None
    if lag_report_path is not None:
        lag_payload = dict(load_json_mapping(lag_report_path))
        lag_source = str(lag_report_path)
    elif live_lag:
        lag_source = "live"
        try:
            lag_payload = asdict(
                RedpandaLagProbe(bootstrap_servers=bootstrap_servers).report(
                    topic=topic,
                    group_id=group_id,
                )
            )
        except RuntimeError as exc:
            lag_error = f"{type(exc).__name__}: {exc}"[:500]

    supervision_payload = (
        dict(load_json_mapping(supervision_report_path))
        if supervision_report_path is not None
        else None
    )
    report = build_stream_health_report(
        topic=topic,
        group_id=group_id,
        dead_letters=store.list_stream_dead_letters(limit=dead_letter_limit),
        dead_letter_limit=dead_letter_limit,
        lag_payload=lag_payload,
        lag_source=lag_source,
        lag_error=lag_error,
        supervision_payload=supervision_payload,
        supervision_source=str(supervision_report_path)
        if supervision_report_path
        else "not_loaded",
        thresholds=StreamHealthThresholds(
            warning_lag=warning_lag,
            critical_lag=critical_lag,
            warning_dead_letters=warning_dead_letters,
            critical_dead_letters=critical_dead_letters,
            warning_failed_batches=warning_failed_batches,
            critical_failed_batches=critical_failed_batches,
        ),
    )
    report = write_stream_health_artifacts(
        report,
        output_path=output_path,
        dashboard_path=dashboard_path,
    )
    _print_json(report.model_dump(mode="json"))
    if report.status == StreamHealthStatus.CRITICAL and fail_on_critical:
        raise typer.Exit(code=2)


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
def evidence_export(
    decision_id: UUID,
    output_path: Path = Path("data/local/evidence/decision-evidence.enc.json"),
    passphrase_env: str = EVIDENCE_PASSPHRASE_ENV,
    store_backend: str = typer.Option("sqlite", "--store-backend"),
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    postgres_dsn: str = "postgresql://fraud:fraud@localhost:5432/fraud_v2",
) -> None:
    passphrase = os.getenv(passphrase_env)
    if passphrase is None:
        raise typer.BadParameter(f"set {passphrase_env} before exporting encrypted evidence")
    store = _store_from_cli(
        store_backend=store_backend,
        db_path=db_path,
        postgres_dsn=postgres_dsn,
    )
    decision = store.get_decision(decision_id)
    envelope = write_encrypted_decision_evidence(
        decision=decision,
        output_path=output_path,
        passphrase=passphrase,
    )
    _print_json(
        {
            "decision_id": str(decision_id),
            "output_path": str(output_path),
            "schema_version": envelope["schema_version"],
            "encryption": envelope["encryption"],
            "kdf": envelope["kdf"],
        }
    )


@app.command()
def retention_report(
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    as_of: str | None = None,
    event_days: int = typer.Option(90, min=1),
    decision_days: int = typer.Option(365, min=1),
    review_days: int = typer.Option(365, min=1),
    outbox_days: int = typer.Option(30, min=1),
    stream_dead_letter_days: int = typer.Option(30, min=1),
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
            stream_dead_letter_days=stream_dead_letter_days,
            audit_days=audit_days,
        ),
    )
    _print_json(report.model_dump(mode="json"))


@app.command()
def retention_prune(
    db_path: Path = Path("data/local/fraud_v2.sqlite"),
    as_of: str | None = None,
    execute: bool = typer.Option(False, "--execute"),
    event_days: int = typer.Option(90, min=1),
    decision_days: int = typer.Option(365, min=1),
    review_days: int = typer.Option(365, min=1),
    outbox_days: int = typer.Option(30, min=1),
    stream_dead_letter_days: int = typer.Option(30, min=1),
    audit_days: int = typer.Option(3650, min=1),
) -> None:
    report_as_of = _parse_as_of(as_of)
    policy = RetentionPolicy(
        event_days=event_days,
        decision_days=decision_days,
        review_days=review_days,
        outbox_days=outbox_days,
        stream_dead_letter_days=stream_dead_letter_days,
        audit_days=audit_days,
    )
    store = SQLiteStore(db_path)
    if execute:
        report = store.prune_retention(as_of=report_as_of, policy=policy)
    else:
        dry_run = store.retention_report(as_of=report_as_of, policy=policy)
        report = dry_run.model_copy(
            update={
                "tables": [
                    table.model_copy(update={"action": "dry_run"}) for table in dry_run.tables
                ]
            }
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


@app.command()
def model_eval_dashboard(
    report_path: Path = Path("data/models/baseline/baseline-report.json"),
    output_path: Path = Path("data/models/eval-dashboard.html"),
    shadow_scores_path: Path | None = None,
) -> None:
    summary = write_model_eval_dashboard(
        report_path=report_path,
        output_path=output_path,
        shadow_scores_path=shadow_scores_path,
    )
    _print_json(summary)


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


def _store_from_cli(store_backend: str, db_path: Path, postgres_dsn: str) -> FraudStore:
    backend = store_backend.lower()
    if backend == "sqlite":
        return SQLiteStore(db_path)
    if backend == "postgres":
        return PostgresStore(postgres_dsn)
    raise typer.BadParameter("store backend must be 'sqlite' or 'postgres'")


def _registered_policy(registry_path: Path, policy_version: str) -> RegisteredThresholdPolicy:
    for policy in JsonThresholdPolicyRegistry(registry_path).list_policies():
        if policy.version == policy_version:
            return policy
    raise typer.BadParameter(f"policy version not found in registry: {policy_version}")
