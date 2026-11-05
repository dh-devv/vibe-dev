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
