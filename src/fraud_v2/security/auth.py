from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.request import urlopen

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


class _JwtConfigError(RuntimeError):
    pass


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
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = _decode_jwt(token, settings)
    except _JwtConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid bearer token") from exc

    subject = _string_claim(payload, "sub")
    roles = _roles_from_claim(payload.get(settings.jwt_roles_claim), settings.jwt_roles_claim)
    principal = AuthPrincipal(subject=subject, roles=frozenset(roles))
    if allowed_roles and not principal.has_any_role(allowed_roles):
        raise HTTPException(status_code=403, detail="insufficient local role")
    return principal


def _decode_jwt(token: str, settings: Settings) -> dict[str, Any]:
    use_jwks = _uses_jwks(settings)
    algorithms = _jwt_algorithms(settings, use_jwks=use_jwks)
    key: str | Any
    if use_jwks:
        key = _jwks_signing_key(token, settings)
    else:
        if not settings.jwt_secret:
            raise _JwtConfigError("FRAUD_JWT_SECRET is required for JWT auth")
        if len(settings.jwt_secret.encode("utf-8")) < 32:
            raise _JwtConfigError("FRAUD_JWT_SECRET must be at least 32 bytes")
        key = settings.jwt_secret
    return jwt.decode(
        token,
        key,
        algorithms=algorithms,
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
        leeway=settings.jwt_leeway_seconds,
        options={"require": ["exp", "iss", "aud", "sub", settings.jwt_roles_claim]},
    )


def _uses_jwks(settings: Settings) -> bool:
    return bool(
        settings.jwt_jwks_path.strip()
        or settings.jwt_jwks_url.strip()
        or settings.jwt_oidc_discovery_url.strip()
    )


def _jwt_algorithms(settings: Settings, *, use_jwks: bool) -> list[str]:
    algorithms = [
        algorithm.strip().upper()
        for algorithm in settings.jwt_algorithms.replace(";", ",").split(",")
        if algorithm.strip()
    ]
    if not algorithms:
        raise _JwtConfigError("FRAUD_JWT_ALGORITHMS must include at least one algorithm")
    if use_jwks and any(algorithm.startswith("HS") for algorithm in algorithms):
        raise _JwtConfigError("JWKS JWT auth cannot allow HS algorithms")
    if not use_jwks and any(not algorithm.startswith("HS") for algorithm in algorithms):
        raise _JwtConfigError("local secret JWT auth only supports HS algorithms")
    return algorithms


def _jwks_signing_key(token: str, settings: Settings) -> Any:
    jwks = _load_jwks(settings)
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    if not isinstance(kid, str) or not kid:
        raise jwt.InvalidTokenError("missing JWT kid header")
    for jwk_data in jwks.get("keys", []):
        if not isinstance(jwk_data, dict):
            continue
        if jwk_data.get("kid") == kid:
            return jwt.PyJWK.from_dict(jwk_data).key
    raise jwt.InvalidTokenError("no matching JWK")


def _load_jwks(settings: Settings) -> dict[str, Any]:
    if settings.jwt_jwks_path.strip():
        return _read_json_file(Path(settings.jwt_jwks_path))
    if settings.jwt_jwks_url.strip():
        return _read_json_url(settings.jwt_jwks_url)
    if settings.jwt_oidc_discovery_url.strip():
        metadata = _read_json_url(settings.jwt_oidc_discovery_url)
        jwks_uri = metadata.get("jwks_uri")
        if not isinstance(jwks_uri, str) or not jwks_uri:
            raise _JwtConfigError("OIDC discovery document is missing jwks_uri")
        return _read_json_url(jwks_uri)
    raise _JwtConfigError(
        "FRAUD_JWT_JWKS_PATH, FRAUD_JWT_JWKS_URL, or FRAUD_JWT_OIDC_DISCOVERY_URL is required"
    )


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        raw_payload = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise _JwtConfigError(f"failed to read JWKS file: {path}") from exc
    return _json_object(raw_payload, source=str(path))


def _read_json_url(url: str) -> dict[str, Any]:
    try:
        with urlopen(url, timeout=5) as response:
            raw_payload = response.read().decode("utf-8")
    except OSError as exc:
        raise _JwtConfigError(f"failed to read JWKS URL: {url}") from exc
    return _json_object(raw_payload, source=url)


def _json_object(raw_payload: str, *, source: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        raise _JwtConfigError(f"invalid JWKS JSON from {source}") from exc
    if not isinstance(payload, dict):
        raise _JwtConfigError(f"JWKS JSON from {source} must be an object")
    return payload


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
