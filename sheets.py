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
        # Условное форматирование - красный для "Нет контактов"
        sh.batch_update({
            "requests": [{
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": ws.id, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 16}],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Нет контактов"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 0.98, "green": 0.88, "blue": 0.88}
                            }
                        }
                    },
                    "index": 0
                }
            }, {
                "addConditionalFormatRule": {
                    "rule": {
                        "ranges": [{"sheetId": ws.id, "startRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 16}],
                        "booleanRule": {
                            "condition": {
                                "type": "TEXT_EQ",
                                "values": [{"userEnteredValue": "Отправлено"}]
                            },
                            "format": {
                                "backgroundColor": {"red": 0.85, "green": 0.95, "blue": 0.85}
                            }
                        }
                    },
                    "index": 1
                }
            }]
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

def get_leads_for_followup():
        """Возвращает лиды где прошло 7 дней и нет ответа и не было повторного письма"""
        try:
                    sheet = get_sheet()
                    rows = sheet.get_all_records()
                    result = []
                    today = datetime.now().date()

        for i, row in enumerate(rows):
                        sent_date_str = row.get('sent_date', '')
                        status = row.get('status', '')
                        followup_sent = row.get('followup_sent', '')
                        email = row.get('email', '')

            if not sent_date_str or not email:
                                continue
                            if status in ['Ответил', 'Отказ']:
                                                continue
                                            if followup_sent:
                                                                continue

            try:
                                sent_date = datetime.strptime(sent_date_str, '%Y-%m-%d').date()
                            except:
                continue

                                            if (today - sent_date).days >= 7:
                                                                result.append({
                                                                                        'row_index': i + 2,
                                                                                        'company': row.get('company', ''),
                                                                                        'email': email,
                                                                                        'name': row.get('contact_name', ''),
                                                                })

        return result
except Exception as e:
        print(f"[sheets] Ошибка get_leads_for_followup: {e}")
        return []


def mark_followup_sent(row_index):
        """Ставит дату в колонку followup_sent"""
    try:
                sheet = get_sheet()
        headers = sheet.row_values(1)
        if 'followup_sent' not in headers:
                        col = len(headers) + 1
                        sheet.update_cell(1, col, 'followup_sent')
else:
            col = headers.index('followup_sent') + 1

        sheet.update_cell(row_index, col, datetime.now().strftime('%Y-%m-%d'))
        print(f"[sheets] Followup отмечен для строки {row_index}")
except Exception as e:
        print(f"[sheets] Ошибка mark_followup_sent: {e}")
