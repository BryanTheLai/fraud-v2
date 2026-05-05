from __future__ import annotations

from fraud_v2.connectors.mock_vendors import ConnectorResult


class LocalCameraMetadataAnalyzer:
    connector_name = "local_camera_metadata"

    def inspect(
        self,
        *,
        camera_make: str | None,
        camera_model: str | None,
        software_tag: str | None,
    ) -> ConnectorResult:
        normalized_software = (software_tag or "").strip().lower()
        virtual_camera = normalized_software in {
            "obs virtual camera",
            "snap camera",
            "manycam",
            "xsplit vcam",
        }
        missing_model = not (camera_model or "").strip()
        missing_make = not (camera_make or "").strip()
        status = "REVIEW" if virtual_camera or missing_model else "OK"
        return ConnectorResult(
            connector_name=self.connector_name,
            status=status,
            safe_reason=("Local metadata signal only; never sufficient for a hard fraud decision."),
            signals={
                "camera_make_missing": missing_make,
                "camera_model_missing": missing_model,
                "virtual_camera_software": virtual_camera,
                "software_tag": software_tag or "",
            },
        )


class LocalPublicKybConnector:
    connector_name = "local_public_kyb"

    def lookup(
        self,
        *,
        business_name: str,
        jurisdiction: str,
        registry_status: str,
        lei_status: str,
        sanctions_hit: bool,
        company_age_days: int,
    ) -> ConnectorResult:
        normalized_registry = registry_status.strip().lower()
        normalized_lei = lei_status.strip().lower()
        registry_watch = normalized_registry not in {"active", "registered", "good_standing"}
        lei_watch = normalized_lei in {"missing", "lapsed", "retired", "annulled", "duplicate"}
        young_company = company_age_days < 30
        status = "REVIEW" if sanctions_hit or registry_watch or lei_watch or young_company else "OK"
        return ConnectorResult(
            connector_name=self.connector_name,
            status=status,
            safe_reason=(
                "Public KYB-style demo uses local inputs only; it is not a real KYC/KYB vendor."
            ),
            signals={
                "business_name": business_name,
                "jurisdiction": jurisdiction,
                "registry_status": registry_status,
                "lei_status": lei_status,
                "sanctions_hit": sanctions_hit,
                "young_company_hint": young_company,
                "public_data_only": True,
            },
        )
