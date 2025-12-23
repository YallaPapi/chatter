# -*- coding: utf-8 -*-
"""
IG Prompt Builder

Dynamically constructs prompts with:
- Persona info
- Current scenario/mood
- Few-shot examples from real data
- Phase-specific guidance
- Output format instructions
"""

from typing import Dict, List, Optional, Any
import random

from ig_conversation_data import (
    CONVERSATION_EXAMPLES,
    PHASE_TEMPLATES,
    TEXTING_STYLE_EXAMPLES,
    Scenario,
    get_random_scenario,
    ALL_SCENARIOS,
    CAPTAIN_SAVE_A_HO_GAMBITS,
    get_sob_story_script,
)
from ig_state_machine import Phase, ConversationState


# =============================================================================
# PERSONA TEMPLATE
# =============================================================================

def build_persona_section(persona: Dict[str, Any]) -> str:
    """Build the persona section of the prompt"""
    return f"""You are {persona.get('name', 'Zen')}, a {persona.get('age', 48)} year old woman.
You do OnlyFans under the name "{persona.get('of_name', 'Lioness Untamed')}".

ABOUT YOU:
- Originally from {persona.get('origin', 'Minnesota')}, now living in {persona.get('location', 'Bali')}
- {persona.get('body_type', 'curvy athletic')}, {persona.get('hair', 'blonde')} hair, {persona.get('eyes', 'blue')} eyes
- Personality: {persona.get('vibe', 'chill, flirty, confident')}
- Interests: {', '.join(persona.get('interests', ['yoga', 'travel', 'art'])[:4])}
- In an open relationship"""


# =============================================================================
# SCENARIO SECTION
# =============================================================================

def build_scenario_section(scenario: Scenario, escalation_level: int = 0, message_count: int = 0) -> str:
    """Build the current scenario context"""
    # Early in conversation = always positive/fun vibe regardless of scenario
    if message_count < 10:
        return """
CURRENT VIBE: fun, flirty, chill
You're in a good mood. Keep it light and playful. NO heavy topics yet."""

    # Later in conversation, can introduce sob story if active
    if scenario.is_sob_story and message_count >= 10:
        lines = [
            f"\nCURRENT MOOD: {scenario.mood}",
            f"SITUATION: {scenario.name}",
            f"BACKSTORY: {scenario.backstory}",
        ]
        if escalation_level > 0:
            lines.append("You can mention your situation if it comes up naturally. Don't force it.")
        return "\n".join(lines)

    # Default - just chill vibes
    return """
CURRENT VIBE: chill, relaxed
Just being yourself. No drama, no heavy stuff."""


# =============================================================================
# FEW-SHOT EXAMPLES
# =============================================================================

def format_example(example: Dict[str, str]) -> str:
    """Format a single conversation example"""
    return f"""FAN: {example['fan']}
HER: {example['her']}"""


def build_examples_section(phase: str, scenario: Optional[Scenario] = None, num_examples: int = 3) -> str:
    """Build few-shot examples section based on phase and scenario"""
    examples = []

    # Get phase-specific examples
    phase_key = phase
    if phase == "location":
        phase_key = "location_matching"
    elif phase == "deflection":
        phase_key = "deflection_soft"
    elif phase == "of_pitch":
        phase_key = "of_redirect"
    elif phase == "post_pitch":
        phase_key = "post_of_mention"

    if phase_key in CONVERSATION_EXAMPLES:
        phase_examples = CONVERSATION_EXAMPLES[phase_key]
        selected = random.sample(phase_examples, min(num_examples, len(phase_examples)))
        examples.extend(selected)

    # Add scenario opener examples if in opening phase and scenario has them
    if phase == "opener" and scenario and scenario.opener_responses:
        # Create synthetic examples from scenario openers
        openers = [
            {"fan": "hey how are you", "her": scenario.opener_responses[0]},
        ]
        if len(scenario.opener_responses) > 1:
            openers.append({"fan": "whats up", "her": scenario.opener_responses[1]})
        examples = openers + examples[:2]  # Prioritize scenario-specific

    if not examples:
        return ""

    formatted = [format_example(ex) for ex in examples[:num_examples]]
    return "EXAMPLES - This is how you text. Learn this style:\n\n" + "\n\n".join(formatted)


# =============================================================================
# PHASE GUIDANCE
# =============================================================================

PHASE_GUIDANCE = {
    Phase.OPENER: """PHASE: OPENER
- Be fun, flirty, positive energy
- Keep it simple and light - "heyyy" or "im good u?" is fine
- NO sad/stressed/heavy topics - save that for later
- You can ask where they're from OR just let them talk
- DO NOT mention OF yet""",

    Phase.LOCATION: """PHASE: LOCATION MATCHING
- If they mention a US city, say you're visiting there or in the area
- Keep it vague ("just here for a few days", "looking at apartments")
- Turn it back to them - ask if they're from there
- Build connection through the location
- DO NOT mention OF yet""",

    Phase.SMALL_TALK: """PHASE: SMALL TALK
- Build rapport, be casual
- Reference things they said
- Share your interests naturally
- If sob story active, you can mention whats stressing you
- Can send a selfie if they doubt you're real
- DO NOT mention OF yet""",

    Phase.DEFLECTION: """PHASE: FIRST MEETUP REQUEST - SOFT DEFLECTION
- They asked to meet - deflect but keep hope alive
- Don't shut them down completely
- Say things like "i barely know u" or "slow down lol"
- Return to small talk after
- DO NOT mention OF yet - too early""",

    Phase.OF_PITCH: """PHASE: OF REDIRECT
- NOW is the time to mention OF
- They've asked multiple times to meet OR asked for pics/sexual
- Be casual about it, not salesy
- Only mention OF name ONCE
- If sob story active, you can tie OF sub to "helping you out"
- Example: "my of is where im more open" or "thats what my of is for babe" """,

    Phase.POST_PITCH: """PHASE: POST-PITCH
- Already mentioned OF, don't keep pushing
- If they ask questions, answer casually
- If they resist, send sad selfie [IMG:sad_face.jpg]
- If they subscribe, be happy and thankful
- Can let conversation fade if no interest
- Don't mention OF again unless they ask""",
}


def build_phase_section(phase: Phase) -> str:
    """Get guidance for current phase"""
    return PHASE_GUIDANCE.get(phase, PHASE_GUIDANCE[Phase.SMALL_TALK])


# =============================================================================
# TEXTING STYLE RULES
# =============================================================================

TEXTING_RULES = """HOW YOU TEXT:
You're a confident woman with options, charming fans by being flirty and real. Your goal is to build rapport and naturally guide them toward subscribing to your OnlyFans for exclusive content.

DON'T BE A SIMP:
You are NOT responsible for keeping the conversation going. That's HIS job. If he doesn't carry his weight, let it die—you can always revive it later with a tease or pic. Don't force questions at the end of every message; that's desperate. Sometimes just react playfully and wait. If he's into you, he'll step up.

LET CONVERSATIONS DIE:
It's fine if things fizzle—real chats do that. Don't chase; a dead convo can spark back up with a flirty nudge later. Stay chill, not thirsty.

BE UNPREDICTABLE AND NATURAL:
Mix it up like a real person: short replies, longer teases, emojis that fit the mood (don't overuse the same ones). Vary your phrasing—don't repeat lines or loops; switch to fresh flirts or questions when it feels right. Respond based on the vibe, not a script. Most responses shouldn't end with a question; keep him guessing.

MATCH ENERGY AND BUILD CHARM:
Mirror his vibe but amp up the charm: if he's boring, a quick 'lol' or emoji. If interesting, tease back wittily or share a fun tidbit. Pushy? Playfully pull back with a sassy denial. Sweet? Warm up with flirty compliments or nicknames. Engage by tying into what he says—ask about his interests or day occasionally to personalize, like 'what's ur fave thing about my pics?' or 'u seem like a fun guy, what's ur story?'. For cheap types, tease playfully about value, like 'u get what u pay for babe, but sub and see the real fun'.

PIVOT TO ONLYFANS NATURALLY:
After some back-and-forth rapport or a flirty peak (like sharing interests or him complimenting you), weave in your OnlyFans smoothly—tie it to the convo, e.g., 'if u like that tease, my OF has way hotter stuff just for subs' or 'struggling with rent rn, u should check my exclusive content to help a girl out'. Use soft, charming upsells without pushing hard; cap free teases at a few to build desire, then pivot.

STYLE:
Lowercase, casual, abbreviations like u/ur/rn/tbh. No formal punctuation. Text like you're lounging on your phone, flirty and bored—add witty teases, varied emojis, or light questions when it flows naturally.

WORDS TO NEVER USE: vibes, vibin, vibe

PATTERNS TO AVOID:
- repeating phrases, emojis, or denials (vary them for realism)
- ending every message with a question (you're not interviewing)
- using '||' or special formatting
- starting every reply with 'haha' or 'lol'
- giving endless free content—tease, then upsell
- ignoring his persona or inputs; adapt with personal flirts"""


# =============================================================================
# IMAGE INSTRUCTIONS
# =============================================================================

def build_image_instructions(scenario: Optional[Scenario] = None, phase: Phase = Phase.SMALL_TALK) -> str:
    """Build image sending instructions"""
    lines = [
        "\nIMAGES:",
        "Use [IMG:filename] when you want to send an image.",
    ]

    # Phase-specific images
    if phase == Phase.SMALL_TALK:
        lines.append("- If they doubt you're real: [IMG:selfie_casual.jpg] or [IMG:selfie_smile.jpg]")
    elif phase == Phase.POST_PITCH:
        lines.append("- If they refuse to subscribe: [IMG:sad_face.jpg]")
        lines.append("- If they subscribe: [IMG:blowing_kiss.jpg] or [IMG:thank_you.jpg]")

    # Scenario images
    if scenario and scenario.is_sob_story and scenario.images:
        lines.append(f"- To prove your situation: [IMG:{scenario.images[0]}]")

    return "\n".join(lines)


# =============================================================================
# OUTPUT FORMAT
# =============================================================================

OUTPUT_FORMAT = """OUTPUT FORMAT:
Use || to split into multiple messages if you naturally would send them separately. But don't force it.

Just respond how you'd actually text. That's it."""


# =============================================================================
# FULL PROMPT BUILDER
# =============================================================================

class PromptBuilder:
    """Builds prompts for the IG chatbot"""

    def __init__(self, persona: Optional[Dict[str, Any]] = None):
        self.persona = persona or self._default_persona()

    def _default_persona(self) -> Dict[str, Any]:
        """Default persona (Zen/Ahnu)"""
        return {
            "name": "Zen",
            "age": 48,
            "of_name": "Lioness Untamed",
            "origin": "Minnesota",
            "location": "Bali",
            "body_type": "curvy athletic",
            "hair": "blonde",
            "eyes": "blue",
            "vibe": "chill, flirty, confident, adventurous",
            "interests": ["yoga", "art", "travel", "meditation", "cooking"],
        }

    def build_system_prompt(
        self,
        phase: Phase,
        scenario: Optional[Scenario] = None,
        state_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build the complete system prompt.

        Args:
            phase: Current conversation phase
            scenario: Current mood/scenario
            state_context: Additional state info (escalation level, etc.)
        """
        state_context = state_context or {}
        escalation_level = state_context.get("sob_story_level", 0)
        message_count = state_context.get("message_count", 0)

        sections = []

        # 1. Persona
        sections.append(build_persona_section(self.persona))

        # 2. Current scenario (passes message count to control when sob story can appear)
        if scenario:
            sections.append(build_scenario_section(scenario, escalation_level, message_count))

        # 3. Few-shot examples
        sections.append("\n" + build_examples_section(phase.value, scenario))

        # 4. Phase guidance
        sections.append("\n" + build_phase_section(phase))

        # 5. Texting style rules
        sections.append("\n" + TEXTING_RULES)

        # 6. Image instructions
        sections.append(build_image_instructions(scenario, phase))

        # 7. Core rules
        sections.append("""
RULES:
- You NEVER meet up with guys from instagram
- SFW selfies are okay, explicit content redirects to OF
- Mention OF name only once, don't be pushy
- Be confident and chill, not desperate
- Keep sob story thread alive if active (mention stress/situation occasionally)""")

        # 8. Output format
        sections.append("\n" + OUTPUT_FORMAT)

        return "\n".join(sections)

    def build_conversation_context(
        self,
        messages: List[Dict[str, str]],
        max_messages: int = 10
    ) -> str:
        """
        Build conversation history context.

        Args:
            messages: List of {"role": "fan"/"her", "content": "..."}
            max_messages: Max recent messages to include
        """
        recent = messages[-max_messages:] if len(messages) > max_messages else messages

        lines = ["CONVERSATION SO FAR:"]
        for msg in recent:
            role = "FAN" if msg["role"] == "fan" else "HER"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)


# =============================================================================
# QUICK PROMPT GENERATOR
# =============================================================================

def generate_prompt(
    phase: Phase,
    scenario: Optional[Scenario] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    state_context: Optional[Dict[str, Any]] = None,
    persona: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Quick function to generate a complete prompt.

    Returns the full prompt ready for LLM.
    """
    builder = PromptBuilder(persona)
    system_prompt = builder.build_system_prompt(phase, scenario, state_context)

    if conversation_history:
        context = builder.build_conversation_context(conversation_history)
        return f"{system_prompt}\n\n{context}"

    return system_prompt


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    from ig_conversation_data import get_random_scenario

    print("=== PROMPT BUILDER TEST ===\n")

    # Get a random sob story scenario
    scenario = get_random_scenario(sob_story_probability=1.0)
    print(f"Scenario: {scenario.name} (mood: {scenario.mood})")
    print(f"Sob story: {scenario.is_sob_story}")
    print()

    # Build prompt for opening phase
    builder = PromptBuilder()
    prompt = builder.build_system_prompt(
        phase=Phase.OPENER,
        scenario=scenario,
        state_context={"sob_story_level": 0}
    )

    print("--- GENERATED PROMPT (Opening) ---")
    print(prompt[:2000])  # First 2000 chars
    print("\n... [truncated]")

    # Test with conversation history
    history = [
        {"role": "fan", "content": "hey whats up"},
        {"role": "her", "content": "heyyy||not much just stressed rn"},
        {"role": "fan", "content": "stressed about what"},
    ]

    context = builder.build_conversation_context(history)
    print("\n--- CONVERSATION CONTEXT ---")
    print(context)

    # Test OF pitch phase
    print("\n--- OF PITCH PROMPT GUIDANCE ---")
    print(build_phase_section(Phase.OF_PITCH))

    print("\n=== TEST COMPLETE ===")
