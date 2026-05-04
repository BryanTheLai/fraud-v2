import pytest
from fastapi import HTTPException

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
