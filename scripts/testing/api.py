# -*- coding: utf-8 -*-
"""
Chatbot API Server

FastAPI server that wraps the Instagram chatbot for phone automation.
Phone automation sends fan messages, gets AI responses back.
"""

import os
import sys
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import our modules
from conversation_store import ConversationStore
from ig_simple_prompt import build_simple_prompt
from llm_client import ClaudeClient


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ChatRequest(BaseModel):
    user_id: str
    message: str
    platform: Optional[str] = "instagram"


class ChatResponse(BaseModel):
    response: str
    conversation_ended: bool


# =============================================================================
# APP SETUP
# =============================================================================

app = FastAPI(
    title="Instagram Chatbot API",
    description="AI-powered responses for Instagram DMs",
    version="1.0.0"
)

# Initialize components
conversation_store = ConversationStore()
llm_client = None  # Lazy init to avoid API key issues at import time


def get_llm_client():
    """Get or create LLM client."""
    global llm_client
    if llm_client is None:
        llm_client = ClaudeClient()
    return llm_client


# =============================================================================
# CONVERSATION END DETECTION
# =============================================================================

def check_conversation_ended(fan_message: str, her_response: str) -> bool:
    """
    Check if the conversation should end.
    Returns True if fan subscribed or gave up.
    """
    fan_lower = fan_message.lower()
    her_lower = her_response.lower()

    # Fan says they subscribed
    sub_phrases = [
        "just subbed", "i subbed", "subbed to", "subscribed",
        "just subscribed", "i subscribed", "signed up"
    ]
    he_subbed = any(phrase in fan_lower for phrase in sub_phrases)

    # She redirected to OF after he subbed
    redirect_phrases = [
        "talk to you on", "chat on of", "see you on of",
        "hit me up on there", "talk to you there", "chat there",
        "talk on of", "catch you on"
    ]
    she_redirected = any(phrase in her_lower for phrase in redirect_phrases)

    if he_subbed and she_redirected:
        return True

    # Fan gave up or got hostile and left
    gave_up_phrases = [
        "fuck off", "blocked", "bye bitch", "waste of time",
        "not gonna sub", "never subbing", "unsubbing"
    ]
    if any(phrase in fan_lower for phrase in gave_up_phrases):
        return True

    return False


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Process a fan message and return AI response.

    - Loads conversation history for this user
    - Generates response using Claude
    - Saves updated history
    - Detects if conversation should end
    """
    try:
        # Validate input
        if not request.user_id.strip():
            raise HTTPException(status_code=400, detail="user_id cannot be empty")
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="message cannot be empty")

        user_id = request.user_id.strip()
        message = request.message.strip()

        # Load conversation history
        conv = conversation_store.load_conversation(user_id)

        # Add fan message to history
        conv["messages"].append({
            "role": "fan",
            "content": message,
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
        })

        # Build messages for LLM
        system_prompt = build_simple_prompt()
        api_messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in conv["messages"]:
            role = "user" if msg["role"] == "fan" else "assistant"
            api_messages.append({"role": role, "content": msg["content"]})

        # Generate response
        client = get_llm_client()
        llm_response = client.generate(
            messages=api_messages,
            max_tokens=175,
            temperature=0.5
        )

        response_text = llm_response.content.strip()

        # Check if conversation should end
        conversation_ended = check_conversation_ended(message, response_text)

        # Add her response to history
        conv["messages"].append({
            "role": "her",
            "content": response_text,
            "timestamp": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc
            ).isoformat()
        })

        # Save updated conversation
        conversation_store.save_conversation(user_id, conv)

        return ChatResponse(
            response=response_text,
            conversation_ended=conversation_ended
        )

    except HTTPException:
        raise
    except Exception as e:
        # Log the error but don't crash
        print(f"Error processing chat: {e}", file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{user_id}")
def get_conversation(user_id: str):
    """Get conversation history for a user (for debugging)."""
    conv = conversation_store.load_conversation(user_id)
    return conv


@app.delete("/conversation/{user_id}")
def delete_conversation(user_id: str):
    """Delete conversation history for a user."""
    conversation_store.clear_conversation(user_id)
    return {"status": "deleted", "user_id": user_id}


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("CHATBOT_API_PORT", "8000"))
    host = os.getenv("CHATBOT_API_HOST", "0.0.0.0")

    print(f"Starting Chatbot API on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
