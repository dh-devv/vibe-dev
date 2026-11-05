import asyncio
from datetime import date

import pytest

from src.agents.model import approve_only_calc_deadline
from src.agents.tools import calc_deadline, days_until
from src.agents.trial import _bounded
from src.app.schemas import VerdictError, parse_verdict
from tests.conftest import VALID_VERDICT


def test_days_until() -> None:
    assert days_until("2026-11-07", today=date(2026, 11, 5)) == 2
    assert days_until("2026-11-01", today=date(2026, 11, 5)) == -4
    with pytest.raises(ValueError):
        days_until("내일")


def test_calc_deadline_tool_rejects_bad_format() -> None:
    result = calc_deadline.func("11/07")

    assert "YYYY-MM-DD" in result


def test_permission_handler_approves_only_calc_deadline() -> None:
    from copilot.generated.rpc import PermissionDecisionApproveOnce
    from copilot.session_events import PermissionRequestCustomTool, PermissionRequestShell

    class Fake(PermissionRequestCustomTool):
        def __init__(self, name: str) -> None:
            self.tool_name = name

    approved = approve_only_calc_deadline(Fake("calc_deadline"), None)
    other_tool = approve_only_calc_deadline(Fake("bash"), None)
    shell = approve_only_calc_deadline(object.__new__(PermissionRequestShell), None)

    assert isinstance(approved, PermissionDecisionApproveOnce)
    assert not isinstance(other_tool, PermissionDecisionApproveOnce)
    assert not isinstance(shell, PermissionDecisionApproveOnce)


def test_parse_verdict_accepts_fenced_json() -> None:
    import json

    raw = "```json\n" + json.dumps(VALID_VERDICT, ensure_ascii=False) + "\n```"

    assert parse_verdict(raw).cause == "막막함"


@pytest.mark.parametrize(
    "patch",
    [
        {"cause": "게으름"},
        {"evidence": []},
        {"evidence": [1, 1]},
        {"evidence": [0]},
        {"summary": "가" * 401},
        {"prescriptions": []},
        {"minutes": 5},
    ],
)
def test_parse_verdict_rejects_invalid(patch: dict) -> None:
    import json

    data = {**VALID_VERDICT, **patch}
    if "minutes" in patch:
        data = {**VALID_VERDICT, "prescriptions": [{**VALID_VERDICT["prescriptions"][0], "minutes": True}]}

    with pytest.raises(VerdictError):
        parse_verdict(json.dumps(data, ensure_ascii=False))


def test_bounded_stops_slow_stream() -> None:
    async def slow():
        await asyncio.sleep(5)
        yield "x"

    async def consume() -> None:
        loop = asyncio.get_running_loop()
        async for _ in _bounded(slow(), loop.time() + 10, 0.2):
            pass

    with pytest.raises(TimeoutError):
        asyncio.run(consume())
