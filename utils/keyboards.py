from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard():
    """Клавиатура для неавторизованных пользователей"""
    kb = [
        [KeyboardButton(text='🔑 Авторизоваться')]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_main_keyboard():
    """Инлайн-клавиатура для авторизованных пользователей"""
    kb = [
        [
            InlineKeyboardButton(text='🔄 Изменить ссылку', callback_data='set_link'),
            InlineKeyboardButton(text='🔗 Моя ссылка', callback_data='my_link')
        ],
        [InlineKeyboardButton(text='🚪 Выйти', callback_data='logout')]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_admin_keyboard():
    """Обычная клавиатура для администраторов"""
    kb = [
        [KeyboardButton(text='🔄 Изменить ссылку'), KeyboardButton(text='🔗 Моя ссылка')],
        [KeyboardButton(text='👥 Пользователи'), KeyboardButton(text='🏪 Добавить')],
        [KeyboardButton(text='✏️ Изменить'), KeyboardButton(text='❌ Удалить')],
        [KeyboardButton(text='📢 Рассылка')],
        [KeyboardButton(text='🚪 Выйти')]
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