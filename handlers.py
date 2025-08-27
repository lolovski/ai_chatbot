import logging
from aiogram import Router, F, Bot
from aiogram.filters import CommandStart
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from api_client import SYSTEM_PROMPT, call_ai
from core import settings

router = Router()

# Храним историю по user_id
memory: dict[int, list[dict]] = {}


class UserForm(StatesGroup):
    waiting_for_contact = State()
    waiting_for_confirmation = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    memory[user_id].append({"role": "assistant", "content": "👋 Привет! Я помогу вам подобрать решение. Хотите узнать больше?"})

    kb = ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[[KeyboardButton(text="Да, интересно")]]
    )

    await message.answer("👋 Привет! Я помогу вам подобрать решение. Хотите узнать больше?", reply_markup=kb)


@router.message(F.text == 'Оставить заявку')
async def form_handler(message: Message, state: FSMContext):
    await message.answer(
        '📋 Чтобы оформить заявку, пришлите, пожалуйста, ваш телефон или @username. Мы свяжемся в течение часа.')
    await state.set_state(UserForm.waiting_for_contact)


@router.message(UserForm.waiting_for_contact)
async def form_data_handler(message: Message, bot: Bot):
    text = message.text
    await message.answer(
        f'Спасибо! Мы получили ваш контакт {text} и скоро свяжемся с вами для уточнения деталей. Если возникнут вопросы — пишите, будем рады помочь!')
    await bot.send_message(
        text=f'Пользователь {message.from_user.id} отправил заявку. Контакты: {text}',
        chat_id=settings.telegram_id
    )


@router.message()
async def handle_message(message: Message):
    user_id = message.from_user.id

    if user_id not in memory:
        memory[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    history = memory[user_id]
    history.append({"role": "user", "content": message.text})

    data = await call_ai(user_id, history)
    reply_text = data.get("reply", "Ошибка ответа")
    buttons = data.get("buttons", [])

    if buttons:
        kb = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[[KeyboardButton(text=b)] for b in buttons])
        await message.answer(reply_text, reply_markup=kb, parse_mode="HTML")
    else:
        await message.answer(reply_text, parse_mode="HTML")

    history.append({"role": "assistant", "content": reply_text})
