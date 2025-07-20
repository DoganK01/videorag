"""
The Core Library for the VideoRAG Application.

This package contains shared, reusable components that are fundamental to both
the indexing pipeline and the real-time API.

Sub-packages:
- models: Wrappers for all external machine learning models (LLMs, VLMs, etc.).
- schemas: Pydantic models defining the data contracts and structures used
           throughout the application.
- storage: Abstract interfaces and concrete implementations for all data stores
           (graph, vector, metadata, and key-value).
"""

# This makes it possible to do `from core import models, schemas, storage`
from app.core import models
from app.core import schemas
from app.core import storage

__all__ = [
    "models",
    "schemas",
    "storage",
]