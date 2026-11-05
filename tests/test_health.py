import pytest
from fastapi.testclient import TestClient

from src.app.config import Settings
from src.app.main import app


def test_health_returns_ok() -> None:
    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_settings_read_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IP_PER_MINUTE", "5")

    configured = Settings(_env_file=None)

    assert configured.ip_per_minute == 5


def test_settings_read_database_and_user_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@localhost:5432/db")
    monkeypatch.setenv("USER_PER_DAY", "7")

    configured = Settings(_env_file=None)

    assert configured.database_url == "postgresql://u:p@localhost:5432/db"
    assert configured.user_per_day == 7
    assert configured.user_per_minute == 3
