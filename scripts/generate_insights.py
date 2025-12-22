"""
Training Insights Generator

Analyzes parsed conversation data to find patterns and generate actionable insights.
Uses statistical analysis + GPT-5.2 for pattern recognition.
"""

import json
import os
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
import random

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

console = Console()


@dataclass
class ConversationStats:
    """Aggregated stats from a conversation."""
    total_spent: Optional[float] = None
    tips: Optional[float] = None
    buy_rate: Optional[str] = None
    sale_made: bool = False
    sale_amount: Optional[float] = None
    tip_received: bool = False
    tip_amount: Optional[float] = None
    technique: Optional[str] = None
    stage: Optional[str] = None
    subscriber_mood: Optional[str] = None
    creator_approach: Optional[str] = None
    message_count: int = 0


def load_parsed_conversations(parsed_dir: Path) -> list[dict]:
    """Load all successfully parsed conversations."""
    conversations = []

    files = list(parsed_dir.rglob("*.json"))
    files = [f for f in files if not f.name.startswith(".")]

    console.print(f"[blue]Loading {len(files)} parsed files...[/blue]")

    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)

            if data.get("success") and not data.get("parsed_data", {}).get("empty"):
                conversations.append({
                    "file": str(f),
                    "data": data.get("parsed_data", {})
                })
        except:
            continue

    console.print(f"[green]Loaded {len(conversations)} valid conversations[/green]")
    return conversations


def extract_stats(conversations: list[dict]) -> list[ConversationStats]:
    """Extract stats from parsed conversations."""
    stats_list = []

    for conv in conversations:
        data = conv.get("data", {})

        sub_stats = data.get("subscriber_stats", {}) or {}
        outcome = data.get("outcome", {}) or {}
        context = data.get("context", {}) or {}
        messages = data.get("messages", []) or []

        stats = ConversationStats(
            total_spent=sub_stats.get("total_spent"),
            tips=sub_stats.get("tips"),
            buy_rate=sub_stats.get("buy_rate"),
            sale_made=outcome.get("sale_in_screenshot", False),
            sale_amount=outcome.get("sale_amount"),
            tip_received=outcome.get("tip_received", False),
            tip_amount=outcome.get("tip_amount"),
            technique=outcome.get("technique_observed"),
            stage=context.get("conversation_stage"),
            subscriber_mood=context.get("subscriber_mood"),
            creator_approach=context.get("creator_approach"),
            message_count=len(messages),
        )
        stats_list.append(stats)

    return stats_list


def statistical_analysis(stats_list: list[ConversationStats]) -> dict:
    """Perform statistical analysis on conversation data."""

    results = {
        "total_conversations": len(stats_list),
        "sales": {"total": 0, "total_amount": 0},
        "tips": {"total": 0, "total_amount": 0},
        "by_stage": defaultdict(lambda: {"count": 0, "sales": 0, "tips": 0}),
        "by_mood": defaultdict(lambda: {"count": 0, "sales": 0, "tips": 0}),
        "by_approach": defaultdict(lambda: {"count": 0, "sales": 0, "tips": 0}),
        "techniques": defaultdict(int),
        "subscriber_tiers": {"free": 0, "low": 0, "medium": 0, "high": 0, "whale": 0},
    }

    for stats in stats_list:
        # Sales
        if stats.sale_made:
            results["sales"]["total"] += 1
            if stats.sale_amount:
                results["sales"]["total_amount"] += stats.sale_amount

        # Tips
        if stats.tip_received:
            results["tips"]["total"] += 1
            if stats.tip_amount:
                results["tips"]["total_amount"] += stats.tip_amount

        # By stage
        if stats.stage:
            results["by_stage"][stats.stage]["count"] += 1
            if stats.sale_made:
                results["by_stage"][stats.stage]["sales"] += 1
            if stats.tip_received:
                results["by_stage"][stats.stage]["tips"] += 1

        # By mood
        if stats.subscriber_mood:
            results["by_mood"][stats.subscriber_mood]["count"] += 1
            if stats.sale_made:
                results["by_mood"][stats.subscriber_mood]["sales"] += 1
            if stats.tip_received:
                results["by_mood"][stats.subscriber_mood]["tips"] += 1

        # By approach
        if stats.creator_approach:
            results["by_approach"][stats.creator_approach]["count"] += 1
            if stats.sale_made:
                results["by_approach"][stats.creator_approach]["sales"] += 1
            if stats.tip_received:
                results["by_approach"][stats.creator_approach]["tips"] += 1

        # Techniques
        if stats.technique:
            results["techniques"][stats.technique] += 1

        # Subscriber tiers
        if stats.total_spent:
            if stats.total_spent >= 5000:
                results["subscriber_tiers"]["whale"] += 1
            elif stats.total_spent >= 1000:
                results["subscriber_tiers"]["high"] += 1
            elif stats.total_spent >= 200:
                results["subscriber_tiers"]["medium"] += 1
            elif stats.total_spent > 0:
                results["subscriber_tiers"]["low"] += 1
            else:
                results["subscriber_tiers"]["free"] += 1

    return results


def print_statistical_results(results: dict):
    """Print statistical analysis results."""

    console.print("\n[bold cyan]=== STATISTICAL ANALYSIS ===[/bold cyan]\n")

    # Overview
    console.print(f"[bold]Total Conversations Analyzed:[/bold] {results['total_conversations']}")
    console.print(f"[bold]Sales Detected:[/bold] {results['sales']['total']} (${results['sales']['total_amount']:,.0f} total)")
    console.print(f"[bold]Tips Detected:[/bold] {results['tips']['total']} (${results['tips']['total_amount']:,.0f} total)")

    # By Stage
    console.print("\n[bold yellow]Conversion by Stage:[/bold yellow]")
    table = Table()
    table.add_column("Stage")
    table.add_column("Count")
    table.add_column("Sales")
    table.add_column("Rate")

    for stage, data in sorted(results["by_stage"].items(), key=lambda x: x[1]["count"], reverse=True):
        rate = (data["sales"] / data["count"] * 100) if data["count"] > 0 else 0
        table.add_row(stage, str(data["count"]), str(data["sales"]), f"{rate:.1f}%")
    console.print(table)

    # By Mood
    console.print("\n[bold yellow]Conversion by Subscriber Mood:[/bold yellow]")
    table = Table()
    table.add_column("Mood")
    table.add_column("Count")
    table.add_column("Sales")
    table.add_column("Rate")

    for mood, data in sorted(results["by_mood"].items(), key=lambda x: x[1]["count"], reverse=True):
        rate = (data["sales"] / data["count"] * 100) if data["count"] > 0 else 0
        table.add_row(mood, str(data["count"]), str(data["sales"]), f"{rate:.1f}%")
    console.print(table)

    # By Approach
    console.print("\n[bold yellow]Conversion by Creator Approach:[/bold yellow]")
    table = Table()
    table.add_column("Approach")
    table.add_column("Count")
    table.add_column("Sales")
    table.add_column("Rate")

    for approach, data in sorted(results["by_approach"].items(), key=lambda x: x[1]["count"], reverse=True):
        rate = (data["sales"] / data["count"] * 100) if data["count"] > 0 else 0
        table.add_row(approach, str(data["count"]), str(data["sales"]), f"{rate:.1f}%")
    console.print(table)

    # Subscriber Tiers
    console.print("\n[bold yellow]Subscriber Tiers:[/bold yellow]")
    for tier, count in results["subscriber_tiers"].items():
        console.print(f"  {tier.capitalize()}: {count}")

    # Top Techniques
    console.print("\n[bold yellow]Top Techniques Observed:[/bold yellow]")
    sorted_techniques = sorted(results["techniques"].items(), key=lambda x: x[1], reverse=True)[:15]
    for technique, count in sorted_techniques:
        console.print(f"  [{count}x] {technique[:80]}...")


def ai_pattern_analysis(conversations: list[dict], model: str = "gpt-5.2") -> str:
    """Use AI to find deeper patterns in the conversation data."""

    console.print(f"\n[bold cyan]=== AI PATTERN ANALYSIS (using {model}) ===[/bold cyan]\n")

    import openai
    client = openai.OpenAI()

    # Sample conversations for analysis (too many would exceed context)
    sample_size = min(100, len(conversations))
    sampled = random.sample(conversations, sample_size)

    # Prepare summary of conversations for AI
    summaries = []
    for conv in sampled:
        data = conv.get("data", {})
        outcome = data.get("outcome", {}) or {}
        context = data.get("context", {}) or {}
        sub_stats = data.get("subscriber_stats", {}) or {}

        summary = {
            "spent": sub_stats.get("total_spent"),
            "stage": context.get("conversation_stage"),
            "mood": context.get("subscriber_mood"),
            "approach": context.get("creator_approach"),
            "sale": outcome.get("sale_in_screenshot"),
            "tip": outcome.get("tip_received"),
            "technique": outcome.get("technique_observed"),
        }
        summaries.append(summary)

    prompt = f"""Analyze these {sample_size} OnlyFans chat conversation summaries and identify:

1. **Winning Patterns**: What combinations of approach + mood + stage lead to sales?
2. **Best Techniques**: Which sales techniques work best?
3. **Subscriber Insights**: How should chatters handle different subscriber types?
4. **Actionable Tips**: Give 5-10 specific, actionable tips for chatters based on this data.

DATA:
{json.dumps(summaries, indent=2)}

Provide a detailed analysis with specific percentages and recommendations. Be direct and practical - these insights will be used to train chatters."""

    console.print(f"[blue]Sending {sample_size} conversation summaries to {model}...[/blue]")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert sales analyst specializing in OnlyFans creator monetization strategies."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=4000,
    )

    analysis = response.choices[0].message.content
    return analysis


def save_insights(results: dict, ai_analysis: str, output_path: Path):
    """Save insights to file."""

    output = {
        "statistical_analysis": {
            "total_conversations": results["total_conversations"],
            "sales": results["sales"],
            "tips": results["tips"],
            "by_stage": dict(results["by_stage"]),
            "by_mood": dict(results["by_mood"]),
            "by_approach": dict(results["by_approach"]),
            "subscriber_tiers": results["subscriber_tiers"],
            "top_techniques": dict(sorted(results["techniques"].items(), key=lambda x: x[1], reverse=True)[:20]),
        },
        "ai_analysis": ai_analysis,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Also save markdown version
    md_path = output_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Chatter Training Insights\n\n")
        f.write(f"Based on analysis of {results['total_conversations']} real conversations.\n\n")
        f.write("## AI Analysis\n\n")
        f.write(ai_analysis)
        f.write("\n\n## Statistical Summary\n\n")
        f.write(f"- Total Conversations: {results['total_conversations']}\n")
        f.write(f"- Sales Detected: {results['sales']['total']} (${results['sales']['total_amount']:,.0f})\n")
        f.write(f"- Tips Detected: {results['tips']['total']} (${results['tips']['total_amount']:,.0f})\n")

    print(f"\nInsights saved to {output_path} and {md_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate training insights from parsed conversations")
    parser.add_argument("--input-dir", default="data/parsed_conversations", help="Parsed conversations directory")
    parser.add_argument("--output", default="data/insights/training_insights.json", help="Output file")
    parser.add_argument("--model", default="gpt-5.2", help="Model for AI analysis")
    parser.add_argument("--skip-ai", action="store_true", help="Skip AI analysis, only do statistics")

    args = parser.parse_args()

    # Load data
    parsed_dir = Path(args.input_dir)
    conversations = load_parsed_conversations(parsed_dir)

    if not conversations:
        console.print("[red]No conversations found![/red]")
        return

    # Extract stats
    stats_list = extract_stats(conversations)

    # Statistical analysis
    results = statistical_analysis(stats_list)
    print_statistical_results(results)

    # AI analysis
    ai_analysis = ""
    if not args.skip_ai:
        ai_analysis = ai_pattern_analysis(conversations, model=args.model)
        console.print("\n[bold cyan]=== AI INSIGHTS ===[/bold cyan]\n")
        # Print safely for Windows console
        try:
            console.print(ai_analysis)
        except UnicodeEncodeError:
            print(ai_analysis.encode('ascii', 'replace').decode('ascii'))

    # Save results
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_insights(results, ai_analysis, output_path)


if __name__ == "__main__":
    main()
