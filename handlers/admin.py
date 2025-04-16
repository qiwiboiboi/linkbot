from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command

from database import db
from models import AddUserStates, EditUserStates, DeleteUserStates
from utils.keyboards import get_admin_keyboard, get_user_action_keyboard, get_cancel_keyboard
from utils.helpers import (
    check_admin,
    cancel_state,
    format_user_list,
    send_error_message,
    send_success_message
)

async def check_admin_and_get_users(message: types.Message) -> list:
    """Проверка админа и получение списка пользователей"""
    if not await check_admin(message):
        return None
        
    users = db.get_all_users()
    if not users:
        await send_error_message(message, "Список пользователей пуст.", reply_markup=get_admin_keyboard())
        return None
    return users

# Команды просмотра и создания пользователей
async def cmd_admin(message: types.Message):
    """Обработчик команды /admin"""
    users = await check_admin_and_get_users(message)
    if not users:
        return
    
    report = format_user_list(users)
    if users:
        report += "\nДля добавления нового пользователя используйте команду /adduser"
    
    await message.answer(report, reply_markup=get_admin_keyboard())

async def cmd_add_user(message: types.Message):
    """Обработчик команды /adduser"""
    if not await check_admin(message):
        return
    
    await message.answer("Введите логин для нового пользователя:", reply_markup=get_cancel_keyboard())
    await AddUserStates.waiting_for_username.set()

async def process_new_username(message: types.Message, state: FSMContext):
    """Обработка ввода логина для нового пользователя"""
    if await cancel_state(message, state):
        return
    
    username = message.text.strip()
    if db.get_user_by_username(username):
        await send_error_message(message, f"Пользователь с логином '{username}' уже существует. Попробуйте другой логин.")
        return
    
    await state.update_data(username=username)
    await message.answer("Теперь введите пароль для нового пользователя:", reply_markup=get_cancel_keyboard())
    await AddUserStates.waiting_for_password.set()

async def process_new_password(message: types.Message, state: FSMContext):
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
    
    await state.finish()

# Редактирование пользователей
async def cmd_edit_user(message: types.Message):
    """Обработчик команды /edituser"""
    users = await check_admin_and_get_users(message)
    if not users:
        return

    report = "Выберите пользователя для редактирования (отправьте ID):\n\n"
    for user_id, username, _, _ in users:
        report += f"ID: {user_id} | Логин: {username}\n"

    await message.answer(report, reply_markup=get_cancel_keyboard())
    await EditUserStates.waiting_for_user_id.set()

async def process_user_id_for_edit(message: types.Message, state: FSMContext):
    """Обработка выбора пользователя для редактирования"""
    if await cancel_state(message, state):
        return

    try:
        user_id = int(message.text)
        user = db.get_user_by_id(user_id)
        if not user:
            await send_error_message(message, "Пользователь с таким ID не найден.", reply_markup=get_admin_keyboard())
            await state.finish()
            return

        await state.update_data(user_id=user_id)
        await message.answer("Выберите действие:", reply_markup=get_user_action_keyboard())
        await EditUserStates.waiting_for_action.set()

    except ValueError:
        await send_error_message(message, "Введите корректный ID пользователя.", reply_markup=get_admin_keyboard())
        await state.finish()

async def process_edit_action(message: types.Message, state: FSMContext):
    """Обработка выбора действия для редактирования пользователя"""
    if await cancel_state(message, state):
        return

    if message.text == "Изменить логин":
        await message.answer("Введите новый логин для пользователя:", reply_markup=get_cancel_keyboard())
        await EditUserStates.waiting_for_new_username.set()
    elif message.text == "Изменить пароль":
        await message.answer("Введите новый пароль для пользователя:", reply_markup=get_cancel_keyboard())
        await EditUserStates.waiting_for_new_password.set()
    else:
        await message.answer("❌ Неверное действие. Выберите действие из клавиатуры.", reply_markup=get_user_action_keyboard())

async def process_new_user_username(message: types.Message, state: FSMContext):
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
    
    await state.finish()

async def process_new_user_password(message: types.Message, state: FSMContext):
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
    
    await state.finish()

# Удаление пользователей
async def cmd_delete_user(message: types.Message):
    """Обработчик команды /deleteuser"""
    users = await check_admin_and_get_users(message)
    if not users:
        return

    report = "Выберите пользователя для удаления (отправьте ID):\n\n"
    for user_id, username, _, _ in users:
        report += f"ID: {user_id} | Логин: {username}\n"
    
    await message.answer(report, reply_markup=get_cancel_keyboard())
    await DeleteUserStates.waiting_for_user_id.set()

async def process_user_id_for_delete(message: types.Message, state: FSMContext):
    """Обработка ID пользователя для удаления"""
    if await cancel_state(message, state):
        return

    try:
        user_id = int(message.text.strip())
        user = db.get_user_by_id(user_id)
        if not user:
            await send_error_message(message, "Пользователь с таким ID не найден.", reply_markup=get_admin_keyboard())
            await state.finish()
            return

        if db.delete_user(user_id):
            await send_success_message(message, "Пользователь успешно удален.")
            await message.answer("Выберите действие:", reply_markup=get_admin_keyboard())
        else:
            await send_error_message(message, "Не удалось удалить пользователя.", reply_markup=get_admin_keyboard())
        
        await state.finish()

    except ValueError:
        await send_error_message(message, "Введите корректный ID пользователя.", reply_markup=get_admin_keyboard())
        await state.finish()

def register_admin_handlers(dp: Dispatcher):
    """Регистрация обработчиков администратора"""
    # Просмотр и создание
    dp.register_message_handler(cmd_admin, text="👥 Пользователи")
    dp.register_message_handler(cmd_admin, Command("admin"))
    dp.register_message_handler(cmd_add_user, text="🏪 Добавить")
    dp.register_message_handler(cmd_add_user, Command("adduser"))
    dp.register_message_handler(process_new_username, state=AddUserStates.waiting_for_username)
    dp.register_message_handler(process_new_password, state=AddUserStates.waiting_for_password)
    
    # Редактирование
    dp.register_message_handler(cmd_edit_user, text="✏️ Изменить")
    dp.register_message_handler(cmd_edit_user, Command("edituser"))
    dp.register_message_handler(process_user_id_for_edit, state=EditUserStates.waiting_for_user_id)
    dp.register_message_handler(process_edit_action, state=EditUserStates.waiting_for_action)
    dp.register_message_handler(process_new_user_username, state=EditUserStates.waiting_for_new_username)
    dp.register_message_handler(process_new_user_password, state=EditUserStates.waiting_for_new_password)
    
    # Удаление
    dp.register_message_handler(cmd_delete_user, text="❌ Удалить")
    dp.register_message_handler(cmd_delete_user, Command("deleteuser"))
    dp.register_message_handler(process_user_id_for_delete, state=DeleteUserStates.waiting_for_user_id)
