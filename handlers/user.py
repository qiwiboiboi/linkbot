import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from database import db
from models import LinkStates
from config import ADMIN_IDS
from utils.keyboards import get_main_keyboard, get_admin_keyboard, get_start_keyboard, get_cancel_keyboard
from utils.helpers import send_error_message, send_success_message, cancel_state

async def check_auth(message: types.Message) -> bool:
    """Проверка авторизации пользователя"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await send_error_message(message, "Вы не авторизованы. Используйте /login", reply_markup=get_start_keyboard())
        return False
    return True

async def cmd_set_link(message: types.Message):
    """Обработчик команды /setlink"""
    if not await check_auth(message):
        return
    
    await message.answer(
        "Пожалуйста, введите вашу ссылку или текст.\n"
        "Это может быть название сервиса, домен или любой другой текст.",
        reply_markup=get_cancel_keyboard()
    )
    await LinkStates.waiting_for_link.set()

async def process_link(message: types.Message, state: FSMContext):
    """Обработка ввода ссылки"""
    if await cancel_state(message, state):
        return
        
    link = message.text.strip()
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await send_error_message(message, "Вы не авторизованы. Используйте /login")
        await state.finish()
        return
    
    # Обновление ссылки в базе данных
    db.update_link(user[0], link)
    
    # После отмены или обновления ссылки показываем соответствующую клавиатуру
    keyboard = get_admin_keyboard() if message.from_user.id in ADMIN_IDS else get_main_keyboard()
    await send_success_message(message, f"Ваша ссылка успешно обновлена: {link}")
    await message.answer("Выберите действие:", reply_markup=keyboard)
    await state.finish()
    
    # Возвращаем информацию для отправки уведомления в канал
    return {
        "username": user[1],
        "link": link
    }

async def cmd_my_link(message: types.Message):
    """Обработчик команды /mylink"""
    if not await check_auth(message):
        return
    
    user = db.get_user_by_telegram_id(message.from_user.id)
    link = user[2]
    # Показываем соответствующую клавиатуру в зависимости от роли пользователя
    keyboard = get_admin_keyboard() if message.from_user.id in ADMIN_IDS else get_main_keyboard()

    if link:
        await message.answer(f"🔗 Ваша текущая ссылка: {link}")
    else:
        await message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте /setlink чтобы добавить ссылку.")
    
    await message.answer("Выберите действие:", reply_markup=keyboard)

def register_user_handlers(dp: Dispatcher):
    """Регистрация обработчиков пользователя"""
    # Команды управления ссылкой
    dp.register_message_handler(cmd_set_link, Command("setlink"))
    dp.register_message_handler(cmd_set_link, text="🔄 Добавить ссылку")
    dp.register_message_handler(cmd_my_link, Command("mylink"))
    dp.register_message_handler(cmd_my_link, text="🔗 Моя ссылка")
    
    # Состояния установки ссылки
    dp.register_message_handler(process_link, state=LinkStates.waiting_for_link)
