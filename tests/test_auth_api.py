from fastapi.testclient import TestClient

from src.app.models import AppUser


def test_api_routes_require_a_valid_session(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, _, _ = api
    client.app.dependency_overrides.clear()

    response = client.get("/api/me")

    assert response.status_code == 401
    assert response.json()["code"] == "HTTP_ERROR"


def test_authenticated_api_responses_are_not_cached(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, _, _ = api
    response = client.get("/api/me")
    assert response.headers["cache-control"] == "no-store"


def test_unauthenticated_mutation_returns_401_before_csrf_error(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, _, _ = api
    client.app.dependency_overrides.clear()

    response = client.delete("/api/records")

    assert response.status_code == 401
    assert response.json()["code"] == "HTTP_ERROR"


def test_login_is_unavailable_without_provider_configuration() -> None:
    from fastapi.testclient import TestClient

    from src.app.config import Settings
    from src.app.main import create_app

    app = create_app(Settings(_env_file=None, session_secret_key=None))

    response = TestClient(app).get("/auth/login")

    assert response.status_code == 503
    assert response.json()["code"] == "HTTP_ERROR"
