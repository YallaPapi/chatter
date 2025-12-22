# -*- coding: utf-8 -*-
"""
Conversation Example Extractor

Extracts full conversation context around techniques, objections, and sales
for use in evidence-based playbooks.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple
from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@dataclass
class ConversationExample:
    """A conversation example with full context."""
    # Identification
    thread_id: str
    chatter: str
    tier: str

    # Full conversation
    messages: List[Dict]  # [{"role": "creator/subscriber", "text": "..."}]

    # Highlight region
    highlight_start: int  # Message index where key action starts
    highlight_end: int    # Message index where key action ends

    # Outcome
    resulted_in_sale: bool
    sale_amount: Optional[float] = None
    messages_to_outcome: Optional[int] = None

    # Classification
    example_type: str = ""  # "objection", "opener", "closer", "technique"
    subtype: str = ""       # e.g., "price", "timing" for objections
    approach: Optional[str] = None

    # Analysis
    analysis: str = ""      # Why this worked/failed

    def to_markdown(self, include_analysis: bool = True) -> str:
        """Format example as markdown for playbook."""
        lines = []

        # Header
        outcome = f"${self.sale_amount:.0f} sale" if self.sale_amount else "No sale"
        lines.append(f"**{self.chatter}** ({self.tier.upper()} tier) - {outcome}")
        lines.append("")

        # Messages
        for i, msg in enumerate(self.messages):
            role = msg["role"].upper()
            text = msg["text"]

            # Highlight the key messages
            if self.highlight_start <= i <= self.highlight_end:
                if role == "SUBSCRIBER":
                    lines.append(f"> **SUB:** {text}")
                else:
                    lines.append(f"> **CREATOR:** {text}")
            else:
                if role == "SUBSCRIBER":
                    lines.append(f"> SUB: {text}")
                else:
                    lines.append(f"> CREATOR: {text}")

        if self.resulted_in_sale and self.sale_amount:
            lines.append(f"> [SALE: ${self.sale_amount:.0f}]")

        if include_analysis and self.analysis:
            lines.append("")
            lines.append(f"*{self.analysis}*")

        return "\n".join(lines)


class ConversationExampleExtractor:
    """Extracts conversation examples from parsed data."""

    def __init__(self, threads: List):
        """
        Initialize with conversation threads.

        Args:
            threads: List of ConversationThread objects from data_loader
        """
        self.threads = threads
        self._message_cache = {}
        self._build_cache()

    def _build_cache(self):
        """Build cache of flattened messages per thread."""
        for thread in self.threads:
            messages = []
            outcomes = []

            for ss in thread.screenshots:
                if ss.empty or not ss.messages:
                    continue
                for msg in ss.messages:
                    messages.append({
                        "role": msg.role,
                        "text": msg.text or ""
                    })
                # Track outcomes per message position
                if ss.outcome and ss.outcome.sale_in_screenshot:
                    outcomes.append({
                        "position": len(messages) - 1,
                        "sale_amount": ss.outcome.sale_amount
                    })

            self._message_cache[thread.thread_id] = {
                "messages": messages,
                "outcomes": outcomes,
                "tier": thread.tier.value if thread.tier else "unknown",
                "chatter": thread.chatter or "unknown",
                "approach": self._get_primary_approach(thread)
            }

    def _get_primary_approach(self, thread) -> Optional[str]:
        """Get most common approach in thread."""
        approaches = defaultdict(int)
        for ss in thread.screenshots:
            if ss.context and ss.context.creator_approach:
                approaches[ss.context.creator_approach] += 1
        if approaches:
            return max(approaches, key=approaches.get)
        return None

    def get_objection_examples(
        self,
        objection_type: str,
        successful: bool = True,
        min_context: int = 3,
        max_context: int = 8,
        limit: int = 10
    ) -> List[ConversationExample]:
        """
        Get conversation examples around objections.

        Args:
            objection_type: "price", "timing", "trust", "need", "commitment"
            successful: If True, get examples that led to sale
            min_context: Minimum messages before objection
            max_context: Maximum messages after objection
            limit: Max examples to return
        """
        # Load objection instances
        objection_file = Path("data/insights/raw/objection_instances.json")
        if not objection_file.exists():
            console.print("[yellow]No objection data found. Run objection_analysis.py first.[/yellow]")
            return []

        with open(objection_file, "r", encoding="utf-8") as f:
            objections = json.load(f)

        # Filter by type and outcome
        filtered = [
            obj for obj in objections
            if obj["objection_type"] == objection_type
            and obj["resulted_in_sale"] == successful
            and obj["thread_id"] in self._message_cache
        ]

        # Sort by sale amount (descending) for successful, by thread for failed
        if successful:
            filtered.sort(key=lambda x: x.get("sale_amount") or 0, reverse=True)
        else:
            filtered.sort(key=lambda x: x.get("thread_id", ""))

        examples = []
        seen_responses = set()  # Dedupe by response text

        for obj in filtered:
            if len(examples) >= limit:
                break

            # Dedupe by first 50 chars of response
            response_key = (obj.get("response_text") or "")[:50]
            if response_key in seen_responses:
                continue
            seen_responses.add(response_key)

            thread_data = self._message_cache[obj["thread_id"]]
            messages = thread_data["messages"]

            # Find objection in messages
            obj_text = obj["objection_text"]
            obj_idx = None
            for i, msg in enumerate(messages):
                if msg["role"] == "subscriber" and obj_text[:30] in msg["text"]:
                    obj_idx = i
                    break

            if obj_idx is None:
                continue

            # Extract context window
            start = max(0, obj_idx - min_context)
            end = min(len(messages), obj_idx + max_context)

            # Find response index
            response_idx = obj_idx
            for i in range(obj_idx + 1, min(obj_idx + 5, len(messages))):
                if messages[i]["role"] == "creator":
                    response_idx = i
                    break

            example = ConversationExample(
                thread_id=obj["thread_id"],
                chatter=obj.get("response_chatter") or thread_data["chatter"],
                tier=obj.get("subscriber_tier") or thread_data["tier"],
                messages=messages[start:end],
                highlight_start=obj_idx - start,
                highlight_end=response_idx - start,
                resulted_in_sale=obj["resulted_in_sale"],
                sale_amount=obj.get("sale_amount"),
                messages_to_outcome=obj.get("messages_to_sale"),
                example_type="objection",
                subtype=objection_type,
                approach=thread_data["approach"],
                analysis=self._generate_analysis(obj, successful)
            )
            examples.append(example)

        return examples

    def get_successful_sale_examples(
        self,
        tier: str,
        min_sale: float = 0,
        limit: int = 5
    ) -> List[ConversationExample]:
        """Get full conversation examples of successful sales by tier."""
        examples = []

        for thread in self.threads:
            if len(examples) >= limit:
                break

            thread_tier = thread.tier.value if thread.tier else "unknown"
            if thread_tier != tier.lower():
                continue

            if thread.total_sale_amount < min_sale:
                continue

            thread_data = self._message_cache.get(thread.thread_id)
            if not thread_data or not thread_data["messages"]:
                continue

            messages = thread_data["messages"]

            # Find sale position
            sale_idx = len(messages) - 1
            for outcome in thread_data["outcomes"]:
                sale_idx = min(sale_idx, outcome["position"])

            # Get opener to sale
            example = ConversationExample(
                thread_id=thread.thread_id,
                chatter=thread_data["chatter"],
                tier=tier,
                messages=messages[:min(sale_idx + 3, len(messages))],
                highlight_start=0,
                highlight_end=min(2, len(messages) - 1),  # Highlight opener
                resulted_in_sale=True,
                sale_amount=thread.total_sale_amount,
                example_type="full_sale",
                subtype=tier,
                approach=thread_data["approach"]
            )
            examples.append(example)

        # Sort by sale amount
        examples.sort(key=lambda x: x.sale_amount or 0, reverse=True)
        return examples[:limit]

    def get_opener_examples(
        self,
        tier: Optional[str] = None,
        successful: bool = True,
        limit: int = 10
    ) -> List[ConversationExample]:
        """Get examples of conversation openers."""
        examples = []

        for thread in self.threads:
            if len(examples) >= limit:
                break

            if tier:
                thread_tier = thread.tier.value if thread.tier else "unknown"
                if thread_tier != tier.lower():
                    continue

            # Check if successful based on sales
            has_sale = thread.total_sale_amount > 0
            if successful != has_sale:
                continue

            thread_data = self._message_cache.get(thread.thread_id)
            if not thread_data or len(thread_data["messages"]) < 3:
                continue

            messages = thread_data["messages"]

            # Get first few messages
            example = ConversationExample(
                thread_id=thread.thread_id,
                chatter=thread_data["chatter"],
                tier=thread_data["tier"],
                messages=messages[:min(6, len(messages))],
                highlight_start=0,
                highlight_end=1,  # First creator message
                resulted_in_sale=has_sale,
                sale_amount=thread.total_sale_amount if has_sale else None,
                example_type="opener",
                subtype="successful" if successful else "failed",
                approach=thread_data["approach"]
            )
            examples.append(example)

        return examples

    def get_chatter_examples(
        self,
        chatter_name: str,
        limit: int = 10
    ) -> List[ConversationExample]:
        """Get best examples from a specific chatter."""
        examples = []

        chatter_threads = [
            t for t in self.threads
            if t.chatter and t.chatter.lower() == chatter_name.lower()
        ]

        # Sort by total sale amount
        chatter_threads.sort(key=lambda t: t.total_sale_amount, reverse=True)

        for thread in chatter_threads[:limit]:
            thread_data = self._message_cache.get(thread.thread_id)
            if not thread_data or not thread_data["messages"]:
                continue

            messages = thread_data["messages"]

            example = ConversationExample(
                thread_id=thread.thread_id,
                chatter=chatter_name,
                tier=thread_data["tier"],
                messages=messages[:min(15, len(messages))],
                highlight_start=0,
                highlight_end=min(3, len(messages) - 1),
                resulted_in_sale=thread.total_sale_amount > 0,
                sale_amount=thread.total_sale_amount,
                example_type="chatter_style",
                subtype=chatter_name,
                approach=thread_data["approach"]
            )
            examples.append(example)

        return examples

    def _generate_analysis(self, objection: Dict, successful: bool) -> str:
        """Generate analysis text for an objection example."""
        obj_type = objection["objection_type"]
        response = objection.get("response_text", "")

        if successful:
            analyses = {
                "price": "Asked about budget instead of defending price, shifting to negotiation.",
                "timing": "Acknowledged timing concern and offered flexibility.",
                "trust": "Built credibility through authenticity and social proof.",
                "need": "Redirected conversation to understand real interests.",
                "commitment": "Reduced pressure and offered low-commitment next step."
            }
        else:
            analyses = {
                "price": "Defended price or begged, losing frame control.",
                "timing": "Pushed too hard instead of scheduling follow-up.",
                "trust": "Failed to provide proof or testimonial.",
                "need": "Didn't uncover underlying interest.",
                "commitment": "Added pressure instead of reducing friction."
            }

        return analyses.get(obj_type, "")


def extract_all_examples(output_dir: Path) -> Dict:
    """Extract all example types and save to JSON."""
    from scripts.analysis.data_loader import load_and_prepare_data

    console.print("[bold]Loading conversation data...[/bold]")
    threads, _ = load_and_prepare_data(Path("data/parsed_conversations"))
    console.print(f"[green]Loaded {len(threads)} threads[/green]")

    extractor = ConversationExampleExtractor(threads)

    all_examples = {
        "objections": {},
        "tiers": {},
        "chatters": {},
        "openers": {}
    }

    # Objection examples
    console.print("\n[bold]Extracting objection examples...[/bold]")
    for obj_type in ["price", "timing", "trust", "need", "commitment"]:
        successful = extractor.get_objection_examples(obj_type, successful=True, limit=5)
        failed = extractor.get_objection_examples(obj_type, successful=False, limit=3)

        all_examples["objections"][obj_type] = {
            "successful": [asdict(e) for e in successful],
            "failed": [asdict(e) for e in failed]
        }
        console.print(f"  {obj_type}: {len(successful)} successful, {len(failed)} failed")

    # Tier examples
    console.print("\n[bold]Extracting tier examples...[/bold]")
    for tier in ["new", "low", "medium", "high", "whale"]:
        examples = extractor.get_successful_sale_examples(tier, limit=5)
        all_examples["tiers"][tier] = [asdict(e) for e in examples]
        console.print(f"  {tier.upper()}: {len(examples)} examples")

    # Chatter examples
    console.print("\n[bold]Extracting chatter examples...[/bold]")
    for chatter in ["Arvin", "Leonel", "Billy", "Weluu", "Marvin"]:
        examples = extractor.get_chatter_examples(chatter, limit=5)
        all_examples["chatters"][chatter] = [asdict(e) for e in examples]
        console.print(f"  {chatter}: {len(examples)} examples")

    # Opener examples
    console.print("\n[bold]Extracting opener examples...[/bold]")
    successful_openers = extractor.get_opener_examples(successful=True, limit=10)
    failed_openers = extractor.get_opener_examples(successful=False, limit=5)
    all_examples["openers"] = {
        "successful": [asdict(e) for e in successful_openers],
        "failed": [asdict(e) for e in failed_openers]
    }
    console.print(f"  {len(successful_openers)} successful, {len(failed_openers)} failed")

    # Save
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "conversation_examples.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_examples, f, indent=2, ensure_ascii=False)

    console.print(f"\n[green]Saved examples to {output_file}[/green]")

    return all_examples


def main():
    """Run example extraction."""
    output_dir = Path("data/insights/examples")
    extract_all_examples(output_dir)


if __name__ == "__main__":
    main()
