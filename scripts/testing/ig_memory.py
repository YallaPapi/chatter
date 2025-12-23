# -*- coding: utf-8 -*-
"""
Conversation Memory System

Persistent per-fan memory for the IG chatbot that stores:
- Conversation history
- Used phrases (for anti-repetition)
- Fan profile (extracted info)
- Conversation state

Based on the Memory System PRD.
"""

import json
import hashlib
import difflib
import re
from pathlib import Path
from dataclasses import dataclass, field, fields, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any


# =============================================================================
# UTILITIES
# =============================================================================

def now_iso() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()


def generate_fan_id(platform: str, username: str) -> str:
    """Generate unique 16-char fan ID from platform:username"""
    return hashlib.sha256(f'{platform}:{username}'.encode()).hexdigest()[:16]


# =============================================================================
# CONVERSATION MEMORY DATACLASS
# =============================================================================

@dataclass
class ConversationMemory:
    """
    Memory for a single fan conversation.

    Stores messages, used phrases, fan profile, and state.
    Auto-trims to prevent unbounded growth.
    """
    fan_id: str
    created_at: str = field(default_factory=now_iso)
    last_active: str = field(default_factory=now_iso)

    # Message history (capped at 100)
    messages: List[Dict[str, str]] = field(default_factory=list)

    # Phrases bot has used (capped at 50, for anti-repetition)
    used_phrases: List[str] = field(default_factory=list)

    # Extracted fan info
    fan_profile: Dict[str, Any] = field(default_factory=lambda: {
        "name": None,
        "location": None,
        "interests": [],
        "job": None,
        "age": None,
        "relationship_status": None,
        "platform_preferences": [],
    })

    # Conversation state
    state: Dict[str, Any] = field(default_factory=lambda: {
        "phase": "opener",
        "of_mentioned": False,
        "of_subscribed": False,
        "meetup_requests": 0,
        "rapport_level": 1,
        "conversation_count": 0,
    })

    # Topics already discussed
    topics_covered: List[str] = field(default_factory=list)

    # -------------------------------------------------------------------------
    # MESSAGE METHODS
    # -------------------------------------------------------------------------

    def add_message(
        self,
        role: str,
        content: str,
        timestamp: Optional[str] = None,
        phase: Optional[str] = None
    ) -> None:
        """Add a message to history, auto-trim to 100"""
        msg = {
            "role": role,
            "content": content,
            "timestamp": timestamp or now_iso(),
        }
        if phase:
            msg["phase"] = phase

        self.messages.append(msg)
        self.messages = self.messages[-100:]  # Keep last 100
        self.last_active = now_iso()

        # Increment conversation count
        if role == "fan":
            self.state["conversation_count"] += 1

    def get_recent_messages(self, n: int = 10) -> List[Dict[str, str]]:
        """Get last n messages"""
        return self.messages[-n:] if self.messages else []

    # -------------------------------------------------------------------------
    # PHRASE TRACKING (Anti-Repetition)
    # -------------------------------------------------------------------------

    def add_phrase(self, phrase: str) -> bool:
        """
        Add phrase if not too similar to existing ones.
        Returns True if added, False if skipped (duplicate).
        """
        normalized = phrase.lower().strip()
        if not normalized:
            return False

        # Check for similarity with existing phrases
        for existing in self.used_phrases:
            similarity = difflib.SequenceMatcher(None, normalized, existing).ratio()
            if similarity > 0.8:
                return False  # Too similar, skip

        self.used_phrases.append(normalized)
        self.used_phrases = self.used_phrases[-50:]  # Keep last 50
        self.last_active = now_iso()
        return True

    def add_phrases_from_response(self, response: str) -> None:
        """Extract and add phrases from a bot response"""
        # Split by common delimiters
        parts = re.split(r'[.!?|]+', response)
        for part in parts[:5]:  # Max 5 phrases per response
            phrase = part.strip()
            if len(phrase) > 3:  # Skip very short fragments
                self.add_phrase(phrase)

    def get_recent_phrases(self, n: int = 15) -> List[str]:
        """Get last n used phrases"""
        return self.used_phrases[-n:] if self.used_phrases else []

    # -------------------------------------------------------------------------
    # PROFILE METHODS
    # -------------------------------------------------------------------------

    def update_profile(self, key: str, value: Any) -> None:
        """Update a fan profile field"""
        if value is not None:
            self.fan_profile[key] = value
            self.last_active = now_iso()

            # Track topic covered
            topic = self._extract_topic(key)
            if topic and topic not in self.topics_covered:
                self.topics_covered.append(topic)
                self.topics_covered = self.topics_covered[-10:]  # Cap at 10

    def _extract_topic(self, key: str) -> Optional[str]:
        """Map profile key to topic category"""
        topic_map = {
            "name": "personal",
            "age": "personal",
            "location": "location",
            "job": "work",
            "interests": "hobbies",
            "relationship_status": "relationship",
        }
        return topic_map.get(key, key)

    def get_profile_summary(self) -> str:
        """Get human-readable profile summary"""
        parts = []
        for key, value in self.fan_profile.items():
            if value:
                if isinstance(value, list) and value:
                    parts.append(f"{key}: {', '.join(value)}")
                elif not isinstance(value, list):
                    parts.append(f"{key}: {value}")
        return "; ".join(parts) if parts else ""

    # -------------------------------------------------------------------------
    # STATE METHODS
    # -------------------------------------------------------------------------

    def update_state(self, **kwargs) -> None:
        """Update state fields"""
        for key, value in kwargs.items():
            if key in self.state:
                self.state[key] = value
        self.last_active = now_iso()

    def increment_meetup_requests(self) -> None:
        """Track meetup request"""
        self.state["meetup_requests"] = self.state.get("meetup_requests", 0) + 1

    def mark_of_mentioned(self) -> None:
        """Mark that OF was mentioned"""
        self.state["of_mentioned"] = True

    def mark_subscribed(self) -> None:
        """Mark that fan subscribed"""
        self.state["of_subscribed"] = True

    def update_rapport(self) -> None:
        """Increment rapport based on conversation count"""
        count = self.state.get("conversation_count", 0)
        # Increase rapport every 3 messages, cap at 5
        new_rapport = min(5, 1 + (count // 3))
        self.state["rapport_level"] = new_rapport

    # -------------------------------------------------------------------------
    # SERIALIZATION
    # -------------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "fan_id": self.fan_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "messages": self.messages,
            "used_phrases": self.used_phrases,
            "fan_profile": self.fan_profile,
            "state": self.state,
            "topics_covered": self.topics_covered,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationMemory":
        """Create from dictionary"""
        memory = cls(fan_id=data["fan_id"])
        memory.created_at = data.get("created_at", now_iso())
        memory.last_active = data.get("last_active", now_iso())
        memory.messages = data.get("messages", [])
        memory.used_phrases = data.get("used_phrases", [])
        memory.fan_profile = data.get("fan_profile", memory.fan_profile)
        memory.state = data.get("state", memory.state)
        memory.topics_covered = data.get("topics_covered", [])
        return memory

    # -------------------------------------------------------------------------
    # PROMPT CONTEXT
    # -------------------------------------------------------------------------

    def to_prompt_context(self) -> str:
        """Generate context string for injection into prompts"""
        parts = []

        # Anti-repetition
        phrases = self.get_recent_phrases(15)
        if phrases:
            parts.append(f"DONT REPEAT these phrases: {', '.join(phrases)}")

        # Fan profile
        profile_summary = self.get_profile_summary()
        if profile_summary:
            parts.append(f"You know about him: {profile_summary}")

        # Topics covered
        if self.topics_covered:
            parts.append(f"Topics already discussed: {', '.join(self.topics_covered)}")

        # Rapport level
        rapport = self.state.get("rapport_level", 1)
        if rapport >= 3:
            parts.append("You've built some rapport - can be slightly warmer")

        return "\n".join(parts)


# =============================================================================
# PROFILE EXTRACTOR
# =============================================================================

class ProfileExtractor:
    """
    Extract fan information from messages using regex patterns.
    """

    def __init__(self):
        # Compile patterns (case-insensitive)
        self.patterns = {
            "name": re.compile(
                r"(?:my name is|call me|i'm|i am|name's|names)\s+([A-Za-z]+)",
                re.IGNORECASE
            ),
            "location": re.compile(
                r"(?:i'm from|im from|i live in|from|in|based in)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
                re.IGNORECASE
            ),
            "age": re.compile(
                r"\b(\d{2})\s*(?:years?\s*old|yo|y\.o\.?|age)",
                re.IGNORECASE
            ),
            "job": re.compile(
                r"(?:i work as|work as|i'm a|im a|i am a|job is|do for work)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)",
                re.IGNORECASE
            ),
            "interests": re.compile(
                r"(?:i love|i like|i enjoy|into|fan of|hobby is)\s+([A-Za-z]+(?:ing)?(?:\s+and\s+[A-Za-z]+(?:ing)?)?)",
                re.IGNORECASE
            ),
        }

    def extract(self, message: str) -> Dict[str, Any]:
        """
        Extract profile info from a message.
        Returns dict with extracted fields (only non-None values).
        """
        extracted = {}

        for field_name, pattern in self.patterns.items():
            match = pattern.search(message)
            if match:
                value = match.group(1).strip()

                # Normalize values
                if field_name == "age":
                    try:
                        value = int(value)
                    except ValueError:
                        continue
                elif field_name == "interests":
                    value = value.lower()
                elif field_name in ("name", "location", "job"):
                    value = value.title()

                extracted[field_name] = value

        return extracted

    def extract_and_update(self, message: str, memory: ConversationMemory) -> Dict[str, Any]:
        """Extract from message and update memory profile"""
        extracted = self.extract(message)
        for key, value in extracted.items():
            if key == "interests":
                # Append to interests list
                current = memory.fan_profile.get("interests", [])
                if value not in current:
                    current.append(value)
                    memory.update_profile("interests", current)
            else:
                memory.update_profile(key, value)
        return extracted


# =============================================================================
# MEMORY MANAGER
# =============================================================================

class MemoryManager:
    """
    Handles persistence of ConversationMemory objects.

    Stores one JSON file per fan in data/memories/{fan_id}.json
    Maintains index.json for quick lookups.
    """

    def __init__(self, memories_dir: Optional[str] = None):
        if memories_dir:
            self.memories_dir = Path(memories_dir)
        else:
            # Default: data/memories relative to this file's location
            self.memories_dir = Path(__file__).parent.parent.parent / "data" / "memories"

        # Ensure directory exists
        self.memories_dir.mkdir(parents=True, exist_ok=True)

        # Initialize index if not exists
        self.index_path = self.memories_dir / "index.json"
        if not self.index_path.exists():
            self._save_index({})

    def _load_index(self) -> Dict[str, Dict[str, str]]:
        """Load the fan index"""
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_index(self, index: Dict[str, Dict[str, str]]) -> None:
        """Save the fan index atomically"""
        tmp_path = self.index_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
        tmp_path.replace(self.index_path)

    def get_memory(self, fan_id: str) -> Optional[ConversationMemory]:
        """Load memory for a fan, or return None if not exists"""
        file_path = self.memories_dir / f"{fan_id}.json"

        if not file_path.exists():
            return None

        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return ConversationMemory.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading memory for {fan_id}: {e}")
            return None

    def get_or_create_memory(self, fan_id: str) -> ConversationMemory:
        """Get existing memory or create new one"""
        memory = self.get_memory(fan_id)
        if memory is None:
            memory = ConversationMemory(fan_id=fan_id)
        return memory

    def save_memory(self, memory: ConversationMemory) -> None:
        """Save memory atomically"""
        file_path = self.memories_dir / f"{memory.fan_id}.json"
        tmp_path = file_path.with_suffix(".tmp")

        # Write to temp file
        tmp_path.write_text(
            json.dumps(memory.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # Atomic rename
        tmp_path.replace(file_path)

        # Update index
        index = self._load_index()
        index[memory.fan_id] = {
            "created_at": memory.created_at,
            "last_active": memory.last_active,
        }
        self._save_index(index)

    def delete_memory(self, fan_id: str) -> bool:
        """Delete a fan's memory"""
        file_path = self.memories_dir / f"{fan_id}.json"

        if file_path.exists():
            file_path.unlink()

            # Remove from index
            index = self._load_index()
            if fan_id in index:
                del index[fan_id]
                self._save_index(index)

            return True
        return False

    def list_all_fans(self) -> List[str]:
        """Get list of all fan IDs"""
        index = self._load_index()
        return sorted(index.keys())

    def get_fan_count(self) -> int:
        """Get total number of fans with memories"""
        return len(self._load_index())


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== MEMORY SYSTEM TEST ===\n")

    # Test fan ID generation
    fan_id = generate_fan_id("ig", "testuser123")
    print(f"Generated fan_id: {fan_id} (len={len(fan_id)})")

    # Test memory creation
    memory = ConversationMemory(fan_id=fan_id)
    print(f"\nNew memory created: {memory.fan_id}")

    # Test message adding
    memory.add_message("fan", "hey whats up")
    memory.add_message("her", "heyyy not much wbu")
    memory.add_message("fan", "im from houston")
    print(f"Messages: {len(memory.messages)}")

    # Test phrase tracking
    memory.add_phrases_from_response("heyyy not much wbu")
    memory.add_phrases_from_response("lol thats cool||where u at")
    print(f"Phrases tracked: {memory.used_phrases}")

    # Test profile extraction
    extractor = ProfileExtractor()
    extracted = extractor.extract("My name is Jake and I'm from Austin")
    print(f"Extracted: {extracted}")

    extractor.extract_and_update("I'm 28 years old and love hiking", memory)
    print(f"Profile: {memory.fan_profile}")

    # Test prompt context
    context = memory.to_prompt_context()
    print(f"\nPrompt context:\n{context}")

    # Test serialization
    data = memory.to_dict()
    restored = ConversationMemory.from_dict(data)
    print(f"\nSerialization test: {restored.fan_id == memory.fan_id}")

    # Test MemoryManager
    print("\n--- MemoryManager Test ---")
    manager = MemoryManager()

    # Save
    manager.save_memory(memory)
    print(f"Saved memory for {memory.fan_id}")

    # Load
    loaded = manager.get_memory(fan_id)
    print(f"Loaded: {loaded.fan_id if loaded else 'None'}")
    print(f"Messages: {len(loaded.messages) if loaded else 0}")

    # List fans
    fans = manager.list_all_fans()
    print(f"All fans: {fans}")

    # Cleanup test data
    manager.delete_memory(fan_id)
    print(f"Deleted test memory")

    print("\n=== TEST COMPLETE ===")
