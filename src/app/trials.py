from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.agents.service import TrialModelError, run_trial
from src.app.auth import get_current_user_with_csrf
from src.app.config import Settings
from src.app.models import AppUser
from src.app.rate_limit import InMemoryRateLimiter, client_ip
from src.app.safety import HELPLINES, contains_crisis_signal
from src.app.schemas import TrialInput

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["trial"])


def _event(name: str, data: dict[str, Any]) -> str:
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {serialized}\n\n"


def _error(
    code: str,
    message: str,
    retryable: bool,
    *,
    request_id: str,
) -> str:
    logger.warning("trial request failed request_id=%s code=%s", request_id, code)
    return _event("error", {"code": code, "message": message, "retryable": retryable})


@router.post("/trial")
async def trial(
    body: TrialInput,
    request: Request,
    user: AppUser = Depends(get_current_user_with_csrf),
) -> StreamingResponse:
    if contains_crisis_signal(body.case):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "CRISIS_SIGNAL",
                "message": "지금은 재판보다 도움이 먼저입니다. 아래 상담 전화로 바로 연락해 주세요.",
                "retryable": False,
                "helplines": HELPLINES,
            },
        )

    settings: Settings = request.app.state.settings
    limiter: InMemoryRateLimiter = request.app.state.rate_limiter
    address = client_ip(request, settings.trusted_proxy_ips)
    limiter.check_and_record(settings, address, str(user.id))

    request_id = str(uuid.uuid4())

    async def stream() -> AsyncIterator[str]:
        try:
            async with asyncio.timeout(settings.trial_timeout_seconds):
                async for name, data in run_trial(settings, body.case, body.deadline):
                    yield _event(name, data)
        except TrialModelError as error:
            yield _error(
                error.code, error.message, error.retryable, request_id=request_id
            )
        except TimeoutError:
            yield _error(
                "TIMEOUT",
                "재판이 너무 오래 걸려 중단했습니다. 다시 시도해 주세요.",
                True,
                request_id=request_id,
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
