from __future__ import annotations

from dataclasses import dataclass

from fraud_v2.domain.decisions import FeatureVector
from fraud_v2.domain.entities import EntityRef
from fraud_v2.infrastructure.optional_imports import optional_module


@dataclass(frozen=True)
class RedisFeatureCache:
    url: str = "redis://localhost:6379/0"
    prefix: str = "fraud-v2:features"

    def put(self, vector: FeatureVector) -> None:
        redis = optional_module("redis", "infra")
        client = redis.Redis.from_url(self.url)
        client.set(self._key(vector.target_entity), vector.model_dump_json())

    def get(self, target: EntityRef) -> FeatureVector | None:
        redis = optional_module("redis", "infra")
        client = redis.Redis.from_url(self.url)
        raw = client.get(self._key(target))
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return FeatureVector.model_validate_json(raw)

    def _key(self, target: EntityRef) -> str:
        return f"{self.prefix}:{target.graph_key}"
