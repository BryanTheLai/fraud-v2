from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

decision_counter = Counter(
    "fraud_decisions_total",
    "Fraud decisions by tier and action.",
    ["tier", "action"],
)
decision_latency = Histogram(
    "fraud_decision_latency_seconds",
    "Decision scoring latency.",
)
event_counter = Counter(
    "fraud_events_ingested_total",
    "Events ingested by type.",
    ["event_type"],
)


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
