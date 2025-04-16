# handlers/auth.py
from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from database import db
from models import AuthStates

async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Добро пожаловать в бот для управления ссылками!\n\n"
        "Для входа используйте команду /login\n"
        "После входа вы сможете управлять своей персональной ссылкой."
    )

async def cmd_login(message: types.Message):
    """Начало процесса авторизации"""
    await message.answer("Пожалуйста, введите ваш логин:")
    await AuthStates.waiting_for_username.set()

async def process_username(message: types.Message, state: FSMContext):
    """Обработка ввода имени пользователя"""
    username = message.text.strip()
    
    # Сохранение имени пользователя
    await state.update_data(username=username)
    
    await message.answer("Теперь введите пароль:")
    await AuthStates.waiting_for_password.set()

async def process_password(message: types.Message, state: FSMContext):
    """Обработка ввода пароля и завершение авторизации"""
    password = message.text.strip()
    user_data = await state.get_data()
    username = user_data.get('username')
    
    # Проверка учетных данных
    user_id = db.authenticate_user(username, password)
    
    if not user_id:
        await message.answer("❌ Неверный логин или пароль. Попробуйте еще раз: /login")
        await state.finish()
        return
    
    # Обновление Telegram ID пользователя
    db.update_telegram_id(user_id, message.from_user.id)
    
    await message.answer(
        f"✅ Успешный вход!\n\n"
        f"Теперь вы можете:\n"
        f"- Установить свою ссылку: /setlink\n"
        f"- Посмотреть текущую ссылку: /mylink\n"
        f"- Выйти из аккаунта: /logout"
    )
    await state.finish()

async def cmd_logout(message: types.Message):
    """Выход из аккаунта"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await message.answer("Вы не авторизованы.")
        return
    
    # Удаление привязки Telegram ID к аккаунту
    db.update_telegram_id(user[0], None)
    
    await message.answer("Вы успешно вышли из аккаунта.")

def register_auth_handlers(dp: Dispatcher):
    """Регистрация обработчиков авторизации"""
    dp.register_message_handler(cmd_start, Command("start"))
    dp.register_message_handler(cmd_login, Command("login"))
    dp.register_message_handler(process_username, state=AuthStates.waiting_for_username)
    dp.register_message_handler(process_password, state=AuthStates.waiting_for_password)
    dp.register_message_handler(cmd_logout, Command("logout"))