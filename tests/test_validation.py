import pytest
from pydantic import ValidationError

from src.app.safety import contains_crisis_signal
from src.app.schemas import ChecksInput, TrialInput, Verdict


def test_trial_input_trims_and_validates_case_length() -> None:
    assert TrialInput(case="  안녕하세요  ").case == "안녕하세요"
    assert TrialInput(case="안녕하세요", reason="  시작이 막막하다  ").reason == "시작이 막막하다"
    with pytest.raises(ValidationError):
        TrialInput(case="   ")
    with pytest.raises(ValidationError):
        TrialInput(case=123)
    with pytest.raises(ValidationError):
        TrialInput(case="안녕하세요", reason="짧음")


def test_execution_checks_require_json_booleans() -> None:
    with pytest.raises(ValidationError):
        ChecksInput(checks=[[1, 0]])


def test_verdict_rejects_out_of_range_evidence() -> None:
    with pytest.raises(ValidationError):
        Verdict.model_validate(
            {
                "summary": "판결 요약",
                "cause": "막막함",
                "prescriptions": [
                    {
                        "title": "목차 만들기",
                        "steps": ["제목 쓰기", "소제목 쓰기"],
                        "minutes": 15,
                        "reason": "시작을 돕습니다.",
                    }
                ],
                "evidence": [4],
            }
        )


def test_crisis_matcher_checks_korean_phrases() -> None:
    assert contains_crisis_signal("요즘 죽고 싶다는 생각이 든다")
    assert contains_crisis_signal("자해를 하고 싶다")
    assert not contains_crisis_signal("보고서를 쓰기 싫다")
