from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import get_welcome_message, update_welcome_message
from models import BroadcastByIdStates, ChannelStates, CustomButtonStates
from database import db
from models import AddUserStates, EditUserStates, DeleteUserStates, BroadcastStates, WelcomeMessageStates

from utils.keyboards import (
    get_admin_keyboard, 
    get_user_action_keyboard, 
    get_cancel_keyboard,
    get_admin_inline_keyboard,
    get_main_keyboard,
    get_start_keyboard,
    get_button_management_keyboard,
    get_button_edit_keyboard
)
from utils.helpers import (
    check_admin,
    cancel_state,
    format_user_list,
    send_error_message,
    send_success_message
)

import asyncio
import logging

logger = logging.getLogger(__name__)

router = Router()
# Заменить функцию get_channel_name и обработчики кнопок каналов в handlers/admin.py:

async def get_channel_info(bot: Bot, channel_id: str) -> str:
    """Получить информацию о канале по его ID"""
    try:
        chat = await bot.get_chat(channel_id)
        if chat.title:
            return f"{chat.title}"
        elif chat.username:
            return f"@{chat.username}"
        else:
            return f"ID: {channel_id}"
    except Exception as e:
        logger.error(f"Failed to get channel info for {channel_id}: {e}")
        return f"ID: {channel_id}"

@router.message(F.text == "📋 Канал для ссылок")
async def cmd_set_links_channel(message: Message, state: FSMContext, bot: Bot):
    """Обработчик команды установки канала для ссылок"""
    if not await check_admin(message):
        return

    # Получаем свежий ID канала из базы данных
    current_channel_id = db.get_channel("links")
    if current_channel_id:
        current_status = await get_channel_info(bot, current_channel_id)
    else:
        current_status = "Отсутствует"
    
    await message.answer(
        f"📋 Текущий канал для ссылок: {current_status}\n\n"
        "Введите ID канала для публикации ссылок.\n"
        "Важно: бот должен быть администратором канала.",
        reply_markup=get_cancel_keyboard()
    )
    await state.update_data(channel_type="links")
    await state.set_state(ChannelStates.waiting_for_channel_id)

@router.message(F.text == "💬 Канал для сообщений")
async def cmd_set_messages_channel(message: Message, state: FSMContext, bot: Bot):
    """Обработчик команды установки канала для сообщений"""
    if not await check_admin(message):
        return

    # Получаем свежий ID канала из базы данных
    current_channel_id = db.get_channel("messages")
    if current_channel_id:
        current_status = await get_channel_info(bot, current_channel_id)
    else:
        current_status = "Отсутствует"
    
    await message.answer(
        f"💬 Текущий канал для сообщений: {current_status}\n\n"
        "Введите ID канала для публикации сообщений пользователей.\n"
        "Важно: бот должен быть администратором канала.",
        reply_markup=get_cancel_keyboard()
    )
    await state.update_data(channel_type="messages")
    await state.set_state(ChannelStates.waiting_for_channel_id)
# Добавить этот обработчик в handlers/admin.py после существующих обработчиков каналов:

@router.message(ChannelStates.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода ID канала"""
    if await cancel_state(message, state):
        return

    channel_id = message.text.strip()
    state_data = await state.get_data()
    channel_type = state_data.get('channel_type')

    logger.info(f"Attempting to set channel {channel_type} to {channel_id}")

    try:
        # Пытаемся отправить тестовое сообщение в канал
        test_message = await bot.send_message(
            chat_id=channel_id,
            text="✅ Тестовое сообщение для проверки прав бота"
        )
        # Если сообщение отправлено успешно, удаляем его
        await test_message.delete()

        # Сохраняем ID канала в базе данных
        save_result = db.set_channel(channel_type, channel_id)
        logger.info(f"Channel save result: {save_result}")
        
        if save_result:
            # Проверяем, что канал действительно сохранился
            saved_channel = db.get_channel(channel_type)
            logger.info(f"Saved channel ID: {saved_channel}")
            
            channel_type_text = "ссылок" if channel_type == "links" else "сообщений"
            await send_success_message(
                message,
                f"Канал для {channel_type_text} успешно установлен!\n"
                f"Новый ID: {channel_id}"
            )
        else:
            await send_error_message(
                message,
                "Не удалось сохранить настройки канала"
            )

    except Exception as e:
        logger.error(f"Error setting channel: {e}")
        await send_error_message(
            message,
            "Не удалось установить канал. Убедитесь, что:\n"
            "1. ID канала указан верно\n"
            "2. Бот добавлен в канал\n"
            "3. Бот является администратором канала\n\n"
            f"Ошибка: {str(e)}"
        )

    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    await state.clear()

def get_display_name(user_data, username):
    """Безопасное получение отображаемого имени пользователя"""
    # Безопасная распаковка данных
    user_id = user_data[0]
    username = user_data[1]
    telegram_id = user_data[2] if len(user_data) > 2 else None
    link = user_data[3] if len(user_data) > 3 else None
    full_name = user_data[4] if len(user_data) > 4 else None
    
    # Формируем отображение имени ТОЛЬКО если есть full_name и оно не пустое
    if full_name and full_name.strip():
        return f"{full_name} (@{username})"
    else:
        return username

def get_display_name_from_user_info(user_info, username):
    """Безопасное получение отображаемого имени из данных пользователя по ID"""
    # user_info может быть (username, telegram_id, link) или (username, telegram_id, link, full_name)
    if len(user_info) >= 4:  # Есть поле full_name
        full_name = user_info[3]
        if full_name and full_name.strip():
            return f"{full_name} (@{username})"
    
    return username

# Обновленная функция для отображения списка пользователей с именами

@router.message(F.text == "📩 Сообщение")
@router.message(Command("broadcast_by_id"))
async def cmd_broadcast_by_id(message: Message, state: FSMContext):
    """Обработчик команды /broadcast_by_id для начала рассылки по ID"""
    if not await check_admin(message):
        return
    
    # Получаем список всех пользователей
    users = db.get_all_users()
    if not users:
        await send_error_message(message, "Список пользователей пуст.", reply_markup=get_admin_keyboard())
        return
    
    # Формируем список пользователей с их ID и именами
    user_list = "📋 Список пользователей:\n\n"
    for user_data in users:
        # Безопасная распаковка данных
        user_id = user_data[0]
        username = user_data[1]
        telegram_id = user_data[2] if len(user_data) > 2 else None
        link = user_data[3] if len(user_data) > 3 else None
        full_name = user_data[4] if len(user_data) > 4 else None
        
        # Формируем отображение имени ТОЛЬКО если есть full_name и оно не пустое
        if full_name and full_name.strip():
            display_name = f"{full_name} (@{username})"
        else:
            display_name = username
        
        user_list += f"👤 ID: {user_id} | {display_name}"
        if telegram_id:
            user_list += f" | ✅ Авторизован (TG ID: {telegram_id})"
        else:
            user_list += " | ❌ Не авторизован"
        user_list += "\n"
    
    user_list += "\nВведите ID пользователя, которому хотите отправить сообщение:"
    
    await message.answer(user_list, reply_markup=get_cancel_keyboard())
    await state.set_state(BroadcastByIdStates.waiting_for_user_id)


@router.message(BroadcastByIdStates.waiting_for_user_id)
async def process_user_id_for_broadcast(message: Message, state: FSMContext):
    """Обработка ввода ID пользователя для рассылки"""
    if await cancel_state(message, state):
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await send_error_message(
            message, 
            "Пожалуйста, введите корректный числовой ID пользователя.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Проверяем существование пользователя с указанным ID
    user = db.get_user_by_id(user_id)
    if not user:
        await send_error_message(
            message, 
            f"Пользователь с ID {user_id} не найден.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return
    
    # user = (username, telegram_id, link)
    username = user[0]
    telegram_id = user[1]
    
    # Проверяем, авторизован ли пользователь
    if not telegram_id:
        await send_error_message(
            message,
            f"Пользователь {username} (ID: {user_id}) не авторизован в боте. "
            f"Отправка сообщения невозможна.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return
    
    # Сохраняем данные пользователя в состоянии
    await state.update_data(
        target_user_id=user_id, 
        target_username=username,
        target_telegram_id=telegram_id
    )
    
    # Теперь запрашиваем контент для отправки без выбора типа
    await message.answer(
        f"Выбран пользователь: {username} (ID: {user_id}, TG ID: {telegram_id})\n"
        f"Отправьте любой контент (текст, фото, видео, аудио, документ), который нужно отправить пользователю:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BroadcastByIdStates.waiting_for_content)
    
@router.message(BroadcastByIdStates.waiting_for_content)
async def process_broadcast_by_id_content(message: Message, state: FSMContext, bot: Bot):
    if await cancel_state(message, state):
        return

    data = await state.get_data()
    target_id = int(data['target_telegram_id'])

    try:
        # Скопируем любое сообщение целиком
        await bot.copy_message(
            chat_id=target_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
        await send_success_message(
            message,
            f"Сообщение успешно отправлено пользователю {data['target_username']}."
        )
    except Exception as e:
        logger.exception("Ошибка при отправке копии сообщения:")
        await send_error_message(
            message,
            f"Не удалось отправить сообщение: {e}"
        )
    finally:
        await state.clear()

# Исправленные методы для handlers/admin.py

@router.message(F.text == "✏️ Изменить")
@router.message(Command("edituser"))
async def cmd_edit_user(message: Message, state: FSMContext):
    """Обработчик команды изменения пользователя"""
    if not await check_admin(message):
        return
    
    users = db.get_all_users()
    if not users:
        await send_error_message(message, "Список пользователей пуст.", reply_markup=get_admin_keyboard())
        return
    
    # Формируем список пользователей с именами
    user_list = "📋 Список пользователей:\n\n"
    for user_data in users:
        # Безопасная распаковка данных
        user_id = user_data[0]
        username = user_data[1]
        telegram_id = user_data[2] if len(user_data) > 2 else None
        link = user_data[3] if len(user_data) > 3 else None
        full_name = user_data[4] if len(user_data) > 4 else None
        
        # Формируем отображение имени ТОЛЬКО если есть full_name и оно не пустое
        if full_name and full_name.strip():
            display_name = f"{full_name} (@{username})"
        else:
            display_name = username
        
        user_list += f"👤 ID: {user_id} | {display_name}"
        if telegram_id:
            user_list += " | ✅ Авторизован"
        else:
            user_list += " | ❌ Не авторизован"
        user_list += "\n"
    
    user_list += "\nВведите ID пользователя для изменения:"
    
    await message.answer(user_list, reply_markup=get_cancel_keyboard())
    await state.set_state(EditUserStates.waiting_for_user_id)

@router.message(EditUserStates.waiting_for_user_id)
async def process_edit_user_id(message: Message, state: FSMContext):
    """Обработка ввода ID пользователя для изменения"""
    if await cancel_state(message, state):
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await send_error_message(
            message, 
            "Пожалуйста, введите корректный числовой ID пользователя.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Проверяем существование пользователя
    user = db.get_user_by_id(user_id)
    if not user:
        await send_error_message(
            message, 
            f"Пользователь с ID {user_id} не найден.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return
    
    # Сохраняем ID пользователя в состоянии
    await state.update_data(user_id=user_id)
    
    # Показываем информацию о пользователе и предлагаем действия
    # Безопасная распаковка данных пользователя
    username = user[0]
    telegram_id = user[1] if len(user) > 1 else None
    link = user[2] if len(user) > 2 else None
    full_name = user[3] if len(user) > 3 else None
    
    # Формируем отображение имени ТОЛЬКО если есть full_name и оно не пустое
    if full_name and full_name.strip():
        display_name = f"{full_name} (@{username})"
    else:
        display_name = username
    
    info_text = (
        f"Выбран пользователь:\n"
        f"👤 Имя: {display_name}\n"
        f"📝 Логин: {username}\n"
        f"🆔 ID: {user_id}\n"
        f"📱 Telegram ID: {telegram_id or 'Не привязан'}\n"
        f"🔗 Информация: {link or 'Не указана'}\n\n"
        f"Что хотите изменить?"
    )
    
    await message.answer(info_text, reply_markup=get_user_action_keyboard())
    await state.set_state(EditUserStates.waiting_for_action)


@router.message(EditUserStates.waiting_for_action)
async def process_edit_action(message: Message, state: FSMContext):
    """Обработка выбора действия для изменения пользователя"""
    if await cancel_state(message, state):
        return
    
    action = message.text.strip()
    
    if action == "Изменить логин":
        await message.answer("Введите новый логин:", reply_markup=get_cancel_keyboard())
        await state.set_state(EditUserStates.waiting_for_new_username)
    elif action == "Изменить пароль":
        await message.answer("Введите новый пароль:", reply_markup=get_cancel_keyboard())
        await state.set_state(EditUserStates.waiting_for_new_password)
    else:
        await send_error_message(
            message, 
            "Неверный выбор. Выберите действие из предложенных кнопок.",
            reply_markup=get_user_action_keyboard()
        )

@router.message(EditUserStates.waiting_for_new_username)
async def process_new_username_edit(message: Message, state: FSMContext):
    """Обработка ввода нового логина"""
    if await cancel_state(message, state):
        return
    
    new_username = message.text.strip()
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    
    # Проверяем, не занят ли новый логин
    existing_user = db.get_user_by_username(new_username)
    if existing_user and existing_user[0] != user_id:  # existing_user[0] - это ID
        await send_error_message(
            message, 
            f"Логин '{new_username}' уже занят другим пользователем.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return
    
    # Обновляем логин
    if db.update_username(user_id, new_username):
        await send_success_message(
            message, 
            f"Логин пользователя (ID: {user_id}) успешно изменен на '{new_username}'",
            reply_markup=get_admin_keyboard()
        )
    else:
        await send_error_message(
            message, 
            "Не удалось изменить логин пользователя",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@router.message(EditUserStates.waiting_for_new_password)
async def process_new_password_edit(message: Message, state: FSMContext):
    """Обработка ввода нового пароля"""
    if await cancel_state(message, state):
        return
    
    new_password = message.text.strip()
    user_data = await state.get_data()
    user_id = user_data.get('user_id')
    
    # Обновляем пароль
    if db.update_password(user_id, new_password):
        await send_success_message(
            message, 
            f"Пароль пользователя (ID: {user_id}) успешно изменен на '{new_password}'",
            reply_markup=get_admin_keyboard()
        )
    else:
        await send_error_message(
            message, 
            "Не удалось изменить пароль пользователя",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@router.message(F.text == "❌ Удалить")
@router.message(Command("deleteuser"))
async def cmd_delete_user(message: Message, state: FSMContext):
    """Обработчик команды удаления пользователя"""
    if not await check_admin(message):
        return
    
    users = db.get_all_users()
    if not users:
        await send_error_message(message, "Список пользователей пуст.", reply_markup=get_admin_keyboard())
        return
    
    # Формируем список пользователей с именами
    user_list = "📋 Список пользователей:\n\n"
    for user_data in users:
        # Безопасная распаковка данных
        user_id = user_data[0]
        username = user_data[1]
        telegram_id = user_data[2] if len(user_data) > 2 else None
        link = user_data[3] if len(user_data) > 3 else None
        full_name = user_data[4] if len(user_data) > 4 else None
        
        # Формируем отображение имени ТОЛЬКО если есть full_name и оно не пустое
        if full_name and full_name.strip():
            display_name = f"{full_name} (@{username})"
        else:
            display_name = username
        
        user_list += f"👤 ID: {user_id} | {display_name}"
        if telegram_id:
            user_list += " | ✅ Авторизован"
        else:
            user_list += " | ❌ Не авторизован"
        user_list += "\n"
    
    user_list += "\nВведите ID пользователя для удаления:"
    
    await message.answer(user_list, reply_markup=get_cancel_keyboard())
    await state.set_state(DeleteUserStates.waiting_for_user_id)

@router.message(DeleteUserStates.waiting_for_user_id)
async def process_delete_user_id(message: Message, state: FSMContext):
    """Обработка ввода ID пользователя для удаления"""
    if await cancel_state(message, state):
        return
    
    try:
        user_id = int(message.text.strip())
    except ValueError:
        await send_error_message(
            message, 
            "Пожалуйста, введите корректный числовой ID пользователя.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    # Проверяем существование пользователя
    user = db.get_user_by_id(user_id)
    if not user:
        await send_error_message(
            message, 
            f"Пользователь с ID {user_id} не найден.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return
    
    # Безопасная распаковка данных пользователя
    username = user[0]
    telegram_id = user[1] if len(user) > 1 else None
    link = user[2] if len(user) > 2 else None
    full_name = user[3] if len(user) > 3 else None
    
    # Формируем отображение имени ТОЛЬКО если есть full_name и оно не пустое
    if full_name and full_name.strip():
        display_name = f"{full_name} (@{username})"
    else:
        display_name = username
    
    # Удаляем пользователя
    if db.delete_user(user_id):
        await send_success_message(
            message, 
            f"Пользователь '{display_name}' (ID: {user_id}) успешно удален",
            reply_markup=get_admin_keyboard()
        )
    else:
        await send_error_message(
            message, 
            f"Не удалось удалить пользователя '{display_name}' (ID: {user_id})",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

# Массовая рассылка всем пользователям
@router.message(F.text == "📢 Рассылка")
@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Обработчик команды /broadcast для начала рассылки всем пользователям"""
    if not await check_admin(message):
        return
    
    # Теперь просто запрашиваем контент для отправки без выбора типа
    await message.answer(
        "Отправьте любой контент (текст, фото, видео, аудио, документ), "
        "который будет разослан всем авторизованным пользователям:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_content)

@router.message(BroadcastStates.waiting_for_content)
async def process_broadcast_content(message: Message, state: FSMContext, bot: Bot):
    """Обработка любого контента для массовой рассылки"""
    if await cancel_state(message, state):
        return
    
    users = db.get_all_users()
    sent_count = 0
    failed_count = 0
    
    logger.info(f"Starting broadcast. Total users: {len(users)}")
    progress_msg = await message.answer("⏳ Начинаю рассылку...")
    
    # Отладочная информация
    await message.answer(f"🔍 Найдено пользователей: {len(users)}")
    
    for user_data in users:
        try:
            # Безопасная распаковка данных пользователей
            user_id = user_data[0]
            username = user_data[1]
            telegram_id = user_data[2] if len(user_data) > 2 else None
            
            logger.info(f"Processing user: {username}, TG ID: {telegram_id}")
            
            # Пропускаем пользователей без telegram_id и отправителя
            if not telegram_id:
                logger.info(f"Skipping user {username} - no telegram_id")
                continue
                
            if telegram_id == message.from_user.id:
                logger.info(f"Skipping sender {username}")
                continue
            
            # Попытка отправки сообщения
            success = False
            
            # Текстовое сообщение
            if message.text and not message.media_group_id:
                text = message.text.strip()
                formatted_message = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{text}"
                await bot.send_message(
                    telegram_id,
                    formatted_message,
                    parse_mode="HTML"
                )
                success = True
            
            # Фото
            elif message.photo:
                photo = message.photo[-1]
                caption = message.caption or ""
                formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if caption else "<b>Сообщение от PARTNERS 🔗</b>"
                
                await bot.send_photo(
                    telegram_id,
                    photo=photo.file_id,
                    caption=formatted_caption,
                    parse_mode="HTML"
                )
                success = True
            
            # Видео
            elif message.video:
                caption = message.caption or ""
                formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if caption else "<b>Сообщение от PARTNERS 🔗</b>"
                
                await bot.send_video(
                    telegram_id,
                    video=message.video.file_id,
                    caption=formatted_caption,
                    parse_mode="HTML"
                )
                success = True
            
            # Аудио
            elif message.audio:
                caption = message.caption or ""
                formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if caption else "<b>Сообщение от PARTNERS 🔗</b>"
                
                await bot.send_audio(
                    telegram_id,
                    audio=message.audio.file_id,
                    caption=formatted_caption,
                    parse_mode="HTML"
                )
                success = True
            
            # Документ
            elif message.document:
                caption = message.caption or ""
                formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if caption else "<b>Сообщение от PARTNERS 🔗</b>"
                
                await bot.send_document(
                    telegram_id,
                    document=message.document.file_id,
                    caption=formatted_caption,
                    parse_mode="HTML"
                )
                success = True
            
            # Голосовое сообщение
            elif message.voice:
                await bot.send_message(
                    telegram_id,
                    "<b>Сообщение от PARTNERS 🔗</b>",
                    parse_mode="HTML"
                )
                await bot.send_voice(
                    telegram_id,
                    voice=message.voice.file_id
                )
                success = True
            
            # Стикер
            elif message.sticker:
                await bot.send_message(
                    telegram_id,
                    "<b>Сообщение от PARTNERS 🔗</b>",
                    parse_mode="HTML"
                )
                await bot.send_sticker(
                    telegram_id,
                    sticker=message.sticker.file_id
                )
                success = True
            
            # Анимация (GIF)
            elif message.animation:
                caption = message.caption or ""
                formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if caption else "<b>Сообщение от PARTNERS 🔗</b>"
                
                await bot.send_animation(
                    telegram_id,
                    animation=message.animation.file_id,
                    caption=formatted_caption,
                    parse_mode="HTML"
                )
                success = True
            
            # Видеосообщение
            elif message.video_note:
                await bot.send_message(
                    telegram_id,
                    "<b>Сообщение от PARTNERS 🔗</b>",
                    parse_mode="HTML"
                )
                await bot.send_video_note(
                    telegram_id,
                    video_note=message.video_note.file_id
                )
                success = True
            
            if success:
                sent_count += 1
                logger.info(f"Message sent successfully to user {username} (TG ID: {telegram_id})")
            else:
                failed_count += 1
                logger.warning(f"Unknown message type for user {username}")
            
            # Обновляем прогресс каждые 5 отправлений
            if (sent_count + failed_count) % 5 == 0:
                try:
                    await progress_msg.edit_text(f"⏳ Обработано: {sent_count + failed_count}/{len(users)} пользователей\n✅ Отправлено: {sent_count}")
                except:
                    pass
            
            # Добавляем задержку между отправками
            await asyncio.sleep(0.3)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send message to user {username if 'username' in locals() else 'unknown'}: {e}")
            import traceback
            traceback.print_exc()
    
    # Удаляем сообщение о прогрессе
    try:
        await progress_msg.delete()
    except:
        pass
    
    # Подсчитываем количество авторизованных пользователей
    authorized_users = sum(1 for user_data in users if len(user_data) > 2 and user_data[2] is not None and user_data[2] != message.from_user.id)
    
    result_message = (
        f"📊 Рассылка завершена!\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"🔐 Авторизованных: {authorized_users}\n"
        f"✅ Отправлено: {sent_count}\n"
        f"❌ Не доставлено: {failed_count}"
    )
    
    logger.info(f"Broadcast completed. Sent: {sent_count}, Failed: {failed_count}")
    
    await send_success_message(message, result_message)
    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    await state.clear()

async def check_admin_and_get_users(message: Message) -> list:
    """Проверка админа и получение списка пользователей"""
    if not await check_admin(message):
        return None
        
    users = db.get_all_users()
    if not users:
        await send_error_message(message, "Список пользователей пуст.", reply_markup=get_admin_keyboard())
        return None
    return users

@router.message(F.text == "👥 Пользователи")
@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Обработчик команды /admin с разбивкой на части"""
    users = await check_admin_and_get_users(message)
    if not users:
        return
    
    # Разбиваем список пользователей на части
    await send_user_list_in_parts(message, users)
    
    await message.answer(
        "Функции администрирования:",
        reply_markup=get_admin_keyboard()
    )

async def send_user_list_in_parts(message: Message, users: list):
    """Отправка списка пользователей частями"""
    if not users:
        await message.answer("Список пользователей пуст.")
        return
    
    # Константы для разбивки
    MAX_MESSAGE_LENGTH = 4000  # Оставляем запас от лимита в 4096 символов
    
    # Формируем данные для каждого пользователя
    user_entries = []
    for user_data in users:
        # Безопасная распаковка данных с учетом возможного отсутствия поля full_name
        user_id = user_data[0]
        username = user_data[1]
        telegram_id = user_data[2] if len(user_data) > 2 else None
        link = user_data[3] if len(user_data) > 3 else None
        full_name = user_data[4] if len(user_data) > 4 else None
        
        # Получаем данные пользователя включая пароль
        from database import db
        user_db_data = db.get_user_by_username(username)
        password = user_db_data[1] if user_db_data else "Не найден"
        
        # Формируем отображение имени ТОЛЬКО если есть full_name и оно не пустое
        if full_name and full_name.strip():
            display_name = f"{full_name} (@{username})"
        else:
            display_name = username
        
        # Формируем текст для одного пользователя
        user_text = f"ID: {user_id} | {display_name}\n"
        user_text += f"   Логин: {username}\n"
        user_text += f"   Пароль: {password}\n"
        
        if telegram_id:
            user_text += f"   Статус: ✅ Авторизован (TG ID: {telegram_id})\n"
        else:
            user_text += f"   Статус: ❌ Не авторизован\n"
            
        user_text += f"   Информация: {link or '—'}\n\n"
        
        user_entries.append(user_text)
    
    # Разбиваем на части
    parts = []
    current_part = ""
    current_length = 0
    
    # Заголовок для первой части
    header = f"📊 Список всех пользователей (всего: {len(users)}):\n\n"
    
    for i, user_entry in enumerate(user_entries):
        # Проверяем, поместится ли текущая запись в текущую часть
        entry_length = len(user_entry)
        
        # Для первой части учитываем длину заголовка
        if not current_part:
            test_length = len(header) + current_length + entry_length
        else:
            test_length = current_length + entry_length
        
        if test_length > MAX_MESSAGE_LENGTH and current_part:
            # Если не помещается и есть текущая часть, сохраняем её
            parts.append(current_part.rstrip())
            current_part = user_entry
            current_length = entry_length
        else:
            # Если помещается, добавляем к текущей части
            current_part += user_entry
            current_length += entry_length
    
    # Добавляем последнюю часть
    if current_part:
        parts.append(current_part.rstrip())
    
    # Отправляем части
    for i, part in enumerate(parts):
        if i == 0:
            # Первая часть с заголовком
            full_message = header + part
        else:
            # Остальные части с номером
            full_message = f"📊 Список пользователей (продолжение {i + 1}):\n\n{part}"
        
        await message.answer(full_message)
        
        # Небольшая задержка между сообщениями
        import asyncio
        await asyncio.sleep(0.1)
    
    # Добавляем итоговую информацию
    if len(parts) > 1:
        await message.answer(f"📝 Итого пользователей: {len(users)}")
    
    # Добавляем инструкцию только в конце
    await message.answer("Для добавления нового пользователя используйте команду /adduser")

@router.message(F.text == "🏪 Добавить")
@router.message(Command("adduser"))
async def cmd_add_user(message: Message, state: FSMContext):
    """Обработчик команды /adduser"""
    if not await check_admin(message):
        return
    
    await message.answer("Введите логин для нового пользователя:", reply_markup=get_cancel_keyboard())
    await state.set_state(AddUserStates.waiting_for_username)

@router.message(AddUserStates.waiting_for_username)
async def process_new_username(message: Message, state: FSMContext):
    """Обработка ввода логина для нового пользователя"""
    if await cancel_state(message, state):
        return
    
    username = message.text.strip()
    if db.get_user_by_username(username):
        await send_error_message(message, f"Пользователь с логином '{username}' уже существует. Попробуйте другой логин.")
        return
    
    await state.update_data(username=username)
    await message.answer("Теперь введите пароль для нового пользователя:", reply_markup=get_cancel_keyboard())
    await state.set_state(AddUserStates.waiting_for_password)

@router.message(AddUserStates.waiting_for_password)
async def process_new_password(message: Message, state: FSMContext):
    """Обработка ввода пароля и создание нового пользователя"""
    if await cancel_state(message, state):
        return
        
    password = message.text.strip()
    user_data = await state.get_data()
    username = user_data.get('username')
    
    if db.add_user(username, password):
        await send_success_message(
            message,
            f"Пользователь '{username}' успешно создан!\n\nЛогин: {username}\nПароль: {password}"
        )
        await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    else:
        await send_error_message(
            message, 
            f"Не удалось создать пользователя. Возможно, логин '{username}' уже занят.",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@router.message(F.text == "✏️ Изменить приветствие")
@router.message(Command("edit_welcome"))
async def cmd_edit_welcome(message: Message, state: FSMContext):
    """Обработчик команды для изменения приветственного сообщения"""
    if not await check_admin(message):
        return
    
    # Показываем текущее сообщение и инструкции
    await message.answer(
        f"Текущее приветственное сообщение:\n\n{get_welcome_message()}\n\n"
        f"Введите новый текст приветственного сообщения. Можно использовать HTML-разметку:\n"
        f"• Гиперссылка: <a href='https://example.com'>текст</a>\n"
        f"• Жирный текст: <b>текст</b>\n"
        f"• Курсив: <i>текст</i>\n\n"
        f"Или нажмите Отмена:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(WelcomeMessageStates.waiting_for_message)

@router.message(WelcomeMessageStates.waiting_for_message)
async def process_welcome_message(message: Message, state: FSMContext):
    """Обработка нового приветственного сообщения"""
    if await cancel_state(message, state):
        return
    
    new_welcome_message = message.text.strip()
    if not new_welcome_message:
        await send_error_message(message, "Текст сообщения не может быть пустым.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    # Обновляем приветственное сообщение
    try:
        # Проверяем, что сообщение корректно отображается с HTML
        test_msg = await message.answer(
            new_welcome_message,
            parse_mode="HTML"
        )
        await test_msg.delete()
        
        # Если HTML валидный, обновляем сообщение
        if update_welcome_message(new_welcome_message):
            await send_success_message(message, "Приветственное сообщение успешно обновлено!")
        else:
            await send_error_message(
                message,
                "Не удалось обновить приветственное сообщение",
                reply_markup=get_admin_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Failed to validate HTML in welcome message: {e}")
        await send_error_message(
            message,
            "Ошибка в HTML-разметке. Проверьте правильность тегов.",
            reply_markup=get_admin_keyboard()
        )
    
    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    await state.clear()

def setup(dp: Dispatcher):
    """Регистрация обработчиков администратора"""
    dp.include_router(router)



@router.message(F.text == "🔘 Управление кнопками")
async def cmd_manage_buttons(message: Message):
    """Обработчик входа в управление кнопками"""
    if not await check_admin(message):
        return
    
    await message.answer(
        "🔘 Управление кастомными кнопками пользователей:",
        reply_markup=get_button_management_keyboard()
    )

@router.message(F.text == "↩️ Назад к админке")
async def cmd_back_to_admin(message: Message):
    """Возврат к админ панели"""
    if not await check_admin(message):
        return
    
    await message.answer("Функции администрирования:", reply_markup=get_admin_keyboard())

@router.message(F.text == "➕ Добавить кнопку")
async def cmd_add_button(message: Message, state: FSMContext):
    """Добавление новой кастомной кнопки"""
    if not await check_admin(message):
        return
    
    await message.answer(
        "Введите название для новой кнопки:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CustomButtonStates.waiting_for_button_name)

@router.message(CustomButtonStates.waiting_for_button_name)
async def process_button_name(message: Message, state: FSMContext):
    """Обработка названия кнопки"""
    if await cancel_state(message, state):
        return
    
    button_name = message.text.strip()
    if not button_name:
        await send_error_message(message, "Название кнопки не может быть пустым.")
        return
    
    await state.update_data(button_name=button_name)
    await message.answer(
        f"Название кнопки: {button_name}\n\n"
        f"Теперь введите ссылку для этой кнопки:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CustomButtonStates.waiting_for_button_url)

@router.message(CustomButtonStates.waiting_for_button_url)
async def process_button_url(message: Message, state: FSMContext):
    """Обработка ссылки кнопки"""
    if await cancel_state(message, state):
        return
    
    button_url = message.text.strip()
    if not button_url:
        await send_error_message(message, "Ссылка не может быть пустой.")
        return
    
    # Проверяем, что ссылка начинается с http:// или https://
    if not (button_url.startswith('http://') or button_url.startswith('https://')):
        button_url = 'https://' + button_url
    
    user_data = await state.get_data()
    button_name = user_data.get('button_name')
    
    # Сохраняем кнопку в базу данных
    if db.add_custom_button(button_name, button_url):
        await send_success_message(
            message,
            f"✅ Кнопка успешно создана!\n\n"
            f"📝 Название: {button_name}\n"
            f"🔗 Ссылка: {button_url}"
        )
    else:
        await send_error_message(message, "Не удалось создать кнопку.")
    
    await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
    await state.clear()

@router.message(F.text == "📋 Список кнопок")
async def cmd_list_buttons(message: Message):
    """Показать список всех кнопок"""
    if not await check_admin(message):
        return
    
    buttons = db.get_custom_buttons(active_only=False)
    
    if not buttons:
        await message.answer("📋 Кастомных кнопок пока нет.")
        return
    
    buttons_text = "📋 Список всех кастомных кнопок:\n\n"
    for button_data in buttons:
        button_id, name, url, is_active = button_data
        status = "✅ Активна" if is_active else "❌ Отключена"
        buttons_text += f"🆔 ID: {button_id}\n"
        buttons_text += f"📝 Название: {name}\n"
        buttons_text += f"🔗 Ссылка: {url}\n"
        buttons_text += f"🔄 Статус: {status}\n\n"
    
    await message.answer(buttons_text)
    await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())

@router.message(F.text == "✏️ Изменить кнопку")
async def cmd_edit_button(message: Message, state: FSMContext):
    """Изменение кастомной кнопки"""
    if not await check_admin(message):
        return
    
    buttons = db.get_custom_buttons(active_only=False)
    
    if not buttons:
        await send_error_message(message, "Нет кнопок для изменения.")
        await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
        return
    
    buttons_text = "📋 Выберите кнопку для изменения (введите ID):\n\n"
    for button_data in buttons:
        button_id, name, url, is_active = button_data
        status = "✅" if is_active else "❌"
        buttons_text += f"🆔 {button_id}: {status} {name}\n"
    
    await message.answer(buttons_text, reply_markup=get_cancel_keyboard())
    await state.set_state(CustomButtonStates.waiting_for_button_id)
    await state.update_data(action="edit")  # Добавить эту строку!

@router.message(CustomButtonStates.waiting_for_button_id)
async def process_edit_button_id(message: Message, state: FSMContext):
    """Обработка ID кнопки для изменения"""
    if await cancel_state(message, state):
        return
    
    try:
        button_id = int(message.text.strip())
    except ValueError:
        await send_error_message(message, "Введите корректный числовой ID кнопки.")
        return
    
    button = db.get_custom_button_by_id(button_id)
    if not button:
        await send_error_message(message, f"Кнопка с ID {button_id} не найдена.")
        await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
        await state.clear()
        return
    
    button_id, name, url, is_active = button
    await state.update_data(button_id=button_id, current_name=name, current_url=url)
    
    await message.answer(
        f"📝 Изменение кнопки:\n\n"
        f"🆔 ID: {button_id}\n"
        f"📝 Текущее название: {name}\n"
        f"🔗 Текущая ссылка: {url}\n\n"
        f"Что хотите изменить?",
        reply_markup=get_button_edit_keyboard()
    )
    await state.set_state(CustomButtonStates.waiting_for_edit_choice)

@router.message(CustomButtonStates.waiting_for_edit_choice)
async def process_edit_choice(message: Message, state: FSMContext):
    """Обработка выбора что изменить"""
    if await cancel_state(message, state):
        return
    
    choice = message.text.strip()
    
    if choice == "📝 Изменить название":
        await message.answer("Введите новое название кнопки:", reply_markup=get_cancel_keyboard())
        await state.set_state(CustomButtonStates.waiting_for_new_name)
    elif choice == "🔗 Изменить ссылку":
        await message.answer("Введите новую ссылку:", reply_markup=get_cancel_keyboard())
        await state.set_state(CustomButtonStates.waiting_for_new_url)
    else:
        await send_error_message(message, "Выберите действие из предложенных кнопок.")

@router.message(CustomButtonStates.waiting_for_new_name)
async def process_new_button_name(message: Message, state: FSMContext):
    """Обработка нового названия кнопки"""
    if await cancel_state(message, state):
        return
    
    new_name = message.text.strip()
    if not new_name:
        await send_error_message(message, "Название не может быть пустым.")
        return
    
    user_data = await state.get_data()
    button_id = user_data.get('button_id')
    
    if db.update_custom_button(button_id, name=new_name):
        await send_success_message(message, f"Название кнопки успешно изменено на '{new_name}'")
    else:
        await send_error_message(message, "Не удалось изменить название кнопки.")
    
    await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
    await state.clear()

@router.message(CustomButtonStates.waiting_for_new_url)
async def process_new_button_url(message: Message, state: FSMContext):
    """Обработка новой ссылки кнопки"""
    if await cancel_state(message, state):
        return
    
    new_url = message.text.strip()
    if not new_url:
        await send_error_message(message, "Ссылка не может быть пустой.")
        return
    
    # Проверяем, что ссылка начинается с http:// или https://
    if not (new_url.startswith('http://') or new_url.startswith('https://')):
        new_url = 'https://' + new_url
    
    user_data = await state.get_data()
    button_id = user_data.get('button_id')
    
    if db.update_custom_button(button_id, url=new_url):
        await send_success_message(message, f"Ссылка кнопки успешно изменена на '{new_url}'")
    else:
        await send_error_message(message, "Не удалось изменить ссылку кнопки.")
    
    await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
    await state.clear()

@router.message(F.text == "🔄 Вкл/Выкл кнопку")
async def cmd_toggle_button(message: Message, state: FSMContext):
    """Включение/выключение кнопки"""
    if not await check_admin(message):
        return
    
    buttons = db.get_custom_buttons(active_only=False)
    
    if not buttons:
        await send_error_message(message, "Нет кнопок для переключения.")
        await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
        return
    
    buttons_text = "🔄 Выберите кнопку для переключения (введите ID):\n\n"
    for button_data in buttons:
        button_id, name, url, is_active = button_data
        status = "✅ Активна" if is_active else "❌ Отключена"
        buttons_text += f"🆔 {button_id}: {name} - {status}\n"
    
    await message.answer(buttons_text, reply_markup=get_cancel_keyboard())
    await state.set_state(CustomButtonStates.waiting_for_button_id)
    await state.update_data(action="toggle")

@router.message(F.text == "🗑 Удалить кнопку")
async def cmd_delete_button(message: Message, state: FSMContext):
    """Удаление кнопки"""
    if not await check_admin(message):
        return
    
    buttons = db.get_custom_buttons(active_only=False)
    
    if not buttons:
        await send_error_message(message, "Нет кнопок для удаления.")
        await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
        return
    
    buttons_text = "🗑 Выберите кнопку для удаления (введите ID):\n\n"
    for button_data in buttons:
        button_id, name, url, is_active = button_data
        buttons_text += f"🆔 {button_id}: {name}\n"
    
    await message.answer(buttons_text, reply_markup=get_cancel_keyboard())
    await state.set_state(CustomButtonStates.waiting_for_button_id)
    await state.update_data(action="delete")

# Дополнительная обработка для переключения и удаления
@router.message(CustomButtonStates.waiting_for_button_id)
async def process_button_action(message: Message, state: FSMContext):
    """Обработка действий с кнопкой по ID"""
    if await cancel_state(message, state):
        return
    
    try:
        button_id = int(message.text.strip())
    except ValueError:
        await send_error_message(message, "Введите корректный числовой ID кнопки.")
        return
    
    user_data = await state.get_data()
    action = user_data.get('action')
    
    button = db.get_custom_button_by_id(button_id)
    if not button:
        await send_error_message(message, f"Кнопка с ID {button_id} не найдена.")
        await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
        await state.clear()
        return
    
    button_id, name, url, is_active = button
    
    if action == "toggle":
        if db.toggle_custom_button(button_id):
            new_status = "отключена" if is_active else "активирована"
            await send_success_message(message, f"Кнопка '{name}' успешно {new_status}!")
        else:
            await send_error_message(message, "Не удалось переключить кнопку.")
        
        await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
        await state.clear()
    
    elif action == "delete":
        if db.delete_custom_button(button_id):
            await send_success_message(message, f"Кнопка '{name}' успешно удалена!")
        else:
            await send_error_message(message, "Не удалось удалить кнопку.")
        
        await message.answer("Управление кнопками:", reply_markup=get_button_management_keyboard())
        await state.clear()
    
    elif action == "edit":
        # Это обработка для редактирования - переходим к выбору что изменить
        await state.update_data(button_id=button_id, current_name=name, current_url=url)
        
        await message.answer(
            f"📝 Изменение кнопки:\n\n"
            f"🆔 ID: {button_id}\n"
            f"📝 Текущее название: {name}\n"
            f"🔗 Текущая ссылка: {url}\n\n"
            f"Что хотите изменить?",
            reply_markup=get_button_edit_keyboard()
        )
        await state.set_state(CustomButtonStates.waiting_for_edit_choice)
    
    else:
        # Если действие не определено - по умолчанию считаем редактированием
        await state.update_data(button_id=button_id, current_name=name, current_url=url)
        
        await message.answer(
            f"📝 Изменение кнопки:\n\n"
            f"🆔 ID: {button_id}\n"
            f"📝 Текущее название: {name}\n"
            f"🔗 Текущая ссылка: {url}\n\n"
            f"Что хотите изменить?",
            reply_markup=get_button_edit_keyboard()
        )
        await state.set_state(CustomButtonStates.waiting_for_edit_choice)