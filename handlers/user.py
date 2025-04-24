from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from models import LinkStates
from config import ADMIN_IDS
from utils.keyboards import get_main_keyboard, get_admin_keyboard, get_start_keyboard, get_cancel_keyboard, get_admin_inline_keyboard
from utils.helpers import send_error_message, send_success_message, cancel_state

# Создаем роутер для пользовательских команд
router = Router()

async def check_auth(message: Message) -> bool:
    """Проверка авторизации пользователя по сообщению"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await send_error_message(message, "Вы не авторизованы. Используйте /login", reply_markup=get_start_keyboard())
        return False
    return True

async def check_auth_callback(callback: CallbackQuery) -> bool:
    """Проверка авторизации пользователя по callback-запросу"""
    user = db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.message.answer("❌ Вы не авторизованы. Используйте /login", reply_markup=get_start_keyboard())
        return False
    return True

@router.message(Command("setlink"))
@router.message(F.text == "🔄 Обновить")
async def cmd_set_link(message: Message, state: FSMContext):
    """Обработчик команды /setlink"""
    if not await check_auth(message):
        return
    
    await message.answer(
        "Введите ваши ссылки и/или текст.\n"
        "Это может быть название сервиса, домен или любой другой текст.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LinkStates.waiting_for_link)

@router.callback_query(F.data == "set_link")
async def callback_set_link(callback: CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопки изменения ссылки"""
    await callback.answer()
    
    if not await check_auth_callback(callback):
        return
    
    await callback.message.answer(
        "Пожалуйста, введите вашу ссылку или текст.\n"
        "Это может быть название сервиса, домен или любой другой текст.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LinkStates.waiting_for_link)

@router.message(LinkStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext):
    """Обработка ввода ссылки"""
    if await cancel_state(message, state):
        return
        
    link = message.text.strip()
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await send_error_message(message, "Вы не авторизованы. Используйте /login")
        await state.clear()
        return
    
    # Обновление ссылки в базе данных
    db.update_link(user[0], link)
    
    # После обновления ссылки показываем сообщение об успехе
    await send_success_message(message, f"Ваша ссылка успешно обновлена: {link}")
    
    # Показываем соответствующие кнопки в зависимости от роли пользователя
    is_admin = message.from_user.id in ADMIN_IDS
    if is_admin:
        
        # Затем обычную клавиатуру с функциями администрирования
        await message.answer(
            "Функции администрирования:",
            reply_markup=get_admin_keyboard()
        )
    else:
        # Для обычного пользователя только инлайн-кнопки
        await message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
    
    await state.clear()
    
    # Возвращаем информацию для отправки уведомления в канал
    return {
        "username": user[1],
        "link": link
    }

@router.message(Command("mylink"))
@router.message(F.text == "🔗 Моё актуальное")
async def cmd_my_link(message: Message):
    """Обработчик команды /mylink"""
    if not await check_auth(message):
        return
    
    user = db.get_user_by_telegram_id(message.from_user.id)
    link = user[2]
    
    if link:
        await message.answer(f"🔗 Ваша текущая ссылка: {link}")
    else:
        await message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте /setlink чтобы добавить ссылку.")
    
    # Показываем соответствующие кнопки в зависимости от роли пользователя
    is_admin = message.from_user.id in ADMIN_IDS
    if is_admin:
        # Для админа сначала инлайн-кнопки для работы со ссылками
        
        # Затем обычную клавиатуру с функциями администрирования
        await message.answer(
            "Функции администрирования:",
            reply_markup=get_admin_keyboard()
        )
    else:
        # Для обычного пользователя только инлайн-кнопки
        await message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )

@router.callback_query(F.data == "my_link")
async def callback_my_link(callback: CallbackQuery):
    """Обработчик инлайн-кнопки просмотра ссылки"""
    await callback.answer()
    
    if not await check_auth_callback(callback):
        return
    
    user = db.get_user_by_telegram_id(callback.from_user.id)
    link = user[2]
    
    if link:
        await callback.message.answer(f"🔗 Ваша текущая ссылка: {link}")
    else:
        await callback.message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте /setlink чтобы добавить ссылку.")
    
    # Показываем соответствующие кнопки в зависимости от роли пользователя
    is_admin = callback.from_user.id in ADMIN_IDS
    if is_admin:

        # Затем обычную клавиатуру с функциями администрирования
        await callback.message.answer(
            "Функции администрирования:",
            reply_markup=get_admin_keyboard()
        )
    else:
        # Для обычного пользователя только инлайн-кнопки
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )

@router.message(Command("mylink"))
@router.message(F.text == "🔗 Моя ссылка")
async def cmd_my_link(message: Message):
    """Обработчик команды /mylink"""
    if not await check_auth(message):
        return
    
    user = db.get_user_by_telegram_id(message.from_user.id)
    link = user[2]
    # Показываем соответствующую клавиатуру в зависимости от роли пользователя
    is_admin = message.from_user.id in ADMIN_IDS
    keyboard = get_admin_keyboard() if is_admin else get_main_keyboard()

    if link:
        await message.answer(f"🔗 Ваша текущая ссылка: {link}")
    else:
        await message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте /setlink чтобы добавить ссылку.")
    
    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.callback_query(F.data == "my_link")
async def callback_my_link(callback: CallbackQuery):
    """Обработчик инлайн-кнопки просмотра ссылки"""
    await callback.answer()
    
    if not await check_auth_callback(callback):
        return
    
    user = db.get_user_by_telegram_id(callback.from_user.id)
    link = user[2]
    # Показываем соответствующую клавиатуру в зависимости от роли пользователя
    is_admin = callback.from_user.id in ADMIN_IDS
    keyboard = get_admin_keyboard() if is_admin else get_main_keyboard()

    if link:
        await callback.message.answer(f"🔗 Ваша текущая ссылка: {link}")
    else:
        await callback.message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте /setlink чтобы добавить ссылку.")
    
    await callback.message.answer("Выберите действие:", reply_markup=keyboard)

@router.callback_query(F.data == "logout")
async def callback_logout(callback: CallbackQuery):
    """Обработчик инлайн-кнопки выхода"""
    await callback.answer()
    
    user = db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.message.answer("❌ Вы не авторизованы.", reply_markup=get_start_keyboard())
        return
    
    # Удаление привязки Telegram ID к аккаунту
    db.update_telegram_id(user[0], None)
    await callback.message.answer("Вы успешно вышли из аккаунта.", reply_markup=get_start_keyboard())

def setup(dp: Dispatcher):
    """Регистрация обработчиков пользователя"""
    dp.include_router(router)