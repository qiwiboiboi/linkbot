from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard():
    """Клавиатура для неавторизованных пользователей"""
    kb = [
        [KeyboardButton(text='🔑 Авторизоваться')]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_start_button():
    """Инлайн-клавиатура с кнопкой Старт для неавторизованных пользователей"""
    kb = [
        [InlineKeyboardButton(text='🚀 Старт', callback_data='start_bot')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_auth_keyboard():
    """Клавиатура для выбора между авторизацией и регистрацией"""
    kb = [
        [KeyboardButton(text='🔑 Авторизоваться'), KeyboardButton(text='📝 Регистрация')]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_keyboard():
    """Обычная клавиатура для авторизованных пользователей"""
    kb = [
        [KeyboardButton(text='🔗 Моё актуальное'), KeyboardButton(text='🔄 Изменить')],
        [KeyboardButton(text='✉️ Написать сообщение')],
        [KeyboardButton(text='🚪 Выйти')]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=False)

def get_admin_inline_keyboard():
    """Инлайн-клавиатура для базовых действий администраторов"""
    kb = [
        [
            InlineKeyboardButton(text='🔗 Моё актуальное', callback_data='my_link'),
            InlineKeyboardButton(text='🔄 Изменить', callback_data='set_link')
        ],
        [InlineKeyboardButton(text='🚪 Выйти', callback_data='logout')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_keyboard():
    """Обычная клавиатура для функций администрирования"""
    kb = [
        [KeyboardButton(text='👥 Пользователи'), KeyboardButton(text='🏪 Добавить')],
        [KeyboardButton(text='✏️ Изменить'), KeyboardButton(text='❌ Удалить')],
        [KeyboardButton(text='📢 Рассылка'), KeyboardButton(text='📩 Сообщение')],
        [KeyboardButton(text='✏️ Изменить приветствие')],
        [KeyboardButton(text='📋 Канал для ссылок'), KeyboardButton(text='💬 Канал для сообщений')]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_user_action_keyboard():
    """Клавиатура для выбора действия с пользователем"""
    kb = [
        [KeyboardButton(text='Изменить логин'), KeyboardButton(text='Изменить пароль')],
        [KeyboardButton(text='❌ Отмена')]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_keyboard():
    """Клавиатура только с кнопкой отмены"""
    kb = [
        [KeyboardButton(text='❌ Отмена')]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)