from __future__ import annotations

from typing import Protocol

from fraud_v2.domain.decisions import FeatureVector
from fraud_v2.domain.entities import EntityRef
from fraud_v2.domain.events import EventEnvelope


class EventRepository(Protocol):
    def add_event(self, event: EventEnvelope) -> EventEnvelope: ...

    def list_events(self) -> list[EventEnvelope]: ...


class EventPublisher(Protocol):
    def publish(self, topic: str, event: EventEnvelope) -> None: ...


class FeatureCache(Protocol):
    def put(self, vector: FeatureVector) -> None: ...

    def get(self, target: EntityRef) -> FeatureVector | None: ...


class GraphProjector(Protocol):
    def project(self, events: list[EventEnvelope]) -> int: ...
