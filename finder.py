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


def find_new_companies(existing_names: list[str], count: int = 5) -> list[dict]:
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
        model="claude-haiku-4-5-20251001",
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


def scrape_website(url: str) -> dict:
    result = {"email": "", "instagram": "", "found": False}

    if not url or not url.startswith("http"):
        return result

    pages_to_check = [url, url.rstrip("/") + "/contacts", url.rstrip("/") + "/contact", url.rstrip("/") + "/about"]

    for page_url in pages_to_check:
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")
            text = soup.get_text(" ", strip=True)
            html = r.text

            if not result["email"]:
                emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
                skip = {"example", "yourdomain", "domain", "email", "mail", "test", "noreply", "no-reply", "support@sentry"}
                clean = [e for e in emails if not any(s in e.lower() for s in skip)]
                if clean:
                    result["email"] = clean[0]
                    result["found"] = True

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


def enrich_lead(lead: dict) -> dict:
    website = lead.get("website", "")
    contacts = scrape_website(website)

    lead["email"] = contacts["email"]
    lead["instagram"] = contacts["instagram"]
    lead["contacts_found"] = contacts["found"]
    lead["status"] = "Не писал"

    print(f"[finder] {lead['company']}: email={'✓' if lead['email'] else '—'}, ig={'✓' if lead['instagram'] else '—'}")
    return lead


def find_and_enrich(existing_names: list[str], count: int = 5) -> list[dict]:
    print(f"[finder] Ищу {count} новых компаний...")
    companies = find_new_companies(existing_names, count)
    print(f"[finder] Найдено: {len(companies)}")

    enriched = []
    for c in companies:
        lead = enrich_lead(c)
        enriched.append(lead)
        time.sleep(1)

    return enriched