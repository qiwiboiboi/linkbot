from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_start_keyboard():
    """Клавиатура для неавторизованных пользователей"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('🔑 Авторизоваться'))
    return keyboard

def get_main_keyboard():
    """Клавиатура для авторизованных пользователей"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('🔄 Изменить ссылку'), KeyboardButton('🔗 Моя ссылка'))
    keyboard.add(KeyboardButton('🚪 Выйти'))
    return keyboard

def get_admin_keyboard():
    """Клавиатура для администраторов"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton('🔄 Изменить ссылку'), KeyboardButton('🔗 Моя ссылка'))
    keyboard.row(KeyboardButton('👥 Пользователи'), KeyboardButton('🏪 Добавить'))
    keyboard.row(KeyboardButton('✏️ Изменить'), KeyboardButton('❌ Удалить'))
    keyboard.add(KeyboardButton('🚪 Выйти'))
    return keyboard

def get_user_action_keyboard():
    """Клавиатура для выбора действия с пользователем"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton('Изменить логин'), KeyboardButton('Изменить пароль'))
    keyboard.add(KeyboardButton('❌ Отмена'))
    return keyboard

def get_cancel_keyboard():
    """Клавиатура только с кнопкой отмены"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton('❌ Отмена'))
    return keyboard
