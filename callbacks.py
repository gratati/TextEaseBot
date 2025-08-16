# callbacks.py
# Обработчики нажатий на кнопки Telegram-бота

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import asyncio
import random
import logging

# Глобальные переменные (должны быть инициализированы в bot.py)
simplify_long_text = None
translate_text = None
evaluate_simplification = None
split_text = None
sent_tokenize = None
logger = logging.getLogger(__name__)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Основной обработчик нажатий на inline-кнопки
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    user_id = update.effective_user.id
    logger.info(f"User {user_id} clicked: {data}")

    # --- Фактчекинг: разбивка на утверждения ---
    if data == "fact_checking":
        original = context.user_data.get('pending_text', '')
        if not original or not original.strip():
            await query.edit_message_text("❌ Нет текста для анализа.")
            return

        try:
            sentences = sent_tokenize(original, language='russian')
        except:
            sentences = sent_tokenize(original)

        claims = [s.strip() for s in sentences if s.strip() and len(s) > 10]
        if not claims:
            await query.edit_message_text("❌ Не удалось выделить утверждения.")
            return

        # Обрезаем, если слишком длинно
        claims_text = "\n".join([f"{i}. {claim}" for i, claim in enumerate(claims, 1)])
        if len(claims_text) > 3500:
            claims_text = claims_text[:3500] + "\n\n… (обрезано)"

        # Кнопка "Назад"
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад к упрощённому", callback_data="back_to_simplified")]
        ]

        await query.edit_message_text(
            f"🔍 *Режим фактчекинга*\n\n{claims_text}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    # --- Возврат к упрощённому тексту ---
    elif data == "back_to_simplified":
        simplified = context.user_data.get('simplified_text', '')
        strength = context.user_data.get('last_strength', 'medium')
        if not simplified:
            await query.edit_message_text("❌ Нет упрощённого текста.")
            return

        keyboard = [
            [InlineKeyboardButton("🔤 Перевести на английский", callback_data="translate")],
            [InlineKeyboardButton("🔄 Попробовать другой уровень", callback_data="change_level")],
            [InlineKeyboardButton("📄 Показать оригинал", callback_data="show_original")],
            [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
        ]

        await query.edit_message_text(
            f"✅ *Упрощённый текст ({'лёгкий' if strength == 'light' else 'средний' if strength == 'medium' else 'сильный'}):*\n\n{simplified}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

    # --- Упрощение текста ---
    elif data.startswith("simplify_"):
        strength = data.split("_")[1]
        text = context.user_data.get('pending_text', '')
        if not text or not text.strip():
            await query.edit_message_text("❌ Не найден текст для упрощения.")
            return

        thinking_messages = [
            "🧠 Анализирую...",
            "✍️ Упрощаю с сохранением смысла...",
            "🔍 Переписываю — чтобы было ясно...",
            "🧩 Готовлю результат...",
            "✅ Почти готово!"
        ]
        messages = random.sample(thinking_messages, len(thinking_messages))

        for msg in messages:
            if msg != query.message.text:
                try:
                    await query.edit_message_text(msg)
                except:
                    pass
            await asyncio.sleep(1.2)

        simplified = simplify_long_text(text, strength=strength)
        context.user_data['simplified_text'] = simplified
        context.user_data['last_strength'] = strength

        metrics = evaluate_simplification(text, simplified)
        quality_info = (
            f"\n\n📊 *Оценка упрощения:*\n"
            f"🔤 Длина: {metrics['original_length']} → {metrics['simplified_length']} слов\n"
            f"⚖️ Сохранение смысла (BLEU): {metrics['bleu']}/100\n"
            f"💡 {metrics['quality_hint']}"
        )

        warning = ""
        if len(simplified.split()) > 300:
            warning = "\n\n⚠️ *Внимание:* текст длинный — мог быть частично обрезан."

        keyboard = [
            [InlineKeyboardButton("🔤 Перевести на английский", callback_data="translate")],
            [InlineKeyboardButton("🔄 Попробовать другой уровень", callback_data="change_level")],
            [InlineKeyboardButton("📄 Показать оригинал", callback_data="show_original")],
            [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ *Упрощённый текст ({strength}):*\n\n{simplified}{quality_info}{warning}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    # --- Перевод на английский ---
    elif data == "translate":
        simplified = context.user_data.get('simplified_text', '')
        if not simplified:
            await query.edit_message_text("❌ Нет текста для перевода.")
            return

        await query.edit_message_text("🔤 Перевожу на английский...")

        try:
            translated = translate_text(simplified)
            keyboard = [
                [InlineKeyboardButton("⬅️ Назад к упрощённому", callback_data="back_to_simplified")]
            ]
            await query.edit_message_text(
                f"🇬🇧 *Перевод на английский:*\n\n{translated}",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Translation error for user {user_id}: {e}")
            await query.edit_message_text(f"❌ Ошибка перевода: {e}")

    # --- Попробовать другой уровень ---
    elif data == "change_level":
        await query.message.reply_text(
            "🔄 *Новый уровень упрощения*\nВыбери другой вариант:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🙂 Лёгкий", callback_data="simplify_light")],
                [InlineKeyboardButton("⚖️ Средний", callback_data="simplify_medium")],
                [InlineKeyboardButton("🔥 Сильный", callback_data="simplify_strong")],
                [InlineKeyboardButton("🔍 Фактчекинг", callback_data="fact_checking")]
            ])
        )

    # --- Показать оригинал ---
    elif data == "show_original":
        original = context.user_data.get('pending_text', '')
        if not original:
            await query.answer("❌ Оригинальный текст не найден", show_alert=True)
            return

        try:
            await query.delete_message()
        except:
            pass

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
        await query.message.reply_text(
            "Хочешь вернуться к упрощённому тексту?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# --- Регистрация обработчика ---
def register_callbacks(app):
    """
    Регистрирует обработчик кнопок.
    """
    app.add_handler(CallbackQueryHandler(button_click))