# utils/url_validator.py
import re
from urllib.parse import urlparse

def validate_and_fix_url(url: str) -> str:
    """
    Валидация и исправление URL для инлайн-кнопок Telegram
    
    Args:
        url: исходный URL
        
    Returns:
        str: исправленный валидный URL
    """
    url = url.strip()
    
    # Обработка Telegram username (@username)
    if url.startswith('@'):
        username = url[1:]  # Убираем @
        return f"https://t.me/{username}"
    
    # Обработка ссылок вида t.me/username
    if url.startswith('t.me/'):
        return f"https://{url}"
    
    # Обработка ссылок вида https://t.me/@username
    if 't.me/@' in url:
        url = url.replace('t.me/@', 't.me/')
    
    # Если URL не начинается с протокола, добавляем https://
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    # Проверяем, что URL валидный
    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("Invalid URL")
        return url
    except:
        # Если URL всё равно невалидный, возвращаем как есть
        # (будет показана ошибка при создании кнопки)
        return url

def is_valid_url(url: str) -> bool:
    """
    Проверка валидности URL
    
    Args:
        url: URL для проверки
        
    Returns:
        bool: True если URL валидный
    """
    try:
        parsed = urlparse(url)
        return bool(parsed.netloc and parsed.scheme in ['http', 'https'])
    except:
        return False

def get_url_display_name(url: str) -> str:
    """
    Получение отображаемого имени для URL
    
    Args:
        url: URL
        
    Returns:
        str: отображаемое имя
    """
    try:
        parsed = urlparse(url)
        if 't.me' in parsed.netloc:
            return "Telegram"
        elif parsed.netloc:
            return parsed.netloc
        else:
            return "Ссылка"
    except:
        return "Ссылка"