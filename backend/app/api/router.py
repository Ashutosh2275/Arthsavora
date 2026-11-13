"""
Arthsavora Master API Router
Centralizes and version-tags all domain API sub-routers.
"""

from fastapi import APIRouter
from app.api import auth, expenses, ml_ops, budget, analytics, goals, reports

api_router = APIRouter()

# Core Domain Routers
api_router.include_router(auth.router, prefix="/auth", tags=["Identity & Auth"])
api_router.include_router(expenses.router, prefix="/expenses", tags=["Expenses & Transactions"])
api_router.include_router(budget.router, prefix="/budget", tags=["Budgets & Forecasting"])
api_router.include_router(goals.router, prefix="/goals", tags=["Milestones & Goals"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Financial Analytics"])
api_router.include_router(ml_ops.router, prefix="/ml", tags=["Ingestion & Intelligence"])
api_router.include_router(reports.router, prefix="/reports", tags=["Statements & Reports"])


@api_router.get("/health", tags=["System"])
async def api_health():
    """Health check endpoint for API consumers and load balancers."""
    return {"status": "healthy", "service": "ARTHSAVORA_API"}
