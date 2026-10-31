
import json
from datetime import datetime, timezone

from app.database import get_db


def create_event(database_path, event_id, event_type, payload):
    """
    Сохраняет событие и создаёт задачу в очереди.

    Возвращает True, если событие новое.
    Возвращает False, если event_id уже существует.
    """

    now = datetime.now(timezone.utc).isoformat()

    with get_db(database_path) as db:
        cursor = db.execute(
            """
            INSERT INTO events (
                event_id,
                type,
                payload,
                created_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(event_id) DO NOTHING
            """,
            (
                event_id,
                event_type,
                json.dumps(payload, ensure_ascii=False),
                now,
            ),
        )

        # Событие уже существует — повторно задачу не создаём.
        if cursor.rowcount == 0:
            return False

        db.execute(
            """
            INSERT INTO tasks (
                event_id,
                status,
                attempts,
                created_at,
                updated_at
            )
            VALUES (?, 'pending', 0, ?, ?)
            """,
            (event_id, now, now),
        )

    return True



def get_statistics(database_path):
    with get_db(database_path) as db:
        # Количество событий каждого типа
        event_rows = db.execute("""
            SELECT type, COUNT(*) AS total
            FROM events
            GROUP BY type
        """).fetchall()

        # Количество задач каждого статуса
        task_rows = db.execute("""
            SELECT status, COUNT(*) AS total
            FROM tasks
            GROUP BY status
        """).fetchall()

    events_by_type = {
        row["type"]: row["total"]
        for row in event_rows
    }

    tasks_by_status = {
        "pending": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    }

    for row in task_rows:
        tasks_by_status[row["status"]] = row["total"]

    return {
        "total_events": sum(events_by_type.values()),
        "events_by_type": events_by_type,
        "total_tasks": sum(tasks_by_status.values()),
        "tasks_by_status": tasks_by_status,
    }
