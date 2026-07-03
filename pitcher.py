"""
pitcher.py - Генерация персонализированных питчей через Claude API.
"""

from anthropic import Anthropic
import config

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

PORTFOLIO = "https://www.youtube.com/shorts/dbYgjtS_q0c"
PORTFOLIO_VFX = "https://vimeo.com/1150965452"
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
        portfolio_line = f"AI-видео: {PORTFOLIO} | VFX: {PORTFOLIO_VFX}"
    else:
        lang_instruction = "Write in English."
        studio_intro = "Bars Production studio (Almaty) - AI video & 3D advertising for brands"
        cases = f"clients include {PORTFOLIO_CASES}"
        ig_handle = "@dollskills3dart"
        portfolio_line = f"AI video: {PORTFOLIO} | VFX: {PORTFOLIO_VFX}"

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

    prompt = f"""Ты - Антон, владелец {studio_intro}. {cases}.

Напиши {channel} для компании "{company}" ({niche}, {city}, {region}).
Контекст о компании: {notes}

{lang_instruction}

Ключевые тезисы которые ОБЯЗАТЕЛЬНО должны быть в письме:
- Работаем быстро и качественно
- За плечами крупные клиенты и реальные проекты: {PORTFOLIO_CASES}
- Есть готовые идеи и сценарии специально под их бизнес/нишу
- Предлагаем либо полный продакшн, либо помощь со сценарием - как им удобно
- Ненавязчивый вопрос: интересно ли им посмотреть пару идей под их бренд?

Правила:
{format_instruction}
- НЕ используй слово "фрилансер"
- НЕ упоминай цену
- НЕ пиши шаблонные фразы типа "рад предложить", "наша команда профессионалов", "надеюсь на сотрудничество"
- Пиши как человек который уверен в своей работе, не как менеджер по продажам
- Тон: уверенный, конкретный, живой

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
