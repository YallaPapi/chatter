# -*- coding: utf-8 -*-
"""
Tension Tracker

Tracks escalation count and determines when to reveal OF.
Uses randomized probability - fishing approach, not hard thresholds.
"""

import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class TensionLevel(Enum):
    """How we respond to escalation attempts"""
    DEFLECT = 1   # Change subject, stay casual
    TEASE = 2     # Acknowledge but don't give
    HINT = 3      # Suggest there's more somewhere
    REVEAL = 4    # Drop the OF


class ConversionState(Enum):
    """Where they are in the OF funnel"""
    PRE_PITCH = "pre_pitch"       # Haven't mentioned OF yet
    PITCHED = "pitched"           # OF mentioned, waiting for response
    INTERESTED = "interested"     # Showed interest ("how much?", "what's on there?")
    RESISTANT = "resistant"       # Pushed back ("I don't pay", "too expensive")
    CONVERTED = "converted"       # Subscribed
    COLD = "cold"                 # Gone silent after pitch


@dataclass
class TensionState:
    """Tracks tension/escalation state for a conversation"""
    escalation_count: int = 0
    current_level: TensionLevel = TensionLevel.DEFLECT
    conversion_state: ConversionState = ConversionState.PRE_PITCH
    of_revealed: bool = False
    messages_since_pitch: int = 0

    # Track what types of escalation we've seen
    escalation_types: list = field(default_factory=list)

    # Objection tracking - when True, stop mentioning OF
    objection_detected: bool = False

    # Proactive pitch tracking - for natural OF mentions without escalation
    message_count: int = 0  # Total messages in conversation
    rapport_score: float = 0.0  # Accumulated from positive interactions
    proactive_pitch_suggested: bool = False  # Prevent spam - only suggest once


# =============================================================================
# PROBABILITY CONFIG
# =============================================================================

# Probability of revealing OF based on escalation count
# Never 0% - some guys are ready immediately
REVEAL_PROBABILITY = {
    1: 0.05,   # 5% - very unlikely, just deflect
    2: 0.10,   # 10% - still early
    3: 0.25,   # 25% - getting warmer
    4: 0.50,   # 50% - coin flip
    5: 0.75,   # 75% - probably time
}
# 6+ = 90% (almost certain)
DEFAULT_PROBABILITY = 0.90


def get_reveal_probability(escalation_count: int) -> float:
    """Get probability of revealing OF at this escalation count"""
    return REVEAL_PROBABILITY.get(escalation_count, DEFAULT_PROBABILITY)


def should_reveal_of(escalation_count: int) -> bool:
    """
    Roll the dice - should we reveal OF now?

    Returns True if random roll passes probability threshold.
    """
    probability = get_reveal_probability(escalation_count)
    roll = random.random()
    return roll < probability


# =============================================================================
# TENSION TRACKER
# =============================================================================

class TensionTracker:
    """Manages tension/escalation state for conversations"""

    def __init__(self):
        # Store state per conversation
        self.conversations: dict[str, TensionState] = {}

    def get_state(self, conversation_id: str) -> TensionState:
        """Get or create tension state for a conversation"""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = TensionState()
        return self.conversations[conversation_id]

    def record_escalation(self, conversation_id: str, intent_name: str) -> TensionLevel:
        """
        Record an escalation attempt and determine how to respond.

        Args:
            conversation_id: Unique conversation identifier
            intent_name: The escalation intent detected (PIC_REQUEST, SEXUAL, etc.)

        Returns:
            TensionLevel indicating how to respond
        """
        state = self.get_state(conversation_id)

        # If we already revealed OF, stay at REVEAL level
        if state.of_revealed:
            return TensionLevel.REVEAL

        # Increment escalation count
        state.escalation_count += 1
        state.escalation_types.append(intent_name)

        # Roll the dice
        if should_reveal_of(state.escalation_count):
            state.current_level = TensionLevel.REVEAL
            state.of_revealed = True
        else:
            # Progress through tension levels
            # Level based on escalation count, capped at HINT until reveal
            if state.escalation_count == 1:
                state.current_level = TensionLevel.DEFLECT
            elif state.escalation_count == 2:
                state.current_level = TensionLevel.TEASE
            else:
                state.current_level = TensionLevel.HINT

        return state.current_level

    def record_of_pitch(self, conversation_id: str):
        """Record that we pitched the OF"""
        state = self.get_state(conversation_id)
        state.of_revealed = True
        state.conversion_state = ConversionState.PITCHED
        state.messages_since_pitch = 0

    def record_message_after_pitch(self, conversation_id: str):
        """Track messages since pitch for cold detection"""
        state = self.get_state(conversation_id)
        if state.conversion_state == ConversionState.PITCHED:
            state.messages_since_pitch += 1
            # If they've sent 3+ messages without showing interest, mark as resistant
            if state.messages_since_pitch >= 3:
                state.conversion_state = ConversionState.RESISTANT

    def record_interest(self, conversation_id: str):
        """Fan showed interest in OF"""
        state = self.get_state(conversation_id)
        state.conversion_state = ConversionState.INTERESTED

    def record_resistance(self, conversation_id: str):
        """Fan pushed back on OF"""
        state = self.get_state(conversation_id)
        state.conversion_state = ConversionState.RESISTANT

    def record_conversion(self, conversation_id: str):
        """Fan subscribed!"""
        state = self.get_state(conversation_id)
        state.conversion_state = ConversionState.CONVERTED

    def get_tension_level(self, conversation_id: str) -> TensionLevel:
        """Get current tension level for a conversation"""
        return self.get_state(conversation_id).current_level

    def get_escalation_count(self, conversation_id: str) -> int:
        """Get escalation count for a conversation"""
        return self.get_state(conversation_id).escalation_count

    def is_of_revealed(self, conversation_id: str) -> bool:
        """Check if OF has been revealed in this conversation"""
        return self.get_state(conversation_id).of_revealed

    def get_conversion_state(self, conversation_id: str) -> ConversionState:
        """Get conversion funnel state"""
        return self.get_state(conversation_id).conversion_state

    def record_objection(self, conversation_id: str):
        """
        Record that the fan objected to paying/subscribing.
        After this, we should stop mentioning OF and switch to casual chat.
        """
        state = self.get_state(conversation_id)
        state.objection_detected = True
        state.conversion_state = ConversionState.RESISTANT

    def has_objected(self, conversation_id: str) -> bool:
        """Check if fan has objected to paying/subscribing"""
        return self.get_state(conversation_id).objection_detected


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== TENSION TRACKER TEST ===\n")

    tracker = TensionTracker()

    # Simulate a conversation with multiple escalations
    conv_id = "test_conv_1"

    print("Simulating escalation sequence:")
    escalation_intents = [
        "COMPLIMENT",      # 1st escalation
        "PIC_REQUEST",     # 2nd
        "MEETUP_REQUEST",  # 3rd
        "SEXUAL",          # 4th
        "PIC_REQUEST",     # 5th
        "SEXUAL",          # 6th
    ]

    for i, intent in enumerate(escalation_intents, 1):
        level = tracker.record_escalation(conv_id, intent)
        state = tracker.get_state(conv_id)
        prob = get_reveal_probability(i) * 100
        print(f"  Escalation {i} ({intent}): {level.name} (prob was {prob:.0f}%)")

        if state.of_revealed:
            print(f"  -> OF REVEALED after {i} escalations!")
            break

    print(f"\nFinal state:")
    state = tracker.get_state(conv_id)
    print(f"  Escalation count: {state.escalation_count}")
    print(f"  Current level: {state.current_level.name}")
    print(f"  OF revealed: {state.of_revealed}")
    print(f"  Escalation types: {state.escalation_types}")

    # Run probability distribution test
    print("\n--- PROBABILITY DISTRIBUTION TEST ---")
    print("Running 1000 simulations to verify reveal distribution:\n")

    reveal_counts = {i: 0 for i in range(1, 7)}

    for _ in range(1000):
        for esc_count in range(1, 7):
            if should_reveal_of(esc_count):
                reveal_counts[esc_count] += 1
                break
        else:
            reveal_counts[6] += 1  # Count as 6 if got through all

    print("Escalation # | Expected % | Actual %")
    print("-" * 40)
    expected = [5, 10, 25, 50, 75, 90]
    for i in range(1, 7):
        actual = reveal_counts[i] / 10
        exp = expected[i-1] if i <= 5 else 90
        print(f"     {i}       |    {exp:>3}%    |   {actual:.1f}%")

    print("\n=== TEST COMPLETE ===")
