# handlers.py
# Обработчики команд и сообщений для TextEaseBot

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from docx import Document
import os

# Глобальные переменные (инициализируются в bot.py)
sent_tokenize = None


# --- Обработчики ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Приветственное сообщение и инструкция.
    """
    await update.message.reply_text(
        "👋 Привет! Я — *TextEaseBot*.\n"
        "Я помогаю упрощать и переводить тексты.\n\n"

        "📌 Отправь:\n"
        "• Текст напрямую\n"
        "• Или файл (.txt, .docx)\n\n"

        "💡 *Важно:* Я — ИИ, а не эксперт.\n"
        "⚠️ Я могу *упрощать* и *переводить*, но:\n"
        "• Не гарантирую 100% точность\n"
        "• Могу искажать смысл в спорных или политических темах\n"
        "• Не заменяю фактчекинг и юридическую экспертизу\n\n"

        "🔍 Для чувствительных текстов используй режим *Фактчекинг*.\n\n"

        "Готов? Пришли текст!",
        parse_mode='Markdown'
    )
    await show_buttons(update, context)


async def show_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляет кнопки выбора действия.
    """
    keyboard = [
        [InlineKeyboardButton("🙂 Лёгкий", callback_data="simplify_light")],
        [InlineKeyboardButton("⚖️ Средний", callback_data="simplify_medium")],
        [InlineKeyboardButton("🔥 Сильный", callback_data="simplify_strong")],
        [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выбери уровень упрощения:", reply_markup=reply_markup)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка текстового сообщения.
    """
    context.user_data['pending_text'] = update.message.text
    await show_buttons(update, context)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка загруженного файла (.txt, .docx).
    """
    doc = update.message.document
    file_name = doc.file_name.lower()
    user_id = update.effective_user.id
    file_path = f"/tmp/temp_{user_id}"

    file = await doc.get_file()
    await file.download_to_drive(file_path)

    text = ""
    try:
        if file_name.endswith(".txt"):
            for enc in ["utf-8", "cp1251", "latin1"]:
                try:
                    with open(file_path, "r", encoding=enc) as f:
                        text = f.read()
                    break
                except Exception:
                    continue
            if not text:
                text = "❌ Ошибка: не удалось прочитать файл (кодировка)."
        elif file_name.endswith(".docx"):
            docx = Document(file_path)
            text = "\n".join([p.text for p in docx.paragraphs if p.text.strip()])
        else:
            await update.message.reply_text("❌ Поддерживаются только .txt и .docx")
            return

        if not text.strip():
            await update.message.reply_text("❌ Файл пустой.")
            return

        context.user_data['pending_text'] = text
        await update.message.reply_text(f"📄 Файл загружен ({len(text)} символов).")
        await show_buttons(update, context)

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при обработке файла: {e}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


async def fact_checking_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Режим фактчекинга: разбивка текста на отдельные утверждения.
    """
    query = update.callback_query
    await query.answer()

    text = context.user_data.get('pending_text', '')
    if not text:
        await query.edit_message_text("❌ Нет текста для анализа.")
        return

    try:
        sentences = sent_tokenize(text, language='russian')
    except:
        sentences = sent_tokenize(text)

    claims = [s.strip() for s in sentences if s.strip() and len(s) > 10]
    if not claims:
        await query.edit_message_text("❌ Не удалось выделить утверждения.")
        return

    await query.edit_message_text("🔍 *Режим фактчекинга:*\n\nВыделенные утверждения:\n")

    for i, claim in enumerate(claims, 1):
        await query.message.reply_text(f"{i}. {claim}")

    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main")]]
    await query.message.reply_text(
        "После анализа каждого утверждения можно упростить или перевести.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# --- Регистрация обработчиков ---
def register_handlers(app):
    """
    Регистрирует все обработчики в приложении.
    """
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(
        filters.Document.FileExtension("txt") |
        filters.Document.FileExtension("docx"),
        handle_document
    ))
    app.add_handler(CallbackQueryHandler(fact_checking_mode, pattern="^fact_checking$"))