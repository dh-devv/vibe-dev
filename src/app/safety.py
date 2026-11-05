<<<<<<< HEAD
CRISIS_TERMS = (
    "자살",
    "자해",
    "죽고 싶",
    "죽고싶",
    "극단적 선택",
    "목숨을 끊",
    "목숨 끊",
)

HELPLINES = [
=======
import re

HELPLINES: list[dict[str, str]] = [
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
    {"name": "자살예방 상담전화", "phone": "109", "hours": "24시간"},
    {"name": "정신건강 위기상담전화", "phone": "1577-0199", "hours": "24시간"},
    {"name": "긴급 상황", "phone": "119", "hours": "24시간"},
]

<<<<<<< HEAD

def contains_crisis_signal(text: str) -> bool:
    normalized = text.casefold()
    return any(term in normalized for term in CRISIS_TERMS)
=======
CRISIS_MESSAGE = "지금은 재판보다 도움이 먼저입니다. 아래 상담 전화로 바로 연락해 주세요."

# 공백을 제거한 문장과 비교하므로 표현에 공백을 넣지 않는다
CRISIS_TERMS: tuple[str, ...] = (
    "자살",
    "자해",
    "극단적선택",
    "극단적인선택",
    "목숨을끊",
    "목숨을버",
    "스스로목숨",
    "삶을끝내",
    "생을마감",
    "죽고싶",
    "죽고만싶",
    "죽어버리고싶",
    "죽을래",
    "사라지고싶",
    "살고싶지않",
    "살기싫",
)

_WHITESPACE = re.compile(r"\s+")


def has_crisis_signal(text: str) -> bool:
    compact = _WHITESPACE.sub("", text).lower()
    return any(term in compact for term in CRISIS_TERMS)
>>>>>>> 382e149d50f0c260af14e231ed70bff13a024f26
