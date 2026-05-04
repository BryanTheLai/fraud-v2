from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from fraud_v2.domain.enums import EntityType


class EntityRef(BaseModel):
    model_config = ConfigDict(frozen=True)

    entity_type: EntityType
    entity_id: str = Field(min_length=1, max_length=160)

    @property
    def graph_key(self) -> str:
        return f"{self.entity_type.value}:{self.entity_id}"


class GraphEdge(BaseModel):
    source: EntityRef
    target: EntityRef
    relationship: str = Field(min_length=1, max_length=80)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EntityGraph(BaseModel):
    nodes: list[EntityRef]
    edges: list[GraphEdge]
