import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.agents.trial import run_trial
from src.app.auth import Owner, current_owner
from src.app.errors import ApiError
from src.app.safety import CRISIS_MESSAGE, HELPLINES, has_crisis_signal
from src.app.schemas import TrialRequest

router = APIRouter(prefix="/api")

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
_LIMIT_MESSAGES = {
    "RATE_LIMITED": "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.",
    "DAILY_LIMIT": "오늘 법정이 만석입니다. 내일 다시 이용해 주세요.",
}


def client_ip(request: Request, trusted_hops: int) -> str:
    """신뢰하도록 설정한 프록시 수(trusted_hops)만큼만 X-Forwarded-For를 믿는다."""
    direct = request.client.host if request.client else "unknown"
    if trusted_hops <= 0:
        return direct
    parts = [p.strip() for p in request.headers.get("x-forwarded-for", "").split(",") if p.strip()]
    return parts[-trusted_hops] if len(parts) >= trusted_hops else direct


def _sse(name: str, data: dict) -> str:
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/trial")
async def start_trial(request: Request, body: TrialRequest, owner: Owner = Depends(current_owner)) -> StreamingResponse:
    state = request.app.state
    settings = state.settings
    if has_crisis_signal(body.case):
        raise ApiError(422, "CRISIS_SIGNAL", CRISIS_MESSAGE, False, extra={"helplines": HELPLINES})
    denied = state.limiter.acquire(client_ip(request, settings.trusted_proxy_hops), owner.key)
    if denied is not None:
        raise ApiError(
            429,
            denied.code,
            _LIMIT_MESSAGES[denied.code],
            denied.code == "RATE_LIMITED",
            headers={"Retry-After": str(denied.retry_after)},
        )

    submitted_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    async def events() -> AsyncIterator[str]:
        async for name, data in run_trial(
            state.trial_model,
            body.case,
            body.deadline,
            submitted_at,
            settings.model_timeout_seconds,
            settings.trial_timeout_seconds,
        ):
            yield _sse(name, data)

    return StreamingResponse(events(), media_type="text/event-stream", headers=SSE_HEADERS)
