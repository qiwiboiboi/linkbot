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
        self.cursor.execute("SELECT username, telegram_id, link FROM users")
        return self.cursor.fetchall()
    
    def close(self):
        """Закрытие соединения с базой данных"""
        self.connection.close()

# Создаем глобальный экземпляр базы данных для использования во всем приложении
db = Database()