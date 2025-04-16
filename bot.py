# bot.py
import logging
from aiogram import Bot, Dispatcher, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from config import BOT_TOKEN, CHANNEL_ID
from handlers import register_all_handlers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

async def send_channel_notification(username, link):
    """Отправка уведомления в канал о новой ссылке"""
    try:
        await bot.send_message(
            CHANNEL_ID,
            f"📢 Пользователь обновил ссылку!\n"
            f"👤 Пользователь: {username}\n"
            f"🔗 Ссылка: {link}"
        )
        logger.info(f"Notification sent to channel about user {username}")
    except Exception as e:
        logger.error(f"Failed to send channel notification: {e}")

# Добавьте middleware для обработки результатов от process_link
from aiogram.dispatcher.middlewares import BaseMiddleware

class NotificationMiddleware(BaseMiddleware):
    async def on_post_process_message(self, message, results, data):
        for result in results:
            if isinstance(result, dict) and 'username' in result and 'link' in result:
                await send_channel_notification(result['username'], result['link'])

async def on_startup(dispatcher):
    """Действия при запуске бота"""
    logger.info("Бот запущен")
    # Регистрация всех обработчиков
    register_all_handlers(dispatcher)
    # Добавление middleware
    dispatcher.middleware.setup(NotificationMiddleware())

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)