"""
Generate a Scoop demo signal for a specific company.
Used for LinkedIn outreach — run this to get a compelling signal
you can paste into a DM.

Usage:
  python demo_signal.py "Datadog" "observability platform"
  python demo_signal.py "Snowflake" "cloud data platform"
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from digest import generate_digest_preview

logger = logging.getLogger(__name__)


async def main() -> None:
    if len(sys.argv) < 3:
        logger.error("Usage: python demo_signal.py <company> <what_prospect_sells>")
        logger.error('Example: python demo_signal.py "Datadog" "observability platform"')
        sys.exit(1)

    company = sys.argv[1]
    product = sys.argv[2]

    logger.info("Generating signal for %s (prospect sells: %s)...", company, product)
    items = await generate_digest_preview([company], product)

    if not items:
        logger.info("No signals found. Try a different company.")
        return

    for item in items:
        logger.info("[%s] %s", item["tag"], item["company"])
        logger.info("%s", item["headline"])
        logger.info("Why this matters: %s", item["why"])
        if item.get("suggested_action"):
            logger.info("-> %s", item["suggested_action"])

    # Also print a ready-to-paste LinkedIn version
    item = items[0]
    logger.info("--- LINKEDIN READY ---")
    logger.info(
        "I ran a quick scan on %s:\n\n%s\n\n%s\n\n"
        "This is what Scoop sends every Monday for your top accounts. "
        "Free, 2 min setup: https://noptus.github.io/scoop",
        item["company"],
        item["headline"],
        item["why"],
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    asyncio.run(main())
