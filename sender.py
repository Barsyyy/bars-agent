import smtplib
import json
import os
from datetime import date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

DAILY_COUNT_FILE = "daily_count.json"
INSTAGRAM_QUEUE_FILE = "instagram_queue.json"

def _load_counts():
    today = str(date.today())
    if os.path.exists(DAILY_COUNT_FILE):
        with open(DAILY_COUNT_FILE, encoding='utf-8') as f:
            data = json.load(f)
        if data.get("date") == today:
            return data
    return {"date": today, "email": 0, "instagram": 0}

def _save_counts(counts):
    with open(DAILY_COUNT_FILE, "w", encoding='utf-8') as f:
        json.dump(counts, f)

def can_send_email():
    return _load_counts()["email"] < config.EMAIL_DAILY_LIMIT

def can_send_instagram():
    return _load_counts()["instagram"] < config.INSTAGRAM_DAILY_LIMIT

def increment_count(channel):
    counts = _load_counts()
    counts[channel] = counts.get(channel, 0) + 1
    _save_counts(counts)

def get_today_counts():
    return _load_counts()

def send_email(to, subject, body):
    if not can_send_email():
        print(f"[sender] Лимит email исчерпан")
        return False
    if not to or "@" not in to:
        print(f"[sender] Невалидный email: {to}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.GMAIL_FROM
        msg["To"] = to
        msg.attach(MIMEText(body, "plain", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(config.GMAIL_FROM, config.GMAIL_APP_PASSWORD)
            server.sendmail(config.GMAIL_FROM, to, msg.as_string())
        increment_count("email")
        print(f"[sender] ✓ Email отправлен → {to}")
        return True
    except Exception as e:
        print(f"[sender] Ошибка: {e}")
        return False

def add_to_instagram_queue(lead, message):
    queue = []
    if os.path.exists(INSTAGRAM_QUEUE_FILE):
        with open(INSTAGRAM_QUEUE_FILE, encoding='utf-8') as f:
            queue = json.load(f)
    queue.append({
        "company": lead.get("company"),
        "instagram": lead.get("instagram"),
        "message": message,
        "date_added": str(date.today()),
        "sent": False
    })
    with open(INSTAGRAM_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    print(f"[sender] 📋 Instagram DM → {lead.get('instagram')}")

def get_instagram_queue(unsent_only=True):
    if not os.path.exists(INSTAGRAM_QUEUE_FILE):
        return []
    with open(INSTAGRAM_QUEUE_FILE, encoding='utf-8') as f:
        queue = json.load(f)
    return [i for i in queue if not i["sent"]] if unsent_only else queue

def mark_instagram_sent(instagram_handle):
    if not os.path.exists(INSTAGRAM_QUEUE_FILE):
        return
    with open(INSTAGRAM_QUEUE_FILE, encoding='utf-8') as f:
        queue = json.load(f)
    for item in queue:
        if item["instagram"] == instagram_handle:
            item["sent"] = True
    with open(INSTAGRAM_QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)
    increment_count("instagram")