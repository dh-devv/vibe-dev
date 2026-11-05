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
    {"name": "자살예방 상담전화", "phone": "109", "hours": "24시간"},
    {"name": "정신건강 위기상담전화", "phone": "1577-0199", "hours": "24시간"},
    {"name": "긴급 상황", "phone": "119", "hours": "24시간"},
]


def contains_crisis_signal(text: str) -> bool:
    normalized = text.casefold()
    return any(term in normalized for term in CRISIS_TERMS)
