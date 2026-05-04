from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

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
