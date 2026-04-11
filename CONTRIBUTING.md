# Contributing to Scoop

Thanks for your interest in contributing! Here's how to get started.

## Getting Started

1. **Fork** the repo and clone your fork.
2. Copy the environment template:
   ```bash
   cp .env.example .env
   ```
3. Fill in your API keys (see `.env.example` for details).
4. Install dependencies:
   ```bash
   cd backend
   python3 -m pip install -r requirements.txt
   ```
5. Run the dev server:
   ```bash
   python3 -m uvicorn main:app --reload
   ```

## Development Guidelines

- **Python 3.12+** is required.
- Use type hints on all public functions.
- Run the linter before submitting:
  ```bash
  python3 -m ruff check backend/
  ```
- Keep commits focused — one logical change per commit.

## Reporting Bugs

Open an issue with:
- Steps to reproduce
- Expected vs. actual behaviour
- Python version and OS

## Security Vulnerabilities

**Do not open a public issue.** Email the maintainer directly (see the repo owner's profile). We'll respond within 48 hours and coordinate a fix before disclosure.

## Pull Requests

1. Create a feature branch from `main`.
2. Write clear commit messages.
3. Open a PR against `main` with a short description of what and why.
4. Ensure the secret-scanning CI check passes.

## Code of Conduct

Be kind, be constructive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
