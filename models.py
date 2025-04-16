# models.py
from aiogram.dispatcher.filters.state import State, StatesGroup

class AuthStates(StatesGroup):
    """Состояния для процесса аутентификации"""
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_captcha = State()

class LinkStates(StatesGroup):
    """Состояния для установки ссылки"""
    waiting_for_link = State()

class AddUserStates(StatesGroup):
    """Состояния для создания нового пользователя админом"""
    waiting_for_username = State()
    waiting_for_password = State()

class EditUserStates(StatesGroup):
    """Состояния для редактирования пользователя админом"""
    waiting_for_user_id = State()
    waiting_for_action = State()
    waiting_for_new_username = State()
    waiting_for_new_password = State()

class DeleteUserStates(StatesGroup):
    """Состояния для удаления пользователя админом"""
    waiting_for_user_id = State()
