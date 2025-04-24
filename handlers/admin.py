from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

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
import re

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


# Обновите этот обработчик для отображения обоих типов клавиатур
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

# Редактирование пользователей
@router.message(F.text == "✏️ Изменить")
@router.message(Command("edituser"))
async def cmd_edit_user(message: Message, state: FSMContext):
    """Обработчик команды /edituser"""
    users = await check_admin_and_get_users(message)
    if not users:
        return

    report = "Выберите пользователя для редактирования (отправьте ID):\n\n"
    for user_id, username, _, _ in users:
        report += f"ID: {user_id} | Логин: {username}\n"

    await message.answer(report, reply_markup=get_cancel_keyboard())
    await state.set_state(EditUserStates.waiting_for_user_id)

@router.message(EditUserStates.waiting_for_user_id)
async def process_user_id_for_edit(message: Message, state: FSMContext):
    """Обработка выбора пользователя для редактирования"""
    if await cancel_state(message, state):
        return

    try:
        user_id = int(message.text)
        user = db.get_user_by_id(user_id)
        if not user:
            await send_error_message(message, "Пользователь с таким ID не найден.", reply_markup=get_admin_keyboard())
            await state.clear()
            return

        await state.update_data(user_id=user_id)
        await message.answer("Выберите действие:", reply_markup=get_user_action_keyboard())
        await state.set_state(EditUserStates.waiting_for_action)

    except ValueError:
        await send_error_message(message, "Введите корректный ID пользователя.", reply_markup=get_admin_keyboard())
        await state.clear()

@router.message(EditUserStates.waiting_for_action)
async def process_edit_action(message: Message, state: FSMContext):
    """Обработка выбора действия для редактирования пользователя"""
    if await cancel_state(message, state):
        return

    if message.text == "Изменить логин":
        await message.answer("Введите новый логин для пользователя:", reply_markup=get_cancel_keyboard())
        await state.set_state(EditUserStates.waiting_for_new_username)
    elif message.text == "Изменить пароль":
        await message.answer("Введите новый пароль для пользователя:", reply_markup=get_cancel_keyboard())
        await state.set_state(EditUserStates.waiting_for_new_password)
    else:
        await message.answer("❌ Неверное действие. Выберите действие из клавиатуры.", reply_markup=get_user_action_keyboard())

@router.message(EditUserStates.waiting_for_new_username)
async def process_new_user_username(message: Message, state: FSMContext):
    """Обработка ввода нового логина"""
    if await cancel_state(message, state):
        return

    user_data = await state.get_data()
    if db.update_username(user_data['user_id'], message.text.strip()):
        await send_success_message(message, f"Логин пользователя успешно изменен на: {message.text.strip()}")
        await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    else:
        await send_error_message(
            message, 
            "Не удалось изменить логин. Возможно, такой логин уже существует.",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

@router.message(EditUserStates.waiting_for_new_password)
async def process_new_user_password(message: Message, state: FSMContext):
    """Обработка ввода нового пароля"""
    if await cancel_state(message, state):
        return

    user_data = await state.get_data()
    if db.update_password(user_data['user_id'], message.text.strip()):
        await send_success_message(message, "Пароль пользователя успешно изменен.")
        await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    else:
        await send_error_message(
            message, 
            "Не удалось изменить пароль.",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

# Удаление пользователей
@router.message(F.text == "❌ Удалить")
@router.message(Command("deleteuser"))
async def cmd_delete_user(message: Message, state: FSMContext):
    """Обработчик команды /deleteuser"""
    users = await check_admin_and_get_users(message)
    if not users:
        return

    report = "Выберите пользователя для удаления (отправьте ID):\n\n"
    for user_id, username, _, _ in users:
        report += f"ID: {user_id} | Логин: {username}\n"
    
    await message.answer(report, reply_markup=get_cancel_keyboard())
    await state.set_state(DeleteUserStates.waiting_for_user_id)

@router.message(DeleteUserStates.waiting_for_user_id)
async def process_user_id_for_delete(message: Message, state: FSMContext):
    """Обработка ID пользователя для удаления"""
    if await cancel_state(message, state):
        return

    try:
        user_id = int(message.text.strip())
        user = db.get_user_by_id(user_id)
        if not user:
            await send_error_message(message, "Пользователь с таким ID не найден.", reply_markup=get_admin_keyboard())
            await state.clear()
            return

        if db.delete_user(user_id):
            await send_success_message(message, "Пользователь успешно удален.")
            await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
        else:
            await send_error_message(message, "Не удалось удалить пользователя.", reply_markup=get_admin_keyboard())
        
        await state.clear()

    except ValueError:
        await send_error_message(message, "Введите корректный ID пользователя.", reply_markup=get_admin_keyboard())
        await state.clear()

# Рассылка сообщений всем пользователям
@router.message(F.text == "📢 Рассылка")
@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    """Обработчик команды /broadcast для начала рассылки"""
    if not await check_admin(message):
        return
    
    # Создаем клавиатуру для выбора типа контента
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
    
    # Сохраняем выбранный тип для дальнейшей обработки
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
        await message.answer(
            "Выбран неизвестный тип контента. Пожалуйста, выберите из предложенных вариантов.",
            reply_markup=keyboard
        )

@router.message(BroadcastStates.waiting_for_media, F.photo | F.video | F.audio | F.document)
async def process_broadcast_media(message: Message, state: FSMContext):
    """Обработка загруженного медиафайла для рассылки"""
    if await cancel_state(message, state):
        return
    
    # Определяем тип медиа и сохраняем его file_id
    user_data = await state.get_data()
    content_type = user_data.get('content_type')
    
    file_id = None
    media_type = None
    
    if message.photo and content_type == "🖼 Фото":
        file_id = message.photo[-1].file_id  # Берем последнее (наибольшее) фото
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
    
    # Сохраняем информацию о медиафайле
    await state.update_data(file_id=file_id, media_type=media_type)
    
    # Предложим добавить подпись к медиафайлу
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
    
    # Получаем сохраненные данные
    user_data = await state.get_data()
    file_id = user_data.get('file_id')
    media_type = user_data.get('media_type')
    
    # Начинаем рассылку
    await start_media_broadcast(message, state, bot, file_id, media_type, caption)


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
    
    # Получаем всех пользователей с telegram_id
    users = db.get_all_users()
    sent_count = 0
    failed_count = 0
    
    # Показываем сообщение о начале рассылки
    progress_msg = await message.answer("⏳ Начинаю рассылку сообщений...")
    
    for user_id, username, telegram_id, _ in users:
        if telegram_id and telegram_id != message.from_user.id:  # Пропускаем отправителя
            try:
                # Добавляем маркер, чтобы пользователь знал, что это рассылка
                formatted_message = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{broadcast_text}"
                
                # Отправляем сообщение без изменения клавиатуры
                await bot.send_message(
                    telegram_id,
                    formatted_message,
                    parse_mode="HTML"
                )
                sent_count += 1
                
                # Обновляем сообщение о прогрессе каждые 10 отправок
                if sent_count % 10 == 0:
                    await progress_msg.edit_text(f"⏳ Отправлено: {sent_count} сообщений...")
                
                # Небольшая задержка, чтобы избежать флуда
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                # Логируем ошибку
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send message to user {username} (ID: {user_id}): {e}")
    
    result_message = f"Рассылка завершена!\n\n📊 Статистика:\n- Отправлено: {sent_count}\n- Не доставлено: {failed_count}"
    await send_success_message(message, result_message)
    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    await state.clear()


# Добавьте эти обработчики в handlers/admin.py
@router.message(F.text == "✏️ Изменить приветствие")
@router.message(Command("edit_welcome"))
async def cmd_edit_welcome(message: Message, state: FSMContext):
    """Обработчик команды для изменения приветственного сообщения"""
    if not await check_admin(message):
        return
    
    # Импортируем текущее приветственное сообщение
    from config import WELCOME_MESSAGE
    
    # Показываем текущее сообщение
    await message.answer(
        f"Текущее приветственное сообщение:\n\n{WELCOME_MESSAGE}\n\n"
        f"Введите новый текст приветственного сообщения или нажмите Отмена:",
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
    
    # Обновляем приветственное сообщение в config.py
    try:
        # Открываем config.py для чтения
        with open('config.py', 'r', encoding='utf-8') as file:
            config_content = file.read()
        
        # Находим строку с WELCOME_MESSAGE и заменяем ее
        import re
        pattern = r'WELCOME_MESSAGE\s*=\s*f?""".*?"""'
        replacement = f'WELCOME_MESSAGE = f"""{new_welcome_message}"""'
        new_config = re.sub(pattern, replacement, config_content, flags=re.DOTALL)
        
        # Записываем обновленный контент обратно
        with open('config.py', 'w', encoding='utf-8') as file:
            file.write(new_config)
        
        # Обновляем переменную в текущей сессии
        import sys
        import config
        from importlib import reload
        reload(config)
        
        await send_success_message(message, "Приветственное сообщение успешно обновлено!")
        await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    except Exception as e:
        logger.error(f"Failed to update welcome message: {e}")
        await send_error_message(
            message,
            f"Не удалось обновить приветственное сообщение: {str(e)}",
            reply_markup=get_admin_keyboard()
        )
    
    await state.clear()

async def start_media_broadcast(message: Message, state: FSMContext, bot: Bot, file_id: str, media_type: str, caption: str = ""):
    """Функция для рассылки медиафайла всем пользователям"""
    # Получаем всех пользователей с telegram_id
    users = db.get_all_users()
    sent_count = 0
    failed_count = 0
    
    # Показываем сообщение о начале рассылки
    progress_msg = await message.answer("⏳ Начинаю рассылку медиафайлов...")
    
    # Форматируем подпись, если она есть
    if caption:
        formatted_caption = f"<b>Сообщение от PARTNERS 🔗:</b>\n\n{caption}"
    else:
        formatted_caption = "<b>Сообщение от PARTNERS 🔗</b>"
    
    for user_id, username, telegram_id, _ in users:
        if telegram_id and telegram_id != message.from_user.id:  # Пропускаем отправителя
            try:
                # Отправляем соответствующий тип медиа
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
                
                # Обновляем сообщение о прогрессе каждые 10 отправок
                if sent_count % 10 == 0:
                    await progress_msg.edit_text(f"⏳ Отправлено: {sent_count} медиафайлов...")
                
                # Небольшая задержка, чтобы избежать флуда
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed_count += 1
                # Логируем ошибку
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send media to user {username} (ID: {user_id}): {e}")
    
    result_message = f"Рассылка медиафайлов завершена!\n\n📊 Статистика:\n- Отправлено: {sent_count}\n- Не доставлено: {failed_count}"
    await send_success_message(message, result_message)
    await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
    await state.clear()

def setup(dp: Dispatcher):
    """Регистрация обработчиков администратора"""
    dp.include_router(router)