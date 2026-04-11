"""
CLI entrypoint for the digest pipeline.
Called by GitHub Actions cron or manually.

Usage:
  python run_digest.py                    # Research + send (all users)
  python run_digest.py --email x          # Research + send (one user)
  python run_digest.py --research-only    # Research and save, no email
  python run_digest.py --send-only        # Send last saved digest, no research
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


async def research(email: str | None = None) -> None:
    """Generate signals and save to DB. No emails sent."""
    from db import get_all_users, get_user_by_email, save_digest
    from digest import generate_digest_for_user

    if email:
        users = [await get_user_by_email(email)]
        users = [u for u in users if u]
    else:
        users = await get_all_users()

    if not users:
        logger.info("No users to process.")
        return

    logger.info("Researching %d user(s)...", len(users))

    for user in users:
        try:
            items = await generate_digest_for_user(user)
            if items:
                await save_digest(user["id"], items)
                logger.info("  Saved %d signals for %s", len(items), user["email"])
            else:
                logger.info("  No signals found for %s", user["email"])
        except Exception:
            logger.exception("  Error researching %s", user["email"])

    logger.info("Research done.")


async def send(email: str | None = None) -> None:
    """Send the most recently saved digest to users."""
    from db import get_all_users, get_last_digest, get_user_by_email
    from send_email import send_digest_email

    if email:
        users = [await get_user_by_email(email)]
        users = [u for u in users if u]
    else:
        users = await get_all_users()

    if not users:
        logger.info("No users to send to.")
        return

    logger.info("Sending to %d user(s)...", len(users))
    sent = 0

    for user in users:
        try:
            items = await get_last_digest(user["id"])
            if items:
                await send_digest_email(user, items)
                sent += 1
                logger.info("  Sent %d signals to %s", len(items), user["email"])
            else:
                logger.info("  No saved digest for %s, skipping", user["email"])
        except Exception:
            logger.exception("  Error sending to %s", user["email"])

    logger.info("Sent %d digests.", sent)


async def research_and_send(email: str | None = None) -> None:
    """Research + send in one pass (original behavior)."""
    from db import get_all_users, get_user_by_email, save_digest
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
                await save_digest(user["id"], items)
                logger.info("  Sent digest to %s (%d items)", user["email"], len(items))
            else:
                logger.info("  No signals found for %s", user["email"])
        except Exception:
            logger.exception("  Error processing %s", user["email"])

    logger.info("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Scoop digest pipeline")
    parser.add_argument("--email", help="Process a specific user")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--research-only", action="store_true", help="Research and save, no email")
    mode.add_argument("--send-only", action="store_true", help="Send last saved digest, no research")
    args = parser.parse_args()

    if args.research_only:
        asyncio.run(research(args.email))
    elif args.send_only:
        asyncio.run(send(args.email))
    else:
        asyncio.run(research_and_send(args.email))
