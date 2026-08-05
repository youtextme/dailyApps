"""Consultative roles — behaviors + exit criteria, not static rule sheets."""

from .base import Role, RoleContext
from .registry import get_role

__all__ = ["Role", "RoleContext", "get_role"]
