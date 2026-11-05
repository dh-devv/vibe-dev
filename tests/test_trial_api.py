import json
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from src.app.models import AppUser

VALID_VERDICT = {
    "summary": "막막함은 받아들이고 마감 압박은 일부만 받아들입니다.",
    "cause": "막막함",
    "prescriptions": [
        {
            "title": "목차부터 만들기",
            "steps": ["보고서 제목을 쓴다", "소제목 3개를 적는다"],
            "minutes": 15,
            "reason": "시작 부담을 줄입니다.",
        }
    ],
    "evidence": [1, 2],
}


class FakeModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def run(self, role: str, _prompt: str) -> AsyncIterator[str]:
        self.prompts.append(_prompt)
        if role == "judge":
            yield json.dumps(VALID_VERDICT, ensure_ascii=False)
        else:
            yield f"{role} 발언입니다."

    async def close(self) -> None:
        return None


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


def test_crisis_signal_in_reason_is_rejected_before_stream(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, _, _ = api
    response = client.post(
        "/api/trial",
        json={"case": "보고서를 작성해야 한다.", "reason": "죽고 싶다는 생각이 든다"},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "CRISIS_SIGNAL"


def test_trial_rate_limit_and_sse_format(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, _, _ = api
    model = FakeModel()
    client.app.state.trial_model = model
    client.app.state.settings.ip_per_minute = 1
    client.app.state.settings.user_per_minute = 1
    payload = {"case": "보고서를 작성해야 한다.", "reason": "무엇부터 할지 막막하다."}

    headers = {"X-CSRF-Token": "test-csrf-token"}
    first = client.post("/api/trial", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.headers["content-type"].startswith("text/event-stream")
    assert "event: trial_started" in first.text
    assert "event: done" in first.text
    assert "미룬 이유: 무엇부터 할지 막막하다." in model.prompts[0]

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
    assert '"code":"MODEL_NOT_CONFIGURED"' in response.text
    assert "event: done" not in response.text
