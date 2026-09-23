"""
Auth layer.

Real deployments authenticate via Entra ID / OIDC: the frontend redirects to
`OIDC_ISSUER`, the IdP handles login + MFA, and this backend only ever sees
a validated OIDC token which it exchanges for a short-lived internal JWT.

This scaffold provides:
  1. A pluggable `verify_oidc_token()` interface (stubbed — wire real
     issuer/JWKS validation before using this for anything beyond local dev).
  2. Internal JWT issuance/verification used by the API after OIDC exchange.
  3. `get_current_user`, the FastAPI dependency every protected route uses.

Do NOT extend this with a local username/password flow — the architecture
deliberately has no local password store (see docs/architecture.md, Security
Architecture section).
"""
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"  # internal token signing; OIDC token validation is separate (RS256 + JWKS)
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_internal_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Issue a short-lived internal JWT after a successful OIDC exchange."""
    to_encode: dict[str, Any] = {"sub": subject}
    if extra_claims:
        to_encode.update(extra_claims)
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.app_secret_key, algorithm=ALGORITHM)


def decode_internal_access_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        ) from exc


async def verify_oidc_token(id_token: str) -> dict[str, Any]:
    """
    STUB: validate an Entra ID / OIDC id_token against the tenant's JWKS
    (issuer, audience, signature, expiry). Replace this with real
    validation (e.g. via `python-jose` + JWKS fetched from
    f"{settings.oidc_issuer}/.well-known/openid-configuration") before
    relying on this for real authentication.
    """
    raise NotImplementedError(
        "Wire real OIDC/JWKS validation here before using this in a non-local "
        "environment. See docs/architecture.md, Security Architecture."
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_internal_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user
