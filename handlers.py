import os
import re
import tempfile
import logging
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from utils import (
    MAX_TEXT_LENGTH, MAX_FILE_SIZE, MAX_PARTS_FOR_WARNING,
    send_typing_action, safe_delete_file, read_txt_file, read_docx_file,
    split_text, simplify_long_text, translate_text, evaluate_simplification,
    get_main_keyboard, get_simplify_keyboard
)

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    await update.message.reply_text(
        "👋 Привет! Я — *TextEaseBot*.\n\n"
        "📌 Я помогаю:\n"
        "• Упрощать сложные тексты\n"
        "• Переводить на английский\n"
        "💡 *Как использовать:*\n"
        "1. Отправь текст напрямую\n"
        "2. Или загрузи файл (.txt, .docx)\n"
        "3. Выбери нужную функцию\n\n"
        "⚠️ *Важно:*\n"
        "• Я — ИИ, а не эксперт\n"
        "• Могу ошибаться в сложных темах\n"
        "• Не заменяю профессиональную экспертизу\n\n"
        "🔍 Для чувствительных тем используй режим *Фактчекинг*.\n\n"
        "Готов к работе? Присылай текст!",
        parse_mode='Markdown',
        disable_web_page_preview=True
    )
    await show_buttons(update, context)

async def show_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню"""
    keyboard = get_main_keyboard()
    await update.message.reply_text(
        "Выбери действие:",
        reply_markup=keyboard
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    text = update.message.text.strip()
    
    if not text:
        await update.message.reply_text("❌ Пустое сообщение. Отправь текст или файл.")
        return
    
    # Проверка длины текста
    if len(text) > MAX_TEXT_LENGTH:
        await update.message.reply_text(
            f"❌ Текст слишком длинный ({len(text)} символов).\n"
            f"Максимальная длина: {MAX_TEXT_LENGTH} символов.\n\n"
            "💡 Пожалуйста, сократите текст или разделите на части."
        )
        return
    
    # Предупреждение о длительной обработке
    estimated_parts = len(text) // 1500 + 1
    if estimated_parts > MAX_PARTS_FOR_WARNING:
        await update.message.reply_text(
            f"⚠️ Текст довольно длинный ({len(text)} символов).\n"
            f"Обработка может занять {estimated_parts * 5} секунд.\n"
            f"Продолжить?"
        )
    
    context.user_data['pending_text'] = text
    context.user_data['source_type'] = 'text'
    
    await update.message.reply_text(
        f"📝 Получен текст ({len(text)} символов).\n"
        "Выбери действие:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚖️ Средний", callback_data="simplify_medium")],
            [InlineKeyboardButton("🔥 Сильный", callback_data="simplify_strong")],
            [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
        ])
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    doc = update.message.document
    file_name = doc.file_name.lower()
    user_id = update.effective_user.id
    
    # Проверка формата файла
    if not any(file_name.endswith(ext) for ext in {".txt", ".docx"}):
        await update.message.reply_text(
            "❌ Неподдерживаемый формат.\n"
            "Поддерживаются: .txt, .docx"
        )
        return
    
    # Проверка размера файла
    if doc.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ Слишком большой файл.\n"
            f"Максимальный размер: {MAX_FILE_SIZE // (1024*1024)} МБ"
        )
        return
    
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=f"_{user_id}{os.path.splitext(file_name)[1]}"
    ) as temp_file:
        temp_path = temp_file.name
    
    try:
        file = await doc.get_file()
        await file.download_to_drive(temp_path)
        
        # Чтение файла
        if file_name.endswith(".txt"):
            text = await read_txt_file(temp_path)
        elif file_name.endswith(".docx"):
            text = await read_docx_file(temp_path)
        else:
            text = None
        
        if text is None:
            await update.message.reply_text(
                "❌ Ошибка чтения файла.\n"
                "Проверьте целостность файла и попробуйте снова."
            )
            return
        
        if not text.strip():
            await update.message.reply_text("❌ Файл пустой.")
            return
        
        # Проверка длины текста
        if len(text) > MAX_TEXT_LENGTH:
            await update.message.reply_text(
                f"❌ Текст слишком длинный ({len(text)} символов).\n"
                f"Максимальная длина: {MAX_TEXT_LENGTH} символов.\n\n"
                "💡 Пожалуйста, сократите текст или разделите на части."
            )
            return
        
        # Предупреждение о длительной обработке
        estimated_parts = len(text) // 1500 + 1
        if estimated_parts > MAX_PARTS_FOR_WARNING:
            await update.message.reply_text(
                f"⚠️ Текст довольно длинный ({len(text)} символов).\n"
                f"Обработка может занять {estimated_parts * 5} секунд.\n"
                f"Продолжить?"
            )
        
        context.user_data['pending_text'] = text
        context.user_data['source_type'] = 'document'
        
        await update.message.reply_text(
            f"📄 Файл успешно загружен:\n"
            f"• Имя: {doc.file_name}\n"
            f"• Размер: {doc.file_size // 1024} КБ\n"
            f"• Текст: {len(text)} символов\n\n"
            "Выбери действие:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚖️ Средний", callback_data="simplify_medium")],
                [InlineKeyboardButton("🔥 Сильный", callback_data="simplify_strong")],
                [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
            ])
        )
    except Exception as e:
        print(f"Ошибка обработки документа: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке файла.\n"
            "Попробуйте отправить его снова или обратитесь в поддержку."
        )
    finally:
        await safe_delete_file(temp_path)

async def fact_checking_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    text = context.user_data.get('pending_text', '').strip()
    if not text:
        await safe_edit_message(query, "❌ Нет текста для анализа. Отправьте текст или файл сначала.")
        return
    
    # Предупреждение для длинных текстов
    if len(text) > 8000:
        await safe_edit_message(query, 
            f"⚠️ Текст довольно длинный ({len(text)} символов).\n"
            f"Выделение утверждений может занять время...\n\n"
            f"Продолжить?"
        )
    
    try:
        sentences = sent_tokenize(text, language='russian')
    except (LookupError, AttributeError) as e:
        logger.warning(f"Tokenizer error: {e}")
        sentences = re.split(r'(?<=[.!?])\s+', text)
    
    claims = [s.strip() for s in sentences if s.strip() and len(s) > 10]
    
    if not claims:
        await safe_edit_message(query, "❌ Не удалось выделить утверждения для проверки.")
        return
    
    # Сохраняем утверждения в контекст
    context.user_data['fact_check_claims'] = claims
    
    # Ограничиваем количество отображаемых утверждений
    MAX_CLAIMS_DISPLAY = 15
    display_claims = claims[:MAX_CLAIMS_DISPLAY]
    remaining = len(claims) - MAX_CLAIMS_DISPLAY
    
    header = "🔍 *Режим фактчекинга:*\n\n"
    if remaining > 0:
        header += f"Выделено утверждений: {len(claims)} (показаны первые {MAX_CLAIMS_DISPLAY}):\n\n"
    else:
        header += f"Выделено утверждений: {len(claims)}:\n\n"
    
    await query.edit_message_text(header, parse_mode='Markdown')
    
    # Отправляем утверждения порциями
    batch_size = 5
    for i in range(0, len(display_claims), batch_size):
        batch = display_claims[i:i+batch_size]
        
        for j, claim in enumerate(batch, i+1):
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            formatted_claim = f"_{j}._ {claim}"
            
            # Только кнопка "Упростить" без кнопки "Проверить"
            keyboard = [
                [InlineKeyboardButton("📝 Упростить", callback_data=f"simplify_claim_{j-1}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.message.reply_text(
                    formatted_claim,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            except Exception as e:
                logger.error(f"Ошибка отправки утверждения: {e}")
                await query.message.reply_text(formatted_claim, parse_mode='Markdown')
        
        if i + batch_size < len(display_claims):
            await asyncio.sleep(1)
    
    if remaining > 0:
        await query.message.reply_text(
            f"ℹ️ Показаны первые {MAX_CLAIMS_DISPLAY} утверждений. "
            f"Остальные {remaining} можно проверить позже."
        )
    
    # Упрощенная клавиатура с кнопкой "Назад к тексту"
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Назад к тексту", callback_data="back_to_uploaded_text")
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="fact_check_help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_typing_action(update, context)
    help_text = (
        "❓ *Помощь по TextEaseBot*\n\n"
        "🤖 *Что я умею:*\n"
        "• 📝 Упрощать сложные тексты на 2 уровнях\n"
        "• 🌍 Переводить тексты на английский язык\n"
        "• 📄 Работать с файлами .txt и .docx\n\n"
        "📋 *Как начать:*\n"
        "1. Отправьте мне текст напрямую\n"
        "2. Или загрузите файл с текстом\n"
        "3. Выберите нужную функцию из меню\n\n"
        "🔧 *Уровни упрощения:*\n"
        "• ⚖️ *Средний* - оптимальное упрощение\n"
        "• 🔥 *Сильный* - максимальное упрощение\n\n"
        "⚠️ *Ограничения:*\n"
        "• Максимальный размер файла: 20 МБ\n"
        "• Максимальная длина текста: 10 000 символов\n"
        "• Я - ИИ, могу ошибаться в сложных темах\n\n"
        "💡 *Совет:* Для длинных текстов используйте файлы."
    )
    keyboard = [
        [
            InlineKeyboardButton("🔄 Начать заново", callback_data="restart")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

def setup_handlers(application, models):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))