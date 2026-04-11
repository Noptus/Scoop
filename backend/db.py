"""
Scoop — Database layer (Supabase)

Simple async wrapper around the Supabase REST API.
Uses httpx directly to keep dependencies minimal.
Swap to the official supabase-py client when you need
realtime or auth helpers.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")


def _headers() -> dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _url(table: str) -> str:
    return f"{SUPABASE_URL}/rest/v1/{table}"


# ── Users ─────────────────────────────────────

async def get_all_users() -> list[dict]:
    """Fetch all users with their companies."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _url("users"),
                headers=_headers(),
                params={"select": "*, companies(name)"},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise DatabaseError(f"Failed to fetch users: {exc}") from exc


async def get_user_by_email(email: str) -> Optional[dict]:
    if not email or not email.strip():
        raise ValidationError("Email must not be empty")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _url("users"),
                headers=_headers(),
                params={
                    "select": "*, companies(name)",
                    "email": f"eq.{email}",
                },
            )
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else None
    except httpx.HTTPStatusError as exc:
        raise DatabaseError(f"Failed to fetch user {email}: {exc}") from exc


async def create_user(email: str, product: str, companies: list[str]) -> dict:
    """Create a user and their tracked companies in one go."""
    if not email or not email.strip():
        raise ValidationError("Email must not be empty")
    if not product or not product.strip():
        raise ValidationError("Product must not be empty")

    try:
        async with httpx.AsyncClient() as client:
            # Create user
            resp = await client.post(
                _url("users"),
                headers=_headers(),
                json={"email": email, "product": product},
            )
            resp.raise_for_status()
            user: dict = resp.json()[0]

            # Create companies
            if companies:
                rows = [{"user_id": user["id"], "name": c} for c in companies]
                resp = await client.post(
                    _url("companies"),
                    headers=_headers(),
                    json=rows,
                )
                resp.raise_for_status()

            return user
    except httpx.HTTPStatusError as exc:
        raise DatabaseError(f"Failed to create user {email}: {exc}") from exc


# ── Digests ───────────────────────────────────

async def get_last_digest(user_id: str) -> list[dict]:
    """Fetch the most recent digest items for a user (for dedup)."""
    if not SUPABASE_URL:
        return []

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                _url("digests"),
                headers=_headers(),
                params={
                    "user_id": f"eq.{user_id}",
                    "select": "items",
                    "order": "sent_at.desc",
                    "limit": "1",
                },
            )
            resp.raise_for_status()
            rows = resp.json()
            return rows[0]["items"] if rows else []
    except httpx.HTTPStatusError as exc:
        logger.warning("Failed to fetch last digest for dedup: %s", exc)
        return []


async def save_digest(user_id: str, items: list[dict]) -> None:
    """Save a sent digest for history/dedup."""
    if not user_id or not user_id.strip():
        raise ValidationError("user_id must not be empty")

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                _url("digests"),
                headers=_headers(),
                json={
                    "user_id": user_id,
                    "item_count": len(items),
                    "items": items,
                },
            )
    except httpx.HTTPStatusError as exc:
        raise DatabaseError(f"Failed to save digest for user {user_id}: {exc}") from exc
