"""
agent.py - Главный оркестратор Bars Production Lead Agent.
Запускается каждый день в 09:00 (cron или Railway scheduler).


Что делает за один запуск:
1. Ищет 20 новых компаний
2. Парсит их сайты — реальные email и Instagram
3. Генерирует персонализированный питч
4. Отправляет email автоматически (до 20/день)
5. Кладёт Instagram DM в очередь (до 3/день)
6. Всё синхронизирует в Google Sheets
"""


import time
from datetime import date


import config
import finder
import pitcher
import sender
import sheets




def run():
    print("\n" + "=" * 50)
    print(f"BARS PRODUCTION LEAD AGENT — {date.today()}")
    print("=" * 50)


    counts = sender.get_today_counts()
    print(f"[agent] Отправлено сегодня: email={counts.get('email', 0)}/{config.EMAIL_DAILY_LIMIT}, instagram={counts.get('instagram', 0)}/{config.INSTAGRAM_DAILY_LIMIT}")


    # ── ШАГ 1: Поиск новых лидов ────────────────────────────────────────────
    print("\n[agent] ШАГ 1: Поиск новых компаний...")
    existing = sheets.get_existing_names()
    new_leads = finder.find_and_enrich(existing, count=20)

