"""
AI Pattern Analysis Module for Chatter Training Data

Uses GPT-5.2 to analyze conversation patterns and generate:
- Full conversation thread analysis
- Tier-specific playbooks
- Script templates
- Technique deep dives

IMPORTANT: All data represents successful sales (selection bias).
We characterize "what success looks like", NOT what works vs what doesn't.
"""

import json
import random
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from collections import defaultdict

from dotenv import load_dotenv
load_dotenv()

import openai
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from scripts.analysis.data_loader import (
    SubscriberTier, ConversationThread,
    load_and_prepare_data, get_threads_by_tier
)

console = Console()


# ============================================================================
# Utility Functions
# ============================================================================

def format_thread_for_ai(thread: ConversationThread, max_messages: int = 30) -> str:
    """Format a conversation thread for AI analysis."""
    lines = []

    # Header
    lines.append(f"=== CONVERSATION: {thread.title} ===")
    lines.append(f"Chatter: {thread.chatter}")
    lines.append(f"Category: {thread.category}")

    # Subscriber stats
    stats = thread.subscriber_stats
    if stats:
        lines.append(f"\nSUBSCRIBER PROFILE:")
        if stats.total_spent is not None:
            lines.append(f"  Total Spent: ${stats.total_spent:,.0f}")
        if stats.tips is not None:
            lines.append(f"  Tips Given: ${stats.tips:,.0f}")
        if stats.highest_purchase is not None:
            lines.append(f"  Highest Purchase: ${stats.highest_purchase}")
        if stats.subscription_status:
            lines.append(f"  Subscription: {stats.subscription_status}")
        if stats.renew:
            lines.append(f"  Auto-Renew: {stats.renew}")

    lines.append(f"  Tier: {thread.tier.value.upper()}")

    # Outcome
    lines.append(f"\nOUTCOME:")
    lines.append(f"  Sale Made: {thread.has_sale}")
    if thread.has_sale:
        lines.append(f"  Sale Amount: ${thread.total_sale_amount:,.0f}")
    lines.append(f"  Tip Received: {thread.has_tip}")
    if thread.has_tip:
        lines.append(f"  Tip Amount: ${thread.total_tip_amount:,.0f}")

    # Messages
    lines.append(f"\nMESSAGES ({len(thread.all_messages)} total):")
    messages = thread.all_messages[:max_messages]
    for msg in messages:
        if msg.text:
            role = "CREATOR" if msg.role == "creator" else "SUB"
            # Truncate long messages
            text = msg.text[:300] + "..." if len(msg.text) > 300 else msg.text
            lines.append(f"  [{role}]: {text}")

    if len(thread.all_messages) > max_messages:
        lines.append(f"  ... ({len(thread.all_messages) - max_messages} more messages)")

    return "\n".join(lines)


def sample_threads_by_tier(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]],
    samples_per_tier: int = 10
) -> Dict[SubscriberTier, List[ConversationThread]]:
    """Sample threads from each tier for AI analysis."""
    sampled = {}
    for tier, threads in threads_by_tier.items():
        if len(threads) <= samples_per_tier:
            sampled[tier] = threads
        else:
            # Prioritize threads with sales and variety of outcomes
            with_sales = [t for t in threads if t.has_sale and t.total_sale_amount > 0]
            with_tips = [t for t in threads if t.has_tip]

            # Sample mix
            sample = []
            if with_sales:
                sample.extend(random.sample(with_sales, min(samples_per_tier // 2, len(with_sales))))
            if with_tips:
                remaining = samples_per_tier - len(sample)
                sample.extend(random.sample([t for t in with_tips if t not in sample],
                                           min(remaining // 2, len(with_tips))))

            # Fill remaining with random
            remaining = samples_per_tier - len(sample)
            if remaining > 0:
                available = [t for t in threads if t not in sample]
                sample.extend(random.sample(available, min(remaining, len(available))))

            sampled[tier] = sample

    return sampled


# ============================================================================
# AI Analysis Functions
# ============================================================================

def analyze_tier_patterns(
    tier: SubscriberTier,
    threads: List[ConversationThread],
    model: str = "gpt-5.2"
) -> str:
    """
    Use AI to analyze conversation patterns for a specific tier.

    Returns structured analysis text.
    """
    client = openai.OpenAI()

    # Format sample conversations
    conversation_samples = []
    for thread in threads[:8]:  # Limit to avoid token overflow
        conversation_samples.append(format_thread_for_ai(thread, max_messages=20))

    conversations_text = "\n\n---\n\n".join(conversation_samples)

    # Build the prompt
    tier_descriptions = {
        SubscriberTier.NEW: "New subscribers with $0 spend history (first-timers or free trial)",
        SubscriberTier.LOW: "Low spenders ($1-199 total) - occasional buyers",
        SubscriberTier.MEDIUM: "Medium spenders ($200-999 total) - regular buyers",
        SubscriberTier.HIGH: "High spenders ($1,000-4,999 total) - high-value subscribers",
        SubscriberTier.WHALE: "Whales ($5,000+ total) - VIP top-tier subscribers",
    }

    prompt = f"""You are analyzing OnlyFans conversation data for chatter training.

TIER: {tier.value.upper()} - {tier_descriptions[tier]}

IMPORTANT CONTEXT:
- All conversations shown are SUCCESSFUL sales (selection bias - we don't have failed attempts)
- Your job is to describe "what successful sales look like" for this tier, NOT calculate conversion rates
- Focus on actionable patterns: openers, escalation, pricing, closing techniques

Here are {len(threads)} sample successful conversations with {tier.value.upper()} subscribers:

{conversations_text}

Analyze these conversations and provide:

1. **OPENING PATTERNS** (How do chatters successfully open with this tier?)
   - What greetings work?
   - How quickly do they get to the point?
   - First message characteristics

2. **ESCALATION PATTERNS** (How do conversations progress to a sale?)
   - Typical conversation arc
   - How is desire/interest built?
   - Key turning points

3. **PRICING PATTERNS** (How is money discussed with this tier?)
   - Typical price points
   - How prices are presented
   - Discount/negotiation patterns

4. **CLOSING TECHNIQUES** (How are sales finalized?)
   - Specific phrases that precede sales
   - Urgency tactics used
   - Final push techniques

5. **TIER-SPECIFIC TIPS** (What makes this tier unique?)
   - What works specifically for {tier.value.upper()} subs?
   - Common mistakes to avoid
   - Key differences from other tiers

Be specific. Quote actual phrases from the conversations. Give actionable advice a chatter could use immediately."""

    console.print(f"[blue]Analyzing {tier.value.upper()} tier with {model}...[/blue]")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert sales conversation analyst specializing in OnlyFans creator monetization strategies. You provide direct, practical advice based on real data."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=3000,
        temperature=0.3,
    )

    return response.choices[0].message.content


def generate_playbook(
    tier: SubscriberTier,
    analysis: str,
    stats: Dict[str, Any],
    model: str = "gpt-5.2"
) -> str:
    """Generate a structured playbook for a tier based on analysis."""
    client = openai.OpenAI()

    tier_stats = stats.get("tier_statistics", {}).get(tier.value, {})

    prompt = f"""Based on this analysis of successful {tier.value.upper()} subscriber conversations:

{analysis}

And these statistics:
- Total conversations analyzed: {tier_stats.get('thread_count', 'N/A')}
- Threads with sales: {tier_stats.get('threads_with_sales', 'N/A')}
- Average sale amount: ${tier_stats.get('avg_sale_amount', 0):.0f}
- Max sale amount: ${tier_stats.get('max_sale_amount', 0):.0f}
- Average tip amount: ${tier_stats.get('avg_tip_amount', 0):.0f}

Create a PLAYBOOK for chatters working with {tier.value.upper()} subscribers.

Format as a practical guide with:

## {tier.value.upper()} SUBSCRIBER PLAYBOOK

### Quick Profile
- Who they are
- What they want
- Typical behavior

### Opening Strategy
- Recommended openers (3-5 copy-paste ready examples)
- What to avoid

### Conversation Flow
- Step-by-step escalation
- Key checkpoints

### Pricing Strategy
- Recommended price ranges
- How to present prices
- When to offer discounts

### Closing Scripts
- 3-5 closing phrases that work
- Urgency techniques

### Red Flags
- Signs they won't buy
- When to disengage

### Golden Rules
- 3-5 must-follow rules for this tier

Make it practical and copy-paste ready. Use bullet points and short sentences."""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are creating a practical sales playbook for OnlyFans chatters. Be direct, specific, and actionable."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=2500,
        temperature=0.4,
    )

    return response.choices[0].message.content


def extract_script_templates(
    threads_by_tier: Dict[SubscriberTier, List[ConversationThread]],
    model: str = "gpt-5.2"
) -> Dict[str, List[str]]:
    """Extract script templates from conversations."""
    client = openai.OpenAI()

    # Collect example messages across all tiers
    openers = []
    tip_requests = []
    ppv_pitches = []
    closings = []

    for tier, threads in threads_by_tier.items():
        for thread in threads[:20]:  # Sample
            messages = thread.all_messages

            # First creator message = opener
            for msg in messages:
                if msg.role == "creator" and msg.text:
                    openers.append(msg.text[:200])
                    break

            # Look for money-related messages
            for msg in messages:
                if msg.role == "creator" and msg.text:
                    text_lower = msg.text.lower()
                    if "tip" in text_lower:
                        tip_requests.append(msg.text[:200])
                    if any(w in text_lower for w in ["unlock", "ppv", "send you", "show you"]):
                        ppv_pitches.append(msg.text[:200])
                    if "$" in msg.text:
                        closings.append(msg.text[:200])

    # Use AI to extract templates
    prompt = f"""Analyze these real OnlyFans chatter messages and extract the BEST patterns as reusable templates.

OPENERS (first messages):
{chr(10).join(openers[:30])}

TIP REQUESTS:
{chr(10).join(tip_requests[:30])}

PPV PITCHES:
{chr(10).join(ppv_pitches[:30])}

CLOSINGS (with prices):
{chr(10).join(closings[:30])}

Extract and format as JSON:
{{
    "openers": ["template 1", "template 2", ...],  // 10 best opener templates
    "tip_requests": ["template 1", ...],  // 10 best tip request templates
    "ppv_pitches": ["template 1", ...],  // 10 best PPV pitch templates
    "closings": ["template 1", ...]  // 10 best closing templates
}}

Use [VARIABLE] for customizable parts like [NAME], [PRICE], [CONTENT_TYPE], etc.
Make templates natural-sounding and copy-paste ready."""

    console.print(f"[blue]Extracting script templates with {model}...[/blue]")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are extracting practical script templates from real sales conversations. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        max_completion_tokens=2000,
        temperature=0.3,
    )

    # Parse JSON from response
    content = response.choices[0].message.content

    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]

    try:
        templates = json.loads(content)
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        templates = {
            "openers": ["Hey babe! How's your day going?"],
            "tip_requests": ["Would you tip me $[PRICE] for something special?"],
            "ppv_pitches": ["I have something hot to show you... want to see?"],
            "closings": ["Ready to unlock this for $[PRICE]?"],
        }

    return templates


# ============================================================================
# Main Runner
# ============================================================================

def run_ai_analysis(
    parsed_dir: Path = Path("data/parsed_conversations"),
    output_dir: Path = Path("data/insights"),
    model: str = "gpt-5.2",
    tiers_to_analyze: List[SubscriberTier] = None
) -> Dict[str, Any]:
    """
    Run full AI pattern analysis.

    Args:
        parsed_dir: Path to parsed conversations
        output_dir: Path to save results
        model: OpenAI model to use
        tiers_to_analyze: Specific tiers to analyze (default: all)
    """
    # Load data
    threads, report = load_and_prepare_data(parsed_dir, show_progress=True, print_report=False)
    threads_by_tier = get_threads_by_tier(threads)

    if tiers_to_analyze is None:
        tiers_to_analyze = list(SubscriberTier)

    # Load existing statistics
    stats_path = output_dir / "raw" / "tier_statistics.json"
    stats = {}
    if stats_path.exists():
        with open(stats_path) as f:
            stats = json.load(f)

    # Sample threads for analysis
    sampled = sample_threads_by_tier(threads_by_tier, samples_per_tier=15)

    results = {
        "tier_analyses": {},
        "playbooks": {},
        "templates": {},
        "model_used": model,
    }

    # Analyze each tier
    for tier in tiers_to_analyze:
        if tier not in sampled or not sampled[tier]:
            console.print(f"[yellow]Skipping {tier.value} - no data[/yellow]")
            continue

        console.print(f"\n[bold cyan]=== ANALYZING {tier.value.upper()} TIER ===[/bold cyan]\n")

        # Get tier analysis
        analysis = analyze_tier_patterns(tier, sampled[tier], model=model)
        results["tier_analyses"][tier.value] = analysis

        console.print(f"[green]Analysis complete for {tier.value.upper()}[/green]")

        # Generate playbook
        console.print(f"[blue]Generating playbook for {tier.value.upper()}...[/blue]")
        playbook = generate_playbook(tier, analysis, stats, model=model)
        results["playbooks"][tier.value] = playbook

        console.print(f"[green]Playbook generated for {tier.value.upper()}[/green]")

    # Extract script templates (uses all tiers)
    console.print("\n[bold cyan]=== EXTRACTING SCRIPT TEMPLATES ===[/bold cyan]\n")
    templates = extract_script_templates(threads_by_tier, model=model)
    results["templates"] = templates

    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save main results
    ai_results_path = output_dir / "raw" / "ai_analysis.json"
    ai_results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ai_results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save individual playbooks as markdown
    playbooks_dir = output_dir / "playbooks"
    playbooks_dir.mkdir(parents=True, exist_ok=True)

    for tier_name, playbook in results["playbooks"].items():
        playbook_path = playbooks_dir / f"{tier_name}_subscriber_playbook.md"
        with open(playbook_path, "w", encoding="utf-8") as f:
            f.write(playbook)
        console.print(f"[green]Saved: {playbook_path}[/green]")

    # Save templates
    templates_path = output_dir / "templates" / "script_templates.json"
    templates_path.parent.mkdir(parents=True, exist_ok=True)
    with open(templates_path, "w", encoding="utf-8") as f:
        json.dump(results["templates"], f, indent=2, ensure_ascii=False)
    console.print(f"[green]Saved: {templates_path}[/green]")

    console.print(f"\n[bold green]AI analysis complete! Results saved to {output_dir}[/bold green]")

    return results


# CLI interface
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run AI pattern analysis on conversation data")
    parser.add_argument(
        "--input-dir",
        default="data/parsed_conversations",
        help="Parsed conversations directory"
    )
    parser.add_argument(
        "--output-dir",
        default="data/insights",
        help="Output directory for results"
    )
    parser.add_argument(
        "--model",
        default="gpt-5.2",
        help="OpenAI model to use"
    )
    parser.add_argument(
        "--tier",
        choices=["new", "low", "medium", "high", "whale", "all"],
        default="all",
        help="Specific tier to analyze"
    )

    args = parser.parse_args()

    tiers = None
    if args.tier != "all":
        tier_map = {
            "new": SubscriberTier.NEW,
            "low": SubscriberTier.LOW,
            "medium": SubscriberTier.MEDIUM,
            "high": SubscriberTier.HIGH,
            "whale": SubscriberTier.WHALE,
        }
        tiers = [tier_map[args.tier]]

    run_ai_analysis(
        parsed_dir=Path(args.input_dir),
        output_dir=Path(args.output_dir),
        model=args.model,
        tiers_to_analyze=tiers
    )
