from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import create_internal_access_token, verify_oidc_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class OIDCCallbackRequest(BaseModel):
    id_token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/oidc/callback", response_model=TokenResponse)
async def oidc_callback(payload: OIDCCallbackRequest):
    """
    Frontend posts the id_token it received from Entra ID here; this
    exchanges it for the app's own short-lived internal JWT (see
    app/core/security.py). `verify_oidc_token` is currently a stub — wire
    real JWKS validation and user provisioning (create/update the `users`
    row from OIDC claims) before using this outside local dev.
    """
    try:
        claims = await verify_oidc_token(payload.id_token)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        ) from exc

    # In a real implementation: look up or provision the User row here from
    # claims["sub"] / claims["email"], then issue a token for that user id.
    token = create_internal_access_token(subject=claims["sub"])
    return TokenResponse(access_token=token)
