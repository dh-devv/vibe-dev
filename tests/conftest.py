import json
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi.testclient import TestClient

from src.app.config import Settings
from src.app.limits import RateLimiter
from src.app.main import app

VALID_VERDICT = {
    "summary": "막막함은 받아들이고 마감 압박은 일부만 받아들입니다.",
    "cause": "막막함",
    "prescriptions": [
        {
            "title": "목차부터 만들기",
            "steps": ["보고서 제목을 쓴다", "소제목 3개를 적는다"],
            "minutes": 15,
            "reason": "시작 부담을 줄입니다.",
        }
    ],
    "evidence": [1, 2],
}


class FakeModel:
    def __init__(self, judge_outputs: list[str] | None = None, fail_role: str | None = None) -> None:
        self.judge_outputs = list(judge_outputs or [json.dumps(VALID_VERDICT, ensure_ascii=False)])
        self.fail_role = fail_role
        self.calls: list[tuple[str, str]] = []

    async def run(self, role: str, prompt: str) -> AsyncIterator[str]:
        self.calls.append((role, prompt))
        if role == self.fail_role:
            raise RuntimeError("모델 오류")
        if role == "judge":
            yield self.judge_outputs.pop(0)
            return
        yield f"{role} 발언 "
        yield "끝"

    async def close(self) -> None:
        return None


@pytest.fixture
def fake_model() -> FakeModel:
    return FakeModel()


@pytest.fixture
def client(fake_model: FakeModel) -> Iterator[TestClient]:
    settings = Settings(_env_file=None, dev_auth_enabled=True)
    app.state.settings = settings
    app.state.trial_model = fake_model
    app.state.limiter = RateLimiter(
        settings.ip_per_minute,
        settings.ip_per_day,
        settings.user_per_minute,
        settings.user_per_day,
        settings.global_per_day,
    )
    with TestClient(app) as test_client:
        yield test_client


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        name, data = "", ""
        for line in block.split("\n"):
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = line[6:]
        events.append((name, json.loads(data)))
    return events
