import requests
import re
import time
from bs4 import BeautifulSoup


GIS_API_URL = "https://catalog.api.2gis.com/3.0/items"


def search_2gis(company_name: str, region: str, api_key: str) -> dict:
    """Ищет компанию в 2GIS и возвращает данные."""
    params = {
        "q": company_name,
        "region_id": region,
        "fields": "items.contact_groups,items.org,items.address",
        "key": api_key,
        "page_size": 1,
    }
    try:
        resp = requests.get(GIS_API_URL, params=params, timeout=10)
        data = resp.json()
        items = data.get("result", {}).get("items", [])
        if not items:
            return {}
        return items[0]
    except Exception as e:
        print(f"[2GIS] Ошибка запроса для {company_name}: {e}")
        return {}


def extract_contacts(item: dict) -> dict:
    """Извлекает телефон, email, сайт из ответа 2GIS."""
    contacts = {"phone": None, "email": None, "website": None}
    groups = item.get("contact_groups", [])
    for group in groups:
        for contact in group.get("contacts", []):
            ctype = contact.get("type")
            value = contact.get("value", "")
            if ctype == "phone" and not contacts["phone"]:
                contacts["phone"] = value
            elif ctype == "email" and not contacts["email"]:
                contacts["email"] = value
            elif ctype == "website" and not contacts["website"]:
                contacts["website"] = value
    return contacts


def scrape_email_from_site(url: str) -> str | None:
    """Парсит email с сайта компании если 2GIS не дал email."""
    if not url:
        return None
    try:
        if not url.startswith("http"):
            url = "https://" + url
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        emails = re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resp.text)
        # фильтруем мусор
        blocked = ["example", "sentry", "domain", "email", "test", "mail@mail"]
        for email in emails:
            if not any(b in email for b in blocked):
                return email
    except Exception as e:
        print(f"[SCRAPE] Ошибка парсинга {url}: {e}")
    return None


# Регионы 2GIS для СНГ
REGIONS = {
    "almaty": "141",
    "astana": "145",
    "moscow": "1",
    "spb": "2",
    "novosibirsk": "7",
    "yekaterinburg": "4",
    "tashkent": "1000016541",
    "minsk": "1000016574",
    "bishkek": "1000016589",
}


def find_contacts_for_lead(company_name: str, country: str, api_key: str) -> dict:
    """
    Основная функция - ищет контакты компании через 2GIS.
    country: 'kz', 'ru', 'uz', 'by', 'kg'
    """
    # Выбираем регион по стране
    region_map = {
        "kz": ["141", "145"],        # Алматы, Астана
        "ru": ["1", "2", "7", "4"],  # Москва, СПб, Новосибирск, Екб
        "uz": ["1000016541"],        # Ташкент
        "by": ["1000016574"],        # Минск
        "kg": ["1000016589"],        # Бишкек
    }
    regions = region_map.get(country, ["141", "1"])

    for region in regions:
        item = search_2gis(company_name, region, api_key)
        if item:
            contacts = extract_contacts(item)
            # Если email не нашли - парсим сайт
            if not contacts["email"] and contacts["website"]:
                contacts["email"] = scrape_email_from_site(contacts["website"])
            if contacts["email"] or contacts["phone"]:
                print(f"[2GIS] Найдено для {company_name}: {contacts}")
                return contacts
        time.sleep(0.3)

    print(f"[2GIS] Ничего не найдено для {company_name}")
    return {}
