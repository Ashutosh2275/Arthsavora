"""
Legacy Dependency Shim
Re-exports dependencies from app.core.dependencies for full backwards compatibility.
"""

from app.core.dependencies import get_current_user, oauth2_scheme

__all__ = ["get_current_user", "oauth2_scheme"]
