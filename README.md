# Bars Production Lead Agent

Автономный агент лидогенерации: каждый день находит новые компании,
парсит реальные контакты, генерирует питч и отправляет письма.

## Что делает каждый день

1. Ищет 5 новых компаний (Claude API)
2. Парсит их сайты - реальные email и Instagram
3. Генерирует персонализированный питч (язык по региону)
4. Отправляет до 20 email автоматически (Gmail API)
5. Кладёт до 3 Instagram DM в очередь - ты отправляешь вручную
6. Все статусы обновляются в Google Sheets автоматически

---

## Настройка

### 1. Переменные окружения (.env)

Создай файл `.env` в папке агента:

```
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_FROM=твой@gmail.com
GOOGLE_SHEETS_ID=ID_таблицы_из_URL
EMAIL_DAILY_LIMIT=20
INSTAGRAM_DAILY_LIMIT=3
```

### 2. Gmail API

1. Перейди на https://console.cloud.google.com
2. Создай проект → APIs & Services → Enable APIs
3. Включи: Gmail API
4. Credentials → Create → OAuth 2.0 Client ID → Desktop App
5. Скачай JSON → сохрани как `gmail_credentials.json`
6. Первый раз запусти локально — откроется браузер для авторизации
7. После авторизации появится `gmail_token.json` — загрузи его на Hetzner

### 3. Google Sheets API

1. В том же проекте → APIs & Services → Enable: Google Sheets API
2. Credentials → Create → Service Account
3. Скачай JSON → сохрани как `sheets_credentials.json`
4. Открой свою таблицу Google Sheets
5. Поделись таблицей с email сервис-аккаунта (из JSON файла)
6. Скопируй ID таблицы из URL (между /d/ и /edit)

### 4. Установка зависимостей

```bash
pip install anthropic gspread google-auth google-auth-oauthlib \
  google-auth-httplib2 google-api-python-client \
  requests beautifulsoup4 lxml python-dotenv
```

---

## Запуск

### Локально (тест)
```bash
python agent.py
```

### На Hetzner (автозапуск каждый день в 09:00)

Загрузи все файлы на сервер:
```bash
scp -r bars-agent/ root@YOUR_SERVER_IP:/home/bars-agent/
```

Добавь cron задачу:
```bash
crontab -e
```

Добавь строку:
```
0 9 * * * cd /home/bars-agent && python agent.py >> /var/log/bars-agent.log 2>&1
```

---

## Структура таблицы Google Sheets

Лист "Лиды" создаётся автоматически при первом запуске.

Колонки:
- ID, Компания, Регион, Город, Ниша, Приоритет
- **Статус** — автообновляется агентом
- Сайт, Email, Instagram
- **Контакты найдены** — ✓ или — (если не нашёл — не выдумывает)
- Питч (email), Питч (Instagram)
- Дата добавления, Дата отправки
- Заметки

### Статусы
- `Не писал` — новый лид, ещё не контактировали
- `Нет контактов` — сайт есть, но email/Instagram не найден
- `Instagram очередь` — ждёт ручной отправки DM
- `Отправлено` — email ушёл
- `Ответил` — меняй вручную
- `В работе` — меняй вручную
- `Отказ` — меняй вручную

---

## Instagram очередь

Агент НЕ отправляет DM автоматически (риск бана @dollskills3dart).
Вместо этого формирует файл `instagram_queue.json`.

Каждый день после запуска агента:
1. Открой Instagram с @dollskills3dart
2. Агент покажет список: кому писать и что писать
3. Скопируй текст, отправь вручную

После отправки пометь в Sheets статус → "Отправлено".

---

## Файлы

```
bars-agent/
├── agent.py          - главный файл, запускай его
├── finder.py         - поиск компаний + парсинг контактов
├── pitcher.py        - генерация питчей (Claude API)
├── sender.py         - Gmail отправка + Instagram очередь
├── sheets.py         - синхронизация с Google Sheets
├── config.py         - настройки
├── .env              - секреты (не коммитить!)
├── gmail_credentials.json
├── gmail_token.json
├── sheets_credentials.json
├── daily_count.json  - счётчик отправок (сбрасывается каждый день)
└── instagram_queue.json
```
