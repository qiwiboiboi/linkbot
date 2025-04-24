from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from config import get_welcome_message, update_welcome_message

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

# Дополнительные импорты
import asyncio
import logging

# Получаем логгер
logger = logging.getLogger(__name__)

# Создаем роутер для админских команд
router = Router()

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

# Рассылка сообщений всем пользователям
@router.message(F.text == "📢 Рассылка")
@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Обработчик команды /broadcast для начала рассылки"""
    if not await check_admin(message):
        return
    
    kb = [
        [KeyboardButton(text='📝 Текст'), KeyboardButton(text='🖼 Фото')],
        [KeyboardButton(text='🎥 Видео'), KeyboardButton(text='🎵 Аудио')],
        [KeyboardButton(text='📎 Документ')],
        [KeyboardButton(text='❌ Отмена')]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(
        "Выберите тип содержимого для рассылки:",
        reply_markup=keyboard
    )
    await state.set_state(BroadcastStates.select_type)

@router.message(BroadcastStates.select_type)
async def process_broadcast_type(message: Message, state: FSMContext):
    """Обработка выбора типа контента для рассылки"""
    if await cancel_state(message, state):
        return
    
    content_type = message.text.strip()
    await state.update_data(content_type=content_type)
    
    if content_type == "📝 Текст":
        await message.answer(
            "Введите текст сообщения для рассылки всем пользователям:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(BroadcastStates.waiting_for_message)
    elif content_type in ["🖼 Фото", "🎥 Видео", "🎵 Аудио", "📎 Документ"]:
        content_type_mapping = {
            "🖼 Фото": "фото",
            "🎥 Видео": "видео",
            "🎵 Аудио": "аудио",
            "📎 Документ": "документ",
        }
        
        await message.answer(
            f"Отправьте {content_type_mapping[content_type]} для рассылки:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(BroadcastStates.waiting_for_media)
    else:
        keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
        await message.answer(
            "Выбран неизвестный тип контента. Пожалуйста, выберите из предложенных вариантов.",
            reply_markup=keyboard
        )

@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Обработка текста сообщения для рассылки"""
    if await cancel_state(message, state):
        return
    
    broadcast_text = message.text.strip()
    if not broadcast_text:
        await send_error_message(message, "Текст сообщения не может быть пустым.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    
    users = db.get_all_users()
    sent_count = 0
    failed_count = 0
    
    progress_msg = await message.answer("⏳ Начинаю рассылку сообщений...")
    
    for user_id, username, telegram_id, _ in users:
        if telegram_id and telegram_id != message.from_user.id:  # Пропускаем отправителя
            try:
                formatted_message = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{broadcast_text}"
                await bot.send_message(
                    telegram_id,
                    formatted_message,
                    parse_mode="HTML"
                )
                sent_count += 1
                
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

@router.message(BroadcastStates.waiting_for_media, F.photo | F.video | F.audio | F.document)
async def process_broadcast_media(message: Message, state: FSMContext):
    """Обработка загруженного медиафайла для рассылки"""
    if await cancel_state(message, state):
        return
    
    user_data = await state.get_data()
    content_type = user_data.get('content_type')
    
    file_id = None
    media_type = None
    
    if message.photo and content_type == "🖼 Фото":
        file_id = message.photo[-1].file_id
        media_type = "photo"
    elif message.video and content_type == "🎥 Видео":
        file_id = message.video.file_id
        media_type = "video"
    elif message.audio and content_type == "🎵 Аудио":
        file_id = message.audio.file_id
        media_type = "audio"
    elif message.document and content_type == "📎 Документ":
        file_id = message.document.file_id
        media_type = "document"
    else:
        await message.answer(
            f"Отправленный файл не соответствует выбранному типу контента ({content_type}). "
            f"Пожалуйста, отправьте правильный тип файла или нажмите Отмена.",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(file_id=file_id, media_type=media_type)
    await message.answer(
        "Хотите добавить текст к этому медиафайлу? Если да, введите текст. "
        "Если нет, отправьте сообщение с текстом 'Без текста'.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_caption)

@router.message(BroadcastStates.waiting_for_caption)
async def process_broadcast_caption(message: Message, state: FSMContext, bot: Bot):
    """Обработка подписи к медиафайлу и начало рассылки"""
    if await cancel_state(message, state):
        return
    
    caption = message.text.strip()
    if caption.lower() == "без текста":
        caption = ""
    
    user_data = await state.get_data()
    file_id = user_data.get('file_id')
    media_type = user_data.get('media_type')
    
    users = db.get_all_users()
    sent_count = 0
    failed_count = 0
    
    progress_msg = await message.answer("⏳ Начинаю рассылку медиафайлов...")
    
    if caption:
        formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}"
    else:
        formatted_caption = "<b>Сообщение от PARTNERS 🔗</b>"
    
    for user_id, username, telegram_id, _ in users:
        if telegram_id and telegram_id != message.from_user.id:
            try:
                if media_type == "photo":
                    await bot.send_photo(
                        telegram_id, 
                        photo=file_id, 
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                elif media_type == "video":
                    await bot.send_video(
                        telegram_id, 
                        video=file_id, 
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                elif media_type == "audio":
                    await bot.send_audio(
                        telegram_id, 
                        audio=file_id, 
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                elif media_type == "document":
                    await bot.send_document(
                        telegram_id, 
                        document=file_id, 
                        caption=formatted_caption,
                        parse_mode="HTML"
                    )
                
                sent_count += 1
                
                if sent_count % 10 == 0:
                    await progress_msg.edit_text(f"⏳ Отправлено: {sent_count} медиафайлов...")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to send media to user {username} (ID: {user_id}): {e}")
    
    result_message = f"Рассылка медиафайлов завершена!\n\n📊 Статистика:\n- Отправлено: {sent_count}\n- Не доставлено: {failed_count}"
    await send_success_message(message, result_message)
    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    await state.clear()

def setup(dp: Dispatcher):
    """Регистрация обработчиков администратора"""
    dp.include_router(router)
