import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from datetime import time, datetime
from app.config import Config
from app.aggregator import Aggregator

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        if not self.token:
            logger.warning("Telegram token not set.")
            return

        self.application = Application.builder().token(self.token).build()
        self.aggregator = Aggregator()

        # Add handlers
        self.application.add_handler(CommandHandler("status", self.status_command))

        # Add scheduled job
        if self.application.job_queue:
            # We want it to run at specific hours
            # Since job_queue.run_daily takes a 'time' object, we need multiple jobs or a custom trigger.
            # python-telegram-bot v20+ job_queue supports 'run_repeating' and 'run_once' easily.
            # 'run_daily' is good for one time a day.
            # We can use cron-like behavior if available, but PTB encapsulates APScheduler.
            # However, direct access to APScheduler is possible via job_queue.scheduler if needed,
            # but usually it's better to stick to PTB API if possible.
            # Or we can just schedule multiple daily jobs.

            # New Logic: run_repeating every POLL_INTERVAL_MINUTES
            # The job itself will check the time window.
            interval_sec = Config.POLL_INTERVAL_MINUTES * 60
            self.application.job_queue.run_repeating(
                self.scheduled_job,
                interval=interval_sec,
                first=10,
                chat_id=self.chat_id,
            )
            logger.info(
                f"Scheduled job every {Config.POLL_INTERVAL_MINUTES} minutes "
                f"({Config.WINDOW_START_HOUR}:00 - {Config.WINDOW_END_HOUR}:00)"
            )
        else:
            logger.warning("JobQueue not available.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        logger.info(
            f"Received /status from {update.effective_chat.id if update.effective_chat else 'unknown'}"
        )

        # Security check: only allow configured chat_id?
        # For now, let's assume we reply to whoever asked if they are in the chat or if we don't enforce strict ID.
        # But for privacy, usually we match ID.
        if str(update.effective_chat.id) != str(self.chat_id):
            await update.message.reply_text("Unauthorized access.")
            return

        await update.message.reply_text("Fetching data...")
        try:
            summary = self.aggregator.get_portfolio_summary()
            msg = self.aggregator.format_message(summary)
            await update.message.reply_text(msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text(f"Error fetching status: {e}")

    async def scheduled_job(self, context: ContextTypes.DEFAULT_TYPE):
        """Scheduled reporting."""

        # Check Time Window
        now = datetime.now(Config.get_timezone_obj())
        if not (Config.WINDOW_START_HOUR <= now.hour <= Config.WINDOW_END_HOUR):
            logger.info("Outside configured time window. Skipping report.")
            return

        chat_id = context.job.chat_id
        logger.info("Running scheduled report...")
        try:
            summary = self.aggregator.get_portfolio_summary()
            msg = self.aggregator.format_message(summary)
            await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML")
            logger.info("Scheduled report sent.")
        except Exception as e:
            logger.error(f"Error in scheduled job: {e}")

    def run(self):
        """Start the bot."""
        if not self.application:
            logger.error("Application not initialized.")
            return

        logger.info("Starting Telegram Bot polling...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
