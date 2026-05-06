from __future__ import annotations

from dataclasses import dataclass

from fraud_v2.domain.events import EventEnvelope
from fraud_v2.graph.service import GraphService
from fraud_v2.infrastructure.optional_imports import optional_module


@dataclass(frozen=True)
class Neo4jGraphProjector:
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "fraud-local-password"

    def project(self, events: list[EventEnvelope]) -> int:
        neo4j = optional_module("neo4j", "infra")
        graph = GraphService(events).graph
        driver = neo4j.GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        try:
            with driver.session() as session:
                session.run("match (n) detach delete n")
                for node, data in graph.nodes(data=True):
                    session.run(
                        "merge (n:Entity {id: $id}) set n.entity_type = $entity_type",
                        id=node,
                        entity_type=data.get("entity_type", "UNKNOWN"),
                    )
                for source, target, data in graph.edges(data=True):
                    session.run(
                        """
                        match (a:Entity {id: $source}), (b:Entity {id: $target})
                        merge (a)-[r:RELATED {relationship: $relationship}]->(b)
                        set r.confidence = $confidence
                        """,
                        source=source,
                        target=target,
                        relationship=data.get("relationship", "RELATED"),
                        confidence=float(data.get("confidence", 1.0)),
                    )
        finally:
            driver.close()
        return graph.number_of_edges()
