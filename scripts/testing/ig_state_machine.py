# -*- coding: utf-8 -*-
"""
IG State Machine

Manages conversation state and phase transitions for the IG chatbot.
Based on the PRD's 6-phase conversation flow.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import re
import json
from datetime import datetime
import uuid


# =============================================================================
# CONVERSATION PHASES
# =============================================================================

class Phase(Enum):
    """
    Conversation phases from the PRD:
    1. OPENER - First contact, greeting
    2. LOCATION - Location matching/building connection
    3. SMALL_TALK - Building rapport, casual conversation
    4. DEFLECTION - Handling meetup requests (soft deflect first)
    5. OF_PITCH - Second meetup or sexual escalation - redirect to OF
    6. POST_PITCH - After OF mentioned, answer questions briefly
    7. COLD - Gone cold after too many POST_PITCH messages without sub
    """
    OPENER = "opener"
    LOCATION = "location"
    SMALL_TALK = "small_talk"
    DEFLECTION = "deflection"
    OF_PITCH = "of_pitch"
    POST_PITCH = "post_pitch"
    COLD = "cold"


# =============================================================================
# MESSAGE DETECTION PATTERNS
# =============================================================================

# Location patterns - US cities and general location mentions
US_CITIES = [
    "new york", "nyc", "los angeles", "la", "chicago", "houston", "phoenix",
    "philadelphia", "san antonio", "san diego", "dallas", "san jose",
    "austin", "jacksonville", "fort worth", "columbus", "charlotte",
    "san francisco", "indianapolis", "seattle", "denver", "washington",
    "boston", "nashville", "detroit", "portland", "memphis", "oklahoma city",
    "las vegas", "louisville", "baltimore", "milwaukee", "albuquerque",
    "tucson", "fresno", "sacramento", "kansas city", "atlanta", "miami",
    "tampa", "orlando", "minneapolis", "cleveland", "new orleans", "pittsburgh",
]

LOCATION_PATTERNS = [
    r"(?:i\'?m\s+)?(?:from|in|live\s+in|based\s+in)\s+(\w+(?:\s+\w+)?)",
    r"(\w+(?:\s+\w+)?)\s+(?:area|city)",
    r"i\s+live\s+(?:in|near)\s+(\w+(?:\s+\w+)?)",
]

# Meetup request patterns
MEETUP_PATTERNS = [
    r"(?:let\'?s?|we\s+should|can\s+we|wanna)\s+(?:meet|hang|link|chill|grab\s+drinks?)",
    r"(?:take\s+you|bring\s+you)\s+(?:out|to\s+dinner)",
    r"(?:get|grab)\s+(?:dinner|lunch|drinks?|coffee|food)",
    r"(?:show\s+you\s+around|hang\s+out|link\s+up)",
    r"when\s+(?:can|will)\s+(?:i|we)\s+(?:see|meet)\s+you",
    r"(?:come\s+)?over",
    r"let\s+me\s+(?:take|see)\s+you",
]

# Picture/sexual request patterns
PIC_REQUEST_PATTERNS = [
    r"send\s+(?:me\s+)?(?:a\s+)?(?:pic|photo|nudes?|something\s+sexy)",
    r"(?:got|have)\s+(?:any\s+)?(?:more\s+)?pics?",
    r"show\s+me\s+(?:something|more)",
    r"what\s+(?:are\s+you|r\s+u)\s+wearing",
]

SEXUAL_PATTERNS = [
    r"(?:so\s+)?(?:hot|sexy|fine|beautiful|gorgeous)",
    r"(?:your\s+)?body",
    r"naked",
    r"bedroom",
    r"(?:what\s+would\s+you|wanna)\s+do\s+(?:to\s+me|together)",
]

# OF mention patterns (detecting if bot mentioned OF)
OF_PATTERNS = [
    r"\bof\b",
    r"onlyfans",
    r"only\s*fans",
    r"subscribe",
    r"sub\b",
]

# Fan subscription patterns (detecting if fan says they subscribed)
FAN_SUBSCRIBED_PATTERNS = [
    r"(?:i\s+)?(?:just\s+)?(?:subbed|subscribed)",
    r"(?:i\s+)?signed\s+up",
    r"bought\s+(?:it|your|the)\s+(?:of|subscription)",
    r"got\s+(?:your|the)\s+(?:of|subscription)",
    r"joined\s+(?:your|the)?\s*(?:of|onlyfans)",
]

# Messages in POST_PITCH before going cold
COLD_THRESHOLD = 4



# =============================================================================
# CONVERSATION STATE
# =============================================================================

@dataclass
class ConversationState:
    """
    Tracks the full state of a conversation.
    """
    # Unique conversation ID
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # Current phase
    phase: Phase = Phase.OPENER

    # Scenario info (set at conversation start)
    scenario_id: Optional[str] = None
    mood: Optional[str] = None
    sob_story_active: bool = False

    # Location tracking
    location_detected: bool = False
    location: Optional[str] = None
    location_matched: bool = False  # Did we say we're visiting there?

    # OF tracking
    of_mentioned: bool = False
    of_mention_count: int = 0

    # Request tracking
    meetup_requests: int = 0
    pic_requests: int = 0
    sexual_escalation: bool = False

    # Message counts
    message_count: int = 0
    fan_message_count: int = 0
    her_message_count: int = 0

    # Sob story escalation level (0-5)
    sob_story_escalation_level: int = 0

    # Images sent
    images_sent: List[str] = field(default_factory=list)
    
    # Post-pitch tracking - for going cold
    post_pitch_messages: int = 0  # Messages since OF was mentioned
    fan_subscribed: bool = False  # Did fan say they subscribed?

    # Timestamp
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Serialize state to dict for JSON storage"""
        return {
            "conversation_id": self.conversation_id,
            "phase": self.phase.value,
            "scenario_id": self.scenario_id,
            "mood": self.mood,
            "sob_story_active": self.sob_story_active,
            "location_detected": self.location_detected,
            "location": self.location,
            "location_matched": self.location_matched,
            "of_mentioned": self.of_mentioned,
            "of_mention_count": self.of_mention_count,
            "meetup_requests": self.meetup_requests,
            "pic_requests": self.pic_requests,
            "sexual_escalation": self.sexual_escalation,
            "message_count": self.message_count,
            "fan_message_count": self.fan_message_count,
            "her_message_count": self.her_message_count,
            "sob_story_escalation_level": self.sob_story_escalation_level,
            "images_sent": self.images_sent,
            "post_pitch_messages": self.post_pitch_messages,
            "fan_subscribed": self.fan_subscribed,
            "started_at": self.started_at,
            "last_activity": self.last_activity,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """Deserialize state from dict"""
        state = cls()
        state.conversation_id = data.get("conversation_id", state.conversation_id)
        state.phase = Phase(data.get("phase", Phase.OPENER.value))
        state.scenario_id = data.get("scenario_id")
        state.mood = data.get("mood")
        state.sob_story_active = data.get("sob_story_active", False)
        state.location_detected = data.get("location_detected", False)
        state.location = data.get("location")
        state.location_matched = data.get("location_matched", False)
        state.of_mentioned = data.get("of_mentioned", False)
        state.of_mention_count = data.get("of_mention_count", 0)
        state.meetup_requests = data.get("meetup_requests", 0)
        state.pic_requests = data.get("pic_requests", 0)
        state.sexual_escalation = data.get("sexual_escalation", False)
        state.message_count = data.get("message_count", 0)
        state.fan_message_count = data.get("fan_message_count", 0)
        state.her_message_count = data.get("her_message_count", 0)
        state.sob_story_escalation_level = data.get("sob_story_escalation_level", 0)
        state.images_sent = data.get("images_sent", [])
        state.post_pitch_messages = data.get("post_pitch_messages", 0)
        state.fan_subscribed = data.get("fan_subscribed", False)
        state.started_at = data.get("started_at", state.started_at)
        state.last_activity = data.get("last_activity", state.last_activity)
        return state


# =============================================================================
# STATE MACHINE
# =============================================================================

class ConversationStateMachine:
    """
    Manages state transitions for a conversation.
    """

    def __init__(self, state: Optional[ConversationState] = None):
        self.state = state or ConversationState()

    def initialize_with_scenario(self, scenario_id: str, mood: str, is_sob_story: bool = False):
        """Initialize conversation with a selected scenario"""
        self.state.scenario_id = scenario_id
        self.state.mood = mood
        self.state.sob_story_active = is_sob_story

    def detect_location(self, message: str) -> Optional[str]:
        """Detect if message contains a location mention"""
        msg_lower = message.lower()

        # Check for US cities first
        for city in US_CITIES:
            if city in msg_lower:
                return city.title()

        # Try patterns
        for pattern in LOCATION_PATTERNS:
            match = re.search(pattern, msg_lower, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # Verify it looks like a real place (not "good" or "great")
                if len(location) > 2 and location not in ["good", "great", "okay", "fine"]:
                    return location.title()

        return None

    def detect_meetup_request(self, message: str) -> bool:
        """Detect if message is a meetup request"""
        msg_lower = message.lower()
        for pattern in MEETUP_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False

    def detect_pic_request(self, message: str) -> bool:
        """Detect if message is asking for pics"""
        msg_lower = message.lower()
        for pattern in PIC_REQUEST_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False

    def detect_sexual_escalation(self, message: str) -> bool:
        """Detect sexual escalation in message"""
        msg_lower = message.lower()
        for pattern in SEXUAL_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False

    def detect_of_mention(self, response: str) -> bool:
        """Detect if our response mentioned OF"""
        resp_lower = response.lower()
        for pattern in OF_PATTERNS:
            if re.search(pattern, resp_lower, re.IGNORECASE):
                return True
        return False

    def detect_fan_subscribed(self, message: str) -> bool:
        """Detect if fan says they subscribed"""
        msg_lower = message.lower()
        for pattern in FAN_SUBSCRIBED_PATTERNS:
            if re.search(pattern, msg_lower, re.IGNORECASE):
                return True
        return False

    def process_fan_message(self, message: str):
        """
        Process incoming fan message and update state.
        Call this BEFORE generating a response.
        """
        self.state.message_count += 1
        self.state.fan_message_count += 1
        self.state.last_activity = datetime.now().isoformat()

        # Detect location
        location = self.detect_location(message)
        if location and not self.state.location_detected:
            self.state.location_detected = True
            self.state.location = location

        # Detect meetup request
        if self.detect_meetup_request(message):
            self.state.meetup_requests += 1

        # Detect pic request
        if self.detect_pic_request(message):
            self.state.pic_requests += 1

        # Detect sexual escalation
        if self.detect_sexual_escalation(message) and self.state.fan_message_count > 3:
            self.state.sexual_escalation = True

        # Detect if fan subscribed
        if self.detect_fan_subscribed(message):
            self.state.fan_subscribed = True

        # Track post-pitch messages (for going cold)
        if self.state.of_mentioned and not self.state.fan_subscribed:
            self.state.post_pitch_messages += 1

        # Update phase
        self._update_phase()

    def process_bot_response(self, response: str, images_sent: List[str] = None):
        """
        Process our response and update state.
        Call this AFTER generating a response.
        """
        self.state.her_message_count += 1

        # Track OF mentions
        if self.detect_of_mention(response):
            self.state.of_mentioned = True
            self.state.of_mention_count += 1
            # Transition to post-pitch
            self.state.phase = Phase.POST_PITCH

        # Track images sent
        if images_sent:
            self.state.images_sent.extend(images_sent)

        # Track location matching (if we said we're visiting)
        if self.state.location_detected and not self.state.location_matched:
            visiting_patterns = [r"visiting", r"just here", r"in the area", r"in town"]
            for pattern in visiting_patterns:
                if re.search(pattern, response.lower()):
                    self.state.location_matched = True
                    break

    def _update_phase(self):
        """
        Update conversation phase based on current state.
        Phase transitions from PRD:
        - OPENER -> LOCATION (when location detected/asked)
        - LOCATION -> SMALL_TALK (after location established)
        - SMALL_TALK -> DEFLECTION (when meetup requested)
        - DEFLECTION -> SMALL_TALK (after soft deflect)
        - DEFLECTION -> OF_PITCH (on 2nd meetup or pic request)
        - OF_PITCH -> POST_PITCH (after OF mentioned)
        - POST_PITCH -> COLD (after threshold messages without subscribing)
        """
        # Already cold, stay cold (unless they subscribe)
        if self.state.phase == Phase.COLD:
            if self.state.fan_subscribed:
                self.state.phase = Phase.POST_PITCH  # Warm back up if they sub
            return

        # Check if we should go cold (in POST_PITCH too long without sub)
        if self.state.phase == Phase.POST_PITCH:
            if not self.state.fan_subscribed and self.state.post_pitch_messages >= COLD_THRESHOLD:
                self.state.phase = Phase.COLD
            return

        # Trigger OF_PITCH conditions
        should_pitch_of = (
            self.state.meetup_requests >= 2 or
            self.state.pic_requests > 0 or
            self.state.sexual_escalation
        ) and not self.state.of_mentioned

        if should_pitch_of:
            self.state.phase = Phase.OF_PITCH
            return

        # First meetup request -> DEFLECTION
        if self.state.meetup_requests == 1 and not self.state.of_mentioned:
            self.state.phase = Phase.DEFLECTION
            return

        # Location detected -> LOCATION phase
        if self.state.location_detected and not self.state.location_matched:
            self.state.phase = Phase.LOCATION
            return

        # After location matched -> SMALL_TALK
        if self.state.location_matched:
            self.state.phase = Phase.SMALL_TALK
            return

        # Early messages -> OPENER
        if self.state.fan_message_count <= 2:
            self.state.phase = Phase.OPENER
            return

        # Default to SMALL_TALK
        self.state.phase = Phase.SMALL_TALK

    def should_escalate_sob_story(self) -> bool:
        """Check if we should escalate the sob story"""
        if not self.state.sob_story_active:
            return False

        # Escalate after some rapport is built
        if self.state.fan_message_count < 5:
            return False

        # Don't escalate if we've already maxed out
        if self.state.sob_story_escalation_level >= 5:
            return False

        # Escalate every 3-4 messages in small talk
        if self.state.phase == Phase.SMALL_TALK:
            return self.state.fan_message_count % 4 == 0

        return False

    def escalate_sob_story(self):
        """Increment sob story escalation level"""
        if self.state.sob_story_escalation_level < 5:
            self.state.sob_story_escalation_level += 1

    def get_phase_name(self) -> str:
        """Get current phase as string"""
        return self.state.phase.value

    def get_context_for_prompt(self) -> Dict[str, Any]:
        """Get state context for prompt building"""
        return {
            "phase": self.state.phase.value,
            "mood": self.state.mood,
            "scenario_id": self.state.scenario_id,
            "sob_story_active": self.state.sob_story_active,
            "sob_story_level": self.state.sob_story_escalation_level,
            "location": self.state.location,
            "location_matched": self.state.location_matched,
            "of_mentioned": self.state.of_mentioned,
            "meetup_requests": self.state.meetup_requests,
            "pic_requests": self.state.pic_requests,
            "message_count": self.state.fan_message_count,
        }


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== STATE MACHINE TEST ===\n")

    # Create state machine
    sm = ConversationStateMachine()
    sm.initialize_with_scenario("car_accident", "stressed", is_sob_story=True)

    print(f"Initial state: phase={sm.get_phase_name()}, mood={sm.state.mood}")

    # Simulate conversation
    test_messages = [
        ("hey", "heyyy||whats up"),
        ("im from houston", "wait fr?||im in houston rn too lol"),
        ("what are you up to", "just dealing with some car stuff||stressed af"),
        ("that sucks what happened", "got rear ended yesterday||the damage is bad"),
        ("damn sorry to hear that", "yeah its been rough||the repair is gonna cost a lot"),
        ("we should get drinks sometime", "haha maybe||i barely know u tho"),
        ("come on let me take you out", "i dont really meet guys from ig||but my of is where im more open"),
    ]

    for fan_msg, bot_response in test_messages:
        sm.process_fan_message(fan_msg)
        print(f"\nFan: {fan_msg}")
        print(f"  -> Phase: {sm.get_phase_name()}")
        print(f"  -> Meetup requests: {sm.state.meetup_requests}")
        print(f"  -> Location: {sm.state.location}")

        sm.process_bot_response(bot_response)
        print(f"Bot: {bot_response}")
        print(f"  -> OF mentioned: {sm.state.of_mentioned}")

    print("\n--- Final State ---")
    print(json.dumps(sm.state.to_dict(), indent=2))

    print("\n=== TEST COMPLETE ===")
