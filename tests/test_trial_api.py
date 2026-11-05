from collections.abc import AsyncIterator
from datetime import date
from typing import Any

from fastapi.testclient import TestClient

from src.app.models import AppUser


def test_crisis_signal_is_rejected_before_stream(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, _, _ = api
    response = client.post(
        "/api/trial",
        json={"case": "요즘 죽고 싶다는 생각이 든다"},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CRISIS_SIGNAL"
    assert len(response.json()["helplines"]) == 3


def test_trial_rate_limit_and_sse_format(
    api: tuple[TestClient, AppUser, AppUser],
    monkeypatch: Any,
) -> None:
    import src.app.trials as trials_module

    async def fake_trial(
        settings: Any, case: str, deadline: date | None
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        yield "trial_started", {"submittedAt": "2026-11-05T00:00:00Z"}
        yield "done", {}

    monkeypatch.setattr(trials_module, "run_trial", fake_trial)
    client, _, _ = api
    client.app.state.settings.ip_per_minute = 1
    client.app.state.settings.user_per_minute = 1
    payload = {"case": "보고서를 작성해야 한다."}

    headers = {"X-CSRF-Token": "test-csrf-token"}
    first = client.post("/api/trial", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.headers["content-type"].startswith("text/event-stream")
    assert "event: trial_started" in first.text
    assert "event: done" in first.text

    second = client.post("/api/trial", json=payload, headers=headers)
    assert second.status_code == 429
    assert second.json()["code"] == "RATE_LIMITED"
    assert "retry-after" in second.headers


def test_missing_model_configuration_returns_sse_error(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, _, _ = api
    response = client.post(
        "/api/trial",
        json={"case": "보고서를 작성해야 한다."},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )

    assert response.status_code == 200
    assert "event: error" in response.text
    assert '"code":"MODEL_ERROR"' in response.text
    assert "event: done" not in response.text
