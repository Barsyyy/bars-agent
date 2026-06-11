"""
pitcher.py - Генерация персонализированных питчей через Claude API.
Язык определяется автоматически по региону.
"""

from anthropic import Anthropic
import config

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)


def get_language(region: str) -> str:
    return config.REGION_LANGUAGE.get(region.upper(), "ru")


def generate_pitch(lead: dict, channel: str = "email") -> str:
    """
    Генерирует питч под конкретную компанию и канал.
    channel: "email" | "instagram"
    """
    lang = get_language(lead.get("region", "RU"))
    company = lead.get("company", "")
    niche = lead.get("niche", "")
    notes = lead.get("notes", "")
    region = lead.get("region", "")
    city = lead.get("city", "")

    if lang == "ru":
        lang_instruction = "Пиши на русском языке."
        studio_intro = "студия Bars Production (Алматы) — AI-видео и 3D реклама для брендов"
        cases = "среди клиентов — Nestlé, Dizzy Energy"
        ig_handle = "@dollskills3dart"
    else:
        lang_instruction = "Write in English."
        studio_intro = "Bars Production studio (Almaty) — AI video & 3D advertising for brands"
        cases = "clients include Nestlé, Dizzy Energy"
        ig_handle = "@dollskills3dart"

    if channel == "email":
        format_instruction = """
- Начни с "Здравствуйте," (или "Hello," для английского)
- Первое предложение — про них, что-то конкретное об их бизнесе или нише
- Второе — конкретное предложение что мы можем сделать для них
- Третье — короткий социальный proof (кейсы)
- Четвёртое — призыв к действию, конкретный вопрос
- Подпись: Антон / Bars Production / {ig_handle}
- Длина: 5-7 предложений, без воды
""".format(ig_handle=ig_handle)
    else:  # instagram
        format_instruction = """
- Без формального приветствия, сразу к делу
- 2-3 коротких предложения максимум
- Конкретное предложение под их нишу
- В конце: {ig_handle} — портфолио
- Тон: живой, не корпоративный
""".format(ig_handle=ig_handle)

    prompt = f"""Ты — Антон, владелец {studio_intro}.
{cases}.

Напиши {channel} для компании "{company}" ({niche}, {city}, {region}).
Контекст о компании: {notes}

{lang_instruction}

Правила:
{format_instruction}
- НЕ используй слово "фрилансер"
- НЕ упоминай цену
- НЕ пиши шаблонные фразы типа "рад предложить", "наша команда профессионалов"
- Пиши как человек, не как маркетолог
- Если не знаешь конкретных деталей о компании — пиши про их нишу в целом

Ответь только текстом письма/сообщения, без пояснений и кавычек."""

    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()


def generate_subject(lead: dict) -> str:
    """Генерирует тему письма для email."""
    lang = get_language(lead.get("region", "RU"))
    company = lead.get("company", "")
    niche = lead.get("niche", "")

    if lang == "ru":
        prompt = f"Напиши тему письма (subject) для холодного email компании {company} ({niche}). Тема должна быть конкретной, не кликбейтной, 5-8 слов. Только тему, без кавычек."
    else:
        prompt = f"Write an email subject line for a cold email to {company} ({niche}). Be specific, not clickbait, 5-8 words. Subject line only, no quotes."

    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()
