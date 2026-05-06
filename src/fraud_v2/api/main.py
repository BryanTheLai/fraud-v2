# ruff: noqa: E501
from __future__ import annotations

import json
import time
from collections import Counter
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from logging import getLogger
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response

from fraud_v2 import __version__
from fraud_v2.cockpit import (
    CockpitScenario,
    DecisionModeComparison,
    SignalContribution,
    cockpit_scenario,
    cockpit_scenarios,
    compare_decision_modes,
    signal_contributions,
)
from fraud_v2.compliance.interventions import build_break_spell_draft
from fraud_v2.compliance.reasons import adverse_action_style_reasons
from fraud_v2.config.settings import Settings, get_settings
from fraud_v2.connectors.mock_vendors import ConnectorResult
from fraud_v2.connectors.signal_lab import LocalCameraMetadataAnalyzer, LocalPublicKybConnector
from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.audit import AuditEntry, AuditVerificationReport
from fraud_v2.domain.decisions import DecisionRequest, DecisionResponse, RiskSignal
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import (
    EntityType,
    EventType,
    FeatureFreshnessStatus,
    LabelValue,
    ReviewOutcome,
)
from fraud_v2.domain.errors import DecisionNotFound, DuplicatePayloadConflict
from fraud_v2.domain.events import (
    CameraMetadataObserved,
    ChargebackReceived,
    DeviceObserved,
    EventEnvelope,
    LabelCreated,
    LoginAttempt,
    PaymentAttempted,
)
from fraud_v2.domain.retention import RetentionPolicy, RetentionReport
from fraud_v2.domain.reviews import ReviewCase, ReviewDecision, ReviewDecisionRequest
from fraud_v2.domain.stream import StreamDeadLetter
from fraud_v2.graph.service import GraphService
from fraud_v2.observability.logging import (
    configure_logging,
    new_trace_id,
    reset_trace_id,
    set_trace_id,
)
from fraud_v2.observability.metrics import (
    decision_counter,
    decision_latency,
    event_counter,
    http_request_counter,
    http_request_latency,
    metrics_response,
)
from fraud_v2.observability.traces import append_local_trace_span
from fraud_v2.policy.thresholds import load_threshold_policy
from fraud_v2.review.service import ReviewService
from fraud_v2.security.auth import AuthPrincipal, AuthRole, require_roles
from fraud_v2.simulation.workbench import SimulationRequest, SimulationResponse, run_simulation
from fraud_v2.storage.ports import FraudStore
from fraud_v2.storage.postgres_store import PostgresStore
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import DEFAULT_SYNTHETIC_USERS, SyntheticFraudGenerator

configure_logging()
logger = getLogger("fraud_v2.api")
app = FastAPI(title="fraud-v2", version=__version__)


@dataclass(frozen=True)
class DemoScenario:
    key: str
    title: str
    user_id: str
    amount: float
    as_of: str
    expected: str
    narrative: str
    action_note: str


@dataclass(frozen=True)
class SyntheticCoverageSummary:
    events: int
    users: int
    fraud_labels: int
    typologies: tuple[tuple[str, int], ...]
    event_types: tuple[tuple[str, int], ...]
    shared_devices: tuple[tuple[str, int], ...]
    payment_burst_users: int
    virtual_camera_events: int
    failed_logins: int
    false_positive_pressure: tuple[tuple[str, int], ...]


DEMO_SCENARIOS: tuple[DemoScenario, ...] = (
    DemoScenario(
        key="clean",
        title="Clean instant-cash applicant",
        user_id="user_00120",
        amount=250,
        as_of="2026-05-08T12:27:00Z",
        expected="GREEN / APPROVE",
        narrative="Normal device, normal session rhythm, no chargeback, no confirmed fraud label.",
        action_note="Simulated auto-approve.",
    ),
    DemoScenario(
        key="virtual_camera",
        title="Virtual camera review",
        user_id="user_00000",
        amount=250,
        as_of="2026-05-05T13:00:00Z",
        expected="YELLOW / MANUAL_REVIEW",
        narrative="Camera metadata is missing and behavior entropy is low, but future labels are hidden.",
        action_note="Inject friction and send to analyst review.",
    ),
    DemoScenario(
        key="graph_neighbor",
        title="Graph-risk neighbor",
        user_id="user_00050",
        amount=250,
        as_of="2026-05-08T12:27:00Z",
        expected="YELLOW / MANUAL_REVIEW",
        narrative="Applicant is near a confirmed fraud cluster through shared graph evidence.",
        action_note="Hold final decision until graph evidence is reviewed.",
    ),
    DemoScenario(
        key="confirmed_fraud",
        title="Confirmed fraud block",
        user_id="user_00000",
        amount=1000,
        as_of="2026-05-08T12:27:00Z",
        expected="RED / BLOCK",
        narrative="Chargeback, confirmed fraud label, camera anomaly, and low behavior entropy align.",
        action_note="Simulated block. No real account action.",
    ),
    DemoScenario(
        key="first_party",
        title="First-party instant-cash default",
        user_id="user_00003",
        amount=1000,
        as_of="2026-05-08T12:27:00Z",
        expected="RED / BLOCK",
        narrative="Instant-cash borrower has a later chargeback/default-style fraud label.",
        action_note="Simulated payout hold and review evidence export.",
    ),
    DemoScenario(
        key="break_spell",
        title="APP/BEC break-the-spell",
        user_id="user_00005",
        amount=1000,
        as_of="2026-05-05T13:00:00Z",
        expected="YELLOW / SIMULATED_INTERVENTION",
        narrative="Risky transfer pattern gets a customer prompt instead of a silent hard block.",
        action_note="Simulated Break-the-Spell prompt. No real message sent.",
    ),
)


def store(settings: Settings = Depends(get_settings)) -> FraudStore:
    backend = settings.store_backend.lower()
    if backend == "sqlite":
        return SQLiteStore(settings.sqlite_path)
    if backend == "postgres":
        return PostgresStore(settings.postgres_dsn)
    raise HTTPException(status_code=500, detail=f"unsupported FRAUD_STORE_BACKEND: {backend}")


@app.middleware("http")
async def add_trace_and_request_metrics(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    trace_id = request.headers.get("X-Request-ID") or new_trace_id()
    token = set_trace_id(trace_id)
    start = time.perf_counter()
    started_at = datetime.now(UTC)
    route = request.url.path
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        route = _route_template(request)
        response.headers["X-Trace-ID"] = trace_id
        return response
    finally:
        duration = time.perf_counter() - start
        route = _route_template(request, fallback=route)
        status = str(status_code)
        http_request_counter.labels(
            method=request.method,
            route=route,
            status=status,
        ).inc()
        http_request_latency.labels(method=request.method, route=route).observe(duration)
        logger.info(
            "request_completed",
            extra={
                "trace_id": trace_id,
                "method": request.method,
                "path": route,
                "status_code": status_code,
                "duration_ms": round(duration * 1000, 3),
            },
        )
        reset_trace_id(token)
        _write_request_trace(
            trace_id=trace_id,
            route=route,
            method=request.method,
            status_code=status_code,
            started_at=started_at,
            duration_ms=duration * 1000,
        )


def _route_template(request: Request, fallback: str | None = None) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str):
        return path
    return fallback or request.url.path


def _write_request_trace(
    *,
    trace_id: str,
    route: str,
    method: str,
    status_code: int,
    started_at: datetime,
    duration_ms: float,
) -> None:
    trace_export_path = get_settings().trace_export_path
    if trace_export_path is None:
        return
    try:
        append_local_trace_span(
            path=trace_export_path,
            trace_id=trace_id,
            span_name="http.request",
            started_at=started_at,
            ended_at=datetime.now(UTC),
            duration_ms=duration_ms,
            status_code=status_code,
            attributes={
                "method": method,
                "route": route,
            },
        )
    except OSError as exc:
        logger.warning(
            "local_trace_export_failed",
            extra={
                "trace_id": trace_id,
                "method": method,
                "path": route,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 3),
                "error": str(exc)[:300],
            },
        )


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "fraud-v2",
        "cockpit": "/cockpit",
        "docs": "/docs",
        "demo": "/demo",
        "dashboard": "/dashboard",
        "health": "/health/ready",
    }


@app.get("/cockpit", response_class=HTMLResponse)
def instant_cash_cockpit(
    scenario: str = Query(default="graph_ring"),
    db: FraudStore = Depends(store),
    settings: Settings = Depends(get_settings),
) -> str:
    _ensure_demo_seed(db)
    selected = cockpit_scenario(scenario)
    policy = load_threshold_policy(settings.policy_path)
    decision = DecisionEngine(db, policy=policy).preview(
        DecisionRequest(
            target_entity=EntityRef(entity_type=EntityType.USER, entity_id=selected.user_id),
            as_of=selected.as_of_datetime(),
            amount=selected.amount,
            context={"surface": "cockpit", "scenario": selected.key},
        )
    )
    simulation = run_simulation(selected.simulation, policy=policy)
    events = [
        event for event in db.list_events() if event.occurred_at <= decision.feature_vector.as_of
    ]
    graph = GraphService(events).neighborhood(decision.target_entity, depth=2)
    fraud_keys = _confirmed_fraud_graph_keys(events)
    modes = compare_decision_modes(selected, decision, policy)
    contributions = signal_contributions(decision, simulation)
    coverage = _synthetic_coverage(events)
    benchmark_report = _load_model_report(Path("data/models/benchmark-report.json"))
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Instant Cash Fraud Cockpit</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("Instant Cash Fraud Cockpit", "One presentation surface: scenario, score, graph, ML, action, blockers.")}
    <main class="shell">
      <section class="main">
        <div class="panel cockpit-hero">
          <div class="panel-head">
            <div>
              <h2>{escape(selected.title)}</h2>
              <p>{escape(selected.narrative)}</p>
            </div>
            <span class="badge neutral">{escape(selected.blog_category)}</span>
          </div>
          {_cockpit_scenario_tabs(selected.key)}
          <div class="hero-row">
            {_plain_tile("Hybrid score", modes[-1].score, "Recommended local operating score")}
            {_status_tile("Tier", modes[-1].tier.value, modes[-1].tier.value.lower())}
            {_status_tile("Action", modes[-1].action.value, _action_class(modes[-1].action.value))}
            {_plain_tile("Model probability", f"{selected.model_probability:.0%}", selected.typology)}
          </div>
        </div>
        <div class="split">
          <section class="panel">
            <h2>Rules-only vs model-only vs hybrid</h2>
            <p>Hybrid wins locally because the model ranks risk while rules keep the decision explainable and bounded.</p>
            {_mode_comparison_table(modes)}
          </section>
          <section class="panel">
            <h2>Score contribution</h2>
            <p>Signals are synthetic/local, but each reason is safe to show in a review workflow.</p>
            {_contribution_table(contributions)}
          </section>
        </div>
        <div class="split">
          <section class="panel">
            <h2>Timeline</h2>
            {_cockpit_timeline(selected)}
            <h3>Local event proof</h3>
            {_event_timeline_table(events, selected.user_id)}
          </section>
          <section class="panel">
            <h2>Explain this decision</h2>
            {_reason_list(decision.safe_reasons)}
            <h3>Missing data</h3>
            {_plain_list(selected.missing_data)}
            <h3>No real action happened</h3>
            <p>Approval, block, hold, customer message, SAR, KYC/KYB, and money movement are simulated or absent unless explicitly wired later with approved vendors and legal review.</p>
          </section>
        </div>
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2>Graph and ring evidence</h2>
              <p>Local NetworkX graph proof. This is the truthful substitute before real consortium data or GNN training exists.</p>
            </div>
            <a class="button secondary" href="/dashboard/graph?entity_id={escape(selected.user_id)}">Open graph page</a>
          </div>
          <div class="graph">{_graph_svg(graph, decision.target_entity.graph_key, fraud_keys)}</div>
          <h3>What matters</h3>
          {_plain_list(selected.graph_evidence)}
        </div>
        {_model_benchmark_panel(benchmark_report)}
        {_synthetic_coverage_panel(coverage)}
      </section>
      <aside class="rail">
        {_cockpit_decision_rail(selected, decision, simulation)}
        {_cockpit_gap_panel(selected)}
        {_action_ladder()}
      </aside>
    </main>
  </body>
</html>"""


@app.get("/demo", response_class=HTMLResponse)
def demo_cockpit(
    decision_id: UUID | None = None,
    db: FraudStore = Depends(store),
) -> str:
    _ensure_demo_seed(db)
    events = db.list_events()
    decisions = db.list_decisions()
    cases = db.list_review_cases()
    coverage = _synthetic_coverage(events)
    selected_decision = _selected_decision(decision_id, decisions)
    scenario_cards = "".join(_scenario_card(scenario) for scenario in DEMO_SCENARIOS)
    selected_panel = _selected_decision_panel(selected_decision)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 demo cockpit</title>
    {_base_style()}
    <script>
      async function runCustomScenario() {{
        const scenario = document.getElementById("scenario").value;
        const userId = document.getElementById("user_id").value;
        const amount = document.getElementById("amount").value;
        const asOf = document.getElementById("as_of").value;
        const params = new URLSearchParams({{scenario: scenario, user_id: userId, amount: amount, as_of: asOf}});
        const response = await fetch("/demo/run?" + params.toString(), {{method: "POST"}});
        window.location.href = response.url;
      }}
    </script>
  </head>
  <body>
    {_top_nav("Demo Cockpit", "Presentation workspace for local synthetic fraud scenarios.")}
    <main class="shell">
      <section class="main">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2>Run a seeded scenario</h2>
              <p>Every action is local and simulated. No real KYC, PII, money movement, or filing.</p>
            </div>
            <form method="post" action="/demo/reset">
              <button class="button secondary" type="submit">Reset demo state</button>
            </form>
          </div>
          <div class="scenario-grid">{scenario_cards}</div>
        </div>
        <div class="panel">
          <h2>Customize one run</h2>
          <div class="custom-grid">
            <label>Scenario<select id="scenario">{_scenario_options()}</select></label>
            <label>User<input id="user_id" value="user_00050"></label>
            <label>Amount<input id="amount" value="750" type="number" min="0" step="50"></label>
            <label>As of<input id="as_of" value="2026-05-08T12:27:00Z"></label>
          </div>
          <button class="button" type="button" onclick="runCustomScenario()">Run customized score</button>
        </div>
        {selected_panel}
        <div class="panel">
          <h2>Recent decisions</h2>
          {_decision_table(decisions[-10:])}
        </div>
      </section>
      <aside class="rail">
        {_queue_summary(events, decisions, cases)}
        {_synthetic_coverage_panel(coverage, compact=True)}
        {_action_ladder()}
        {_coverage_map()}
      </aside>
    </main>
  </body>
</html>"""


@app.post("/demo/run")
def run_demo_scenario(
    scenario: str = Query(default="graph_neighbor"),
    user_id: str | None = Query(default=None),
    amount: float | None = Query(default=None, ge=0),
    as_of: str | None = Query(default=None),
    db: FraudStore = Depends(store),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    _ensure_demo_seed(db)
    selected = _scenario_by_key(scenario)
    target_user_id = user_id or selected.user_id
    target_amount = amount if amount is not None else selected.amount
    target_as_of = _demo_as_of(as_of or selected.as_of)
    decision = _score_local_decision(
        db=db,
        settings=settings,
        user_id=target_user_id,
        amount=target_amount,
        as_of=target_as_of,
    )
    location = f"/demo?decision_id={decision.decision_id}"
    return RedirectResponse(url=location, status_code=303)


@app.post("/demo/reset")
def reset_demo_state(db: FraudStore = Depends(store)) -> RedirectResponse:
    dataset = SyntheticFraudGenerator().generate(users=DEFAULT_SYNTHETIC_USERS)
    resetter = getattr(db, "reset_demo_data", None)
    if not callable(resetter):
        raise HTTPException(status_code=409, detail="demo reset is available for local stores only")
    resetter(dataset.events)
    return RedirectResponse(url="/demo", status_code=303)


@app.get("/dashboard/cases/{case_id}", response_class=HTMLResponse)
def case_dashboard(case_id: UUID, db: FraudStore = Depends(store)) -> str:
    case = _case_by_id(db.list_review_cases(), case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"review case not found: {case_id}")
    decision = db.get_decision(case.decision_id)
    events = [
        event for event in db.list_events() if event.occurred_at <= decision.feature_vector.as_of
    ]
    graph = GraphService(events).neighborhood(decision.target_entity, depth=2)
    fraud_keys = _confirmed_fraud_graph_keys(events)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 case {escape(str(case.case_id))}</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("Primary Case", "Timeline first. Facts second. Simulated actions only.")}
    <main class="shell">
      <section class="main">
        <div class="hero-row">
          {_score_tile(decision)}
          {_status_tile("Recommendation", decision.action.value, _action_class(decision.action.value))}
          {_status_tile("Resolution", case.status.upper(), "neutral")}
          {_status_tile("Trace", str(decision.reasoning_trace_id)[:8], "neutral")}
        </div>
        <div class="split">
          <section class="panel">
            <h2>What happened</h2>
            <p>Timeline for the target user, using only local synthetic events.</p>
            {_event_timeline_table(events, decision.target_entity.entity_id)}
          </section>
          <section class="panel">
            <h2>Why this case is high-risk</h2>
            {_reason_list(decision.safe_reasons)}
            <h3>Feature values</h3>
            {_feature_table(decision)}
          </section>
        </div>
        <div class="panel">
          <h2>Graph evidence</h2>
          <div class="graph">{_graph_svg(graph, decision.target_entity.graph_key, fraud_keys)}</div>
          {_graph_relationship_table(graph["edges"])}
        </div>
      </section>
      <aside class="rail">
        {_decision_rail(case, decision)}
        {_action_ladder()}
      </aside>
    </main>
  </body>
</html>"""


@app.post("/demo/review/{case_id}")
def simulate_review_decision(
    case_id: UUID,
    outcome: ReviewOutcome = Query(default=ReviewOutcome.NEEDS_MORE_INFO),
    db: FraudStore = Depends(store),
) -> RedirectResponse:
    ReviewService(db).decide(
        case_id,
        ReviewDecisionRequest(
            analyst_id="demo-analyst",
            outcome=outcome,
            confidence=0.9,
            note="Simulated local analyst decision from demo UI.",
        ),
    )
    return RedirectResponse(url=f"/dashboard/cases/{case_id}", status_code=303)


@app.get("/dashboard/ops", response_class=HTMLResponse)
def ops_dashboard(db: FraudStore = Depends(store)) -> str:
    _ensure_demo_seed(db)
    events = db.list_events()
    decisions = db.list_decisions()
    cases = db.list_review_cases()
    dead_letters = db.list_stream_dead_letters(limit=100)
    audit = db.verify_audit_chain()
    outbox = db.outbox_counts()
    stale_features = _stale_feature_count(decisions)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 ops dashboard</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("Ops Metrics", "Human-readable health. Raw Prometheus stays at /metrics.")}
    <main class="shell single">
      <section class="main">
        <div class="hero-row">
          {_plain_tile("Events", len(events), "Canonical synthetic/local events")}
          {_plain_tile("Decisions", len(decisions), "Stored decision records")}
          {_plain_tile("Open reviews", sum(1 for case in cases if case.status == "open"), "Manual queue")}
          {_plain_tile("Dead letters", len(dead_letters), "Stream records needing inspection")}
        </div>
        <div class="split">
          <section class="panel">
            <h2>Reliability checks</h2>
            <table><tbody>
              {_ops_row("Audit hash chain", "healthy" if audit.valid else "broken", f"{audit.entries_checked} entries checked")}
              {_ops_row("Feature freshness", "healthy" if stale_features == 0 else "watch", f"{stale_features} stale/missing/degraded values in recent decisions")}
              {_ops_row("Outbox pending", "healthy" if outbox.get("PENDING", 0) == 0 else "watch", str(outbox))}
              {_ops_row("Raw Prometheus", "available", "<a href='/metrics'>/metrics</a>")}
              {_ops_row("Grafana full mode", "optional", "http://127.0.0.1:3000/d/fraud-v2-overview/fraud-v2-overview")}
            </tbody></table>
          </section>
          <section class="panel">
            <h2>Decision mix</h2>
            {_tier_mix_table(decisions)}
          </section>
        </div>
      </section>
    </main>
  </body>
</html>"""


@app.get("/dashboard/ml", response_class=HTMLResponse)
def ml_dashboard() -> str:
    report_path = Path("data/models/baseline/baseline-report.json")
    mlops_path = Path("data/local/mlops-report.json")
    report = _load_model_report(report_path)
    mlops = _load_model_report(mlops_path)
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 ML dashboard</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("ML Dashboard", "Calibration, profit, threshold, and shadow-model proof.")}
    <main class="shell single">
      <section class="main">
        {_ml_report_panel(report, report_path)}
        {_mlops_report_panel(mlops, mlops_path)}
      </section>
    </main>
  </body>
</html>"""


@app.get("/dashboard/signals", response_class=HTMLResponse)
def signal_lab_dashboard(
    camera_make: str | None = "Canon",
    camera_model: str | None = "",
    software_tag: str | None = "OBS Virtual Camera",
    business_name: str = "Bryan Lab Holdings",
    jurisdiction: str = "US",
    registry_status: str = "active",
    lei_status: str = "missing",
    sanctions_hit: bool = False,
    company_age_days: int = Query(default=14, ge=0, le=50000),
) -> str:
    camera = LocalCameraMetadataAnalyzer().inspect(
        camera_make=camera_make,
        camera_model=camera_model,
        software_tag=software_tag,
    )
    kyb = LocalPublicKybConnector().lookup(
        business_name=business_name,
        jurisdiction=jurisdiction,
        registry_status=registry_status,
        lei_status=lei_status,
        sanctions_hit=sanctions_hit,
        company_age_days=company_age_days,
    )
    checked = "checked" if sanctions_hit else ""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 signal lab</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("Signal Lab", "Local metadata and public-KYB style checks. No external calls.")}
    <main class="shell single">
      <section class="main">
        <div class="split">
          <section class="panel">
            <h2>Camera metadata</h2>
            <form method="get" action="/dashboard/signals" class="custom-grid">
              <label>Camera make<input name="camera_make" value="{escape(camera_make or "")}"></label>
              <label>Camera model<input name="camera_model" value="{escape(camera_model or "")}"></label>
              <label>Software tag<input name="software_tag" value="{escape(software_tag or "")}"></label>
              <label>Business<input name="business_name" value="{escape(business_name)}"></label>
              <label>Jurisdiction<input name="jurisdiction" value="{escape(jurisdiction)}"></label>
              <label>Registry status<input name="registry_status" value="{escape(registry_status)}"></label>
              <label>LEI status<input name="lei_status" value="{escape(lei_status)}"></label>
              <label>Company age days<input name="company_age_days" type="number" min="0" value="{company_age_days}"></label>
              <label>Sanctions hit<input name="sanctions_hit" type="checkbox" value="true" {checked}></label>
              <button class="button" type="submit">Run local checks</button>
            </form>
          </section>
          <section class="panel">
            <h2>Results</h2>
            {_connector_result_panel("Camera", camera)}
            {_connector_result_panel("Public KYB", kyb)}
            <p>These checks are weak signals. They can route to review; they cannot prove identity, liveness, sanctions status, or fraud by themselves.</p>
          </section>
        </div>
      </section>
    </main>
  </body>
</html>"""


@app.get("/dashboard/simulate", response_class=HTMLResponse)
def simulation_dashboard(
    amount: float = Query(default=750.0, ge=0),
    virtual_camera: bool = False,
    low_behavior_entropy: bool = False,
    high_application_velocity: bool = False,
    payment_velocity: bool = False,
    prior_chargeback: bool = False,
    one_hop_from_fraud: bool = False,
    public_kyb_watch: bool = False,
    sanctions_hit: bool = False,
    app_bec_pattern: bool = False,
    model_or_graph_outage: bool = False,
    settings: Settings = Depends(get_settings),
) -> str:
    request = SimulationRequest(
        amount=amount,
        virtual_camera=virtual_camera,
        low_behavior_entropy=low_behavior_entropy,
        high_application_velocity=high_application_velocity,
        payment_velocity=payment_velocity,
        prior_chargeback=prior_chargeback,
        one_hop_from_fraud=one_hop_from_fraud,
        public_kyb_watch=public_kyb_watch,
        sanctions_hit=sanctions_hit,
        app_bec_pattern=app_bec_pattern,
        model_or_graph_outage=model_or_graph_outage,
    )
    result = run_simulation(request, policy=load_threshold_policy(settings.policy_path))
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 simulation workbench</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("Simulation Workbench", "Manual local knobs for presenting risk movement without touching real systems.")}
    <main class="shell">
      <section class="main">
        <div class="panel">
          <div class="panel-head">
            <div>
              <h2>Build one local scenario</h2>
              <p>Every knob is synthetic. No real KYC, PII, liveness, sanctions, payment, customer message, or filing.</p>
            </div>
            <span class="badge neutral">No real action</span>
          </div>
          <form method="get" action="/dashboard/simulate">
            <div class="custom-grid">
              <label>Amount<input name="amount" value="{escape(_fmt(request.amount))}" type="number" min="0" step="50"></label>
            </div>
            <div class="scenario-grid">
              {_simulation_checkbox("virtual_camera", "Virtual camera", request.virtual_camera, "Camera metadata is missing or virtual-driver shaped.")}
              {_simulation_checkbox("low_behavior_entropy", "Low behavior entropy", request.low_behavior_entropy, "Session rhythm is too uniform for normal human behavior.")}
              {_simulation_checkbox("high_application_velocity", "Application velocity", request.high_application_velocity, "Same device submits many applications quickly.")}
              {_simulation_checkbox("payment_velocity", "Payment velocity", request.payment_velocity, "Multiple payment attempts arrive in a short window.")}
              {_simulation_checkbox("prior_chargeback", "Prior chargeback", request.prior_chargeback, "Prior dispute/default signal exists.")}
              {_simulation_checkbox("one_hop_from_fraud", "One hop from fraud", request.one_hop_from_fraud, "Graph evidence links the applicant to confirmed fraud.")}
              {_simulation_checkbox("public_kyb_watch", "Public KYB watch", request.public_kyb_watch, "Business registry-style signal needs review.")}
              {_simulation_checkbox("sanctions_hit", "Sanctions-style hit", request.sanctions_hit, "Local sanctions-shaped flag exists.")}
              {_simulation_checkbox("app_bec_pattern", "APP/BEC pattern", request.app_bec_pattern, "Payment instruction pattern deserves Break-the-Spell friction.")}
              {_simulation_checkbox("model_or_graph_outage", "Model/graph outage", request.model_or_graph_outage, "Dependency degraded; policy forces review.")}
            </div>
            <p><button class="button" type="submit">Simulate result</button></p>
          </form>
        </div>
        {_simulation_result_panel(result)}
      </section>
      <aside class="rail">
        {_action_ladder()}
        {_simulation_boundary_panel()}
      </aside>
    </main>
  </body>
</html>"""


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(db: FraudStore = Depends(store)) -> str:
    _ensure_demo_seed(db)
    events = db.list_events()
    decisions = db.list_decisions()
    cases = db.list_review_cases()
    coverage = _synthetic_coverage(events)
    red = sum(1 for decision in decisions if decision.risk_tier.value == "RED")
    yellow = sum(1 for decision in decisions if decision.risk_tier.value == "YELLOW")
    green = sum(1 for decision in decisions if decision.risk_tier.value == "GREEN")
    recent_decisions = _decision_table(decisions[-12:])
    review_queue = _review_table([case for case in cases if case.status == "open"][:12])
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 analyst dashboard</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("Analyst Dashboard", "Queue, decisions, and the local synthetic dataset in one work surface.")}
    <main class="shell">
      <section class="main">
        <div class="hero-row">
          {_plain_tile("Events", len(events), "Canonical synthetic/local events")}
          {_plain_tile("Green", green, "Approve lane")}
          {_plain_tile("Yellow", yellow, "Manual review/friction lane")}
          {_plain_tile("Red", red, "Simulated block/hold lane")}
        </div>
        <div class="split">
          <section class="panel">
            <h2>Recent decisions</h2>
            {recent_decisions}
          </section>
          <section class="panel">
            <h2>Open review queue</h2>
            {review_queue}
          </section>
        </div>
        {_synthetic_coverage_panel(coverage)}
      </section>
      <aside class="rail">
        {_action_ladder()}
        {_coverage_map()}
      </aside>
    </main>
  </body>
</html>"""


def _base_style() -> str:
    return """<style>
      :root { --ink:#102033; --muted:#64748b; --line:#d8e0ea; --soft:#f6f8fb; --navy:#0f2238; --orange:#ff5a1f; --red:#c62828; --green:#137a3a; --yellow:#a16207; --blue:#2563eb; }
      * { box-sizing: border-box; }
      html, body { width:100%; max-width:100%; overflow-x:hidden; }
      body { font-family: Aptos, Segoe UI, Tahoma, sans-serif; margin: 0; color: var(--ink); background: #edf1f5; font-size: 14px; }
      a { color: #0b5cad; text-decoration: none; }
      a:hover { text-decoration: underline; }
      .top { background: #fff; border-bottom: 1px solid var(--line); padding: 16px 20px; }
      .brand { display: flex; gap: 12px; align-items: center; }
      .brand > div:last-child { min-width:0; }
      .mark { width: 38px; height: 38px; border-radius: 5px; background: var(--navy); color: #fff; display: grid; place-items: center; font-weight: 800; }
      h1 { font-size: 18px; margin: 0 0 3px; letter-spacing: 0; overflow-wrap:anywhere; }
      h2 { font-size: 16px; margin: 0 0 6px; letter-spacing: 0; overflow-wrap:anywhere; }
      h3 { font-size: 13px; margin: 16px 0 8px; color: #40546b; text-transform: uppercase; letter-spacing: .04em; overflow-wrap:anywhere; }
      p, a, strong, span { overflow-wrap:anywhere; }
      p { color: var(--muted); margin: 0 0 12px; }
      .navlinks { margin-top: 14px; display: flex; gap: 16px; flex-wrap: wrap; font-size: 13px; }
      .shell { display: grid; grid-template-columns: minmax(0,1fr); gap: 12px; padding: 12px; width:100%; max-width:100vw; overflow-x:hidden; }
      .shell.single { grid-template-columns: 1fr; }
      .main { display: grid; gap: 12px; align-content: start; min-width:0; }
      .rail { display: grid; gap: 12px; align-content: start; min-width:0; }
      .shell > *, .split > *, .hero-row > *, .scenario-grid > * { min-width:0; max-width:100%; }
      .panel, .tile { background: #fff; border: 1px solid var(--line); border-radius: 6px; padding: 14px; min-width: 0; max-width:100%; overflow-x: auto; }
      .panel-head { display:flex; justify-content:space-between; gap:12px; align-items:start; flex-wrap:wrap; border-bottom:1px solid var(--line); padding-bottom:12px; margin-bottom:12px; }
      .panel-head > * { min-width:0; }
      .scenario-grid { display:grid; grid-template-columns: repeat(auto-fit, minmax(230px,1fr)); gap:10px; }
      .scenario { background:#f8fafc; border:1px solid var(--line); border-radius:6px; padding:12px; display:grid; gap:8px; min-width:0; max-width:100%; }
      .scenario.active { border-color: var(--orange); background: #fff7ed; }
      .scenario strong { font-size: 14px; }
      .cockpit-hero { border-top:4px solid var(--orange); }
      .hero-row { display:grid; grid-template-columns: repeat(auto-fit, minmax(190px,1fr)); gap:10px; }
      .score-tile { background: var(--navy); color: #fff; }
      .score-tile p, .score-tile .label { color: #cbd5e1; }
      .label { color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .06em; }
      .value { font-size: 28px; font-weight: 800; margin-top: 4px; }
      .button { border:1px solid var(--orange); background:var(--orange); color:#111827; font-weight:700; border-radius:4px; padding:9px 12px; cursor:pointer; }
      .button.secondary { background:#fff; border-color:var(--line); color:var(--ink); }
      .button.danger { background:#fff4f2; color:var(--red); border-color:#f2b8b5; }
      .button.good { background:#ecfdf3; color:var(--green); border-color:#a7f3c0; }
      .badge { display:inline-block; border:1px solid var(--line); border-radius:5px; padding:4px 7px; font-size:12px; font-weight:700; max-width:100%; overflow-wrap:anywhere; }
      .badge.red { color:var(--red); background:#fff4f2; border-color:#f2b8b5; }
      .badge.yellow { color:var(--yellow); background:#fff8e7; border-color:#facc15; }
      .badge.green { color:var(--green); background:#ecfdf3; border-color:#a7f3c0; }
      .badge.neutral { color:#475569; background:#f8fafc; }
      .custom-grid { display:grid; grid-template-columns: repeat(auto-fit,minmax(170px,1fr)); gap:10px; margin: 8px 0 12px; }
      label { color:#40546b; font-size:12px; font-weight:700; display:grid; gap:5px; }
      input, select { border:1px solid var(--line); border-radius:4px; padding:8px; font:inherit; background:#fff; min-width:0; width:100%; max-width:100%; }
      table { width:100%; max-width:100%; table-layout:fixed; border-collapse:collapse; font-size:13px; }
      th, td { border-bottom:1px solid #e5eaf0; padding:8px; text-align:left; vertical-align:top; overflow-wrap:anywhere; }
      th { color:#52616b; background:#f6f8fa; font-size:11px; text-transform:uppercase; letter-spacing:.06em; }
      pre { white-space:pre-wrap; overflow-wrap:anywhere; }
      .split { display:grid; grid-template-columns: minmax(0,1fr); gap:12px; }
      .graph { border:1px solid var(--line); border-radius:6px; overflow:hidden; background:#fff; }
      .graph svg { display:block; width:100%; height:auto; min-height:260px; }
      .bar { width:100%; min-width:0; background:#edf2f7; border-radius:4px; overflow:hidden; height:10px; }
      .bar span { display:block; height:10px; background:var(--orange); }
      .bar.green span { background:var(--green); }
      .bar.yellow span { background:var(--yellow); }
      .bar.red span { background:var(--red); }
      .bar.blue span { background:var(--blue); }
      .recommended-row td { background:#fff7ed; font-weight:700; }
      .tier-RED { color: var(--red); font-weight: 800; }
      .tier-YELLOW { color: var(--yellow); font-weight: 800; }
      .tier-GREEN { color: var(--green); font-weight: 800; }
      ul.clean { margin: 8px 0 0; padding-left: 18px; }
      li { margin: 6px 0; }
      @media (min-width: 1100px) { .shell:not(.single) { grid-template-columns: minmax(0,1fr) minmax(260px,300px); } .split { grid-template-columns: minmax(0,1fr) minmax(0,1fr); } }
      @media (max-width: 520px) { .top { padding:14px 12px; } .shell { padding:8px; } .panel, .tile { padding:12px; } .hero-row, .scenario-grid, .custom-grid { grid-template-columns:1fr; } .navlinks { gap:10px; } .value { font-size:24px; overflow-wrap:anywhere; } }
    </style>"""


def _top_nav(title: str, subtitle: str) -> str:
    return f"""<header class="top">
      <div class="brand">
        <div class="mark">FV2</div>
        <div><h1>{escape(title)}</h1><p>{escape(subtitle)}</p></div>
      </div>
      <nav class="navlinks">
        <a href="/cockpit">Cockpit</a>
        <a href="/demo">Demo</a>
        <a href="/dashboard">Analyst dashboard</a>
        <a href="/dashboard/ops">Ops metrics</a>
        <a href="/dashboard/ml">ML dashboard</a>
        <a href="/dashboard/signals">Signal lab</a>
        <a href="/dashboard/simulate">Simulation</a>
        <a href="/dashboard/graph?entity_id=user_00000">Graph evidence</a>
        <a href="/docs">API docs</a>
        <a href="/metrics">Raw metrics</a>
      </nav>
    </header>"""


def _ensure_demo_seed(db: FraudStore) -> None:
    if db.list_events():
        return
    db.add_events(SyntheticFraudGenerator().generate(users=DEFAULT_SYNTHETIC_USERS).events)


def _scenario_by_key(key: str) -> DemoScenario:
    for scenario in DEMO_SCENARIOS:
        if scenario.key == key:
            return scenario
    raise HTTPException(status_code=404, detail=f"unknown demo scenario: {key}")


def _scenario_card(scenario: DemoScenario) -> str:
    return f"""<div class="scenario">
      <div><strong>{escape(scenario.title)}</strong><p>{escape(scenario.narrative)}</p></div>
      <div><span class="badge neutral">{escape(scenario.expected)}</span></div>
      <form method="post" action="/demo/run?scenario={escape(scenario.key)}">
        <button class="button" type="submit">Run scenario</button>
      </form>
    </div>"""


def _cockpit_scenario_tabs(selected_key: str) -> str:
    cards = []
    for scenario in cockpit_scenarios():
        active = " active" if scenario.key == selected_key else ""
        cards.append(
            f"""<a class="scenario{active}" href="/cockpit?scenario={escape(scenario.key)}">
              <strong>{escape(scenario.title)}</strong>
              <p>{escape(scenario.expected_operator_action)}</p>
              <span class="badge neutral">{escape(scenario.typology)}</span>
            </a>"""
        )
    return f"<div class='scenario-grid'>{''.join(cards)}</div>"


def _mode_comparison_table(modes: list[DecisionModeComparison]) -> str:
    rows = []
    for mode in modes:
        row_class = " class='recommended-row'" if mode.recommended else ""
        rows.append(
            f"<tr{row_class}>"
            f"<td>{escape(mode.label)}</td>"
            f"<td>{mode.score}</td>"
            f"<td><span class='badge {mode.tier.value.lower()}'>{mode.tier.value}</span></td>"
            f"<td>{escape(mode.action.value)}</td>"
            f"<td>{escape(_fmt(mode.expected_profit))}</td>"
            f"<td>{escape(mode.note)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Mode</th><th>Score</th><th>Tier</th><th>Action</th>"
        "<th>Expected profit</th><th>Why it matters</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _contribution_table(contributions: list[SignalContribution]) -> str:
    rows = []
    max_points = max((item.points for item in contributions), default=1)
    for item in contributions:
        width = 0 if max_points == 0 else round(item.points / max_points * 100)
        rows.append(
            "<tr>"
            f"<td>{escape(item.code)}</td>"
            f"<td>{item.points}</td>"
            f"<td><div class='bar'><span style='width:{width}%'></span></div></td>"
            f"<td>{escape(item.source)}</td>"
            f"<td>{escape(item.safe_reason)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Signal</th><th>Points</th><th>Weight</th><th>Source</th>"
        "<th>Safe reason</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _cockpit_timeline(scenario: CockpitScenario) -> str:
    rows = "".join(
        f"<tr><td>{index}</td><td>{escape(step)}</td></tr>"
        for index, step in enumerate(scenario.timeline, start=1)
    )
    return (
        f"<table><thead><tr><th>Step</th><th>Event</th></tr></thead><tbody>{rows}</tbody></table>"
    )


def _cockpit_decision_rail(
    scenario: CockpitScenario,
    decision: DecisionResponse,
    simulation: SimulationResponse,
) -> str:
    return f"""<section class="panel">
      <h2>Decision rail</h2>
      <table><tbody>
        <tr><td>Scenario</td><td>{escape(scenario.title)}</td></tr>
        <tr><td>Expected label</td><td>{escape(scenario.expected_label)}</td></tr>
        <tr><td>Rules score</td><td>{decision.risk_score}</td></tr>
        <tr><td>Simulation score</td><td>{simulation.score}</td></tr>
        <tr><td>Policy</td><td>{escape(decision.policy_version)}</td></tr>
        <tr><td>Model</td><td>{escape(decision.model_version or "n/a")}</td></tr>
        <tr><td>Trace</td><td>{escape(str(decision.reasoning_trace_id)[:8])}</td></tr>
      </tbody></table>
    </section>"""


def _cockpit_gap_panel(scenario: CockpitScenario) -> str:
    return f"""<section class="panel">
      <h2>Production blockers</h2>
      {_plain_list(scenario.production_blockers)}
      <h3>Decision</h3>
      <p>Implement local/simulated proof now. Pause real vendor, PII, money, messaging, and filing until access and approval exist.</p>
    </section>"""


def _model_benchmark_panel(report: dict[str, Any] | None) -> str:
    if report is None:
        return """<div class="panel">
          <h2>ML benchmark</h2>
          <p>No benchmark report found. Run this to compare local lightweight models:</p>
          <pre>uv run fraud-v2 model-benchmark --events-path data\\synthetic\\tiny\\events.jsonl --output-path data\\models\\benchmark-report.json</pre>
          <p>Use this as a model proof lane, not as a production claim.</p>
        </div>"""
    model_rows = list(report.get("models", []))
    best_profit = (
        max((_as_float(item.get("best_profit")) for item in model_rows), default=0.0) or 1.0
    )
    rows = "".join(_model_benchmark_row(item, best_profit) for item in model_rows)
    return f"""<div class="panel">
      <div class="panel-head">
        <div>
          <h2>ML benchmark</h2>
          <p>{escape(str(report.get("rows", 0)))} local synthetic rows. Recommended: {escape(str(report.get("recommended_model_family", "n/a")))}</p>
        </div>
        <span class="badge neutral">local sklearn</span>
      </div>
      <table><thead><tr><th>Model</th><th>AUPRC</th><th>Profit visual</th><th>Brier</th><th>Recall @ 1% FPR</th><th>Best profit</th></tr></thead><tbody>{rows}</tbody></table>
      <p>{escape(str(report.get("recommendation", "")))}</p>
    </div>"""


def _model_benchmark_row(item: Any, best_profit: float) -> str:
    row = item if isinstance(item, dict) else {}
    profit = _as_float(row.get("best_profit"))
    width = max(0, min(100, round(profit / best_profit * 100)))
    return (
        "<tr>"
        f"<td>{escape(str(row.get('model_family', '')))}</td>"
        f"<td>{escape(_fmt(row.get('average_precision')))}</td>"
        f"<td><div class='bar green'><span style='width:{width}%'></span></div></td>"
        f"<td>{escape(_fmt(row.get('brier_score')))}</td>"
        f"<td>{escape(_fmt(row.get('recall_at_1pct_fpr')))}</td>"
        f"<td>{escape(_fmt(row.get('best_profit')))}</td>"
        "</tr>"
    )


def _scenario_options() -> str:
    return "".join(
        f'<option value="{escape(scenario.key)}">{escape(scenario.title)}</option>'
        for scenario in DEMO_SCENARIOS
    )


def _demo_as_of(raw_value: str) -> datetime:
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _score_local_decision(
    *,
    db: FraudStore,
    settings: Settings,
    user_id: str,
    amount: float,
    as_of: datetime,
) -> DecisionResponse:
    policy = load_threshold_policy(settings.policy_path)
    request = DecisionRequest(
        target_entity=EntityRef(entity_type=EntityType.USER, entity_id=user_id),
        as_of=as_of,
        amount=amount,
        context={"surface": "demo"},
    )
    start = time.perf_counter()
    decision = DecisionEngine(db, policy=policy).score(request)
    ReviewService(db).ensure_case_for_decision(decision.decision_id)
    decision_counter.labels(tier=decision.risk_tier.value, action=decision.action.value).inc()
    decision_latency.observe(time.perf_counter() - start)
    return decision


def _selected_decision(
    decision_id: UUID | None, decisions: list[DecisionResponse]
) -> DecisionResponse | None:
    if decision_id is None:
        return decisions[-1] if decisions else None
    for decision in decisions:
        if decision.decision_id == decision_id:
            return decision
    return None


def _selected_decision_panel(decision: DecisionResponse | None) -> str:
    if decision is None:
        return '<div class="panel"><h2>No selected decision</h2><p>Run a scenario to see the result.</p></div>'
    return f"""<div class="panel">
      <div class="panel-head">
        <div>
          <h2>Latest result</h2>
          <p>{escape(str(decision.decision_id))}</p>
        </div>
        <a class="button secondary" href="/dashboard/graph?entity_id={escape(decision.target_entity.entity_id)}">Open graph</a>
      </div>
      <div class="hero-row">
        {_score_tile(decision)}
        {_status_tile("Tier", decision.risk_tier.value, decision.risk_tier.value.lower())}
        {_status_tile("Action", decision.action.value, _action_class(decision.action.value))}
        {_status_tile("Policy", decision.policy_version, "neutral")}
      </div>
      <h3>Reasons</h3>
      {_reason_list(decision.safe_reasons)}
    </div>"""


def _queue_summary(
    events: list[EventEnvelope],
    decisions: list[DecisionResponse],
    cases: list[ReviewCase],
) -> str:
    open_cases = [case for case in cases if case.status == "open"]
    return f"""<section class="panel">
      <h2>Queue summary</h2>
      <table><tbody>
        <tr><td>Events</td><td><strong>{len(events)}</strong></td></tr>
        <tr><td>Decisions</td><td><strong>{len(decisions)}</strong></td></tr>
        <tr><td>Open review cases</td><td><strong>{len(open_cases)}</strong></td></tr>
        <tr><td>Red decisions</td><td><strong>{sum(1 for decision in decisions if decision.risk_tier.value == "RED")}</strong></td></tr>
      </tbody></table>
    </section>"""


def _action_ladder() -> str:
    return """<section class="panel">
      <h2>Action ladder</h2>
      <table>
        <thead><tr><th>Score</th><th>Outcome</th><th>Meaning</th></tr></thead>
        <tbody>
          <tr><td>0-20</td><td><span class="badge green">Approve</span></td><td>No hold.</td></tr>
          <tr><td>21-79</td><td><span class="badge yellow">Review</span></td><td>Pause, verify, or inject friction.</td></tr>
          <tr><td>80+</td><td><span class="badge red">Block</span></td><td>Simulated block; human override visible.</td></tr>
        </tbody>
      </table>
    </section>"""


def _coverage_map() -> str:
    rows = [
        ("Gateway", "mock/public", "KYC/KYB/liveness are simulated or public-data only"),
        ("Streaming", "implemented", "Outbox, Redpanda profile, lag/DLQ tools"),
        ("Decision", "implemented", "Rules, graph features, safe reasons"),
        ("Ops", "implemented", "Review queue, drafts, audit, metrics"),
        ("MLOps", "implemented", "Training/eval, PSI drift, and simulated Kappa reports"),
    ]
    return (
        '<section class="panel"><h2>Blog layer coverage</h2><table><tbody>'
        + "".join(
            f"<tr><td>{escape(layer)}</td><td><span class='badge neutral'>{escape(status)}</span></td><td>{escape(note)}</td></tr>"
            for layer, status, note in rows
        )
        + "</tbody></table></section>"
    )


def _synthetic_coverage(events: list[EventEnvelope]) -> SyntheticCoverageSummary:
    users = {
        ref.entity_id
        for event in events
        for ref in event.entity_refs
        if ref.entity_type == EntityType.USER
    }
    event_types = Counter(event.event_type.value for event in events)
    typologies: Counter[str] = Counter()
    device_counts: Counter[str] = Counter()
    payment_attempts_by_user: Counter[str] = Counter()
    failed_logins_by_user: Counter[str] = Counter()
    chargebacks_by_user: Counter[str] = Counter()
    fraud_label_users: set[str] = set()
    virtual_camera_users: set[str] = set()
    virtual_camera_events = 0
    failed_logins = 0
    for event in events:
        payload = event.payload
        if isinstance(payload, LabelCreated) and payload.label_value == LabelValue.FRAUD:
            typologies[payload.typology.value] += 1
            fraud_label_users.add(payload.target_entity.entity_id)
        if isinstance(payload, DeviceObserved):
            device_counts[payload.device_id] += 1
        if isinstance(payload, PaymentAttempted):
            payment_attempts_by_user[payload.user_id] += 1
        if isinstance(payload, CameraMetadataObserved) and payload.software_tag:
            virtual_camera_events += 1
            virtual_camera_users.add(payload.user_id)
        if isinstance(payload, LoginAttempt) and not payload.success:
            failed_logins_by_user[payload.user_id] += 1
            failed_logins += 1
        if isinstance(payload, ChargebackReceived):
            chargebacks_by_user[payload.user_id] += 1
    shared_devices = tuple(
        (device_id, count) for device_id, count in device_counts.most_common(8) if count > 1
    )
    payment_burst_users = sum(1 for count in payment_attempts_by_user.values() if count >= 3)
    benign_burst_users = {
        user_id
        for user_id, count in payment_attempts_by_user.items()
        if count >= 3 and user_id not in fraud_label_users
    }
    false_positive_pressure = (
        (
            "Benign corporate virtual-camera users",
            len(virtual_camera_users - fraud_label_users),
        ),
        (
            "Benign account-recovery users",
            len(set(failed_logins_by_user) - fraud_label_users),
        ),
        ("Benign payment-burst users", len(benign_burst_users)),
        (
            "Legitimate dispute/chargeback users",
            len(set(chargebacks_by_user) - fraud_label_users),
        ),
    )
    return SyntheticCoverageSummary(
        events=len(events),
        users=len(users),
        fraud_labels=sum(typologies.values()),
        typologies=tuple(typologies.most_common()),
        event_types=tuple(event_types.most_common()),
        shared_devices=shared_devices,
        payment_burst_users=payment_burst_users,
        virtual_camera_events=virtual_camera_events,
        failed_logins=failed_logins,
        false_positive_pressure=false_positive_pressure,
    )


def _synthetic_coverage_panel(summary: SyntheticCoverageSummary, *, compact: bool = False) -> str:
    edge_rows = (
        ("Payment-burst users", summary.payment_burst_users, "Card testing, APP/BEC, bust-out"),
        (
            "Virtual camera events",
            summary.virtual_camera_events,
            "Deepfake/liveness-shaped metadata",
        ),
        ("ATO failed logins", summary.failed_logins, "Account-takeover password bursts"),
        (
            "Shared devices",
            len(summary.shared_devices),
            "Fraud rings plus benign household sharing",
        ),
    )
    event_distribution = (
        ""
        if compact
        else f"<h3>Event mix</h3>{_distribution_table(summary.event_types, 'Event type')}"
    )
    return f"""<section class="panel">
      <div class="panel-head">
        <div>
          <h2>Synthetic dataset coverage</h2>
          <p>Deterministic local data with fraud rings, benign false-positive pressure, payment bursts, delayed labels, and no real PII.</p>
        </div>
        <span class="badge neutral">{DEFAULT_SYNTHETIC_USERS} seeded users</span>
      </div>
      <div class="hero-row">
        {_plain_tile("Users", summary.users, "Synthetic applicants")}
        {_plain_tile("Events", summary.events, "Canonical event envelopes")}
        {_plain_tile("Fraud labels", summary.fraud_labels, "Delayed ground truth")}
        {_plain_tile("Burst users", summary.payment_burst_users, "3+ payment attempts")}
      </div>
      <h3>Fraud typologies</h3>
      {_distribution_table(summary.typologies, "Typology")}
      <h3>Edge-case proof</h3>
      {_edge_case_table(edge_rows)}
      <h3>False-positive pressure</h3>
      {_false_positive_pressure_table(summary.false_positive_pressure)}
      {_shared_device_table(summary.shared_devices)}
      {event_distribution}
    </section>"""


def _distribution_table(rows: tuple[tuple[str, int], ...], label: str) -> str:
    if not rows:
        return "<p>No distribution data yet.</p>"
    max_value = max(count for _, count in rows) or 1
    table_rows = "".join(
        "<tr>"
        f"<td>{escape(name)}</td>"
        f"<td>{count}</td>"
        f"<td><div class='bar blue'><span style='width:{round(count / max_value * 100)}%'></span></div></td>"
        "</tr>"
        for name, count in rows
    )
    return (
        f"<table><thead><tr><th>{escape(label)}</th><th>Count</th><th>Visual</th></tr></thead>"
        f"<tbody>{table_rows}</tbody></table>"
    )


def _edge_case_table(rows: tuple[tuple[str, int, str], ...]) -> str:
    return (
        "<table><thead><tr><th>Edge case</th><th>Count</th><th>Why it exists</th></tr></thead>"
        "<tbody>"
        + "".join(
            f"<tr><td>{escape(label)}</td><td>{count}</td><td>{escape(note)}</td></tr>"
            for label, count, note in rows
        )
        + "</tbody></table>"
    )


def _false_positive_pressure_table(rows: tuple[tuple[str, int], ...]) -> str:
    return _edge_case_table(
        tuple((label, count, "Legitimate-looking counterexample") for label, count in rows)
    )


def _shared_device_table(shared_devices: tuple[tuple[str, int], ...]) -> str:
    if not shared_devices:
        return ""
    rows = "".join(
        f"<tr><td>{escape(device_id)}</td><td>{count}</td></tr>"
        for device_id, count in shared_devices
    )
    return (
        "<h3>Shared device pressure</h3>"
        "<table><thead><tr><th>Device</th><th>Observed users/events</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _score_tile(decision: DecisionResponse) -> str:
    return (
        '<div class="tile score-tile">'
        '<div class="label">Score</div>'
        f'<div class="value">{decision.risk_score}</div>'
        f"<p>{escape(decision.target_entity.entity_id)}</p>"
        "</div>"
    )


def _status_tile(label: str, value: str, css_class: str) -> str:
    badge_class = css_class if css_class in {"red", "yellow", "green", "neutral"} else "neutral"
    return (
        '<div class="tile">'
        f'<div class="label">{escape(label)}</div>'
        f'<p><span class="badge {badge_class}">{escape(value)}</span></p>'
        "</div>"
    )


def _simulation_checkbox(name: str, label: str, checked: bool, note: str) -> str:
    checked_attr = " checked" if checked else ""
    return f"""<label class="scenario">
      <span><input name="{escape(name)}" value="true" type="checkbox"{checked_attr}> {escape(label)}</span>
      <p>{escape(note)}</p>
    </label>"""


def _simulation_result_panel(result: SimulationResponse) -> str:
    return f"""<div class="panel">
      <div class="panel-head">
        <div>
          <h2>Simulation result</h2>
          <p>Policy {escape(result.policy_version)}. Local-only score, no real action.</p>
        </div>
        <span class="badge neutral">No real action</span>
      </div>
      <div class="hero-row">
        {_plain_tile("Score", result.score, "0-100 local simulator score")}
        {_status_tile("Tier", result.tier.value, result.tier.value.lower())}
        {_status_tile("Action", result.action.value, _action_class(result.action.value))}
        {_status_tile("Mode", "DEGRADED" if result.degraded else "NORMAL", "yellow" if result.degraded else "green")}
      </div>
      <h3>Reasons</h3>
      {_reason_list(result.safe_reasons)}
      <h3>Signals</h3>
      {_risk_signal_table(result.signals)}
    </div>"""


def _simulation_boundary_panel() -> str:
    return """<section class="panel">
      <h2>Boundary</h2>
      <table><tbody>
        <tr><td>Data</td><td>Synthetic/local only</td></tr>
        <tr><td>Vendors</td><td>No external calls</td></tr>
        <tr><td>Actions</td><td>No customer message, no hold, no filing</td></tr>
        <tr><td>Purpose</td><td>Presentation, policy tuning, edge-case rehearsal</td></tr>
      </tbody></table>
    </section>"""


def _risk_signal_table(signals: list[RiskSignal]) -> str:
    if not signals:
        return "<p>No risk signals selected.</p>"
    rows = "".join(
        "<tr>"
        f"<td>{escape(signal.code)}</td>"
        f"<td>{signal.severity}</td>"
        f"<td>{escape(signal.source)}</td>"
        f"<td>{escape(signal.safe_reason)}</td>"
        "</tr>"
        for signal in signals
    )
    return (
        "<table><thead><tr><th>Code</th><th>Severity</th><th>Source</th><th>Safe Reason</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _plain_tile(label: str, value: object, note: str) -> str:
    return (
        '<div class="tile">'
        f'<div class="label">{escape(label)}</div>'
        f'<div class="value">{escape(str(value))}</div>'
        f"<p>{escape(note)}</p>"
        "</div>"
    )


def _action_class(value: str) -> str:
    if value in {"BLOCK", "HOLD_FUNDS", "SAR_DRAFT"}:
        return "red"
    if value in {"MANUAL_REVIEW", "STEP_UP_AUTH", "BREAK_THE_SPELL"}:
        return "yellow"
    if value == "APPROVE":
        return "green"
    return "neutral"


def _reason_list(reasons: list[str]) -> str:
    return (
        "<ul class='clean'>" + "".join(f"<li>{escape(reason)}</li>" for reason in reasons) + "</ul>"
    )


def _plain_list(items: tuple[str, ...] | list[str]) -> str:
    return "<ul class='clean'>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def _feature_table(decision: DecisionResponse) -> str:
    rows = []
    for name, value in decision.feature_vector.values.items():
        freshness = decision.feature_vector.freshness.get(name)
        rows.append(
            "<tr>"
            f"<td>{escape(name)}</td>"
            f"<td>{escape(str(value))}</td>"
            f"<td>{escape(freshness.value if freshness else 'n/a')}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Feature</th><th>Value</th><th>Freshness</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _case_by_id(cases: list[ReviewCase], case_id: UUID) -> ReviewCase | None:
    for case in cases:
        if case.case_id == case_id:
            return case
    return None


def _event_timeline_table(events: list[EventEnvelope], user_id: str) -> str:
    rows = []
    user_events = [event for event in events if _has_user_ref(event, user_id)][-14:]
    for event in user_events:
        rows.append(
            "<tr>"
            f"<td>{escape(event.occurred_at.strftime('%m-%d %H:%M'))}</td>"
            f"<td>{escape(event.event_type.value)}</td>"
            f"<td>{escape(_timeline_result(event))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p>No user timeline events found.</p>"
    return (
        "<table><thead><tr><th>Time</th><th>Event</th><th>Result</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _has_user_ref(event: EventEnvelope, user_id: str) -> bool:
    return any(
        ref.entity_type == EntityType.USER and ref.entity_id == user_id for ref in event.entity_refs
    )


def _timeline_result(event: EventEnvelope) -> str:
    if event.event_type == EventType.LABEL_CREATED:
        return "label became available"
    if event.event_type == EventType.CHARGEBACK_RECEIVED:
        return "dispute/chargeback"
    if event.event_type == EventType.PAYMENT_ATTEMPTED:
        return "payment attempted"
    if event.event_type == EventType.PAYMENT_SETTLED:
        return "payment settled"
    if event.event_type == EventType.CAMERA_METADATA_OBSERVED:
        return "metadata observed"
    if event.event_type == EventType.BEHAVIORAL_SIGNAL_OBSERVED:
        return "session signal observed"
    return "completed"


def _decision_rail(case: ReviewCase, decision: DecisionResponse) -> str:
    action_class = _action_class(decision.action.value)
    review_buttons = ""
    if case.status == "open":
        review_buttons = f"""<form method="post" action="/demo/review/{case.case_id}?outcome=CONFIRMED_FRAUD">
            <button class="button danger" type="submit">Mark fraud</button>
          </form>
          <form method="post" action="/demo/review/{case.case_id}?outcome=CONFIRMED_LEGITIMATE">
            <button class="button good" type="submit">Mark legitimate</button>
          </form>
          <form method="post" action="/demo/review/{case.case_id}?outcome=ESCALATED">
            <button class="button secondary" type="submit">Escalate</button>
          </form>"""
    intervention = (
        _break_spell_panel(decision)
        if decision.risk_tier.value == "YELLOW" or decision.action.value == "BREAK_THE_SPELL"
        else ""
    )
    return f"""<section class="panel">
      <h2>Decision rail</h2>
      <div class="tile score-tile">
        <div class="label">Recommended action</div>
        <h2>{escape(decision.action.value)}</h2>
        <p>{decision.risk_score}% risk score. Simulated local action only.</p>
      </div>
      <p><span class="badge {action_class}">{escape(decision.risk_tier.value)}</span></p>
      {review_buttons}
      <p>Compliance exports stay draft-only. No real SAR, account freeze, payout hold, or customer message is sent.</p>
      {intervention}
    </section>"""


def _break_spell_panel(decision: DecisionResponse) -> str:
    draft = build_break_spell_draft(decision)
    return f"""<div class="tile">
      <div class="label">{escape(draft.title)}</div>
      <p>{escape(draft.message)}</p>
      <h3>Customer confirmation checklist</h3>
      <ul class="clean">{"".join(f"<li>{escape(item)}</li>" for item in draft.checklist)}</ul>
      <h3>Why shown</h3>
      <ul class="clean">{"".join(f"<li>{escape(reason)}</li>" for reason in draft.risk_reasons)}</ul>
      <p><span class="badge neutral">demo only</span> No real message sent.</p>
    </div>"""


def _ops_row(name: str, state: str, detail: str) -> str:
    css_class = (
        "green"
        if state == "healthy"
        else "yellow"
        if state in {"watch", "available", "optional"}
        else "red"
    )
    return (
        "<tr>"
        f"<td>{escape(name)}</td>"
        f"<td><span class='badge {css_class}'>{escape(state)}</span></td>"
        f"<td>{detail}</td>"
        "</tr>"
    )


def _stale_feature_count(decisions: list[DecisionResponse]) -> int:
    stale = {
        FeatureFreshnessStatus.STALE,
        FeatureFreshnessStatus.MISSING,
        FeatureFreshnessStatus.DEGRADED,
    }
    return sum(
        1
        for decision in decisions[-20:]
        for status in decision.feature_vector.freshness.values()
        if status in stale
    )


def _tier_mix_table(decisions: list[DecisionResponse]) -> str:
    tiers = ["GREEN", "YELLOW", "RED"]
    counts = {
        tier: sum(1 for decision in decisions if decision.risk_tier.value == tier) for tier in tiers
    }
    max_count = max(counts.values(), default=0) or 1
    rows = []
    for tier in tiers:
        count = counts[tier]
        rows.append(
            f"<tr><td><span class='badge {tier.lower()}'>{tier}</span></td><td>{count}</td>"
            f"<td><div class='bar {tier.lower()}'><span style='width:{round(count / max_count * 100)}%'></span></div></td></tr>"
        )
    return (
        "<table><thead><tr><th>Tier</th><th>Count</th><th>Mix</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _load_model_report(report_path: Path) -> dict[str, Any] | None:
    if not report_path.exists():
        return None
    return json.loads(report_path.read_text(encoding="utf-8"))


def _ml_report_panel(report: dict[str, Any] | None, report_path: Path) -> str:
    if report is None:
        return f"""<div class="panel">
          <h2>No model report found</h2>
          <p>Run this first:</p>
          <pre>uv run fraud-v2 train --events-path data\\synthetic\\tiny\\events.jsonl --output-dir data\\models\\baseline</pre>
          <p>Then refresh this page. Expected report path: {escape(str(report_path))}</p>
        </div>"""
    candidates = report.get("threshold_candidates", [])[:12]
    feature_importances = report.get("feature_importances", [])[:12]
    return f"""<div class="panel">
      <div class="panel-head">
        <div><h2>{escape(str(report.get("model_version", "model")))}</h2><p>{escape(str(report.get("model_family", "unknown")))}</p></div>
        <span class="badge neutral">{escape(str(report.get("rows", 0)))} rows</span>
      </div>
      <div class="hero-row">
        {_plain_tile("Average precision", _fmt(report.get("average_precision")), "Rare-fraud ranking quality")}
        {_plain_tile("Brier score", _fmt(report.get("brier_score")), "Calibration error; lower is better")}
        {_plain_tile("Recall @ 1% FPR threshold", _threshold_label(report.get("recall_under_1pct_fpr_threshold")), "Strict false-positive operating point")}
        {_plain_tile("Profit threshold", _threshold_label(report.get("cost_weighted_threshold")), "Custom financial reward winner")}
      </div>
      <h3>Feature columns</h3>
      <p>{", ".join(f"<code>{escape(str(feature))}</code>" for feature in report.get("features", []))}</p>
      <h3>Feature importance</h3>
      {_feature_importance_table(feature_importances)}
      <h3>Threshold candidates</h3>
      <table><thead><tr><th>Threshold</th><th>TP</th><th>FP</th><th>FN</th><th>Profit</th></tr></thead><tbody>
        {"".join(_threshold_candidate_row(candidate) for candidate in candidates)}
      </tbody></table>
    </div>"""


def _mlops_report_panel(report: dict[str, Any] | None, report_path: Path) -> str:
    if report is None:
        return f"""<div class="panel">
          <h2>MLOps drift and analyst consistency</h2>
          <p>Run this first:</p>
          <pre>uv run fraud-v2 mlops-report --events-path data\\synthetic\\tiny\\events.jsonl --output-path data\\local\\mlops-report.json --simulate-score-shift-points 12</pre>
          <p>Then refresh this page. Expected report path: {escape(str(report_path))}</p>
        </div>"""
    score_drift = _dict_value(report.get("score_drift"))
    consistency = _dict_value(report.get("analyst_consistency"))
    confusion = _dict_value(report.get("confusion_at_red"))
    return f"""<div class="panel">
      <div class="panel-head">
        <div><h2>MLOps drift and analyst consistency</h2><p>{escape(str(report.get("rows", 0)))} scored synthetic users</p></div>
        <span class="badge neutral">local simulation</span>
      </div>
      <div class="hero-row">
        {_plain_tile("Score PSI", _fmt(score_drift.get("psi")), f"Status: {score_drift.get('status', 'n/a')}")}
        {_plain_tile("Analyst Kappa", _fmt(consistency.get("cohens_kappa")), f"Status: {consistency.get('status', 'n/a')}")}
        {_plain_tile("True positives", str(confusion.get("tp", "n/a")), "Red threshold proxy")}
        {_plain_tile("False positives", str(confusion.get("fp", "n/a")), "Red threshold proxy")}
      </div>
      <div class="split">
        <section>
          <h3>Score drift bands</h3>
          {_mapping_table(_dict_value(score_drift.get("reference_distribution")), _dict_value(score_drift.get("current_distribution")))}
        </section>
        <section>
          <h3>Reviewer distributions</h3>
          {_mapping_table(_dict_value(consistency.get("reviewer_a_distribution")), _dict_value(consistency.get("reviewer_b_distribution")))}
        </section>
      </div>
      <p>{escape(str(consistency.get("note", "")))}</p>
    </div>"""


def _dict_value(raw_value: object) -> dict[str, Any]:
    return raw_value if isinstance(raw_value, dict) else {}


def _mapping_table(left: dict[str, Any], right: dict[str, Any]) -> str:
    keys = sorted(set(left) | set(right))
    rows = "".join(
        "<tr>"
        f"<td>{escape(key)}</td>"
        f"<td>{escape(str(left.get(key, 0)))}</td>"
        f"<td>{escape(str(right.get(key, 0)))}</td>"
        "</tr>"
        for key in keys
    )
    return (
        "<table><thead><tr><th>Bucket</th><th>Reference/A</th><th>Current/B</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _connector_result_panel(title: str, result: ConnectorResult) -> str:
    css_class = "green" if result.status == "OK" else "yellow"
    return f"""<div class="tile">
      <div class="label">{escape(title)}</div>
      <h2><span class="badge {css_class}">{escape(result.status)}</span></h2>
      <p>{escape(result.safe_reason)}</p>
      {_signal_table(result.signals)}
    </div>"""


def _signal_table(signals: dict[str, str | int | float | bool]) -> str:
    rows = "".join(
        f"<tr><td>{escape(key)}</td><td>{escape(str(value))}</td></tr>"
        for key, value in signals.items()
    )
    return f"<table><tbody>{rows}</tbody></table>"


def _threshold_label(raw_value: object) -> str:
    if not isinstance(raw_value, dict):
        return "n/a"
    return _fmt(raw_value.get("threshold"))


def _threshold_candidate_row(candidate: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{escape(_fmt(candidate.get('threshold')))}</td>"
        f"<td>{escape(str(candidate.get('tp', '')))}</td>"
        f"<td>{escape(str(candidate.get('fp', '')))}</td>"
        f"<td>{escape(str(candidate.get('fn', '')))}</td>"
        f"<td>{escape(_fmt(candidate.get('profit')))}</td>"
        "</tr>"
    )


def _feature_importance_table(feature_importances: list[dict[str, Any]]) -> str:
    if not feature_importances:
        return "<p>No feature importance values found in the model report.</p>"
    max_importance = (
        max((_as_float(item.get("importance")) for item in feature_importances), default=0.0) or 1.0
    )
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('feature', '')))}</td>"
        f"<td>{escape(_fmt(item.get('importance')))}</td>"
        f"<td><div class='bar blue'><span style='width:{round(_as_float(item.get('importance')) / max_importance * 100)}%'></span></div></td>"
        "</tr>"
        for item in feature_importances
    )
    return (
        "<table><thead><tr><th>Feature</th><th>Importance</th><th>Visual</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )


def _as_float(value: object) -> float:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _fmt(value: object) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, int | float):
        return f"{value:.4f}"
    return str(value)


def _decision_table(decisions: list[DecisionResponse]) -> str:
    if not decisions:
        return "<p>No decisions yet.</p>"
    rows = []
    for decision in reversed(decisions):
        rows.append(
            "<tr>"
            f"<td>{escape(str(decision.decision_id))}</td>"
            "<td>"
            f'<a href="/dashboard/graph?entity_id={escape(decision.target_entity.entity_id)}">'
            f"{escape(decision.target_entity.entity_id)}</a>"
            "</td>"
            f'<td class="tier-{decision.risk_tier.value}">{decision.risk_tier.value}</td>'
            f"<td>{decision.risk_score}</td>"
            f"<td>{decision.action.value}</td>"
            f"<td>{escape(', '.join(decision.safe_reasons[:2]))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Decision</th><th>User</th><th>Tier</th>"
        "<th>Score</th><th>Action</th><th>Reasons</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _entity_type_options(selected: EntityType) -> str:
    return "".join(
        f'<option value="{escape(entity_type.value)}"{" selected" if entity_type == selected else ""}>{escape(entity_type.value)}</option>'
        for entity_type in EntityType
    )


@app.get("/dashboard/graph", response_class=HTMLResponse)
def graph_dashboard(
    entity_id: str = "user_00000",
    entity_type: EntityType = EntityType.USER,
    depth: int = Query(default=2, ge=1, le=4),
    db: FraudStore = Depends(store),
) -> str:
    _ensure_demo_seed(db)
    target = EntityRef(entity_type=entity_type, entity_id=entity_id)
    events = db.list_events()
    graph = GraphService(events).neighborhood(target, depth=depth)
    svg = _graph_svg(graph, target.graph_key, _confirmed_fraud_graph_keys(events))
    relationships = _graph_relationship_table(graph["edges"])
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>fraud-v2 graph evidence</title>
    {_base_style()}
  </head>
  <body>
    {_top_nav("Graph evidence", "Local entity neighborhood with type lanes, fraud labels, and relationship proof.")}
    <main class="shell">
      <section class="main">
        <section class="panel">
          <div class="panel-head">
            <div>
              <h2>{escape(target.graph_key)}</h2>
              <p>Depth {depth}. Red nodes are confirmed synthetic fraud labels; bold orange edges touch target or confirmed fraud.</p>
            </div>
            <span class="badge neutral">{len(graph["nodes"])} nodes / {len(graph["edges"])} edges</span>
          </div>
          <form method="get" action="/dashboard/graph" class="custom-grid">
            <label>Entity<input name="entity_id" value="{escape(entity_id)}"></label>
            <label>Type<select name="entity_type">{_entity_type_options(entity_type)}</select></label>
            <label>Depth<input name="depth" value="{depth}" type="number" min="1" max="4"></label>
            <button class="button" type="submit">Render graph</button>
          </form>
          <div class="graph">{svg}</div>
        </section>
        <section class="panel">
          <h2>Relationships</h2>
          {relationships}
        </section>
      </section>
      <aside class="rail">
        {_graph_summary_panel(graph)}
        {_coverage_map()}
      </aside>
    </main>
  </body>
</html>"""


def _graph_summary_panel(graph: dict[str, list[dict[str, str]]]) -> str:
    node_types = Counter(node["label"] for node in graph["nodes"])
    edge_types = Counter(edge["relationship"] for edge in graph["edges"])
    return f"""<section class="panel">
      <h2>Graph mix</h2>
      <h3>Node types</h3>
      {_distribution_table(tuple(node_types.most_common()), "Node type")}
      <h3>Relationship types</h3>
      {_distribution_table(tuple(edge_types.most_common()), "Relationship")}
    </section>"""


def _graph_svg(
    graph: dict[str, list[dict[str, str]]],
    target_key: str,
    fraud_keys: set[str] | None = None,
) -> str:
    fraud_keys = fraud_keys or set()
    nodes = graph["nodes"][:18]
    if not nodes:
        return (
            '<svg viewBox="0 0 900 520" width="100%" height="520">'
            '<text x="32" y="48">No graph evidence found.</text></svg>'
        )

    width = 900
    height = 520
    ordered_nodes = sorted(nodes, key=lambda node: (node["id"] != target_key, node["id"]))
    positions = _graph_positions(ordered_nodes, target_key, width=width, height=height)

    visible = set(positions)
    edge_lines = []
    for edge in graph["edges"]:
        source = edge["source"]
        target = edge["target"]
        if source not in visible or target not in visible:
            continue
        x1, y1 = positions[source]
        x2, y2 = positions[target]
        highlighted = (
            source == target_key
            or target == target_key
            or source in fraud_keys
            or target in fraud_keys
        )
        stroke = "#ff5a1f" if highlighted else "#c3ccd6"
        width_value = "3.0" if highlighted else "1.2"
        opacity = "1.0" if highlighted else "0.55"
        edge_lines.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{stroke}" stroke-width="{width_value}" opacity="{opacity}" />'
        )

    node_shapes = []
    for node in ordered_nodes:
        node_id = node["id"]
        x, y = positions[node_id]
        color = "#dc2626" if node_id in fraud_keys else _graph_node_color(node["label"])
        stroke = "#111827" if node_id == target_key else "#ffffff"
        stroke_width = 4 if node_id == target_key else 2
        label = _short_node_label(node_id)
        icon = _graph_node_icon(node["label"])
        node_shapes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{color}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" />'
            f'<text x="{x:.1f}" y="{y + 5:.1f}" text-anchor="middle" '
            'font-size="13" font-weight="800" fill="#ffffff">'
            f"{escape(icon)}</text>"
            f'<text x="{x:.1f}" y="{y + 43:.1f}" text-anchor="middle" '
            'font-size="12" font-weight="650" fill="#17202a">'
            f"{escape(label)}</text>"
        )

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="520" role="img" '
        f'aria-label="Graph evidence for {escape(target_key)}">'
        '<rect width="900" height="520" fill="#ffffff" />'
        '<text x="24" y="32" font-size="13" font-weight="700" fill="#102033">Lane layout: network/device to the left, target center, transactions to the right, users below</text>'
        '<text x="150" y="70" font-size="11" font-weight="700" fill="#64748b">Network</text>'
        '<text x="292" y="70" font-size="11" font-weight="700" fill="#64748b">Device</text>'
        '<text x="428" y="70" font-size="11" font-weight="700" fill="#64748b">Applicant</text>'
        '<text x="626" y="70" font-size="11" font-weight="700" fill="#64748b">Payment</text>'
        '<rect x="24" y="448" width="852" height="48" rx="6" fill="#f8fafc" stroke="#d8e0ea" />'
        '<text x="42" y="478" font-size="12" fill="#102033">U=user  D=device  IP=network  $=bank account  T=transaction  A=application  red node=confirmed fraud</text>'
        + "".join(edge_lines)
        + "".join(node_shapes)
        + "</svg>"
    )


def _graph_positions(
    nodes: list[dict[str, str]],
    target_key: str,
    *,
    width: int,
    height: int,
) -> dict[str, tuple[float, float]]:
    target_node = next((node for node in nodes if node["id"] == target_key), nodes[0])
    positions: dict[str, tuple[float, float]] = {target_node["id"]: (width / 2, height / 2)}
    grouped: dict[str, list[dict[str, str]]] = {}
    for node in nodes:
        if node["id"] == target_node["id"]:
            continue
        grouped.setdefault(node["label"], []).append(node)
    vertical_lanes = {
        "IP_ADDRESS": (150.0, 100.0, 300.0),
        "DEVICE": (300.0, 100.0, 310.0),
        "TRANSACTION": (640.0, 105.0, 310.0),
        "BANK_ACCOUNT": (760.0, 140.0, 230.0),
    }
    for label, lane_nodes in grouped.items():
        lane_nodes = sorted(lane_nodes, key=lambda item: item["id"])
        if label == "USER":
            for index, node in enumerate(lane_nodes):
                x = 235.0 + (430.0 * (index + 1) / (len(lane_nodes) + 1))
                positions[node["id"]] = (x, 405.0)
            continue
        if label == "APPLICATION":
            for index, node in enumerate(lane_nodes):
                x = 395.0 + (110.0 * (index + 1) / (len(lane_nodes) + 1))
                positions[node["id"]] = (x, 110.0)
            continue
        x, y_start, y_span = vertical_lanes.get(label, (760.0, 150.0, 220.0))
        for index, node in enumerate(lane_nodes):
            y = y_start + (y_span * (index + 1) / (len(lane_nodes) + 1))
            positions[node["id"]] = (x, y)
    return positions


def _graph_relationship_table(edges: list[dict[str, str]]) -> str:
    if not edges:
        return "<p>No relationships found.</p>"
    rows = []
    for edge in edges[:40]:
        rows.append(
            "<tr>"
            f"<td>{escape(edge['source'])}</td>"
            f"<td>{escape(edge['relationship'])}</td>"
            f"<td>{escape(edge['target'])}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Source</th><th>Relationship</th><th>Target</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _graph_node_color(label: str) -> str:
    return {
        "USER": "#2563eb",
        "DEVICE": "#f59e0b",
        "IP_ADDRESS": "#10b981",
        "TRANSACTION": "#ef4444",
        "BANK_ACCOUNT": "#7c3aed",
        "APPLICATION": "#64748b",
    }.get(label, "#475569")


def _graph_node_icon(label: str) -> str:
    return {
        "USER": "U",
        "DEVICE": "D",
        "IP_ADDRESS": "IP",
        "TRANSACTION": "T",
        "BANK_ACCOUNT": "$",
        "APPLICATION": "A",
    }.get(label, "?")


def _confirmed_fraud_graph_keys(events: list[EventEnvelope]) -> set[str]:
    keys: set[str] = set()
    for event in events:
        payload = event.payload
        if (
            event.event_type == EventType.LABEL_CREATED
            and getattr(payload, "label_value", None) == "FRAUD"
        ):
            target = getattr(payload, "target_entity", None)
            graph_key = getattr(target, "graph_key", None)
            if isinstance(graph_key, str):
                keys.add(graph_key)
    return keys


def _short_node_label(node_id: str) -> str:
    if ":" not in node_id:
        return node_id[:24]
    entity_type, entity_id = node_id.split(":", 1)
    return f"{entity_type}:{entity_id[-12:]}"


def _review_table(cases: list[ReviewCase]) -> str:
    if not cases:
        return "<p>No open review cases.</p>"
    rows = []
    for case in cases:
        rows.append(
            "<tr>"
            f'<td><a href="/dashboard/cases/{case.case_id}">{escape(str(case.case_id))}</a></td>'
            f"<td>{escape(str(case.decision_id))}</td>"
            f"<td>{escape(case.target_entity_id)}</td>"
            f"<td>{case.priority}</td>"
            f"<td>{escape(case.status)}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>Case</th><th>Decision</th><th>User</th><th>Priority</th>"
        "<th>Status</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
def ready(db: FraudStore = Depends(store)) -> dict[str, str | int]:
    return {"status": "ready", "events": len(db.list_events())}


@app.get("/metrics")
def metrics() -> Response:
    return metrics_response()


@app.get("/v1/auth/whoami")
def whoami(
    principal: AuthPrincipal = Depends(
        require_roles(AuthRole.ADMIN, AuthRole.ANALYST, AuthRole.SYSTEM)
    ),
) -> dict[str, object]:
    return {
        "subject": principal.subject,
        "roles": sorted(role.value for role in principal.roles),
    }


@app.get(
    "/v1/audit/entries",
    response_model=list[AuditEntry],
    dependencies=[Depends(require_roles(AuthRole.ADMIN))],
)
def list_audit_entries(
    limit: int = Query(default=100, ge=1, le=1000),
    db: FraudStore = Depends(store),
) -> list[AuditEntry]:
    return db.list_audit_entries(limit=limit)


@app.get(
    "/v1/audit/verify",
    response_model=AuditVerificationReport,
    dependencies=[Depends(require_roles(AuthRole.ADMIN))],
)
def verify_audit_chain(db: FraudStore = Depends(store)) -> AuditVerificationReport:
    return db.verify_audit_chain()


@app.get(
    "/v1/retention/report",
    response_model=RetentionReport,
    dependencies=[Depends(require_roles(AuthRole.ADMIN))],
)
def retention_report(
    as_of: str | None = Query(default=None),
    event_days: int = Query(default=90, ge=1),
    decision_days: int = Query(default=365, ge=1),
    review_days: int = Query(default=365, ge=1),
    outbox_days: int = Query(default=30, ge=1),
    stream_dead_letter_days: int = Query(default=30, ge=1),
    audit_days: int = Query(default=3650, ge=1),
    db: FraudStore = Depends(store),
) -> RetentionReport:
    return db.retention_report(
        as_of=_parse_as_of(as_of),
        policy=_retention_policy(
            event_days=event_days,
            decision_days=decision_days,
            review_days=review_days,
            outbox_days=outbox_days,
            stream_dead_letter_days=stream_dead_letter_days,
            audit_days=audit_days,
        ),
    )


@app.post(
    "/v1/retention/prune",
    response_model=RetentionReport,
    dependencies=[Depends(require_roles(AuthRole.ADMIN))],
)
def prune_retention(
    execute: bool = Query(default=False),
    as_of: str | None = Query(default=None),
    event_days: int = Query(default=90, ge=1),
    decision_days: int = Query(default=365, ge=1),
    review_days: int = Query(default=365, ge=1),
    outbox_days: int = Query(default=30, ge=1),
    stream_dead_letter_days: int = Query(default=30, ge=1),
    audit_days: int = Query(default=3650, ge=1),
    db: FraudStore = Depends(store),
) -> RetentionReport:
    policy = _retention_policy(
        event_days=event_days,
        decision_days=decision_days,
        review_days=review_days,
        outbox_days=outbox_days,
        stream_dead_letter_days=stream_dead_letter_days,
        audit_days=audit_days,
    )
    if not execute:
        report = db.retention_report(as_of=_parse_as_of(as_of), policy=policy)
        return report.model_copy(
            update={
                "tables": [
                    table.model_copy(update={"action": "dry_run"}) for table in report.tables
                ]
            }
        )
    return db.prune_retention(as_of=_parse_as_of(as_of), policy=policy)


def _retention_policy(
    *,
    event_days: int,
    decision_days: int,
    review_days: int,
    outbox_days: int,
    stream_dead_letter_days: int,
    audit_days: int,
) -> RetentionPolicy:
    return RetentionPolicy(
        event_days=event_days,
        decision_days=decision_days,
        review_days=review_days,
        outbox_days=outbox_days,
        stream_dead_letter_days=stream_dead_letter_days,
        audit_days=audit_days,
    )


def _parse_as_of(raw_value: str | None) -> datetime | None:
    if raw_value is None:
        return None
    parsed = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


@app.post("/v1/events", dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.SYSTEM))])
def ingest_event(event: EventEnvelope, db: FraudStore = Depends(store)) -> EventEnvelope:
    try:
        stored = db.add_event(event)
    except DuplicatePayloadConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    event_counter.labels(event_type=stored.event_type.value).inc()
    return stored


@app.post(
    "/v1/synthetic/generate", dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.SYSTEM))]
)
def generate_synthetic(
    users: int = Query(default=DEFAULT_SYNTHETIC_USERS, ge=10, le=10000),
    output: Path | None = None,
    db: FraudStore = Depends(store),
) -> dict[str, int | str]:
    dataset = SyntheticFraudGenerator().generate(users=users)
    db.add_events(dataset.events)
    if output:
        dataset.write_jsonl(output)
    return {"events": len(dataset.events), "users": users}


@app.post(
    "/v1/decisions/score",
    response_model=DecisionResponse,
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.SYSTEM))],
)
def score_decision(
    request: DecisionRequest,
    db: FraudStore = Depends(store),
    settings: Settings = Depends(get_settings),
) -> DecisionResponse:
    start = time.perf_counter()
    policy = load_threshold_policy(settings.policy_path)
    decision = DecisionEngine(db, policy=policy).score(request)
    ReviewService(db).ensure_case_for_decision(decision.decision_id)
    decision_counter.labels(tier=decision.risk_tier.value, action=decision.action.value).inc()
    decision_latency.observe(time.perf_counter() - start)
    return decision


@app.get(
    "/v1/decisions/{decision_id}",
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST, AuthRole.SYSTEM))],
)
def get_decision(decision_id: UUID, db: FraudStore = Depends(store)) -> dict[str, object]:
    try:
        decision = db.get_decision(decision_id)
    except DecisionNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "decision": decision,
        "adverse_action_style_reasons": adverse_action_style_reasons(decision),
    }


@app.get(
    "/v1/decisions",
    response_model=list[DecisionResponse],
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST, AuthRole.SYSTEM))],
)
def list_decisions(db: FraudStore = Depends(store)) -> list[DecisionResponse]:
    return db.list_decisions()


@app.get(
    "/v1/graph/neighborhood",
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST))],
)
def graph_neighborhood(
    entity_id: str,
    entity_type: EntityType = EntityType.USER,
    depth: int = Query(default=2, ge=1, le=4),
    db: FraudStore = Depends(store),
) -> dict[str, list[dict[str, str]]]:
    return GraphService(db.list_events()).neighborhood(
        EntityRef(entity_type=entity_type, entity_id=entity_id), depth=depth
    )


@app.get(
    "/v1/stream/dead-letters",
    response_model=list[StreamDeadLetter],
    dependencies=[Depends(require_roles(AuthRole.ADMIN))],
)
def list_stream_dead_letters(
    limit: int = Query(default=100, ge=1, le=1000),
    db: FraudStore = Depends(store),
) -> list[StreamDeadLetter]:
    return db.list_stream_dead_letters(limit=limit)


@app.get(
    "/v1/review/cases",
    response_model=list[ReviewCase],
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST))],
)
def list_review_cases(db: FraudStore = Depends(store)) -> list[ReviewCase]:
    return ReviewService(db).list_cases()


@app.post(
    "/v1/review/cases/{case_id}/decision",
    response_model=ReviewDecision,
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST))],
)
def decide_review_case(
    case_id: UUID,
    request: ReviewDecisionRequest,
    db: FraudStore = Depends(store),
) -> ReviewDecision:
    return ReviewService(db).decide(case_id, request)
