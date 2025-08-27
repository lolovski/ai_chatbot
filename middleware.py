# file: middleware.py

import time
import logging
from typing import Callable, Awaitable, Any, Dict

from aiogram import BaseMiddleware
from aiogram.types import Update, Message

from core import settings

# --- Конфиг ---
ADMIN_ID = settings.telegram_id
MIN_INTERVAL = 1.0  # минимум секунд между сообщениями
DAILY_LIMIT = 200  # сколько сообщений в день можно отправить
COOLDOWN_AFTER_LIMIT = 180  # сколько секунд ждать после превышения лимита

# user_id -> { "last_time": float, "daily_count": int, "day_timestamp": str }
user_limits: dict[int, dict] = {}


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

        now = time.time()
        today = time.strftime("%Y-%-m-%d")

        user_stats = user_limits.setdefault(user_id, {
            "last_time": 0.0,
            "daily_count": 0,
            "day_timestamp": "1970-01-01"
        })

        if user_stats["day_timestamp"] != today:
            user_stats["day_timestamp"] = today
            user_stats["daily_count"] = 0

        # 1. Проверка минимального интервала. ЭТО КЛЮЧЕВОЕ ИЗМЕНЕНИЕ.
        if now - user_stats["last_time"] < MIN_INTERVAL:
            if isinstance(message, Message):
                await message.answer("⏱ Пожалуйста, не так быстро 🙏")
            return

        # Сразу обновляем время, чтобы заблокировать следующие быстрые запросы
        user_stats["last_time"] = now

        # 2. Проверка дневного лимита
        if user_stats["daily_count"] >= DAILY_LIMIT:
            # Используем now, так как last_time уже обновлено
            if now - user_stats["last_time"] < COOLDOWN_AFTER_LIMIT and user_stats["daily_count"] > DAILY_LIMIT:
                if isinstance(message, Message):
                    await message.answer("📵 Вы достигли дневного лимита сообщений. Подождите немного ⏳")
                return

        # Вызываем следующий обработчик
        result = await handler(event, data)

        # Увеличиваем счетчик только после успешной обработки
        user_stats["daily_count"] += 1

        return result