
import os
import logging
import sqlite3
import asyncio

from datetime import timedelta
from telegram import Update
from telegram.error import RetryAfter, TimedOut, NetworkError

from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    AIORateLimiter,
    filters
)

DB_NAME = "bot_database.db"


# Database Setup
def init_db():
    with sqlite3.connect(DB_NAME, timeout=30) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message_text TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()


# Save User and Message
def save_user_and_message(user_id, username, message_text):
    with sqlite3.connect(DB_NAME, timeout=30) as conn:
        conn.execute("PRAGMA foreign_keys=ON")

        conn.execute("""
            INSERT INTO users (user_id, username)
            VALUES (?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET username = excluded.username
        """, (user_id, username))

        conn.execute("""
            INSERT INTO messages (user_id, message_text)
            VALUES (?, ?)
        """, (user_id, message_text))

        conn.commit()


# Logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# RetryAfter Safe Message Sender
async def safe_reply(message, text, max_retries=5):

    for attempt in range(max_retries + 1):
        try:
            await message.reply_text(text)
            return True

        except RetryAfter as error:

            delay = error.retry_after

            if isinstance(delay, timedelta):
                delay = delay.total_seconds()

            wait_time = float(delay) + 1

            logger.warning(
                f"Rate limit reached. "
                f"Waiting {wait_time} seconds."
            )

            if attempt == max_retries:
                raise

            await asyncio.sleep(wait_time)

    return False


# Start Command
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    await asyncio.to_thread(
        save_user_and_message,
        user.id,
        user.username,
        message.text
    )

    await safe_reply(
        message,
        f"မင်္ဂလာပါ {user.first_name}!\n"
        "Database ထဲ မှတ်သားပြီးပါပြီ။"
    )


# Echo Handler
async def echo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.text:
        return

    await asyncio.to_thread(
        save_user_and_message,
        user.id,
        user.username,
        message.text
    )

    await safe_reply(message, message.text)


# Global Error Handler
async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    error = context.error

    if isinstance(error, RetryAfter):
        logger.warning(
            f"Retry limit reached: {error.retry_after}"
        )

    elif isinstance(error, TimedOut):
        logger.warning("Telegram API request timed out.")

    elif isinstance(error, NetworkError):
        logger.warning("Telegram network connection error.")

    else:
        logger.error(
            "Unexpected error:",
            exc_info=error
        )


# Main Application
if __name__ == "__main__":

    init_db()

    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    if not TOKEN:
        raise RuntimeError("Bot token is missing.")

    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .rate_limiter(
            AIORateLimiter(
                overall_max_rate=20,
                overall_time_period=1,
                group_max_rate=15,
                group_time_period=60,
                max_retries=0
            )
        )
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            echo
        )
    )

    application.add_error_handler(error_handler)

    logger.info("Database initialized.")
    logger.info("Telegram Bot starting...")

    application.run_polling(
        bootstrap_retries=3
    )
