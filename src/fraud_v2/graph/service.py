from __future__ import annotations

import networkx as nx

from fraud_v2.domain.entities import EntityRef, GraphEdge
from fraud_v2.domain.enums import EntityType, LabelValue
from fraud_v2.domain.events import DeviceObserved, EventEnvelope, LabelCreated, PaymentAttempted


class GraphService:
    def __init__(self, events: list[EventEnvelope]) -> None:
        self.graph = nx.Graph()
        self._fraud_nodes: set[str] = set()
        self._build(events)

    def distance_to_confirmed_fraud(self, target: EntityRef, cutoff: int = 3) -> int | None:
        source = target.graph_key
        if source not in self.graph:
            return None
        distances: list[int] = []
        for fraud_node in self._fraud_nodes:
            if fraud_node == source:
                return 0
            try:
                length = nx.shortest_path_length(self.graph, source=source, target=fraud_node)
            except nx.NetworkXNoPath:
                continue
            if length <= cutoff:
                distances.append(int(length))
        return min(distances) if distances else None

    def neighborhood(self, target: EntityRef, depth: int = 2) -> dict[str, list[dict[str, str]]]:
        source = target.graph_key
        if source not in self.graph:
            return {"nodes": [], "edges": []}
        nodes = nx.single_source_shortest_path_length(self.graph, source, cutoff=depth).keys()
        subgraph = self.graph.subgraph(nodes)
        return {
            "nodes": [{"id": node, "label": node.split(":", 1)[0]} for node in subgraph.nodes],
            "edges": [
                {
                    "source": source_node,
                    "target": target_node,
                    "relationship": str(data.get("relationship", "RELATED")),
                }
                for source_node, target_node, data in subgraph.edges(data=True)
            ],
        }

    def _build(self, events: list[EventEnvelope]) -> None:
        for event in events:
            for ref in event.entity_refs:
                self.graph.add_node(ref.graph_key, entity_type=ref.entity_type.value)
            for edge in self._edges_for_event(event):
                self.graph.add_edge(
                    edge.source.graph_key,
                    edge.target.graph_key,
                    relationship=edge.relationship,
                    confidence=edge.confidence,
                )
            if (
                isinstance(event.payload, LabelCreated)
                and event.payload.label_value == LabelValue.FRAUD
            ):
                self._fraud_nodes.add(event.payload.target_entity.graph_key)

    def _edges_for_event(self, event: EventEnvelope) -> list[GraphEdge]:
        payload = event.payload
        if isinstance(payload, DeviceObserved):
            return [
                GraphEdge(
                    source=EntityRef(entity_type=EntityType.USER, entity_id=payload.user_id),
                    target=EntityRef(entity_type=EntityType.DEVICE, entity_id=payload.device_id),
                    relationship="USED_DEVICE",
                ),
                GraphEdge(
                    source=EntityRef(entity_type=EntityType.USER, entity_id=payload.user_id),
                    target=EntityRef(
                        entity_type=EntityType.IP_ADDRESS, entity_id=payload.ip_address
                    ),
                    relationship="USED_IP",
                    confidence=0.7,
                ),
            ]
        if isinstance(payload, PaymentAttempted):
            return [
                GraphEdge(
                    source=EntityRef(entity_type=EntityType.USER, entity_id=payload.user_id),
                    target=EntityRef(
                        entity_type=EntityType.TRANSACTION, entity_id=payload.transaction_id
                    ),
                    relationship="ATTEMPTED_PAYMENT",
                ),
                GraphEdge(
                    source=EntityRef(entity_type=EntityType.USER, entity_id=payload.user_id),
                    target=EntityRef(entity_type=EntityType.DEVICE, entity_id=payload.device_id),
                    relationship="USED_DEVICE",
                ),
                GraphEdge(
                    source=EntityRef(entity_type=EntityType.USER, entity_id=payload.user_id),
                    target=EntityRef(
                        entity_type=EntityType.BANK_ACCOUNT, entity_id=payload.payee_hash
                    ),
                    relationship="PAID_PAYEE",
                ),
            ]
        refs = event.entity_refs
        if len(refs) <= 1:
            return []
        first = refs[0]
        return [
            GraphEdge(source=first, target=ref, relationship=f"CO_OCCURS_{event.event_type.value}")
            for ref in refs[1:]
        ]
