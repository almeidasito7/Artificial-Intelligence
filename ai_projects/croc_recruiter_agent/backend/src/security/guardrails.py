from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailDecision:
    allowed: bool
    message: str = ""
    category: str = ""


_PROFANITY = {
    "idiot",
    "stupid",
    "dumb",
    "moron",
    "retard",
    "bitch",
    "asshole",
    "fuck",
    "shit",
    "cunt",
    "puta",
    "caralho",
    "porra",
    "vadia",
    "buceta",
    "arrombado",
}

_INJECTION_PATTERNS = [
    r"ignore (all|any|the) (previous|prior) (instructions|rules)",
    r"disregard (all|any|the) (previous|prior) (instructions|rules)",
    r"reveal (the )?(system|developer) prompt",
    r"print (the )?(system|developer) prompt",
    r"you are now (a|an) (different|new) (assistant|model)",
    r"act as (a|an) .*",
    r"jailbreak",
    r"prompt injection",
]

_OFFTOPIC_PATTERNS = [
    r"\btell me a joke\b",
    r"\bpolitics?\b",
    r"\breligion\b",
    r"\bcrypto( currency)?\b",
]


def check_message(text: str) -> GuardrailDecision:
    normalized = (text or "").strip().lower()
    if not normalized:
        return GuardrailDecision(allowed=True)

    tokens = set(re.findall(r"[a-zA-ZÀ-ÿ']+", normalized))
    if tokens & _PROFANITY:
        return GuardrailDecision(
            allowed=False,
            category="abusive_language",
            message="I can’t help with abusive or derogatory language. Please rephrase your request.",
        )

    for pattern in _INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            return GuardrailDecision(
                allowed=False,
                category="prompt_injection",
                message="I can’t follow instructions that attempt to override system rules. Please ask a work-related question.",
            )

    for pattern in _OFFTOPIC_PATTERNS:
        if re.search(pattern, normalized):
            return GuardrailDecision(
                allowed=False,
                category="off_topic",
                message="I can only help with work-related topics: staffing data, candidates, placements, policies, and office resources.",
            )

    return GuardrailDecision(allowed=True)

