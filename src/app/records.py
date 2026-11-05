from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.auth import get_current_user, get_current_user_with_csrf
from src.app.database import get_db
from src.app.models import AppUser, Trial
from src.app.schemas import ChecksInput, CreateRecordInput, RecordOut

router = APIRouter(prefix="/api/records", tags=["records"])


def _to_record(trial: Trial) -> RecordOut:
    return RecordOut(
        id=trial.id,
        case=trial.case_text,
        deadline=trial.deadline,
        verdict=trial.verdict,
        checks=trial.checks,
        submittedAt=trial.submitted_at,
        acceptedAt=trial.accepted_at,
        firstCheckedAt=trial.first_checked_at,
        completedAt=trial.completed_at,
    )


def _encode_cursor(trial: Trial) -> str:
    accepted_at = trial.accepted_at
    if accepted_at.tzinfo is None:
        accepted_at = accepted_at.replace(tzinfo=timezone.utc)
    value = f"{accepted_at.isoformat()}|{trial.id}"
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        decoded = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)).decode(
            "utf-8"
        )
        timestamp, record_id = decoded.rsplit("|", 1)
        accepted_at = datetime.fromisoformat(timestamp)
        if accepted_at.tzinfo is None:
            raise ValueError
        return accepted_at, UUID(record_id)
    except (ValueError, UnicodeDecodeError, binascii.Error):
        raise HTTPException(status_code=422, detail="페이지 커서가 올바르지 않습니다.") from None


@router.post(
    "",
    response_model=RecordOut,
    status_code=201,
)
async def create_record(
    body: CreateRecordInput,
    user: AppUser = Depends(get_current_user_with_csrf),
    session: AsyncSession = Depends(get_db),
) -> RecordOut:
    accepted_at = datetime.now(timezone.utc)
    verdict = body.verdict.model_dump(mode="json")
    trial = Trial(
        owner_id=user.id,
        case_text=body.case,
        deadline=body.deadline,
        verdict=verdict,
        checks=[
            [False for _ in prescription.steps]
            for prescription in body.verdict.prescriptions
        ],
        submitted_at=body.submitted_at,
        accepted_at=accepted_at,
    )
    session.add(trial)
    await session.commit()
    await session.refresh(trial)
    return _to_record(trial)


@router.get("", response_model=dict[str, object])
async def list_records(
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = None,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict[str, object]:
    statement = select(Trial).where(Trial.owner_id == user.id)
    if cursor:
        accepted_at, record_id = _decode_cursor(cursor)
        statement = statement.where(
            or_(
                Trial.accepted_at < accepted_at,
                and_(Trial.accepted_at == accepted_at, Trial.id < record_id),
            )
        )
    statement = statement.order_by(Trial.accepted_at.desc(), Trial.id.desc()).limit(
        limit + 1
    )
    trials = list((await session.execute(statement)).scalars())
    has_more = len(trials) > limit
    page = trials[:limit]
    return {
        "items": [_to_record(trial) for trial in page],
        "nextCursor": _encode_cursor(page[-1]) if has_more and page else None,
    }


async def _owned_trial(record_id: UUID, user_id: UUID, session: AsyncSession) -> Trial:
    result = await session.execute(
        select(Trial).where(Trial.id == record_id, Trial.owner_id == user_id)
    )
    trial = result.scalar_one_or_none()
    if trial is None:
        raise HTTPException(status_code=404, detail="기록을 찾을 수 없습니다.")
    return trial


@router.get("/{record_id}", response_model=RecordOut)
async def get_record(
    record_id: UUID,
    user: AppUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RecordOut:
    return _to_record(await _owned_trial(record_id, user.id, session))


@router.patch(
    "/{record_id}",
    response_model=RecordOut,
)
async def update_checks(
    record_id: UUID,
    body: ChecksInput,
    user: AppUser = Depends(get_current_user_with_csrf),
    session: AsyncSession = Depends(get_db),
) -> RecordOut:
    trial = await _owned_trial(record_id, user.id, session)
    expected = [len(item["steps"]) for item in trial.verdict["prescriptions"]]
    if len(body.checks) != len(expected) or any(
        len(checks) != step_count
        for checks, step_count in zip(body.checks, expected, strict=True)
    ):
        raise HTTPException(status_code=422, detail="체크 항목의 구성이 판결 처방과 다릅니다.")

    now = datetime.now(timezone.utc)
    first_step_checked = bool(body.checks[0][0])
    all_checked = all(all(group) for group in body.checks)
    trial.checks = body.checks
    if first_step_checked and trial.first_checked_at is None:
        trial.first_checked_at = now
    if all_checked and trial.completed_at is None:
        trial.completed_at = now
    elif not all_checked:
        trial.completed_at = None
    trial.updated_at = now
    await session.commit()
    await session.refresh(trial)
    return _to_record(trial)


@router.delete("/{record_id}", status_code=204)
async def delete_record(
    record_id: UUID,
    user: AppUser = Depends(get_current_user_with_csrf),
    session: AsyncSession = Depends(get_db),
) -> Response:
    trial = await _owned_trial(record_id, user.id, session)
    await session.delete(trial)
    await session.commit()
    return Response(status_code=204)


@router.delete("", status_code=204)
async def delete_records(
    user: AppUser = Depends(get_current_user_with_csrf),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await session.execute(delete(Trial).where(Trial.owner_id == user.id))
    await session.commit()
    return Response(status_code=204)
