import asyncio
import logging
import random
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Any

from src.agents.model import ModelNotConfiguredError, Role, TrialModel
from src.app.schemas import VerdictError, parse_verdict

logger = logging.getLogger(__name__)

STEPS: tuple[tuple[int, Role, str], ...] = (
    (1, "defense", "defense"),
    (2, "prosecution", "prosecution"),
    (3, "defense", "rebuttal"),
)
SPEAKER = {"defense": "변호인", "prosecution": "검사"}

# 같은 사건도 재판마다 다른 공방이 되도록 매번 하나씩 뽑아 프롬프트에 더한다
STRATEGIES: dict[str, tuple[str, ...]] = {
    "defense": (
        "피고인의 부담감과 막막함에 먼저 공감하며 변론하라.",
        "이미 해낸 작은 일과 지금까지의 노력을 근거로 변론하라.",
        "재치 있는 비유를 하나 들어 변론하라.",
        "지금 미루는 것이 합리적인 이유를 차분하게 따지며 변론하라.",
        "시작이 어려울 뿐이라는 점을 강조하며 변론하라.",
    ),
    "prosecution": (
        "미룰수록 커지는 부담과 마감의 현실을 날카롭게 짚어라.",
        "변호인 논리의 허점을 하나 골라 정면으로 반박하라.",
        "미룬 시간만큼 줄어든 선택지를 따져라.",
        "유머를 섞되 핵심은 놓치지 말고 추궁하라.",
        "'나중에 하면 된다'는 믿음을 의심하게 하는 질문을 던져라.",
    ),
    "judge": (
        "아주 작게 시작하는 처방을 중심으로 판결하라.",
        "환경과 순서를 바꾸는 처방을 중심으로 판결하라.",
        "시간을 정해 두고 끝내는 처방을 중심으로 판결하라.",
        "가장 쉬운 첫 행동부터 쌓는 처방을 중심으로 판결하라.",
    ),
}

FAILURES: dict[str, tuple[str, bool]] = {
    "MODEL_NOT_CONFIGURED": (
        "AI 토큰 설정이 필요합니다. COPILOT_GITHUB_TOKEN을 확인해 주세요.",
        False,
    ),
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


def _case_block(case: str, reason: str, deadline: str | None) -> str:
    reason_text = f"\n미룬 이유: {_escape(reason)}" if reason else ""
    return f"<case>{_escape(case)}{reason_text}</case>\n<deadline>{deadline or '없음'}</deadline>"


def _transcript(statements: list[tuple[int, str, str]]) -> str:
    return "\n".join(f"[{n}] {SPEAKER[role]}: {_escape(text)}" for n, role, text in statements)


def _step_prompt(
    stage: str,
    case: str,
    reason: str,
    deadline: str | None,
    statements: list[tuple[int, str, str]],
    strategy: str,
) -> str:
    instruction = {
        "defense": "변호인으로서 첫 변론을 하라.",
        "prosecution": "검사로서 변호인의 발언을 반박하라.",
        "rebuttal": "변호인으로서 검사의 발언에 재반박하라.",
    }[stage]
    parts = [_case_block(case, reason, deadline)]
    if statements:
        parts.append(_transcript(statements))
    parts.append(f"{instruction}\n이번 재판의 방향: {strategy}")
    return "\n\n".join(parts)


def _judge_prompt(
    case: str,
    case_reason: str,
    deadline: str | None,
    statements: list[tuple[int, str, str]],
    retry_reason: str | None,
    strategy: str,
) -> str:
    parts = [
        _case_block(case, case_reason, deadline),
        _transcript(statements),
        f"위 발언을 읽고 판결 JSON을 출력하라.\n이번 재판의 방향: {strategy}",
    ]
    if retry_reason:
        parts.append(f"이전 출력이 검증에서 반려되었다. 사유: {retry_reason}\n형식 규칙을 지켜 JSON만 다시 출력하라.")
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
    case_reason: str = "",
) -> AsyncIterator[Event]:
    """변호인 → 검사 → 변호인 → 판사 → 검증기 순서를 코드가 정한다. 상태는 이 함수 안에서만 쓴다."""
    overall_deadline = asyncio.get_running_loop().time() + trial_timeout
    yield "trial_started", {"submittedAt": submitted_at}
    statements: list[tuple[int, str, str]] = []
    picks = {role: random.choice(options) for role, options in STRATEGIES.items()}
    try:
        for n, role, stage in STEPS:
            yield "stage", {"stage": stage, "n": n}
            text = ""
            prompt = _step_prompt(stage, case, case_reason, deadline, statements, picks[role])
            async with aclosing(_bounded(model.run(role, prompt), overall_deadline, model_timeout)) as chunks:
                async for delta in chunks:
                    if delta:
                        text += delta
                        yield "statement", {"n": n, "role": role, "delta": delta}
            if not text.strip():
                raise TrialFailure("MODEL_ERROR")
            statements.append((n, role, text))
            yield "statement_done", {"n": n, "role": role, "text": text}

        verdict = None
        reason: str | None = None
        for attempt in range(2):
            if attempt == 1:
                yield "stage", {"stage": "retry", "n": None}
            yield "stage", {"stage": "judging", "n": None}
            prompt = _judge_prompt(case, case_reason, deadline, statements, reason, picks["judge"])
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
    except ModelNotConfiguredError:
        yield _error_event("MODEL_NOT_CONFIGURED")
    except TimeoutError:
        yield _error_event("TIMEOUT")
    except Exception as exc:
        # 사건·발언이 로그에 남지 않도록 예외 형식만 기록한다
        logger.error("trial_failed type=%s", type(exc).__name__)
        yield _error_event("MODEL_ERROR")


def _error_event(code: str) -> Event:
    message, retryable = FAILURES[code]
    return "error", {"code": code, "message": message, "retryable": retryable}
