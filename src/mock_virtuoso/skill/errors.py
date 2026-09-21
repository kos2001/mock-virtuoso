"""SKILL 실행 중 발생하는 오류들."""

from __future__ import annotations


class SkillError(Exception):
    """SKILL 런타임 오류. 서버가 NAK 메시지로 변환한다."""


class ParseError(SkillError):
    """SKILL 소스를 읽지 못했다."""


class UnknownFunction(SkillError):
    """mock이 구현하지 않은 함수가 호출되었다.

    조용히 nil을 반환하지 않는 것이 의도다. 미지원이 통과한 테스트로
    위장하는 것을 막는다.
    """

    def __init__(self, name: str) -> None:
        super().__init__(f"unknown function: {name}")
        self.name = name


class StepBudgetExceeded(SkillError):
    """평가 스텝 예산을 초과했다. 무한 루프 방어."""
