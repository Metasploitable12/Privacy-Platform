from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.rbac import seed_rbac_from_yaml

settings = get_settings()

app = FastAPI(
    title="Privacy Operations Platform API",
    version="0.1.0-phase1",
    description=(
        "Self-hosted privacy operations platform — Phase 1 scaffold "
        "(auth, RBAC, ROPA, data inventory, evidence, versioning, audit log). "
        "See /docs/architecture.md in the repository for the full design."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.on_event("startup")
async def on_startup() -> None:
    # Idempotent RBAC seed from rbac_matrix.yaml — safe to run on every boot.
    async with AsyncSessionLocal() as db:
        await seed_rbac_from_yaml(db)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "env": settings.app_env}
