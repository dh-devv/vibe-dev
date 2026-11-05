import asyncio
import logging
import shutil
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, Literal, Protocol

from src.agents.policy import tool_permission
from src.agents.tools import calc_deadline
from src.app.config import Settings

logger = logging.getLogger(__name__)

Role = Literal["defense", "prosecution", "judge"]
PROMPT_DIR = Path(__file__).parent / "prompts"
ALLOWED_TOOL = "calc_deadline"


class TrialModel(Protocol):
    def run(self, role: Role, prompt: str) -> AsyncIterator[str]: ...


class ModelNotConfiguredError(RuntimeError):
    pass


def load_prompt(role: Role) -> str:
    return (PROMPT_DIR / f"{role}.md").read_text(encoding="utf-8")


def approve_only_calc_deadline(request: Any, _context: Any) -> Any:
    """허용한 도구(calc_deadline) 하나만 승인한다. 셸·파일·URL 등은 모두 거부한다."""
    from copilot.generated.rpc import PermissionDecisionApproveOnce, PermissionDecisionUserNotAvailable
    from copilot.session_events import PermissionRequestCustomTool

    allowed = tool_permission(getattr(request, "tool_name", None), True)
    if (
        isinstance(request, PermissionRequestCustomTool)
        and allowed["permissionDecision"] == "allow"
    ):
        return PermissionDecisionApproveOnce()
    return PermissionDecisionUserNotAvailable()


class CopilotTrialModel:
    """GitHub Copilot SDK 클라이언트를 한 번 만들어 재사용하고, 호출마다 새 에이전트 세션을 연다."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any = None
        self._lock = asyncio.Lock()
        self._workdir: str | None = None
        self._base_dir: str | None = None

    async def _ensure_client(self) -> Any:
        async with self._lock:
            if self._client is None:
                token = self._settings.copilot_github_token
                if not token:
                    raise ModelNotConfiguredError
                from copilot import CopilotClient

                # 저장소 설정이나 훅을 읽지 않도록 비어 있는 임시 폴더에서 실행한다
                self._workdir = tempfile.mkdtemp(prefix="vibe-copilot-work-")
                self._base_dir = tempfile.mkdtemp(prefix="vibe-copilot-state-")
                client = CopilotClient(
                    github_token=token,
                    working_directory=self._workdir,
                    base_directory=self._base_dir,
                )
                await client.start()
                self._client = client
            return self._client

    def run(self, role: Role, prompt: str) -> AsyncIterator[str]:
        return self._stream(role, prompt)

    async def _stream(self, role: Role, prompt: str) -> AsyncIterator[str]:
        from agent_framework_github_copilot import GitHubCopilotAgent

        client = await self._ensure_client()
        options: dict[str, Any] = {
            "timeout": float(self._settings.model_timeout_seconds),
            "on_permission_request": approve_only_calc_deadline,
            "available_tools": [ALLOWED_TOOL],
            "working_directory": self._workdir,
        }
        if self._settings.copilot_model:
            options["model"] = self._settings.copilot_model
        agent = GitHubCopilotAgent(
            instructions=load_prompt(role),
            client=client,
            tools=[calc_deadline] if role == "prosecution" else None,
            default_options=options,
        )
        async with agent:
            async for update in agent.run(prompt, stream=True):
                if update.text:
                    yield update.text

    async def close(self) -> None:
        if self._client is not None:
            try:
                await self._client.stop()
            except Exception as exc:  # 종료 중 오류는 무시하고 형식만 남긴다
                logger.warning("copilot_stop_failed type=%s", type(exc).__name__)
            self._client = None
        for path in (self._workdir, self._base_dir):
            if path:
                shutil.rmtree(path, ignore_errors=True)
