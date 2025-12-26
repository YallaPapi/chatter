# Chatbot API Server PRD

## Overview

Build a REST API server that wraps the existing Instagram chatbot logic, allowing phone automation (Geelark cloud phones or Pixel devices) to get AI-generated responses for Instagram DMs.

## Problem

The phone automation can detect new Instagram DMs and extract message text, but it needs an external "brain" to decide what to reply. The chatbot logic already exists and works (`ig_chatbot.py`, `ig_simple_prompt.py`, `llm_client.py`), but there's no way for the phone automation to call it.

## Solution

Create a FastAPI server with a single endpoint that:
1. Receives fan message + user ID
2. Loads conversation history for that user
3. Calls Claude API with system prompt + history
4. Saves updated history
5. Returns the response

## Technical Requirements

### API Endpoint

```
POST /chat
Content-Type: application/json

Request:
{
  "user_id": "string",        # Unique identifier for the fan (Instagram user ID or username)
  "message": "string",        # The fan's message text
  "platform": "instagram"     # Optional, for future multi-platform support
}

Response:
{
  "response": "string",       # The chatbot's reply
  "conversation_ended": bool  # True if convo should end (fan subbed or gave up)
}
```

### Conversation History Storage

- Store per-user conversation history in JSON files
- Location: `data/conversations/{user_id}.json`
- Structure:
```json
{
  "user_id": "fan123",
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00",
  "messages": [
    {"role": "fan", "content": "hey gorgeous", "timestamp": "..."},
    {"role": "her", "content": "hey thanks babe", "timestamp": "..."}
  ]
}
```

### Integration with Existing Code

Use the existing modules:
- `ig_simple_prompt.py` - System prompt (already working)
- `llm_client.py` - Claude API client with caching (already working)
- `response_generator.py` - Response generation logic (already working)

### Server Requirements

- FastAPI framework
- Run on configurable port (default 8000)
- Load API keys from `.env` file
- Health check endpoint: `GET /health`
- Graceful error handling (don't crash on bad requests)

### Conversation End Detection

Detect when conversation should end:
- Fan says they subscribed → respond with thanks, set `conversation_ended: true`
- Fan refuses/gives up → set `conversation_ended: true`
- Use existing detection logic from `ig_auto_tester.py`

## File Structure

```
scripts/testing/
├── api.py                    # NEW: FastAPI server
├── conversation_store.py     # NEW: History storage/retrieval
├── ig_simple_prompt.py       # Existing: System prompt
├── llm_client.py             # Existing: Claude client
├── response_generator.py     # Existing: Response logic
└── ig_chatbot.py             # Existing: Chatbot class

data/
└── conversations/            # NEW: Per-user conversation files
    ├── fan123.json
    └── fan456.json
```

## Non-Requirements (Out of Scope)

- Authentication/API keys for the server itself (internal use only)
- Rate limiting (phone automation controls request rate)
- Database (JSON files are sufficient for this scale)
- WebSocket/real-time (HTTP request/response is fine)
- Multi-model support (Claude only for now)

## Success Criteria

1. Server starts and responds to health check
2. Can receive a message and return a coherent response
3. Conversation history persists across requests
4. Same user gets contextual responses based on history
5. Conversation end detection works
6. Handles errors gracefully (invalid JSON, missing fields, API failures)

## Example Flow

```
# First message from fan
POST /chat {"user_id": "john123", "message": "hey gorgeous"}
→ {"response": "hey thanks babe", "conversation_ended": false}

# Second message (history loaded)
POST /chat {"user_id": "john123", "message": "you in miami?"}
→ {"response": "haha maybe, where are you", "conversation_ended": false}

# Fan subscribes
POST /chat {"user_id": "john123", "message": "just subbed to your OF!"}
→ {"response": "omg yay thanks babe! hit me up on there", "conversation_ended": true}
```
