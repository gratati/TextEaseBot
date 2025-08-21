# Используем официальный образ Python 3.9
FROM python:3.9-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скачиваем модель spacy для русского языка
RUN python -m spacy download ru_core_news_sm

# Копируем исходный код
COPY . .

# Создаем директорию для моделей
RUN mkdir -p /app/models

# Устанавливаем переменные окружения
ENV MODEL_PATH=/app/models
ENV NLTK_DATA=/app/nltk_data

# Создаем директорию для NLTK данных
RUN mkdir -p /app/nltk_data

# Скачиваем необходимые NLTK пакеты
RUN python -c "import nltk; nltk.download('punkt', download_dir='/app/nltk_data'); nltk.download('punkt_tab', download_dir='/app/nltk_data'); nltk.download('stopwords', download_dir='/app/nltk_data')"

# Устанавливаем точку входа
ENTRYPOINT ["python", "bot.py"]

# Указываем порт (если понадобится веб-интерфейс в будущем)
EXPOSE 8080