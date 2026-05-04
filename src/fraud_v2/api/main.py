from __future__ import annotations

import time
from pathlib import Path
from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException, Query
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
from fraud_v2.observability.metrics import (
    decision_counter,
    decision_latency,
    event_counter,
    metrics_response,
)
from fraud_v2.review.service import ReviewService
from fraud_v2.storage.sqlite_store import SQLiteStore
from fraud_v2.synthetic.generator import SyntheticFraudGenerator

app = FastAPI(title="fraud-v2", version=__version__)


def store(settings: Settings = Depends(get_settings)) -> SQLiteStore:
    return SQLiteStore(settings.sqlite_path)


def require_token(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = f"Bearer {settings.api_token}"
    if authorization is None:
        return
    if authorization != expected:
        raise HTTPException(status_code=401, detail="invalid local token")


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
    return f"""
    <!doctype html>
    <html lang="en">
      <head>
        <title>fraud-v2 dashboard</title>
        <style>
          body {{ font-family: Segoe UI, Arial, sans-serif; margin: 32px; color: #17202a; }}
          .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }}
          .metric {{ border: 1px solid #d7dde5; border-radius: 8px; padding: 16px; }}
          .label {{ color: #5d6d7e; font-size: 12px; text-transform: uppercase; }}
          .value {{ font-size: 32px; font-weight: 700; margin-top: 8px; }}
          a {{ color: #0b5cad; }}
        </style>
      </head>
      <body>
        <h1>fraud-v2 local dashboard</h1>
        <div class="grid">
          {event_card}
          {green_card}
          {yellow_card}
          {red_card}
        </div>
        <p>Open review cases: {sum(1 for case in cases if case.status == "open")}</p>
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


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "live"}


@app.get("/health/ready")
def ready(db: SQLiteStore = Depends(store)) -> dict[str, str | int]:
    return {"status": "ready", "events": len(db.list_events())}


@app.get("/metrics")
def metrics() -> Response:
    return metrics_response()


@app.post("/v1/events", dependencies=[Depends(require_token)])
def ingest_event(event: EventEnvelope, db: SQLiteStore = Depends(store)) -> EventEnvelope:
    try:
        stored = db.add_event(event)
    except DuplicatePayloadConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    event_counter.labels(event_type=stored.event_type.value).inc()
    return stored


@app.post("/v1/synthetic/generate", dependencies=[Depends(require_token)])
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
    "/v1/decisions/score", response_model=DecisionResponse, dependencies=[Depends(require_token)]
)
def score_decision(request: DecisionRequest, db: SQLiteStore = Depends(store)) -> DecisionResponse:
    start = time.perf_counter()
    decision = DecisionEngine(db).score(request)
    ReviewService(db).ensure_case_for_decision(decision.decision_id)
    decision_counter.labels(tier=decision.risk_tier.value, action=decision.action.value).inc()
    decision_latency.observe(time.perf_counter() - start)
    return decision


@app.get("/v1/decisions/{decision_id}", dependencies=[Depends(require_token)])
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
    "/v1/decisions", response_model=list[DecisionResponse], dependencies=[Depends(require_token)]
)
def list_decisions(db: SQLiteStore = Depends(store)) -> list[DecisionResponse]:
    return db.list_decisions()


@app.get("/v1/graph/neighborhood", dependencies=[Depends(require_token)])
def graph_neighborhood(
    entity_id: str,
    entity_type: EntityType = EntityType.USER,
    depth: int = Query(default=2, ge=1, le=4),
    db: SQLiteStore = Depends(store),
) -> dict[str, list[dict[str, str]]]:
    return GraphService(db.list_events()).neighborhood(
        EntityRef(entity_type=entity_type, entity_id=entity_id), depth=depth
    )


@app.get("/v1/review/cases", response_model=list[ReviewCase], dependencies=[Depends(require_token)])
def list_review_cases(db: SQLiteStore = Depends(store)) -> list[ReviewCase]:
    return ReviewService(db).list_cases()


@app.post(
    "/v1/review/cases/{case_id}/decision",
    response_model=ReviewDecision,
    dependencies=[Depends(require_token)],
)
def decide_review_case(
    case_id: UUID,
    request: ReviewDecisionRequest,
    db: SQLiteStore = Depends(store),
) -> ReviewDecision:
    return ReviewService(db).decide(case_id, request)
