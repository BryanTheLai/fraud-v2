from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException

from fraud_v2.config.settings import Settings, get_settings


class AuthRole(StrEnum):
    ADMIN = "admin"
    ANALYST = "analyst"
    SYSTEM = "system"


@dataclass(frozen=True)
class AuthPrincipal:
    subject: str
    roles: frozenset[AuthRole]

    def has_any_role(self, allowed_roles: set[AuthRole]) -> bool:
        return bool(self.roles.intersection(allowed_roles))


def require_roles(*allowed_roles: AuthRole) -> Callable[[str | None, Settings], AuthPrincipal]:
    allowed = set(allowed_roles)

    def dependency(
        authorization: str | None = Header(default=None),
        settings: Settings = Depends(get_settings),
    ) -> AuthPrincipal:
        return authorize_bearer(authorization, settings, allowed)

    return dependency


def authorize_bearer(
    authorization: str | None,
    settings: Settings,
    allowed_roles: set[AuthRole],
) -> AuthPrincipal:
    if settings.auth_mode.lower() == "jwt":
        return _authorize_jwt(authorization, settings, allowed_roles)
    if settings.auth_mode.lower() != "token":
        raise HTTPException(
            status_code=500, detail=f"unsupported FRAUD_AUTH_MODE: {settings.auth_mode}"
        )

    token_roles = _token_roles(settings)
    if not token_roles:
        return AuthPrincipal(
            subject="local-auth-disabled",
            roles=frozenset({AuthRole.ADMIN, AuthRole.ANALYST, AuthRole.SYSTEM}),
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing local token")

    token = authorization.removeprefix("Bearer ").strip()
    roles = token_roles.get(token)
    if roles is None:
        raise HTTPException(status_code=401, detail="invalid local token")

    principal = AuthPrincipal(subject=_subject_for_roles(roles), roles=frozenset(roles))
    if allowed_roles and not principal.has_any_role(allowed_roles):
        raise HTTPException(status_code=403, detail="insufficient local role")
    return principal


def _authorize_jwt(
    authorization: str | None,
    settings: Settings,
    allowed_roles: set[AuthRole],
) -> AuthPrincipal:
    if not settings.jwt_secret:
        raise HTTPException(status_code=500, detail="FRAUD_JWT_SECRET is required for JWT auth")
    if len(settings.jwt_secret.encode("utf-8")) < 32:
        raise HTTPException(status_code=500, detail="FRAUD_JWT_SECRET must be at least 32 bytes")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=settings.jwt_leeway_seconds,
            options={"require": ["exp", "iss", "aud", "sub", settings.jwt_roles_claim]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid bearer token") from exc

    subject = _string_claim(payload, "sub")
    roles = _roles_from_claim(payload.get(settings.jwt_roles_claim), settings.jwt_roles_claim)
    principal = AuthPrincipal(subject=subject, roles=frozenset(roles))
    if allowed_roles and not principal.has_any_role(allowed_roles):
        raise HTTPException(status_code=403, detail="insufficient local role")
    return principal


def _string_claim(payload: dict[str, Any], claim: str) -> str:
    value = payload.get(claim)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=401, detail=f"invalid JWT {claim} claim")
    return value


def _roles_from_claim(raw_roles: Any, claim: str) -> set[AuthRole]:
    if isinstance(raw_roles, str):
        role_names = [role.strip().lower() for role in raw_roles.replace(";", ",").split(",")]
    elif isinstance(raw_roles, list):
        role_names = [str(role).strip().lower() for role in raw_roles]
    else:
        raise HTTPException(status_code=401, detail=f"invalid JWT {claim} claim")

    roles: set[AuthRole] = set()
    for role_name in role_names:
        if not role_name:
            continue
        try:
            roles.add(AuthRole(role_name))
        except ValueError as exc:
            raise HTTPException(status_code=401, detail=f"invalid JWT role: {role_name}") from exc
    if not roles:
        raise HTTPException(status_code=401, detail=f"invalid JWT {claim} claim")
    return roles


def _token_roles(settings: Settings) -> dict[str, set[AuthRole]]:
    token_roles: dict[str, set[AuthRole]] = {}
    if settings.api_token:
        token_roles[settings.api_token] = {AuthRole.ADMIN, AuthRole.ANALYST, AuthRole.SYSTEM}

    for binding in _split_bindings(settings.api_tokens):
        role_name, token = _parse_binding(binding)
        role = AuthRole(role_name)
        token_roles.setdefault(token, set()).add(role)
    return token_roles


def _split_bindings(raw_bindings: str) -> list[str]:
    normalized = raw_bindings.replace(";", ",")
    return [binding.strip() for binding in normalized.split(",") if binding.strip()]


def _parse_binding(binding: str) -> tuple[str, str]:
    if ":" not in binding:
        raise HTTPException(
            status_code=500,
            detail="invalid FRAUD_API_TOKENS entry; expected role:token",
        )
    role_name, token = binding.split(":", 1)
    role_name = role_name.strip().lower()
    token = token.strip()
    if not role_name or not token:
        raise HTTPException(
            status_code=500,
            detail="invalid FRAUD_API_TOKENS entry; role and token are required",
        )
    try:
        AuthRole(role_name)
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"invalid FRAUD_API_TOKENS role: {role_name}",
        ) from exc
    return role_name, token


def _subject_for_roles(roles: set[AuthRole]) -> str:
    role_text = "+".join(sorted(role.value for role in roles))
    return f"local-{role_text}"
