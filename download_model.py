import os
import torch
import requests
from shutil import rmtree
from zipfile import ZipFile
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, BertTokenizer, BertModel
from dotenv import load_dotenv

load_dotenv()

# Настройка устройства
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"✅ Используем устройство: {device}")

# Настройка путей
MODEL_DIR = os.getenv("MODEL_PATH", "/content/rut5_simplifier_new")
ZIP_PATH = "/content/rut5_simplifier.zip"
PUBLIC_LINK = "https://disk.yandex.ru/d/GcR3ougL6bY6kw"

# Функция загрузки с Яндекс.Диска
def download_from_yandex_disk(public_url, output_path):
    base_url = "https://cloud-api.yandex.net/v1/disk/public/resources/download"
    params = {"public_key": public_url}
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    download_url = response.json()["href"]
    print("📥 Скачиваем модель с Яндекс.Диска...")
    session = requests.Session()
    session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=10))
    with session.get(download_url, stream=True) as r:
        r.raise_for_status()
        with open(output_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print(f"✅ Файл сохранён: {output_path}")

# Распаковка модели
def extract_model(zip_path, extract_to):
    print("📦 Распаковываем архив...")
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print(f"✅ Модель распакована в: {extract_to}")

# Функция загрузки моделей
def load_model(model_path, model_type):
    try:
        print(f"📥 Загружаем {model_type} модель из: {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_path).to(device)
        
        # Оптимизация для GPU
        if device == "cuda":
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            if gpu_memory < 8:
                model.half()
                print("🔧 Модель переведена в float16 для экономии памяти")
        print(f"✅ {model_type} модель загружена")
        return tokenizer, model
    except Exception as e:
        error_msg = f"❌ Ошибка загрузки {model_type} модели: {e}"
        print(error_msg)
        raise RuntimeError(error_msg)

async def download_and_setup_models():
    print("🔄 Загрузка моделей...")
    
    # Загрузка основной модели
    if not os.path.exists(MODEL_DIR):
        print("🔍 Модель не найдена локально. Загружаем...")
        try:
            download_from_yandex_disk(PUBLIC_LINK, ZIP_PATH)
            extract_model(ZIP_PATH, MODEL_DIR)
            os.remove(ZIP_PATH)
        except Exception as e:
            if os.path.exists(ZIP_PATH):
                os.remove(ZIP_PATH)
            if os.path.exists(MODEL_DIR):
                rmtree(MODEL_DIR)
            raise RuntimeError(f"❌ Ошибка загрузки модели: {e}")
    else:
        print(f"✅ Модель уже существует: {MODEL_DIR}")
    
    # Явное указание пути к модели
    MODEL_SUBDIR = "rut5_simplifier"
    MODEL_PATH = os.path.join(MODEL_DIR, MODEL_SUBDIR)
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(f"❌ Папка модели не найдена: {MODEL_PATH}")
    print(f"✅ Используем путь к модели: {MODEL_PATH}")
    
    # Проверка файлов модели
    required_files = ['config.json']
    model_files = ['pytorch_model.bin', 'model.safetensors']
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(os.path.join(MODEL_PATH, file)):
            missing_files.append(file)
    
    # Проверяем наличие хотя бы одного файла модели
    model_found = False
    for model_file in model_files:
        file_path = os.path.join(MODEL_PATH, model_file)
        if os.path.exists(file_path):
            print(f"✅ Найден файл модели: {model_file}")
            model_found = True
            break
    
    if not model_found:
        missing_files.extend(model_files)
    
    if missing_files:
        raise RuntimeError(f"❌ В папке модели отсутствуют файлы: {missing_files}")
    print("✅ Все необходимые файлы модели присутствуют")
    
    # Загрузка моделей
    try:
        simplify_tokenizer, simplify_model = load_model(MODEL_PATH, "упрощения")
    except Exception as e:
        raise RuntimeError(f"❌ Критическая ошибка при загрузке модели упрощения: {e}")
    
    TRANSLATE_MODEL_NAME = "Helsinki-NLP/opus-mt-ru-en"
    try:
        translator_tokenizer, translator_model = load_model(TRANSLATE_MODEL_NAME, "перевода")
    except Exception as e:
        raise RuntimeError(f"❌ Критическая ошибка при загрузке модели перевода: {e}")
    
    # Инициализация BERT
    bert_model_name = "bert-base-multilingual-cased"
    bert_tokenizer = BertTokenizer.from_pretrained(bert_model_name)
    bert_model = BertModel.from_pretrained(bert_model_name)
    bert_model.to(device)
    
    # Оптимизация для Colab
    torch.backends.cuda.max_split_size_mb = 512
    if device == "cuda":
        torch.cuda.empty_cache()
        print(f"🧹 Очищен кэш CUDA. Свободно памяти: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
    
    print("✅ Все модели успешно загружены")
    
    return {
        'simplify_tokenizer': simplify_tokenizer,
        'simplify_model': simplify_model,
        'translator_tokenizer': translator_tokenizer,
        'translator_model': translator_model,
        'bert_tokenizer': bert_tokenizer,
        'bert_model': bert_model,
        'device': device
    }