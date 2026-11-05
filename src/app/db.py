import logging
from uuid import UUID

import asyncpg
from fastapi import Request

from src.app.errors import ApiError

logger = logging.getLogger(__name__)


async def create_pool(dsn: str) -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn, min_size=1, max_size=5, command_timeout=10)


async def get_pool(request: Request) -> asyncpg.Pool:
    state = request.app.state
    if state.pool is not None:
        return state.pool
    dsn = state.settings.database_url
    if not dsn:
        raise ApiError(503, "DB_UNAVAILABLE", "저장소를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.", True)
    try:
        pool = await create_pool(dsn)
    except (OSError, asyncpg.PostgresError) as exc:
        logger.error("db_connect_failed type=%s", type(exc).__name__)
        raise ApiError(503, "DB_UNAVAILABLE", "저장소를 사용할 수 없습니다. 잠시 후 다시 시도해 주세요.", True) from exc
    if state.pool is not None:
        await pool.close()
        return state.pool
    state.pool = pool
    return pool


async def ensure_user(pool: asyncpg.Pool, issuer: str, subject: str) -> UUID:
    return await pool.fetchval(
        """
        INSERT INTO app_users (oidc_issuer, oidc_subject)
        VALUES ($1, $2)
        ON CONFLICT (oidc_issuer, oidc_subject)
        DO UPDATE SET oidc_subject = EXCLUDED.oidc_subject
        RETURNING id
        """,
        issuer,
        subject,
    )
