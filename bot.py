# bot.py
import logging
import asyncio
import signal
import sys
import traceback
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, CHANNEL_ID
from handlers import register_all_handlers
from database import db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

async def send_channel_notification(username, link):
    """Отправка уведомления в канал о новой ссылке"""
    try:
        await bot.send_message(
            CHANNEL_ID,
            f"📢 Пользователь обновил ссылки!\n"
            f"👤 Пользователь: {username}\n"
            f"🔗 Ссылки: {link}"
        )
        logger.info(f"Notification sent to channel about user {username}")
    except Exception as e:
        logger.error(f"Failed to send channel notification: {e}")

# Middleware для обработки результатов от process_link
class NotificationMiddleware:
    async def __call__(self, handler, event, data):
        result = await handler(event, data)
        if isinstance(result, dict) and 'username' in result and 'link' in result:
            await send_channel_notification(result['username'], result['link'])
        return result

async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запущен")

async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Завершение работы бота...")
    
    # Закрываем подключение к базе данных
    try:
        db.close()
        logger.info("Соединение с базой данных закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с базой данных: {e}")
    
    # Закрываем сессию бота
    try:
        await bot.session.close()
        logger.info("Сессия бота закрыта")
    except Exception as e:
        logger.error(f"Ошибка при закрытии сессии бота: {e}")

async def main():
    try:
        # Регистрация всех обработчиков
        register_all_handlers(dp)
        
        # Добавление middleware
        dp.message.middleware.register(NotificationMiddleware())
        
        # Запуск бота
        await on_startup()
        logger.info("Бот готов к работе!")
        
        # Настройка обработки сигналов для корректного завершения
        def signal_handler(signum, frame):
            logger.info(f"Получен сигнал завершения, останавливаю бота...")
            raise KeyboardInterrupt
        
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Запускаем поллинг
        await dp.start_polling(bot, skip_updates=True)
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен по запросу пользователя")
    except Exception as e:
        error_message = f"Критическая ошибка: {e}\n\n{traceback.format_exc()}"
        logger.error(error_message)
    finally:
        # Выполняем действия при завершении в любом случае
        await on_shutdown()
        logger.info("Бот остановлен")

if __name__ == '__main__':
    # Простая обработка ошибок на верхнем уровне
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        traceback.print_exc()