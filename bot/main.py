import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)

# Separate conversation log
conv_logger = logging.getLogger("conversation")
conv_logger.setLevel(logging.INFO)
conv_handler = logging.FileHandler("logs/conversations.log", encoding="utf-8")
conv_handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
conv_logger.addHandler(conv_handler)


async def main():
    from database.connection import init_db
    from aiogram import Bot, Dispatcher
    from aiogram.types import Message
    from bot.handlers import create_dp

    await init_db()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logging.error("TELEGRAM_BOT_TOKEN not set in .env")
        return

    bot = Bot(token=bot_token)
    dp = create_dp()

    # Conversation logging middleware
    conv_logger = logging.getLogger("conversation")

    @dp.message.middleware
    async def log_conversation(handler, event: Message, data):
        user = event.from_user
        user_msg = event.text or event.caption or "[non-text]"
        conv_logger.info(f"USER [{user.id}] @{user.username or user.first_name}: {user_msg}")
        result = await handler(event, data)
        return result

    logging.info("Bot started. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
