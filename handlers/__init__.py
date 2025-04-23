# handlers/__init__.py
from . import auth, user, admin

def register_all_handlers(dp):
    """Регистрация всех обработчиков"""
    auth.setup(dp)
    user.setup(dp)
    admin.setup(dp)