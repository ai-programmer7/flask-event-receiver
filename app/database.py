
import sqlite3

from contextlib import contextmanager
from pathlib import Path


@contextmanager
def get_db(database_path):
    """
    Создаёт соединение с SQLite.
    Автоматически фиксирует транзакцию
    или откатывает её при ошибке.
    """
    Path(database_path).parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        database_path,
        timeout=5.0,
    )

    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(database_path):
    """Создаёт таблицы, если их ещё нет."""

    with get_db(database_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (
                        status IN (
                            'pending',
                            'success',
                            'failed',
                            'skipped'
                        )
                    ),
                attempts INTEGER NOT NULL DEFAULT 0
                    CHECK (attempts >= 0),
                next_retry_at TEXT,
                locked_until TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY (event_id)
                    REFERENCES events(event_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_queue
            ON tasks(status, next_retry_at, locked_until);
            """
        )
