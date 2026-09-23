from fastapi import APIRouter

from app.api.v1 import assets, audit, auth, dashboard, evidence, import_export, ropa

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(ropa.router)
api_router.include_router(import_export.router)
api_router.include_router(assets.router)
api_router.include_router(evidence.router)
api_router.include_router(audit.router)
api_router.include_router(dashboard.router)
