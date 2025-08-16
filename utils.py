# utils.py
# Вспомогательные функции для упрощения, перевода и оценки текста

import re
from nltk.tokenize import sent_tokenize
from sacrebleu import sentence_bleu

# Глобальные переменные (должны быть инициализированы в bot.py)
simplify_tokenizer = None
simplify_model = None
translator_tokenizer = None
translator_model = None
device = None


def split_text(text, max_chars=2000):
    """
    Разбивает текст на части по предложениям, не превышая max_chars.
    """
    try:
        sentences = sent_tokenize(text, language='russian')
    except:
        sentences = sent_tokenize(text)
    parts = []
    current = ""
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(current) + len(sent) <= max_chars:
            current += (" " + sent) if current else sent
        else:
            if current:
                parts.append(current)
            current = sent
    if current:
        parts.append(current)
    return parts


def simplify_text(text, strength="medium"):
    """
    Упрощает текст с заданной степенью.
    """
    if not text.strip():
        return text

    prompt = "упрости: " + text.strip()
    inputs = simplify_tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512
    ).to(device)

    input_length = inputs["input_ids"].shape[1]

    if strength == "strong":
        max_length = min(200, input_length + 50)
        min_length = max(60, input_length // 2)
        length_penalty = 0.6
    elif strength == "light":
        max_length = min(512, input_length * 2)
        min_length = max(120, input_length // 2)
        length_penalty = 1.2
    else:  # medium
        max_length = min(400, input_length + 100)
        min_length = max(100, input_length // 2)
        length_penalty = 1.0

    min_length = min(min_length, max_length)

    with torch.no_grad():
        outputs = simplify_model.generate(
            **inputs,
            max_length=max_length,
            min_length=min_length,
            num_beams=4,
            length_penalty=length_penalty,
            repetition_penalty=1.1,
            no_repeat_ngram_size=3,
            early_stopping=True,
            pad_token_id=simplify_tokenizer.pad_token_id,
            eos_token_id=simplify_tokenizer.eos_token_id
        )

    result = simplify_tokenizer.decode(outputs[0], skip_special_tokens=True)
    result = re.sub(r"<extra_id_\d+>", "", result)
    result = re.sub(r"\s+", " ", result).strip()
    result = re.sub(r"^Текст:\s*", "", result, flags=re.IGNORECASE)

    return result or text


def simplify_long_text(text, strength="medium"):
    """
    Упрощает длинный текст по частям.
    """
    parts = split_text(text, 2000)
    return " ".join(simplify_text(p, strength) for p in parts if p.strip())


def translate_text(text):
    """
    Переводит текст с русского на английский.
    """
    if not text.strip():
        return ""

    if len(text) < 500:
        inputs = translator_tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(device)
        with torch.no_grad():
            translated = translator_model.generate(
                **inputs,
                max_length=600
            )
        result = translator_tokenizer.decode(translated[0], skip_special_tokens=True)
        result = re.sub(r"^Text:\s*", "", result, flags=re.IGNORECASE)
        return result

    # Для длинных текстов — рекурсивная обработка
    sentences = sent_tokenize(text, language='russian')
    chunk = ""
    parts = []
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        if len(chunk) + len(sent) < 400:
            chunk += " " + sent if chunk else sent
        else:
            if chunk:
                parts.append(translate_text(chunk))
            chunk = sent
    if chunk:
        parts.append(translate_text(chunk))
    return " ".join(parts)


def evaluate_simplification(orig, simp):
    """
    Оценивает качество упрощения: длина, BLEU, интерпретация.
    """
    orig_len = len(orig.split())
    simp_len = len(simp.split())
    try:
        bleu = sentence_bleu(simp, [orig]).score
    except:
        bleu = 0.0
    return {
        "original_length": orig_len,
        "simplified_length": simp_len,
        "bleu": round(bleu, 2),
        "quality_hint": "🟢 Высокое сохранение" if bleu > 50 else "🟡 Частичное искажение"
    }