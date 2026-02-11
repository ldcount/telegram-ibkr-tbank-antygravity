import logging
from app.config import Config
from app.utils.logging_redaction import setup_logging
from app.telegram_client import TelegramBot

# Setup logging
logger = setup_logging()


def main():
    try:
        Config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        # Continue if just missing keys but still want to run status?
        # Probably better to crash for now so user fixes it.
        # But for development we might want to proceed.

    bot = TelegramBot()
    bot.run()


if __name__ == "__main__":
    main()
