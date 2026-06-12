"""
sheets.py - Чтение и запись лидов в Google Sheets.
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

COLUMNS = [
    "ID", "Компания", "Регион", "Город", "Ниша", "Приоритет",
    "Статус", "Сайт", "Email", "Instagram", "Контакты найдены",
    "Питч (email)", "Питч (Instagram)", "Дата добавления", "Дата отправки", "Заметки"
]

STATUS_NOT_SENT   = "Не писал"
STATUS_SENT       = "Отправлено"
STATUS_REPLIED    = "Ответил"
STATUS_REJECTED   = "Отказ"
STATUS_IN_WORK    = "В работе"
STATUS_NO_CONTACT = "Нет контактов"


def _get_sheet():
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    if creds_json:
        creds = Credentials.from_service_account_info(json.loads(creds_json), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(config.GOOGLE_SHEETS_CREDENTIALS, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(config.GOOGLE_SHEETS_ID)
    try:
        ws = sh.worksheet("Лиды")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="Лиды", rows=1000, cols=len(COLUMNS))
        ws.append_row(COLUMNS)
        ws.format("A1:P1", {
            "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.1},
            "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
        })
    return ws


def get_all_leads() -> list[dict]:
    ws = _get_sheet()
    records = ws.get_all_records()
    return records


def get_existing_names() -> list[str]:
    leads = get_all_leads()
    return [l.get("Компания", "") for l in leads if l.get("Компания")]


def add_lead(lead: dict) -> int:
    ws = _get_sheet()
    all_rows = ws.get_all_values()
    new_id = len(all_rows)

    contacts_found = "✓" if lead.get("contacts_found") else "—"
    status = STATUS_NO_CONTACT if not lead.get("contacts_found") else STATUS_NOT_SENT

    row = [
        new_id,
        lead.get("company", ""),
        lead.get("region", ""),
        lead.get("city", ""),
        lead.get("niche", ""),
        lead.get("priority", "Средний"),
        status,
        lead.get("website", ""),
        lead.get("email", ""),
        lead.get("instagram", ""),
        contacts_found,
        lead.get("pitch_email", ""),
        lead.get("pitch_instagram", ""),
        str(date.today()),
        "",
        lead.get("notes", ""),
    ]

    ws.append_row(row, value_input_option="USER_ENTERED")
    print(f"[sheets] + Добавлен лид: {lead.get('company')} [{status}]")
    return new_id


def update_status(company_name: str, status: str, sent_date: str = None):
    ws = _get_sheet()
    records = ws.get_all_records()

    for i, row in enumerate(records, start=2):
        if row.get("Компания") == company_name:
            status_col = COLUMNS.index("Статус") + 1
            ws.update_cell(i, status_col, status)
            if sent_date:
                date_col = COLUMNS.index("Дата отправки") + 1
                ws.update_cell(i, date_col, sent_date)
            print(f"[sheets] ✓ Статус обновлён: {company_name} → {status}")
            return True

    print(f"[sheets] Компания не найдена: {company_name}")
    return False


def update_pitch(company_name: str, pitch_email: str = None, pitch_instagram: str = None):
    ws = _get_sheet()
    records = ws.get_all_records()

    for i, row in enumerate(records, start=2):
        if row.get("Компания") == company_name:
            if pitch_email:
                col = COLUMNS.index("Питч (email)") + 1
                ws.update_cell(i, col, pitch_email)
            if pitch_instagram:
                col = COLUMNS.index("Питч (Instagram)") + 1
                ws.update_cell(i, col, pitch_instagram)
            return True
    return False


def get_leads_to_contact() -> list[dict]:
    leads = get_all_leads()
    return [
        l for l in leads
        if l.get("Статус") == STATUS_NOT_SENT
        and (l.get("Email") or l.get("Instagram"))
    ]