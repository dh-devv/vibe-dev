import json
import re
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
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

    @field_validator("case", mode="before")
    @classmethod
    def strip_case(cls, value: object) -> object:
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
