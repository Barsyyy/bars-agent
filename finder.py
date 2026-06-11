"""
finder.py - Поиск новых компаний и их реальных контактов.
Принцип: лучше пустое поле, чем выдуманный контакт.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from anthropic import Anthropic
import config

client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


# ─── Поиск новых компаний через Claude + web ────────────────────────────────

def find_new_companies(existing_names: list[str], count: int = 5) -> list[dict]:
    """
    Просит Claude найти реальные компании.
    Возвращает список с полями: company, region, niche, priority, website, notes
    """
    exclude = ", ".join(existing_names[-50:]) if existing_names else "нет"

    prompt = f"""Ты агент поиска лидов для студии Bars Production (AI-видео и 3D реклама, Алматы).

Найди {count} реальных компаний — потенциальных клиентов для AI-видеорекламы и 3D контента.
Целевые регионы: Казахстан, Россия, Узбекистан, Беларусь, Грузия, Армения.
Целевые ниши: бренды FMCG, beauty, fashion, недвижимость, финтех, e-commerce, рестораны, авто, спорт, телеком, digital-агентства, рекламные агентства.
Приоритет — средний и крупный бизнес, активно использующий видеорекламу.

НЕ включай эти компании (уже в базе): {exclude}

ВАЖНО: указывай только реально существующие компании с реальными сайтами.
Если не уверен в сайте — лучше оставь поле website пустым.

Ответь СТРОГО в JSON, без markdown, без пояснений:
[
  {{
    "company": "Название компании",
    "region": "KZ|RU|UZ|BY|GE|AM",
    "city": "Город",
    "niche": "Ниша",
    "priority": "Высокий|Средний",
    "website": "https://... или пусто",
    "notes": "1-2 предложения почему они нам подходят"
  }}
]"""

    response = client.messages.create(
        model="claude-opus-4-5-20251101",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    text = re.sub(r"```json|```", "", text).strip()

    try:
        companies = __import__("json").loads(text)
        return companies
    except Exception as e:
        print(f"[finder] Ошибка парсинга JSON от Claude: {e}")
        return []


# ─── Парсинг сайта компании ──────────────────────────────────────────────────

def scrape_website(url: str) -> dict:
    """
    Парсит сайт компании, ищет email и Instagram.
    Возвращает: { email, instagram, found }
    """
    result = {"email": "", "instagram": "", "found": False}

    if not url or not url.startswith("http"):
        return result

    # Страницы где обычно есть контакты
    pages_to_check = [url, url.rstrip("/") + "/contacts", url.rstrip("/") + "/contact", url.rstrip("/") + "/about"]

    for page_url in pages_to_check:
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text(" ", strip=True)
            html = r.text

            # Поиск email
            if not result["email"]:
                emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
                # Фильтруем мусор
                skip = {"example", "yourdomain", "domain", "email", "mail", "test", "noreply", "no-reply", "support@sentry"}
                clean = [e for e in emails if not any(s in e.lower() for s in skip)]
                if clean:
                    result["email"] = clean[0]
                    result["found"] = True

            # Поиск Instagram
            if not result["instagram"]:
                ig = re.findall(r'instagram\.com/([a-zA-Z0-9_.]+)', html)
                ig = [h for h in ig if h not in ("p", "reel", "stories", "explore", "accounts", "shoppingbag")]
                if ig:
                    result["instagram"] = "@" + ig[0]
                    result["found"] = True

            if result["email"] and result["instagram"]:
                break

            time.sleep(0.5)

        except Exception as e:
            print(f"[finder] Ошибка парсинга {page_url}: {e}")
            continue

    return result


# ─── Основная функция обогащения лида ───────────────────────────────────────

def enrich_lead(lead: dict) -> dict:
    """
    Принимает лид с полем website, добавляет email и instagram.
    Если ничего не нашёл — поля остаются пустыми (не выдумываем).
    """
    website = lead.get("website", "")
    contacts = scrape_website(website)

    lead["email"] = contacts["email"]
    lead["instagram"] = contacts["instagram"]
    lead["contacts_found"] = contacts["found"]
    lead["status"] = "Не писал"

    print(f"[finder] {lead['company']}: email={'✓' if lead['email'] else '—'}, ig={'✓' if lead['instagram'] else '—'}")
    return lead


# ─── Поиск + обогащение пачки новых лидов ───────────────────────────────────

def find_and_enrich(existing_names: list[str], count: int = 5) -> list[dict]:
    """
    Полный цикл: находит компании → парсит их сайты → возвращает обогащённые лиды.
    """
    print(f"[finder] Ищу {count} новых компаний...")
    companies = find_new_companies(existing_names, count)
    print(f"[finder] Найдено: {len(companies)}")

    enriched = []
    for c in companies:
        lead = enrich_lead(c)
        enriched.append(lead)
        time.sleep(1)  # вежливо к серверам

    return enriched
