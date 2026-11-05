import re
from datetime import date, datetime, timezone
from typing import Annotated

from agent_framework import tool
from pydantic import Field

_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def days_until(deadline: str, today: date | None = None) -> int:
    if not _DATE_PATTERN.fullmatch(deadline):
        raise ValueError("마감일은 YYYY-MM-DD 형식이어야 합니다.")
    base = today or datetime.now(timezone.utc).date()
    return (date.fromisoformat(deadline) - base).days


@tool(approval_mode="always_require")
def calc_deadline(
    deadline: Annotated[str, Field(description="마감일 YYYY-MM-DD 형식")],
) -> str:
    """현재 UTC 날짜와 마감일 사이의 남은 날짜 수를 계산한다."""
    try:
        days = days_until(deadline)
    except ValueError:
        return "마감일은 YYYY-MM-DD 형식이어야 합니다."
    return f"마감일까지 {days}일 남았습니다." if days >= 0 else f"마감일이 {abs(days)}일 지났습니다."
