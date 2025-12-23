# -*- coding: utf-8 -*-
"""
IG Conversation Logger

Logs all conversations and categorizes:
- Where conversations drop off
- Which objections we're getting
- Which conversational flows lead to most success
- Demand tracking (snap requests, etc.)
"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from enum import Enum


# Log storage
LOG_DIR = Path(__file__).parent.parent.parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class DropOffPoint(Enum):
    """Where conversations typically end"""
    OPENER = "opener"
    LOCATION = "location"
    SMALL_TALK = "small_talk"
    FIRST_DEFLECTION = "first_deflection"
    SECOND_DEFLECTION = "second_deflection"
    OF_REDIRECT = "of_redirect"
    POST_OF_QUESTION = "post_of_question"
    POST_OF_PRICE = "post_of_price"
    POST_OF_REFUSE = "post_of_refuse"
    POST_OF_MAYBE = "post_of_maybe"
    SUBSCRIBED = "subscribed"  # Success!
    UNKNOWN = "unknown"


class Objection(Enum):
    """Common objections we encounter"""
    TOO_EXPENSIVE = "too_expensive"
    DONT_PAY_FOR_PORN = "dont_pay_for_porn"
    WANT_FREE = "want_free"
    WANT_TO_MEET = "want_to_meet"
    WANT_SNAP = "want_snap"
    WANT_NUMBER = "want_number"
    THINK_BOT = "think_bot"
    THINK_SCAM = "think_scam"
    NOT_INTERESTED = "not_interested"
    MAYBE_LATER = "maybe_later"
    GIRLFRIEND = "girlfriend"
    BROKE = "broke"
    OTHER = "other"


@dataclass
class ConversationLog:
    """Full log of a single conversation"""
    conversation_id: str
    started_at: str
    ended_at: Optional[str] = None

    # Outcome tracking
    outcome: str = "ongoing"  # ongoing, subscribed, dropped_off, blocked
    drop_off_point: Optional[str] = None
    objections_encountered: List[str] = field(default_factory=list)

    # Demand tracking
    requested_snap: bool = False
    requested_number: bool = False
    requested_other_social: bool = False
    requested_meet: bool = False
    requested_free_content: bool = False

    # Flow tracking
    phases_reached: List[str] = field(default_factory=list)
    of_mentioned: bool = False
    of_mentioned_count: int = 0
    deal_offered: bool = False
    sad_pic_sent: bool = False

    # Message counts
    total_messages: int = 0
    fan_messages: int = 0
    her_messages: int = 0

    # Full message history
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConversationLogger:
    """Manages logging for all conversations"""

    def __init__(self):
        self.active_conversations: Dict[str, ConversationLog] = {}
        self.log_file = LOG_DIR / f"conversations_{datetime.now().strftime('%Y%m%d')}.jsonl"

        # Aggregated stats
        self.stats_file = LOG_DIR / "aggregate_stats.json"
        self.stats = self._load_stats()

    def _load_stats(self) -> Dict[str, Any]:
        """Load aggregate stats from file"""
        if self.stats_file.exists():
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        return {
            "total_conversations": 0,
            "subscriptions": 0,
            "drop_offs": 0,
            "drop_off_points": {},
            "objections": {},
            "requests": {
                "snap": 0,
                "number": 0,
                "other_social": 0,
                "meet": 0,
                "free_content": 0,
            },
            "avg_messages_before_drop": 0,
            "avg_messages_to_subscribe": 0,
            "conversion_rate": 0.0,
            "phases_reached": {},
        }

    def _save_stats(self):
        """Save aggregate stats to file"""
        with open(self.stats_file, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def start_conversation(self, conversation_id: str) -> ConversationLog:
        """Start logging a new conversation"""
        log = ConversationLog(
            conversation_id=conversation_id,
            started_at=datetime.now().isoformat()
        )
        self.active_conversations[conversation_id] = log
        self.stats["total_conversations"] += 1
        return log

    def log_message(
        self,
        conversation_id: str,
        role: str,  # "fan" or "her"
        content: str,
        phase: str,
        images: List[str] = None
    ):
        """Log a single message"""
        if conversation_id not in self.active_conversations:
            self.start_conversation(conversation_id)

        log = self.active_conversations[conversation_id]

        # Add message
        log.messages.append({
            "role": role,
            "content": content,
            "phase": phase,
            "images": images or [],
            "timestamp": datetime.now().isoformat()
        })

        # Update counts
        log.total_messages += 1
        if role == "fan":
            log.fan_messages += 1
        else:
            log.her_messages += 1

        # Track phase
        if phase not in log.phases_reached:
            log.phases_reached.append(phase)
            self.stats["phases_reached"][phase] = self.stats["phases_reached"].get(phase, 0) + 1

        # Detect requests in fan messages
        if role == "fan":
            self._detect_requests(log, content)
            self._detect_objections(log, content)

        # Detect OF mention in her messages
        if role == "her":
            if "of" in content.lower() or "onlyfans" in content.lower():
                log.of_mentioned = True
                log.of_mentioned_count += 1
            if "deal" in content.lower() or "surprise" in content.lower() or "gift" in content.lower():
                log.deal_offered = True
            if "sad_face" in str(images) or "pouty" in str(images):
                log.sad_pic_sent = True

    def _detect_requests(self, log: ConversationLog, message: str):
        """Detect what the fan is requesting"""
        msg_lower = message.lower()

        if any(w in msg_lower for w in ["snap", "snapchat", "sc"]):
            log.requested_snap = True
            self.stats["requests"]["snap"] += 1

        if any(w in msg_lower for w in ["number", "phone", "text me", "call me"]):
            log.requested_number = True
            self.stats["requests"]["number"] += 1

        if any(w in msg_lower for w in ["insta", "twitter", "tiktok", "discord"]):
            log.requested_other_social = True
            self.stats["requests"]["other_social"] += 1

        if any(w in msg_lower for w in ["meet", "hang", "drink", "date", "see you", "link up"]):
            log.requested_meet = True
            self.stats["requests"]["meet"] += 1

        if any(w in msg_lower for w in ["free", "dont pay", "not paying"]):
            log.requested_free_content = True
            self.stats["requests"]["free_content"] += 1

    def _detect_objections(self, log: ConversationLog, message: str):
        """Detect objections in fan messages"""
        msg_lower = message.lower()

        objection = None

        if any(w in msg_lower for w in ["expensive", "too much", "cost"]):
            objection = Objection.TOO_EXPENSIVE.value
        elif any(w in msg_lower for w in ["dont pay for porn", "pay for that", "not paying"]):
            objection = Objection.DONT_PAY_FOR_PORN.value
        elif any(w in msg_lower for w in ["free", "for free"]):
            objection = Objection.WANT_FREE.value
        elif any(w in msg_lower for w in ["bot", "fake", "scam", "catfish"]):
            objection = Objection.THINK_BOT.value
        elif any(w in msg_lower for w in ["maybe later", "later", "not now"]):
            objection = Objection.MAYBE_LATER.value
        elif any(w in msg_lower for w in ["girlfriend", "wife", "married"]):
            objection = Objection.GIRLFRIEND.value
        elif any(w in msg_lower for w in ["broke", "poor", "no money"]):
            objection = Objection.BROKE.value
        elif any(w in msg_lower for w in ["not interested", "nah", "no thanks"]):
            objection = Objection.NOT_INTERESTED.value

        if objection and objection not in log.objections_encountered:
            log.objections_encountered.append(objection)
            self.stats["objections"][objection] = self.stats["objections"].get(objection, 0) + 1

    def end_conversation(
        self,
        conversation_id: str,
        outcome: str,  # "subscribed", "dropped_off", "blocked"
        drop_off_point: str = None
    ):
        """End and save a conversation"""
        if conversation_id not in self.active_conversations:
            return

        log = self.active_conversations[conversation_id]
        log.ended_at = datetime.now().isoformat()
        log.outcome = outcome
        log.drop_off_point = drop_off_point

        # Update stats
        if outcome == "subscribed":
            self.stats["subscriptions"] += 1
        elif outcome == "dropped_off":
            self.stats["drop_offs"] += 1
            if drop_off_point:
                self.stats["drop_off_points"][drop_off_point] = \
                    self.stats["drop_off_points"].get(drop_off_point, 0) + 1

        # Calculate conversion rate
        if self.stats["total_conversations"] > 0:
            self.stats["conversion_rate"] = \
                self.stats["subscriptions"] / self.stats["total_conversations"]

        # Save to file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log.to_dict()) + "\n")

        # Save stats
        self._save_stats()

        # Remove from active
        del self.active_conversations[conversation_id]

    def get_stats_summary(self) -> str:
        """Get a human-readable stats summary"""
        s = self.stats
        lines = [
            "=" * 50,
            "CONVERSATION ANALYTICS",
            "=" * 50,
            f"Total Conversations: {s['total_conversations']}",
            f"Subscriptions: {s['subscriptions']}",
            f"Drop-offs: {s['drop_offs']}",
            f"Conversion Rate: {s['conversion_rate']:.1%}",
            "",
            "DROP-OFF POINTS:",
        ]
        for point, count in sorted(s["drop_off_points"].items(), key=lambda x: -x[1]):
            lines.append(f"  {point}: {count}")

        lines.extend([
            "",
            "OBJECTIONS ENCOUNTERED:",
        ])
        for obj, count in sorted(s["objections"].items(), key=lambda x: -x[1]):
            lines.append(f"  {obj}: {count}")

        lines.extend([
            "",
            "REQUESTS (demand tracking):",
            f"  Snap: {s['requests']['snap']}",
            f"  Number: {s['requests']['number']}",
            f"  Other Social: {s['requests']['other_social']}",
            f"  Meet: {s['requests']['meet']}",
            f"  Free Content: {s['requests']['free_content']}",
            "",
            "PHASES REACHED:",
        ])
        for phase, count in sorted(s["phases_reached"].items(), key=lambda x: -x[1]):
            lines.append(f"  {phase}: {count}")

        lines.append("=" * 50)
        return "\n".join(lines)


# Global logger instance
logger = ConversationLogger()


# Convenience functions
def log_message(conversation_id: str, role: str, content: str, phase: str, images: List[str] = None):
    """Log a message"""
    logger.log_message(conversation_id, role, content, phase, images)


def end_conversation(conversation_id: str, outcome: str, drop_off_point: str = None):
    """End a conversation"""
    logger.end_conversation(conversation_id, outcome, drop_off_point)


def get_stats() -> str:
    """Get stats summary"""
    return logger.get_stats_summary()


if __name__ == "__main__":
    # Test the logger
    print("Testing conversation logger...")

    # Simulate a conversation
    logger.start_conversation("test123")
    logger.log_message("test123", "fan", "hey", "opener")
    logger.log_message("test123", "her", "heyyy", "opener")
    logger.log_message("test123", "fan", "ur hot", "opener")
    logger.log_message("test123", "her", "thanks babe", "opener")
    logger.log_message("test123", "fan", "can i get ur snap", "small_talk")
    logger.log_message("test123", "her", "i dont have snap but we can chat on my of", "small_talk")
    logger.log_message("test123", "fan", "nah im not paying for that", "of_redirect")
    logger.log_message("test123", "her", "aww ok [IMG:sad_face.jpg]", "post_of")
    logger.end_conversation("test123", "dropped_off", "post_of_refuse")

    print(logger.get_stats_summary())
