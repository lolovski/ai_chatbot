import time
from typing import Callable, Awaitable, Any, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update, Message
from redis.asyncio.client import Redis

from core import settings

# === Конфиг ===
ADMIN_ID = settings.telegram_id
MIN_INTERVAL = 1.0  # Минимум секунд между сообщениями
DAILY_LIMIT = 200  # Сообщений в день на пользователя
COOLDOWN_AFTER_LIMIT = 180  # Секунд блокировки после превышения лимита


class AntiFloodMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
            event: Update,
            data: Dict[str, Any],
    ) -> Any:
        message: Message | None = getattr(event, "message", None) or getattr(event, "callback_query", None)
        if not message:
            return await handler(event, data)

        user_id = message.from_user.id
        if user_id == ADMIN_ID:
            return await handler(event, data)

        redis: Redis = data["redis_client"]

        # Ключи для Redis
        key_last_time = f"antiflood:last_time:{user_id}"
        key_daily_count = f"antiflood:daily_count:{user_id}"
        key_cooldown = f"antiflood:cooldown:{user_id}"

        # 1. Проверка на cooldown
        if await redis.get(key_cooldown):
            if isinstance(message, Message):
                await message.answer("📵 Вы достигли дневного лимита. Попробуйте снова через несколько минут ⏳")
            return

        # 2. Проверка минимального интервала
        last_time = await redis.get(key_last_time)
        if last_time and time.time() - float(last_time) < MIN_INTERVAL:
            if isinstance(message, Message):
                await message.answer("⏱ Пожалуйста, не так быстро 🙏")
            return

        await redis.set(key_last_time, time.time(), ex=int(MIN_INTERVAL) + 1)

        # 3. Проверка дневного лимита
        daily_count_raw = await redis.get(key_daily_count)
        daily_count = int(daily_count_raw) if daily_count_raw else 0

        if daily_count >= DAILY_LIMIT:
            await redis.set(key_cooldown, 1, ex=COOLDOWN_AFTER_LIMIT)
            if isinstance(message, Message):
                await message.answer("📵 Вы достигли дневного лимита. Попробуйте снова через несколько минут ⏳")
            return

        # Инкремент счетчика и установка TTL до конца дня
        p = redis.pipeline()
        p.incr(key_daily_count)
        if daily_count == 0:
            # TTL до полуночи
            seconds_until_midnight = 86400 - (int(time.time()) % 86400)
            p.expire(key_daily_count, seconds_until_midnight)
        await p.execute()

        return await handler(event, data)