"""
sender.py - Отправка через Gmail API (не SMTP).

SMTP заблокирован Railway, поэтому используем официальный Gmail API.

Счётчики хранятся в Google Sheets с кешем на 60 секунд.
"""

import os
import json
import base64
import time
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread
import config

INSTAGRAM_QUEUE_FILE = "instagram_queue.json"

SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.send"]
SCOPES_SHEETS = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Кеш счётчиков - читаем Sheets не чаще раза в 60 секунд
_counts_cache = None
_counts_cache_time = 0
_CACHE_TTL = 60


def _get_counters_sheet():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if creds_json:
        creds = service_account.Credentials.from_service_account_info(
            json.loads(creds_json), scopes=SCOPES_SHEETS
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            config.GOOGLE_SHEETS_CREDENTIALS, scopes=SCOPES_SHEETS
        )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(config.GOOGLE_SHEETS_ID)
    try:
        ws = sh.worksheet("Счётчики")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="Счётчики", rows=10, cols=3)
        ws.append_row(["Дата", "Email", "Instagram"])
    return ws


def _load_counts():
    global _counts_cache, _counts_cache_time
    today = str(date.today())

    if _counts_cache and _counts_cache.get("date") == today and (time.time() - _counts_cache_time) < _CACHE_TTL:
        return _counts_cache

    try:
        ws = _get_counters_sheet()
        records = ws.get_all_records()
        for row in records:
            if str(row.get("Дата")) == today:
                result = {
                    "date": today,
                    "email": int(row.get("Email", 0)),
                    "instagram": int(row.get("Instagram", 0)),
                }
                _counts_cache = result
                _counts_cache_time = time.time()
                return result
    except Exception as e:
        print(f"[sender] Ошибка чтения счётчиков: {e}")
        if _counts_cache and _counts_cache.get("date") == today:
            return _counts_cache

    result = {"date": today, "email": 0, "instagram": 0}
    _counts_cache = result
    _counts_cache_time = time.time()
    return result


def _save_counts(counts):
    global _counts_cache, _counts_cache_time
    today = str(date.today())
    try:
        ws = _get_counters_sheet()
        records = ws.get_all_records()
        for i, row in enumerate(records, start=2):
            if str(row.get("Дата")) == today:
                ws.update(f"A{i}:C{i}", [[today, counts["email"], counts["instagram"]]])
                _counts_cache = counts
                _counts_cache_time = time.time()
                return
        ws.append_row([today, counts["email"], counts["instagram"]])
        _counts_cache = counts
        _counts_cache_time = time.time()
    except Exception as e:
        print(f"[sender] Ошибка сохранения счётчиков: {e}")


def can_send_email():
    return _load_counts()["email"] < config.EMAIL_DAILY_LIMIT


def can_send_instagram():
    return _load_counts()["instagram"] < config.INSTAGRAM_DAILY_LIMIT


def increment_count(channel):
    counts = dict(_load_counts())
    counts[channel] = counts.get(channel, 0) + 1
    _save_counts(counts)


def get_today_counts():
    return _load_counts()


# ── Gmail API ────────────────────────────────────────────────────────────────

def _get_gmail_service():
    token_json = os.environ.get("GMAIL_TOKEN_JSON")
    if not token_json:
        token_file = config.GMAIL_TOKEN_FILE
        if os.path.exists(token_file):
            with open(token_file) as f:
                token_json = f.read()
        else:
            raise Exception("Нет GMAIL_TOKEN_JSON в env и нет файла gmail_token.json.")

    creds_data = json.loads(token_json)
    creds = Credentials(
        token=creds_data.get("token"),
        refresh_token=creds_data.get("refresh_token"),
        token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=creds_data.get("client_id"),
        client_secret=creds_data.get("client_secret"),
        scopes=creds_data.get("scopes", SCOPES_GMAIL),
    )
    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str) -> bool:
    if not can_send_email():
        print(f"[sender] Лимит email исчерпан")
        return False

    if not to or "@" not in to:
        print(f"[sender] Невалидный email: {to}")
        return False

    try:
        service = _get_gmail_service()

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.GMAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()

        increment_count("email")
        print(f"[sender] Email отправлен -> {to}")
        return True

    except HttpError as e:
        print(f"[sender] Gmail API ошибка: {e}")
        return False
    except Exception as e:
        print(f"[sender] Ошибка: {e}")
        return False


# ── Instagram очередь ────────────────────────────────────────────────────────

def add_to_instagram_queue(lead, message):
    queue = []
    if os.path.exists(INSTAGRAM_QUEUE_FILE):
        with open(INSTAGRAM_QUEUE_FILE, encoding="utf-8") as f:
            queue = json.load(f)

    queue.append({
        "company": lead.get("company"),
        "instagram": lead.get("instagram"),
        "message": message,
        "date_added": str(date.today()),
        "sent": False,
    })

    with open(INSTAGRAM_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

    print(f"[sender] Instagram DM -> {lead.get('instagram')}")


def get_instagram_queue(unsent_only=True):
    if not os.path.exists(INSTAGRAM_QUEUE_FILE):
        return []
    with open(INSTAGRAM_QUEUE_FILE, encoding="utf-8") as f:
        queue = json.load(f)
    return [i for i in queue if not i["sent"]] if unsent_only else queue


def mark_instagram_sent(instagram_handle):
    if not os.path.exists(INSTAGRAM_QUEUE_FILE):
        return
    with open(INSTAGRAM_QUEUE_FILE, encoding="utf-8") as f:
        queue = json.load(f)
    for item in queue:
        if item["instagram"] == instagram_handle:
            item["sent"] = True
    with open(INSTAGRAM_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    increment_count("instagram")


def send_followup_email(to_email, company_name, contact_name):
        """Отправляет повторное письмо через 7 дней"""
        try:
                    creds = get_gmail_credentials()
                    service = build('gmail', 'v1', credentials=creds)

        name_part = contact_name if contact_name else 'Добрый день'

            body = f"""{name_part},

            неделю назад я отправлял вам письмо с предложением по AI-видео и 3D-рекламе для {company_name}.

            Хотел уточнить — актуально ли это для вас сейчас? Буду рад ответить на любые вопросы.

            С уважением,
            Антон
            Bars Production | @dollskills3dart
            """

        message = MIMEMultipart()
        message['To'] = to_email
        message['From'] = 'dollskills@gmail.com'
        message['Subject'] = f'Повторно: AI-видео для {company_name}'
        message.attach(MIMEText(body, 'plain', 'utf-8'))

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(
                        userId='me',
                        body={'raw': raw}
        ).execute()

        print(f"[sender] Followup отправлен: {to_email}")
        return True

except Exception as e:
        print(f"[sender] Ошибка followup {to_email}: {e}")
        return False
