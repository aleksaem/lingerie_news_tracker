"""
Application entry point.

Initializes DB, registers handlers, starts aiogram polling.
"""

# TODO: import Bot, Dispatcher from aiogram
#       import init_db from db.session
#       import top_news_handler from bot.handlers.top_news
#       import settings from config


async def main():
    """
    Bootstrap sequence:
    1. init_db() — create tables
    2. Init Bot(token=settings.BOT_TOKEN)
    3. Init Dispatcher, register routers/handlers
    4. await dp.start_polling(bot)
    """
    # TODO: implement bootstrap
    raise NotImplementedError


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
