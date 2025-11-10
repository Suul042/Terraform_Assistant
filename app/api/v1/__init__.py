"""
API v1 package
"""
from fastapi import APIRouter

from app.api.v1.endpoints import generate, validate, templates

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    generate.router,
    prefix="/generate",
    tags=["Code Generation"]
)

api_router.include_router(
    validate.router,
    prefix="/validate",
    tags=["Code Validation"]
)

api_router.include_router(
    templates.router,
    prefix="/templates",
    tags=["Templates"]
)
