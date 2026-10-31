
import json
import time

from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.handlers import process_event, SkipEvent


MAX_ATTEMPTS = 3
LOCK_DURATION = 30


def utc_now():
    return datetime.now(timezone.utc)


def claim_task(database_path):
    """
    Атомарно забирает одну доступную задачу.

    Возвращает данные задачи или None.
    """

    now = utc_now()
    now_str = now.isoformat()

    with get_db(database_path) as db:
        # Не допускаем одновременного захвата
        # одной задачи разными worker.
        db.execute("BEGIN IMMEDIATE")

        # Если третий запуск завершился аварийно,
        # после окончания блокировки закрываем задачу.
        db.execute(
            """
            UPDATE tasks
            SET status = 'failed',
                last_error = 'Worker lease expired after max attempts',
                locked_until = NULL,
                updated_at = ?
            WHERE status = 'pending'
              AND attempts >= ?
              AND locked_until IS NOT NULL
              AND locked_until <= ?
            """,
            (now_str, MAX_ATTEMPTS, now_str),
        )

        task = db.execute(
            """
            SELECT
                tasks.id,
                tasks.event_id,
                tasks.attempts,
                events.type,
                events.payload
            FROM tasks
            JOIN events
                ON events.event_id = tasks.event_id
            WHERE tasks.status = 'pending'
              AND tasks.attempts < ?
              AND (
                  tasks.next_retry_at IS NULL
                  OR tasks.next_retry_at <= ?
              )
              AND (
                  tasks.locked_until IS NULL
                  OR tasks.locked_until <= ?
              )
            ORDER BY tasks.created_at, tasks.id
            LIMIT 1
            """,
            (MAX_ATTEMPTS, now_str, now_str),
        ).fetchone()

        if task is None:
            return None

        attempt = task["attempts"] + 1

        locked_until = (
            now + timedelta(seconds=LOCK_DURATION)
        ).isoformat()

        db.execute(
            """
            UPDATE tasks
            SET attempts = ?,
                locked_until = ?,
                updated_at = ?
            WHERE id = ?
              AND status = 'pending'
            """,
            (
                attempt,
                locked_until,
                now_str,
                task["id"],
            ),
        )

        return {
            "id": task["id"],
            "event_id": task["event_id"],
            "type": task["type"],
            "payload": json.loads(task["payload"]),
            "attempt": attempt,
            "locked_until": locked_until,
        }


def finish_task(database_path, task, status, error=None):
    """Завершает обработку задачи."""

    now = utc_now().isoformat()

    with get_db(database_path) as db:
        db.execute(
            """
            UPDATE tasks
            SET status = ?,
                last_error = ?,
                next_retry_at = NULL,
                locked_until = NULL,
                updated_at = ?
            WHERE id = ?
              AND status = 'pending'
              AND locked_until = ?
            """,
            (
                status,
                error,
                now,
                task["id"],
                task["locked_until"],
            ),
        )



def process_one_task(database_path):
    task = claim_task(database_path)

    if task is None:
        return False

    try:
        process_event(
            event_type=task["type"],
            payload=task["payload"],
            attempt=task["attempt"],
        )

    except SkipEvent as error:
        finish_task(
            database_path,
            task,
            status="skipped",
            error=str(error),
        )
        print(
            f"Task {task['id']} skipped: {error}"
        )

    except Exception as error:
        if task["attempt"] >= MAX_ATTEMPTS:
            finish_task(
                database_path,
                task,
                status="failed",
                error=str(error),
            )
            print(
                f"Task {task['id']} failed "
                f"on attempt {task['attempt']}/{MAX_ATTEMPTS}. "
                f"No more retries. Error: {error}"
            )
        else:
            delay = 2 ** (task["attempt"] - 1)
            retry_at = (
                utc_now() + timedelta(seconds=delay)
            ).isoformat()
            now = utc_now().isoformat()

            with get_db(database_path) as db:
                db.execute(
                    """
                    UPDATE tasks
                    SET status = 'pending',
                        next_retry_at = ?,
                        locked_until = NULL,
                        last_error = ?,
                        updated_at = ?
                    WHERE id = ?
                      AND status = 'pending'
                      AND locked_until = ?
                    """,
                    (
                        retry_at,
                        str(error),
                        now,
                        task["id"],
                        task["locked_until"],
                    ),
                )

            print(
                f"Task {task['id']} failed on attempt "
                f"{task['attempt']}/{MAX_ATTEMPTS}. "
                f"Retry in {delay} seconds. Error: {error}"
            )

    else:
        finish_task(
            database_path,
            task,
            status="success",
        )
        print(
            f"Task {task['id']} completed successfully "
            f"on attempt {task['attempt']}/{MAX_ATTEMPTS}."
        )

    return True



def run_worker(database_path, poll_interval=1):
    """Непрерывно проверяет очередь."""

    print("Worker started")

    while True:
        try:
            has_task = process_one_task(database_path)

            if not has_task:
                time.sleep(poll_interval)

        except Exception as error:
            print(f"Worker error: {error}")
            time.sleep(poll_interval)
