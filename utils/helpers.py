# Обновление utils/helpers.py

from asyncio.log import logger
from aiogram import types
from aiogram.fsm.context import FSMContext
from config import ADMIN_IDS
from utils.keyboards import get_admin_keyboard, get_start_keyboard, get_admin_inline_keyboard

async def check_admin(message: types.Message) -> bool:
    """Проверка на администратора"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=get_start_keyboard())
        return False
    return True

async def cancel_state(message: types.Message, state: FSMContext) -> bool:
    """Обработка отмены операции"""
    if message.text == "❌ Отмена":
        await state.clear()  # Clear state first to ensure no more state handlers run
        
        # Проверяем, авторизован ли пользователь
        from database import db  # Import here to avoid circular imports
        from aiogram.types import ReplyKeyboardRemove
        user = db.get_user_by_telegram_id(message.from_user.id)
        
        if user:
            # Пользователь авторизован
            is_admin = message.from_user.id in ADMIN_IDS
            
            if is_admin:
                # Для админа отправляем сообщение с кнопками администрирования
                await message.answer(
                    "Действие отменено.", 
                    reply_markup=get_admin_keyboard()
                )
            else:
                # Для обычного авторизованного пользователя - сначала убираем reply клавиатуру
                await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())
                # Затем отправляем инлайн клавиатуру
                from utils.keyboards import get_main_keyboard
                await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        else:
            # Если не авторизован - сначала убираем reply клавиатуру, затем отправляем инлайн кнопку
            from utils.keyboards import get_start_button
            await message.answer("Действие отменено.", reply_markup=ReplyKeyboardRemove())
            await message.answer("Нажмите Старт для начала работы:", reply_markup=get_start_button())
        
        return True
    return False

def format_user_list(users: list) -> str:
    """Форматирование списка пользователей - используется только для коротких списков"""
    if not users:
        return "Список пользователей пуст."
    
    # Для отображения более 5 пользователей используем send_user_list_in_parts
    if len(users) > 5:
        return f"📊 Найдено пользователей: {len(users)}\n\n⚠️ Используется разбивка на части."
    
    # Для короткого списка возвращаем базовую информацию
    report = f"📊 Пользователи ({len(users)}):\n\n"
    for user_data in users:
        try:
            user_id = user_data[0]
            username = user_data[1]
            telegram_id = user_data[2] if len(user_data) > 2 else None
            full_name = user_data[4] if len(user_data) > 4 else None
            
            if full_name and full_name.strip():
                display_name = f"{full_name} (@{username})"
            else:
                display_name = username
            
            report += f"🆔 {user_id}: {display_name}"
            if telegram_id:
                report += " ✅"
            else:
                report += " ❌"
            report += "\n"
            
        except Exception as e:
            logger.error(f"Error formatting user in short list: {e}")
            report += f"❌ Ошибка пользователя\n"
    
    return report

async def send_error_message(message: types.Message, error_text: str, reply_markup=None):
    """Отправка сообщения об ошибке"""
    if reply_markup is None:
        # Не отправляем клавиатуру автоматически
        await message.answer(f"❌ {error_text}")
    else:
        # Если указана конкретная клавиатура, используем ее
        await message.answer(f"❌ {error_text}", reply_markup=reply_markup)

async def send_success_message(message: types.Message, success_text: str, reply_markup=None):
    """Отправка сообщения об успехе"""
    if reply_markup is None:
        # Не отправляем клавиатуру автоматически
        await message.answer(f"✅ {success_text}")
    else:
        # Если указана конкретная клавиатура, используем ее
        await message.answer(f"✅ {success_text}", reply_markup=reply_markup)