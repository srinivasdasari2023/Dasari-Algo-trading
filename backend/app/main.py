"""
CapitalGuard Algo Trader – FastAPI application entry.
Risk-first, event-driven; no hardcoded credentials.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.email_service import log_email_status
    log_email_status()
    # So user can confirm OAuth redirect URI matches Upstox console
    print(f"[Upstox] Set this Redirect URI in Developer Console: {settings.UPSTOX_OAUTH_REDIRECT_URI}")
    yield
    # Shutdown: close pools
    pass


app = FastAPI(
    title="CapitalGuard Algo Trader API",
    description="Capital-preserving index options trading – Upstox",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV != "production" else None,
    redoc_url="/redoc" if settings.APP_ENV != "production" else None,
)


@app.exception_handler(404)
def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Not Found",
            "path": str(request.url.path),
            "hint": "Check /docs for available endpoints. Use /api/v1/auth/upstox/status, /api/v1/market/context/NIFTY, etc.",
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root():
    """Root: redirect to docs or return a short message so / is not 404."""
    if settings.APP_ENV != "production":
        return RedirectResponse(url="/docs", status_code=302)
    return {"message": "CapitalGuard API", "docs": "/docs", "health": "/health"}


@app.get("/api/v1")
def api_root():
    """So /api/v1 does not return 404."""
    return {"message": "CapitalGuard API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "capitalguard-api"}
