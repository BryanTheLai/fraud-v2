from __future__ import annotations

from pydantic import BaseModel, Field


class ConnectorResult(BaseModel):
    connector_name: str
    status: str
    safe_reason: str
    signals: dict[str, str | int | float | bool] = Field(default_factory=dict)


class MockKycConnector:
    connector_name = "mock_kyc"

    def screen(self, user_id: str, document_hash: str | None = None) -> ConnectorResult:
        synthetic_hit = user_id.endswith("999") or document_hash == "synthetic_doc_reuse"
        return ConnectorResult(
            connector_name=self.connector_name,
            status="OK",
            safe_reason="Mock KYC completed with synthetic local signals.",
            signals={
                "synthetic_identity_hint": synthetic_hit,
                "document_hash_seen_before": document_hash == "synthetic_doc_reuse",
            },
        )


class MockDeviceIntelConnector:
    connector_name = "mock_device_intel"

    def inspect(self, device_id: str, user_agent_family: str) -> ConnectorResult:
        emulator_hint = "emulator" in user_agent_family.lower() or device_id.endswith("emulator")
        return ConnectorResult(
            connector_name=self.connector_name,
            status="OK",
            safe_reason="Mock device intelligence completed with synthetic local signals.",
            signals={
                "emulator_hint": emulator_hint,
                "new_device_hint": device_id.endswith("new"),
            },
        )


class MockConsortiumConnector:
    connector_name = "mock_consortium"

    def lookup(self, identifier_hash: str) -> ConnectorResult:
        high_risk = identifier_hash.startswith("bad_") or identifier_hash.endswith("_fraud")
        return ConnectorResult(
            connector_name=self.connector_name,
            status="OK",
            safe_reason="Mock consortium lookup completed with synthetic local signals.",
            signals={"known_bad_identifier": high_risk},
        )
