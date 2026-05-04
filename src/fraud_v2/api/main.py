from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from html import escape
from logging import getLogger
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from fraud_v2 import __version__
from fraud_v2.compliance.reasons import adverse_action_style_reasons
from fraud_v2.config.settings import Settings, get_settings
from fraud_v2.decision.engine import DecisionEngine
from fraud_v2.domain.decisions import DecisionRequest, DecisionResponse
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.enums import EntityType
from fraud_v2.domain.errors import DecisionNotFound, DuplicatePayloadConflict
from fraud_v2.domain.events import EventEnvelope
from fraud_v2.domain.reviews import ReviewCase, ReviewDecision, ReviewDecisionRequest
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
from fraud_v2.review.service import ReviewService
from fraud_v2.security.auth import AuthPrincipal, AuthRole, require_roles
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator

configure_logging()
logger = getLogger("fraud_v2.api")
app = FastAPI(title="fraud-v2", version=__version__)


def store(settings: Settings = Depends(get_settings)) -> SQLiteStore:
    return SQLiteStore(settings.sqlite_path)


@app.middleware("http")
async def add_trace_and_request_metrics(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    trace_id = request.headers.get("X-Request-ID") or new_trace_id()
    token = set_trace_id(trace_id)
    start = time.perf_counter()
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


def _route_template(request: Request, fallback: str | None = None) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str):
        return path
    return fallback or request.url.path


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "fraud-v2",
        "docs": "/docs",
        "dashboard": "/dashboard",
        "health": "/health/ready",
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(db: SQLiteStore = Depends(store)) -> str:
    events = db.list_events()
    decisions = db.list_decisions()
    cases = db.list_review_cases()
    red = sum(1 for decision in decisions if decision.risk_tier.value == "RED")
    yellow = sum(1 for decision in decisions if decision.risk_tier.value == "YELLOW")
    green = sum(1 for decision in decisions if decision.risk_tier.value == "GREEN")
    event_card = _metric_card("Events", len(events))
    green_card = _metric_card("Green", green)
    yellow_card = _metric_card("Yellow", yellow)
    red_card = _metric_card("Red", red)
    recent_decisions = _decision_table(decisions[-12:])
    review_queue = _review_table([case for case in cases if case.status == "open"][:12])
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <title>fraud-v2 dashboard</title>
        <style>
          body {{ font-family: Segoe UI, Arial, sans-serif; margin: 28px; color: #17202a; }}
          h1 {{ font-size: 24px; margin: 0 0 18px; }}
          h2 {{ font-size: 16px; margin: 28px 0 10px; }}
          .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
          .metric {{ border: 1px solid #d7dde5; border-radius: 6px; padding: 14px; }}
          .label {{ color: #5d6d7e; font-size: 12px; text-transform: uppercase; }}
          .value {{ font-size: 28px; font-weight: 700; margin-top: 6px; }}
          table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
          th, td {{ border-bottom: 1px solid #e4e8ee; padding: 8px; text-align: left; }}
          th {{ color: #566573; font-weight: 600; background: #f8fafc; }}
          .tier-RED {{ color: #a61b1b; font-weight: 700; }}
          .tier-YELLOW {{ color: #8a5a00; font-weight: 700; }}
          .tier-GREEN {{ color: #17633a; font-weight: 700; }}
          a {{ color: #0b5cad; }}
          @media (max-width: 760px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        </style>
      </head>
      <body>
        <h1>fraud-v2 analyst dashboard</h1>
        <div class="grid">
          {event_card}
          {green_card}
          {yellow_card}
          {red_card}
        </div>
        <h2>Recent decisions</h2>
        {recent_decisions}
        <h2>Open review queue</h2>
        {review_queue}
        <p><a href="/docs">API docs</a> | <a href="/metrics">Metrics</a></p>
      </body>
    </html>
    """


def _metric_card(label: str, value: int) -> str:
    return (
        '<div class="metric">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        "</div>"
    )


def _decision_table(decisions: list[DecisionResponse]) -> str:
    if not decisions:
        return "<p>No decisions yet.</p>"
    rows = []
    for decision in reversed(decisions):
        rows.append(
            "<tr>"
            f"<td>{escape(str(decision.decision_id))}</td>"
            f"<td>{escape(decision.target_entity.entity_id)}</td>"
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


def _review_table(cases: list[ReviewCase]) -> str:
    if not cases:
        return "<p>No open review cases.</p>"
    rows = []
    for case in cases:
        rows.append(
            "<tr>"
            f"<td>{escape(str(case.case_id))}</td>"
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
def ready(db: SQLiteStore = Depends(store)) -> dict[str, str | int]:
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


@app.post("/v1/events", dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.SYSTEM))])
def ingest_event(event: EventEnvelope, db: SQLiteStore = Depends(store)) -> EventEnvelope:
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
    users: int = Query(default=120, ge=10, le=10000),
    output: Path | None = None,
    db: SQLiteStore = Depends(store),
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
def score_decision(request: DecisionRequest, db: SQLiteStore = Depends(store)) -> DecisionResponse:
    start = time.perf_counter()
    decision = DecisionEngine(db).score(request)
    ReviewService(db).ensure_case_for_decision(decision.decision_id)
    decision_counter.labels(tier=decision.risk_tier.value, action=decision.action.value).inc()
    decision_latency.observe(time.perf_counter() - start)
    return decision


@app.get(
    "/v1/decisions/{decision_id}",
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST, AuthRole.SYSTEM))],
)
def get_decision(decision_id: UUID, db: SQLiteStore = Depends(store)) -> dict[str, object]:
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
def list_decisions(db: SQLiteStore = Depends(store)) -> list[DecisionResponse]:
    return db.list_decisions()


@app.get(
    "/v1/graph/neighborhood",
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST))],
)
def graph_neighborhood(
    entity_id: str,
    entity_type: EntityType = EntityType.USER,
    depth: int = Query(default=2, ge=1, le=4),
    db: SQLiteStore = Depends(store),
) -> dict[str, list[dict[str, str]]]:
    return GraphService(db.list_events()).neighborhood(
        EntityRef(entity_type=entity_type, entity_id=entity_id), depth=depth
    )


@app.get(
    "/v1/review/cases",
    response_model=list[ReviewCase],
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST))],
)
def list_review_cases(db: SQLiteStore = Depends(store)) -> list[ReviewCase]:
    return ReviewService(db).list_cases()


@app.post(
    "/v1/review/cases/{case_id}/decision",
    response_model=ReviewDecision,
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.ANALYST))],
)
def decide_review_case(
    case_id: UUID,
    request: ReviewDecisionRequest,
    db: SQLiteStore = Depends(store),
) -> ReviewDecision:
    return ReviewService(db).decide(case_id, request)
