from __future__ import annotations

from dataclasses import dataclass
import re


FENCED_CODE_RE = re.compile(r"```.*?```", re.DOTALL)
BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
HEADING_RE = re.compile(r"^\s*#{1,6}\s+", re.MULTILINE)


@dataclass(frozen=True)
class ResponseStyleAssessment:
    passed: bool
    violations: tuple[str, ...]
    character_count: int
    bullet_count: int
    heading_count: int


def assess_response_style(
    answer: str | None,
    *,
    max_characters: int = 1200,
    max_bullets: int = 6,
    max_headings: int = 3,
) -> ResponseStyleAssessment:
    prose = FENCED_CODE_RE.sub("", answer or "").strip()
    character_count = len(prose)
    bullet_count = len(BULLET_RE.findall(prose))
    heading_count = len(HEADING_RE.findall(prose))
    violations: list[str] = []

    if character_count > max_characters:
        violations.append("answer_too_long")
    if bullet_count > max_bullets:
        violations.append("too_many_bullets")
    if heading_count > max_headings:
        violations.append("too_many_headings")
    return ResponseStyleAssessment(
        passed=not violations,
        violations=tuple(violations),
        character_count=character_count,
        bullet_count=bullet_count,
        heading_count=heading_count,
    )
