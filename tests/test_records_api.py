<<<<<<< HEAD
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
=======
﻿import json
import os
import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.app.auth import Owner, current_owner
from src.app.config import Settings
from src.app.main import app
from tests.conftest import VALID_VERDICT

DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or "postgresql://{}:{}@127.0.0.1:5432/vibe_dev?sslmode=disable".format(
    "vibe_dev", "local-dev-only"
)


def _db_reachable() -> bool:
    import asyncio

    import asyncpg

    async def probe() -> bool:
        try:
            conn = await asyncpg.connect(DATABASE_URL, timeout=5)
            exists = await conn.fetchval("SELECT to_regclass('public.trials') IS NOT NULL")
            await conn.close()
            return bool(exists)
        except (OSError, asyncpg.PostgresError):
            return False

    return asyncio.run(probe())


pytestmark = pytest.mark.skipif(not _db_reachable(), reason="PostgreSQL(스키마 적용)에 연결할 수 없음")

STORED = {k: v for k, v in VALID_VERDICT.items() if k != "evidence"}


def record_body(**overrides) -> dict:
    submitted = (datetime.now(UTC) - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    return {"case": "보고서를 3일째 못 쓰고 있다.", "deadline": None, "submittedAt": submitted, "verdict": STORED, **overrides}


@pytest.fixture
def make_client() -> Iterator:
    app.state.settings = Settings(_env_file=None, database_url=DATABASE_URL)
    created: list[Owner] = []
    with TestClient(app) as client:

        def for_owner(label: str) -> TestClient:
            owner = Owner(f"test-{uuid.uuid4()}", label)
            created.append(owner)
            return _OwnerClient(client, owner)

        yield for_owner
        for owner in created:
            app.dependency_overrides[current_owner] = lambda o=owner: o
            client.delete("/api/account")
        app.dependency_overrides.clear()


class _OwnerClient:
    """요청마다 지정한 소유자로 인증된 것처럼 호출한다."""

    def __init__(self, client: TestClient, owner: Owner) -> None:
        self._client, self._owner = client, owner

    def request(self, method: str, url: str, **kwargs):
        app.dependency_overrides[current_owner] = lambda: self._owner
        return self._client.request(method, url, **kwargs)

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def patch(self, url, **kw):
        return self.request("PATCH", url, **kw)

    def delete(self, url, **kw):
        return self.request("DELETE", url, **kw)


def test_create_and_get_record(make_client) -> None:
    alice = make_client("alice")

    created = alice.post("/api/records", json=record_body(deadline="2026-11-07"))

    assert created.status_code == 201
    body = created.json()
    assert body["case"] == "보고서를 3일째 못 쓰고 있다."
    assert body["deadline"] == "2026-11-07"
    assert body["verdict"] == STORED
    assert body["checks"] == [[False, False]]
    assert body["acceptedAt"].endswith("Z") and body["firstCheckedAt"] is None
    assert alice.get(f"/api/records/{body['id']}").json() == body


def test_evidence_is_validated_but_not_stored(make_client) -> None:
    alice = make_client("alice")

    ok = alice.post("/api/records", json=record_body(verdict=VALID_VERDICT))
    bad = alice.post("/api/records", json=record_body(verdict={**VALID_VERDICT, "evidence": [1, 1]}))

    assert "evidence" not in ok.json()["verdict"]
    assert bad.status_code == 422


@pytest.mark.parametrize(
    "overrides",
    [
        {"case": "짧음"},
        {"submittedAt": "2999-01-01T00:00:00Z"},
        {"submittedAt": "2026-11-05T14:30:00"},
        {"verdict": {**STORED, "cause": "게으름"}},
        {"verdict": {**STORED, "prescriptions": []}},
        {"verdict": {**STORED, "prescriptions": [{**STORED["prescriptions"][0], "minutes": 3}]}},
    ],
)
def test_invalid_record_rejected(make_client, overrides) -> None:
    response = make_client("alice").post("/api/records", json=record_body(**overrides))

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_owner_isolation_returns_404(make_client) -> None:
    alice, bob = make_client("alice"), make_client("bob")
    record_id = alice.post("/api/records", json=record_body()).json()["id"]

    assert bob.get(f"/api/records/{record_id}").status_code == 404
    assert bob.patch(f"/api/records/{record_id}", json={"checks": [[True, True]]}).status_code == 404
    assert bob.delete(f"/api/records/{record_id}").status_code == 404
    assert bob.get("/api/records").json()["items"] == []
    assert alice.get(f"/api/records/{record_id}").status_code == 200


def test_client_supplied_owner_is_ignored(make_client) -> None:
    alice, bob = make_client("alice"), make_client("bob")
    forged = alice.post("/api/records", json={**record_body(), "owner_id": str(uuid.uuid4())}).json()

    assert bob.get(f"/api/records/{forged['id']}").status_code == 404
    assert alice.get(f"/api/records/{forged['id']}").status_code == 200


def test_update_checks_tracks_progress(make_client) -> None:
    alice = make_client("alice")
    record_id = alice.post("/api/records", json=record_body()).json()["id"]

    first = alice.patch(f"/api/records/{record_id}", json={"checks": [[True, False]]}).json()
    assert first["firstCheckedAt"] is not None and first["completedAt"] is None

    done = alice.patch(f"/api/records/{record_id}", json={"checks": [[True, True]]}).json()
    assert done["completedAt"] is not None and done["firstCheckedAt"] == first["firstCheckedAt"]

    reset = alice.patch(f"/api/records/{record_id}", json={"checks": [[False, False]]}).json()
    assert reset["completedAt"] is None and reset["firstCheckedAt"] == first["firstCheckedAt"]


@pytest.mark.parametrize("checks", [[[True]], [[True, True], [True]], [[1, 0]], [["a", "b"]], "x"])
def test_update_checks_shape_validated(make_client, checks) -> None:
    alice = make_client("alice")
    record_id = alice.post("/api/records", json=record_body()).json()["id"]

    response = alice.patch(f"/api/records/{record_id}", json={"checks": checks})

    assert response.status_code == 422


def test_list_pagination_newest_first(make_client) -> None:
    alice = make_client("alice")
    ids = [alice.post("/api/records", json=record_body(case=f"사건 번호 {i} 입니다")).json()["id"] for i in range(3)]

    page1 = alice.get("/api/records", params={"limit": 2}).json()
    page2 = alice.get("/api/records", params={"limit": 2, "cursor": page1["nextCursor"]}).json()

    assert [r["id"] for r in page1["items"]] == [ids[2], ids[1]]
    assert [r["id"] for r in page2["items"]] == [ids[0]]
    assert page2["nextCursor"] is None


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 51}, {"cursor": "!!!"}])
def test_list_rejects_bad_params(make_client, params) -> None:
    assert make_client("alice").get("/api/records", params=params).status_code == 422


def test_delete_one_all_and_account(make_client) -> None:
    alice, bob = make_client("alice"), make_client("bob")
    first = alice.post("/api/records", json=record_body()).json()["id"]
    alice.post("/api/records", json=record_body())
    bob_record = bob.post("/api/records", json=record_body()).json()["id"]

    assert alice.delete(f"/api/records/{first}").status_code == 204
    assert alice.delete(f"/api/records/{first}").status_code == 404
    assert alice.delete("/api/records").status_code == 204
    assert alice.get("/api/records").json()["items"] == []
    assert bob.get(f"/api/records/{bob_record}").status_code == 200

    assert bob.delete("/api/account").status_code == 204
    assert bob.get("/api/records").json()["items"] == []


def test_records_require_auth() -> None:
    app.state.settings = Settings(_env_file=None, database_url=DATABASE_URL)
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        assert client.get("/api/records").status_code == 401
        assert client.delete("/api/account").status_code == 401
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
