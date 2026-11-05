import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any

from src.agents.model import Role, TrialModel
from src.app.schemas import VerdictError, parse_verdict

logger = logging.getLogger(__name__)

MAX_STATEMENT_CHARS = 250
STEPS: tuple[tuple[int, Role, str], ...] = (
    (1, "defense", "defense"),
    (2, "prosecution", "prosecution"),
    (3, "defense", "rebuttal"),
)
SPEAKER = {"defense": "변호인", "prosecution": "검사"}

FAILURES: dict[str, tuple[str, bool]] = {
    "MODEL_ERROR": ("법정에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.", True),
    "TIMEOUT": ("재판이 너무 오래 걸려 중단했습니다. 다시 시도해 주세요.", True),
    "VERDICT_INVALID": ("판결문을 만들지 못했습니다. 다시 시도해 주세요.", True),
    "INTERNAL": ("알 수 없는 오류가 발생했습니다.", False),
}

Event = tuple[str, dict[str, Any]]


class TrialFailure(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _escape(text: str) -> str:
    # 사용자 입력이 <case> 태그를 닫지 못하게 한다
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _case_block(case: str, deadline: str | None) -> str:
    return f"<case>{_escape(case)}</case>\n<deadline>{deadline or '없음'}</deadline>"


def _transcript(statements: list[tuple[int, str, str]]) -> str:
    return "\n".join(f"[{n}] {SPEAKER[role]}: {_escape(text)}" for n, role, text in statements)


def _step_prompt(stage: str, case: str, deadline: str | None, statements: list[tuple[int, str, str]]) -> str:
    instruction = {
        "defense": "변호인으로서 첫 변론을 하라.",
        "prosecution": "검사로서 변호인의 발언을 반박하라.",
        "rebuttal": "변호인으로서 검사의 발언에 재반박하라.",
    }[stage]
    parts = [_case_block(case, deadline)]
    if statements:
        parts.append(_transcript(statements))
    parts.append(instruction)
    return "\n\n".join(parts)


def _judge_prompt(case: str, deadline: str | None, statements: list[tuple[int, str, str]], reason: str | None) -> str:
    parts = [_case_block(case, deadline), _transcript(statements), "위 발언을 읽고 판결 JSON을 출력하라."]
    if reason:
        parts.append(f"이전 출력이 검증에서 반려되었다. 사유: {reason}\n형식 규칙을 지켜 JSON만 다시 출력하라.")
    return "\n\n".join(parts)


async def _bounded(stream: AsyncIterator[str], overall_deadline: float, call_timeout: float) -> AsyncIterator[str]:
    """모델 호출 1회(call_timeout)와 재판 전체(overall_deadline) 시간을 모두 지킨다."""
    loop = asyncio.get_running_loop()
    limit = min(overall_deadline, loop.time() + call_timeout)
    iterator = stream.__aiter__()
    try:
        while True:
            remaining = limit - loop.time()
            if remaining <= 0:
                raise TimeoutError
            try:
                chunk = await asyncio.wait_for(iterator.__anext__(), remaining)
            except StopAsyncIteration:
                return
            yield chunk
    finally:
        close = getattr(iterator, "aclose", None)
        if close is not None:
            await close()


async def run_trial(
    model: TrialModel,
    case: str,
    deadline: str | None,
    submitted_at: str,
    model_timeout: float,
    trial_timeout: float,
) -> AsyncIterator[Event]:
    """변호인 → 검사 → 변호인 → 판사 → 검증기 순서를 코드가 정한다. 상태는 이 함수 안에서만 쓴다."""
    overall_deadline = asyncio.get_running_loop().time() + trial_timeout
    yield "trial_started", {"submittedAt": submitted_at}
    statements: list[tuple[int, str, str]] = []
    try:
        for n, role, stage in STEPS:
            yield "stage", {"stage": stage, "n": n}
            text = ""
            prompt = _step_prompt(stage, case, deadline, statements)
            async with aclosing(_bounded(model.run(role, prompt), overall_deadline, model_timeout)) as chunks:
                async for delta in chunks:
                    piece = delta[: MAX_STATEMENT_CHARS - len(text)]
                    if piece:
                        text += piece
                        yield "statement", {"n": n, "role": role, "delta": piece}
                    if len(text) >= MAX_STATEMENT_CHARS:
                        break
            text = text.strip()
            if not text:
                raise TrialFailure("MODEL_ERROR")
            statements.append((n, role, text))
            yield "statement_done", {"n": n, "role": role, "text": text}

        verdict = None
        reason: str | None = None
        for attempt in range(2):
            if attempt == 1:
                yield "stage", {"stage": "retry", "n": None}
            yield "stage", {"stage": "judging", "n": None}
            prompt = _judge_prompt(case, deadline, statements, reason)
            async with aclosing(_bounded(model.run("judge", prompt), overall_deadline, model_timeout)) as chunks:
                raw = "".join([chunk async for chunk in chunks])
            try:
                verdict = parse_verdict(raw)
                break
            except VerdictError as exc:
                reason = str(exc)
        if verdict is None:
            raise TrialFailure("VERDICT_INVALID")
        yield "verdict", verdict.model_dump()
        yield "done", {}
    except TrialFailure as exc:
        yield _error_event(exc.code)
    except TimeoutError:
        yield _error_event("TIMEOUT")
    except Exception as exc:
        # 사건·발언이 로그에 남지 않도록 예외 형식만 기록한다
        logger.error("trial_failed type=%s", type(exc).__name__)
        yield _error_event("MODEL_ERROR")


def _error_event(code: str) -> Event:
    message, retryable = FAILURES[code]
    return "error", {"code": code, "message": message, "retryable": retryable}
