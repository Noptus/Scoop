"""
One-time test: send a Scoop digest to archange618@gmail.com
with news about Nike, Apple, SAP, Airbus for selling Solace Agent Mesh.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

EMAIL = "archange618@gmail.com"
PRODUCT = "Solace Agent Mesh"
COMPANIES = ["Nike", "Apple", "SAP", "Airbus"]


async def main() -> None:
    from db import create_user, get_user_by_email
    from digest import generate_digest_for_user
    from send_email import send_digest_email

    # Ensure user exists
    user = await get_user_by_email(EMAIL)
    if not user:
        logger.info("Creating test user %s...", EMAIL)
        user = await create_user(EMAIL, PRODUCT, COMPANIES)
        # Re-fetch to get companies expanded
        user = await get_user_by_email(EMAIL)

    logger.info("User: %s (tracking %d companies)", user["email"], len(user.get("companies", [])))

    # Generate digest
    logger.info("Generating digest for %s...", PRODUCT)
    items = await generate_digest_for_user(user)

    if not items:
        logger.info("No signals found. Try again later.")
        return

    logger.info("Got %d signals. Sending email...", len(items))

    # Send
    await send_digest_email(user, items)
    logger.info("Email sent to %s!", EMAIL)


if __name__ == "__main__":
    asyncio.run(main())
