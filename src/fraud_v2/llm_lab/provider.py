from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Protocol

from fraud_v2.infrastructure.optional_imports import optional_module


class LlmProvider(Protocol):
    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate one structured object that must still pass deterministic validation."""


@dataclass(frozen=True)
class LedgerEntry:
    content_hash: str
    schema_name: str
    model: str
    prompt_pack_version: str


class NoveltyLedger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def seen(self, payload: dict[str, Any]) -> bool:
        return self._hash(payload) in self._hashes()

    def append(
        self, payload: dict[str, Any], schema_name: str, model: str, prompt_pack_version: str
    ) -> None:
        entry = LedgerEntry(
            content_hash=self._hash(payload),
            schema_name=schema_name,
            model=model,
            prompt_pack_version=prompt_pack_version,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.__dict__, sort_keys=True) + "\n")

    def _hashes(self) -> set[str]:
        if not self.path.exists():
            return set()
        hashes: set[str] = set()
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    try:
                        record = json.loads(line)
                    except JSONDecodeError:
                        continue
                    content_hash = record.get("content_hash")
                    if isinstance(content_hash, str):
                        hashes.add(content_hash)
        return hashes

    def _hash(self, payload: dict[str, Any]) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class OfflineStubProvider:
    """No-network provider for tests and local dry runs."""

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        schema_title = str(schema.get("title", "scenario_spec"))
        return {
            "scenario_id": hashlib.sha1(prompt.encode("utf-8")).hexdigest()[:12],
            "schema_title": schema_title,
            "typology": "account_takeover",
            "signals": [
                "new_device_for_known_user",
                "impossible_travel",
                "payment_instruction_changed",
            ],
            "expected_label": "fraud",
            "narrative": (
                "offline stub scenario; replace with OpenAI or Azure provider when configured"
            ),
        }


@dataclass(frozen=True)
class OpenAIResponsesProvider:
    model: str
    api_key: str
    base_url: str | None = None
    timeout_seconds: float = 60.0

    def generate_structured(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        openai = optional_module("openai", "llm")
        client_kwargs: dict[str, Any] = {
            "api_key": self.api_key,
            "timeout": self.timeout_seconds,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = openai.OpenAI(**client_kwargs)
        schema_name = str(schema.get("title", "fraud_scenario")).replace("-", "_")
        response = client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        payload = json.loads(_extract_response_text(response))
        validate_structured_payload(payload, schema)
        return payload


def provider_from_env(provider_name: str | None = None) -> LlmProvider:
    provider = (provider_name or os.getenv("LLM_PROVIDER") or "offline").lower()
    if provider == "offline":
        return OfflineStubProvider()
    if provider in {"openai", "azure", "azure-openai"}:
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "LLM_PROVIDER requires OPENAI_API_KEY or AZURE_OPENAI_API_KEY; "
                "use LLM_PROVIDER=offline for no-network local runs"
            )
        model = os.getenv("OPENAI_MODEL", "gpt-5.5")
        base_url = os.getenv("OPENAI_BASE_URL")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if provider in {"azure", "azure-openai"} and azure_endpoint and not base_url:
            base_url = _azure_responses_base_url(azure_endpoint)
        return OpenAIResponsesProvider(model=model, api_key=api_key, base_url=base_url)
    raise RuntimeError(f"unknown LLM_PROVIDER: {provider}")


def validate_structured_payload(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    jsonschema = optional_module("jsonschema", "llm")
    jsonschema.validate(instance=payload, schema=schema)


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    if hasattr(response, "model_dump"):
        response_data = response.model_dump()
    elif isinstance(response, dict):
        response_data = response
    else:
        raise RuntimeError("OpenAI response did not expose output_text or model_dump")
    for output_item in response_data.get("output", []):
        for content_item in output_item.get("content", []):
            text = content_item.get("text")
            if isinstance(text, str) and text.strip():
                return text
    raise RuntimeError("OpenAI response did not include a text output")


def _azure_responses_base_url(endpoint: str) -> str:
    normalized = endpoint.rstrip("/")
    if normalized.endswith("/openai/v1"):
        return f"{normalized}/"
    return f"{normalized}/openai/v1/"
