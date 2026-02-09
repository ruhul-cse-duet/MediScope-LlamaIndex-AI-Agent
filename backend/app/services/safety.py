from __future__ import annotations

from dataclasses import dataclass

RED_FLAG_PHRASES = [
    "chest pain",
    "shortness of breath",
    "severe bleeding",
    "loss of consciousness",
    "stroke",
    "seizure",
    "suicidal",
    "overdose",
    "severe headache",
    "sudden weakness",
    "confusion",
    "blue lips",
    "not breathing",
    "severe allergic",
    "anaphylaxis",
]

SAFETY_DISCLAIMER = (
    "This information is for education and triage support only. "
    "It is not a medical diagnosis or treatment plan."
)

RED_FLAG_MESSAGE = (
    "Your message contains possible emergency warning signs. "
    "If you or someone else is experiencing this, seek urgent medical care or emergency services now."
)


@dataclass
class SafetyResult:
    is_red_flag: bool
    disclaimer: str
    urgent_notice: str | None


def assess(text: str) -> SafetyResult:
    lowered = text.lower()
    is_red_flag = any(phrase in lowered for phrase in RED_FLAG_PHRASES)
    urgent_notice = RED_FLAG_MESSAGE if is_red_flag else None
    return SafetyResult(is_red_flag=is_red_flag, disclaimer=SAFETY_DISCLAIMER, urgent_notice=urgent_notice)
