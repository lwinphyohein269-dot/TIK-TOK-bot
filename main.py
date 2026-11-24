
import os
import logging
import sqlite3

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters
)

# Database Configuration
DB_NAME = "bot_database.db"

# Database Setup
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

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
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
            )
        """)

        conn.commit()


# Save User and Message
def save_user_and_message(user_id, username, message_text):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("PRAGMA foreign_keys = ON")

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


# Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Start Command
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message:
        return

    save_user_and_message(
        user.id,
        user.username,
        message.text
    )

    await message.reply_text(
        f"မင်္ဂလာပါ {user.first_name}!\n"
        "Database ထဲတွင် မှတ်တမ်းတင်ပြီးပါပြီ။"
    )


# Echo Message
async def echo(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    user = update.effective_user
    message = update.effective_message

    if not user or not message or not message.text:
        return

    save_user_and_message(
        user.id,
        user.username,
        message.text
    )

    await message.reply_text(message.text)


# Error Handler
async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):
    logger.error(
        "Bot error:",
        exc_info=context.error
    )


# Run Bot
if __name__ == "__main__":
    init_db()

    TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    if not TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is missing."
        )

    application = (
        ApplicationBuilder()
        .token(TOKEN)
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

    print("Database initialized successfully.")
    print("Telegram Bot is running...")

    application.run_polling()
