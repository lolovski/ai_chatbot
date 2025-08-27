import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from api_client import SYSTEM_PROMPT, call_ai
from core import settings

router = Router()


# Определяем состояния FSM
class ChatStates(StatesGroup):
    chatting = State()  # Основное состояние диалога
    waiting_for_contact = State()  # Состояние ожидания контакта для заявки


# --- Вспомогательная функция для отправки ответа от AI ---
async def send_ai_response(message: Message, text: str, buttons: list):
    builder = InlineKeyboardBuilder()
    for button_text in buttons:
        # Специальный callback_data для кнопки "Оставить заявку"
        callback_data = "leave_application" if "заявку" in button_text.lower() else button_text
        builder.add(InlineKeyboardButton(text=button_text, callback_data=callback_data))

    # Располагаем кнопки по одной в строке для лучшей читаемости
    builder.adjust(1)

    await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")


# --- Хендлеры ---

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(ChatStates.chatting)

    # Инициализируем историю и сразу делаем первый вызов AI для приветствия
    history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "/start"}
    ]

    data = await call_ai(user_id, history)
    reply_text = data.get("reply", "Здравствуйте! 👋")
    buttons = data.get("buttons", [])

    history.append({"role": "assistant", "content": reply_text})
    await state.update_data(history=history)

    await send_ai_response(message, reply_text, buttons)


@router.callback_query(F.data == "leave_application")
async def form_start_handler(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        '📋 Чтобы оформить заявку, пришлите, пожалуйста, ваш телефон или @username. Мы свяжемся в течение часа.'
    )
    await state.set_state(ChatStates.waiting_for_contact)
    await callback.answer()


@router.message(ChatStates.waiting_for_contact)
async def form_data_handler(message: Message, state: FSMContext, bot: Bot):
    contact_info = message.text
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"

    await message.answer(
        f'Спасибо! Мы получили ваш контакт «{contact_info}» и скоро свяжемся с вами для уточнения деталей. ✅'
    )
    # Отправляем уведомление администратору
    await bot.send_message(
        chat_id=settings.telegram_id,
        text=f"🔔 Новая заявка!\n\nПользователь: {user_info}\nКонтакты: {contact_info}"
    )
    # Возвращаем пользователя в основной диалог
    await state.set_state(ChatStates.chatting)


# Обработчик текстовых сообщений от пользователя
@router.message(ChatStates.chatting)
async def handle_text_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_text = message.text

    fsm_data = await state.get_data()
    history = fsm_data.get("history", [])

    # Безопасная инициализация истории, если она пуста
    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]

    history.append({"role": "user", "content": user_text})

    data = await call_ai(user_id, history)
    reply_text = data.get("reply", "Извините, произошла ошибка.")
    buttons = data.get("buttons", [])

    history.append({"role": "assistant", "content": reply_text})
    await state.update_data(history=history)

    await send_ai_response(message, reply_text, buttons)


# Обработчик нажатий на Inline-кнопки
@router.callback_query(ChatStates.chatting)
async def handle_callback_query(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    button_text = callback.data  # Текст кнопки становится "сообщением" пользователя

    # Отвечаем на callback, чтобы убрать "часики"
    await callback.answer()

    fsm_data = await state.get_data()
    history = fsm_data.get("history", [])

    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]

    history.append({"role": "user", "content": button_text})

    data = await call_ai(user_id, history)
    reply_text = data.get("reply", "Извините, произошла ошибка.")
    buttons = data.get("buttons", [])

    history.append({"role": "assistant", "content": reply_text})
    await state.update_data(history=history)

    await send_ai_response(callback.message, reply_text, buttons)