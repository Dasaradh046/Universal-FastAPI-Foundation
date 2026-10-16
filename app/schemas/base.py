"""
Base response schema using ORM Mode.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ORMBase(BaseModel):
    """Base model that auto-populates from ORM objects.

    Legacy support — new endpoints should use the ResponseEnvelope instead.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


__all__ = ["ORMBase"]