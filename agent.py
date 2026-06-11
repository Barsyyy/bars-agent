"""
agent.py - Главный оркестратор Bars Production Lead Agent.
Запускается каждый день в 09:00 (cron или Railway scheduler).

Что делает за один запуск:
1. Ищет 5 новых компаний
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
    new_leads = finder.find_and_enrich(existing, count=5)

    added_count = 0
    for lead in new_leads:
        # Дедупликация
        if lead.get("company") in existing:
            print(f"[agent] Пропуск дубля: {lead.get('company')}")
            continue

        # ── ШАГ 2: Генерация питчей ──────────────────────────────────────
        print(f"[agent] Генерирую питч для {lead.get('company')}...")

        if lead.get("email"):
            try:
                pitch_email = pitcher.generate_pitch(lead, channel="email")
                subject = pitcher.generate_subject(lead)
                lead["pitch_email"] = pitch_email
                lead["email_subject"] = subject
            except Exception as e:
                print(f"[agent] Ошибка генерации email-питча: {e}")
                lead["pitch_email"] = ""

        if lead.get("instagram"):
            try:
                pitch_ig = pitcher.generate_pitch(lead, channel="instagram")
                lead["pitch_instagram"] = pitch_ig
            except Exception as e:
                print(f"[agent] Ошибка генерации ig-питча: {e}")
                lead["pitch_instagram"] = ""

        # ── ШАГ 3: Добавление в Sheets ──────────────────────────────────
        sheets.add_lead(lead)
        existing.append(lead.get("company"))
        added_count += 1
        time.sleep(1)

    print(f"\n[agent] Добавлено новых лидов: {added_count}")

    # ── ШАГ 4: Отправка email по существующим лидам ──────────────────────────
    print("\n[agent] ШАГ 4: Отправка email...")
    to_contact = sheets.get_leads_to_contact()
    print(f"[agent] Лидов в очереди на контакт: {len(to_contact)}")

    email_sent = 0
    ig_queued = 0

    for lead in to_contact:
        company = lead.get("Компания", "")

        # Email
        if lead.get("Email") and sender.can_send_email():
            pitch = lead.get("Питч (email)", "")
            subject = f"AI-видео и 3D реклама для {company}"

            # Если питч не был сохранён — генерируем сейчас
            if not pitch:
                try:
                    pitch = pitcher.generate_pitch({
                        "company": company,
                        "region": lead.get("Регион", "RU"),
                        "city": lead.get("Город", ""),
                        "niche": lead.get("Ниша", ""),
                        "notes": lead.get("Заметки", ""),
                    }, channel="email")
                    subject = pitcher.generate_subject({
                        "company": company,
                        "region": lead.get("Регион", "RU"),
                        "niche": lead.get("Ниша", ""),
                    })
                    sheets.update_pitch(company, pitch_email=pitch)
                except Exception as e:
                    print(f"[agent] Ошибка генерации питча для {company}: {e}")
                    continue

            success = sender.send_email(lead["Email"], subject, pitch)
            if success:
                sheets.update_status(company, sheets.STATUS_SENT, str(date.today()))
                email_sent += 1
                time.sleep(2)  # пауза между отправками
            continue  # если email отправлен — instagram не нужен в этот же день

        # Instagram (только если email не отправлен)
        if lead.get("Instagram") and sender.can_send_instagram():
            pitch = lead.get("Питч (Instagram)", "")

            if not pitch:
                try:
                    pitch = pitcher.generate_pitch({
                        "company": company,
                        "region": lead.get("Регион", "RU"),
                        "city": lead.get("Город", ""),
                        "niche": lead.get("Ниша", ""),
                        "notes": lead.get("Заметки", ""),
                    }, channel="instagram")
                    sheets.update_pitch(company, pitch_instagram=pitch)
                except Exception as e:
                    print(f"[agent] Ошибка генерации ig-питча для {company}: {e}")
                    continue

            sender.add_to_instagram_queue(
                {"company": company, "instagram": lead["Instagram"]},
                pitch
            )
            sheets.update_status(company, "Instagram очередь")
            ig_queued += 1

    # ── ИТОГ ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 50)
    print(f"[agent] ГОТОВО:")
    print(f"  Новых лидов добавлено:  {added_count}")
    print(f"  Email отправлено:       {email_sent}")
    print(f"  Instagram в очереди:    {ig_queued}")
    ig_queue = sender.get_instagram_queue()
    if ig_queue:
        print(f"\n[agent] 📋 Instagram очередь ({len(ig_queue)} DM):")
        for item in ig_queue:
            print(f"  → {item['instagram']} ({item['company']})")
        print("  Открой @dollskills3dart и отправь вручную")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    run()
