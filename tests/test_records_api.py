from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.app.models import AppUser


def _record_payload() -> dict[str, object]:
    return {
        "case": "보고서를 이번 주 안에 작성해야 한다.",
        "deadline": None,
        "submittedAt": datetime.now(timezone.utc).isoformat(),
        "verdict": {
            "summary": "첫 단계를 작게 나누는 편이 좋습니다.",
            "cause": "막막함",
            "prescriptions": [
                {
                    "title": "목차 만들기",
                    "steps": ["제목을 적는다", "소제목 세 개를 쓴다"],
                    "minutes": 15,
                    "reason": "시작 부담을 줄입니다.",
                }
            ],
        },
    }


def test_record_acceptance_and_execution(
    api: tuple[TestClient, AppUser, AppUser]
) -> None:
    client, _, _ = api
    created = client.post(
        "/api/records",
        json=_record_payload(),
        headers={"X-CSRF-Token": "test-csrf-token"},
    )
    assert created.status_code == 201
    record = created.json()
    assert record["checks"] == [[False, False]]
    assert "evidence" not in record["verdict"]

    later_step_first = client.patch(
        f"/api/records/{record['id']}",
        json={"checks": [[False, True]]},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )
    assert later_step_first.status_code == 200
    assert later_step_first.json()["firstCheckedAt"] is None

    first_check = client.patch(
        f"/api/records/{record['id']}",
        json={"checks": [[True, False]]},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )
    assert first_check.status_code == 200
    assert first_check.json()["firstCheckedAt"] is not None
    assert first_check.json()["completedAt"] is None

    completed = client.patch(
        f"/api/records/{record['id']}",
        json={"checks": [[True, True]]},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )
    assert completed.status_code == 200
    assert completed.json()["completedAt"] is not None

    completion_time = completed.json()["completedAt"]
    repeated = client.patch(
        f"/api/records/{record['id']}",
        json={"checks": [[True, True]]},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )
    assert repeated.json()["completedAt"] == completion_time

    unchecked = client.patch(
        f"/api/records/{record['id']}",
        json={"checks": [[False, False]]},
        headers={"X-CSRF-Token": "test-csrf-token"},
    )
    assert unchecked.json()["completedAt"] is None
    assert unchecked.json()["firstCheckedAt"] == first_check.json()["firstCheckedAt"]

    listing = client.get("/api/records")
    assert listing.status_code == 200
    assert listing.json()["items"][0]["id"] == record["id"]


def test_records_are_scoped_to_the_authenticated_owner(
    api: tuple[TestClient, AppUser, AppUser],
) -> None:
    client, owner_a, owner_b = api
    created = client.post(
        "/api/records",
        json=_record_payload(),
        headers={"X-CSRF-Token": "test-csrf-token"},
    )
    record_id = created.json()["id"]
    client.app.dependency_overrides.clear()

    async def owner_b_user() -> AppUser:
        return owner_b

    from src.app.auth import get_current_user

    client.app.dependency_overrides[get_current_user] = owner_b_user
    assert client.get(f"/api/records/{record_id}").status_code == 404
    assert (
        client.patch(
            f"/api/records/{record_id}",
            json={"checks": [[True, True]]},
            headers={"X-CSRF-Token": "test-csrf-token"},
        ).status_code
        == 404
    )
    assert (
        client.delete(
            f"/api/records/{record_id}",
            headers={"X-CSRF-Token": "test-csrf-token"},
        ).status_code
        == 404
    )

    async def owner_a_user() -> AppUser:
        return owner_a

    client.app.dependency_overrides[get_current_user] = owner_a_user
    assert client.get(f"/api/records/{record_id}").status_code == 200


def test_invalid_csrf_is_rejected(api: tuple[TestClient, AppUser, AppUser]) -> None:
    client, _, _ = api
    response = client.post("/api/records", json=_record_payload())
    assert response.status_code == 403
    assert response.json()["code"] == "HTTP_ERROR"
