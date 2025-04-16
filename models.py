# models.py
from aiogram.dispatcher.filters.state import State, StatesGroup

class AuthStates(StatesGroup):
    """Состояния для процесса аутентификации"""
    waiting_for_username = State()
    waiting_for_password = State()

class LinkStates(StatesGroup):
    """Состояния для установки ссылки"""
    waiting_for_link = State()

# Добавляем новые состояния для создания пользователя
class AddUserStates(StatesGroup):
    """Состояния для создания нового пользователя админом"""
    waiting_for_username = State()
    waiting_for_password = State()