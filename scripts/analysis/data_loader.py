"""
Data Loader Module for Chatter Training Analysis

Loads all parsed conversations, groups by thread, and applies subscriber tier classification.
This is the foundation module - all other analysis depends on this.
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from collections import defaultdict
from datetime import datetime

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

console = Console()


class SubscriberTier(str, Enum):
    """Subscriber tier based on total_spent."""
    NEW = "new"        # $0 or null
    LOW = "low"        # $1-199
    MEDIUM = "medium"  # $200-999
    HIGH = "high"      # $1000-4999
    WHALE = "whale"    # $5000+


@dataclass
class Message:
    """A single message in a conversation."""
    role: str  # "creator" or "subscriber"
    text: str
    timestamp: Optional[str] = None


@dataclass
class SubscriberStats:
    """Subscriber statistics from the conversation."""
    total_spent: Optional[float] = None
    tips: Optional[float] = None
    messages_spent: Optional[float] = None
    buy_rate: Optional[str] = None
    subscription_status: Optional[str] = None
    subscription_price: Optional[float] = None
    highest_purchase: Optional[float] = None
    last_paid: Optional[str] = None
    renew: Optional[str] = None

    @property
    def tier(self) -> SubscriberTier:
        """Calculate subscriber tier based on total_spent."""
        return classify_tier(self.total_spent)


@dataclass
class Outcome:
    """Outcome data from the conversation."""
    sale_in_screenshot: bool = False
    sale_amount: Optional[float] = None
    tip_received: bool = False
    tip_amount: Optional[float] = None
    ppv_sent: bool = False
    ppv_price: Optional[float] = None
    technique_observed: Optional[str] = None


@dataclass
class Context:
    """Conversation context metadata."""
    conversation_stage: Optional[str] = None
    subscriber_mood: Optional[str] = None
    creator_approach: Optional[str] = None


@dataclass
class ParsedScreenshot:
    """A single parsed screenshot from a conversation."""
    source_file: str
    messages: List[Message] = field(default_factory=list)
    subscriber_stats: Optional[SubscriberStats] = None
    outcome: Optional[Outcome] = None
    context: Optional[Context] = None
    empty: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> 'ParsedScreenshot':
        """Create ParsedScreenshot from parsed JSON data."""
        parsed = data.get('parsed_data', {})

        # Check if empty
        if parsed.get('empty', False):
            return cls(
                source_file=data.get('source_file', ''),
                empty=True
            )

        # Parse messages
        messages = []
        for msg in parsed.get('messages', []):
            messages.append(Message(
                role=msg.get('role', 'unknown'),
                text=msg.get('text', ''),
                timestamp=msg.get('timestamp')
            ))

        # Parse subscriber stats
        stats_data = parsed.get('subscriber_stats') or {}
        subscriber_stats = SubscriberStats(
            total_spent=stats_data.get('total_spent'),
            tips=stats_data.get('tips'),
            messages_spent=stats_data.get('messages_spent'),
            buy_rate=stats_data.get('buy_rate'),
            subscription_status=stats_data.get('subscription_status'),
            subscription_price=stats_data.get('subscription_price'),
            highest_purchase=stats_data.get('highest_purchase'),
            last_paid=stats_data.get('last_paid'),
            renew=stats_data.get('renew')
        ) if stats_data else None

        # Parse outcome
        outcome_data = parsed.get('outcome') or {}
        outcome = Outcome(
            sale_in_screenshot=outcome_data.get('sale_in_screenshot', False),
            sale_amount=outcome_data.get('sale_amount'),
            tip_received=outcome_data.get('tip_received', False),
            tip_amount=outcome_data.get('tip_amount'),
            ppv_sent=outcome_data.get('ppv_sent', False),
            ppv_price=outcome_data.get('ppv_price'),
            technique_observed=outcome_data.get('technique_observed')
        ) if outcome_data else None

        # Parse context
        context_data = parsed.get('context') or {}
        context = Context(
            conversation_stage=context_data.get('conversation_stage'),
            subscriber_mood=context_data.get('subscriber_mood'),
            creator_approach=context_data.get('creator_approach')
        ) if context_data else None

        return cls(
            source_file=data.get('source_file', ''),
            messages=messages,
            subscriber_stats=subscriber_stats,
            outcome=outcome,
            context=context,
            empty=False
        )


@dataclass
class ConversationThread:
    """A grouped conversation thread (multiple screenshots from same folder)."""
    thread_id: str  # Folder path as unique ID
    chatter: str  # Extracted from path
    title: str  # Folder name (conversation title)
    category: str  # Top-level category (Example conversations, Selling, etc.)
    screenshots: List[ParsedScreenshot] = field(default_factory=list)

    @property
    def subscriber_stats(self) -> Optional[SubscriberStats]:
        """Get subscriber stats from first screenshot with valid data."""
        for ss in self.screenshots:
            if ss.subscriber_stats and ss.subscriber_stats.total_spent is not None:
                return ss.subscriber_stats
        # Return first non-None stats even without total_spent
        for ss in self.screenshots:
            if ss.subscriber_stats:
                return ss.subscriber_stats
        return None

    @property
    def tier(self) -> SubscriberTier:
        """Get subscriber tier for this thread."""
        stats = self.subscriber_stats
        if stats:
            return stats.tier
        return SubscriberTier.NEW

    @property
    def total_sale_amount(self) -> float:
        """Sum of all sales in thread."""
        total = 0.0
        for ss in self.screenshots:
            if ss.outcome and ss.outcome.sale_amount:
                total += ss.outcome.sale_amount
        return total

    @property
    def total_tip_amount(self) -> float:
        """Sum of all tips in thread."""
        total = 0.0
        for ss in self.screenshots:
            if ss.outcome and ss.outcome.tip_amount:
                total += ss.outcome.tip_amount
        return total

    @property
    def total_revenue(self) -> float:
        """Sum of all sales + tips in thread (total money generated)."""
        return self.total_sale_amount + self.total_tip_amount

    @property
    def has_sale(self) -> bool:
        """Whether any screenshot in thread has a sale."""
        return any(ss.outcome and ss.outcome.sale_in_screenshot for ss in self.screenshots)

    @property
    def has_tip(self) -> bool:
        """Whether any screenshot in thread has a tip."""
        return any(ss.outcome and ss.outcome.tip_received for ss in self.screenshots)

    @property
    def all_messages(self) -> List[Message]:
        """Get all messages from all screenshots (may have duplicates)."""
        messages = []
        for ss in self.screenshots:
            messages.extend(ss.messages)
        return messages

    @property
    def techniques_observed(self) -> List[str]:
        """Get all techniques observed in thread."""
        techniques = []
        for ss in self.screenshots:
            if ss.outcome and ss.outcome.technique_observed:
                techniques.append(ss.outcome.technique_observed)
        return techniques

    @property
    def approaches_used(self) -> List[str]:
        """Get all creator approaches used in thread."""
        approaches = []
        for ss in self.screenshots:
            if ss.context and ss.context.creator_approach:
                approaches.append(ss.context.creator_approach)
        return approaches

    @property
    def moods_observed(self) -> List[str]:
        """Get all subscriber moods observed in thread."""
        moods = []
        for ss in self.screenshots:
            if ss.context and ss.context.subscriber_mood:
                moods.append(ss.context.subscriber_mood)
        return moods

    @property
    def stages_observed(self) -> List[str]:
        """Get all conversation stages in thread."""
        stages = []
        for ss in self.screenshots:
            if ss.context and ss.context.conversation_stage:
                stages.append(ss.context.conversation_stage)
        return stages


@dataclass
class DataQualityReport:
    """Data quality metrics for the loaded dataset."""
    total_files_loaded: int = 0
    valid_conversations: int = 0
    empty_conversations: int = 0
    load_errors: int = 0

    # Field completeness
    has_subscriber_stats: int = 0
    has_total_spent: int = 0
    has_outcome: int = 0
    has_context: int = 0
    has_messages: int = 0

    # Thread statistics
    total_threads: int = 0
    single_screenshot_threads: int = 0
    multi_screenshot_threads: int = 0
    max_screenshots_in_thread: int = 0
    avg_screenshots_per_thread: float = 0.0

    # Tier distribution
    tier_distribution: Dict[SubscriberTier, int] = field(default_factory=dict)

    # Category distribution
    category_distribution: Dict[str, int] = field(default_factory=dict)

    # Chatter distribution
    chatter_distribution: Dict[str, int] = field(default_factory=dict)

    def print_report(self):
        """Print formatted data quality report."""
        console.print("\n[bold cyan]=== DATA QUALITY REPORT ===[/bold cyan]\n")

        # Overview table
        table = Table(title="Overview")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Files Loaded", f"{self.total_files_loaded:,}")
        table.add_row("Valid Conversations", f"{self.valid_conversations:,}")
        table.add_row("Empty Conversations", f"{self.empty_conversations:,}")
        table.add_row("Load Errors", f"{self.load_errors:,}")
        console.print(table)

        # Field completeness table
        total = self.valid_conversations or 1
        table = Table(title="\nField Completeness")
        table.add_column("Field", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Rate", style="yellow")
        table.add_row("Has Messages", f"{self.has_messages:,}", f"{self.has_messages/total*100:.1f}%")
        table.add_row("Has Subscriber Stats", f"{self.has_subscriber_stats:,}", f"{self.has_subscriber_stats/total*100:.1f}%")
        table.add_row("Has Total Spent", f"{self.has_total_spent:,}", f"{self.has_total_spent/total*100:.1f}%")
        table.add_row("Has Outcome", f"{self.has_outcome:,}", f"{self.has_outcome/total*100:.1f}%")
        table.add_row("Has Context", f"{self.has_context:,}", f"{self.has_context/total*100:.1f}%")
        console.print(table)

        # Thread statistics table
        table = Table(title="\nThread Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Total Threads", f"{self.total_threads:,}")
        table.add_row("Single-Screenshot Threads", f"{self.single_screenshot_threads:,}")
        table.add_row("Multi-Screenshot Threads", f"{self.multi_screenshot_threads:,}")
        table.add_row("Max Screenshots in Thread", f"{self.max_screenshots_in_thread}")
        table.add_row("Avg Screenshots per Thread", f"{self.avg_screenshots_per_thread:.2f}")
        console.print(table)

        # Tier distribution table
        table = Table(title="\nSubscriber Tier Distribution")
        table.add_column("Tier", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Percentage", style="yellow")
        for tier in SubscriberTier:
            count = self.tier_distribution.get(tier, 0)
            pct = count / self.total_threads * 100 if self.total_threads > 0 else 0
            table.add_row(tier.value.upper(), f"{count:,}", f"{pct:.1f}%")
        console.print(table)

        # Category distribution table
        if self.category_distribution:
            table = Table(title="\nCategory Distribution")
            table.add_column("Category", style="cyan")
            table.add_column("Threads", style="green")
            for cat, count in sorted(self.category_distribution.items(), key=lambda x: x[1], reverse=True):
                table.add_row(cat, f"{count:,}")
            console.print(table)

        # Top chatters table
        if self.chatter_distribution:
            table = Table(title="\nTop 10 Chatters by Conversation Count")
            table.add_column("Chatter", style="cyan")
            table.add_column("Threads", style="green")
            sorted_chatters = sorted(self.chatter_distribution.items(), key=lambda x: x[1], reverse=True)[:10]
            for chatter, count in sorted_chatters:
                table.add_row(chatter, f"{count:,}")
            console.print(table)


def classify_tier(total_spent: Optional[float]) -> SubscriberTier:
    """Classify subscriber tier based on total_spent."""
    if total_spent is None or total_spent == 0:
        return SubscriberTier.NEW
    elif total_spent < 200:
        return SubscriberTier.LOW
    elif total_spent < 1000:
        return SubscriberTier.MEDIUM
    elif total_spent < 5000:
        return SubscriberTier.HIGH
    else:
        return SubscriberTier.WHALE


def extract_sort_key(filename: str) -> tuple:
    """
    Extract sort key from filename for proper ordering.
    Handles patterns like: image.png, image 1.png, image 2.png, etc.
    """
    name = Path(filename).stem  # Remove extension

    # Try to extract number from "image N" pattern
    match = re.search(r'(\d+)', name)
    if match:
        return (0, int(match.group(1)))
    else:
        # No number means it's the base "image" (should come first)
        return (0, 0)


def load_all_conversations(parsed_dir: Path, show_progress: bool = True) -> List[dict]:
    """
    Load all parsed conversation JSON files from the directory.

    Args:
        parsed_dir: Path to the parsed_conversations directory
        show_progress: Whether to show progress bar

    Returns:
        List of raw JSON data dicts
    """
    conversations = []
    errors = 0

    # Find all .parsed.json files
    files = list(parsed_dir.rglob("*.parsed.json"))

    if show_progress:
        console.print(f"[blue]Found {len(files):,} parsed files to load...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        disable=not show_progress
    ) as progress:
        task = progress.add_task("[cyan]Loading conversations...", total=len(files))

        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fp:
                    data = json.load(fp)
                    data['_file_path'] = str(f)  # Store file path for grouping
                    conversations.append(data)
            except Exception as e:
                errors += 1

            progress.update(task, advance=1)

    if show_progress:
        console.print(f"[green]Loaded {len(conversations):,} conversations ({errors} errors)[/green]")

    return conversations


def group_by_thread(conversations: List[dict]) -> List[ConversationThread]:
    """
    Group conversations by folder (conversation thread).

    Each folder represents a single conversation thread with potentially
    multiple screenshots.

    Args:
        conversations: List of raw conversation data

    Returns:
        List of ConversationThread objects
    """
    # Group by folder path
    folder_groups: Dict[str, List[dict]] = defaultdict(list)

    for conv in conversations:
        file_path = Path(conv.get('_file_path', ''))
        folder_path = file_path.parent
        folder_groups[str(folder_path)].append(conv)

    threads = []

    for folder_path, folder_convs in folder_groups.items():
        # Sort by filename to maintain screenshot order
        folder_convs.sort(key=lambda x: extract_sort_key(x.get('_file_path', '')))

        # Parse path to extract metadata
        path_parts = Path(folder_path).parts

        # Extract category, chatter, and title from path
        # Expected structure: .../parsed_conversations/Category/Chatter/Title/
        category = ""
        chatter = ""
        title = ""

        # Find the parsed_conversations folder and extract from there
        try:
            pc_idx = next(i for i, p in enumerate(path_parts) if p == "parsed_conversations")
            remaining = path_parts[pc_idx + 1:]

            if len(remaining) >= 1:
                category = remaining[0]
            if len(remaining) >= 2:
                # Handle "Other Chatters" subfolder - the actual chatter name is one level deeper
                if remaining[1] == "Other Chatters" and len(remaining) >= 3:
                    chatter = remaining[2]
                    if len(remaining) >= 4:
                        title = remaining[3]
                else:
                    chatter = remaining[1]
                    if len(remaining) >= 3:
                        title = remaining[2]
        except StopIteration:
            # parsed_conversations not in path, use folder name
            title = Path(folder_path).name

        # Create ParsedScreenshot objects
        screenshots = []
        for conv in folder_convs:
            if conv.get('success', False):
                ss = ParsedScreenshot.from_dict(conv)
                if not ss.empty:
                    screenshots.append(ss)

        # Only create thread if we have valid screenshots
        if screenshots:
            thread = ConversationThread(
                thread_id=folder_path,
                chatter=chatter,
                title=title,
                category=category,
                screenshots=screenshots
            )
            threads.append(thread)

    return threads


def get_threads_by_tier(threads: List[ConversationThread]) -> Dict[SubscriberTier, List[ConversationThread]]:
    """
    Organize threads by subscriber tier.

    Args:
        threads: List of conversation threads

    Returns:
        Dictionary mapping tier to list of threads
    """
    by_tier: Dict[SubscriberTier, List[ConversationThread]] = {
        tier: [] for tier in SubscriberTier
    }

    for thread in threads:
        by_tier[thread.tier].append(thread)

    return by_tier


def get_threads_by_chatter(threads: List[ConversationThread]) -> Dict[str, List[ConversationThread]]:
    """
    Organize threads by chatter name.

    Args:
        threads: List of conversation threads

    Returns:
        Dictionary mapping chatter name to list of threads
    """
    by_chatter: Dict[str, List[ConversationThread]] = defaultdict(list)

    for thread in threads:
        if thread.chatter:
            by_chatter[thread.chatter].append(thread)

    return dict(by_chatter)


def generate_data_quality_report(
    conversations: List[dict],
    threads: List[ConversationThread]
) -> DataQualityReport:
    """
    Generate a comprehensive data quality report.

    Args:
        conversations: Raw conversation data
        threads: Grouped conversation threads

    Returns:
        DataQualityReport with all statistics
    """
    report = DataQualityReport()

    # Basic counts
    report.total_files_loaded = len(conversations)

    valid = 0
    empty = 0
    errors = 0

    for conv in conversations:
        if not conv.get('success', False):
            errors += 1
            continue

        parsed = conv.get('parsed_data', {})
        if parsed.get('empty', False):
            empty += 1
        else:
            valid += 1

            # Field completeness
            if parsed.get('messages'):
                report.has_messages += 1
            if parsed.get('subscriber_stats'):
                report.has_subscriber_stats += 1
                if parsed['subscriber_stats'].get('total_spent') is not None:
                    report.has_total_spent += 1
            if parsed.get('outcome'):
                report.has_outcome += 1
            if parsed.get('context'):
                report.has_context += 1

    report.valid_conversations = valid
    report.empty_conversations = empty
    report.load_errors = errors

    # Thread statistics
    report.total_threads = len(threads)

    screenshot_counts = [len(t.screenshots) for t in threads]
    if screenshot_counts:
        report.single_screenshot_threads = sum(1 for c in screenshot_counts if c == 1)
        report.multi_screenshot_threads = sum(1 for c in screenshot_counts if c > 1)
        report.max_screenshots_in_thread = max(screenshot_counts)
        report.avg_screenshots_per_thread = sum(screenshot_counts) / len(screenshot_counts)

    # Tier distribution
    tier_counts: Dict[SubscriberTier, int] = defaultdict(int)
    for thread in threads:
        tier_counts[thread.tier] += 1
    report.tier_distribution = dict(tier_counts)

    # Category distribution
    cat_counts: Dict[str, int] = defaultdict(int)
    for thread in threads:
        if thread.category:
            cat_counts[thread.category] += 1
    report.category_distribution = dict(cat_counts)

    # Chatter distribution
    chatter_counts: Dict[str, int] = defaultdict(int)
    for thread in threads:
        if thread.chatter:
            chatter_counts[thread.chatter] += 1
    report.chatter_distribution = dict(chatter_counts)

    return report


def load_and_prepare_data(
    parsed_dir: Path = Path("data/parsed_conversations"),
    show_progress: bool = True,
    print_report: bool = True
) -> tuple[List[ConversationThread], DataQualityReport]:
    """
    Main entry point: Load all data, group by thread, and generate report.

    Args:
        parsed_dir: Path to parsed conversations directory
        show_progress: Whether to show progress bars
        print_report: Whether to print the quality report

    Returns:
        Tuple of (threads, report)
    """
    # Load raw data
    conversations = load_all_conversations(parsed_dir, show_progress)

    # Group by thread
    if show_progress:
        console.print("[blue]Grouping conversations by thread...[/blue]")
    threads = group_by_thread(conversations)
    if show_progress:
        console.print(f"[green]Created {len(threads):,} conversation threads[/green]")

    # Generate quality report
    report = generate_data_quality_report(conversations, threads)

    if print_report:
        report.print_report()

    return threads, report


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load and analyze conversation data")
    parser.add_argument(
        "--input-dir",
        default="data/parsed_conversations",
        help="Parsed conversations directory"
    )
    parser.add_argument(
        "--output",
        help="Save report to JSON file"
    )

    args = parser.parse_args()

    # Load data
    parsed_dir = Path(args.input_dir)
    threads, report = load_and_prepare_data(parsed_dir)

    # Show tier breakdown with example threads
    console.print("\n[bold cyan]=== TIER BREAKDOWN ===[/bold cyan]\n")

    by_tier = get_threads_by_tier(threads)
    for tier in SubscriberTier:
        tier_threads = by_tier[tier]
        console.print(f"\n[bold yellow]{tier.value.upper()}[/bold yellow] ({len(tier_threads):,} threads)")

        # Show example
        if tier_threads:
            example = tier_threads[0]
            stats = example.subscriber_stats
            spent = stats.total_spent if stats else "N/A"
            console.print(f"  Example: {example.title[:50]}...")
            console.print(f"  Total Spent: ${spent}")
            console.print(f"  Screenshots: {len(example.screenshots)}")
            if example.has_sale:
                console.print(f"  Sale Amount: ${example.total_sale_amount:.0f}")

    # Save report if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert report to dict for JSON serialization
        report_dict = {
            "total_files_loaded": report.total_files_loaded,
            "valid_conversations": report.valid_conversations,
            "empty_conversations": report.empty_conversations,
            "load_errors": report.load_errors,
            "has_subscriber_stats": report.has_subscriber_stats,
            "has_total_spent": report.has_total_spent,
            "has_outcome": report.has_outcome,
            "has_context": report.has_context,
            "has_messages": report.has_messages,
            "total_threads": report.total_threads,
            "single_screenshot_threads": report.single_screenshot_threads,
            "multi_screenshot_threads": report.multi_screenshot_threads,
            "max_screenshots_in_thread": report.max_screenshots_in_thread,
            "avg_screenshots_per_thread": report.avg_screenshots_per_thread,
            "tier_distribution": {k.value: v for k, v in report.tier_distribution.items()},
            "category_distribution": report.category_distribution,
            "chatter_distribution": report.chatter_distribution,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]Report saved to {output_path}[/green]")
