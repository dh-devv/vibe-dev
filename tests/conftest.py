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
