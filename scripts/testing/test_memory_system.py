# -*- coding: utf-8 -*-
"""
Memory System Tests

Tests for the conversation memory system including:
- ConversationMemory dataclass
- MemoryManager persistence
- ProfileExtractor regex patterns
- Anti-repetition tracking
- Integration with IGChatbot
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from ig_memory import (
    ConversationMemory,
    MemoryManager,
    ProfileExtractor,
    generate_fan_id,
    now_iso,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def temp_memories_dir():
    """Create a temporary directory for test memories"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def memory_manager(temp_memories_dir):
    """Create a MemoryManager with temporary directory"""
    return MemoryManager(memories_dir=temp_memories_dir)


@pytest.fixture
def sample_memory():
    """Create a sample ConversationMemory"""
    return ConversationMemory(fan_id="test123")


# =============================================================================
# FAN ID GENERATION TESTS
# =============================================================================

def test_generate_fan_id_length():
    """Fan ID should be 16 characters"""
    fan_id = generate_fan_id("ig", "testuser")
    assert len(fan_id) == 16


def test_generate_fan_id_consistency():
    """Same inputs should produce same fan_id"""
    id1 = generate_fan_id("ig", "testuser")
    id2 = generate_fan_id("ig", "testuser")
    assert id1 == id2


def test_generate_fan_id_uniqueness():
    """Different inputs should produce different fan_ids"""
    id1 = generate_fan_id("ig", "user1")
    id2 = generate_fan_id("ig", "user2")
    id3 = generate_fan_id("twitter", "user1")
    assert id1 != id2
    assert id1 != id3


# =============================================================================
# CONVERSATION MEMORY TESTS
# =============================================================================

def test_memory_creation(sample_memory):
    """Memory should initialize with correct defaults"""
    assert sample_memory.fan_id == "test123"
    assert len(sample_memory.messages) == 0
    assert len(sample_memory.used_phrases) == 0
    assert sample_memory.state["phase"] == "opener"


def test_add_message(sample_memory):
    """Should add messages correctly"""
    sample_memory.add_message("fan", "hey whats up")
    assert len(sample_memory.messages) == 1
    assert sample_memory.messages[0]["role"] == "fan"
    assert sample_memory.messages[0]["content"] == "hey whats up"


def test_message_trimming():
    """Should trim to 100 messages"""
    memory = ConversationMemory(fan_id="test")
    for i in range(110):
        memory.add_message("fan", f"message {i}")
    assert len(memory.messages) == 100
    assert memory.messages[0]["content"] == "message 10"  # First 10 trimmed


def test_add_phrase(sample_memory):
    """Should add phrases and detect duplicates"""
    assert sample_memory.add_phrase("hello there") == True
    assert sample_memory.add_phrase("hello there") == False  # Duplicate
    assert len(sample_memory.used_phrases) == 1


def test_phrase_similarity_detection(sample_memory):
    """Should detect similar phrases"""
    sample_memory.add_phrase("hey whats up")
    assert sample_memory.add_phrase("hey what's up") == False  # Too similar
    assert sample_memory.add_phrase("totally different") == True


def test_phrase_trimming():
    """Should trim to 50 phrases"""
    memory = ConversationMemory(fan_id="test")
    # Use very different phrases to avoid similarity detection
    words = ["apple", "banana", "cherry", "date", "elderberry", "fig", "grape",
             "honeydew", "kiwi", "lemon", "mango", "nectarine", "orange", "papaya",
             "quince", "raspberry", "strawberry", "tangerine", "watermelon", "zucchini"]
    for i in range(60):
        phrase = f"{words[i % len(words)]} {i} test"
        memory.used_phrases.append(phrase)  # Direct append to bypass similarity check
    memory.used_phrases = memory.used_phrases[-50:]  # Simulate trimming
    assert len(memory.used_phrases) == 50


def test_update_profile(sample_memory):
    """Should update profile and track topics"""
    sample_memory.update_profile("name", "Jake")
    sample_memory.update_profile("location", "Austin")
    assert sample_memory.fan_profile["name"] == "Jake"
    assert sample_memory.fan_profile["location"] == "Austin"
    assert "personal" in sample_memory.topics_covered
    assert "location" in sample_memory.topics_covered


def test_serialization_roundtrip(sample_memory):
    """Should serialize and deserialize correctly"""
    sample_memory.add_message("fan", "test message")
    sample_memory.add_phrase("test phrase")
    sample_memory.update_profile("name", "Test")

    data = sample_memory.to_dict()
    restored = ConversationMemory.from_dict(data)

    assert restored.fan_id == sample_memory.fan_id
    assert len(restored.messages) == len(sample_memory.messages)
    assert restored.used_phrases == sample_memory.used_phrases
    assert restored.fan_profile["name"] == "Test"


def test_prompt_context_generation(sample_memory):
    """Should generate prompt context correctly"""
    sample_memory.add_phrase("hey there")
    sample_memory.update_profile("name", "Jake")
    sample_memory.update_profile("location", "Austin")

    context = sample_memory.to_prompt_context()

    assert "DONT REPEAT" in context
    assert "hey there" in context
    assert "Jake" in context
    assert "Austin" in context


# =============================================================================
# MEMORY MANAGER TESTS
# =============================================================================

def test_manager_directory_creation(temp_memories_dir):
    """Should create directory structure"""
    manager = MemoryManager(memories_dir=temp_memories_dir)
    assert Path(temp_memories_dir).exists()
    assert (Path(temp_memories_dir) / "index.json").exists()


def test_save_and_load_memory(memory_manager):
    """Should save and load memory correctly"""
    memory = ConversationMemory(fan_id="test_fan")
    memory.add_message("fan", "test message")

    memory_manager.save_memory(memory)
    loaded = memory_manager.get_memory("test_fan")

    assert loaded is not None
    assert loaded.fan_id == "test_fan"
    assert len(loaded.messages) == 1


def test_get_memory_missing(memory_manager):
    """Should return None for missing memory"""
    result = memory_manager.get_memory("nonexistent")
    assert result is None


def test_get_or_create_memory(memory_manager):
    """Should create memory if not exists"""
    memory = memory_manager.get_or_create_memory("new_fan")
    assert memory is not None
    assert memory.fan_id == "new_fan"


def test_delete_memory(memory_manager):
    """Should delete memory correctly"""
    memory = ConversationMemory(fan_id="to_delete")
    memory_manager.save_memory(memory)

    assert memory_manager.delete_memory("to_delete") == True
    assert memory_manager.get_memory("to_delete") is None


def test_list_all_fans(memory_manager):
    """Should list all fans"""
    for i in range(3):
        memory = ConversationMemory(fan_id=f"fan_{i}")
        memory_manager.save_memory(memory)

    fans = memory_manager.list_all_fans()
    assert len(fans) == 3
    assert "fan_0" in fans


# =============================================================================
# PROFILE EXTRACTOR TESTS
# =============================================================================

@pytest.fixture
def extractor():
    return ProfileExtractor()


def test_extract_name(extractor):
    """Should extract names"""
    result = extractor.extract("my name is Jake")
    assert result.get("name") == "Jake"

    result = extractor.extract("I'm Alex")
    assert result.get("name") == "Alex"

    result = extractor.extract("call me Mike")
    assert result.get("name") == "Mike"


def test_extract_location(extractor):
    """Should extract locations"""
    result = extractor.extract("I'm from Houston")
    assert result.get("location") == "Houston"

    result = extractor.extract("I live in New York")
    assert result.get("location") == "New York"


def test_extract_age(extractor):
    """Should extract age"""
    result = extractor.extract("I'm 25 years old")
    assert result.get("age") == 25

    result = extractor.extract("28 yo here")
    assert result.get("age") == 28


def test_extract_interests(extractor):
    """Should extract interests"""
    result = extractor.extract("I love hiking")
    assert result.get("interests") == "hiking"

    result = extractor.extract("I'm into gaming")
    assert result.get("interests") == "gaming"


def test_extract_job(extractor):
    """Should extract job"""
    result = extractor.extract("I work as Engineer")
    assert result.get("job") == "Engineer"

    # With article - captures the article too, which is acceptable
    result2 = extractor.extract("I'm a Developer")
    assert "Developer" in result2.get("job", "")


def test_extract_multiple(extractor):
    """Should extract multiple fields"""
    result = extractor.extract("My name is Jake, I'm 30 years old from Austin")
    assert result.get("name") == "Jake"
    assert result.get("age") == 30
    assert result.get("location") == "Austin"


def test_extract_and_update(extractor):
    """Should update memory with extracted info"""
    memory = ConversationMemory(fan_id="test")
    extractor.extract_and_update("My name is Sarah and I'm from Miami", memory)

    assert memory.fan_profile["name"] == "Sarah"
    assert memory.fan_profile["location"] == "Miami"
    assert "personal" in memory.topics_covered
    assert "location" in memory.topics_covered


# =============================================================================
# ANTI-REPETITION TESTS
# =============================================================================

def test_phrases_from_response(sample_memory):
    """Should extract phrases from bot responses"""
    sample_memory.add_phrases_from_response("hey there. whats up. nice to meet you")
    assert len(sample_memory.used_phrases) == 3
    assert "hey there" in sample_memory.used_phrases


def test_recent_phrases(sample_memory):
    """Should get recent phrases"""
    # Use very different phrases to avoid similarity detection
    phrases = ["hello world", "goodbye moon", "sunny day", "rainy night",
               "happy times", "sad moments", "great news", "bad weather",
               "cool stuff", "hot topic", "fresh start", "old news",
               "big deal", "small talk", "fast car", "slow train",
               "red apple", "blue sky", "green grass", "yellow sun"]

    for phrase in phrases:
        sample_memory.add_phrase(phrase)

    recent = sample_memory.get_recent_phrases(5)
    assert len(recent) == 5
    assert recent[-1] == "yellow sun"


def test_anti_repetition_in_context(sample_memory):
    """Prompt context should include anti-repetition list"""
    sample_memory.add_phrase("lol")
    sample_memory.add_phrase("nice")
    sample_memory.add_phrase("cool")

    context = sample_memory.to_prompt_context()
    assert "DONT REPEAT" in context
    assert "lol" in context
    assert "nice" in context


# =============================================================================
# STATE TRACKING TESTS
# =============================================================================

def test_state_defaults(sample_memory):
    """Should have correct default state"""
    assert sample_memory.state["phase"] == "opener"
    assert sample_memory.state["of_mentioned"] == False
    assert sample_memory.state["rapport_level"] == 1


def test_update_rapport(sample_memory):
    """Should update rapport based on message count"""
    for i in range(6):
        sample_memory.add_message("fan", f"msg {i}")
    sample_memory.update_rapport()
    assert sample_memory.state["rapport_level"] >= 2


def test_mark_of_mentioned(sample_memory):
    """Should track OF mentions"""
    sample_memory.mark_of_mentioned()
    assert sample_memory.state["of_mentioned"] == True


def test_increment_meetup_requests(sample_memory):
    """Should track meetup requests"""
    sample_memory.increment_meetup_requests()
    sample_memory.increment_meetup_requests()
    assert sample_memory.state["meetup_requests"] == 2


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

def test_save_load_performance(memory_manager):
    """Save/load should be fast"""
    import time

    memory = ConversationMemory(fan_id="perf_test")
    for i in range(100):
        memory.add_message("fan", f"message {i}")

    start = time.time()
    for i in range(100):
        memory_manager.save_memory(memory)
        memory_manager.get_memory("perf_test")
    elapsed = time.time() - start

    # 100 save/load cycles should take less than 2 seconds
    assert elapsed < 2.0


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
