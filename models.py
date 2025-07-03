# models.py
from aiogram.fsm.state import State, StatesGroup

class AuthStates(StatesGroup):
    """Состояния для процесса аутентификации"""
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_captcha = State()

class RegistrationStates(StatesGroup):
    """Состояния для процесса регистрации"""
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_password_confirm = State()

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

class BroadcastStates(StatesGroup):
    """Состояния для рассылки сообщений всем пользователям"""
    waiting_for_content = State()  # Универсальное состояние для любого контента

class BroadcastByIdStates(StatesGroup):
    """Состояния для рассылки сообщений по ID пользователя"""
    waiting_for_user_id = State()  # Ожидание ввода ID пользователя
    waiting_for_content = State()  # Универсальное состояние для любого контента

class WelcomeMessageStates(StatesGroup):
    """Состояния для редактирования приветственного сообщения"""
    waiting_for_message = State()

class CustomButtonStates(StatesGroup):
    """Состояния для управления кастомными кнопками"""
    waiting_for_button_name = State()
    waiting_for_button_url = State()
    waiting_for_button_id = State()
    waiting_for_edit_choice = State()
    waiting_for_new_name = State()
    waiting_for_new_url = State()
    waiting_for_toggle_id = State()
    waiting_for_delete_id = State()
    
class ChannelStates(StatesGroup):
    """Состояния для управления каналами"""
    waiting_for_channel_type = State()
    waiting_for_channel_id = State()

class MessageStates(StatesGroup):
    """Состояния для отправки сообщений пользователями"""
    waiting_for_message = State()