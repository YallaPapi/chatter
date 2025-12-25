# -*- coding: utf-8 -*-
"""
Intent Detector

Detects what the fan is doing RIGHT NOW, not what phase we're in.
Uses pre-compiled patterns from patterns.py for better performance.
"""

from typing import Optional
from dataclasses import dataclass

# Import pre-compiled patterns
from patterns import INTENT_PATTERNS, INTENT_PRIORITY


@dataclass
class Intent:
    """Detected intent with confidence"""
    name: str
    confidence: float  # 0-1
    raw_match: Optional[str] = None  # What pattern matched


def detect_intent(message: str) -> Intent:
    """
    Detect the primary intent from a message.

    Returns Intent with name and confidence.
    Falls back to GENERIC if nothing matches.

    Uses pre-compiled patterns for ~15ms performance improvement.
    """
    msg_lower = message.lower().strip()

    # Check each intent in priority order
    for intent_name in INTENT_PRIORITY:
        patterns = INTENT_PATTERNS.get(intent_name, [])
        for pattern in patterns:
            # Pattern is already compiled - use .search() directly
            match = pattern.search(msg_lower)
            if match:
                # Confidence based on match quality
                match_len = len(match.group())
                msg_len = max(len(msg_lower), 1)
                confidence = min(0.5 + (match_len / msg_len) * 0.5, 1.0)

                return Intent(
                    name=intent_name,
                    confidence=confidence,
                    raw_match=match.group()
                )

    # No match - generic
    return Intent(name="GENERIC", confidence=0.5)


def is_escalation(intent: Intent) -> bool:
    """Check if this intent represents escalation (wanting more)"""
    escalation_intents = {
        "PIC_REQUEST",
        "SEXUAL",
        "MEETUP_REQUEST",
        "CONTACT_REQUEST",
        "COMPLIMENT",  # Repeated compliments = escalation
    }
    return intent.name in escalation_intents


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    test_messages = [
        "hey",
        "hey whats up",
        "you're so hot",
        "send pics",
        "lets meet up",
        "what's your snap",
        "are you real?",
        "I just subscribed",
        "fuck this bye",
        "I'm from Chicago",
        "where are you from",
        "do you have an onlyfans",
        "rough day today",
        "what are you wearing",
        "just chilling",
        "ok cool",
        "nah im good",
        "not paying for that",
    ]

    print("=== INTENT DETECTOR TEST ===\n")
    for msg in test_messages:
        intent = detect_intent(msg)
        esc = " [ESCALATION]" if is_escalation(intent) else ""
        print(f'"{msg}" -> {intent.name} ({intent.confidence:.2f}){esc}')
