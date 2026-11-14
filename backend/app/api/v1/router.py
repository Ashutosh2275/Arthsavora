"""
Arthsavora V1 Master Router
Aggregates all versioned V1 API sub-routers.
"""

from fastapi import APIRouter
from app.api.v1 import accounts, analytics_routes, auth, health, import_routes, intelligence_routes, invitations, ledger, transactions, users, workspaces

v1_router = APIRouter()

v1_router.include_router(health.router, prefix="/health")
v1_router.include_router(auth.router, prefix="/auth")
v1_router.include_router(users.router, prefix="/users")
v1_router.include_router(workspaces.router, prefix="/workspaces")
v1_router.include_router(invitations.router, prefix="/invitations")
v1_router.include_router(accounts.router, prefix="/accounts")
v1_router.include_router(accounts.router, prefix="/workspaces/{workspace_id}/accounts")
v1_router.include_router(transactions.router, prefix="/transactions")
v1_router.include_router(transactions.router, prefix="/workspaces/{workspace_id}/transactions")
v1_router.include_router(transactions.transfers_router, prefix="/transfers")
v1_router.include_router(transactions.transfers_router, prefix="/workspaces/{workspace_id}/transfers")
v1_router.include_router(ledger.router, prefix="/ledger")
v1_router.include_router(ledger.router, prefix="/workspaces/{workspace_id}/ledger")
v1_router.include_router(import_routes.router, prefix="/imports")
v1_router.include_router(import_routes.router, prefix="/workspaces/{workspace_id}/imports")
v1_router.include_router(intelligence_routes.router, prefix="")
v1_router.include_router(intelligence_routes.router, prefix="/workspaces/{workspace_id}")
v1_router.include_router(analytics_routes.router, prefix="/analytics")
v1_router.include_router(analytics_routes.router, prefix="/workspaces/{workspace_id}/analytics")
