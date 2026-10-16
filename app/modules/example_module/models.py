"""
SQLAlchemy models for the example module.

These models are re-exported from app.models for centralized model management.
See app/models/example.py for the full implementation.
"""

from __future__ import annotations

from app.models.example import Example

__all__ = ["Example"]