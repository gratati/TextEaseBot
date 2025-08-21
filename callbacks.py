import os
import re
import asyncio
import random
import logging
from typing import Optional, List, Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils import (
    send_typing_action, safe_edit_message, send_thinking_messages,
    split_text, simplify_text, translate_text, evaluate_simplification,
    get_main_keyboard, get_simplify_keyboard
)

logger = logging.getLogger(__name__)

async def simplify_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    claim_index = int(query.data.split('_')[-1])
    claims = context.user_data.get('fact_check_claims', [])
    
    if not claims or claim_index >= len(claims):
        await query.edit_message_text("❌ Утверждение не найдено.")
        return
    
    claim = claims[claim_index]
    
    await query.edit_message_text(
        f"📝 *Упрощение утверждения:*\n\n_{claim}_\n\n"
        "⏳ Выполняется упрощение...",
        parse_mode='Markdown'
    )
    
    try:
        # Используем модель упрощения с уровнем medium по умолчанию
        simplified = simplify_text(
            claim,
            strength="medium",
            simplify_tokenizer=context.bot_data['simplify_tokenizer'],
            simplify_model=context.bot_data['simplify_model'],
            device=context.bot_data['device']
        )
        
        result_text = (
            f"📝 *Упрощенное утверждение:*\n\n"
            f"{simplified}\n\n"
            f"📌 *Оригинал:*\n_{claim}_"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Другой уровень", callback_data=f"change_claim_level_{claim_index}"),
                InlineKeyboardButton("⬅️ Назад", callback_data="back_to_uploaded_text")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка упрощения утверждения: {e}")
        await query.edit_message_text(f"❌ Ошибка при упрощении утверждения: {e}")

async def change_claim_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    claim_index = int(query.data.split('_')[-1])
    claims = context.user_data.get('fact_check_claims', [])
    
    if not claims or claim_index >= len(claims):
        await query.edit_message_text("❌ Утверждение не найдено.")
        return
    
    # Сохраняем индекс утверждения для последующего использования
    context.user_data['current_claim_index'] = claim_index
    
    keyboard = [
        [
            InlineKeyboardButton("⚖️ Средний", callback_data=f"simplify_claim_medium_{claim_index}"),
            InlineKeyboardButton("🔥 Сильный", callback_data=f"simplify_claim_strong_{claim_index}")
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data="back_to_uploaded_text")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Выбери уровень упрощения:",
        reply_markup=reply_markup
    )

async def simplify_claim_with_strength(update: Update, context: ContextTypes.DEFAULT_TYPE, claim_index: int, strength: str):
    query = update.callback_query
    await query.answer()
    
    claims = context.user_data.get('fact_check_claims', [])
    
    if not claims or claim_index >= len(claims):
        await query.edit_message_text("❌ Утверждение не найдено.")
        return
    
    claim = claims[claim_index]
    
    await query.edit_message_text(
        f"📝 *Упрощение утверждения ({strength}):*\n\n_{claim}_\n\n"
        "⏳ Выполняется упрощение...",
        parse_mode='Markdown'
    )
    
    try:
        simplified = simplify_text(
            claim,
            strength=strength,
            simplify_tokenizer=context.bot_data['simplify_tokenizer'],
            simplify_model=context.bot_data['simplify_model'],
            device=context.bot_data['device']
        )
        
        result_text = (
            f"📝 *Упрощенное утверждение ({strength}):*\n\n"
            f"{simplified}\n\n"
            f"📌 *Оригинал:*\n_{claim}_"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Другой уровень", callback_data=f"change_claim_level_{claim_index}"),
                InlineKeyboardButton("⬅️ Назад", callback_data="back_to_uploaded_text")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            result_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка упрощения утверждения: {e}")
        await query.edit_message_text(f"❌ Ошибка при упрощении утверждения: {e}")

async def show_last_uploaded_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = context.user_data.get('pending_text', '').strip()
    
    if not text:
        await safe_edit_message(query, "❌ Нет загруженного текста.")
        return
    
    # Показываем оригинальный текст
    try:
        await query.delete_message()
    except Exception as e:
        logger.warning(f"Error deleting message: {e}")
    
    max_length = 4096 - 100
    if len(text) <= max_length:
        await query.message.reply_text(
            f"📜 *Последний загруженный текст:*\n\n{text}",
            parse_mode='Markdown'
        )
    else:
        parts = split_text(text, max_chars=3500)
        for i, part in enumerate(parts):
            if part.strip():
                text_part = f"📜 *Последний загруженный текст (часть {i+1}):*\n\n{part}"
                await query.message.reply_text(text_part, parse_mode='Markdown')
                await asyncio.sleep(0.5)
    
    # Добавляем кнопки для действий с текстом
    keyboard = [
        [InlineKeyboardButton("⚖️ Средний", callback_data="simplify_medium")],
        [InlineKeyboardButton("🔥 Сильный", callback_data="simplify_strong")],
        [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        "Выбери действие:",
        reply_markup=reply_markup
    )

async def fact_check_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    help_text = (
        "❓ *Помощь по режиму фактчекинга*\n\n"
        "🔍 *Что это такое?*\n"
        "Режим фактчекинга анализирует текст и выделяет отдельные утверждения, которые можно проверить на достоверность.\n\n"
        "📋 *Как использовать:*\n"
        "1. Отправьте текст или загрузите файл\n"
        "2. Выберите режим 'Фактчекинг'\n"
        "3. Бот разобьет текст на утверждения\n"
        "4. Для каждого утверждения доступны действия:\n"
        "   • 📝 *Упростить* - упростить утверждение\n\n"
        "⚠️ *Важно:*\n"
        "• Бот не заменяет профессиональную экспертизу\n"
        "• Результаты носят рекомендательный характер\n"
        "• Для важных решений всегда проверяйте несколько источников\n\n"
        "💡 *Совет:* Начните с проверки наиболее важных или спорных утверждений."
    )
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Назад к утверждениям", callback_data="back_to_fact_check")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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
            InlineKeyboardButton("⬅️ Назад", callback_data="back_to_main"),
            InlineKeyboardButton("🔄 Начать заново", callback_data="restart")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        help_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def handle_back_to_simplified(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    simplified = context.user_data.get('simplified_text', '').strip()
    strength = context.user_data.get('last_strength', 'medium')
    
    if not simplified:
        await safe_edit_message(query, "❌ Нет упрощённого текста.")
        return
    
    strength_names = {
        'light': 'лёгкий',
        'medium': 'средний',
        'strong': 'сильный'
    }
    strength_name = strength_names.get(strength, 'средний')
    
    await safe_edit_message(
        query,
        f"✅ *Упрощённый текст ({strength_name}):*\n\n{simplified}",
        reply_markup=get_simplify_keyboard(),
        parse_mode='Markdown'
    )

async def handle_simplify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    strength = data.split("_")[1]
    text = context.user_data.get('pending_text', '').strip()
    
    if not text:
        await safe_edit_message(query, "❌ Не найден текст для упрощения.")
        return
    
    await safe_edit_message(query, f"🔄 Упрощаю текст ({strength} уровень)...")
    
    if len(text) > 2000:
        parts = split_text(text, 1500)
        total_parts = len(parts)
        for i, part in enumerate(parts):
            if part.strip():
                progress = (i + 1) / total_parts * 100
                await safe_edit_message(
                    query,
                    f"🔄 Упрощаю текст ({strength} уровень)...\n\n"
                    f"Прогресс: {i+1}/{total_parts} частей ({progress:.0f}%)"
                )
                await asyncio.sleep(0.5)
    
    thinking_messages = [
        "🧠 Анализирую структуру текста...",
        "✍️ Упрощаю с сохранением смысла...",
        "🔍 Переписываю — чтобы было ясно...",
        "🧩 Готовлю результат...",
        "✅ Почти готово!"
    ]
    random.shuffle(thinking_messages)
    await send_thinking_messages(query, thinking_messages)
    
    try:
        simplified = simplify_long_text(
            text,
            strength=strength,
            simplify_tokenizer=context.bot_data['simplify_tokenizer'],
            simplify_model=context.bot_data['simplify_model'],
            device=context.bot_data['device']
        )
        
        context.user_data['simplified_text'] = simplified
        context.user_data['last_strength'] = strength
        
        metrics = evaluate_simplification(text, simplified)
        quality_info = (
            f"\n\n📊 *Оценка упрощения:*\n"
            f"🔤 Длина: {metrics['original_length']} → {metrics['simplified_length']} слов\n"
            f"⚖️ Сохранение смысла: {metrics['keyword_overlap_%']}%\n"
            f"💡 {metrics['quality_hint']}"
        )
        
        warning = ""
        if len(simplified.split()) > 300:
            warning = "\n\n⚠️ *Внимание:* текст длинный — мог быть частично обрезан."
        
        # Обновленная клавиатура без кнопки "Фактчекинг"
        keyboard = [
            [InlineKeyboardButton("🔤 Перевести на английский", callback_data="translate")],
            [InlineKeyboardButton("🔄 Попробовать другой уровень", callback_data="change_level")],
            [InlineKeyboardButton("📄 Показать оригинал", callback_data="show_original")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(
            query,
            f"✅ *Упрощённый текст ({strength}):*\n\n{simplified}{quality_info}{warning}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Simplification error: {e}")
        await safe_edit_message(query, f"❌ Ошибка при упрощении текста: {e}")

async def handle_translate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    simplified = context.user_data.get('simplified_text', '').strip()
    
    if not simplified:
        await safe_edit_message(query, "❌ Нет текста для перевода.")
        return
    
    await safe_edit_message(query, "🔤 Перевожу на английский...")
    
    try:
        translated = translate_text(
            simplified,
            translator_tokenizer=context.bot_data['translator_tokenizer'],
            translator_model=context.bot_data['translator_model'],
            bert_tokenizer=context.bot_data['bert_tokenizer'],
            bert_model=context.bot_data['bert_model'],
            device=context.bot_data['device']
        )
        
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к упрощённому", callback_data="back_to_simplified")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await safe_edit_message(
            query,
            f"🇬🇧 *Перевод на английский:*\n\n{translated}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await safe_edit_message(query, f"❌ Ошибка перевода: {e}")

async def handle_change_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # Проверяем, есть ли текст для упрощения
    if not context.user_data.get('pending_text'):
        await safe_edit_message(query, "❌ Нет текста для упрощения. Отправьте текст или файл сначала.")
        return
    
    await query.message.reply_text(
        "🔄 *Новый уровень упрощения*\nВыбери другой вариант:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            # Убрана кнопка "Лёгкий"
            [InlineKeyboardButton("⚖️ Средний", callback_data="simplify_medium")],
            [InlineKeyboardButton("🔥 Сильный", callback_data="simplify_strong")],
            [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
        ])
    )

async def handle_show_original(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    original = context.user_data.get('pending_text', '').strip()
    
    if not original:
        await query.answer("❌ Оригинальный текст не найден", show_alert=True)
        return
    
    try:
        await query.delete_message()
    except Exception as e:
        logger.warning(f"Error deleting message: {e}")
    
    max_length = 4096 - 100
    if len(original) <= max_length:
        await query.message.reply_text(
            f"📜 *Оригинальный текст:*\n\n{original}",
            parse_mode='Markdown'
        )
    else:
        parts = split_text(original, max_chars=3500)
        for i, part in enumerate(parts):
            if part.strip():
                text = f"📜 *Оригинальный текст (часть {i+1}):*\n\n{part}"
                await query.message.reply_text(text, parse_mode='Markdown')
                await asyncio.sleep(0.5)
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад к упрощённому", callback_data="back_to_simplified")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(
        "Хочешь вернуться к упрощённому тексту?",
        reply_markup=reply_markup
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    logger.info(f"User {user_id} clicked: {data}")
    
    if data.startswith("simplify_claim_"):
        await simplify_claim(update, context)
    elif data.startswith("change_claim_level_"):
        await change_claim_level(update, context)
    elif data.startswith("simplify_claim_medium_") or data.startswith("simplify_claim_strong_"):
        # Извлекаем индекс утверждения и уровень
        parts = data.split('_')
        strength = parts[2]
        claim_index = int(parts[3])
        await simplify_claim_with_strength(update, context, claim_index, strength)
    elif data == "back_to_uploaded_text":
        await show_last_uploaded_text(update, context)
    elif data == "back_to_fact_check":
        from handlers import fact_checking_mode
        await fact_checking_mode(update, context)
    elif data == "fact_check_help":
        await fact_check_help(update, context)
    elif data == "fact_checking":
        from handlers import fact_checking_mode
        await fact_checking_mode(update, context)
    elif data == "back_to_simplified":
        await handle_back_to_simplified(update, context)
    elif data.startswith("simplify_"):
        await handle_simplify(update, context)
    elif data == "translate":
        await handle_translate(update, context)
    elif data == "change_level":
        await handle_change_level(update, context)
    elif data == "show_original":
        await handle_show_original(update, context)
    elif data == "back_to_main":
        keyboard = get_main_keyboard()
        await query.message.reply_text(
            "Выбери действие:",
            reply_markup=keyboard
        )
    elif data == "help":
        await show_help(update, context)
    elif data == "restart":
        from handlers import start
        await start(update, context)
    else:
        logger.warning(f"Unknown callback data: {data}")
        await query.edit_message_text("❌ Неизвестное действие")

def setup_callbacks(application, models):
    # Сохраняем модели в bot_data для доступа из обработчиков
    application.bot_data.update(models)
    
    # Добавляем обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_click))