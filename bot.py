import asyncio
import logging
import os
import signal
import sys
from dotenv import load_dotenv

from telegram.ext import Application
from download_model import download_and_setup_models
from handlers import setup_handlers
from callbacks import setup_callbacks

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверка токена
if not BOT_TOKEN or BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise RuntimeError("❌ Токен бота не предоставлен. Бот не может быть запущен.")

print(f"✅ Токен бота загружен: {BOT_TOKEN[:10]}...")

# Обработчик сигналов для корректного завершения работы
def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения работы"""
    print("\n🛑 Получен сигнал завершения. Останавливаем бота...")
    sys.exit(0)

async def shutdown(application):
    """Корректное завершение работы приложения"""
    print("🔄 Завершаем работу бота...")
    try:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
    except Exception as e:
        print(f"❌ Ошибка при завершении работы: {e}")

async def main():
    try:
        # Загрузка моделей
        models = await download_and_setup_models()
        
        # Создание приложения
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Настройка обработчиков
        setup_handlers(application, models)
        setup_callbacks(application, models)
        
        print("🤖 Бот запущен...")
        print("💡 Для остановки бота нажмите Ctrl+C")
        
        # Инициализация и запуск
        await application.initialize()
        await application.start()
        await application.updater.start_polling(drop_pending_updates=True)
        
        # Ожидаем сигнала завершения
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'application' in locals():
            await shutdown(application)
        print("🛑 Бот остановлен")

if __name__ == "__main__":
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал завершения. Останавливаем бота...")
    except Exception as e:
        print(f"❌ Необработанное исключение: {e}")
        import traceback
        traceback.print_exc()