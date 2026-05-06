import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jwt.algorithms import RSAAlgorithm

from fraud_v2.config.settings import Settings
from fraud_v2.security.auth import AuthRole, authorize_bearer


def test_legacy_dev_token_gets_all_local_roles() -> None:
    principal = authorize_bearer(
        authorization="Bearer dev-token-change-me",
        settings=Settings(api_token="dev-token-change-me"),
        allowed_roles={AuthRole.ADMIN},
    )

    assert principal.subject == "local-admin+analyst+system"
    assert principal.roles == frozenset({AuthRole.ADMIN, AuthRole.ANALYST, AuthRole.SYSTEM})


def test_role_token_must_have_allowed_role() -> None:
    settings = Settings(api_token="", api_tokens="analyst:analyst-token,system:system-token")

    principal = authorize_bearer(
        authorization="Bearer analyst-token",
        settings=settings,
        allowed_roles={AuthRole.ANALYST},
    )
    assert principal.roles == frozenset({AuthRole.ANALYST})

    with pytest.raises(HTTPException) as exc:
        authorize_bearer(
            authorization="Bearer analyst-token",
            settings=settings,
            allowed_roles={AuthRole.SYSTEM},
        )
    assert exc.value.status_code == 403


def test_auth_disabled_only_when_no_tokens_configured() -> None:
    principal = authorize_bearer(
        authorization=None,
        settings=Settings(api_token="", api_tokens=""),
        allowed_roles={AuthRole.ADMIN},
    )

    assert principal.subject == "local-auth-disabled"
    assert AuthRole.ADMIN in principal.roles


def test_invalid_role_binding_fails_closed() -> None:
    with pytest.raises(HTTPException) as exc:
        authorize_bearer(
            authorization="Bearer any-token",
            settings=Settings(api_token="", api_tokens="owner:owner-token"),
            allowed_roles={AuthRole.ADMIN},
        )

    assert exc.value.status_code == 500


def test_jwt_auth_validates_claims_and_roles() -> None:
    token = _jwt_token(roles=["analyst"], secret=JWT_SECRET)
    settings = Settings(auth_mode="jwt", jwt_secret=JWT_SECRET)

    principal = authorize_bearer(
        authorization=f"Bearer {token}",
        settings=settings,
        allowed_roles={AuthRole.ANALYST},
    )

    assert principal.subject == "analyst-1"
    assert principal.roles == frozenset({AuthRole.ANALYST})


def test_jwt_auth_rejects_wrong_audience() -> None:
    token = _jwt_token(roles=["admin"], secret=JWT_SECRET, audience="wrong-api")
    settings = Settings(auth_mode="jwt", jwt_secret=JWT_SECRET)

    with pytest.raises(HTTPException) as exc:
        authorize_bearer(
            authorization=f"Bearer {token}",
            settings=settings,
            allowed_roles={AuthRole.ADMIN},
        )

    assert exc.value.status_code == 401


def test_jwt_auth_fails_closed_without_secret() -> None:
    token = _jwt_token(roles=["admin"], secret=JWT_SECRET)

    with pytest.raises(HTTPException) as exc:
        authorize_bearer(
            authorization=f"Bearer {token}",
            settings=Settings(auth_mode="jwt", jwt_secret=""),
            allowed_roles={AuthRole.ADMIN},
        )

    assert exc.value.status_code == 500


def test_jwt_auth_role_claim_must_match_allowed_role() -> None:
    token = _jwt_token(roles=["analyst"], secret=JWT_SECRET)

    with pytest.raises(HTTPException) as exc:
        authorize_bearer(
            authorization=f"Bearer {token}",
            settings=Settings(auth_mode="jwt", jwt_secret=JWT_SECRET),
            allowed_roles={AuthRole.SYSTEM},
        )

    assert exc.value.status_code == 403


def test_jwt_auth_accepts_rs256_token_from_local_jwks(tmp_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwks_path = tmp_path / "jwks.json"
    jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk.update({"kid": "local-rs256-key", "alg": "RS256", "use": "sig"})
    jwks_path.write_text(json.dumps({"keys": [jwk]}), encoding="utf-8")
    token = _jwt_token(
        roles=["admin"],
        secret=private_key,
        algorithm="RS256",
        headers={"kid": "local-rs256-key"},
    )

    principal = authorize_bearer(
        authorization=f"Bearer {token}",
        settings=Settings(
            auth_mode="jwt",
            jwt_algorithms="RS256",
            jwt_jwks_path=str(jwks_path),
        ),
        allowed_roles={AuthRole.ADMIN},
    )

    assert principal.subject == "analyst-1"
    assert principal.roles == frozenset({AuthRole.ADMIN})


def test_jwt_jwks_auth_rejects_symmetric_algorithms(tmp_path: Path) -> None:
    jwks_path = tmp_path / "jwks.json"
    jwks_path.write_text(json.dumps({"keys": []}), encoding="utf-8")
    token = _jwt_token(roles=["admin"], secret=JWT_SECRET)

    with pytest.raises(HTTPException) as exc:
        authorize_bearer(
            authorization=f"Bearer {token}",
            settings=Settings(
                auth_mode="jwt",
                jwt_algorithms="HS256",
                jwt_jwks_path=str(jwks_path),
            ),
            allowed_roles={AuthRole.ADMIN},
        )

    assert exc.value.status_code == 500


JWT_SECRET = "local-jwt-secret-for-fraud-v2-tests-32b"


def _jwt_token(
    *,
    roles: list[str],
    secret: object,
    subject: str = "analyst-1",
    issuer: str = "fraud-v2-local",
    audience: str = "fraud-v2-api",
    algorithm: str = "HS256",
    headers: dict[str, str] | None = None,
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": subject,
            "roles": roles,
            "iss": issuer,
            "aud": audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        secret,
        algorithm=algorithm,
        headers=headers,
    )
