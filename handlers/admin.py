from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import get_welcome_message, update_welcome_message
from models import BroadcastByIdStates, ChannelStates
from database import db
from models import AddUserStates, EditUserStates, DeleteUserStates, BroadcastStates, WelcomeMessageStates
from utils.keyboards import (
    get_admin_keyboard, 
    get_user_action_keyboard, 
    get_cancel_keyboard,
    get_admin_inline_keyboard,
    get_main_keyboard,
    get_start_keyboard
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

@router.message(F.text == "📋 Канал для ссылок")
async def cmd_set_links_channel(message: Message, state: FSMContext):
    """Обработчик команды установки канала для ссылок"""
    if not await check_admin(message):
        return

    await message.answer(
        "Введите ID канала для публикации ссылок.\n"
        "Важно: бот должен быть администратором канала.",
        reply_markup=get_cancel_keyboard()
    )
    await state.update_data(channel_type="links")
    await state.set_state(ChannelStates.waiting_for_channel_id)

@router.message(F.text == "💬 Канал для сообщений")
async def cmd_set_messages_channel(message: Message, state: FSMContext):
    """Обработчик команды установки канала для сообщений"""
    if not await check_admin(message):
        return

    await message.answer(
        "Введите ID канала для публикации сообщений пользователей.\n"
        "Важно: бот должен быть администратором канала.",
        reply_markup=get_cancel_keyboard()
    )
    await state.update_data(channel_type="messages")
    await state.set_state(ChannelStates.waiting_for_channel_id)

@router.message(ChannelStates.waiting_for_channel_id)
async def process_channel_id(message: Message, state: FSMContext, bot: Bot):
    """Обработка ввода ID канала"""
    if await cancel_state(message, state):
        return

    channel_id = message.text.strip()
    state_data = await state.get_data()
    channel_type = state_data.get('channel_type')

    try:
        # Пытаемся отправить тестовое сообщение в канал
        test_message = await bot.send_message(
            chat_id=channel_id,
            text="✅ Тестовое сообщение для проверки прав бота"
        )
        # Если сообщение отправлено успешно, удаляем его
        await test_message.delete()

        # Сохраняем ID канала в базе данных
        if db.set_channel(channel_type, channel_id):
            channel_type_text = "ссылок" if channel_type == "links" else "сообщений"
            await send_success_message(
                message,
                f"Канал для {channel_type_text} успешно установлен!"
            )
        else:
            await send_error_message(
                message,
                "Не удалось сохранить настройки канала"
            )

    except Exception as e:
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


# Добавьте следующие функции в файл handlers/admin.py
# (разместите их перед функцией setup(dp))


@router.message(F.text == "📩 Сообщение ")
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
    
    # Формируем список пользователей с их ID
    user_list = "📋 Список пользователей:\n\n"
    for user_id, username, telegram_id, link in users:
        user_list += f"👤 ID: {user_id} | Логин: {username}"
        if telegram_id:
            user_list += " | ✅ Авторизован"
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
    
    # Сохраняем ID пользователя в состоянии
    await state.update_data(target_user_id=user_id, target_username=user[0])
    
    # Теперь запрашиваем контент для отправки без выбора типа
    await message.answer(
        f"Выбран пользователь: {user[0]} (ID: {user_id})\n"
        f"Отправьте любой контент (текст, фото, видео, аудио, документ), который нужно отправить пользователю:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BroadcastByIdStates.waiting_for_content)

# Обработчик для любого типа контента в рассылке по ID
@router.message(BroadcastByIdStates.waiting_for_content)
async def process_broadcast_by_id_content(message: Message, state: FSMContext, bot: Bot):
    """Обработка любого контента для рассылки по ID"""
    if await cancel_state(message, state):
        return
    
    # Получаем данные о целевом пользователе из состояния
    user_data = await state.get_data()
    target_user_id = user_data.get('target_user_id')
    target_username = user_data.get('target_username')
    
    # Получаем Telegram ID пользователя из базы данных
    user = db.get_user_by_id(target_user_id)
    if not user or not user[1]:  # user[1] - это telegram_id
        await send_error_message(
            message, 
            f"Не удалось отправить сообщение пользователю {target_username} (ID: {target_user_id}). "
            f"Пользователь не авторизован в боте.",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return
    
    telegram_id = user[1]
    
    try:
        # Определяем тип контента и отправляем соответствующим образом
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
            # Берем фото максимального размера
            photo = message.photo[-1]
            caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
            formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
            
            await bot.send_photo(
                telegram_id,
                photo=photo.file_id,
                caption=formatted_caption,
                parse_mode="HTML"
            )
            success = True
        
        # Видео
        elif message.video:
            caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
            formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
            
            await bot.send_video(
                telegram_id,
                video=message.video.file_id,
                caption=formatted_caption,
                parse_mode="HTML"
            )
            success = True
        
        # Аудио
        elif message.audio:
            caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
            formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
            
            await bot.send_audio(
                telegram_id,
                audio=message.audio.file_id,
                caption=formatted_caption,
                parse_mode="HTML"
            )
            success = True
        
        # Документ
        elif message.document:
            caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
            formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
            
            await bot.send_document(
                telegram_id,
                document=message.document.file_id,
                caption=formatted_caption,
                parse_mode="HTML"
            )
            success = True
            
        # Голосовое сообщение
        elif message.voice:
            caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
            formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
            
            await bot.send_voice(
                telegram_id,
                voice=message.voice.file_id,
                caption=formatted_caption,
                parse_mode="HTML"
            )
            success = True
            
        # Стикер
        elif message.sticker:
            await bot.send_sticker(
                telegram_id,
                sticker=message.sticker.file_id
            )
            success = True
            
        # Анимация (GIF)
        elif message.animation:
            caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
            formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
            
            await bot.send_animation(
                telegram_id,
                animation=message.animation.file_id,
                caption=formatted_caption,
                parse_mode="HTML"
            )
            success = True
        
        # Если не удалось определить тип контента
        if not success:
            await send_error_message(
                message, 
                f"Не удалось определить тип отправляемого контента.",
                reply_markup=get_admin_keyboard()
            )
            await state.clear()
            return
        
        await send_success_message(
            message, 
            f"Сообщение успешно отправлено пользователю {target_username} (ID: {target_user_id}).",
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to send message to user {target_username} (ID: {target_user_id}): {e}")
        await send_error_message(
            message, 
            f"Ошибка при отправке сообщения пользователю {target_username} (ID: {target_user_id}): {e}",
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
    
    progress_msg = await message.answer("⏳ Начинаю рассылку...")
    
    for user_id, username, telegram_id, _ in users:
        if telegram_id and telegram_id != message.from_user.id:  # Пропускаем отправителя
            try:
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
                    caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
                    formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
                    
                    await bot.send_photo(
                        telegram_id,
                        photo=photo.file_id,
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                    success = True
                
                # Видео
                elif message.video:
                    caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
                    formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
                    
                    await bot.send_video(
                        telegram_id,
                        video=message.video.file_id,
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                    success = True
                
                # Аудио
                elif message.audio:
                    caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
                    formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
                    
                    await bot.send_audio(
                        telegram_id,
                        audio=message.audio.file_id,
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                    success = True
                
                # Документ
                elif message.document:
                    caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
                    formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
                    
                    await bot.send_document(
                        telegram_id,
                        document=message.document.file_id,
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                    success = True
                
                # Голосовое сообщение
                elif message.voice:
                    caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
                    formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
                    
                    await bot.send_voice(
                        telegram_id,
                        voice=message.voice.file_id,
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                    success = True
                
                # Стикер
                elif message.sticker:
                    await bot.send_sticker(
                        telegram_id,
                        sticker=message.sticker.file_id
                    )
                    success = True
                
                # Анимация (GIF)
                elif message.animation:
                    caption = message.caption or "<b>Сообщение от PARTNERS 🔗</b>"
                    formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}" if message.caption else caption
                    
                    await bot.send_animation(
                        telegram_id,
                        animation=message.animation.file_id,
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                    success = True
                
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                
                if sent_count % 10 == 0:
                    await progress_msg.edit_text(f"⏳ Отправлено: {sent_count} сообщений...")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send message to user {username} (ID: {user_id}): {e}")
    
    result_message = f"Рассылка завершена!\n\n📊 Статистика:\n- Отправлено: {sent_count}\n- Не доставлено: {failed_count}"
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
    """Обработчик команды /admin"""
    users = await check_admin_and_get_users(message)
    if not users:
        return
    
    report = format_user_list(users)
    if users:
        report += "\nДля добавления нового пользователя используйте команду /adduser"
    
    await message.answer(report)
    await message.answer(
        "Функции администрирования:",
        reply_markup=get_admin_keyboard()
    )

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
