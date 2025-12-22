# -*- coding: utf-8 -*-
"""
Objection Analysis Module

Extracts objection patterns from subscriber messages, tracks creator responses,
and measures effectiveness based on whether a sale followed.
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple
from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.progress import Progress

console = Console()


# Objection pattern definitions
OBJECTION_PATTERNS = {
    "price": {
        "patterns": [
            r"\btoo expensive\b",
            r"\bcan'?t afford\b",
            r"\btoo much\b",
            r"\bthat'?s a lot\b",
            r"\bbroke\b",
            r"\bno money\b",
            r"\bdon'?t have (the )?money\b",
            r"\bout of my (price )?range\b",
            r"\bbudget\b",
            r"\bcheaper\b",
            r"\bdiscount\b",
            r"\bexpensive\b",
            r"\bcost(s)? too much\b",
            r"\bpoor\b",
            r"\bcan'?t pay\b",
        ],
        "description": "Price/affordability concerns"
    },
    "timing": {
        "patterns": [
            r"\bmaybe later\b",
            r"\bnot (right )?now\b",
            r"\bnext time\b",
            r"\bafter payday\b",
            r"\bwhen i get paid\b",
            r"\bpayday\b",
            r"\bgotta wait\b",
            r"\blater\b",
            r"\banother time\b",
            r"\btomorrow\b",
            r"\bnext week\b",
            r"\bbusy (right )?now\b",
            r"\bat work\b",
        ],
        "description": "Timing/not ready now"
    },
    "trust": {
        "patterns": [
            r"\bis it worth\b",
            r"\bhow do i know\b",
            r"\bwhat if\b",
            r"\bscam\b",
            r"\bfake\b",
            r"\bprove\b",
            r"\bshow me first\b",
            r"\bpreview\b",
            r"\bbefore i (buy|pay)\b",
            r"\btrust\b",
            r"\breal\?\b",
        ],
        "description": "Trust/verification concerns"
    },
    "need": {
        "patterns": [
            r"\bi don'?t need\b",
            r"\balready have\b",
            r"\bnot interested\b",
            r"\bnot (really )?into\b",
            r"\bdon'?t want\b",
            r"\bnot for me\b",
            r"\bi'?m good\b",
            r"\bno thanks\b",
            r"\bpass\b",
        ],
        "description": "Don't need/not interested"
    },
    "commitment": {
        "patterns": [
            r"\bi'?ll think about it\b",
            r"\blet me (think|see)\b",
            r"\bnot sure\b",
            r"\bidk\b",
            r"\bi don'?t know\b",
            r"\bmaybe\b",
            r"\bpossibly\b",
            r"\bwe'?ll see\b",
            r"\bconsidering\b",
        ],
        "description": "Hesitation/non-committal"
    }
}


@dataclass
class ObjectionInstance:
    """A single objection found in a conversation."""
    objection_text: str
    objection_type: str
    matched_pattern: str
    message_index: int  # Position in conversation

    # Response tracking
    response_text: Optional[str] = None
    response_chatter: Optional[str] = None
    messages_until_response: int = 0

    # Outcome tracking
    resulted_in_sale: bool = False
    messages_to_sale: Optional[int] = None
    sale_amount: Optional[float] = None

    # Context
    subscriber_tier: Optional[str] = None
    thread_id: Optional[str] = None
    conversation_approach: Optional[str] = None


@dataclass
class ObjectionStats:
    """Aggregated statistics for an objection type."""
    objection_type: str
    total_count: int = 0
    resulted_in_sale: int = 0
    total_sale_amount: float = 0.0

    # By tier breakdown
    by_tier: Dict[str, Dict] = field(default_factory=dict)

    # Top responses
    successful_responses: List[Tuple[str, float, str]] = field(default_factory=list)  # (response, sale_amount, chatter)
    failed_responses: List[Tuple[str, str]] = field(default_factory=list)  # (response, chatter)

    @property
    def success_rate(self) -> float:
        return (self.resulted_in_sale / self.total_count * 100) if self.total_count > 0 else 0.0

    @property
    def avg_sale_after_objection(self) -> float:
        return (self.total_sale_amount / self.resulted_in_sale) if self.resulted_in_sale > 0 else 0.0


def compile_patterns() -> Dict[str, List[re.Pattern]]:
    """Compile all objection patterns for efficient matching."""
    compiled = {}
    for obj_type, config in OBJECTION_PATTERNS.items():
        compiled[obj_type] = [
            re.compile(p, re.IGNORECASE)
            for p in config["patterns"]
        ]
    return compiled


def find_objections_in_message(
    text: str,
    compiled_patterns: Dict[str, List[re.Pattern]]
) -> List[Tuple[str, str]]:
    """Find all objection patterns in a message.

    Returns list of (objection_type, matched_pattern) tuples.
    """
    found = []
    text_lower = text.lower()

    for obj_type, patterns in compiled_patterns.items():
        for pattern in patterns:
            if pattern.search(text_lower):
                found.append((obj_type, pattern.pattern))
                break  # Only one match per type per message

    return found


def extract_objections_from_thread(
    thread,  # ConversationThread from data_loader
    compiled_patterns: Dict[str, List[re.Pattern]]
) -> List[ObjectionInstance]:
    """Extract all objections from a conversation thread.

    For each objection found:
    1. Records the objection text and type
    2. Finds the creator's response (next creator message)
    3. Tracks whether a sale occurred within 5 messages
    """
    objections = []

    # Flatten all messages from thread with metadata
    all_messages = []
    for ss in thread.screenshots:
        if ss.empty or not ss.messages:
            continue
        for msg in ss.messages:
            all_messages.append({
                "role": msg.role,
                "text": msg.text or "",
                "outcome": ss.outcome,
                "context": ss.context,
            })

    if not all_messages:
        return []

    # Scan for objections in subscriber messages
    for i, msg in enumerate(all_messages):
        if msg["role"] != "subscriber":
            continue

        matches = find_objections_in_message(msg["text"], compiled_patterns)

        for obj_type, pattern in matches:
            obj = ObjectionInstance(
                objection_text=msg["text"][:200],  # Truncate long messages
                objection_type=obj_type,
                matched_pattern=pattern,
                message_index=i,
                subscriber_tier=thread.tier.value if thread.tier else None,
                thread_id=thread.thread_id,
                conversation_approach=msg.get("context", {}).creator_approach if msg.get("context") else None,
            )

            # Find creator response (next creator message after objection)
            for j in range(i + 1, min(i + 5, len(all_messages))):
                if all_messages[j]["role"] == "creator":
                    obj.response_text = all_messages[j]["text"][:200]
                    obj.response_chatter = thread.chatter
                    obj.messages_until_response = j - i
                    break

            # Check if sale occurred within 5 messages after objection
            for j in range(i + 1, min(i + 10, len(all_messages))):
                outcome = all_messages[j].get("outcome")
                if outcome and outcome.sale_in_screenshot and outcome.sale_amount:
                    obj.resulted_in_sale = True
                    obj.messages_to_sale = j - i
                    obj.sale_amount = outcome.sale_amount
                    break

            objections.append(obj)

    return objections


def analyze_all_objections(
    threads: List,  # List[ConversationThread]
    compiled_patterns: Optional[Dict] = None
) -> Tuple[List[ObjectionInstance], Dict[str, ObjectionStats]]:
    """Analyze objections across all conversation threads.

    Returns:
        - List of all ObjectionInstance found
        - Dict of ObjectionStats aggregated by type
    """
    if compiled_patterns is None:
        compiled_patterns = compile_patterns()

    all_objections = []
    stats_by_type = {t: ObjectionStats(objection_type=t) for t in OBJECTION_PATTERNS.keys()}

    with Progress() as progress:
        task = progress.add_task("Analyzing objections...", total=len(threads))

        for thread in threads:
            objections = extract_objections_from_thread(thread, compiled_patterns)
            all_objections.extend(objections)

            # Aggregate stats
            for obj in objections:
                stats = stats_by_type[obj.objection_type]
                stats.total_count += 1

                if obj.resulted_in_sale:
                    stats.resulted_in_sale += 1
                    stats.total_sale_amount += obj.sale_amount or 0

                    if obj.response_text:
                        stats.successful_responses.append((
                            obj.response_text,
                            obj.sale_amount or 0,
                            obj.response_chatter or "unknown"
                        ))
                else:
                    if obj.response_text:
                        stats.failed_responses.append((
                            obj.response_text,
                            obj.response_chatter or "unknown"
                        ))

                # By tier breakdown
                tier = obj.subscriber_tier or "unknown"
                if tier not in stats.by_tier:
                    stats.by_tier[tier] = {
                        "count": 0,
                        "sales": 0,
                        "total_amount": 0
                    }
                stats.by_tier[tier]["count"] += 1
                if obj.resulted_in_sale:
                    stats.by_tier[tier]["sales"] += 1
                    stats.by_tier[tier]["total_amount"] += obj.sale_amount or 0

            progress.update(task, advance=1)

    return all_objections, stats_by_type


def get_top_responses(
    stats: ObjectionStats,
    top_n: int = 5
) -> Dict[str, List]:
    """Get top successful and failed responses for an objection type."""

    # Sort successful by sale amount
    sorted_successful = sorted(
        stats.successful_responses,
        key=lambda x: x[1],
        reverse=True
    )[:top_n]

    # Get unique failed responses
    seen = set()
    unique_failed = []
    for resp, chatter in stats.failed_responses:
        resp_key = resp[:50]  # Dedupe by first 50 chars
        if resp_key not in seen:
            seen.add(resp_key)
            unique_failed.append((resp, chatter))
            if len(unique_failed) >= top_n:
                break

    return {
        "successful": sorted_successful,
        "failed": unique_failed
    }


def generate_objection_report(
    stats_by_type: Dict[str, ObjectionStats],
    output_path: Optional[Path] = None
) -> str:
    """Generate a markdown report of objection analysis."""

    lines = [
        "# Objection Handling Analysis",
        "",
        "Analysis of subscriber objections and creator response effectiveness.",
        "",
        "---",
        "",
        "## Summary",
        "",
        "| Objection Type | Count | Success Rate | Avg Sale After | Description |",
        "|----------------|-------|--------------|----------------|-------------|",
    ]

    # Sort by count
    sorted_types = sorted(
        stats_by_type.items(),
        key=lambda x: x[1].total_count,
        reverse=True
    )

    for obj_type, stats in sorted_types:
        desc = OBJECTION_PATTERNS[obj_type]["description"]
        lines.append(
            f"| {obj_type.title()} | {stats.total_count} | "
            f"{stats.success_rate:.1f}% | ${stats.avg_sale_after_objection:.0f} | {desc} |"
        )

    lines.extend(["", "---", ""])

    # Detailed breakdown by type
    for obj_type, stats in sorted_types:
        if stats.total_count == 0:
            continue

        lines.extend([
            f"## {obj_type.title()} Objections",
            "",
            f"**Total instances:** {stats.total_count}",
            f"**Resulted in sale:** {stats.resulted_in_sale} ({stats.success_rate:.1f}%)",
            f"**Average sale amount:** ${stats.avg_sale_after_objection:.0f}",
            "",
        ])

        # By tier breakdown
        if stats.by_tier:
            lines.extend([
                "### By Subscriber Tier",
                "",
                "| Tier | Count | Sales | Success Rate | Avg Sale |",
                "|------|-------|-------|--------------|----------|",
            ])
            for tier, data in sorted(stats.by_tier.items()):
                rate = (data["sales"] / data["count"] * 100) if data["count"] > 0 else 0
                avg = (data["total_amount"] / data["sales"]) if data["sales"] > 0 else 0
                lines.append(f"| {tier.upper()} | {data['count']} | {data['sales']} | {rate:.1f}% | ${avg:.0f} |")
            lines.append("")

        # Top responses
        top = get_top_responses(stats)

        if top["successful"]:
            lines.extend([
                "### Successful Responses (led to sale)",
                "",
            ])
            for i, (resp, amount, chatter) in enumerate(top["successful"], 1):
                lines.extend([
                    f"**{i}. {chatter}** (${amount:.0f} sale)",
                    f"> \"{resp}\"",
                    "",
                ])

        if top["failed"]:
            lines.extend([
                "### Responses That Didn't Convert",
                "",
            ])
            for i, (resp, chatter) in enumerate(top["failed"][:3], 1):
                lines.append(f"{i}. ({chatter}) \"{resp}\"")
            lines.append("")

        lines.extend(["---", ""])

    report = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        console.print(f"[green]Report saved to {output_path}[/green]")

    return report


def save_objections_json(
    objections: List[ObjectionInstance],
    output_path: Path
) -> None:
    """Save all objection instances to JSON for further analysis."""
    data = []
    for obj in objections:
        data.append({
            "objection_text": obj.objection_text,
            "objection_type": obj.objection_type,
            "matched_pattern": obj.matched_pattern,
            "response_text": obj.response_text,
            "response_chatter": obj.response_chatter,
            "resulted_in_sale": obj.resulted_in_sale,
            "messages_to_sale": obj.messages_to_sale,
            "sale_amount": obj.sale_amount,
            "subscriber_tier": obj.subscriber_tier,
            "thread_id": obj.thread_id,
        })

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    console.print(f"[green]Saved {len(data)} objections to {output_path}[/green]")


def print_summary_table(stats_by_type: Dict[str, ObjectionStats]) -> None:
    """Print a rich table summary of objection stats."""
    table = Table(title="Objection Analysis Summary")

    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Success Rate", justify="right")
    table.add_column("Avg Sale", justify="right", style="green")
    table.add_column("Total Revenue", justify="right", style="green")

    for obj_type, stats in sorted(stats_by_type.items(), key=lambda x: x[1].total_count, reverse=True):
        table.add_row(
            obj_type.title(),
            str(stats.total_count),
            f"{stats.success_rate:.1f}%",
            f"${stats.avg_sale_after_objection:.0f}",
            f"${stats.total_sale_amount:.0f}"
        )

    console.print(table)


def main():
    """Run objection analysis on parsed conversation data."""
    from scripts.analysis.data_loader import load_and_prepare_data

    # Load data
    console.print("[bold]Loading conversation data...[/bold]")
    threads, _ = load_and_prepare_data(Path("data/parsed_conversations"))
    console.print(f"[green]Loaded {len(threads)} conversation threads[/green]")

    # Analyze objections
    console.print("\n[bold]Analyzing objections...[/bold]")
    objections, stats = analyze_all_objections(threads)

    console.print(f"\n[green]Found {len(objections)} total objections[/green]")

    # Print summary
    print_summary_table(stats)

    # Save outputs
    output_dir = Path("data/insights")

    generate_objection_report(
        stats,
        output_dir / "objection_analysis.md"
    )

    save_objections_json(
        objections,
        output_dir / "raw" / "objection_instances.json"
    )

    console.print("\n[bold green]Objection analysis complete![/bold green]")


if __name__ == "__main__":
    main()
