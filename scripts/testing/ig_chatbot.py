# -*- coding: utf-8 -*-
"""
IG Chatbot

Main chatbot class that integrates:
- State machine for phase management
- Prompt builder for dynamic few-shot prompts
- Message parser for multi-message output
- Image library for contextual images
- LLM generation (Grok/xAI)

Based on the IG Chatbot PRD.
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime

from openai import OpenAI

# Local imports
from ig_conversation_data import get_random_scenario, Scenario, ALL_SCENARIOS
from ig_state_machine import ConversationStateMachine, ConversationState, Phase
from ig_phase_prompts import get_phase_prompt  # NEW: short, phase-specific prompts
from ig_message_parser import MessageParser, ParsedMessage, enforce_length_limit
from ig_image_library import (
    get_image_for_trigger,
    detect_image_trigger,
    get_verification_image,
    get_sad_reaction,
    get_happy_reaction,
)
from ig_memory import (
    MemoryManager,
    ConversationMemory,
    ProfileExtractor,
    generate_fan_id,
)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class ChatbotConfig:
    """Configuration for the chatbot"""
    # LLM settings
    model: str = "grok-4-1-fast-non-reasoning"
    api_base: str = "https://api.x.ai/v1"
    api_key: Optional[str] = None

    # Generation settings
    max_tokens: int = 100  # Reduced - responses should be SHORT
    temperature: float = 0.9  # Higher for more variety

    # Behavior settings
    sob_story_probability: float = 0.3  # 30% chance of sob story scenario
    max_of_mentions: int = 2  # Don't mention OF more than this

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")


# =============================================================================
# MESSAGE HISTORY
# =============================================================================

@dataclass
class Message:
    """A message in the conversation"""
    role: str  # "fan" or "her"
    content: str
    images: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# MAIN CHATBOT CLASS
# =============================================================================

class IGChatbot:
    """
    Instagram DM chatbot that mimics a real woman.

    Usage:
        bot = IGChatbot()
        bot.start_conversation()
        response = bot.respond("hey whats up")
    """

    def __init__(
        self,
        config: Optional[ChatbotConfig] = None,
        persona: Optional[Dict[str, Any]] = None,
        memory_manager: Optional[MemoryManager] = None,
        fan_id: Optional[str] = None,
    ):
        self.config = config or ChatbotConfig()
        self.persona = persona or self._default_persona()

        # Initialize components
        self.state_machine = ConversationStateMachine()
        self.message_parser = MessageParser()

        # Memory system
        self.memory_manager = memory_manager or MemoryManager()
        self.profile_extractor = ProfileExtractor()
        self.fan_id = fan_id  # Set per-conversation
        self.memory: Optional[ConversationMemory] = None

        # Conversation state
        self.scenario: Optional[Scenario] = None
        self.messages: List[Message] = []

        # Initialize LLM client
        self.client = self._init_client()

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

    def _init_client(self) -> OpenAI:
        """Initialize the OpenAI-compatible client for Grok"""
        return OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.api_base,
        )

    def start_conversation(
        self,
        scenario: Optional[Scenario] = None,
        fan_id: Optional[str] = None,
        platform: str = "ig",
        username: Optional[str] = None,
    ) -> None:
        """
        Start a new conversation.

        Selects a random mood/scenario if not provided.
        Loads or creates memory for the fan.
        """
        # Reset state
        self.state_machine = ConversationStateMachine()
        self.messages = []

        # Set up fan identity and load memory
        if fan_id:
            self.fan_id = fan_id
        elif username:
            self.fan_id = generate_fan_id(platform, username)
        else:
            # Generate random fan_id for testing
            import random
            self.fan_id = generate_fan_id(platform, f"test_{random.randint(1000, 9999)}")

        # Load or create memory
        self.memory = self.memory_manager.get_or_create_memory(self.fan_id)

        # Select scenario
        if scenario:
            self.scenario = scenario
        else:
            self.scenario = get_random_scenario(self.config.sob_story_probability)

        # Initialize state machine with scenario
        self.state_machine.initialize_with_scenario(
            scenario_id=self.scenario.id,
            mood=self.scenario.mood,
            is_sob_story=self.scenario.is_sob_story,
        )

    def respond(self, fan_message: str) -> List[ParsedMessage]:
        """
        Generate a response to a fan message.

        Args:
            fan_message: The message from the fan

        Returns:
            List of ParsedMessage objects (text + optional images)
        """
        # Ensure conversation is started
        if self.scenario is None:
            self.start_conversation()

        # Ensure memory is loaded
        if self.memory is None:
            self.memory = self.memory_manager.get_or_create_memory(self.fan_id)

        # Record fan message in memory
        phase_name = self.state_machine.state.phase.value
        self.memory.add_message("fan", fan_message, phase=phase_name)

        # Extract profile info from fan message
        self.profile_extractor.extract_and_update(fan_message, self.memory)

        # Record fan message in local history
        self.messages.append(Message(role="fan", content=fan_message))

        # Update state machine
        self.state_machine.process_fan_message(fan_message)

        # COLD phase = silence (no response) unless they subscribed
        if self.state_machine.state.phase == Phase.COLD and not self.state_machine.state.fan_subscribed:
            # Silent - left on read
            self.messages.append(Message(role="her", content="", images=[]))
            self.state_machine.process_bot_response("", [])
            self.memory_manager.save_memory(self.memory)
            return []

        # Generate response
        raw_response = self._generate_response(fan_message)

        # Parse into multiple messages
        parsed_messages = self.message_parser.parse(raw_response)

        # Enforce length limits
        parsed_messages = enforce_length_limit(parsed_messages, max_words=15)

        # Post-process: add contextual images if needed
        parsed_messages = self._add_contextual_images(fan_message, parsed_messages)

        # Record our response
        combined_text = "||".join([m.text for m in parsed_messages if m.text])
        images = [m.image for m in parsed_messages if m.has_image()]
        self.messages.append(Message(role="her", content=combined_text, images=images))

        # Update memory with bot response
        self.memory.add_message("her", combined_text, phase=phase_name)
        self.memory.add_phrases_from_response(combined_text)
        self.memory.update_rapport()

        # Track OF mentions
        if "onlyfans" in combined_text.lower() or "of" in combined_text.lower().split():
            self.memory.mark_of_mentioned()

        # Save memory
        self.memory_manager.save_memory(self.memory)

        # Update state with our response
        self.state_machine.process_bot_response(combined_text, images)

        return parsed_messages

    def _generate_response(self, fan_message: str) -> str:
        """Generate raw response from LLM using phase-specific prompt"""
        # Get current phase
        phase = self.state_machine.state.phase.value

        # Build conversation history for context
        history = self._format_history_for_llm()

        # Get memory context for anti-repetition and personalization
        memory_context = None
        if self.memory:
            memory_context = self.memory.to_prompt_context()

        # Get the SHORT, FOCUSED prompt for this phase
        system_prompt = get_phase_prompt(
            phase=phase,
            last_message=fan_message,
            context={"history": history} if history else None,
            memory_context=memory_context
        )

        # Create messages for API - simpler now
        api_messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Add recent conversation history (just last 4 exchanges)
        for msg in history[-8:]:
            role = "user" if msg["role"] == "fan" else "assistant"
            api_messages.append({"role": role, "content": msg["content"]})

        # Add current message
        api_messages.append({"role": "user", "content": fan_message})

        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=api_messages,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return self._get_fallback_response()

    def _format_history_for_llm(self) -> List[Dict[str, str]]:
        """Format message history for LLM context"""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.messages[:-1]  # Exclude current message
        ]

    def _add_contextual_images(
        self,
        fan_message: str,
        messages: List[ParsedMessage]
    ) -> List[ParsedMessage]:
        """Add images based on context if AI didn't include them"""
        # Check if we should add an image
        trigger = detect_image_trigger(fan_message)

        if not trigger:
            return messages

        # Check if any message already has an image
        has_image = any(m.has_image() for m in messages)
        if has_image:
            return messages

        # Get appropriate image
        image = None
        if trigger in ["prove_real", "casual_pic"]:
            image = get_verification_image()
        elif trigger == "fan_refuses":
            image = get_sad_reaction()
        elif trigger == "fan_subscribes":
            image = get_happy_reaction()

        if image:
            # Add image to last message
            messages.append(ParsedMessage(text="", image=image))

        return messages

    def _get_fallback_response(self) -> str:
        """Get a fallback response if LLM fails"""
        phase = self.state_machine.state.phase

        fallbacks = {
            Phase.OPENER: "heyyy||whats up",
            Phase.LOCATION: "nice||u from there?",
            Phase.SMALL_TALK: "lol thats cool",
            Phase.DEFLECTION: "haha maybe||i barely know u",
            Phase.OF_PITCH: "lol i dont do that here||check my of tho",
            Phase.POST_PITCH: "its on my of babe",
            Phase.COLD: "",  # Left on read
        }

        return fallbacks.get(phase, "lol")

    def get_state(self) -> Dict[str, Any]:
        """Get current conversation state"""
        return {
            "scenario": {
                "id": self.scenario.id if self.scenario else None,
                "mood": self.scenario.mood if self.scenario else None,
                "is_sob_story": self.scenario.is_sob_story if self.scenario else False,
            },
            "phase": self.state_machine.get_phase_name(),
            "state": self.state_machine.state.to_dict(),
            "message_count": len(self.messages),
        }

    def get_conversation_log(self) -> List[Dict[str, Any]]:
        """Get full conversation log"""
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "images": msg.images,
                "timestamp": msg.timestamp,
            }
            for msg in self.messages
        ]


# =============================================================================
# INTERACTIVE TESTING
# =============================================================================

def interactive_test():
    """Run an interactive test session"""
    print("=" * 60)
    print("IG CHATBOT - Interactive Test")
    print("=" * 60)

    # Check for API key
    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    if not api_key:
        print("\nWARNING: No GROK_API_KEY or XAI_API_KEY found in environment.")
        print("Set one of these to enable LLM generation.\n")

    # Create chatbot
    config = ChatbotConfig()
    bot = IGChatbot(config=config)

    # Start conversation
    bot.start_conversation()

    print(f"\nScenario: {bot.scenario.name}")
    print(f"Mood: {bot.scenario.mood}")
    print(f"Sob story: {bot.scenario.is_sob_story}")
    print("\nType 'quit' to exit, 'state' to see state, 'log' for history")
    print("-" * 60)

    while True:
        try:
            fan_input = input("\nFan: ").strip()

            if not fan_input:
                continue

            if fan_input.lower() == 'quit':
                break

            if fan_input.lower() == 'state':
                print(json.dumps(bot.get_state(), indent=2))
                continue

            if fan_input.lower() == 'log':
                for msg in bot.get_conversation_log():
                    role = "FAN" if msg["role"] == "fan" else "HER"
                    print(f"{role}: {msg['content']}")
                    if msg.get("images"):
                        print(f"     [Images: {msg['images']}]")
                continue

            # Get response
            responses = bot.respond(fan_input)

            # Display
            for msg in responses:
                if msg.has_image():
                    if msg.text:
                        print(f"Her: {msg.text}")
                    print(f"     [IMG: {msg.image}]")
                else:
                    print(f"Her: {msg.text}")

            # Show phase
            print(f"     (phase: {bot.state_machine.get_phase_name()})")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

    print("\n" + "=" * 60)
    print("Session ended")


# =============================================================================
# BATCH TESTING
# =============================================================================

def run_test_conversation():
    """Run a scripted test conversation"""
    # Fix encoding for Windows
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 60)
    print("IG CHATBOT - Scripted Test")
    print("=" * 60)

    # Create chatbot with a specific scenario
    config = ChatbotConfig()
    bot = IGChatbot(config=config)

    # Force a sob story scenario for testing
    from ig_conversation_data import SOB_STORY_SCENARIOS
    scenario = SOB_STORY_SCENARIOS[0]  # car_accident
    bot.start_conversation(scenario)

    print(f"\nScenario: {scenario.name}")
    print(f"Mood: {scenario.mood}")
    print("-" * 60)

    # Test messages
    test_messages = [
        "hey whats up",
        "im from houston",
        "what are you up to tonight",
        "we should get drinks sometime",
        "come on let me take you out",
        "send me a pic",
    ]

    for msg in test_messages:
        print(f"\nFan: {msg}")
        responses = bot.respond(msg)

        for resp in responses:
            if resp.has_image():
                if resp.text:
                    print(f"Her: {resp.text}")
                print(f"     [IMG: {resp.image}]")
            else:
                print(f"Her: {resp.text}")

        print(f"     (phase: {bot.state_machine.get_phase_name()})")

    print("\n" + "-" * 60)
    print("Final State:")
    print(json.dumps(bot.get_state(), indent=2))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_test()
    else:
        run_test_conversation()
