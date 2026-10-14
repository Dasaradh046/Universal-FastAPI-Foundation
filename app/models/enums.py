"""
Shared application enums.

These enums are used across modules, models, and schemas. They use ``str``
as the base type so they serialize transparently to JSON and render as
plain string values in PostgreSQL ENUM columns.
"""

from app.core.enums import *  # Re-export for convenience
