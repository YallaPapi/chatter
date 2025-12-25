# -*- coding: utf-8 -*-
"""
Intent-Based Prompt Builder

Builds LLM prompts based on:
- Detected intent (what fan is doing NOW)
- Tension level (how to respond to escalation)
- Conversation context
"""

from typing import List
import random

from ig_intent_detector import detect_intent, is_escalation, Intent
from ig_tension_tracker import TensionTracker, TensionLevel, ConversionState
from ig_response_templates import get_template, format_template_for_prompt, POST_REVEAL_TEMPLATES, PROACTIVE_OF_TEMPLATES
from ig_persona import DEFAULT_PERSONA, TEMPLATES, PERSONAL_HOOKS, get_random_personal_hook
from ig_mood import MoodState


# =============================================================================
# RESPONSE EXAMPLES FROM PERSONA TEMPLATES
# =============================================================================

def get_response_examples(intent_name: str, tension_level: TensionLevel) -> List[str]:
    """
    Get example responses from persona TEMPLATES based on context.

    Used for few-shot prompting to ensure Zen's actual voice is used.

    Args:
        intent_name: The detected intent (e.g., 'MEETUP_REQUEST', 'PIC_REQUEST')
        tension_level: Current tension level

    Returns:
        List of 2-3 example response strings
    """
    examples = []

    # Meetup requests - use deflection templates based on tension
    if intent_name == "MEETUP_REQUEST":
        if tension_level == TensionLevel.DEFLECT:
            examples = TEMPLATES.get("meetup_deflect_soft", [])
        elif tension_level == TensionLevel.HINT:
            examples = TEMPLATES.get("meetup_deflect_medium", [])
        else:  # REVEAL or higher
            examples = TEMPLATES.get("of_redirect", [])

    # Pic requests and sexual escalation
    elif intent_name in ["PIC_REQUEST", "SEXUAL"]:
        if tension_level == TensionLevel.REVEAL:
            examples = TEMPLATES.get("sexual_redirect", [])
        else:
            examples = TEMPLATES.get("of_redirect", [])

    # Contact requests (snap, number, etc.)
    elif intent_name == "CONTACT_REQUEST":
        if tension_level.value >= TensionLevel.REVEAL.value:
            examples = TEMPLATES.get("of_redirect", [])
        else:
            examples = TEMPLATES.get("meetup_deflect_medium", [])

    # Small talk / location
    elif intent_name == "LOCATION":
        examples = TEMPLATES.get("location_responses", [])

    elif intent_name in ["QUESTION", "SMALL_TALK"]:
        examples = TEMPLATES.get("small_talk", [])

    # Post-pitch scenarios
    elif intent_name == "SUBSCRIBED":
        examples = ["omg yay babe", "hehe welcome", "u wont regret it"]

    elif intent_name == "OF_QUESTION":
        examples = TEMPLATES.get("post_of", [])

    # Default - return empty, will use template system
    if not examples:
        return []

    # Return 2-3 random examples
    num_examples = min(3, len(examples))
    return random.sample(examples, num_examples) if len(examples) > num_examples else examples


# =============================================================================
# PHRASE BLOCKLIST - Common overused phrases to NEVER repeat
# =============================================================================

PHRASE_BLOCKLIST = [
    "believe what u want",
    "think what u want",
    "whatever u say",
    "check my profile",
    "anyway whats up",
    "so whats up",
    "lol anyway",
    "haha anyway",
    "wyd tho",
    "whats ur deal",
    "thats cool",
    "oh nice",
    "haha true",
    "lol true",
    "fair enough",
    "spill babe",
    "spill deets",
    "spill the deets",
    "tell me more babe",
]

# Variety guidance - rotate these instead of repeating same ones
NICKNAME_VARIETY = ["babe", "cutie", "hun", "love", ""]  # Empty = no nickname
ENDER_VARIETY = ["what about u", "u?", "wbu", "hbu", "ur turn", ""]  # Different question enders


def build_anti_repetition_section(recent_phrases: list = None) -> str:
    """Build anti-repetition section - COMPACT"""
    section = """IMPORTANT - SOUND HUMAN:
- STAY ON TOPIC. If he's flirty, be flirty back. If he's casual, be casual.
- Do NOT pivot to random questions like "what do u do for work" mid-flirt
- Sometimes just react: "lol", "damn", "nice", "thats crazy"
- Not every message needs a question at the end"""
    if recent_phrases and len(recent_phrases) > 0:
        section += f"\nRecent phrases to skip: {recent_phrases[:8]}"
    return section


# =============================================================================
# CORE RULES (appended to persona prompt)
# =============================================================================

CORE_RULES = """FORMAT: Use || to split messages. NO emojis.

RULES:
- Stay consistent. If you said no, stick with it.
- NEVER agree to meetup. Deflect or change subject.
- NEVER deny having OF. Just dont spam it.
- If skeptical: send selfie with [IMG:selfie]"""


# =============================================================================
# INTENT-BASED PROMPT BUILDER
# =============================================================================

class IntentPromptBuilder:
    """
    Builds prompts based on detected intent and tension level.

    Replaces phase-based prompts with intent-based approach.
    Now includes persona integration and mood tracking.
    """

    def __init__(self):
        self.tension_tracker = TensionTracker()
        self.persona = DEFAULT_PERSONA
        self.mood_states: dict[str, MoodState] = {}  # conversation_id -> MoodState

    def get_mood(self, conversation_id: str) -> MoodState:
        """Get or create mood state for a conversation."""
        if conversation_id not in self.mood_states:
            self.mood_states[conversation_id] = MoodState()
        return self.mood_states[conversation_id]

    def reset_mood(self, conversation_id: str) -> None:
        """Reset mood for a new conversation."""
        if conversation_id in self.mood_states:
            self.mood_states[conversation_id].reset()
        else:
            self.mood_states[conversation_id] = MoodState()

    def build_prompt(
        self,
        fan_message: str,
        conversation_id: str,
        memory_context: str = None,
        of_link: str = "linktr.ee/yourof",
    ) -> tuple[str, Intent, TensionLevel]:
        """
        Build the system prompt for the LLM.

        Args:
            fan_message: The fan's message
            conversation_id: Unique ID for this conversation
            memory_context: Optional memory/anti-repetition context
            of_link: The OF link to use when revealing

        Returns:
            Tuple of (prompt_string, detected_intent, tension_level)
        """
        # Detect what the fan is doing
        intent = detect_intent(fan_message)

        # Get current tension state
        state = self.tension_tracker.get_state(conversation_id)

        # Track message count for proactive pitch timing
        state.message_count += 1

        # Update rapport score based on fan's message
        self._update_rapport_score(state, intent, fan_message)

        # Handle OBJECTION intent - record it and stop OF mentions
        if intent.name == "OBJECTION":
            self.tension_tracker.record_objection(conversation_id)

        # Handle escalation intents
        if is_escalation(intent):
            tension_level = self.tension_tracker.record_escalation(
                conversation_id, intent.name
            )
        else:
            tension_level = state.current_level

        # Get and update mood for this conversation
        mood = self.get_mood(conversation_id)
        mood.update(fan_message, intent.name)

        # Extract recent phrases for anti-repetition (if memory_context exists)
        recent_phrases = []
        if memory_context and "NEVER repeat" in memory_context:
            # Extract phrases from memory context
            import re
            match = re.search(r"NEVER repeat these exact phrases[^:]*:\s*([^.]+)", memory_context)
            if match:
                phrases_str = match.group(1)
                recent_phrases = [p.strip() for p in phrases_str.split(",") if p.strip()]

        # Build the prompt - ANTI-REPETITION AT TOP
        prompt_parts = [build_anti_repetition_section(recent_phrases)]

        # Add persona
        prompt_parts.append(self.persona.to_prompt())

        # Add core rules
        prompt_parts.append(CORE_RULES)

        # Add current mood guidance
        mood_style = mood.get_response_style()
        prompt_parts.append(f"\nCURRENT MOOD: {mood_style}")

        # Add personal hook occasionally for bored/neutral moods (30% chance)
        if mood.engagement < 0.6 and random.random() < 0.3:
            hook_type = "bored_fillers" if mood.engagement < 0.4 else "personality_moments"
            hook = get_random_personal_hook(hook_type)
            if hook:
                prompt_parts.append(f'\nOCCASIONALLY MENTION: "{hook}" (only if it fits naturally)')

        # Add memory context if available
        if memory_context:
            prompt_parts.append(f"\n{memory_context}")

        # Add intent-specific guidance
        prompt_parts.append(self._build_intent_section(intent, tension_level, of_link))

        # Check if we should nudge OF mention (after 4+ messages, not yet mentioned)
        if self._should_proactive_pitch(state, mood, intent, fan_message):
            prompt_parts.append(self._build_proactive_pitch_section(intent, fan_message))
            state.proactive_pitch_suggested = True

        # Add post-reveal context if applicable
        if state.of_revealed:
            prompt_parts.append(self._build_post_reveal_section(intent))

        # If fan objected, ease off but don't ban OF entirely
        if state.objection_detected:
            prompt_parts.append(self._build_objection_section())

        return "\n\n".join(prompt_parts), intent, tension_level

    def _build_intent_section(
        self,
        intent: Intent,
        tension_level: TensionLevel,
        of_link: str,
    ) -> str:
        """Build the intent-specific section of the prompt"""
        template = get_template(tension_level, intent.name)

        section = f"""
CURRENT SITUATION:
The fan just sent a {intent.name.replace('_', ' ').lower()} type message.
Confidence: {intent.confidence:.0%}

YOUR RESPONSE APPROACH:
{format_template_for_prompt(template)}"""

        # Add 1 example from persona templates (reduced for token efficiency)
        examples = get_response_examples(intent.name, tension_level)
        if examples:
            section += f'\nExample vibe: "{examples[0]}"'

        # Add OF link for reveal level
        if tension_level == TensionLevel.REVEAL:
            section += f"\n\nYour OF link: {of_link}"

        return section

    def _update_rapport_score(self, state, intent, fan_message: str) -> None:
        """
        Update rapport score based on fan's intent and message.

        Rapport accumulates from positive interactions:
        - COMPLIMENT: +0.5
        - QUESTION (about her): +0.3
        - SMALL_TALK (engaged): +0.2
        - Long messages (>50 chars): +0.2
        - Positive signals (haha, lol, emoji): +0.1
        """
        score_delta = 0.0

        # Intent-based scoring
        if intent.name == "COMPLIMENT":
            score_delta += 0.5
        elif intent.name == "QUESTION":
            score_delta += 0.3
        elif intent.name == "SMALL_TALK":
            score_delta += 0.2
        elif intent.name == "GREETING":
            score_delta += 0.1

        # Message quality scoring
        if len(fan_message) > 50:
            score_delta += 0.2

        # Positive mood signals
        positive_signals = ["haha", "lol", "lmao", "😂", "😍", "🔥", "❤", "😊"]
        if any(signal in fan_message.lower() for signal in positive_signals):
            score_delta += 0.1

        # Update score with cap at 10.0
        state.rapport_score = min(state.rapport_score + score_delta, 10.0)

    def _should_proactive_pitch(self, state, mood, intent, fan_message: str) -> bool:
        """
        Simple check: should we remind her to mention OF?

        Just a gentle nudge after 4+ messages if she hasn't yet.
        The persona already knows OF is part of her life - this just reminds her.
        """
        # Don't remind if OF already mentioned or fan objected
        if state.of_revealed or state.objection_detected or state.proactive_pitch_suggested:
            return False

        # After 4 messages, gently remind her OF exists
        if state.message_count >= 4:
            return True

        return False

    def _build_proactive_pitch_section(self, intent, fan_message: str) -> str:
        """Direct reminder to mention OF."""
        return """
>>> MENTION YOUR OF IN THIS RESPONSE <<<
You have an OnlyFans (lioness untamed). Mention it NOW in this response.
Say something like: "yeah i post a lot of that on my of" or "got more on my of if ur curious"
Keep it casual but DEFINITELY mention it."""

    def _build_objection_section(self) -> str:
        """Build section when fan has objected to paying/subscribing"""
        return """
FAN SAID NO TO OF:
They're not interested in subscribing. That's fine.
- Don't push it or try to convince them
- Just keep chatting normally
- If it comes up naturally later, one casual mention is ok
- Focus on having a fun conversation"""

    def _build_post_reveal_section(self, intent: Intent) -> str:
        """Build section for after OF has been revealed"""
        # Determine which post-reveal template to use
        if intent.name == "SUBSCRIBED":
            template = POST_REVEAL_TEMPLATES["SUBSCRIBED"]
            section_name = "They subscribed!"
        elif intent.name in ["OF_QUESTION"]:
            template = POST_REVEAL_TEMPLATES["INTERESTED"]
            section_name = "They're interested in OF"
        elif intent.name in ["HOSTILE", "SKEPTICAL"]:
            template = POST_REVEAL_TEMPLATES["RESISTANT"]
            section_name = "They're resistant"
        else:
            # Default post-reveal behavior - engage naturally
            return """
You mentioned OF already. Don't spam it.
- Keep the conversation going naturally about whatever they're interested in
- If they ask for free stuff, playfully decline but stay engaged
- NEVER say "told u already" - sounds robotic
- Keep flirting/chatting, don't just pivot to "where u from" randomly"""

        return f"""
POST-REVEAL: {section_name}
Vibe: {template['vibe']}
Goal: {template['goal']}
Example responses: {', '.join(template['examples'][:2])}
IMPORTANT: Do not spam the OF link. One mention is enough."""

    def record_subscription(self, conversation_id: str):
        """Record that fan subscribed"""
        self.tension_tracker.record_conversion(conversation_id)

    def get_stats(self, conversation_id: str) -> dict:
        """Get stats for debugging"""
        state = self.tension_tracker.get_state(conversation_id)
        mood = self.get_mood(conversation_id)
        return {
            "escalation_count": state.escalation_count,
            "tension_level": state.current_level.name,
            "of_revealed": state.of_revealed,
            "objection_detected": state.objection_detected,
            "conversion_state": state.conversion_state.value,
            "escalation_types": state.escalation_types,
            "mood": mood.get_mood_summary(),
            "mood_state": mood.to_dict(),
        }

    def has_objected(self, conversation_id: str) -> bool:
        """Check if fan has objected to paying"""
        return self.tension_tracker.has_objected(conversation_id)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== INTENT PROMPT BUILDER TEST ===\n")

    builder = IntentPromptBuilder()
    conv_id = "test_conv"

    test_sequence = [
        "hey whats up",
        "you're so hot",
        "send me a pic",
        "come on just one",
        "lets meet up",
        "whats your snap",
    ]

    for msg in test_sequence:
        print(f'Fan: "{msg}"')
        prompt, intent, level = builder.build_prompt(msg, conv_id)

        stats = builder.get_stats(conv_id)
        print(f"  Intent: {intent.name} ({intent.confidence:.0%})")
        print(f"  Tension: {level.name}")
        print(f"  Escalation count: {stats['escalation_count']}")
        print(f"  OF revealed: {stats['of_revealed']}")
        print()

        # Show the guidance section only
        if "YOUR RESPONSE APPROACH:" in prompt:
            approach = prompt.split("YOUR RESPONSE APPROACH:")[1]
            if "POST-REVEAL:" in approach:
                approach = approach.split("POST-REVEAL:")[0]
            print(f"  Guidance:{approach[:200]}...")
        print("-" * 50)

    print("\n=== TEST COMPLETE ===")
