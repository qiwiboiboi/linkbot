# handlers/__init__.py
from . import auth, user, admin

def register_all_handlers(dp):
    """Регистрация всех обработчиков"""
    auth.setup(dp)      # Сначала авторизация
    admin.setup(dp)     # Потом админ
    user.setup(dp)      # В конце пользователь