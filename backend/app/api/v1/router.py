from fastapi import APIRouter

from app.domains.ai.router import router as ai_router
from app.domains.dashboard.router import router as dashboard_router
from app.domains.insurance.router import router as insurance_router
from app.domains.platform.auth_router import router as auth_router
from app.domains.platform.router import router as platform_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(platform_router)
api_router.include_router(insurance_router)
api_router.include_router(ai_router)
api_router.include_router(dashboard_router)
