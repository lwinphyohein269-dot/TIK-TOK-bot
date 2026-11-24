import logging
import sqlite3
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters


# Database Setup
def init_db():
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute('''

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF</em> NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER,
            message_text TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    conn.commit()
    conn.close()


# Log User and Message
def save_user_and_message(user_id, username, message_text):
    conn = sqlite3.connect('bot_database.db')
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO users VALUES (?, ?)", (user_id, username))
    c.execute("INSERT INTO messages (user_id, message_text) VALUES (?, ?)", (user_id, message_text))
    conn.commit()
    conn.close()


# Bot Handlers
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_and_message(
        user.id, user.username, update.message.text
    )
    await update.message.reply_text(
        f'မင်္ဂလာပါ {user.first_name} ! Database ထဲ မှတ်သားပြီးပါပြီ။'
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user_and_message(
        user.id, user.username, update.message.text
    )
    await update.message.reply_text(update.message.text)


if __name__ == '__main__':
    init_db()

    # Proxy မပါဘဲ တိုက်ရိုက်ချိတ်ဆက်ခြင်း (VPN ဖွင့်ထားရန်)
    application = ApplicationBuilder().token(
        '9128977384:AAEh0kIVrqIk1N2-JbvCdUmWx5xcBBsfeU'
    ).build()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(
        filters.TEXT & (~filters.COMMAND), echo
    )

    application.add_handler(start_handler)
    application.add_handler(echo_handler)

    application.run_polling()
