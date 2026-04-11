"""
Scoop API Server

Endpoints:
  POST /api/subscribe  — Sign up a new user (from landing page)
  POST /api/digest     — Run weekly digest (called by cron)
  GET  /health         — Health check
"""

from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from exceptions import ConfigError

load_dotenv()

logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://noptus.github.io,http://localhost:8080",
).split(",")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if not os.getenv("PPLX_KEY"):
        raise ConfigError("PPLX_KEY environment variable is required")
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Scoop API", version="0.2.0", lifespan=lifespan)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return Response(
        content='{"detail":"Too many requests"}',
        status_code=429,
        media_type="application/json",
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains"
    )
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Accept"],
    allow_credentials=False,
)


# ── Models ───────────────────────────────────

class SubscribeRequest(BaseModel):
    email: EmailStr
    product: str
    companies: list[str]


class DigestRequest(BaseModel):
    user_email: Optional[str] = None
    api_secret: str


# ── Validation helpers ───────────────────────

def _validate_subscribe(req: SubscribeRequest) -> tuple[str, list[str]]:
    """Validate and normalise subscribe request fields.

    Returns the cleaned product string and company list.
    Raises HTTPException on invalid input.
    """
    product = req.product.strip()
    if not product or len(product) > 500:
        raise HTTPException(400, "Product must be between 1 and 500 characters")

    companies: list[str] = []
    for c in req.companies:
        name = c.strip()
        if not name:
            continue
        if len(name) > 200:
            raise HTTPException(
                400,
                f"Company name too long (max 200 chars): {name[:40]}...",
            )
        companies.append(name)

    companies = companies[:10]
    if not companies:
        raise HTTPException(400, "At least one company is required")

    return product, companies


# ── Endpoints ────────────────────────────────

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/subscribe")
@limiter.limit("5/minute")
async def subscribe(request: Request, req: SubscribeRequest) -> dict[str, str]:
    """Sign up a new user from the landing page."""
    product, companies = _validate_subscribe(req)

    # Save to Supabase if configured
    if os.getenv("SUPABASE_URL"):
        from db import create_user, get_user_by_email

        existing = await get_user_by_email(req.email)
        if not existing:
            await create_user(req.email, product, companies)

    # Send welcome email via Gmail
    from send_email import send_welcome_email

    await send_welcome_email(req.email)

    return {"status": "ok"}


@app.post("/api/digest")
@limiter.limit("2/minute")
async def run_digest(request: Request, req: DigestRequest) -> dict[str, str | int]:
    """Run the weekly digest pipeline. Called by GitHub Actions cron."""
    expected = os.getenv("CRON_SECRET", "")
    if not expected:
        raise HTTPException(500, "CRON_SECRET is not configured")
    if not secrets.compare_digest(req.api_secret, expected):
        raise HTTPException(403, "Invalid API secret")

    from db import get_all_users, get_user_by_email
    from digest import generate_digest_for_user
    from send_email import send_digest_email

    if req.user_email:
        user = await get_user_by_email(req.user_email)
        users = [user] if user else []
    else:
        users = await get_all_users()

    sent = 0
    for user in users:
        items = await generate_digest_for_user(user)
        if items:
            await send_digest_email(user, items)
            sent += 1

    return {"status": "ok", "processed": sent}
