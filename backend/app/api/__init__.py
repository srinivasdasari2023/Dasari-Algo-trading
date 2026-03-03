from fastapi import APIRouter
from app.api import auth, market, signals, risk, orders, dashboard, audit

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(market.router, prefix="/market", tags=["market"])
router.include_router(signals.router, prefix="/signals", tags=["signals"])
router.include_router(risk.router, prefix="/risk", tags=["risk"])
router.include_router(orders.router, prefix="/orders", tags=["orders"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
router.include_router(audit.router, prefix="/audit", tags=["audit"])
