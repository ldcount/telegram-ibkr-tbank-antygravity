import asyncio
from app.aggregator import Aggregator
from app.config import Config
from app.utils.logging_redaction import setup_logging

# Mock config for verification if env vars are missing
# Config.BYBIT_API_KEY = "test"
# Config.BYBIT_API_SECRET = "test"


async def verify():
    logger = setup_logging()
    logger.info("Starting verification...")

    aggregator = Aggregator()
    summary = aggregator.get_portfolio_summary()

    print("\n--- Summary Data ---")
    print(summary)

    msg = aggregator.format_message(summary)
    print("\n--- Formatted Message ---")
    print(msg)

    logger.info("Verification finished.")


if __name__ == "__main__":
    asyncio.run(verify())
