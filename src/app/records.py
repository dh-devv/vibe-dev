import base64
import binascii
import json
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Query, Request, Response

from src.app.auth import owner_id
from src.app.db import get_pool
from src.app.errors import ApiError
from src.app.schemas import ChecksUpdate, RecordCreate

router = APIRouter(prefix="/api")

_COLUMNS = "id, case_text, deadline, verdict, checks, submitted_at, accepted_at, first_checked_at, completed_at"
def _not_found() -> ApiError:
    return ApiError(404, "NOT_FOUND", "기록을 찾을 수 없습니다.", False)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _record(row: asyncpg.Record) -> dict[str, Any]:
    deadline: date | None = row["deadline"]
    return {
        "id": str(row["id"]),
        "case": row["case_text"],
        "deadline": deadline.isoformat() if deadline else None,
        "verdict": json.loads(row["verdict"]),
        "checks": json.loads(row["checks"]),
        "submittedAt": _iso(row["submitted_at"]),
        "acceptedAt": _iso(row["accepted_at"]),
        "firstCheckedAt": _iso(row["first_checked_at"]),
        "completedAt": _iso(row["completed_at"]),
    }


def _encode_cursor(accepted_at: datetime, record_id: UUID) -> str:
    raw = json.dumps({"a": accepted_at.isoformat(), "i": str(record_id)})
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        accepted_at = datetime.fromisoformat(data["a"])
        if accepted_at.tzinfo is None:
            raise ValueError("시간대가 없다")
        return accepted_at, UUID(data["i"])
    except (binascii.Error, ValueError, KeyError, TypeError) as exc:
        raise ApiError(422, "INVALID_INPUT", "cursor 값이 올바르지 않습니다.", False) from exc


@router.post("/records", status_code=201)
async def create_record(request: Request, body: RecordCreate, owner: UUID = Depends(owner_id)) -> dict[str, Any]:
    accepted_at = datetime.now(UTC)
    if body.submitted_at > accepted_at:
        raise ApiError(422, "INVALID_INPUT", "재판 접수 시각이 올바르지 않습니다.", False)
    verdict = body.verdict.model_dump(exclude={"evidence"})
    checks = [[False] * len(p["steps"]) for p in verdict["prescriptions"]]
    deadline = date.fromisoformat(body.deadline) if body.deadline else None
    pool = await get_pool(request)
    row = await pool.fetchrow(
        f"""
        INSERT INTO trials (owner_id, case_text, deadline, verdict, checks, submitted_at, accepted_at)
        VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7)
        RETURNING {_COLUMNS}
        """,
        owner,
        body.case,
        deadline,
        json.dumps(verdict, ensure_ascii=False),
        json.dumps(checks),
        body.submitted_at,
        accepted_at,
    )
    return _record(row)


@router.get("/records")
async def list_records(
    request: Request,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = None,
    owner: UUID = Depends(owner_id),
) -> dict[str, Any]:
    after_at, after_id = _decode_cursor(cursor) if cursor else (None, None)
    pool = await get_pool(request)
    rows = await pool.fetch(
        f"""
        SELECT {_COLUMNS} FROM trials
        WHERE owner_id = $1
          AND ($2::timestamptz IS NULL OR (accepted_at, id) < ($2::timestamptz, $3::uuid))
        ORDER BY accepted_at DESC, id DESC
        LIMIT $4
        """,
        owner,
        after_at,
        after_id,
        limit + 1,
    )
    page = rows[:limit]
    next_cursor = _encode_cursor(page[-1]["accepted_at"], page[-1]["id"]) if len(rows) > limit else None
    return {"items": [_record(r) for r in page], "nextCursor": next_cursor}


@router.get("/records/{record_id}")
async def get_record(request: Request, record_id: UUID, owner: UUID = Depends(owner_id)) -> dict[str, Any]:
    pool = await get_pool(request)
    row = await pool.fetchrow(
        f"SELECT {_COLUMNS} FROM trials WHERE id = $1 AND owner_id = $2", record_id, owner
    )
    if row is None:
        raise _not_found()
    return _record(row)


@router.patch("/records/{record_id}")
async def update_checks(
    request: Request, record_id: UUID, body: ChecksUpdate, owner: UUID = Depends(owner_id)
) -> dict[str, Any]:
    pool = await get_pool(request)
    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            f"SELECT {_COLUMNS} FROM trials WHERE id = $1 AND owner_id = $2 FOR UPDATE", record_id, owner
        )
        if row is None:
            raise _not_found()
        shape = [len(p["steps"]) for p in json.loads(row["verdict"])["prescriptions"]]
        if [len(c) for c in body.checks] != shape:
            raise ApiError(422, "INVALID_INPUT", "체크 목록이 처방의 단계 수와 맞지 않습니다.", False)

        now = datetime.now(UTC)
        any_checked = any(any(c) for c in body.checks)
        all_checked = all(all(c) for c in body.checks)
        first_checked = row["first_checked_at"] or (now if any_checked else None)
        completed = (row["completed_at"] or now) if all_checked else None
        updated = await conn.fetchrow(
            f"""
            UPDATE trials
            SET checks = $3::jsonb, first_checked_at = $4, completed_at = $5
            WHERE id = $1 AND owner_id = $2
            RETURNING {_COLUMNS}
            """,
            record_id,
            owner,
            json.dumps(body.checks),
            first_checked,
            completed,
        )
    return _record(updated)


@router.delete("/records/{record_id}", status_code=204)
async def delete_record(request: Request, record_id: UUID, owner: UUID = Depends(owner_id)) -> Response:
    pool = await get_pool(request)
    deleted = await pool.fetchval(
        "DELETE FROM trials WHERE id = $1 AND owner_id = $2 RETURNING id", record_id, owner
    )
    if deleted is None:
        raise _not_found()
    return Response(status_code=204)


@router.delete("/records", status_code=204)
async def delete_all_records(request: Request, owner: UUID = Depends(owner_id)) -> Response:
    pool = await get_pool(request)
    await pool.execute("DELETE FROM trials WHERE owner_id = $1", owner)
    return Response(status_code=204)


@router.delete("/account", status_code=204)
async def delete_account(request: Request, owner: UUID = Depends(owner_id)) -> Response:
    pool = await get_pool(request)
    await pool.execute("DELETE FROM app_users WHERE id = $1", owner)
    return Response(status_code=204)
