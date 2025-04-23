from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.types import Message, BufferedInputFile, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from io import BytesIO

from database import db
from models import AuthStates
from config import ADMIN_IDS
from utils.keyboards import get_start_keyboard, get_main_keyboard, get_admin_keyboard
from utils.captcha import generate_captcha_text, generate_captcha_image
from utils.helpers import send_error_message, send_success_message

# Создаем роутер для аутентификации
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start"""
    # Генерация капчи
    captcha_text = generate_captcha_text()
    captcha_image = generate_captcha_image(captcha_text)
    
    await state.update_data(captcha_text=captcha_text)
    
    await message.answer(
        "👋 Добро пожаловать в бот для управления ссылками!\n\n"
        "Для начала пройдите проверку, введя текст с картинки:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # В aiogram 3.x для отправки байтов используем BufferedInputFile вместо FSInputFile
    await message.answer_photo(
        BufferedInputFile(captcha_image, filename="captcha.png")
    )
    await state.set_state(AuthStates.waiting_for_captcha)

@router.message(Command("login"))
@router.message(F.text == "🔑 Авторизоваться")
async def cmd_login(message: Message, state: FSMContext):
    """Начало процесса авторизации"""
    await message.answer("Пожалуйста, введите ваш логин:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AuthStates.waiting_for_username)

@router.message(AuthStates.waiting_for_captcha)
async def process_captcha(message: Message, state: FSMContext):
    """Проверка капчи и запрос логина"""
    user_input = message.text.strip().upper()
    user_data = await state.get_data()
    captcha_text = user_data.get('captcha_text')
    
    if user_input != captcha_text:
        await send_error_message(message, "Неверный код с картинки. Начните сначала: /start", reply_markup=get_start_keyboard())
        await state.clear()
        return
    
    await message.answer("Пожалуйста, введите ваш логин:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AuthStates.waiting_for_username)

@router.message(AuthStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    """Обработка ввода имени пользователя"""
    username = message.text.strip()
    await state.update_data(username=username)
    
    await message.answer("Теперь введите пароль:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AuthStates.waiting_for_password)

@router.message(AuthStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    """Обработка ввода пароля и завершение авторизации"""
    password = message.text.strip()
    user_data = await state.get_data()
    username = user_data.get('username')
    
    # Проверка учетных данных
    user_id = db.authenticate_user(username, password)
    
    if not user_id:
        await send_error_message(message, "Неверный логин или пароль. Попробуйте еще раз: /login", reply_markup=get_start_keyboard())
        await state.clear()
        return
    
    # Обновление Telegram ID пользователя
    db.update_telegram_id(user_id, message.from_user.id)
    
    is_admin = message.from_user.id in ADMIN_IDS
    keyboard = get_admin_keyboard() if is_admin else get_main_keyboard()
    
    await message.answer(
        "✅ Успешный вход!\n\n"
        "Теперь вы можете:\n"
        "- Установить свою ссылку: /setlink\n"
        "- Посмотреть текущую ссылку: /mylink\n"
        "- Выйти из аккаунта: /logout",
        reply_markup=keyboard
    )
    await state.clear()

@router.message(Command("logout"))
@router.message(F.text == "🚪 Выйти")
async def cmd_logout(message: Message):
    """Выход из аккаунта"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await send_error_message(message, "Вы не авторизованы.", reply_markup=get_start_keyboard())
        return
    
    # Удаление привязки Telegram ID к аккаунту
    db.update_telegram_id(user[0], None)
    await message.answer("Вы успешно вышли из аккаунта.", reply_markup=get_start_keyboard())

def setup(dp: Dispatcher):
    """Регистрация обработчиков авторизации"""
    dp.include_router(router)