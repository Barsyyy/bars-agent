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


def search_google_contacts(company: str, website: str) -> dict:
    """Ищет контакты компании через Google."""
    result = {"email": "", "instagram": ""}
    try:
        domain = website.replace("https://", "").replace("http://", "").split("/")[0] if website else ""
        query = f'"{company}" email contact' if not domain else f'site:{domain} email OR contact'
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=5"
        r = requests.get(url, headers=HEADERS, timeout=8)
        text = r.text

        if not result["email"]:
            emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
            skip = {"example", "yourdomain", "domain", "email", "mail", "test", "noreply", "no-reply", "google", "sentry", "w3"}
            clean = [e for e in emails if not any(s in e.lower() for s in skip)]
            if clean:
                result["email"] = clean[0]

        if not result["instagram"]:
            ig = re.findall(r'instagram\.com/([a-zA-Z0-9_.]+)', text)
            ig = [h for h in ig if h not in ("p", "reel", "stories", "explore", "accounts", "shoppingbag", "instagram")]
            if ig:
                result["instagram"] = "@" + ig[0]

    except Exception as e:
        print(f"[finder] Google поиск ошибка: {e}")
    return result


def scrape_website(url: str) -> dict:
    """Парсит сайт компании - расширенный список страниц."""
    result = {"email": "", "instagram": "", "found": False}

    if not url or not url.startswith("http"):
        return result

    base = url.rstrip("/")
    pages_to_check = [
        base,
        base + "/contacts",
        base + "/contact",
        base + "/about",
        base + "/kontakty",
        base + "/o-nas",
        base + "/about-us",
        base + "/kontakt",
        base + "/team",
        base + "/ru/contacts",
        base + "/ru/contact",
    ]

    for page_url in pages_to_check:
        try:
            r = requests.get(page_url, headers=HEADERS, timeout=8)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "lxml")

            # Ищем email в mailto ссылках
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("mailto:"):
                    email = href.replace("mailto:", "").split("?")[0].strip()
                    if email and "@" in email and not result["email"]:
                        skip = {"example", "yourdomain", "noreply", "no-reply", "test"}
                        if not any(s in email.lower() for s in skip):
                            result["email"] = email
                            result["found"] = True

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


def find_new_companies(existing_names: list[str], count: int = 5) -> list[dict]:
    exclude = ", ".join(existing_names[-50:]) if existing_names else "нет"

    prompt = f"""Ты агент поиска лидов для студии Bars Production (AI-видео и 3D реклама, Алматы).

Найди {count} реальных компаний — потенциальных клиентов для AI-видеорекламы и 3D контента.
Целевые регионы: Казахстан, Россия, Узбекистан, Беларусь, Грузия, Армения.
Целевые ниши: бренды FMCG, beauty, fashion, недвижимость, финтех, e-commerce, рестораны, авто, спорт, телеком, digital-агентства, рекламные агентства.
Приоритет — средний и крупный бизнес, активно использующий видеорекламу.

НЕ включай эти компании (уже в базе): {exclude}

ВАЖНО: указывай только реально существующие компании с реальными сайтами.
Также укажи поле contact_hint — где обычно публикуют контакты эта компания (например "пресс-служба", "отдел маркетинга", типичный email формат).

Ответь СТРОГО в JSON, без markdown, без пояснений:
[
  {{
    "company": "Название компании",
    "region": "KZ|RU|UZ|BY|GE|AM",
    "city": "Город",
    "niche": "Ниша",
    "priority": "Высокий|Средний",
    "website": "https://... или пусто",
    "notes": "1-2 предложения почему они нам подходят",
    "contact_hint": "где искать контакты"
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


def enrich_lead(lead: dict) -> dict:
    website = lead.get("website", "")
    company = lead.get("company", "")

    # Сначала парсим сайт
    contacts = scrape_website(website)

    # Если не нашли - ищем через Google
    if not contacts["email"] and not contacts["instagram"]:
        print(f"[finder] {company}: сайт пустой, ищу через Google...")
        google = search_google_contacts(company, website)
        if google["email"]:
            contacts["email"] = google["email"]
            contacts["found"] = True
        if google["instagram"]:
            contacts["instagram"] = google["instagram"]
            contacts["found"] = True

    lead["email"] = contacts["email"]
    lead["instagram"] = contacts["instagram"]
    lead["contacts_found"] = contacts["found"]
    lead["status"] = "Не писал"

    print(f"[finder] {company}: email={'✓' if lead['email'] else '—'}, ig={'✓' if lead['instagram'] else '—'}")
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