"""
pitcher.py - Генерация персонализированных питчей через Claude API.
"""

from anthropic import Anthropic
import config

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

PORTFOLIO = "https://www.behance.net/dollskills3dart"
PORTFOLIO_CASES = "Dizzy Energy x Helios, Nornickel, Nestle"


def get_language(region: str) -> str:
    return config.REGION_LANGUAGE.get(region.upper(), "ru")


def generate_pitch(lead: dict, channel: str = "email") -> str:
    lang = get_language(lead.get("region", "RU"))
    company = lead.get("company", "")
    niche = lead.get("niche", "")
    notes = lead.get("notes", "")
    region = lead.get("region", "")
    city = lead.get("city", "")

    if lang == "ru":
        lang_instruction = "Пиши на русском языке."
        studio_intro = "студия Bars Production (Алматы) - AI-видео и 3D реклама для брендов"
        cases = f"среди клиентов - {PORTFOLIO_CASES}"
        ig_handle = "@dollskills3dart"
        portfolio_line = f"Портфолио: {PORTFOLIO}"
    else:
        lang_instruction = "Write in English."
        studio_intro = "Bars Production studio (Almaty) - AI video & 3D advertising for brands"
        cases = f"clients include {PORTFOLIO_CASES}"
        ig_handle = "@dollskills3dart"
        portfolio_line = f"Portfolio: {PORTFOLIO}"

    if channel == "email":
        format_instruction = f"""
- Начни с "Здравствуйте," (или "Hello," для английского)
- Первое предложение - про них конкретно, их нишу или продукт
- Второе - что конкретно мы можем сделать для них (AI-видео, 3D реклама, CGI)
- Третье - социальный proof: {cases}
- Четвёртое - призыв к действию, конкретный вопрос
- Пятое - {portfolio_line}
- Подпись: Антон / Bars Production / {ig_handle}
- Длина: 5-7 предложений, без воды
"""
    else:
        format_instruction = f"""
- Без формального приветствия, сразу к делу
- 2-3 коротких предложения максимум
- Конкретное предложение под их нишу
- В конце: {portfolio_line} | {ig_handle}
- Тон: живой, не корпоративный
"""

    prompt = f"""Ты - Антон, владелец {studio_intro}.

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

Ответь только текстом письма/сообщения, без пояснений и кавычек."""

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()


def generate_subject(lead: dict) -> str:
    lang = get_language(lead.get("region", "RU"))
    company = lead.get("company", "")
    niche = lead.get("niche", "")

    if lang == "ru":
        prompt = f"Напиши тему письма для холодного email компании {company} ({niche}). Конкретная, не кликбейтная, 5-8 слов. Только тему, без кавычек."
    else:
        prompt = f"Write email subject for cold email to {company} ({niche}). Specific, not clickbait, 5-8 words. Subject only, no quotes."

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=50,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()
