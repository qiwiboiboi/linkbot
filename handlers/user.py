# Полный исправленный handlers/user.py

import logging
from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database import db
from models import LinkStates, MessageStates
from config import ADMIN_IDS
from utils.keyboards import get_main_keyboard, get_admin_keyboard, get_start_keyboard, get_cancel_keyboard, get_admin_inline_keyboard
from utils.helpers import send_error_message, send_success_message, cancel_state
from utils.url_validator import validate_and_fix_url, is_valid_url, get_url_display_name

# Создаем роутер для пользовательских команд
router = Router()

# Исправленный импорт logger
logger = logging.getLogger(__name__)

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

# =============================================================================
# ОБРАБОТЧИКИ КНОПОК ДЛЯ ОБЫЧНЫХ ПОЛЬЗОВАТЕЛЕЙ
# =============================================================================

@router.message(F.text == "🔄 Изменить")
async def cmd_set_link_button(message: Message, state: FSMContext):
    """Обработчик кнопки 'Изменить' для обычных пользователей"""
    if not await check_auth(message):
        return
    
    await message.answer(
        """Введите информацию в формате:

http://ссылка|Название

Также можете дополнительно указать любую информацию, которую посчитаете нужной, либо написать в ЛС через меню бота.""",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LinkStates.waiting_for_link)

@router.message(F.text == "🔗 Моё актуальное")
async def cmd_my_link_button(message: Message):
    """Обработчик кнопки 'Моё актуальное' для обычных пользователей"""
    if not await check_auth(message):
        return
    
    user = db.get_user_by_telegram_id(message.from_user.id)
    link = user[2]
    
    if link:
        await message.answer(f"🔗 Ваша текущая информация:\n{link}")
    else:
        await message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте кнопку 'Изменить' чтобы добавить ссылку.")
    
    # Показываем клавиатуру для обычного пользователя
    await message.answer("Выберите действие:", reply_markup=get_main_keyboard())

@router.message(F.text == "✉️ Написать сообщение")
async def cmd_send_message_button(message: Message, state: FSMContext):
    """Обработчик кнопки 'Написать сообщение' для обычных пользователей"""
    if not await check_auth(message):
        return
    
    # Проверяем, настроен ли канал для сообщений
    messages_channel = db.get_channel("messages")
    if not messages_channel:
        await send_error_message(
            message,
            "Канал для сообщений не настроен. Обратитесь к администратору."
        )
        await message.answer("Выберите действие:", reply_markup=get_main_keyboard())
        return
    
    await message.answer(
        "Введите ваше сообщение:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(MessageStates.waiting_for_message)

@router.message(F.text == "🚪 Выйти")
async def cmd_logout_button(message: Message):
    """Обработчик кнопки 'Выйти' для обычных пользователей"""
    user = db.get_user_by_telegram_id(message.from_user.id)
    
    if not user:
        await send_error_message(message, "Вы не авторизованы.")
        from utils.keyboards import get_start_button
        await message.answer("Нажмите Старт для начала работы:", reply_markup=get_start_button())
        return
    
    # Удаление привязки Telegram ID к аккаунту
    db.update_telegram_id(user[0], None)
    
    # Отправляем сообщение о выходе и кнопку для перезапуска
    from utils.keyboards import get_start_button
    await message.answer(
        "Вы успешно вышли из аккаунта.",
        reply_markup=get_start_button()
    )

# =============================================================================
# ОБРАБОТЧИКИ КОМАНД (для совместимости)
# =============================================================================

@router.message(Command("setlink"))
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

@router.message(Command("mylink"))
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
        await message.answer(f"🔗 Ваша текущая информация: {link}")
    else:
        await message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте /setlink чтобы добавить ссылку.")
    
    await message.answer("Выберите действие:", reply_markup=keyboard)

# =============================================================================
# ОБРАБОТЧИКИ СОСТОЯНИЙ
# =============================================================================

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
    is_admin = message.from_user.id in ADMIN_IDS
    if is_admin:
        # Для админа показываем сообщение и административную клавиатуру
        await send_success_message(message, f"Актуальное:\n{link}", reply_markup=get_admin_keyboard())
    else:
        # Для обычного пользователя показываем обычную клавиатуру
        await send_success_message(message, f"Актуальное:\n{link}", reply_markup=get_main_keyboard())
    
    await state.clear()
    
    # Возвращаем информацию для отправки уведомления в канал
    return {
        "username": user[1],
        "link": link
    }

@router.message(MessageStates.waiting_for_message)
async def process_user_message(message: Message, state: FSMContext, bot: Bot):
    """Обработка сообщения от пользователя"""
    if await cancel_state(message, state):
        return
    
    user_text = message.text.strip()
    if not user_text:
        await send_error_message(message, "Сообщение не может быть пустым")
        return
    
    user = db.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await send_error_message(message, "Пользователь не найден")
        await state.clear()
        return
    
    try:
        messages_channel = db.get_channel("messages")
        if not messages_channel:
            await send_error_message(
                message,
                "Канал для сообщений не настроен. Обратитесь к администратору."
            )
            # Показываем соответствующую клавиатуру
            is_admin = message.from_user.id in ADMIN_IDS
            keyboard = get_admin_keyboard() if is_admin else get_main_keyboard()
            await message.answer("Выберите действие:", reply_markup=keyboard)
            await state.clear()
            return
        
        # Получаем имя пользователя для отображения
        username = user[1]
        full_name = None
        
        # Проверяем, есть ли поле full_name
        if len(user) > 3:
            full_name = user[3]
        
        # Формируем отображаемое имя
        if full_name and full_name.strip():
            display_name = f"{full_name} (@{username})"
        else:
            display_name = username
        
        # Отправляем сообщение в канал
        await bot.send_message(
            chat_id=messages_channel,
            text=f"📨 Новое сообщение от пользователя\n\n"
                 f"👤 Пользователь: {display_name}\n"
                 f"💬 Сообщение:\n{user_text}",
            parse_mode="HTML"
        )
        
        # Отправляем сообщение об успехе
        is_admin = message.from_user.id in ADMIN_IDS
        keyboard = get_admin_keyboard() if is_admin else get_main_keyboard()
        
        await send_success_message(
            message, 
            "Ваше сообщение успешно отправлено!",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Failed to send message to channel: {e}")
        
        # Показываем соответствующую клавиатуру при ошибке
        is_admin = message.from_user.id in ADMIN_IDS
        keyboard = get_admin_keyboard() if is_admin else get_main_keyboard()
        
        await send_error_message(
            message,
            "Не удалось отправить сообщение. Попробуйте позже или обратитесь к администратору.",
            reply_markup=keyboard
        )
    
    await state.clear()

# =============================================================================
# ОБРАБОТЧИКИ CALLBACK-ЗАПРОСОВ (для админов)
# =============================================================================

@router.callback_query(F.data == "set_link")
async def callback_set_link(callback: CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопки изменения ссылки (для админов)"""
    await callback.answer()
    
    if not await check_auth_callback(callback):
        return
    
    await callback.message.answer(
        """Введите информацию в формате:

http://ссылка|Название

Также можете дополнительно указать любую информацию, которую посчитаете нужной, либо написать в ЛС через меню бота.""",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(LinkStates.waiting_for_link)

@router.callback_query(F.data == "send_message")
async def callback_send_message(callback: CallbackQuery, state: FSMContext):
    """Обработчик инлайн-кнопки отправки сообщения (для админов)"""
    await callback.answer()
    
    if not await check_auth_callback(callback):
        return
    
    # Проверяем, настроен ли канал для сообщений
    messages_channel = db.get_channel("messages")
    if not messages_channel:
        await callback.message.answer(
            "❌ Канал для сообщений не настроен. Обратитесь к администратору.",
            reply_markup=get_main_keyboard()
        )
        return
    
    await callback.message.answer(
        "Введите ваше сообщение:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(MessageStates.waiting_for_message)

@router.callback_query(F.data == "my_link")
async def callback_my_link(callback: CallbackQuery):
    """Обработчик инлайн-кнопки просмотра ссылки (для админов)"""
    await callback.answer()
    
    if not await check_auth_callback(callback):
        return
    
    user = db.get_user_by_telegram_id(callback.from_user.id)
    link = user[2]
    
    if link:
        await callback.message.answer(f"🔗 Актуальное:\n{link}")
    else:
        await callback.message.answer("У вас еще нет сохраненной ссылки.\nИспользуйте /setlink чтобы добавить ссылку.")
    
    # Показываем соответствующие кнопки в зависимости от роли пользователя
    is_admin = callback.from_user.id in ADMIN_IDS
    if is_admin:
        # Для админа показываем функции администрирования
        await callback.message.answer(
            "Функции администрирования:",
            reply_markup=get_admin_keyboard()
        )
    else:
        # Для обычного пользователя показываем основную клавиатуру
        await callback.message.answer(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )

@router.callback_query(F.data == "logout")
async def callback_logout(callback: CallbackQuery):
    """Обработчик инлайн-кнопки выхода (для админов)"""
    await callback.answer()
    
    user = db.get_user_by_telegram_id(callback.from_user.id)
    
    if not user:
        from utils.keyboards import get_start_button
        await callback.message.answer("❌ Вы не авторизованы.", reply_markup=get_start_button())
        return
    
    # Удаление привязки Telegram ID к аккаунту
    db.update_telegram_id(user[0], None)
    from utils.keyboards import get_start_button
    await callback.message.answer("Вы успешно вышли из аккаунта.", reply_markup=get_start_button())

# =============================================================================
# ОБРАБОТЧИК КАСТОМНЫХ КНОПОК (должен быть последним)
# =============================================================================

@router.message()
async def handle_custom_buttons(message: Message):
    """Обработчик кастомных кнопок - должен быть последним в цепочке обработчиков"""
    if not await check_auth(message):
        return
    
    # Получаем все активные кастомные кнопки
    custom_buttons = db.get_custom_buttons(active_only=True)
    
    # Ищем кнопку с таким названием
    for button_data in custom_buttons:
        button_id, name, url, is_active = button_data
        if message.text.strip() == name:
            try:
                # Проверяем и исправляем URL
                fixed_url = validate_and_fix_url(url)
                
                if not is_valid_url(fixed_url):
                    # Если URL невалидный, показываем текстовое сообщение
                    await message.answer(
                        f"🔗 {name}\n\n"
                        f"Ссылка: {url}\n\n"
                        f"⚠️ Некорректный формат ссылки. Обратитесь к администратору.",
                        disable_web_page_preview=True
                    )
                else:
                    # Создаем инлайн-клавиатуру с кнопкой-ссылкой
                    display_name = get_url_display_name(fixed_url)
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"🔗 Перейти в {display_name}", url=fixed_url)]
                    ])
                    
                    # Отправляем сообщение с кнопкой-ссылкой
                    await message.answer(
                        f"🔗 {name}\n\n"
                        f"Нажмите на кнопку ниже, чтобы перейти:",
                        reply_markup=keyboard,
                        disable_web_page_preview=True
                    )
                
                # Показываем основную клавиатуру обратно
                is_admin = message.from_user.id in ADMIN_IDS
                keyboard_main = get_admin_keyboard() if is_admin else get_main_keyboard()
                await message.answer("Выберите действие:", reply_markup=keyboard_main)
                return
                
            except Exception as e:
                logger.error(f"Error processing custom button URL: {e}")
                # В случае ошибки показываем текстовое сообщение
                await message.answer(
                    f"🔗 {name}\n\n"
                    f"Ссылка: {url}\n\n"
                    f"⚠️ Ошибка при обработке ссылки. Обратитесь к администратору.",
                    disable_web_page_preview=True
                )
                
                # Показываем основную клавиатуру обратно
                is_admin = message.from_user.id in ADMIN_IDS
                keyboard_main = get_admin_keyboard() if is_admin else get_main_keyboard()
                await message.answer("Выберите действие:", reply_markup=keyboard_main)
                return
    
    # Если кнопка не найдена, не отвечаем (позволяем другим обработчикам сработать)

def setup(dp: Dispatcher):
    """Регистрация обработчиков пользователя"""
    dp.include_router(router)