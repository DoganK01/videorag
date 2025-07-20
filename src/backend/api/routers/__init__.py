# videorag_project/api/routers/__init__.py
"""
This package defines the API endpoints (routes) for the FastAPI application.
Each file typically corresponds to a specific resource or logical grouping of endpoints.
"""

from app.api.routers.query import router as query_router
from app.api.routers.indexing_router import router as indexing_router
from app.api.routers.library_router import router as library_router

__all__ = [
    "query_router",
    "indexing_router",
    "library_router"
]