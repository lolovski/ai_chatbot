import time
import logging
from typing import Callable, Awaitable, Any, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update, Message

from core import settings

# === Конфиг ===
ADMIN_ID = settings.telegram_id        # сюда подставь свой Telegram ID
MIN_INTERVAL = 1.0          # минимум секунд между сообщениями
DAILY_LIMIT = 200           # сколько сообщений в день можно отправить
COOLDOWN_AFTER_LIMIT = 180  # сколько секунд ждать после превышения лимита

# user_id -> { "last_time": float, "count": int, "day": str }
user_limits: dict[int, dict] = {}


class AntiFloodMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        message: Message | None = getattr(event, "message", None)
        if not message:
            return await handler(event, data)

        user_id = message.from_user.id
        now = time.time()
        day = time.strftime("%Y-%m-%d")

        # Админ без ограничений
        if user_id == ADMIN_ID:
            return await handler(event, data)

        stats = user_limits.setdefault(user_id, {"last_time": 0.0, "count": 0, "day": day})

        # Сброс счётчика в новый день
        if stats["day"] != day:
            stats["day"] = day
            stats["count"] = 0

        # Проверка минимального интервала
        if now - stats["last_time"] < MIN_INTERVAL:
            await message.answer("⏱ Пожалуйста, не так быстро 🙏")
            return

        # Проверка дневного лимита
        if stats["count"] >= DAILY_LIMIT:
            if now - stats["last_time"] < COOLDOWN_AFTER_LIMIT:
                await message.answer("📵 Вы достигли дневного лимита сообщений. Подождите немного ⏳")
                return
            else:
                stats["count"] = DAILY_LIMIT  # не сбрасываем полностью, но ждём cooldown

        # Обновление статистики
        stats["last_time"] = now
        stats["count"] += 1
        user_limits[user_id] = stats

        return await handler(event, data)
