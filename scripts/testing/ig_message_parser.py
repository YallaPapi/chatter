# -*- coding: utf-8 -*-
"""
IG Message Parser

Parses AI output into multiple messages:
- Splits on || delimiter
- Handles [IMG:filename] tags
- Cleans and formats messages
"""

import re
from dataclasses import dataclass
from typing import List, Tuple, Optional
from ig_image_library import parse_image_tags, resolve_image_path


# =============================================================================
# MESSAGE DATA STRUCTURE
# =============================================================================

@dataclass
class ParsedMessage:
    """A single parsed message ready to send"""
    text: str
    image: Optional[str] = None  # Filename if message includes image
    image_path: Optional[str] = None  # Full path to image file

    def has_image(self) -> bool:
        return self.image is not None

    def __repr__(self):
        if self.image:
            return f"ParsedMessage(text='{self.text}', image='{self.image}')"
        return f"ParsedMessage(text='{self.text}')"


# =============================================================================
# PARSER
# =============================================================================

class MessageParser:
    """Parses AI output into sendable messages"""

    # Pattern for splitting on || (with optional whitespace)
    SPLIT_PATTERN = re.compile(r'\s*\|\|\s*')

    # Pattern for [IMG:filename]
    IMG_PATTERN = re.compile(r'\[IMG:([^\]]+)\]')

    def __init__(self):
        pass

    def parse(self, raw_response: str) -> List[ParsedMessage]:
        """
        Parse a raw AI response into list of messages.

        Args:
            raw_response: Raw text from AI, may contain || and [IMG:] tags

        Returns:
            List of ParsedMessage objects
        """
        if not raw_response:
            return []

        # Clean the response
        cleaned = self._clean_response(raw_response)

        # Split on ||
        parts = self.SPLIT_PATTERN.split(cleaned)

        messages = []
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for image tag
            img_match = self.IMG_PATTERN.search(part)
            if img_match:
                image_filename = img_match.group(1)
                # Remove the image tag from text
                text = self.IMG_PATTERN.sub('', part).strip()

                # Get full path
                image_path = resolve_image_path(image_filename)
                path_str = str(image_path) if image_path else None

                # If there's text with the image
                if text:
                    messages.append(ParsedMessage(text=text))
                # Add image as separate message
                messages.append(ParsedMessage(
                    text="",  # Images can be text-less
                    image=image_filename,
                    image_path=path_str
                ))
            else:
                messages.append(ParsedMessage(text=part))

        return messages

    def _clean_response(self, response: str) -> str:
        """Clean up the raw response"""
        # Remove leading/trailing whitespace
        cleaned = response.strip()

        # Remove any leading/trailing ||
        cleaned = cleaned.strip('|').strip()

        # Remove multiple consecutive ||
        cleaned = re.sub(r'\|\|\s*\|\|', '||', cleaned)

        # Remove newlines (shouldn't be there but just in case)
        cleaned = cleaned.replace('\n', ' ')

        # Clean up multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned

    def format_for_display(self, messages: List[ParsedMessage]) -> str:
        """Format messages for display/debugging"""
        lines = []
        for i, msg in enumerate(messages, 1):
            if msg.has_image():
                if msg.text:
                    lines.append(f"  {i}. {msg.text}")
                    lines.append(f"     [IMAGE: {msg.image}]")
                else:
                    lines.append(f"  {i}. [IMAGE: {msg.image}]")
            else:
                lines.append(f"  {i}. {msg.text}")
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_response(raw_response: str) -> List[ParsedMessage]:
    """Quick parse function"""
    parser = MessageParser()
    return parser.parse(raw_response)


def get_message_texts(raw_response: str) -> List[str]:
    """Get just the text content of messages (for simple use)"""
    messages = parse_response(raw_response)
    return [msg.text for msg in messages if msg.text]


def get_images_from_response(raw_response: str) -> List[str]:
    """Get list of image filenames from response"""
    messages = parse_response(raw_response)
    return [msg.image for msg in messages if msg.has_image()]


# =============================================================================
# POST-PROCESSING
# =============================================================================

def apply_casual_style(text: str) -> str:
    """
    Apply casual texting style transformations.
    Only used if the AI doesn't apply them consistently.
    """
    # Common replacements
    replacements = {
        " you ": " u ",
        " your ": " ur ",
        " you're ": " ur ",
        " youre ": " ur ",
        "You ": "u ",
        "Your ": "ur ",
        " are ": " r ",
        " right now": " rn",
        " to be honest": " tbh",
        "To be honest": "tbh",
        " because ": " cuz ",
        "Because ": "cuz ",
        " probably ": " prob ",
        " though": " tho",
        " about ": " abt ",
    }

    result = text
    for old, new in replacements.items():
        result = result.replace(old, new)

    # Lowercase (80% of the time the AI should already do this)
    # Only lowercase if it looks too formal
    if result[0].isupper() and len(result) > 1 and not result[1].isupper():
        # Check if it's not a name/proper noun situation
        if result.split()[0].lower() not in ['i', "i'm", "im"]:
            result = result[0].lower() + result[1:]

    return result


def enforce_length_limit(messages: List[ParsedMessage], max_words: int = 15) -> List[ParsedMessage]:
    """
    Split messages that are too long.
    Most messages should be under 10 words, this catches outliers.
    """
    result = []
    for msg in messages:
        if not msg.text:
            result.append(msg)
            continue

        words = msg.text.split()
        if len(words) <= max_words:
            result.append(msg)
        else:
            # Split into chunks
            for i in range(0, len(words), max_words):
                chunk = ' '.join(words[i:i + max_words])
                result.append(ParsedMessage(text=chunk))

            # Keep image with last chunk if present
            if msg.has_image():
                result[-1] = ParsedMessage(
                    text=result[-1].text,
                    image=msg.image,
                    image_path=msg.image_path
                )

    return result


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== MESSAGE PARSER TEST ===\n")

    parser = MessageParser()

    test_cases = [
        # Basic split
        "heyyy||whats up",

        # Multiple messages
        "haha stop||ur funny||but seriously tho",

        # With image
        "lol here||[IMG:selfie_casual.jpg]||happy now?",

        # Image only
        "[IMG:sad_face.jpg]",

        # Mixed
        "omg look at this||[IMG:car_damage.jpg]||im so stressed",

        # Edge cases
        "just one message",
        "||leading pipes||",
        "double || || pipes",

        # Longer message
        "honestly i dont really meet guys from instagram like that but if you want to get to know me better my of is where im more open",
    ]

    for raw in test_cases:
        print(f"Input: {raw}")
        messages = parser.parse(raw)
        print(parser.format_for_display(messages))
        print()

    # Test length enforcement
    print("--- LENGTH ENFORCEMENT ---")
    long_msg = [ParsedMessage(text="honestly i dont really meet guys from instagram like that but if you want to get to know me better my of is where im more open")]
    split_msgs = enforce_length_limit(long_msg, max_words=10)
    print("Split long message:")
    print(parser.format_for_display(split_msgs))

    print("\n=== TEST COMPLETE ===")
