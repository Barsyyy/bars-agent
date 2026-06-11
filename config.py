import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GMAIL_CREDENTIALS_FILE = os.getenv("GMAIL_CREDENTIALS_FILE", "gmail_credentials.json")
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
GMAIL_FROM = os.getenv("GMAIL_FROM")  # твой gmail
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID")
GOOGLE_SHEETS_CREDENTIALS = os.getenv("GOOGLE_SHEETS_CREDENTIALS", "sheets_credentials.json")

# Лимиты отправки в день
EMAIL_DAILY_LIMIT = int(os.getenv("EMAIL_DAILY_LIMIT", 20))
INSTAGRAM_DAILY_LIMIT = int(os.getenv("INSTAGRAM_DAILY_LIMIT", 3))

# Instagram аккаунт
INSTAGRAM_HANDLE = "dollskills3dart"

# Регионы и язык
REGION_LANGUAGE = {
    "KZ": "ru",
    "RU": "ru",
    "UZ": "ru",
    "BY": "ru",
    "GE": "en",
    "AM": "en",
    "EU": "en",
}

# Ниши для поиска новых лидов
SEARCH_NICHES = [
    "рекламное агентство",
    "digital агентство",
    "FMCG бренд",
    "beauty бренд",
    "fashion бренд",
    "застройщик недвижимость",
    "fintech стартап",
    "e-commerce бренд",
    "автодилер",
    "ресторанная сеть",
    "медицинская клиника",
    "спортивный бренд",
    "производитель напитков",
    "телеком оператор",
]

SEARCH_REGIONS = ["Алматы", "Астана", "Москва", "Санкт-Петербург", "Ташкент", "Минск"]
