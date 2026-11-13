"""
Arthsavora V1 Master Router
Aggregates all versioned V1 API sub-routers.
"""

from fastapi import APIRouter
from app.api.v1 import auth, health, workspaces

v1_router = APIRouter()

v1_router.include_router(health.router, prefix="/health")
v1_router.include_router(auth.router, prefix="/auth")
v1_router.include_router(workspaces.router, prefix="/workspaces")
