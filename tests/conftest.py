<<<<<<< HEAD
from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.app.auth import get_current_user
from src.app.config import Settings
from src.app.main import create_app
from src.app.models import AppUser, Base


@pytest.fixture
def api() -> Iterator[tuple[TestClient, AppUser, AppUser]]:
    import tempfile
    from pathlib import Path

    directory = tempfile.TemporaryDirectory()
    database_path = Path(directory.name) / "test.db"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    engine = create_async_engine(database_url)

    async def create_database() -> tuple[AppUser, AppUser]:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            first = AppUser(oidc_issuer="https://issuer.example", oidc_subject="user-a")
            second = AppUser(
                oidc_issuer="https://issuer.example", oidc_subject="user-b"
            )
            session.add_all((first, second))
            await session.commit()
            return first, second

    first_user, second_user = asyncio.run(create_database())
    config = Settings(
        _env_file=None,
        database_url=database_url,
        oidc_issuer="https://issuer.example",
        oidc_client_id="test-client",
        session_secret_key="test-session-secret-that-is-long-enough",
        public_base_url="http://testserver",
        cookie_secure=False,
    )
    app = create_app(config)
    active_user = {"user": first_user}

    async def current_user() -> AppUser:
        return active_user["user"]

    app.dependency_overrides[get_current_user] = current_user
    with TestClient(app) as client:
        client.cookies.set("vibe_csrf", "test-csrf-token")
        yield client, first_user, second_user
    asyncio.run(engine.dispose())
    directory.cleanup()
=======
import json
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient

from src.app.config import Settings
from src.app.limits import RateLimiter
from src.app.main import app

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
    def __init__(self, judge_outputs: list[str] | None = None, fail_role: str | None = None) -> None:
        self.judge_outputs = list(judge_outputs or [json.dumps(VALID_VERDICT, ensure_ascii=False)])
        self.fail_role = fail_role
        self.calls: list[tuple[str, str]] = []

    async def run(self, role: str, prompt: str) -> AsyncIterator[str]:
        self.calls.append((role, prompt))
        if role == self.fail_role:
            raise RuntimeError("모델 오류")
        if role == "judge":
            yield self.judge_outputs.pop(0)
            return
        yield f"{role} 발언 "
        yield "끝"

    async def close(self) -> None:
        return None


@pytest.fixture
def fake_model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def client(fake_model: FakeModel) -> Iterator[TestClient]:
    settings = Settings(_env_file=None, dev_auth_enabled=True)
    app.state.settings = settings
    app.state.trial_model = fake_model
    app.state.limiter = RateLimiter(
        settings.ip_per_minute,
        settings.ip_per_day,
        settings.user_per_minute,
        settings.user_per_day,
        settings.global_per_day,
    )
    with TestClient(app) as test_client:
        yield test_client


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        name, data = "", ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        events.append((name, json.loads(data)))
    return events
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
