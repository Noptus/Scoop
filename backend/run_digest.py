"""
CLI entrypoint for the digest pipeline.
Called by GitHub Actions cron or manually.

Usage:
  python run_digest.py              # Process all users
  python run_digest.py --email x    # Process one user
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main(email: str | None = None) -> None:
    from db import get_all_users, get_user_by_email
    from digest import generate_digest_for_user
    from send_email import send_digest_email

    if email:
        users = [await get_user_by_email(email)]
        users = [u for u in users if u]
    else:
        users = await get_all_users()

    if not users:
        logger.info("No users to process.")
        return

    logger.info("Processing %d user(s)...", len(users))

    for user in users:
        try:
            items = await generate_digest_for_user(user)
            if items:
                await send_digest_email(user, items)
                logger.info("  Sent digest to %s (%d items)", user["email"], len(items))
            else:
                logger.info("  No signals found for %s", user["email"])
        except Exception:
            logger.exception("  Error processing %s", user["email"])

    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Scoop digest pipeline")
    parser.add_argument("--email", help="Process a specific user")
    args = parser.parse_args()
    asyncio.run(main(args.email))
