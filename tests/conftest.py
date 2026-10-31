
import pytest
from app import create_app


@pytest.fixture
def app(tmp_path):
    # Для тестов используем отдельную временную базу данных
    test_db = tmp_path / "test_events.db"

    app = create_app({
        "TESTING": True,
        "DATABASE": str(test_db),
    })

    yield app


@pytest.fixture
def client(app):
    return app.test_client()
