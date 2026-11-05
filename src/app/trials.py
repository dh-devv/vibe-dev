from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.agents.trial import run_trial
from src.app.auth import get_current_user_with_csrf
from src.app.config import Settings
from src.app.models import AppUser
from src.app.rate_limit import InMemoryRateLimiter, client_ip
from src.app.safety import HELPLINES, contains_crisis_signal
from src.app.schemas import TrialInput

router = APIRouter(prefix="/api", tags=["trial"])


def _event(name: str, data: dict[str, Any]) -> str:
    serialized = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {name}\ndata: {serialized}\n\n"


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

    async def stream() -> AsyncIterator[str]:
        async for name, data in run_trial(
            request.app.state.trial_model,
            body.case,
            body.deadline.isoformat() if body.deadline else None,
            datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            settings.model_timeout_seconds,
            settings.trial_timeout_seconds,
        ):
            yield _event(name, data)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
