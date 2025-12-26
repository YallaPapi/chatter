# -*- coding: utf-8 -*-
"""
LLM Client Abstraction

Provides an abstract interface for LLM calls, enabling:
- Easy switching between providers (Grok, OpenAI, etc.)
- Mock implementations for testing
- Consistent interface across the codebase
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
import os
import logging

from exceptions import ConfigError, LLMError

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from an LLM call"""
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None  # tokens used


class LLMClient(ABC):
    """Abstract base class for LLM clients"""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 175,
        temperature: float = 0.95,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature

        Returns:
            LLMResponse with generated content
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Get the model name being used"""
        pass


class GrokClient(LLMClient):
    """
    Grok (xAI) LLM client using OpenAI-compatible API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base: str = "https://api.x.ai/v1",
        model: str = "grok-4-1-fast-non-reasoning",
    ):
        self.api_base = api_base
        self.model = model
        self.api_key = api_key or os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")

        if not self.api_key:
            raise ConfigError(
                "No API key found. Set GROK_API_KEY or XAI_API_KEY environment variable."
            )

        # Lazy import to avoid dependency issues in tests
        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
            )
        except ImportError as e:
            raise ConfigError(f"openai package not installed: {e}")

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 175,
        temperature: float = 0.95,
    ) -> LLMResponse:
        """Generate response using Grok API"""
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise LLMError(f"API call failed: {e}") from e

        usage = None
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        content = response.choices[0].message.content
        if not content:
            logger.warning("LLM returned empty response")
            content = ""

        return LLMResponse(
            content=content.strip(),
            model=self.model,
            usage=usage,
        )

    @property
    def model_name(self) -> str:
        return self.model


class ClaudeClient(LLMClient):
    """
    Claude (Anthropic) LLM client.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
    ):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ConfigError(
                "No API key found. Set ANTHROPIC_API_KEY environment variable."
            )

        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError as e:
            raise ConfigError(f"anthropic package not installed: {e}")

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 175,
        temperature: float = 0.95,
    ) -> LLMResponse:
        """Generate response using Claude API with prompt caching"""
        try:
            # Claude uses system message separately with caching
            system_content = []
            chat_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    # Cache the system prompt - saves ~90% on repeated calls
                    system_content.append({
                        "type": "text",
                        "text": msg["content"],
                        "cache_control": {"type": "ephemeral"}
                    })
                else:
                    chat_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })

            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system_content,
                messages=chat_messages,
            )
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise LLMError(f"API call failed: {e}") from e

        content = response.content[0].text if response.content else ""

        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
        }

        return LLMResponse(
            content=content.strip(),
            model=self.model,
            usage=usage,
        )

    @property
    def model_name(self) -> str:
        return self.model


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing.

    Can be configured with:
    - Fixed responses
    - Response sequences
    - Custom response logic
    """

    def __init__(
        self,
        default_response: str = "lol ok",
        responses: Optional[List[str]] = None,
        response_map: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize mock client.

        Args:
            default_response: Default response when no match found
            responses: List of responses to cycle through
            response_map: Dict mapping keywords to responses
        """
        self.default_response = default_response
        self.responses = responses or []
        self.response_map = response_map or {}
        self._call_count = 0
        self._call_history: List[Dict[str, Any]] = []

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 175,
        temperature: float = 0.95,
    ) -> LLMResponse:
        """Generate mock response"""
        # Record the call
        self._call_history.append({
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })

        # Get the user message (last one with role=user)
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "").lower()
                break

        # Check response map first (keyword matching)
        for keyword, response in self.response_map.items():
            if keyword.lower() in user_message:
                return LLMResponse(content=response, model="mock")

        # Then check response sequence
        if self.responses:
            response = self.responses[self._call_count % len(self.responses)]
            self._call_count += 1
            return LLMResponse(content=response, model="mock")

        # Default response
        return LLMResponse(content=self.default_response, model="mock")

    @property
    def model_name(self) -> str:
        return "mock"

    @property
    def call_count(self) -> int:
        """Number of times generate() was called"""
        return len(self._call_history)

    @property
    def call_history(self) -> List[Dict[str, Any]]:
        """Full history of all calls"""
        return self._call_history

    def reset(self):
        """Reset call count and history"""
        self._call_count = 0
        self._call_history = []


class ScriptedLLMClient(LLMClient):
    """
    LLM client that returns scripted responses in order.
    Useful for deterministic testing of conversation flows.
    """

    def __init__(self, script: List[str]):
        """
        Initialize with a script of responses.

        Args:
            script: List of responses to return in order
        """
        self.script = script
        self._index = 0

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 175,
        temperature: float = 0.95,
    ) -> LLMResponse:
        """Return next scripted response"""
        if self._index >= len(self.script):
            # Loop back to start or return default
            self._index = 0

        response = self.script[self._index]
        self._index += 1

        return LLMResponse(content=response, model="scripted")

    @property
    def model_name(self) -> str:
        return "scripted"

    def reset(self):
        """Reset to beginning of script"""
        self._index = 0


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_llm_client(
    provider: str = "claude",
    **kwargs,
) -> LLMClient:
    """
    Factory function to create LLM clients.

    Args:
        provider: One of "claude", "grok", "mock", "scripted"
        **kwargs: Provider-specific arguments

    Returns:
        Configured LLMClient instance
    """
    if provider == "claude":
        return ClaudeClient(**kwargs)
    elif provider == "grok":
        return GrokClient(**kwargs)
    elif provider == "mock":
        return MockLLMClient(**kwargs)
    elif provider == "scripted":
        return ScriptedLLMClient(**kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider}")


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== LLM Client Test ===\n")

    # Test MockLLMClient
    print("--- MockLLMClient ---")
    mock = MockLLMClient(
        default_response="haha nice",
        response_map={
            "hey": "heyyy||whats up",
            "hot": "lol thanks babe",
            "meet": "haha maybe||i barely know u",
        }
    )

    test_messages = [
        [{"role": "user", "content": "hey"}],
        [{"role": "user", "content": "youre so hot"}],
        [{"role": "user", "content": "lets meet up"}],
        [{"role": "user", "content": "random message"}],
    ]

    for msgs in test_messages:
        response = mock.generate(msgs)
        print(f"  Input: {msgs[0]['content']!r}")
        print(f"  Output: {response.content!r}\n")

    print(f"Total calls: {mock.call_count}")

    # Test ScriptedLLMClient
    print("\n--- ScriptedLLMClient ---")
    scripted = ScriptedLLMClient([
        "heyyy",
        "lol nice",
        "haha thats cool",
    ])

    for i in range(5):
        response = scripted.generate([{"role": "user", "content": f"msg {i}"}])
        print(f"  Response {i}: {response.content!r}")

    print("\n=== Test Complete ===")
