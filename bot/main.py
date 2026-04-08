import asyncio
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


async def main():
    from database.connection import init_db
    from aiogram import Bot, Dispatcher
    from bot.handlers import create_dp

    await init_db()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logging.error("TELEGRAM_BOT_TOKEN not set in .env")
        return

    bot = Bot(token=bot_token)
    dp = create_dp()

    logging.info("Bot started. Polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
