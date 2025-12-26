# -*- coding: utf-8 -*-
"""
Conversation Store

Handles per-user conversation history storage using JSON files.
Each user gets their own file: data/conversations/{user_id}.json
"""

import json
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
import tempfile
import shutil

# Default storage directory
DEFAULT_STORAGE_DIR = Path(__file__).parent.parent.parent / "data" / "conversations"


class ConversationStore:
    """Manages conversation history storage with atomic writes."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else DEFAULT_STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_filepath(self, user_id: str) -> Path:
        """Get the file path for a user's conversation."""
        # Sanitize user_id to be filesystem-safe
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return self.storage_dir / f"{safe_id}.json"

    def load_conversation(self, user_id: str) -> dict:
        """
        Load conversation history for a user.
        Returns empty conversation structure if not found.
        """
        filepath = self._get_filepath(user_id)

        if not filepath.exists():
            return self._create_empty_conversation(user_id)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Corrupted file, start fresh
            return self._create_empty_conversation(user_id)

    def save_conversation(self, user_id: str, data: dict) -> None:
        """
        Save conversation history for a user.
        Uses atomic write (temp file + rename) to prevent corruption.
        """
        filepath = self._get_filepath(user_id)

        # Update the updated_at timestamp
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Atomic write: write to temp file, then rename
        fd, temp_path = tempfile.mkstemp(suffix=".json", dir=self.storage_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Atomic rename (works on same filesystem)
            shutil.move(temp_path, filepath)
        except Exception:
            # Clean up temp file on failure
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    def add_message(self, user_id: str, role: str, content: str) -> dict:
        """
        Add a message to a user's conversation history.
        Creates conversation if it doesn't exist.
        Returns the updated conversation.
        """
        conv = self.load_conversation(user_id)

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        conv["messages"].append(message)
        self.save_conversation(user_id, conv)

        return conv

    def get_messages(self, user_id: str) -> list:
        """Get just the messages list for a user."""
        conv = self.load_conversation(user_id)
        return conv.get("messages", [])

    def clear_conversation(self, user_id: str) -> None:
        """Delete a user's conversation history."""
        filepath = self._get_filepath(user_id)
        if filepath.exists():
            filepath.unlink()

    def _create_empty_conversation(self, user_id: str) -> dict:
        """Create an empty conversation structure."""
        now = datetime.now(timezone.utc).isoformat()
        return {
            "user_id": user_id,
            "created_at": now,
            "updated_at": now,
            "messages": []
        }


# Convenience singleton for simple usage
_default_store = None

def get_store() -> ConversationStore:
    """Get the default conversation store instance."""
    global _default_store
    if _default_store is None:
        _default_store = ConversationStore()
    return _default_store


# For testing
if __name__ == "__main__":
    store = ConversationStore()

    # Test basic flow
    test_user = "test_user_123"
    store.clear_conversation(test_user)

    # Add messages
    store.add_message(test_user, "fan", "hey gorgeous")
    store.add_message(test_user, "her", "hey thanks babe")
    store.add_message(test_user, "fan", "you in miami?")

    # Load and print
    conv = store.load_conversation(test_user)
    print(json.dumps(conv, indent=2))

    # Cleanup
    store.clear_conversation(test_user)
    print("\nTest passed!")
