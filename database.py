# Обновление database.py - добавляем поле full_name

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
        self._migrate_tables()  # Добавляем миграцию
    
    def _create_tables(self):
        """Создание необходимых таблиц, если они не существуют"""
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            telegram_id INTEGER UNIQUE,
            link TEXT,
            full_name TEXT  -- Добавляем поле для полного имени
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
    
    def _migrate_tables(self):
        """Миграция существующих таблиц"""
        try:
            # Проверяем, есть ли колонка full_name
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            if 'full_name' not in columns:
                # Добавляем колонку full_name, если её нет
                self.cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
                self.connection.commit()
                logger.info("Added full_name column to users table")
        except Exception as e:
            logger.error(f"Migration error: {e}")
    
    def add_user(self, username, password, full_name=None):
        """Добавление нового пользователя"""
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password, full_name) VALUES (?, ?, ?)",
                (username, password, full_name)
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
    
    def update_telegram_id(self, user_id, telegram_id, full_name=None):
        """Обновление Telegram ID и полного имени пользователя"""
        if full_name:
            self.cursor.execute(
                "UPDATE users SET telegram_id = ?, full_name = ? WHERE id = ?",
                (telegram_id, full_name, user_id)
            )
        else:
            self.cursor.execute(
                "UPDATE users SET telegram_id = ? WHERE id = ?",
                (telegram_id, user_id)
            )
        self.connection.commit()
    
    def get_user_by_telegram_id(self, telegram_id):
        """Получение информации о пользователе по Telegram ID"""
        self.cursor.execute(
            "SELECT id, username, link, full_name FROM users WHERE telegram_id = ?",
            (telegram_id,)
        )
        result = self.cursor.fetchone()
        # Обеспечиваем обратную совместимость: если full_name NULL, возвращаем только первые 3 поля
        if result and result[3] is None:
            return result[:3]  # (id, username, link)
        return result  # (id, username, link, full_name) или None
    
    def get_user_by_username(self, username):
        """Получение информации о пользователе по имени пользователя"""
        self.cursor.execute(
            "SELECT id, password, telegram_id, link, full_name FROM users WHERE username = ?",
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
        try:
            # Проверяем, есть ли колонка full_name
            self.cursor.execute("PRAGMA table_info(users)")
            columns = [column[1] for column in self.cursor.fetchall()]
            
            if 'full_name' in columns:
                # Если колонка есть, выбираем все поля включая full_name
                self.cursor.execute("SELECT id, username, telegram_id, link, full_name FROM users")
            else:
                # Если колонки нет, выбираем только старые поля
                self.cursor.execute("SELECT id, username, telegram_id, link FROM users")
            
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            # Fallback to old query format
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
            "SELECT username, telegram_id, link, full_name FROM users WHERE id = ?",
            (user_id,)
        )
        result = self.cursor.fetchone()
        # Обеспечиваем обратную совместимость: если full_name NULL, возвращаем только первые 3 поля
        if result and result[3] is None:
            return result[:3]  # (username, telegram_id, link)
        return result  # (username, telegram_id, link, full_name) или None
        
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