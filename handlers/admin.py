# handlers/admin.py
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from database import db
from config import ADMIN_IDS
from models import AddUserStates

async def cmd_admin(message: types.Message):
    """Обработчик команды /admin"""
    # Проверка, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    # Получение списка всех пользователей
    users = db.get_all_users()
    
    if not users:
        await message.answer("Список пользователей пуст.")
        return
    
    # Формирование отчета для администратора
    report = "📊 Список всех пользователей:\n\n"
    
    for i, (username, telegram_id, link) in enumerate(users, 1):
        report += f"{i}. Логин: {username}\n"
        
        # Вместо ID показываем ссылку на профиль, если ID есть
        if telegram_id:
            report += f"   Профиль: tg://user?id={telegram_id}\n"
        else:
            report += f"   Профиль: —\n"
            
        report += f"   Ссылка: {link or '—'}\n\n"
    
    # Добавляем информацию о команде создания пользователей
    report += "\nДля добавления нового пользователя используйте команду /adduser"
    
    await message.answer(report)

async def cmd_add_user(message: types.Message):
    """Обработчик команды /adduser для добавления нового пользователя"""
    # Проверка, является ли пользователь администратором
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к этой команде.")
        return
    
    await message.answer("Введите логин для нового пользователя:")
    await AddUserStates.waiting_for_username.set()

async def process_new_username(message: types.Message, state: FSMContext):
    """Обработка ввода логина для нового пользователя"""
    username = message.text.strip()
    
    # Проверяем, существует ли пользователь с таким логином
    user = db.get_user_by_username(username)
    if user:
        await message.answer(f"❌ Пользователь с логином '{username}' уже существует. Попробуйте другой логин.")
        return
    
    # Сохраняем логин в состоянии
    await state.update_data(username=username)
    
    await message.answer("Теперь введите пароль для нового пользователя:")
    await AddUserStates.waiting_for_password.set()

async def process_new_password(message: types.Message, state: FSMContext):
    """Обработка ввода пароля и создание нового пользователя"""
    password = message.text.strip()
    
    # Получаем данные из состояния
    user_data = await state.get_data()
    username = user_data.get('username')
    
    # Создаем нового пользователя в базе данных
    if db.add_user(username, password):
        await message.answer(f"✅ Пользователь '{username}' успешно создан с указанным паролем.\n\nЛогин: {username}\nПароль: {password}")
    else:
        await message.answer(f"❌ Не удалось создать пользователя. Возможно, логин '{username}' уже занят.")
    
    # Завершаем состояние
    await state.finish()

def register_admin_handlers(dp: Dispatcher):
    """Регистрация обработчиков администратора"""
    dp.register_message_handler(cmd_admin, Command("admin"))
    dp.register_message_handler(cmd_add_user, Command("adduser"))
    dp.register_message_handler(process_new_username, state=AddUserStates.waiting_for_username)
    dp.register_message_handler(process_new_password, state=AddUserStates.waiting_for_password)