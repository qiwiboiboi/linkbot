# utils/keyboards.py с отладкой
import logging
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)

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
    """Обычная клавиатура для авторизованных пользователей с кастомными кнопками"""
    try:
        # Импортируем здесь, чтобы избежать циклического импорта
        from database import db
        
        # Базовые кнопки
        kb = [
            [KeyboardButton(text='🔗 Моё актуальное'), KeyboardButton(text='🔄 Изменить')],
            [KeyboardButton(text='✉️ Написать сообщение')]
        ]
        
        # Добавляем кастомные кнопки
        try:
            custom_buttons = db.get_custom_buttons(active_only=True)
            logger.info(f"Found {len(custom_buttons)} custom buttons")
            
            # Группируем кастомные кнопки по 2 в строке
            custom_rows = []
            current_row = []
            
            for button_data in custom_buttons:
                button_name = button_data[1]  # name
                current_row.append(KeyboardButton(text=button_name))
                logger.info(f"Added custom button: {button_name}")
                
                # Если в строке уже 2 кнопки, добавляем строку и начинаем новую
                if len(current_row) == 2:
                    custom_rows.append(current_row)
                    current_row = []
            
            # Если остались кнопки в незавершенной строке, добавляем их
            if current_row:
                custom_rows.append(current_row)
            
            # Добавляем все строки с кастомными кнопками
            kb.extend(custom_rows)
                
        except Exception as e:
            logger.error(f"Error getting custom buttons: {e}")
            # Если возникла ошибка с базой данных, просто пропускаем кастомные кнопки
            pass
        
        # Кнопка выхода в конце
        kb.append([KeyboardButton(text='🚪 Выйти')])
        
        keyboard = ReplyKeyboardMarkup(
            keyboard=kb, 
            resize_keyboard=True, 
            one_time_keyboard=False,
            is_persistent=True
        )
        
        logger.info(f"Created main keyboard with {len(kb)} rows")
        return keyboard
        
    except Exception as e:
        logger.error(f"Error creating main keyboard: {e}")
        # Fallback клавиатура без кастомных кнопок
        kb = [
            [KeyboardButton(text='🔗 Моё актуальное'), KeyboardButton(text='🔄 Изменить')],
            [KeyboardButton(text='✉️ Написать сообщение')],
            [KeyboardButton(text='🚪 Выйти')]
        ]
        return ReplyKeyboardMarkup(
            keyboard=kb, 
            resize_keyboard=True, 
            one_time_keyboard=False,
            is_persistent=True
        )

def get_admin_inline_keyboard():
    """Инлайн-клавиатура для базовых действий администраторов"""
    kb = [
        [
            InlineKeyboardButton(text='🔗 Моё актуальное', callback_data='my_link'),
            InlineKeyboardButton(text='🔄 Изменить', callback_data='set_link')
        ],
        [InlineKeyboardButton(text='✉️ Написать сообщение', callback_data='send_message')],
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
        [KeyboardButton(text='📋 Канал для ссылок'), KeyboardButton(text='💬 Канал для сообщений')],
        [KeyboardButton(text='🔘 Управление кнопками')]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb, 
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True
    )

def get_button_management_keyboard():
    """Клавиатура для управления кастомными кнопками"""
    kb = [
        [KeyboardButton(text='➕ Добавить кнопку'), KeyboardButton(text='📋 Список кнопок')],
        [KeyboardButton(text='✏️ Изменить кнопку'), KeyboardButton(text='🗑 Удалить кнопку')],
        [KeyboardButton(text='🔄 Вкл/Выкл кнопку')],
        [KeyboardButton(text='↩️ Назад к админке')]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb, 
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True
    )

def get_button_edit_keyboard():
    """Клавиатура для выбора что изменить в кнопке"""
    kb = [
        [KeyboardButton(text='📝 Изменить название'), KeyboardButton(text='🔗 Изменить ссылку')],
        [KeyboardButton(text='❌ Отмена')]
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