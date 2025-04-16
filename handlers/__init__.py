# handlers/__init__.py
from .auth import register_auth_handlers
from .user import register_user_handlers
from .admin import register_admin_handlers

def register_all_handlers(dp):
    """Регистрация всех обработчиков"""
    register_auth_handlers(dp)
    register_user_handlers(dp)
    register_admin_handlers(dp)