<<<<<<< HEAD
from datetime import date, datetime, timezone
from typing import Annotated

from agent_framework import tool
from pydantic import Field


@tool(approval_mode="always_require")
def calc_deadline(
    deadline: Annotated[str, Field(description="마감일 YYYY-MM-DD 형식")],
) -> str:
    """현재 UTC 날짜와 마감일 사이의 남은 날짜 수를 계산한다."""
    try:
        due_date = date.fromisoformat(deadline)
    except ValueError:
        raise ValueError("마감일은 YYYY-MM-DD 형식이어야 합니다.") from None
    today = datetime.now(timezone.utc).date()
    days = (due_date - today).days
    return f"마감일까지 {days}일 남았습니다." if days >= 0 else f"마감일이 {abs(days)}일 지났습니다."
=======
from datetime import UTC, date, datetime
from typing import Annotated

from agent_framework import tool

from src.app.schemas import parse_iso_date


def days_until(deadline: str, today: date | None = None) -> int:
    base = today or datetime.now(UTC).date()
    return (parse_iso_date(deadline) - base).days


@tool(
    name="calc_deadline",
    description="YYYY-MM-DD 마감일까지 남은 일수를 계산한다.",
    approval_mode="never_require",
)
def calc_deadline(deadline: Annotated[str, "YYYY-MM-DD 형식의 마감일"]) -> str:
    try:
        days = days_until(deadline)
    except ValueError:
        return "마감일 형식이 올바르지 않습니다. YYYY-MM-DD로 입력해야 합니다."
    if days < 0:
        return f"마감일이 {-days}일 지났습니다."
    if days == 0:
        return "마감일은 오늘입니다."
    return f"마감까지 {days}일 남았습니다."
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
