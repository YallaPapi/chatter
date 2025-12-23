# Conversation Memory System PRD

## Overview

Build a persistent memory system for the IG chatbot that stores per-fan conversation history, learned information, and used phrases. This enables longer, more natural conversations by preventing repetition and allowing personalization.

## Problem Statement

Current issues with the chatbot:
1. **Repetition** - Bot repeats the same phrases ("nah babe", "keep tryin") because it has no memory of what it already said
2. **No personalization** - Bot can't reference things the fan shared (name, location, interests)
3. **Short conversations** - Conversations feel robotic after 4-5 messages due to repetition
4. **No persistence** - If fan comes back later, bot doesn't remember them

## Goals

1. **Eliminate repetition** - Track all phrases used and inject into prompts to prevent reuse
2. **Enable personalization** - Extract and store fan info, reference it naturally in conversation
3. **Support longer convos** - With variety and personalization, convos can go 20+ messages naturally
4. **Persist across sessions** - Fan returns days later, bot remembers them

## Non-Goals

- Real-time sync across multiple instances (single-instance for now)
- Complex NLP entity extraction (simple regex/pattern matching is fine)
- Analytics dashboard (just storage for now)

## Architecture

### Storage Structure

```
data/memories/
├── {fan_id}.json     # One file per fan
└── index.json        # Optional: fan_id -> metadata lookup
```

### Memory Schema (per fan)

```json
{
  "fan_id": "string",
  "created_at": "ISO timestamp",
  "last_active": "ISO timestamp",

  "messages": [
    {
      "role": "fan|her",
      "content": "message text",
      "timestamp": "ISO timestamp",
      "phase": "opener|location|small_talk|etc"
    }
  ],

  "used_phrases": [
    "heyyy",
    "whats up",
    "nah babe thats on of"
  ],

  "fan_profile": {
    "name": "string|null",
    "location": "string|null",
    "interests": ["hiking", "netflix"],
    "job": "string|null",
    "age": "number|null",
    "relationship_status": "string|null",
    "platform_preferences": ["snap", "ig"]
  },

  "state": {
    "phase": "opener|location|small_talk|deflection|of_pitch|post_pitch|cold",
    "of_mentioned": "boolean",
    "of_subscribed": "boolean",
    "meetup_requests": "number",
    "rapport_level": "1-5 scale",
    "conversation_count": "number"
  },

  "topics_covered": [
    "location",
    "job",
    "hobbies",
    "relationship"
  ]
}
```

### Core Components

#### 1. ConversationMemory Class
- Represents a single fan's memory
- Methods: add_message(), add_phrase(), update_profile(), get_recent_phrases(), to_dict(), from_dict()

#### 2. MemoryManager Class
- Handles persistence (load/save to disk)
- Methods: get_memory(fan_id), save_memory(memory), list_all_fans(), delete_memory(fan_id)
- Creates data directory if not exists

#### 3. ProfileExtractor Class
- Extracts fan info from messages using patterns
- Detects: names, locations, jobs, interests, age
- Returns structured updates to fan_profile

#### 4. Prompt Injector (update to ig_phase_prompts.py)
- Takes memory and injects into prompt:
  - "Don't repeat these phrases: [...]"
  - "You know about him: [fan_profile summary]"
  - "Topics already covered: [...]"

### Integration Points

1. **IGChatbot.respond()** - Load memory at start, save after response
2. **get_phase_prompt()** - Accept memory context, inject anti-repetition
3. **State machine** - Sync state with memory (phase, of_mentioned, etc)

## Implementation Plan

### Phase 1: Core Memory Infrastructure
- Create ConversationMemory dataclass
- Create MemoryManager with JSON persistence
- Unit tests for save/load

### Phase 2: Anti-Repetition
- Track used_phrases in memory
- Update get_phase_prompt() to inject "don't repeat" list
- Test that repetition decreases

### Phase 3: Profile Extraction
- Build ProfileExtractor with regex patterns
- Extract name, location, interests from fan messages
- Store in fan_profile

### Phase 4: Personalization
- Inject fan_profile into prompts
- Bot can say "u said ur from austin right?"
- Track topics_covered to avoid re-asking

### Phase 5: Integration & Testing
- Wire memory into IGChatbot
- Run automated tests with memory enabled
- Measure improvement in scores

## Success Metrics

1. **Repetition rate** - % of responses that repeat earlier phrases (target: <5%)
2. **Human-likeness score** - From automated tester (target: 6+/10)
3. **Conversation length** - Average messages before going cold (target: 15+)
4. **Would subscribe rate** - From automated tester (target: 60%+)

## Technical Considerations

### File Locking
- For now, assume single process access
- Future: add file locking or move to SQLite

### Memory Size
- Cap messages array at 100 entries (trim oldest)
- Cap used_phrases at 50 (trim oldest)

### Fan ID Generation
- Use hash of platform + username
- Or accept fan_id as parameter from caller

## Open Questions

1. Should we use SQLite instead of JSON files for better querying?
2. How to handle fan returning after weeks - reset or continue?
3. Should bot proactively reference old convos ("hey u again!")?

## Timeline

Phase 1-2: Core memory + anti-repetition (highest priority)
Phase 3-4: Profile extraction + personalization
Phase 5: Testing and iteration
