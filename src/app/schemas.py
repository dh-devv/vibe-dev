from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictInt,
    field_validator,
    model_validator,
)
from pydantic import ValidationError

CAUSES = ("막막함", "완벽주의", "흥미 상실", "시간 부족", "피로")
_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class VerdictError(ValueError):
    pass


class ApiModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class TrialInput(ApiModel):
    case: str = Field(min_length=5, max_length=300)
    deadline: date | None = None

    @field_validator("case", mode="before")
    @classmethod
    def strip_case(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_deadline(self) -> TrialInput:
        if self.deadline is not None:
            today = datetime.now(timezone.utc).date()
            if not today <= self.deadline <= today + timedelta(days=365):
                raise ValueError("마감일은 오늘부터 365일 이내여야 합니다.")
        return self


class Prescription(ApiModel):
    title: str = Field(min_length=1, max_length=30)
    steps: list[str] = Field(min_length=2, max_length=4)
    minutes: StrictInt = Field(ge=5, le=120)
    reason: str = Field(min_length=1, max_length=150)

    @field_validator("steps")
    @classmethod
    def validate_steps(cls, steps: list[str]) -> list[str]:
        if any(not step.strip() or len(step) > 80 for step in steps):
            raise ValueError("각 단계는 1자 이상 80자 이하여야 합니다.")
        return steps


class Verdict(ApiModel):
    summary: str = Field(min_length=1, max_length=400)
    cause: Literal["막막함", "완벽주의", "흥미 상실", "시간 부족", "피로"]
    prescriptions: list[Prescription] = Field(min_length=1, max_length=2)
    evidence: list[Annotated[StrictInt, Field(ge=1, le=3)]] = Field(
        min_length=1, max_length=3
    )

    @field_validator("evidence")
    @classmethod
    def unique_evidence(cls, evidence: list[StrictInt]) -> list[StrictInt]:
        if len(set(evidence)) != len(evidence):
            raise ValueError("근거 번호는 중복될 수 없습니다.")
        return evidence


def parse_verdict(raw: str) -> Verdict:
    candidate = _JSON_FENCE.sub("", raw.strip())
    try:
        value = json.loads(candidate)
        return Verdict.model_validate(value)
    except (json.JSONDecodeError, ValidationError, ValueError) as error:
        raise VerdictError("판결문 형식이 올바르지 않습니다.") from error


class AcceptedVerdict(ApiModel):
    summary: str = Field(min_length=1, max_length=400)
    cause: Literal["막막함", "완벽주의", "흥미 상실", "시간 부족", "피로"]
    prescriptions: list[Prescription] = Field(min_length=1, max_length=2)


class CreateRecordInput(ApiModel):
    case: str = Field(min_length=5, max_length=300)
    deadline: date | None = None
    submitted_at: datetime = Field(alias="submittedAt")
    verdict: AcceptedVerdict

    @field_validator("case", mode="before")
    @classmethod
    def strip_case(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("submitted_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("submittedAt에는 시간대가 필요합니다.")
        if value.astimezone(timezone.utc) > datetime.now(timezone.utc):
            raise ValueError("submittedAt은 미래 시각일 수 없습니다.")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def validate_deadline(self) -> CreateRecordInput:
        if self.deadline is not None:
            today = datetime.now(timezone.utc).date()
            if not today <= self.deadline <= today + timedelta(days=365):
                raise ValueError("마감일은 오늘부터 365일 이내여야 합니다.")
        return self


class ChecksInput(ApiModel):
    checks: list[list[StrictBool]]


class RecordOut(ApiModel):
    id: UUID
    case: str
    deadline: date | None
    verdict: AcceptedVerdict
    checks: list[list[bool]]
    submitted_at: datetime = Field(alias="submittedAt")
    accepted_at: datetime = Field(alias="acceptedAt")
    first_checked_at: datetime | None = Field(alias="firstCheckedAt")
    completed_at: datetime | None = Field(alias="completedAt")
