"""
Scoop — Custom exception hierarchy

All Scoop-specific exceptions inherit from ScoopError,
making it easy to catch any Scoop failure in one place.
"""

from __future__ import annotations


class ScoopError(Exception):
    """Base exception for Scoop."""


class ConfigError(ScoopError):
    """Missing or invalid configuration."""


class APIError(ScoopError):
    """External API call failed."""


class DatabaseError(ScoopError):
    """Database operation failed."""


class EmailError(ScoopError):
    """Email delivery failed."""


class ValidationError(ScoopError):
    """Input validation failed."""
