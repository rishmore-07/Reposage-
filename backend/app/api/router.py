"""
app/api/router.py

Root API router — aggregates all versioned routers.

Adding a new feature:
1. Create app/api/v1/myfeature/router.py
2. Import it here
3. Include it in api_router with the correct prefix and tags
4. Zero changes to any other file.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.repositories.router import router as repositories_router
from app.modules.users.router import router as users_router

# Root API router — mounted at /api in main.py
api_router = APIRouter()

# ── Version 1 routes ──────────────────────────────────────────────────────────
api_router.include_router(
    auth_router,
    prefix="/v1/auth",
    tags=["Authentication"],
)

api_router.include_router(
    users_router,
    prefix="/v1/users",
    tags=["Users"],
)

api_router.include_router(
    repositories_router,
    prefix="/v1/repositories",
    tags=["Repositories"],
)
