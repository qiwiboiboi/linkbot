from aiogram import types
from aiogram.fsm.context import FSMContext
from config import ADMIN_IDS
from utils.keyboards import get_admin_keyboard, get_start_keyboard

async def check_admin(message: types.Message) -> bool:
    """Проверка на администратора"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.", reply_markup=get_start_keyboard())
        return False
    return True

async def cancel_state(message: types.Message, state: FSMContext) -> bool:
    """Обработка отмены операции"""
    if message.text == "❌ Отмена":
        is_admin = message.from_user.id in ADMIN_IDS
        keyboard = get_admin_keyboard() if is_admin else get_start_keyboard()
        await message.answer("Действие отменено.", reply_markup=keyboard)
        await state.clear()
        return True
    return False

def format_user_list(users: list) -> str:
    """Форматирование списка пользователей"""
    if not users:
        return "Список пользователей пуст."
    
    report = "📊 Список всех пользователей:\n\n"
    for user_id, username, telegram_id, link in users:
        report += f"ID: {user_id} | Логин: {username}\n"
        report += f"   Профиль: @{username}\n"
        report += f"   Ссылка: {link or '—'}\n\n"
    return report

async def send_error_message(message: types.Message, error_text: str, reply_markup=None):
    """Отправка сообщения об ошибке"""
    if reply_markup is None:
        is_admin = message.from_user.id in ADMIN_IDS
        reply_markup = get_admin_keyboard() if is_admin else get_start_keyboard()
    await message.answer(f"❌ {error_text}", reply_markup=reply_markup)

async def send_success_message(message: types.Message, success_text: str, reply_markup=None):
    """Отправка сообщения об успехе"""
    if reply_markup is None:
        is_admin = message.from_user.id in ADMIN_IDS
        reply_markup = get_admin_keyboard() if is_admin else get_start_keyboard()
    await message.answer(f"✅ {success_text}", reply_markup=reply_markup)