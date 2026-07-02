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

def scrape_website(url: str) -> dict:
    """Парсит сайт компании - ищет реальные контакты."""
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

                    # Ищем mailto ссылки
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


def find_new_companies(existing_names: list[str], count: int = 20) -> list[dict]:
        exclude = ", ".join(existing_names[-50:]) if existing_names else "нет"

    prompt = f"""Ты агент поиска лидов для студии Bars Production (AI-видео и 3D реклама, Алматы).

    Найди {count} реальных компаний - потенциальных клиентов для AI-видеорекламы и 3D контента.

    Целевые регионы: Казахстан, Россия, Узбекистан, Беларусь, Грузия, Армения.

    Целевые ниши: бренды FMCG, beauty, fashion, недвижимость, финтех, e-commerce, рестораны, авто, спорт, телеком, digital-агентства, рекламные агентства.

    Приоритет - средний и крупный бизнес с активным маркетингом и видеорекламой.

    НЕ включай эти компании (уже в базе): {exclude}

    ВАЖНО:
    - Только реально существующие компании с работающими сайтами
    - Выбирай компании у которых на сайте ТОЧНО есть страница контактов с email
    - Предпочитай компании среднего размера - у крупных (Kaspi, Halyk) нет публичного email маркетинга
    - instagram_handle указывай только если точно знаешь реальный handle

    Ответь СТРОГО в JSON, без markdown:
    [
      {{
          "company": "Название",
              "region": "KZ|RU|UZ|BY|GE|AM",
                  "city": "Город",
                      "niche": "Ниша",
                          "priority": "Высокий|Средний",
                              "website": "https://...",
                                  "instagram_handle": "@handle или пусто",
                                      "notes": "почему подходят"
  }}
  ]"""

    response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text.strip()
    text = re.sub(r"```json|```", "", text).strip()

    try:
                import json
                companies = json.loads(text)
                return companies
except Exception as e:
            print(f"[finder] Ошибка парсинга JSON от Claude: {e}")
            return []


def enrich_lead(lead: dict) -> dict:
        website = lead.get("website", "")
        company = lead.get("company", "")

    # Парсим сайт - только реальные контакты
        contacts = scrape_website(website)

    # Instagram из подсказки Claude если парсер не нашёл
    if not contacts["instagram"]:
                ig_hint = lead.get("instagram_handle", "")
                if ig_hint and ig_hint.startswith("@"):
                                contacts["instagram"] = ig_hint
                                if contacts["email"]:
                                                    contacts["found"] = True

                        lead["email"] = contacts["email"]
    lead["instagram"] = contacts["instagram"]
    lead["contacts_found"] = contacts["found"]
    lead["status"] = "Не писал"

    print(f"[finder] {company}: email={'ok' if lead['email'] else '-'}, ig={'ok' if lead['instagram'] else '-'}")
    return lead


def find_and_enrich(existing_names: list[str], count: int = 20) -> list[dict]:
        print(f"[finder] Ищу {count} новых компаний...")
    companies = find_new_companies(existing_names, count)
    print(f"[finder] Найдено: {len(companies)}")

    enriched = []
    for c in companies:
                lead = enrich_lead(c)
        enriched.append(lead)
        time.sleep(1)

    return enriched
