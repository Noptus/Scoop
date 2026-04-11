# Security Policy

## Reporting a Vulnerability

**Do not open a public issue.**

If you discover a security vulnerability in Scoop, please report it responsibly:

1. Email the maintainer directly (see the repo owner's GitHub profile).
2. Include a clear description of the issue and steps to reproduce it.
3. We will acknowledge your report within **48 hours**.
4. We will coordinate a fix and release before any public disclosure.

## Supported Versions

Only the latest version on the `main` branch is actively maintained.

## Scope

The following are in scope:

- The FastAPI backend (`backend/`)
- GitHub Actions workflows (`.github/workflows/`)
- Database schema and RLS policies (`backend/schema.sql`)
- The static landing page (`docs/`)

## Security Measures

- All API secrets are stored in environment variables, never in code.
- TruffleHog secret scanning runs on every push and PR.
- Supabase Row-Level Security enforces per-user data isolation.
- All user-sourced strings are HTML-escaped before rendering.
- The cron endpoint uses timing-safe secret comparison.
- Rate limiting protects public endpoints from abuse.
