# -*- coding: utf-8 -*-
"""
Enhanced Playbook Generator

Combines Perplexity research + real conversation examples into
evidence-based training playbooks.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from rich.console import Console

console = Console()


@dataclass
class PlaybookSection:
    """A section of an enhanced playbook."""
    title: str
    statistics: Dict
    research: Dict
    successful_examples: List[Dict]
    failed_examples: List[Dict]


def load_research(research_file: Path) -> Dict:
    """Load Perplexity research results."""
    if not research_file.exists():
        return {}
    with open(research_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_examples(examples_file: Path) -> Dict:
    """Load extracted conversation examples."""
    if not examples_file.exists():
        return {}
    with open(examples_file, "r", encoding="utf-8") as f:
        return json.load(f)


def load_objection_stats(stats_file: Path) -> Dict:
    """Load objection statistics."""
    # We'll generate these from the objection_instances.json
    instances_file = Path("data/insights/raw/objection_instances.json")
    if not instances_file.exists():
        return {}

    with open(instances_file, "r", encoding="utf-8") as f:
        instances = json.load(f)

    stats = {}
    for obj_type in ["price", "timing", "trust", "need", "commitment"]:
        type_instances = [i for i in instances if i["objection_type"] == obj_type]
        successful = [i for i in type_instances if i["resulted_in_sale"]]

        stats[obj_type] = {
            "total_count": len(type_instances),
            "success_count": len(successful),
            "success_rate": (len(successful) / len(type_instances) * 100) if type_instances else 0,
            "total_revenue": sum(i.get("sale_amount") or 0 for i in successful),
            "avg_sale": (sum(i.get("sale_amount") or 0 for i in successful) / len(successful)) if successful else 0,
            "by_tier": {}
        }

        # By tier breakdown
        for tier in ["new", "low", "medium", "high", "whale"]:
            tier_instances = [i for i in type_instances if i.get("subscriber_tier") == tier]
            tier_successful = [i for i in tier_instances if i["resulted_in_sale"]]
            if tier_instances:
                stats[obj_type]["by_tier"][tier] = {
                    "count": len(tier_instances),
                    "success_count": len(tier_successful),
                    "success_rate": (len(tier_successful) / len(tier_instances) * 100),
                    "avg_sale": (sum(i.get("sale_amount") or 0 for i in tier_successful) / len(tier_successful)) if tier_successful else 0
                }

    return stats


def format_example_markdown(example: Dict, number: int) -> str:
    """Format a single conversation example as markdown."""
    lines = []

    chatter = example.get("chatter", "Unknown")
    tier = example.get("tier", "unknown").upper()
    sale_amount = example.get("sale_amount")
    outcome = f"${sale_amount:.0f} sale" if sale_amount else "No sale"

    lines.append(f"#### Example {number}: {chatter} ({tier} tier) - {outcome}")
    lines.append("")

    messages = example.get("messages", [])
    highlight_start = example.get("highlight_start", 0)
    highlight_end = example.get("highlight_end", len(messages) - 1)

    for i, msg in enumerate(messages):
        role = msg.get("role", "").upper()
        text = msg.get("text", "")[:200]  # Truncate long messages

        # Bold highlight key messages
        if highlight_start <= i <= highlight_end:
            if role == "SUBSCRIBER":
                lines.append(f"> **SUB:** {text}")
            else:
                lines.append(f"> **CREATOR:** {text}")
        else:
            if role == "SUBSCRIBER":
                lines.append(f"> SUB: {text}")
            else:
                lines.append(f"> CREATOR: {text}")

    if sale_amount:
        lines.append(f"> **[SALE: ${sale_amount:.0f}]**")

    # Analysis
    analysis = example.get("analysis", "")
    if analysis:
        lines.append("")
        lines.append(f"*Why it worked: {analysis}*")

    lines.append("")
    return "\n".join(lines)


def generate_enhanced_objection_playbook(
    research: Dict,
    examples: Dict,
    stats: Dict,
    output_path: Path
) -> str:
    """Generate the enhanced objection handling playbook."""

    lines = [
        "# Evidence-Based Objection Handling Playbook",
        "",
        "Training guide combining psychological research with real conversation examples.",
        "",
        f"**Data source:** 1,604 objections from 1,295 conversations",
        f"**Research source:** Perplexity AI (sales psychology, behavioral research)",
        "",
        "---",
        "",
        "## Quick Reference",
        "",
        "| Objection Type | Count | Success Rate | Avg Sale | Best Tier |",
        "|----------------|-------|--------------|----------|-----------|",
    ]

    # Summary table
    for obj_type in ["price", "timing", "trust", "need", "commitment"]:
        s = stats.get(obj_type, {})
        by_tier = s.get("by_tier", {})
        best_tier = max(by_tier.items(), key=lambda x: x[1].get("success_rate", 0))[0] if by_tier else "N/A"

        lines.append(
            f"| {obj_type.title()} | {s.get('total_count', 0)} | "
            f"{s.get('success_rate', 0):.1f}% | ${s.get('avg_sale', 0):.0f} | {best_tier.upper()} |"
        )

    lines.extend(["", "---", ""])

    # Detailed sections for each objection type
    for obj_type in ["price", "timing", "trust", "need", "commitment"]:
        lines.extend(generate_objection_section(obj_type, research, examples, stats))

    content = "\n".join(lines)

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    console.print(f"[green]Enhanced playbook saved to {output_path}[/green]")
    return content


def generate_objection_section(
    obj_type: str,
    research: Dict,
    examples: Dict,
    stats: Dict
) -> List[str]:
    """Generate a detailed section for one objection type."""
    lines = []

    s = stats.get(obj_type, {})
    r = research.get(obj_type, {})
    obj_examples = examples.get("objections", {}).get(obj_type, {})

    type_titles = {
        "price": "Price Objections: \"I can't afford it\" / \"Too expensive\"",
        "timing": "Timing Objections: \"Maybe later\" / \"Not now\"",
        "trust": "Trust Objections: \"Is it worth it?\" / \"How do I know?\"",
        "need": "Need Objections: \"I don't need it\" / \"Not interested\"",
        "commitment": "Commitment Objections: \"Let me think about it\" / \"Maybe\""
    }

    lines.append(f"## {type_titles.get(obj_type, obj_type.title())}")
    lines.append("")

    # Statistics
    lines.append("### The Data")
    lines.append("")
    lines.append(f"- **Total instances:** {s.get('total_count', 0)}")
    lines.append(f"- **Success rate:** {s.get('success_rate', 0):.1f}%")
    lines.append(f"- **Average sale after handling:** ${s.get('avg_sale', 0):.0f}")
    lines.append(f"- **Total revenue from successful handling:** ${s.get('total_revenue', 0):,.0f}")
    lines.append("")

    # Tier breakdown
    by_tier = s.get("by_tier", {})
    if by_tier:
        lines.append("**Success Rate by Tier:**")
        lines.append("")
        lines.append("| Tier | Count | Success Rate | Avg Sale |")
        lines.append("|------|-------|--------------|----------|")
        for tier in ["new", "low", "medium", "high", "whale"]:
            t = by_tier.get(tier, {})
            if t:
                lines.append(
                    f"| {tier.upper()} | {t.get('count', 0)} | "
                    f"{t.get('success_rate', 0):.1f}% | ${t.get('avg_sale', 0):.0f} |"
                )
        lines.append("")

    # Research findings
    findings = r.get("findings", "")
    key_points = r.get("key_points", [])

    if key_points:
        lines.append("### The Psychology")
        lines.append("")
        lines.append("Research-backed insights on why these objections occur and how to address them:")
        lines.append("")
        for point in key_points[:6]:  # Top 6 points
            if point and len(point) > 20:
                lines.append(f"- {point}")
        lines.append("")

    # Extract techniques from research
    if "PRACTICAL TECHNIQUES" in findings:
        tech_section = findings.split("PRACTICAL TECHNIQUES")[1].split("SOURCES")[0] if "SOURCES" in findings else findings.split("PRACTICAL TECHNIQUES")[1]
        lines.append("### Proven Techniques")
        lines.append("")
        # Extract first few technique descriptions
        tech_lines = [l.strip() for l in tech_section.split("\n") if l.strip() and len(l.strip()) > 30][:5]
        for tech in tech_lines:
            if tech.startswith("- ") or tech.startswith("**"):
                lines.append(tech)
        lines.append("")

    # Real conversation examples - successful
    successful = obj_examples.get("successful", [])
    if successful:
        lines.append("### Real Examples That Worked")
        lines.append("")
        for i, ex in enumerate(successful[:3], 1):  # Top 3
            lines.append(format_example_markdown(ex, i))

    # Real conversation examples - failed
    failed = obj_examples.get("failed", [])
    if failed:
        lines.append("### What Didn't Work")
        lines.append("")
        lines.append("Learn from these failed attempts:")
        lines.append("")
        for i, ex in enumerate(failed[:2], 1):  # Top 2
            lines.append(format_example_markdown(ex, i))

    # Response templates
    lines.append("### Response Templates")
    lines.append("")
    templates = get_response_templates(obj_type)
    for template in templates:
        lines.append(f"```")
        lines.append(template)
        lines.append(f"```")
        lines.append("")

    lines.extend(["---", ""])

    return lines


def get_response_templates(obj_type: str) -> List[str]:
    """Get response templates for each objection type."""
    templates = {
        "price": [
            "Acknowledgment: \"I totally get it babe, [price] isn't nothing\"\nBridge: \"how much can u do?\"\nNegotiate: \"let me see what I can put together for that\"",
            "Reframe value: \"This isn't just a video - it's [X minutes] of [specific content] just for you\"\nOffer alternative: \"I also have something at [lower price] if that works better\""
        ],
        "timing": [
            "Accept + Schedule: \"No rush at all babe. When's payday?\"\nFollow-up: \"I'll save something special for you then\"",
            "Create FOMO: \"I understand! Just so you know, this [content] is only available this week\"\nSoft close: \"Want me to hold it for you?\""
        ],
        "trust": [
            "Offer proof: \"Here's a little preview...\"\nSocial proof: \"This was my most popular video last month\"\nRisk reversal: \"If you don't love it, I'll make it right\"",
            "Build credibility: \"I've been doing this for [X months/years]\"\nPersonalize: \"I remember you mentioned you liked [X], this is exactly that\""
        ],
        "need": [
            "Explore interests: \"What are you in the mood for today?\"\nRedirect: \"What would you like to see from me?\"\nCreate desire: \"I just filmed something I think you'd really enjoy...\"",
            "Soft acceptance: \"No problem babe, just wanted to share\"\nPlant seed: \"Let me know if you change your mind\""
        ],
        "commitment": [
            "Reduce pressure: \"Take your time, no rush at all\"\nRedirect: [Change subject to build rapport]\nReturn later: [Bring back offer naturally after more conversation]",
            "Small commitment: \"How about just the preview for now?\"\nFoot-in-door: \"Want me to send you a teaser first?\""
        ]
    }
    return templates.get(obj_type, [])


def main():
    """Generate all enhanced playbooks."""
    console.print("[bold]Generating Enhanced Playbooks[/bold]\n")

    # Load data
    research = load_research(Path("data/insights/research/objection_research.json"))
    examples = load_examples(Path("data/insights/examples/conversation_examples.json"))
    stats = load_objection_stats(Path("data/insights/raw/objection_instances.json"))

    if not research:
        console.print("[yellow]No research found. Run perplexity_research.py first.[/yellow]")
    if not examples:
        console.print("[yellow]No examples found. Run example_extractor.py first.[/yellow]")

    # Generate objection playbook
    generate_enhanced_objection_playbook(
        research,
        examples,
        stats,
        Path("data/insights/playbooks/objection_playbook_enhanced.md")
    )

    console.print("\n[bold green]Enhanced playbook generation complete![/bold green]")


if __name__ == "__main__":
    main()
