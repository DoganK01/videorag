"""
Utility functions for the indexing pipeline, primarily for low-level
file and media processing.
"""

from app.indexing.utils.video_processor import extract_frames

__all__ = [
    "extract_frames",
]