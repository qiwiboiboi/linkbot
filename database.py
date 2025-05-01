import sqlite3
import logging
from config import DATABASE_PATH

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Инициализация соединения с базой данных"""
        self.connection = sqlite3.connect(DATABASE_PATH)
        self.cursor = self.connection.cursor()
        self._create_tables()
    
    def _create_tables(self):
        """Создание необходимых таблиц, если они не существуют"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            telegram_id INTEGER UNIQUE,
            link TEXT
        )
        ''')
        
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            channel_id TEXT NOT NULL
        )
        ''')
        self.connection.commit()
    
    def add_user(self, username, password):
        """Добавление нового пользователя"""
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            logger.error(f"Пользователь {username} уже существует")
            return False
    
    def authenticate_user(self, username, password):
        """Проверка учетных данных пользователя"""
        self.cursor.execute(
            "SELECT id FROM users WHERE username = ? AND password = ?",
            (username, password)
        )
        user = self.cursor.fetchone()
        return user[0] if user else None
    
    def update_telegram_id(self, user_id, telegram_id):
        """Обновление Telegram ID пользователя"""
        self.cursor.execute(
            "UPDATE users SET telegram_id = ? WHERE id = ?",
            (telegram_id, user_id)
        )
        self.connection.commit()
    
    def get_user_by_telegram_id(self, telegram_id):
        """Получение информации о пользователе по Telegram ID"""
        self.cursor.execute(
            "SELECT id, username, link FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        return self.cursor.fetchone()
    
    def get_user_by_username(self, username):
        """Получение информации о пользователе по имени пользователя"""
        self.cursor.execute(
            "SELECT id, password, telegram_id, link FROM users WHERE username = ?",
            (username,)
        )
        return self.cursor.fetchone()
    
    def update_link(self, user_id, link):
        """Обновление ссылки пользователя"""
        self.cursor.execute(
            "UPDATE users SET link = ? WHERE id = ?",
            (link, user_id)
        )
        self.connection.commit()
    
    def get_all_users(self):
        """Получение списка всех пользователей для админа"""
        self.cursor.execute("SELECT id, username, telegram_id, link FROM users")
        return self.cursor.fetchall()
    
    def delete_user(self, user_id):
        """Удаление пользователя"""
        try:
            self.cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при удалении пользователя: {e}")
            return False
    
    def update_username(self, user_id, new_username):
        """Изменение логина пользователя"""
        try:
            self.cursor.execute(
                "UPDATE users SET username = ? WHERE id = ?",
                (new_username, user_id)
            )
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            logger.error(f"Пользователь с логином {new_username} уже существует")
            return False
        except sqlite3.Error as e:
            logger.error(f"Ошибка при изменении логина: {e}")
            return False
    
    def update_password(self, user_id, new_password):
        """Изменение пароля пользователя"""
        try:
            self.cursor.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (new_password, user_id)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при изменении пароля: {e}")
            return False
    
    def get_user_by_id(self, user_id):
        """Получение информации о пользователе по ID"""
        self.cursor.execute(
            "SELECT username, telegram_id, link FROM users WHERE id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()
        
    def set_channel(self, channel_type, channel_id):
        """Установка или обновление канала определенного типа"""
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO channels (type, channel_id) VALUES (?, ?)",
                (channel_type, channel_id)
            )
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при установке канала: {e}")
            return False

    def get_channel(self, channel_type):
        """Получение ID канала по типу"""
        try:
            self.cursor.execute(
                "SELECT channel_id FROM channels WHERE type = ?",
                (channel_type,)
            )
            result = self.cursor.fetchone()
            return result[0] if result else None
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении канала: {e}")
            return None

    def close(self):
        """Закрытие соединения с базой данных"""
        self.connection.close()

# Создаем глобальный экземпляр базы данных для использования во всем приложении
db = Database()
