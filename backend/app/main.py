from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.observability import TraceIdMiddleware


app = FastAPI(title=f"{settings.app_name} API", version="0.1.0")
app.add_middleware(TraceIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get(f"{settings.api_prefix}/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
