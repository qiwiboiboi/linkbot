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
    """Форматирование списка пользователей с выводом паролей"""
    if not users:
        return "Список пользователей пуст."
    
    # Для отображения списка пользователей нужно получить пароли
    from database import db
    
    report = "📊 Список всех пользователей:\n\n"
    for user_id, username, telegram_id, link in users:
        # Получаем данные пользователя включая пароль
        user_data = db.get_user_by_username(username)
        password = user_data[1] if user_data else "Не найден"  # user_data[1] - это пароль
        
        report += f"ID: {user_id} | Логин: {username}\n"
        report += f"   Пароль: {password}\n"
        report += f"   Статус: {'✅ Авторизован' if telegram_id else '❌ Не авторизован'}\n"
        report += f"   Информация: {link or '—'}\n\n"
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