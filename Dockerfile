FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

RUN mkdir -p /app/nltk_data
RUN python -c "import nltk; \
    nltk.download('punkt', download_dir='/app/nltk_data'); \
    nltk.download('punkt_tab', download_dir='/app/nltk_data')"

CMD ["python", "bot.py"]