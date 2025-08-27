# file: main.py

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from core import settings
from middleware import AntiFloodMiddleware # Убрали setup_database
from handlers import router


async def main():
    # Инициализируем хранилище в памяти для FSM
    storage = MemoryStorage()

    # Инициализация бота и диспетчера
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    # Регистрируем middleware без параметров
    dp.update.middleware.register(AntiFloodMiddleware())

    # Подключаем роутер с хендлерами
    dp.include_router(router)

    # Запускаем polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())