# download_model.py
# Полная подготовка окружения: модель, NLTK, .env с токеном
# Использование: python download_model.py

import os
import sys
import requests
import zipfile
import argparse
from getpass import getpass

# --- Проверка и установка зависимостей ---
def install_dependencies():
    """Установка необходимых пакетов, если их нет"""
    required = ["requests", "nltk", "transformers", "torch", "python-dotenv"]
    for package in required:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            print(f"📦 Устанавливаем {package}...")
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# --- Настройка NLTK ---
def setup_nltk():
    """Загружает необходимые данные NLTK"""
    import nltk

    nltk_data_dir = os.path.join(os.getcwd(), "nltk_data")
    os.makedirs(nltk_data_dir, exist_ok=True)
    if nltk_data_dir not in nltk.data.path:
        nltk.data.path.insert(0, nltk_data_dir)

    print("🔍 Проверяем NLTK данные: punkt_tab для русского языка...")
    try:
        nltk.data.find('tokenizers/punkt_tab/russian/')
        print("✅ punkt_tab уже установлен")
    except LookupError:
        print("📥 Устанавливаем punkt_tab...")
        nltk.download('punkt_tab', download_dir=nltk_data_dir)
    print(f"💾 NLTK данные сохранены в: {nltk_data_dir}")

# --- Загрузка модели с Яндекс.Диска ---
def download_model():
    """Скачивает и распаковывает модель упрощения"""
    PUBLIC_LINK = "https://disk.yandex.ru/d/Ux1wDo_P1s0x6Q"
    MODEL_DIR = "model/rut5_simplifier_new"
    ZIP_PATH = "model/rut5_simplifier.zip"

    os.makedirs("model", exist_ok=True)

    if os.path.exists(MODEL_DIR):
        print(f"✅ Модель уже существует: {MODEL_DIR}")
        return MODEL_DIR

    print("🔗 Получаем прямую ссылку на скачивание...")
    try:
        api_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
        response = requests.get(api_url, params={"public_key": PUBLIC_LINK})
        response.raise_for_status()
        download_url = response.json()["href"]

        print("📥 Скачиваем модель...")
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(ZIP_PATH, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"✅ Архив сохранён: {ZIP_PATH}")

        print("📦 Распаковываем модель...")
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(MODEL_DIR)
        print(f"✅ Модель распакована в: {MODEL_DIR}")

        os.remove(ZIP_PATH)
        print("🗑️ Временный архив удалён")

        return MODEL_DIR

    except Exception as e:
        raise RuntimeError(f"❌ Ошибка при загрузке модели: {e}")

# --- Управление .env и токеном ---
def setup_env(model_path):
    """Создаёт .env файл с MODEL_PATH и запрашивает BOT_TOKEN, если его нет"""
    env_file = ".env"

    # Читаем существующие переменные
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    key, value = line.strip().split("=", 1)
                    env_vars[key] = value

    # Обновляем MODEL_PATH
    env_vars["MODEL_PATH"] = model_path

    # Запрашиваем BOT_TOKEN, если его нет
    if "BOT_TOKEN" not in env_vars:
        print("\n🔐 Введите токен Telegram-бота (не виден при вводе):")
        bot_token = getpass()
        if not bot_token or ":" not in bot_token:
            raise ValueError("❌ Некорректный токен. Должен быть в формате 123456789:ABCdefGhIJKlmnOPqrsTUVWXyz123456789")
        env_vars["BOT_TOKEN"] = bot_token

    # Сохраняем
    with open(env_file, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

    print(f"📄 Конфигурация сохранена в: {env_file}")

# --- Основная функция ---
def main():
    print("🚀 Начинаем подготовку окружения для TextEaseBot...")

    # 1. Установка зависимостей
    install_dependencies()

    # 2. Настройка NLTK
    setup_nltk()

    # 3. Загрузка модели
    model_path = download_model()

    # 4. Настройка .env (с токеном)
    setup_env(model_path)

    print("🎉 Готово! Теперь можно запускать бота: python bot.py")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Подготовка окружения для TextEaseBot")
    parser.add_argument('--force', action='store_true', help='Перезагрузить модель, даже если она есть')
    args = parser.parse_args()

    if args.force:
        model_dir = "model/rut5_simplifier_new"
        if os.path.exists(model_dir):
            import shutil
            print("🔁 Принудительная перезагрузка: удаляем старую модель...")
            shutil.rmtree(model_dir)

    main()