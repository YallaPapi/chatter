"""
Message Content Analysis Module for Chatter Training Data

Analyzes message-level metrics:
- Message length and talk-to-listen ratio
- Keyword extraction
- Opener patterns
- Closing language patterns
- Objection handling patterns

No AI/LLM calls - text analysis only.
"""

import json
import re
import statistics
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from collections import Counter, defaultdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.analysis.data_loader import (
    SubscriberTier, ConversationThread, Message,
    load_and_prepare_data, get_threads_by_tier
)

console = Console()


# ============================================================================
# TASK 20: Message Length and Ratio Analysis
# ============================================================================

@dataclass
class MessageMetrics:
    """Message-level metrics for a tier."""
    tier: str
    avg_creator_message_length: float = 0.0
    avg_subscriber_message_length: float = 0.0
    avg_messages_per_thread: float = 0.0
    avg_creator_messages_per_thread: float = 0.0
    avg_subscriber_messages_per_thread: float = 0.0
    talk_to_listen_ratio: float = 0.0  # creator messages / subscriber messages

    def to_dict(self) -> dict:
        return {
            "tier": self.tier,
            "avg_creator_message_length": round(self.avg_creator_message_length, 1),
            "avg_subscriber_message_length": round(self.avg_subscriber_message_length, 1),
            "avg_messages_per_thread": round(self.avg_messages_per_thread, 1),
            "avg_creator_messages_per_thread": round(self.avg_creator_messages_per_thread, 1),
            "avg_subscriber_messages_per_thread": round(self.avg_subscriber_messages_per_thread, 1),
            "talk_to_listen_ratio": round(self.talk_to_listen_ratio, 2),
        }


def calculate_message_metrics(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]]
) -> Dict[str, MessageMetrics]:
    """Calculate message metrics per tier."""
    results = {}

    for tier, threads in threads_by_tier.items():
        creator_lengths = []
        subscriber_lengths = []
        thread_message_counts = []
        thread_creator_counts = []
        thread_subscriber_counts = []

        for thread in threads:
            creator_count = 0
            subscriber_count = 0

            for msg in thread.all_messages:
                if not msg.text:
                    continue
                text_len = len(msg.text)

                if msg.role == "creator":
                    creator_lengths.append(text_len)
                    creator_count += 1
                elif msg.role == "subscriber":
                    subscriber_lengths.append(text_len)
                    subscriber_count += 1

            thread_message_counts.append(creator_count + subscriber_count)
            thread_creator_counts.append(creator_count)
            thread_subscriber_counts.append(subscriber_count)

        metrics = MessageMetrics(tier=tier.value)

        if creator_lengths:
            metrics.avg_creator_message_length = statistics.mean(creator_lengths)
        if subscriber_lengths:
            metrics.avg_subscriber_message_length = statistics.mean(subscriber_lengths)
        if thread_message_counts:
            metrics.avg_messages_per_thread = statistics.mean(thread_message_counts)
        if thread_creator_counts:
            metrics.avg_creator_messages_per_thread = statistics.mean(thread_creator_counts)
        if thread_subscriber_counts:
            metrics.avg_subscriber_messages_per_thread = statistics.mean(thread_subscriber_counts)

        # Talk-to-listen ratio (creator messages / subscriber messages)
        total_creator = sum(thread_creator_counts)
        total_subscriber = sum(thread_subscriber_counts)
        if total_subscriber > 0:
            metrics.talk_to_listen_ratio = total_creator / total_subscriber

        results[tier.value] = metrics

    return results


# ============================================================================
# TASK 21: Keyword Extraction
# ============================================================================

# Common words to exclude
STOP_WORDS = {
    "i", "me", "my", "you", "your", "we", "us", "the", "a", "an", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "can", "may", "might", "must",
    "shall", "to", "of", "in", "for", "on", "with", "at", "by", "from", "up",
    "about", "into", "over", "after", "it", "its", "this", "that", "these",
    "those", "what", "which", "who", "whom", "and", "but", "or", "nor", "so",
    "if", "then", "else", "when", "where", "why", "how", "all", "each", "every",
    "both", "few", "more", "most", "other", "some", "such", "no", "not", "only",
    "own", "same", "than", "too", "very", "just", "also", "as", "like", "get",
    "got", "im", "dont", "cant", "wont", "ive", "youre", "ill", "thats", "haha",
    "lol", "ok", "okay", "yeah", "yes", "no", "oh", "um", "uh", "well", "now",
    "here", "there", "really", "gonna", "want", "know", "think", "see", "go",
    "come", "make", "take", "let", "give", "tell", "say", "said", "one", "two",
    "first", "new", "good", "bad", "right", "back", "still", "even", "way",
    "any", "thing", "things", "lot", "much", "many", "something", "anything",
    "everything", "nothing", "someone", "anyone", "everyone", "time", "day",
}


def extract_keywords(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]],
    top_n: int = 30
) -> Dict[str, Dict[str, List[Tuple[str, int]]]]:
    """
    Extract top keywords by role for each tier.

    Returns:
        {tier: {creator: [(word, count)], subscriber: [(word, count)]}}
    """
    results = {}

    for tier, threads in threads_by_tier.items():
        creator_words: Counter = Counter()
        subscriber_words: Counter = Counter()

        for thread in threads:
            for msg in thread.all_messages:
                if not msg.text:
                    continue
                # Tokenize: lowercase, split on non-alpha
                words = re.findall(r'[a-z]+', msg.text.lower())

                # Filter stop words and short words
                words = [w for w in words if w not in STOP_WORDS and len(w) > 2]

                if msg.role == "creator":
                    creator_words.update(words)
                elif msg.role == "subscriber":
                    subscriber_words.update(words)

        results[tier.value] = {
            "creator": creator_words.most_common(top_n),
            "subscriber": subscriber_words.most_common(top_n),
        }

    return results


def extract_phrases(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]],
    role: str = "creator",
    top_n: int = 20
) -> Dict[str, List[Tuple[str, int]]]:
    """
    Extract common 2-3 word phrases for a role.

    Returns:
        {tier: [(phrase, count)]}
    """
    results = {}

    for tier, threads in threads_by_tier.items():
        phrase_counter: Counter = Counter()

        for thread in threads:
            for msg in thread.all_messages:
                if msg.role != role or not msg.text:
                    continue

                text = msg.text.lower()
                words = re.findall(r'[a-z]+', text)

                # 2-grams
                for i in range(len(words) - 1):
                    if words[i] not in STOP_WORDS or words[i+1] not in STOP_WORDS:
                        phrase = f"{words[i]} {words[i+1]}"
                        phrase_counter[phrase] += 1

                # 3-grams
                for i in range(len(words) - 2):
                    phrase = f"{words[i]} {words[i+1]} {words[i+2]}"
                    phrase_counter[phrase] += 1

        results[tier.value] = phrase_counter.most_common(top_n)

    return results


# ============================================================================
# TASK 22: Opener Analysis
# ============================================================================

@dataclass
class OpenerAnalysis:
    """Analysis of conversation openers."""
    tier: str
    total_threads: int = 0
    creator_opens_first: int = 0
    subscriber_opens_first: int = 0
    avg_opener_length: float = 0.0
    opener_patterns: Dict[str, int] = field(default_factory=dict)  # pattern -> count


def analyze_openers(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]]
) -> Dict[str, OpenerAnalysis]:
    """Analyze conversation opener patterns."""
    results = {}

    # Common opener patterns to look for
    opener_patterns = {
        "greeting": r'\b(hey|hi|hello|hii|heyy|heyyy)\b',
        "emoji_only": r'^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\s]+$',
        "pet_name": r'\b(baby|babe|daddy|honey|sweetie|hubby|love)\b',
        "question": r'\?',
        "compliment": r'\b(beautiful|gorgeous|sexy|hot|amazing|cute|pretty)\b',
        "miss_you": r'\b(miss|missed|missing)\b',
        "how_are_you": r'\bhow (are|r) (you|u)\b',
        "thank_you": r'\b(thank|thanks|thx)\b',
        "thinking_of_you": r'\b(thinking|thought) (of|about) (you|u)\b',
    }

    for tier, threads in threads_by_tier.items():
        analysis = OpenerAnalysis(tier=tier.value, total_threads=len(threads))
        opener_lengths = []
        pattern_counts: Counter = Counter()

        for thread in threads:
            messages = thread.all_messages
            if not messages:
                continue

            first_msg = messages[0]

            if first_msg.role == "creator":
                analysis.creator_opens_first += 1
            else:
                analysis.subscriber_opens_first += 1

            # Only analyze creator openers
            creator_opener = None
            for msg in messages:
                if msg.role == "creator":
                    creator_opener = msg
                    break

            if creator_opener and creator_opener.text:
                opener_lengths.append(len(creator_opener.text))
                text = creator_opener.text.lower()

                for pattern_name, pattern in opener_patterns.items():
                    if re.search(pattern, text, re.IGNORECASE):
                        pattern_counts[pattern_name] += 1

        if opener_lengths:
            analysis.avg_opener_length = statistics.mean(opener_lengths)

        analysis.opener_patterns = dict(pattern_counts.most_common(10))
        results[tier.value] = analysis

    return results


# ============================================================================
# TASK 23: Closing Language Analysis
# ============================================================================

@dataclass
class ClosingAnalysis:
    """Analysis of closing/money request patterns."""
    tier: str
    tip_request_patterns: Dict[str, int] = field(default_factory=dict)
    ppv_pitch_patterns: Dict[str, int] = field(default_factory=dict)
    price_mentions: Dict[str, int] = field(default_factory=dict)  # price range -> count
    urgency_patterns: Dict[str, int] = field(default_factory=dict)


def analyze_closing_language(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]]
) -> Dict[str, ClosingAnalysis]:
    """Analyze how creators ask for money."""
    results = {}

    # Patterns for tip requests
    tip_patterns = {
        "tip_me": r'\btip (me|for)\b',
        "send_tip": r'\bsend (a |me )?tip\b',
        "tip_amount": r'\btip \$?\d+\b',
        "tip_question": r'\b(can|could|would) (you|u) tip\b',
        "appreciation_tip": r'\b(appreciate|show).*(tip|support)\b',
    }

    # Patterns for PPV pitches
    ppv_patterns = {
        "want_to_see": r'\b(want|wanna) (to )?(see|watch)\b',
        "special_content": r'\b(special|exclusive|private) (content|video|pic)\b',
        "unlock_message": r'\bunlock\b',
        "send_something": r'\b(send|show) (you|u) something\b',
        "i_have": r'\bi have (a |something )',
        "just_for_you": r'\bjust for (you|u)\b',
    }

    # Urgency patterns
    urgency_patterns = {
        "limited_time": r'\b(limited|only today|expires|hurry)\b',
        "right_now": r'\b(right now|rn|now)\b',
        "before_gone": r'\b(before|until) (it\'?s?|they\'?re?) gone\b',
    }

    # Price mentions
    price_pattern = r'\$(\d+)'

    for tier, threads in threads_by_tier.items():
        analysis = ClosingAnalysis(tier=tier.value)
        tip_counts: Counter = Counter()
        ppv_counts: Counter = Counter()
        urgency_counts: Counter = Counter()
        price_ranges: Counter = Counter()

        for thread in threads:
            for msg in thread.all_messages:
                if msg.role != "creator" or not msg.text:
                    continue

                text = msg.text.lower()

                # Check tip patterns
                for pattern_name, pattern in tip_patterns.items():
                    if re.search(pattern, text, re.IGNORECASE):
                        tip_counts[pattern_name] += 1

                # Check PPV patterns
                for pattern_name, pattern in ppv_patterns.items():
                    if re.search(pattern, text, re.IGNORECASE):
                        ppv_counts[pattern_name] += 1

                # Check urgency patterns
                for pattern_name, pattern in urgency_patterns.items():
                    if re.search(pattern, text, re.IGNORECASE):
                        urgency_counts[pattern_name] += 1

                # Extract prices
                prices = re.findall(price_pattern, text)
                for price in prices:
                    price_val = int(price)
                    if price_val <= 10:
                        price_ranges["$1-10"] += 1
                    elif price_val <= 25:
                        price_ranges["$11-25"] += 1
                    elif price_val <= 50:
                        price_ranges["$26-50"] += 1
                    elif price_val <= 100:
                        price_ranges["$51-100"] += 1
                    else:
                        price_ranges["$100+"] += 1

        analysis.tip_request_patterns = dict(tip_counts.most_common(10))
        analysis.ppv_pitch_patterns = dict(ppv_counts.most_common(10))
        analysis.urgency_patterns = dict(urgency_counts.most_common(10))
        analysis.price_mentions = dict(price_ranges)

        results[tier.value] = analysis

    return results


# ============================================================================
# TASK 24: Objection Handling Analysis
# ============================================================================

@dataclass
class ObjectionAnalysis:
    """Analysis of objection handling patterns."""
    tier: str
    objection_patterns: Dict[str, int] = field(default_factory=dict)
    response_patterns: Dict[str, int] = field(default_factory=dict)
    negotiation_count: int = 0


def analyze_objection_handling(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]]
) -> Dict[str, ObjectionAnalysis]:
    """Analyze how creators handle objections."""
    results = {}

    # Subscriber objection patterns
    objection_patterns = {
        "too_expensive": r'\b(expensive|too much|cost|afford|cheap)\b',
        "no_money": r'\b(no money|broke|don\'t have|can\'t afford)\b',
        "maybe_later": r'\b(later|next time|payday|tomorrow|wait)\b',
        "not_sure": r'\b(not sure|think about|consider|maybe)\b',
        "already_bought": r'\b(already|bought|have it)\b',
    }

    # Creator response patterns
    response_patterns = {
        "discount_offer": r'\b(discount|off|special price|deal)\b',
        "payment_plan": r'\b(pay later|payment|installment)\b',
        "lower_option": r'\b(smaller|shorter|cheaper option|instead)\b',
        "value_add": r'\b(bonus|extra|include|free)\b',
        "scarcity": r'\b(only|last|limited|exclusive)\b',
        "understanding": r'\b(understand|get it|no worries|okay)\b',
        "persistence": r'\b(trust me|worth it|promise)\b',
    }

    for tier, threads in threads_by_tier.items():
        analysis = ObjectionAnalysis(tier=tier.value)
        obj_counts: Counter = Counter()
        resp_counts: Counter = Counter()
        negotiation_threads = 0

        for thread in threads:
            thread_has_objection = False

            for i, msg in enumerate(thread.all_messages):
                if not msg.text:
                    continue
                text = msg.text.lower()

                if msg.role == "subscriber":
                    # Check for objections
                    for pattern_name, pattern in objection_patterns.items():
                        if re.search(pattern, text, re.IGNORECASE):
                            obj_counts[pattern_name] += 1
                            thread_has_objection = True

                elif msg.role == "creator":
                    # Check for response patterns
                    for pattern_name, pattern in response_patterns.items():
                        if re.search(pattern, text, re.IGNORECASE):
                            resp_counts[pattern_name] += 1

            if thread_has_objection:
                negotiation_threads += 1

        analysis.objection_patterns = dict(obj_counts.most_common(10))
        analysis.response_patterns = dict(resp_counts.most_common(10))
        analysis.negotiation_count = negotiation_threads

        results[tier.value] = analysis

    return results


# ============================================================================
# Main Runner
# ============================================================================

def print_message_analysis(
    message_metrics: Dict[str, MessageMetrics],
    keywords: Dict[str, Dict[str, List[Tuple[str, int]]]],
    openers: Dict[str, OpenerAnalysis],
    closings: Dict[str, ClosingAnalysis],
    objections: Dict[str, ObjectionAnalysis],
):
    """Print formatted message analysis results."""
    console.print("\n[bold cyan]=== MESSAGE CONTENT ANALYSIS ===[/bold cyan]\n")

    # Message metrics table
    table = Table(title="Message Metrics by Tier")
    table.add_column("Tier", style="cyan")
    table.add_column("Avg Msgs/Thread", justify="right")
    table.add_column("Creator Msg Len", justify="right")
    table.add_column("Sub Msg Len", justify="right")
    table.add_column("Talk:Listen", justify="right")

    for tier in ["new", "low", "medium", "high", "whale"]:
        m = message_metrics.get(tier)
        if m:
            table.add_row(
                tier.upper(),
                f"{m.avg_messages_per_thread:.1f}",
                f"{m.avg_creator_message_length:.0f} chars",
                f"{m.avg_subscriber_message_length:.0f} chars",
                f"{m.talk_to_listen_ratio:.2f}",
            )
    console.print(table)

    # Top keywords by tier
    console.print("\n[bold cyan]=== TOP KEYWORDS BY TIER ===[/bold cyan]\n")

    for tier in ["new", "low", "medium", "high", "whale"]:
        if tier in keywords:
            console.print(f"[bold yellow]{tier.upper()}[/bold yellow]")
            creator_kw = keywords[tier].get("creator", [])[:10]
            sub_kw = keywords[tier].get("subscriber", [])[:10]

            console.print(f"  Creator: {', '.join(w for w, c in creator_kw)}")
            console.print(f"  Subscriber: {', '.join(w for w, c in sub_kw)}")
            console.print()

    # Opener patterns
    console.print("\n[bold cyan]=== OPENER PATTERNS ===[/bold cyan]\n")

    for tier in ["new", "low", "medium", "high", "whale"]:
        if tier in openers:
            o = openers[tier]
            console.print(f"[bold yellow]{tier.upper()}[/bold yellow]")
            console.print(f"  Creator opens first: {o.creator_opens_first}/{o.total_threads} ({o.creator_opens_first/max(1,o.total_threads)*100:.0f}%)")
            console.print(f"  Avg opener length: {o.avg_opener_length:.0f} chars")
            if o.opener_patterns:
                top_patterns = list(o.opener_patterns.items())[:5]
                console.print(f"  Top patterns: {', '.join(f'{p}({c})' for p, c in top_patterns)}")
            console.print()

    # Closing patterns
    console.print("\n[bold cyan]=== MONEY REQUEST PATTERNS ===[/bold cyan]\n")

    for tier in ["new", "low", "medium", "high", "whale"]:
        if tier in closings:
            c = closings[tier]
            console.print(f"[bold yellow]{tier.upper()}[/bold yellow]")
            if c.ppv_pitch_patterns:
                console.print(f"  PPV: {', '.join(f'{p}({cnt})' for p, cnt in list(c.ppv_pitch_patterns.items())[:3])}")
            if c.tip_request_patterns:
                console.print(f"  Tips: {', '.join(f'{p}({cnt})' for p, cnt in list(c.tip_request_patterns.items())[:3])}")
            if c.price_mentions:
                console.print(f"  Prices: {c.price_mentions}")
            console.print()

    # Objection handling
    console.print("\n[bold cyan]=== OBJECTION HANDLING ===[/bold cyan]\n")

    table = Table(title="Negotiations by Tier")
    table.add_column("Tier", style="cyan")
    table.add_column("Threads w/ Objections", justify="right")
    table.add_column("Top Objections", style="yellow")
    table.add_column("Top Responses", style="green")

    for tier in ["new", "low", "medium", "high", "whale"]:
        if tier in objections:
            obj = objections[tier]
            top_obj = list(obj.objection_patterns.keys())[:2]
            top_resp = list(obj.response_patterns.keys())[:2]
            table.add_row(
                tier.upper(),
                str(obj.negotiation_count),
                ", ".join(top_obj) if top_obj else "N/A",
                ", ".join(top_resp) if top_resp else "N/A",
            )

    console.print(table)


def run_message_analysis(
    parsed_dir: Path = Path("data/parsed_conversations"),
    output_dir: Path = Path("data/insights/raw"),
    show_output: bool = True
) -> Dict[str, Any]:
    """Run full message content analysis."""

    # Load data
    threads, report = load_and_prepare_data(parsed_dir, show_progress=True, print_report=False)
    threads_by_tier = get_threads_by_tier(threads)

    # Run all analyses
    console.print("[blue]Analyzing message metrics...[/blue]")
    message_metrics = calculate_message_metrics(threads_by_tier)

    console.print("[blue]Extracting keywords...[/blue]")
    keywords = extract_keywords(threads_by_tier)
    phrases = extract_phrases(threads_by_tier, role="creator")

    console.print("[blue]Analyzing openers...[/blue]")
    openers = analyze_openers(threads_by_tier)

    console.print("[blue]Analyzing closing language...[/blue]")
    closings = analyze_closing_language(threads_by_tier)

    console.print("[blue]Analyzing objection handling...[/blue]")
    objections = analyze_objection_handling(threads_by_tier)

    # Print results
    if show_output:
        print_message_analysis(message_metrics, keywords, openers, closings, objections)

    # Compile and save results
    results = {
        "message_metrics": {k: v.to_dict() for k, v in message_metrics.items()},
        "keywords": keywords,
        "creator_phrases": phrases,
        "openers": {k: {
            "tier": v.tier,
            "total_threads": v.total_threads,
            "creator_opens_first": v.creator_opens_first,
            "subscriber_opens_first": v.subscriber_opens_first,
            "avg_opener_length": round(v.avg_opener_length, 1),
            "opener_patterns": v.opener_patterns,
        } for k, v in openers.items()},
        "closings": {k: {
            "tier": v.tier,
            "tip_request_patterns": v.tip_request_patterns,
            "ppv_pitch_patterns": v.ppv_pitch_patterns,
            "price_mentions": v.price_mentions,
            "urgency_patterns": v.urgency_patterns,
        } for k, v in closings.items()},
        "objections": {k: {
            "tier": v.tier,
            "objection_patterns": v.objection_patterns,
            "response_patterns": v.response_patterns,
            "negotiation_count": v.negotiation_count,
        } for k, v in objections.items()},
    }

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "message_analysis.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if show_output:
        console.print(f"\n[green]Results saved to {output_path}[/green]")

    return results


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run message content analysis")
    parser.add_argument(
        "--input-dir",
        default="data/parsed_conversations",
        help="Parsed conversations directory"
    )
    parser.add_argument(
        "--output-dir",
        default="data/insights/raw",
        help="Output directory for results"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output"
    )

    args = parser.parse_args()

    run_message_analysis(
        parsed_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        show_output=not args.quiet
    )
