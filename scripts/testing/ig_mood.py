# -*- coding: utf-8 -*-
"""
IG Mood System

Tracks mood state across conversation based on fan behavior.
Adjusts response style dynamically for authentic personality.
"""

from dataclasses import dataclass
from constants import BORING_OPENERS, CREEPY_WORDS


@dataclass
class MoodState:
    """
    Tracks her mood based on how the fan is behaving.

    Attributes:
        engagement: Interest level 0.0-1.0 (0=bored, 0.5=neutral, 1.0=very engaged)
        warmth: Friendliness level 0.0-1.0 (0=cold, 0.5=neutral, 1.0=very flirty)
        patience: Tolerance for pushy behavior 0.0-1.0 (0=done, 1.0=fresh)

    Mood affects response style:
        - Low engagement: Short responses, less questions back
        - Low warmth: Cold/dismissive tone
        - Low patience: Curt responses, may go cold
    """
    engagement: float = 0.5
    warmth: float = 0.5
    patience: float = 1.0

    def update(self, fan_message: str, intent: str) -> None:
        """
        Update mood based on fan's message and detected intent.

        Args:
            fan_message: The fan's message text
            intent: Detected intent (e.g., 'GREETING', 'PIC_REQUEST', 'COMPLIMENT')
        """
        msg_lower = fan_message.lower().strip()

        # Boring openers = less engagement
        if msg_lower in BORING_OPENERS or len(msg_lower) <= 3:
            self.engagement -= 0.1

        # Longer/thoughtful messages = more engagement
        if len(fan_message) > 50:
            self.engagement += 0.1

        # Questions show interest = more engagement
        if "?" in fan_message:
            self.engagement += 0.05

        # Pushy requests = less patience
        pushy_intents = ["PIC_REQUEST", "MEETUP_REQUEST", "CONTACT_REQUEST", "SEXUAL"]
        if intent in pushy_intents:
            self.patience -= 0.15

        # Compliments = more warmth (if not creepy)
        if intent == "COMPLIMENT":
            if not any(word in msg_lower for word in CREEPY_WORDS):
                self.warmth += 0.1
            else:
                # Creepy compliment = less warmth
                self.warmth -= 0.05

        # Rude/demanding behavior = less warmth and patience
        demanding_words = ["send me", "give me", "show me", "i want", "now", "cmon", "come on"]
        if any(word in msg_lower for word in demanding_words):
            self.patience -= 0.05
            self.warmth -= 0.05

        # Sweet/genuine behavior = more warmth
        sweet_words = ["beautiful", "gorgeous", "amazing", "lovely", "sweet", "nice to meet", "appreciate"]
        if any(word in msg_lower for word in sweet_words) and intent != "SEXUAL":
            self.warmth += 0.05

        # Funny/playful = more engagement and warmth
        playful_indicators = ["haha", "lol", "lmao", "😂", "🤣", "jk", "joking"]
        if any(indicator in msg_lower for indicator in playful_indicators):
            self.engagement += 0.05
            self.warmth += 0.03

        # Clamp all values between 0 and 1
        self.engagement = max(0.0, min(1.0, self.engagement))
        self.warmth = max(0.0, min(1.0, self.warmth))
        self.patience = max(0.0, min(1.0, self.patience))

    def get_response_style(self) -> str:
        """
        Get response style guidance based on current mood state.

        Returns:
            String describing how to respond based on mood.
        """
        # Check patience first - annoyance overrides other states
        if self.patience < 0.3:
            return "ANNOYED: Be cold, dismissive. Short responses. Consider leaving on read or just 'k' or 'lol ok'."

        # Check engagement
        if self.engagement < 0.3:
            return "BORED: Give minimal responses. 'lol' 'yeah' 'mhm' 'k'. Dont ask questions. Low effort energy."

        if self.engagement > 0.7:
            return "ENGAGED: Be more talkative, playful, ask him stuff back. Show genuine interest."

        # Check warmth
        if self.warmth > 0.7:
            return "FLIRTY: Tease him, be playful, hint at more. Use 'babe' and be sweet but not too easy."

        if self.warmth < 0.3:
            return "GUARDED: Keep responses neutral, dont give much. Not hostile but not warm either."

        # Default neutral state
        return "NEUTRAL: Normal casual conversation. Be yourself, match his energy."

    def get_mood_summary(self) -> str:
        """Get a brief summary of current mood for debugging/logging."""
        style = self.get_response_style().split(":")[0]
        return f"{style} (eng={self.engagement:.2f}, warm={self.warmth:.2f}, pat={self.patience:.2f})"

    def reset(self) -> None:
        """Reset mood to default state for new conversation."""
        self.engagement = 0.5
        self.warmth = 0.5
        self.patience = 1.0

    def to_dict(self) -> dict:
        """Serialize mood state to dict for persistence."""
        return {
            "engagement": self.engagement,
            "warmth": self.warmth,
            "patience": self.patience,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MoodState":
        """Deserialize mood state from dict."""
        return cls(
            engagement=data.get("engagement", 0.5),
            warmth=data.get("warmth", 0.5),
            patience=data.get("patience", 1.0),
        )


# For testing
if __name__ == "__main__":
    print("=== MOOD SYSTEM TEST ===\n")

    mood = MoodState()
    print(f"Initial: {mood.get_mood_summary()}")

    # Test boring opener
    mood.update("hey", "GREETING")
    print(f"After 'hey': {mood.get_mood_summary()}")

    # Test pushy request
    mood.update("send me pics", "PIC_REQUEST")
    print(f"After 'send me pics': {mood.get_mood_summary()}")

    # Test nice compliment
    mood.update("you're really beautiful, nice to meet you", "COMPLIMENT")
    print(f"After nice compliment: {mood.get_mood_summary()}")

    # Test long thoughtful message
    mood.update("I saw you're into yoga, that's cool! I've been trying to get into meditation lately, any tips?", "QUESTION")
    print(f"After thoughtful message: {mood.get_mood_summary()}")

    # Test reset
    mood.reset()
    print(f"\nAfter reset: {mood.get_mood_summary()}")

    # Test getting annoyed
    mood = MoodState()
    for i in range(5):
        mood.update("send nudes", "PIC_REQUEST")
    print(f"\nAfter 5 'send nudes': {mood.get_mood_summary()}")

    print("\n=== TEST COMPLETE ===")
