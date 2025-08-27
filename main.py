import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio.client import Redis

from core import settings
from middleware import AntiFloodMiddleware
from handlers import router


async def main():
    # Инициализация Redis
    redis_client = Redis(host=settings.redis_host, port=settings.redis_port)
    storage = RedisStorage(redis=redis_client)

    # Инициализация бота и диспетчера
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    # Передаем клиент Redis в middleware через workflow_data
    dp.workflow_data["redis_client"] = redis_client
    dp.update.middleware.register(AntiFloodMiddleware())

    # Подключаем роутер с хендлерами
    dp.include_router(router)

    # Запускаем polling
    try:
        await dp.start_polling(bot)
    finally:
        await redis_client.close()
        await bot.session.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())