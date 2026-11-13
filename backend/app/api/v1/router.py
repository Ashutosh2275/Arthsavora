"""
Arthsavora V1 Master Router
Aggregates all versioned V1 API sub-routers.
"""

from fastapi import APIRouter
from app.api.v1 import accounts, auth, health, invitations, transactions, users, workspaces

v1_router = APIRouter()

v1_router.include_router(health.router, prefix="/health")
v1_router.include_router(auth.router, prefix="/auth")
v1_router.include_router(users.router, prefix="/users")
v1_router.include_router(workspaces.router, prefix="/workspaces")
v1_router.include_router(invitations.router, prefix="/invitations")
v1_router.include_router(accounts.router, prefix="/accounts")
v1_router.include_router(transactions.router, prefix="/transactions")
