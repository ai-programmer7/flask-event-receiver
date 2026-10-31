# Event Receiver

Небольшой Flask-сервис для приёма webhook-событий, сохранения их в SQLite и асинхронной обработки через собственную очередь задач.

## Технологии

- Python 3.11+
- Flask
- SQLite
- pytest

## Возможности

- Приём событий через `POST /webhook`.
- Проверка входящих данных.
- Защита от повторной обработки событий по уникальному `event_id`.
- Сохранение событий и задач в SQLite.
- Обработка задач отдельным worker-процессом.
- Повторные попытки обработки: максимум 3.
- Увеличение задержки между попытками.
- Статусы задач: `pending`, `success`, `failed`, `skipped`.
- Получение статистики через `GET /stats`.

## Установка

Клонируйте репозиторий и перейдите в папку проекта.

Создайте виртуальное окружение:

```bash
python -m venv .venv
```

Активируйте его.

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Установите зависимости:

```bash
pip install -r requirements.txt
```

## Запуск приложения

Запустите Flask-сервер:

```bash
python run.py
```

Приложение будет доступно по адресу:

`http://127.0.0.1:5000`

Проверка состояния:

`GET /health`

## Запуск worker

В отдельном терминале активируйте виртуальное окружение и выполните:

```bash
python run_worker.py
```

Worker будет проверять очередь и обрабатывать доступные задачи.

## API

### POST /webhook

Принимает новое событие.

Пример запроса:

```json
{
  "event_id": "payment-001",
  "type": "payment_succeeded",
  "payload": {
    "amount": 1500,
    "currency": "RUB"
  }
}
```

Успешный приём нового события:

- HTTP 202 Accepted.

Повторное событие с тем же `event_id`:

- HTTP 200 OK.

Некорректные данные:

- HTTP 400 Bad Request.

Неподдерживаемый Content-Type:

- HTTP 415 Unsupported Media Type.

### GET /stats

Возвращает статистику событий и задач.

Пример:

```json
{
  "total_events": 1,
  "events_by_type": {
    "payment_succeeded": 1
  },
  "total_tasks": 1,
  "tasks_by_status": {
    "pending": 0,
    "success": 1,
    "failed": 0,
    "skipped": 0
  }
}
```

## Обработка задач

Для типа события `payment_succeeded` реализован демонстрационный обработчик.

Поле `simulate_failures` в payload позволяет имитировать ошибки обработки.

Например:

```json
{
  "event_id": "payment-retry-001",
  "type": "payment_succeeded",
  "payload": {
    "amount": 2500,
    "simulate_failures": 2
  }
}
```

В этом случае первые две попытки завершатся ошибкой, а третья будет успешной.

Задержка между повторными попытками увеличивается: 1 секунда, затем 2 секунды.

После третьей неудачной попытки задача получает статус `failed`.

Неизвестные типы событий получают статус `skipped`.

## Тестирование

Запуск автоматических тестов:

```bash
pytest -v
```

Тесты проверяют доступность сервиса, приём webhook, защиту от дубликатов, валидацию данных и статистику.

## Структура проекта

```text
event_receiver/
├── app/
│   ├── __init__.py
│   ├── database.py
│   ├── routes.py
│   ├── services.py
│   ├── worker.py
│   └── handlers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_app.py
├── instance/
├── run.py
├── run_worker.py
├── requirements.txt
├── requirements-lock.txt
├── .gitignore
└── README.md
```
