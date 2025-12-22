"""
Chatter Analysis Module

Analyzes performance and style differences between individual chatters.
Key insight: Different chatters have different styles - what works for one may not work for another.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from scripts.analysis.data_loader import (
    ConversationThread,
    SubscriberTier,
    load_and_prepare_data,
    get_threads_by_chatter,
    get_threads_by_tier,
)

console = Console()


@dataclass
class ChatterProfile:
    """Complete profile for a single chatter's performance and style."""
    name: str

    # Volume metrics
    total_threads: int = 0  # Number of conversations
    total_messages_sent: int = 0  # Creator messages sent

    # Revenue metrics
    # NOTE: Tips data is unreliable (parsing bug - tip_amount contains lifetime tips, not conversation tips)
    # We focus on SALES as the primary reliable metric
    total_sales: float = 0.0
    total_tips_lifetime: float = 0.0  # Subscriber lifetime tips (NOT per-conversation)

    # Efficiency metrics (per conversation/message, NOT per screenshot)
    sales_per_thread: float = 0.0  # Sales per conversation
    sales_per_message: float = 0.0  # Sales per creator message sent

    # Breakdown
    sale_count: int = 0
    avg_sale: float = 0.0

    # Tier distribution (what tier subscribers does this chatter work with?)
    tier_distribution: Dict[str, int] = field(default_factory=dict)
    tier_revenue: Dict[str, float] = field(default_factory=dict)

    # Approach distribution (what style does this chatter use?)
    approach_distribution: Dict[str, int] = field(default_factory=dict)
    approach_percentages: Dict[str, float] = field(default_factory=dict)

    # Mood handling (what subscriber moods does this chatter handle?)
    mood_distribution: Dict[str, int] = field(default_factory=dict)

    # Message style metrics
    avg_message_length: float = 0.0
    avg_messages_per_thread: float = 0.0
    talk_listen_ratio: float = 0.0

    # Specialization indicators
    primary_tier: str = ""  # Which tier generates most sales
    primary_approach: str = ""  # Most used approach

    # Active status
    is_active: bool = True


def analyze_chatter(name: str, threads: List[ConversationThread]) -> ChatterProfile:
    """
    Generate a complete profile for a single chatter.

    Args:
        name: Chatter name
        threads: List of conversation threads for this chatter

    Returns:
        ChatterProfile with all metrics
    """
    profile = ChatterProfile(name=name)

    # Check if marked as inactive
    profile.is_active = "(NO LONGER UPDATED)" not in name

    # Basic counts
    profile.total_threads = len(threads)

    # Count creator messages sent (across all threads)
    creator_msg_count = 0
    for thread in threads:
        for msg in thread.all_messages:
            if msg.role == "creator" and msg.text:
                creator_msg_count += 1
    profile.total_messages_sent = creator_msg_count

    # Revenue metrics (SALES ONLY - tips data is unreliable)
    sales = []

    for thread in threads:
        for ss in thread.screenshots:
            if ss.outcome and ss.outcome.sale_amount:
                sales.append(ss.outcome.sale_amount)
                profile.total_sales += ss.outcome.sale_amount

    profile.sale_count = len(sales)

    if sales:
        profile.avg_sale = profile.total_sales / len(sales)

    # Efficiency metrics (per conversation and per message)
    if profile.total_threads > 0:
        profile.sales_per_thread = profile.total_sales / profile.total_threads
    if profile.total_messages_sent > 0:
        profile.sales_per_message = profile.total_sales / profile.total_messages_sent

    # Tier distribution
    tier_counts: Dict[str, int] = defaultdict(int)
    tier_sales: Dict[str, float] = defaultdict(float)

    for thread in threads:
        tier_name = thread.tier.value
        tier_counts[tier_name] += 1
        tier_sales[tier_name] += thread.total_sale_amount

    profile.tier_distribution = dict(tier_counts)
    profile.tier_revenue = dict(tier_sales)  # Using sales as primary revenue metric

    # Primary tier (by sales)
    if tier_sales:
        profile.primary_tier = max(tier_sales.keys(), key=lambda k: tier_sales[k])

    # Approach distribution
    approach_counts: Dict[str, int] = defaultdict(int)

    for thread in threads:
        for approach in thread.approaches_used:
            if approach:
                approach_counts[approach] += 1

    total_approaches = sum(approach_counts.values()) or 1
    profile.approach_distribution = dict(approach_counts)
    profile.approach_percentages = {
        k: (v / total_approaches * 100) for k, v in approach_counts.items()
    }

    # Primary approach
    if approach_counts:
        profile.primary_approach = max(approach_counts.keys(), key=lambda k: approach_counts[k])

    # Mood distribution
    mood_counts: Dict[str, int] = defaultdict(int)

    for thread in threads:
        for mood in thread.moods_observed:
            if mood:
                mood_counts[mood] += 1

    profile.mood_distribution = dict(mood_counts)

    # Message style metrics
    total_creator_chars = 0
    total_creator_msgs = 0
    total_sub_chars = 0
    total_sub_msgs = 0

    for thread in threads:
        for msg in thread.all_messages:
            if not msg.text:
                continue
            if msg.role == "creator":
                total_creator_chars += len(msg.text)
                total_creator_msgs += 1
            elif msg.role == "subscriber":
                total_sub_chars += len(msg.text)
                total_sub_msgs += 1

    if total_creator_msgs > 0:
        profile.avg_message_length = total_creator_chars / total_creator_msgs

    if profile.total_threads > 0:
        profile.avg_messages_per_thread = (total_creator_msgs + total_sub_msgs) / profile.total_threads

    # Talk:Listen ratio
    creator_volume = total_creator_chars
    sub_volume = total_sub_chars or 1
    profile.talk_listen_ratio = creator_volume / sub_volume

    return profile


def analyze_all_chatters(threads: List[ConversationThread]) -> Dict[str, ChatterProfile]:
    """
    Generate profiles for all chatters.

    Args:
        threads: All conversation threads

    Returns:
        Dictionary mapping chatter name to profile
    """
    by_chatter = get_threads_by_chatter(threads)
    profiles = {}

    for name, chatter_threads in by_chatter.items():
        # Skip tutorial/guide folders
        if name in ["Writing PPV descriptions", "Creating the scenario", "Understanding the value ladder"]:
            continue
        # Skip chatters with very few threads (likely incomplete data)
        if len(chatter_threads) < 3:
            continue

        profiles[name] = analyze_chatter(name, chatter_threads)

    return profiles


def rank_chatters(
    profiles: Dict[str, ChatterProfile],
    metric: str = "revenue_per_thread",
    active_only: bool = True
) -> List[ChatterProfile]:
    """
    Rank chatters by a specific metric.

    Args:
        profiles: Dictionary of chatter profiles
        metric: Metric to rank by
        active_only: Only include active chatters

    Returns:
        List of profiles sorted by metric (descending)
    """
    filtered = list(profiles.values())

    if active_only:
        filtered = [p for p in filtered if p.is_active]

    return sorted(filtered, key=lambda p: getattr(p, metric, 0), reverse=True)


def compare_chatter_styles(profiles: Dict[str, ChatterProfile]) -> Dict[str, Any]:
    """
    Compare styles across all chatters to identify different approaches.

    Returns insights about style variations.
    """
    comparisons = {
        "whale_specialists": [],  # Chatters who excel with whales
        "volume_players": [],  # Chatters with high thread counts
        "high_efficiency": [],  # High sales per thread
        "playful_style": [],
        "teasing_style": [],
        "romantic_style": [],
        "transactional_style": [],
    }

    for name, profile in profiles.items():
        if not profile.is_active:
            continue

        # Whale specialist (>30% sales from whales)
        whale_sales = profile.tier_revenue.get("whale", 0)
        if profile.total_sales > 0 and whale_sales / profile.total_sales > 0.3:
            comparisons["whale_specialists"].append(name)

        # Volume player (>150 threads)
        if profile.total_threads > 150:
            comparisons["volume_players"].append(name)

        # High efficiency (>$100 sales per thread)
        if profile.sales_per_thread > 100:
            comparisons["high_efficiency"].append(name)

        # Style classifications
        for approach, pct in profile.approach_percentages.items():
            if pct > 40:  # Dominant approach
                style_key = f"{approach}_style"
                if style_key in comparisons:
                    comparisons[style_key].append(name)

    return comparisons


def generate_chatter_report(
    profiles: Dict[str, ChatterProfile],
    output_path: Optional[Path] = None
) -> str:
    """
    Generate a comprehensive chatter comparison report.

    Args:
        profiles: Dictionary of chatter profiles
        output_path: Optional path to save markdown report

    Returns:
        Markdown formatted report
    """
    lines = [
        "# Chatter Performance & Style Analysis",
        "",
        "Comparison of individual chatter performance, styles, and specializations.",
        "",
        "> **Note:** Analysis focuses on SALES only. Tip data was found to be unreliable",
        "> (parsing bug: tip_amount contained lifetime tips, not per-conversation tips).",
        "",
        "---",
        "",
        "## Performance Rankings",
        "",
        "### By Total Sales",
        "",
        "| Rank | Chatter | Total Sales | Threads | Sales/Thread | Avg Sale |",
        "|------|---------|-------------|---------|--------------|----------|",
    ]

    # Sales ranking
    ranked = rank_chatters(profiles, "total_sales", active_only=False)
    for i, p in enumerate(ranked[:15], 1):
        active = "" if p.is_active else " *"
        lines.append(
            f"| {i} | {p.name}{active} | ${p.total_sales:,.0f} | "
            f"{p.total_threads} | ${p.sales_per_thread:.0f} | ${p.avg_sale:.0f} |"
        )

    lines.extend([
        "",
        "*\\* = No longer active*",
        "",
        "### By Efficiency (Sales per Thread)",
        "",
        "| Rank | Chatter | Sales/Thread | Sales/Message | Total Sales | Threads |",
        "|------|---------|--------------|---------------|-------------|---------|",
    ])

    # Efficiency ranking (active only, minimum 20 threads)
    efficient = [p for p in profiles.values() if p.is_active and p.total_threads >= 20]
    efficient = sorted(efficient, key=lambda p: p.sales_per_thread, reverse=True)

    for i, p in enumerate(efficient[:10], 1):
        lines.append(
            f"| {i} | {p.name} | ${p.sales_per_thread:.0f} | "
            f"${p.sales_per_message:.2f} | ${p.total_sales:,.0f} | {p.total_threads} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Style Analysis",
        "",
        "### Approach Distribution by Chatter",
        "",
        "| Chatter | Playful | Teasing | Transactional | Romantic | Primary |",
        "|---------|---------|---------|---------------|----------|---------|",
    ])

    # Approach distribution
    for p in sorted(profiles.values(), key=lambda x: x.total_sales, reverse=True)[:12]:
        if not p.is_active:
            continue
        playful = p.approach_percentages.get("playful", 0)
        teasing = p.approach_percentages.get("teasing", 0)
        transactional = p.approach_percentages.get("transactional", 0)
        romantic = p.approach_percentages.get("romantic", 0)
        lines.append(
            f"| {p.name} | {playful:.0f}% | {teasing:.0f}% | "
            f"{transactional:.0f}% | {romantic:.0f}% | {p.primary_approach} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Tier Specialization",
        "",
        "### Sales by Tier per Chatter",
        "",
        "| Chatter | NEW | LOW | MEDIUM | HIGH | WHALE | Primary Tier |",
        "|---------|-----|-----|--------|------|-------|--------------|",
    ])

    for p in sorted(profiles.values(), key=lambda x: x.total_sales, reverse=True)[:12]:
        if not p.is_active:
            continue
        new = p.tier_revenue.get("new", 0)
        low = p.tier_revenue.get("low", 0)
        medium = p.tier_revenue.get("medium", 0)
        high = p.tier_revenue.get("high", 0)
        whale = p.tier_revenue.get("whale", 0)
        lines.append(
            f"| {p.name} | ${new:,.0f} | ${low:,.0f} | ${medium:,.0f} | "
            f"${high:,.0f} | ${whale:,.0f} | {p.primary_tier.upper()} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## Message Style Metrics",
        "",
        "| Chatter | Avg Msg Length | Msgs/Thread | Talk:Listen |",
        "|---------|----------------|-------------|-------------|",
    ])

    for p in sorted(profiles.values(), key=lambda x: x.total_sales, reverse=True)[:12]:
        if not p.is_active:
            continue
        lines.append(
            f"| {p.name} | {p.avg_message_length:.0f} chars | "
            f"{p.avg_messages_per_thread:.1f} | {p.talk_listen_ratio:.2f} |"
        )

    # Style comparisons
    comparisons = compare_chatter_styles(profiles)

    lines.extend([
        "",
        "---",
        "",
        "## Style Categories",
        "",
    ])

    if comparisons["whale_specialists"]:
        lines.append(f"**Whale Specialists** (>30% sales from whales): {', '.join(comparisons['whale_specialists'])}")
    if comparisons["high_efficiency"]:
        lines.append(f"**High Efficiency** (>$100 sales/thread): {', '.join(comparisons['high_efficiency'])}")
    if comparisons["volume_players"]:
        lines.append(f"**Volume Players** (>150 threads): {', '.join(comparisons['volume_players'])}")

    lines.extend([
        "",
        "---",
        "",
        "## Key Insights",
        "",
    ])

    # Generate insights
    active_profiles = [p for p in profiles.values() if p.is_active]

    if active_profiles:
        # Top performer
        top = max(active_profiles, key=lambda p: p.total_sales)
        lines.append(f"1. **Top Seller**: {top.name} with ${top.total_sales:,.0f} total sales")

        # Most efficient
        efficient_min = [p for p in active_profiles if p.total_threads >= 50]
        if efficient_min:
            most_efficient = max(efficient_min, key=lambda p: p.sales_per_thread)
            lines.append(
                f"2. **Most Efficient**: {most_efficient.name} at ${most_efficient.sales_per_thread:.0f} sales/thread"
            )

        # Highest average sale
        high_avg = max(active_profiles, key=lambda p: p.avg_sale if p.sale_count > 10 else 0)
        if high_avg.avg_sale > 0:
            lines.append(f"3. **Highest Avg Sale**: {high_avg.name} at ${high_avg.avg_sale:.0f}/sale")

        # Style variation
        playful_pcts = [p.approach_percentages.get("playful", 0) for p in active_profiles if p.approach_percentages]
        if playful_pcts:
            lines.append(
                f"4. **Style Variation**: Playful approach ranges from {min(playful_pcts):.0f}% to {max(playful_pcts):.0f}% across chatters"
            )

    lines.extend([
        "",
        "---",
        "",
        f"*Analysis based on {len(profiles)} chatters, {sum(p.total_threads for p in profiles.values())} conversation threads*",
    ])

    report = "\n".join(lines)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report)
        console.print(f"[green]Report saved to {output_path}[/green]")

    return report


def print_chatter_summary(profiles: Dict[str, ChatterProfile]):
    """Print a quick summary table to console."""
    console.print("\n[bold cyan]=== CHATTER PERFORMANCE SUMMARY ===[/bold cyan]\n")

    table = Table(title="Top Chatters by Total Sales")
    table.add_column("Chatter", style="cyan")
    table.add_column("Total Sales", style="green", justify="right")
    table.add_column("Threads", justify="right")
    table.add_column("Sales/Thread", style="magenta", justify="right")
    table.add_column("Avg Sale", style="yellow", justify="right")
    table.add_column("Style", style="blue")

    ranked = rank_chatters(profiles, "total_sales", active_only=True)

    for p in ranked[:10]:
        table.add_row(
            p.name,
            f"${p.total_sales:,.0f}",
            str(p.total_threads),
            f"${p.sales_per_thread:.0f}",
            f"${p.avg_sale:.0f}",
            p.primary_approach or "N/A"
        )

    console.print(table)


def run_chatter_analysis(
    parsed_dir: Path = Path("data/parsed_conversations"),
    output_dir: Path = Path("data/insights"),
    show_output: bool = True
) -> Dict[str, ChatterProfile]:
    """
    Run complete chatter analysis pipeline.

    Args:
        parsed_dir: Path to parsed conversations
        output_dir: Path for output files
        show_output: Whether to print to console

    Returns:
        Dictionary of chatter profiles
    """
    # Load data
    threads, report = load_and_prepare_data(parsed_dir, show_progress=show_output, print_report=False)

    if show_output:
        console.print(f"[blue]Analyzing {len(threads)} threads across chatters...[/blue]")

    # Generate profiles
    profiles = analyze_all_chatters(threads)

    if show_output:
        console.print(f"[green]Generated profiles for {len(profiles)} chatters[/green]")
        print_chatter_summary(profiles)

    # Generate report
    report_path = output_dir / "chatter_analysis.md"
    generate_chatter_report(profiles, report_path)

    # Save raw data
    raw_path = output_dir / "raw" / "chatter_profiles.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert profiles to JSON-serializable format
    profiles_dict = {}
    for name, p in profiles.items():
        profiles_dict[name] = {
            "name": p.name,
            "is_active": p.is_active,
            "total_threads": p.total_threads,
            "total_messages_sent": p.total_messages_sent,
            "total_sales": p.total_sales,
            "sales_per_thread": p.sales_per_thread,
            "sales_per_message": p.sales_per_message,
            "sale_count": p.sale_count,
            "avg_sale": p.avg_sale,
            "tier_distribution": p.tier_distribution,
            "tier_revenue": p.tier_revenue,
            "approach_distribution": p.approach_distribution,
            "approach_percentages": p.approach_percentages,
            "mood_distribution": p.mood_distribution,
            "avg_message_length": p.avg_message_length,
            "avg_messages_per_thread": p.avg_messages_per_thread,
            "talk_listen_ratio": p.talk_listen_ratio,
            "primary_tier": p.primary_tier,
            "primary_approach": p.primary_approach,
        }

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(profiles_dict, f, indent=2, ensure_ascii=False)

    if show_output:
        console.print(f"[green]Saved raw data to {raw_path}[/green]")

    return profiles


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze chatter performance and styles")
    parser.add_argument(
        "--input-dir",
        default="data/parsed_conversations",
        help="Parsed conversations directory"
    )
    parser.add_argument(
        "--output-dir",
        default="data/insights",
        help="Output directory for reports"
    )

    args = parser.parse_args()

    run_chatter_analysis(
        parsed_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        show_output=True
    )
