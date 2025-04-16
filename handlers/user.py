# handlers/user.py
import logging
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from database import db
from models import LinkStates
from config import CHANNEL_ID

logger = logging.getLogger(__name__)

async def cmd_set_link(message: types.Message):
    """Обработчик команды /setlink"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Вы не авторизованы. Используйте /login")
        return
    
    await message.answer(
        "Пожалуйста, введите вашу ссылку или текст.\n"
        "Это может быть название сервиса, домен или любой другой текст."
    )
    await LinkStates.waiting_for_link.set()

async def process_link(message: types.Message, state: FSMContext):
    """Обработка ввода ссылки"""
    link = message.text.strip()
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Вы не авторизованы. Используйте /login")
        await state.finish()
        return
    
    # Обновление ссылки в базе данных
    db.update_link(user[0], link)
    
    await message.answer(f"✅ Ваша ссылка успешно обновлена: {link}")
    
    # Отправка уведомления в канал
    # Будем отправлять уведомление из основного файла бота
    # или создадим отдельную функцию для этого
    
    await state.finish()
    
    # Возвращаем информацию для отправки уведомления в канал
    return {
        "username": user[1],
        "link": link
    }

async def cmd_my_link(message: types.Message):
    """Обработчик команды /mylink"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("❌ Вы не авторизованы. Используйте /login")
        return
    
    link = user[2]
    
    if link:
        await message.answer(f"🔗 Ваша текущая ссылка: {link}")
    else:
        await message.answer(
            "У вас еще нет сохраненной ссылки.\n"
            "Используйте /setlink чтобы добавить ссылку."
        )

def register_user_handlers(dp: Dispatcher):
    """Регистрация обработчиков пользователя"""
    dp.register_message_handler(cmd_set_link, Command("setlink"))
    dp.register_message_handler(process_link, state=LinkStates.waiting_for_link)
    dp.register_message_handler(cmd_my_link, Command("mylink"))