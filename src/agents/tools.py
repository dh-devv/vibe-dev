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
