<<<<<<< HEAD
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
=======
import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
<<<<<<< HEAD
    StrictInt,
    field_validator,
    model_validator,
)

CAUSES = ("막막함", "완벽주의", "흥미 상실", "시간 부족", "피로")


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


class AcceptedVerdict(ApiModel):
    summary: str = Field(min_length=1, max_length=400)
    cause: Literal["막막함", "완벽주의", "흥미 상실", "시간 부족", "피로"]
    prescriptions: list[Prescription] = Field(min_length=1, max_length=2)


class CreateRecordInput(ApiModel):
    case: str = Field(min_length=5, max_length=300)
    deadline: date | None = None
    submitted_at: datetime = Field(alias="submittedAt")
    verdict: AcceptedVerdict
=======
    ValidationError,
    field_validator,
)

Cause = Literal["막막함", "완벽주의", "흥미 상실", "시간 부족", "피로"]
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def clean_case(value: object) -> object:
    if not isinstance(value, str):
        return value
    cleaned = value.strip()
    if "\x00" in cleaned:
        raise ValueError("NUL 문자는 허용하지 않는다")
    return cleaned


def parse_iso_date(value: str) -> date:
    if not _DATE_PATTERN.match(value):
        raise ValueError("YYYY-MM-DD 형식이어야 한다")
    return date.fromisoformat(value)


class Prescription(BaseModel):
    title: str = Field(min_length=1, max_length=30)
    steps: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(min_length=2, max_length=4)
    minutes: int = Field(ge=5, le=120, strict=True)
    reason: str = Field(min_length=1, max_length=150)


class StoredVerdict(BaseModel):
    summary: str = Field(min_length=1, max_length=400)
    cause: Cause
    prescriptions: list[Prescription] = Field(min_length=1, max_length=2)


Evidence = Annotated[list[Annotated[int, Field(ge=1, le=3, strict=True)]], Field(min_length=1, max_length=3)]


def _unique(value: list[int]) -> list[int]:
    if len(set(value)) != len(value):
        raise ValueError("근거 번호는 중복될 수 없다")
    return value


class Verdict(StoredVerdict):
    evidence: Evidence

    @field_validator("evidence")
    @classmethod
    def evidence_unique(cls, value: list[int]) -> list[int]:
        return _unique(value)


class RecordVerdict(StoredVerdict):
    """기록 저장 요청의 판결. 근거 번호가 있으면 검사하되 저장하지 않는다."""

    evidence: Evidence | None = None

    @field_validator("evidence")
    @classmethod
    def evidence_unique(cls, value: list[int] | None) -> list[int] | None:
        return None if value is None else _unique(value)


class VerdictError(ValueError):
    pass


def describe_errors(exc: ValidationError) -> str:
    # 판사에게 돌려줄 사유에는 필드 위치와 규칙 종류만 담는다
    return ", ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['type']}" for e in exc.errors())


def parse_verdict(raw: str) -> Verdict:
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        raise VerdictError("JSON 객체가 없다")
    try:
        data = json.loads(raw[start : end + 1])
    except ValueError as exc:
        raise VerdictError("JSON 형식이 아니다") from exc
    try:
        return Verdict.model_validate(data)
    except ValidationError as exc:
        raise VerdictError(describe_errors(exc)) from exc


class TrialRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case: str = Field(min_length=5, max_length=300)
    deadline: str | None = None
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26

    @field_validator("case", mode="before")
    @classmethod
    def strip_case(cls, value: object) -> object:
<<<<<<< HEAD
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
=======
        return clean_case(value)

    @field_validator("deadline")
    @classmethod
    def deadline_in_range(cls, value: str | None) -> str | None:
        if value is None:
            return None
        today = datetime.now(UTC).date()
        parsed = parse_iso_date(value)
        if not today <= parsed <= today + timedelta(days=365):
            raise ValueError("마감일은 오늘부터 365일 이내여야 한다")
        return value


class RecordCreate(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    case: str = Field(min_length=5, max_length=300)
    deadline: str | None = None
    submitted_at: AwareDatetime = Field(alias="submittedAt")
    verdict: RecordVerdict

    @field_validator("case", mode="before")
    @classmethod
    def strip_case(cls, value: object) -> object:
        return clean_case(value)

    @field_validator("deadline")
    @classmethod
    def deadline_is_date(cls, value: str | None) -> str | None:
        if value is not None:
            parse_iso_date(value)
        return value


class ChecksUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    checks: list[list[StrictBool]]
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
