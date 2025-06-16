from aiogram import Router, F, Bot, Dispatcher, types
from aiogram.types import Message, BufferedInputFile, ReplyKeyboardRemove, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from io import BytesIO
import os
import logging

logger = logging.getLogger(__name__)

from datetime import datetime
from database import db
from models import AuthStates, RegistrationStates
from config import ADMIN_IDS, BOT_NAME, get_welcome_message
from utils.keyboards import get_start_keyboard, get_main_keyboard, get_admin_keyboard, get_admin_inline_keyboard, get_auth_keyboard
from utils.captcha import generate_captcha_text, generate_captcha_image
from utils.helpers import send_error_message, send_success_message, cancel_state

# Создаем роутер для аутентификации
router = Router()

# Функция для создания клавиатуры с кнопкой "Старт" для неавторизованных пользователей
def get_start_button():
    kb = [
        [InlineKeyboardButton(text='🚀 Старт', callback_data='start_bot')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

@router.message(CommandStart())
@router.callback_query(F.data == "start_bot")
async def cmd_start(event: Message | types.CallbackQuery, state: FSMContext):
    """Обработчик команды /start и нажатия на кнопку Старт"""
    # Определяем, что это: сообщение или callback
    is_callback = isinstance(event, types.CallbackQuery)
    
    if is_callback:
        # Если это callback, то нужно ответить на него и получить сообщение
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        # Если это сообщение, то просто используем его
        message = event
        user_id = message.from_user.id
    
    # Проверяем, авторизован ли пользователь
    user = db.get_user_by_telegram_id(user_id)
    
    if user:  # Если пользователь уже авторизован
        is_admin = user_id in ADMIN_IDS
        
        # Отправляем приветственное сообщение
        await message.answer(f"С возвращением, {user[1]}! Чем могу помочь?")
        
        # Отображаем нужные клавиатуры
        if is_admin:
            # Для админа - обе клавиатуры
            await message.answer(
                "Управление ссылками:", 
                reply_markup=get_admin_inline_keyboard()
            )
            await message.answer(
                "Функции администрирования:", 
                reply_markup=get_admin_keyboard()
            )
        else:
            # Для обычного пользователя - только инлайн клавиатура
            await message.answer(
                "Выберите действие:", 
                reply_markup=get_main_keyboard()
            )
        
        return  # Завершаем обработку для авторизованных пользователей
    
    # Для неавторизованных пользователей сразу показываем капчу
    # Генерация капчи
    captcha_text = generate_captcha_text()
    captcha_image = generate_captcha_image(captcha_text)
    
    await state.update_data(captcha_text=captcha_text)
    
    await message.answer(
        "Для продолжения введите текст с картинки:",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # В aiogram 3.x для отправки байтов используем BufferedInputFile вместо FSInputFile
    await message.answer_photo(
        BufferedInputFile(captcha_image, filename="captcha.png")
    )
    await state.set_state(AuthStates.waiting_for_captcha)

@router.message(AuthStates.waiting_for_captcha)
async def process_captcha(message: Message, state: FSMContext):
    """Проверка капчи и предложение авторизации или регистрации"""
    user_input = message.text.strip().upper()
    user_data = await state.get_data()
    captcha_text = user_data.get('captcha_text')
    
    if user_input != captcha_text:
        await send_error_message(
            message, 
            "Неверный код с картинки. Начните сначала.",
            reply_markup=get_start_button()
        )
        await state.clear()
        return
    
    # После успешной проверки капчи предлагаем выбор
    await message.answer(
        "Капча пройдена успешно! Выберите действие:",
        reply_markup=get_auth_keyboard()
    )
    await state.clear()

@router.message(Command("register"))
@router.message(F.text == "📝 Регистрация")
async def cmd_register(message: Message, state: FSMContext):
    """Начало процесса регистрации"""
    await message.answer(
        "Придумайте логин для входа в систему:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationStates.waiting_for_username)

@router.message(RegistrationStates.waiting_for_username)
async def process_registration_username(message: Message, state: FSMContext):
    """Обработка ввода логина при регистрации"""
    username = message.text.strip()
    
    # Проверяем, не занят ли логин
    if db.get_user_by_username(username):
        await send_error_message(
            message,
            f"Логин '{username}' уже занят. Попробуйте другой."
        )
        return
    
    # Проверяем длину логина
    if len(username) < 3:
        await send_error_message(
            message,
            "Логин должен содержать минимум 3 символа."
        )
        return
    
    if len(username) > 20:
        await send_error_message(
            message,
            "Логин не должен превышать 20 символов."
        )
        return
    
    await state.update_data(username=username)
    await message.answer(
        "Отлично! Теперь придумайте пароль (минимум 6 символов):",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationStates.waiting_for_password)

@router.message(RegistrationStates.waiting_for_password)
async def process_registration_password(message: Message, state: FSMContext):
    """Обработка ввода пароля при регистрации"""
    password = message.text.strip()
    
    # Проверяем длину пароля
    if len(password) < 6:
        await send_error_message(
            message,
            "Пароль должен содержать минимум 6 символов."
        )
        return
    
    await state.update_data(password=password)
    await message.answer(
        "Подтвердите пароль, введите его еще раз:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationStates.waiting_for_password_confirm)

@router.message(RegistrationStates.waiting_for_password_confirm)
async def process_registration_password_confirm(message: Message, state: FSMContext, bot: Bot):
    """Подтверждение пароля и завершение регистрации"""
    password_confirm = message.text.strip()
    user_data = await state.get_data()
    username = user_data.get('username')
    password = user_data.get('password')
    
    # Проверяем совпадение паролей
    if password != password_confirm:
        await send_error_message(
            message,
            "Пароли не совпадают. Попробуйте еще раз."
        )
        await message.answer(
            "Введите пароль:",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationStates.waiting_for_password)
        return
    
    # Получаем полное имя пользователя из Telegram
    full_name = message.from_user.full_name
    
    # Создаем пользователя с полным именем
    if db.add_user(username, password, full_name):
        # Получаем ID созданного пользователя
        user_id = db.authenticate_user(username, password)
        
        # Привязываем Telegram ID с полным именем
        db.update_telegram_id(user_id, message.from_user.id, full_name)
        
        # Отправляем уведомление админам о новой регистрации
        await send_admin_notification_registration(bot, username, full_name, message.from_user.id)
        
        # Остальной код остается без изменений...
        await message.answer(
            f"✅ Регистрация успешно завершена!\n\n"
            f"Ваш логин: {username}\n"
            f"Ваш пароль: {password}\n\n"
            f"Сохраните эти данные для последующего входа."
        )
        
        # Теперь отправляем приветственное сообщение с логотипом
        logo_path = "assets/logo.jpg"
        
        if os.path.exists(logo_path):
            try:
                await message.answer_photo(
                    FSInputFile(logo_path),
                    caption=get_welcome_message(),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending welcome message with photo: {e}")
                await message.answer_photo(
                    FSInputFile(logo_path),
                    caption=get_welcome_message()
                )
        else:
            try:
                await message.answer(
                    get_welcome_message(),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending welcome message: {e}")
                await message.answer(get_welcome_message())
        
        # Определяем, является ли пользователь админом
        is_admin = message.from_user.id in ADMIN_IDS
        
        # Отправляем соответствующие клавиатуры
        if is_admin:
            await message.answer(
                "Управление ссылками:",
                reply_markup=get_admin_inline_keyboard()
            )
            await message.answer(
                "Функции администрирования:",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
        
        await state.clear()
    else:
        await send_error_message(
            message,
            "Произошла ошибка при регистрации. Попробуйте позже."
        )
        await state.clear()
    
@router.message(Command("login"))
@router.message(F.text == "🔑 Авторизоваться")
async def cmd_login(message: Message, state: FSMContext):
    """Начало процесса авторизации"""
    await message.answer("Введите ваш логин для входа:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AuthStates.waiting_for_username)

@router.message(AuthStates.waiting_for_username)
async def process_username(message: Message, state: FSMContext):
    """Обработка ввода имени пользователя"""
    username = message.text.strip()
    await state.update_data(username=username)
    
    await message.answer("Теперь введите пароль:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(AuthStates.waiting_for_password)

async def send_admin_notification(bot: Bot, username, user_full_name, user_id):
    """Отправка уведомления админу о новой авторизации"""
    try:
        notification_text = (
            f"🔔 Новая авторизация!\n\n"
            f"👤 Пользователь: {user_full_name}\n"
            f"🆔 Telegram ID: {user_id}\n"
            f"📝 Логин: {username}\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        # Отправляем уведомление всем админам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, notification_text)
                logger.info(f"Admin notification sent to {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")

async def send_admin_notification_registration(bot: Bot, username, user_full_name, user_id):
    """Отправка уведомления админу о новой регистрации"""
    try:
        notification_text = (
            f"🆕 Новая регистрация!\n\n"
            f"👤 Пользователь: {user_full_name}\n"
            f"🆔 Telegram ID: {user_id}\n"
            f"📝 Логин: {username}\n"
            f"⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        # Отправляем уведомление всем админам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, notification_text)
                logger.info(f"Admin notification sent to {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")
                
    except Exception as e:
        logger.error(f"Failed to send admin notification: {e}")

@router.message(AuthStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода пароля и завершение авторизации"""
    password = message.text.strip()
    user_data = await state.get_data()
    username = user_data.get('username')
    
    # Проверка учетных данных
    user_id = db.authenticate_user(username, password)
    
    if not user_id:
        await send_error_message(
            message, 
            "Неверный логин или пароль. Попробуйте еще раз."
        )
        # Return to username input state
        await message.answer("Введите ваш логин для входа:", reply_markup=ReplyKeyboardRemove())
        await state.set_state(AuthStates.waiting_for_username)
        return
    
    # Получаем полное имя пользователя из Telegram
    full_name = message.from_user.full_name
    
    # Обновление Telegram ID пользователя с полным именем
    db.update_telegram_id(user_id, message.from_user.id, full_name)
    
    # Отправляем уведомление админу о новой авторизации
    await send_admin_notification(bot, username, full_name, message.from_user.id)
    
    # Остальной код остается без изменений...
    await message.answer(
        f"✅ Успешный вход!\n\n"
        f"Добро пожаловать {full_name}!"
    )
    
    # Отправляем приветственное сообщение с логотипом
    logo_path = "assets/logo.jpg"
    
    if os.path.exists(logo_path):
        try:
            await message.answer_photo(
                FSInputFile(logo_path),
                caption=get_welcome_message(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending welcome message with photo: {e}")
            await message.answer_photo(
                FSInputFile(logo_path),
                caption=get_welcome_message()
            )
    else:
        try:
            await message.answer(
                get_welcome_message(),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Error sending welcome message: {e}")
            await message.answer(get_welcome_message())
    
    is_admin = message.from_user.id in ADMIN_IDS
    
    # Отправляем основные кнопки для работы со ссылками
    if is_admin:
        # Для админа: сначала отправляем инлайн-кнопки для работы со ссылками
        await message.answer(
            "Управление ссылками:",
            reply_markup=get_admin_inline_keyboard()
        )
        
        # Затем отправляем обычную клавиатуру с функциями администрирования
        await message.answer(
            "Функции администрирования:",
            reply_markup=get_admin_keyboard()
        )
    else:
        # Для обычного пользователя - просто инлайн-кнопки
        await message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()

@router.message(Command("logout"))
@router.message(F.text == "🚪 Выйти")
@router.callback_query(F.data == "logout")
async def cmd_logout(event: Message | types.CallbackQuery):
    """Выход из аккаунта"""
    # Определяем, что это: сообщение или callback
    is_callback = isinstance(event, types.CallbackQuery)
    
    if is_callback:
        # Если это callback, то нужно ответить на него и получить данные
        await event.answer()
        message = event.message
        user_id = event.from_user.id
    else:
        # Если это сообщение, то просто используем его
        message = event
        user_id = message.from_user.id
    
    user = db.get_user_by_telegram_id(user_id)
    
    if not user:
        text = "Вы не авторизованы."
        if is_callback:
            await message.answer(f"❌ {text}", reply_markup=get_start_button())
        else:
            await send_error_message(message, text, reply_markup=get_start_button())
        return
    
    # Удаление привязки Telegram ID к аккаунту
    db.update_telegram_id(user[0], None)
    
    # Отправляем сообщение о выходе и кнопку для перезапуска
    await message.answer(
        "Вы успешно вышли из аккаунта.",
        reply_markup=get_start_button()
    )

def setup(dp: Dispatcher):
    """Регистрация обработчиков авторизации"""
    dp.include_router(router)