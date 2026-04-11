"""
Scoop - URL helpers

Centralized URL generation to avoid circular imports.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from urllib.parse import quote


def unsubscribe_token(email: str) -> str:
    """Generate an HMAC token for unsubscribe links."""
    key = os.getenv("CRON_SECRET", "")
    if not key:
        raise RuntimeError("CRON_SECRET must be set to generate unsubscribe tokens")
    return hmac.new(key.encode(), email.lower().strip().encode(), hashlib.sha256).hexdigest()[:16]


def build_unsubscribe_url(email: str) -> str:
    """Build a signed unsubscribe URL."""
    base = os.getenv("API_URL", "http://localhost:8000")
    token = unsubscribe_token(email)
    return f"{base}/api/unsubscribe?email={quote(email)}&token={token}"


def build_tracking_url(user_id: str) -> str:
    """Build the open-tracking pixel URL."""
    base = os.getenv("API_URL", "http://localhost:8000")
    return f"{base}/api/track/open?uid={quote(user_id)}"
