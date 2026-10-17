"""
SQLAlchemy models for the example module.

Re-exports the canonical Example model from app.models.example.
"""

from __future__ import annotations

from app.models.example import Example

__all__ = ["Example"]
