# bot.py
# Основной файл запуска TextEaseBot

import asyncio
import logging
import os
from getpass import getpass
from telegram.ext import Application
from dotenv import load_dotenv

# --- Загрузка переменных окружения ---
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
MODEL_PATH = os.getenv("MODEL_PATH")

if not TOKEN:
    print("🔐 Токен не найден в .env. Введите вручную:")
    TOKEN = getpass()
    with open(".env", "a") as f:
        f.write(f"BOT_TOKEN={TOKEN}\n")

if not MODEL_PATH:
    raise ValueError("❌ MODEL_PATH не найден в .env. Запустите download_model.py")

# --- Настройка логирования ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Загрузка моделей ---
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"✅ Используем устройство: {device}")

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

print("📥 Загружаем модель упрощения...")
simplify_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
simplify_model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_PATH).to(device)

print("📥 Загружаем модель перевода...")
translator_tokenizer = AutoTokenizer.from_pretrained("Helsinki-NLP/opus-mt-ru-en")
translator_model = AutoModelForSeq2SeqLM.from_pretrained("Helsinki-NLP/opus-mt-ru-en").to(device)

# --- Инициализация утилит ---
import utils
import handlers
import callbacks
from nltk.tokenize import sent_tokenize

# Передаём зависимости в модули
utils.simplify_tokenizer = simplify_tokenizer
utils.simplify_model = simplify_model
utils.translator_tokenizer = translator_tokenizer
utils.translator_model = translator_model
utils.device = device
utils.sent_tokenize = sent_tokenize

handlers.sent_tokenize = sent_tokenize

callbacks.simplify_long_text = utils.simplify_long_text
callbacks.translate_text = utils.translate_text
callbacks.evaluate_simplification = utils.evaluate_simplification
callbacks.split_text = utils.split_text
callbacks.sent_tokenize = sent_tokenize
callbacks.logger = logger

# --- Запуск бота ---
async def main():
    print("🚀 Создаём приложение...")
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики
    handlers.register_handlers(app)
    callbacks.register_callbacks(app)

    print("🤖 Бот запущен. Ожидаем сообщения...")
    while True:
        try:
            await app.run_polling(
                poll_interval=2,
                timeout=20,
                drop_pending_updates=True
            )
        except Exception as e:
            logger.warning(f"🔁 Ошибка: {e}. Перезапуск через 5 сек...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Бот остановлен вручную.")
        