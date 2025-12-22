"""
Statistical Analysis Module for Chatter Training Data

Performs comprehensive statistical analysis across subscriber tiers.
No AI/LLM calls - pure statistical analysis.

IMPORTANT: All data represents successful sales (selection bias).
We characterize "what success looks like", NOT conversion rates.
"""

import json
import statistics
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from collections import defaultdict, Counter

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# Import from our data loader
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.analysis.data_loader import (
    SubscriberTier, ConversationThread, load_and_prepare_data, get_threads_by_tier
)

console = Console()


@dataclass
class TierStatistics:
    """Comprehensive statistics for a subscriber tier."""
    tier: str
    thread_count: int = 0
    screenshot_count: int = 0

    # Sale statistics
    threads_with_sales: int = 0
    total_sale_amount: float = 0.0
    avg_sale_amount: float = 0.0
    median_sale_amount: float = 0.0
    min_sale_amount: float = 0.0
    max_sale_amount: float = 0.0
    sale_amounts: List[float] = field(default_factory=list)

    # Tip statistics
    threads_with_tips: int = 0
    total_tip_amount: float = 0.0
    avg_tip_amount: float = 0.0

    # PPV statistics
    ppv_sent_count: int = 0

    # Subscriber profile
    avg_total_spent: float = 0.0
    avg_highest_purchase: float = 0.0

    # Approach distribution
    approach_distribution: Dict[str, int] = field(default_factory=dict)

    # Mood distribution
    mood_distribution: Dict[str, int] = field(default_factory=dict)

    # Stage distribution
    stage_distribution: Dict[str, int] = field(default_factory=dict)

    # Technique distribution
    technique_distribution: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "tier": self.tier,
            "thread_count": self.thread_count,
            "screenshot_count": self.screenshot_count,
            "threads_with_sales": self.threads_with_sales,
            "total_sale_amount": round(self.total_sale_amount, 2),
            "avg_sale_amount": round(self.avg_sale_amount, 2),
            "median_sale_amount": round(self.median_sale_amount, 2),
            "min_sale_amount": round(self.min_sale_amount, 2),
            "max_sale_amount": round(self.max_sale_amount, 2),
            "threads_with_tips": self.threads_with_tips,
            "total_tip_amount": round(self.total_tip_amount, 2),
            "avg_tip_amount": round(self.avg_tip_amount, 2),
            "ppv_sent_count": self.ppv_sent_count,
            "avg_total_spent": round(self.avg_total_spent, 2),
            "avg_highest_purchase": round(self.avg_highest_purchase, 2),
            "approach_distribution": dict(self.approach_distribution),
            "mood_distribution": dict(self.mood_distribution),
            "stage_distribution": dict(self.stage_distribution),
            "technique_distribution": dict(self.technique_distribution),
        }


@dataclass
class SaleDistribution:
    """Sale amount distribution analysis."""
    tier: str
    bins: List[Tuple[float, float, int]] = field(default_factory=list)  # (min, max, count)
    percentiles: Dict[int, float] = field(default_factory=dict)  # p25, p50, p75, p90, p95


@dataclass
class UpsellingAnalysis:
    """Analysis of upselling patterns."""
    tier: str
    avg_sale_vs_highest_ratio: float = 0.0  # How much of their max do they spend?
    threads_above_previous_max: int = 0  # Times sale exceeded highest_purchase
    new_high_percentage: float = 0.0


def calculate_tier_statistics(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]]
) -> Dict[str, TierStatistics]:
    """
    Calculate comprehensive statistics for each tier.

    Args:
        threads_by_tier: Dictionary mapping tier to list of threads

    Returns:
        Dictionary mapping tier name to TierStatistics
    """
    results = {}

    for tier, threads in threads_by_tier.items():
        stats = TierStatistics(tier=tier.value)
        stats.thread_count = len(threads)

        sale_amounts = []
        tip_amounts = []
        total_spents = []
        highest_purchases = []

        approach_counter: Counter = Counter()
        mood_counter: Counter = Counter()
        stage_counter: Counter = Counter()
        technique_counter: Counter = Counter()

        for thread in threads:
            stats.screenshot_count += len(thread.screenshots)

            # Sales
            if thread.has_sale:
                stats.threads_with_sales += 1
                sale_amount = thread.total_sale_amount
                if sale_amount > 0:
                    sale_amounts.append(sale_amount)
                    stats.total_sale_amount += sale_amount

            # Tips
            if thread.has_tip:
                stats.threads_with_tips += 1
                tip_amount = thread.total_tip_amount
                if tip_amount > 0:
                    tip_amounts.append(tip_amount)
                    stats.total_tip_amount += tip_amount

            # PPV count
            for ss in thread.screenshots:
                if ss.outcome and ss.outcome.ppv_sent:
                    stats.ppv_sent_count += 1

            # Subscriber profile
            sub_stats = thread.subscriber_stats
            if sub_stats:
                if sub_stats.total_spent is not None:
                    total_spents.append(sub_stats.total_spent)
                if sub_stats.highest_purchase is not None:
                    highest_purchases.append(sub_stats.highest_purchase)

            # Distributions (count across all screenshots in thread)
            for approach in thread.approaches_used:
                approach_counter[approach.lower()] += 1

            for mood in thread.moods_observed:
                mood_counter[mood.lower()] += 1

            for stage in thread.stages_observed:
                stage_counter[stage.lower()] += 1

            for technique in thread.techniques_observed:
                technique_counter[technique.lower()] += 1

        # Calculate averages
        if sale_amounts:
            stats.avg_sale_amount = statistics.mean(sale_amounts)
            stats.median_sale_amount = statistics.median(sale_amounts)
            stats.min_sale_amount = min(sale_amounts)
            stats.max_sale_amount = max(sale_amounts)
            stats.sale_amounts = sale_amounts

        if tip_amounts:
            stats.avg_tip_amount = statistics.mean(tip_amounts)

        if total_spents:
            stats.avg_total_spent = statistics.mean(total_spents)

        if highest_purchases:
            stats.avg_highest_purchase = statistics.mean(highest_purchases)

        # Store distributions
        stats.approach_distribution = dict(approach_counter.most_common(15))
        stats.mood_distribution = dict(mood_counter.most_common(15))
        stats.stage_distribution = dict(stage_counter.most_common(15))
        stats.technique_distribution = dict(technique_counter.most_common(15))

        results[tier.value] = stats

    return results


def calculate_sale_distribution(
    tier_stats: TierStatistics,
    bins: List[Tuple[float, float]] = None
) -> SaleDistribution:
    """
    Calculate sale amount distribution for a tier.

    Args:
        tier_stats: Statistics for a tier
        bins: Optional list of (min, max) tuples for bins

    Returns:
        SaleDistribution with histogram bins and percentiles
    """
    dist = SaleDistribution(tier=tier_stats.tier)

    if not tier_stats.sale_amounts:
        return dist

    amounts = sorted(tier_stats.sale_amounts)

    # Default bins if not provided
    if bins is None:
        bins = [
            (0, 10), (10, 25), (25, 50), (50, 100),
            (100, 200), (200, 500), (500, 1000), (1000, float('inf'))
        ]

    # Calculate histogram
    for bin_min, bin_max in bins:
        count = sum(1 for a in amounts if bin_min <= a < bin_max)
        dist.bins.append((bin_min, bin_max if bin_max != float('inf') else 9999, count))

    # Calculate percentiles
    if len(amounts) >= 4:
        dist.percentiles = {
            25: statistics.quantiles(amounts, n=4)[0],
            50: statistics.median(amounts),
            75: statistics.quantiles(amounts, n=4)[2],
        }
        if len(amounts) >= 10:
            quantiles_10 = statistics.quantiles(amounts, n=10)
            dist.percentiles[90] = quantiles_10[8]
        if len(amounts) >= 20:
            quantiles_20 = statistics.quantiles(amounts, n=20)
            dist.percentiles[95] = quantiles_20[18]

    return dist


def calculate_upselling_patterns(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]]
) -> Dict[str, UpsellingAnalysis]:
    """
    Analyze upselling patterns - how do sale amounts relate to historical highest purchase?

    Args:
        threads_by_tier: Dictionary mapping tier to list of threads

    Returns:
        Dictionary mapping tier name to UpsellingAnalysis
    """
    results = {}

    for tier, threads in threads_by_tier.items():
        analysis = UpsellingAnalysis(tier=tier.value)

        ratios = []
        above_max_count = 0
        total_with_both = 0

        for thread in threads:
            if not thread.has_sale:
                continue

            sale_amount = thread.total_sale_amount
            sub_stats = thread.subscriber_stats

            if sub_stats and sub_stats.highest_purchase and sub_stats.highest_purchase > 0:
                total_with_both += 1
                ratio = sale_amount / sub_stats.highest_purchase
                ratios.append(ratio)

                if sale_amount > sub_stats.highest_purchase:
                    above_max_count += 1

        if ratios:
            analysis.avg_sale_vs_highest_ratio = statistics.mean(ratios)

        analysis.threads_above_previous_max = above_max_count
        if total_with_both > 0:
            analysis.new_high_percentage = (above_max_count / total_with_both) * 100

        results[tier.value] = analysis

    return results


def calculate_approach_effectiveness(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]]
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Analyze which approaches are used for each tier and their sale amounts.

    NOTE: We cannot calculate "effectiveness" since all data is successful.
    We can only show what approaches are USED for successful sales.

    Returns:
        {tier: {approach: {count, avg_sale_amount, total_sale_amount}}}
    """
    results = {}

    for tier, threads in threads_by_tier.items():
        approach_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "count": 0,
            "sale_amounts": [],
            "total_sale": 0.0,
        })

        for thread in threads:
            # Get the dominant approach for this thread
            approaches = thread.approaches_used
            if not approaches:
                continue

            # Use most common approach in thread
            approach_counter = Counter(approaches)
            dominant_approach = approach_counter.most_common(1)[0][0].lower()

            approach_data[dominant_approach]["count"] += 1
            if thread.has_sale:
                sale_amount = thread.total_sale_amount
                approach_data[dominant_approach]["sale_amounts"].append(sale_amount)
                approach_data[dominant_approach]["total_sale"] += sale_amount

        # Calculate averages
        tier_result = {}
        for approach, data in approach_data.items():
            avg_sale = 0.0
            if data["sale_amounts"]:
                avg_sale = statistics.mean(data["sale_amounts"])

            tier_result[approach] = {
                "count": data["count"],
                "threads_with_sales": len(data["sale_amounts"]),
                "avg_sale_amount": round(avg_sale, 2),
                "total_sale_amount": round(data["total_sale"], 2),
            }

        results[tier.value] = tier_result

    return results


def print_tier_statistics(tier_stats: Dict[str, TierStatistics]):
    """Print formatted tier statistics."""
    console.print("\n[bold cyan]=== TIER STATISTICS ===[/bold cyan]")
    console.print("[dim]Note: All data represents successful sales. We're showing what success looks like, NOT conversion rates.[/dim]\n")

    # Summary table
    table = Table(title="Overview by Tier")
    table.add_column("Tier", style="cyan", width=10)
    table.add_column("Threads", style="white", justify="right")
    table.add_column("With Sales", style="green", justify="right")
    table.add_column("Total Sales $", style="green", justify="right")
    table.add_column("Avg Sale $", style="yellow", justify="right")
    table.add_column("Median $", style="yellow", justify="right")
    table.add_column("Max Sale $", style="magenta", justify="right")

    for tier in ["new", "low", "medium", "high", "whale"]:
        stats = tier_stats.get(tier)
        if stats:
            table.add_row(
                tier.upper(),
                f"{stats.thread_count:,}",
                f"{stats.threads_with_sales:,}",
                f"${stats.total_sale_amount:,.0f}",
                f"${stats.avg_sale_amount:.0f}",
                f"${stats.median_sale_amount:.0f}",
                f"${stats.max_sale_amount:.0f}",
            )

    console.print(table)

    # Tips table
    table = Table(title="\nTip Statistics by Tier")
    table.add_column("Tier", style="cyan", width=10)
    table.add_column("With Tips", style="green", justify="right")
    table.add_column("Total Tips $", style="green", justify="right")
    table.add_column("Avg Tip $", style="yellow", justify="right")

    for tier in ["new", "low", "medium", "high", "whale"]:
        stats = tier_stats.get(tier)
        if stats:
            table.add_row(
                tier.upper(),
                f"{stats.threads_with_tips:,}",
                f"${stats.total_tip_amount:,.0f}",
                f"${stats.avg_tip_amount:.0f}" if stats.avg_tip_amount else "N/A",
            )

    console.print(table)

    # Approach distribution per tier
    console.print("\n[bold cyan]=== APPROACH USAGE BY TIER ===[/bold cyan]")
    console.print("[dim]What approaches are used for successful sales at each tier?[/dim]\n")

    for tier in ["new", "low", "medium", "high", "whale"]:
        stats = tier_stats.get(tier)
        if stats and stats.approach_distribution:
            console.print(f"[bold yellow]{tier.upper()}[/bold yellow]")

            # Calculate percentages
            total = sum(stats.approach_distribution.values())
            approaches_pct = [(k, v, v/total*100) for k, v in stats.approach_distribution.items()]
            approaches_pct.sort(key=lambda x: x[1], reverse=True)

            for approach, count, pct in approaches_pct[:5]:
                bar_len = int(pct / 3)
                bar = "#" * bar_len
                console.print(f"  {approach:15} {bar:20} {pct:5.1f}% ({count})")
            console.print()


def run_statistical_analysis(
    parsed_dir: Path = Path("data/parsed_conversations"),
    output_dir: Path = Path("data/insights/raw"),
    show_output: bool = True
) -> Dict[str, Any]:
    """
    Run full statistical analysis and save results.

    Args:
        parsed_dir: Path to parsed conversations
        output_dir: Path to save results
        show_output: Whether to print results

    Returns:
        Dictionary with all analysis results
    """
    # Load data
    threads, report = load_and_prepare_data(parsed_dir, show_progress=True, print_report=False)
    threads_by_tier = get_threads_by_tier(threads)

    # Calculate statistics
    tier_stats = calculate_tier_statistics(threads_by_tier)
    approach_effectiveness = calculate_approach_effectiveness(threads_by_tier)
    upselling_patterns = calculate_upselling_patterns(threads_by_tier)

    # Calculate sale distributions
    sale_distributions = {}
    for tier_name, stats in tier_stats.items():
        dist = calculate_sale_distribution(stats)
        sale_distributions[tier_name] = {
            "bins": dist.bins,
            "percentiles": dist.percentiles,
        }

    # Print results
    if show_output:
        print_tier_statistics(tier_stats)

        # Print approach effectiveness
        console.print("\n[bold cyan]=== APPROACH DETAILS BY TIER ===[/bold cyan]\n")
        for tier in ["new", "low", "medium", "high", "whale"]:
            if tier in approach_effectiveness:
                console.print(f"[bold yellow]{tier.upper()}[/bold yellow]")
                approaches = approach_effectiveness[tier]
                sorted_approaches = sorted(approaches.items(), key=lambda x: x[1]["count"], reverse=True)

                table = Table()
                table.add_column("Approach", style="cyan")
                table.add_column("Count", justify="right")
                table.add_column("Avg Sale $", justify="right")
                table.add_column("Total $", justify="right")

                for approach, data in sorted_approaches[:5]:
                    table.add_row(
                        approach,
                        str(data["count"]),
                        f"${data['avg_sale_amount']:.0f}",
                        f"${data['total_sale_amount']:.0f}",
                    )
                console.print(table)
                console.print()

        # Print upselling patterns
        console.print("\n[bold cyan]=== UPSELLING PATTERNS ===[/bold cyan]")
        console.print("[dim]How do current sales relate to subscriber's highest previous purchase?[/dim]\n")

        table = Table()
        table.add_column("Tier", style="cyan")
        table.add_column("Sale/HighestPurchase Ratio", justify="right")
        table.add_column("New Records Set", justify="right")
        table.add_column("New Record %", justify="right")

        for tier in ["new", "low", "medium", "high", "whale"]:
            if tier in upselling_patterns:
                analysis = upselling_patterns[tier]
                table.add_row(
                    tier.upper(),
                    f"{analysis.avg_sale_vs_highest_ratio:.2f}x",
                    str(analysis.threads_above_previous_max),
                    f"{analysis.new_high_percentage:.1f}%",
                )

        console.print(table)

    # Compile results
    results = {
        "tier_statistics": {k: v.to_dict() for k, v in tier_stats.items()},
        "approach_by_tier": approach_effectiveness,
        "sale_distributions": sale_distributions,
        "upselling_patterns": {k: asdict(v) for k, v in upselling_patterns.items()},
        "metadata": {
            "total_threads": len(threads),
            "total_screenshots": sum(len(t.screenshots) for t in threads),
            "note": "All data represents successful sales. Selection bias present.",
        }
    }

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "tier_statistics.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if show_output:
        console.print(f"\n[green]Results saved to {output_path}[/green]")

    return results


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run statistical analysis on conversation data")
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

    run_statistical_analysis(
        parsed_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        show_output=not args.quiet
    )
