from __future__ import annotations

import asyncio
import html
import os
import re
import tempfile
from collections.abc import AsyncIterator, Sequence
from datetime import date, datetime, timezone
from importlib.resources import files
from typing import Any

from pydantic import ValidationError

from src.agents.policy import tool_permission
from src.app.config import Settings
from src.app.schemas import Verdict


class TrialModelError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = True) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


def _prompt(name: str) -> str:
    return files("src.agents.prompts").joinpath(name).read_text(encoding="utf-8")


def _tagged_case(case: str) -> str:
    return f"<case>{html.escape(case, quote=False)}</case>"


async def _agent_text(
    settings: Settings,
    instructions: str,
    prompt: str,
    *,
    tools: Sequence[Any] = (),
) -> AsyncIterator[str]:
    if not settings.copilot_github_token:
        raise TrialModelError(
            "MODEL_ERROR",
            "재판 모델 설정이 필요합니다. 잠시 후 다시 시도해 주세요.",
        )

    try:
        from agent_framework.exceptions import AgentException
        from agent_framework.github import GitHubCopilotAgent, GitHubCopilotOptions
        from copilot import CopilotClient
        from copilot.generated.rpc import PermissionDecisionReject
        from copilot.session import PreToolUseHookInput, PreToolUseHookOutput
    except ImportError as error:
        raise TrialModelError(
            "MODEL_ERROR",
            "재판 모델을 시작하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        ) from error

    from src.agents.tools import calc_deadline

    def tool_gate(
        hook_input: PreToolUseHookInput,
        _context: dict[str, str],
    ) -> PreToolUseHookOutput:
        return tool_permission(hook_input.get("toolName"), bool(tools))

    def deny_permission(request: Any, _context: Any) -> Any:
        return PermissionDecisionReject(feedback="이 재판에서 허용하지 않은 도구입니다.")

    working_directory = tempfile.TemporaryDirectory(prefix="trial-agent-")
    try:
        env = {**os.environ, "COPILOT_GITHUB_TOKEN": settings.copilot_github_token}
        client = CopilotClient(
            env=env,
            working_directory=working_directory.name,
            base_directory=working_directory.name,
            use_logged_in_user=False,
        )
        agent = GitHubCopilotAgent(
            instructions=instructions,
            tools=[calc_deadline] if tools else [],
            client=client,
            default_options=GitHubCopilotOptions(
                enable_file_hooks=False,
                on_pre_tool_use=tool_gate,
                on_permission_request=deny_permission,
            ),
        )
        async with client:
            async with agent:
                async for chunk in agent.run(prompt, stream=True):
                    text = getattr(chunk, "text", None)
                    if isinstance(text, str) and text:
                        yield text
    except TimeoutError as error:
        raise TrialModelError("TIMEOUT", "재판이 너무 오래 걸려 중단했습니다. 다시 시도해 주세요.") from error
    except TrialModelError:
        raise
    except (AgentException, OSError, RuntimeError, ValueError) as error:
        raise TrialModelError(
            "MODEL_ERROR",
            "법정에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.",
        ) from error
    finally:
        working_directory.cleanup()


def _numbered_statements(statements: list[tuple[str, str]]) -> str:
    return "\n".join(
        f"[{number}] {role}: {text}"
        for number, (role, text) in enumerate(statements, 1)
    )


def _parse_verdict(text: str) -> Verdict:
    candidate = text.strip()
    candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
    return Verdict.model_validate_json(candidate)


async def _collect_verdict(settings: Settings, prompt: str) -> str:
    output: list[str] = []
    try:
        async with asyncio.timeout(settings.model_timeout_seconds):
            async for text in _agent_text(settings, _prompt("judge.md"), prompt):
                output.append(text)
    except TimeoutError as error:
        raise TrialModelError("TIMEOUT", "재판이 너무 오래 걸려 중단했습니다. 다시 시도해 주세요.") from error
    return "".join(output)


async def run_trial(
    settings: Settings, case: str, deadline: date | None
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    submitted_at = datetime.now(timezone.utc)
    yield "trial_started", {
        "submittedAt": submitted_at.isoformat().replace("+00:00", "Z")
    }

    safe_case = _tagged_case(case)
    deadline_text = deadline.isoformat() if deadline else "없음"
    statements: list[tuple[str, str]] = []
    defense_prompt = f"사건:\n{safe_case}\n마감일: {deadline_text}\n첫 변론을 작성하라."
    yield "stage", {"stage": "defense", "n": 1}
    defense_parts: list[str] = []
    async for event in _stream_statement(
        settings, "defense.md", defense_prompt, 1, "defense", defense_parts
    ):
        yield event
    statements.append(("defense", "".join(defense_parts).strip()))

    prosecution_prompt = (
        f"사건:\n{safe_case}\n마감일: {deadline_text}\n"
        f"변호인의 직전 발언:\n{statements[0][1]}\n이에 답하라."
    )
    yield "stage", {"stage": "prosecution", "n": 2}
    prosecution_parts: list[str] = []
    async for event in _stream_statement(
        settings,
        "prosecution.md",
        prosecution_prompt,
        2,
        "prosecution",
        prosecution_parts,
    ):
        yield event
    statements.append(("prosecution", "".join(prosecution_parts).strip()))

    rebuttal_prompt = (
        f"사건:\n{safe_case}\n마감일: {deadline_text}\n검사의 직전 발언:\n{statements[-1][1]}\n"
        "변호인의 재반박을 작성하라."
    )
    yield "stage", {"stage": "rebuttal", "n": 3}
    rebuttal_parts: list[str] = []
    async for event in _stream_statement(
        settings, "defense.md", rebuttal_prompt, 3, "defense", rebuttal_parts
    ):
        yield event
    statements.append(("defense", "".join(rebuttal_parts).strip()))

    judging_prompt = (
        f"사건:\n{safe_case}\n마감일: {deadline_text}\n"
        f"공방 발언:\n{_numbered_statements(statements)}\n판결을 JSON으로 출력하라."
    )
    for attempt in range(2):
        yield "stage", {"stage": "judging", "n": None}
        raw_verdict = await _collect_verdict(settings, judging_prompt)
        try:
            verdict = _parse_verdict(raw_verdict)
            yield "verdict", verdict.model_dump(mode="json")
            yield "done", {}
            return
        except (ValidationError, ValueError):
            if attempt == 1:
                raise TrialModelError(
                    "VERDICT_INVALID",
                    "판결문을 만들지 못했습니다. 다시 시도해 주세요.",
                )
            yield "stage", {"stage": "retry", "n": None}
            judging_prompt += (
                "\n이전 출력은 유효하지 않았다. 형식 오류를 고쳐 JSON 객체만 출력하라. "
                "필수 규칙: summary 1~400자, cause 허용값, prescriptions 1~2개, "
                "각 처방 steps 2~4개, evidence는 중복 없이 1~3."
            )


async def _stream_statement(
    settings: Settings,
    prompt_file: str,
    prompt: str,
    number: int,
    role: str,
    output: list[str],
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    instructions = _prompt(prompt_file)
    tools = ("calc_deadline",) if role == "prosecution" else ()
    try:
        async with asyncio.timeout(settings.model_timeout_seconds):
            async for delta in _agent_text(settings, instructions, prompt, tools=tools):
                remaining = 250 - sum(map(len, output))
                if remaining <= 0:
                    break
                bounded = delta[:remaining]
                if bounded:
                    output.append(bounded)
                    yield "statement", {"n": number, "role": role, "delta": bounded}
    except TimeoutError as error:
        raise TrialModelError("TIMEOUT", "재판이 너무 오래 걸려 중단했습니다. 다시 시도해 주세요.") from error
    text = "".join(output)
    if not text.strip():
        raise TrialModelError("MODEL_ERROR", "법정에 문제가 생겼습니다. 잠시 후 다시 시도해 주세요.")
    output[:] = [text]
    yield "statement_done", {"n": number, "role": role, "text": text}
