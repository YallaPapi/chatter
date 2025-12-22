# -*- coding: utf-8 -*-
"""
Perplexity Research Module

Uses Perplexity API to research psychological studies, sales techniques,
and other evidence to back up playbook recommendations.
"""

import os
import json
import time
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from dotenv import load_dotenv

import requests
from rich.console import Console
from rich.panel import Panel

load_dotenv()
console = Console()

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"


@dataclass
class ResearchResult:
    """A single research finding."""
    topic: str
    query: str
    findings: str
    sources: List[str] = field(default_factory=list)
    key_points: List[str] = field(default_factory=list)
    citations: List[Dict] = field(default_factory=list)
    timestamp: str = ""


class PerplexityResearcher:
    """Research assistant using Perplexity API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        if not self.api_key:
            raise ValueError("PERPLEXITY_API_KEY not found in environment")

    def research(
        self,
        query: str,
        context: Optional[str] = None,
        model: str = "sonar-pro"
    ) -> ResearchResult:
        """
        Research a topic using Perplexity.

        Args:
            query: The research question
            context: Optional context to focus the research
            model: Perplexity model to use

        Returns:
            ResearchResult with findings and sources
        """
        system_prompt = """You are a research assistant helping build evidence-based sales training materials.

Your task is to find psychological studies, sales research, and proven techniques related to the query.

Format your response as:
1. KEY FINDINGS: Bullet points of the most important findings
2. PSYCHOLOGICAL PRINCIPLES: Relevant principles (e.g., Cialdini's principles, cognitive biases)
3. PRACTICAL TECHNIQUES: Specific techniques backed by research
4. SOURCES: List the sources you found

Be specific and cite studies/researchers where possible."""

        if context:
            system_prompt += f"\n\nContext: {context}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            "max_tokens": 2000,
            "temperature": 0.2
        }

        try:
            response = requests.post(
                PERPLEXITY_API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])

            # Parse key points from content
            key_points = self._extract_key_points(content)

            return ResearchResult(
                topic=query[:100],
                query=query,
                findings=content,
                sources=[c.get("url", "") for c in citations if isinstance(c, dict)],
                key_points=key_points,
                citations=citations,
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )

        except requests.exceptions.RequestException as e:
            console.print(f"[red]Perplexity API error: {e}[/red]")
            return ResearchResult(
                topic=query[:100],
                query=query,
                findings=f"Error: {str(e)}",
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S")
            )

    def _extract_key_points(self, content: str) -> List[str]:
        """Extract bullet points from research content."""
        points = []
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(("- ", "• ", "* ", "1.", "2.", "3.", "4.", "5.")):
                # Clean up the bullet/number
                clean = line.lstrip("-•* 0123456789.)")
                if clean and len(clean) > 10:
                    points.append(clean.strip())
        return points[:10]  # Top 10 points

    def research_objection_handling(self, objection_type: str) -> ResearchResult:
        """Research psychological techniques for handling a specific objection type."""
        queries = {
            "price": "psychological techniques for handling 'I can't afford it' price objections in sales, research studies on price negotiation and value reframing",
            "timing": "sales psychology research on handling 'maybe later' timing objections, urgency and scarcity principles, follow-up strategies",
            "trust": "building trust in sales conversations research, psychological principles of credibility and social proof, handling skeptical customers",
            "need": "creating desire and need in sales psychology, handling 'I don't need it' objections, research on want vs need in purchasing decisions",
            "commitment": "psychological research on handling hesitation in sales, commitment and consistency principle, reducing buyer friction"
        }

        query = queries.get(objection_type, f"sales psychology research on handling {objection_type} objections")
        context = f"This research is for training OnlyFans chatters who sell content via text messages. The objection type is '{objection_type}'."

        return self.research(query, context)

    def research_tier_selling(self, tier: str) -> ResearchResult:
        """Research selling techniques for a specific customer tier."""
        tier_contexts = {
            "new": "selling to first-time customers, building initial trust, low-commitment entry offers",
            "low": "selling to price-sensitive customers, value demonstration, upselling from small purchases",
            "medium": "selling to proven buyers, relationship building, repeat purchase psychology",
            "high": "selling to high-value customers, premium positioning, VIP treatment psychology",
            "whale": "selling to top spenders, luxury psychology, exclusivity and personalization"
        }

        context_detail = tier_contexts.get(tier.lower(), tier)
        query = f"Sales psychology research on {context_detail}. What techniques work best for this customer segment?"
        context = "This is for OnlyFans content sales via text messaging."

        return self.research(query, context)

    def research_sales_technique(self, technique: str) -> ResearchResult:
        """Research a specific sales technique."""
        query = f"Research on '{technique}' as a sales technique. Psychological basis, effectiveness studies, best practices."
        return self.research(query)


def research_all_objection_types(output_dir: Optional[Path] = None) -> Dict[str, ResearchResult]:
    """Research all objection types and save results."""
    researcher = PerplexityResearcher()
    results = {}

    objection_types = ["price", "timing", "trust", "need", "commitment"]

    for obj_type in objection_types:
        console.print(f"\n[bold]Researching {obj_type} objections...[/bold]")
        result = researcher.research_objection_handling(obj_type)
        results[obj_type] = result

        console.print(Panel(
            result.findings[:500] + "..." if len(result.findings) > 500 else result.findings,
            title=f"{obj_type.title()} Objection Research"
        ))

        # Rate limiting
        time.sleep(2)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "objection_research.json"

        data = {
            obj_type: {
                "topic": r.topic,
                "findings": r.findings,
                "key_points": r.key_points,
                "sources": r.sources,
                "timestamp": r.timestamp
            }
            for obj_type, r in results.items()
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]Research saved to {output_file}[/green]")

    return results


def research_all_tiers(output_dir: Optional[Path] = None) -> Dict[str, ResearchResult]:
    """Research selling techniques for all customer tiers."""
    researcher = PerplexityResearcher()
    results = {}

    tiers = ["new", "low", "medium", "high", "whale"]

    for tier in tiers:
        console.print(f"\n[bold]Researching {tier.upper()} tier selling...[/bold]")
        result = researcher.research_tier_selling(tier)
        results[tier] = result

        console.print(Panel(
            result.findings[:500] + "..." if len(result.findings) > 500 else result.findings,
            title=f"{tier.upper()} Tier Research"
        ))

        time.sleep(2)

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "tier_research.json"

        data = {
            tier: {
                "topic": r.topic,
                "findings": r.findings,
                "key_points": r.key_points,
                "sources": r.sources,
                "timestamp": r.timestamp
            }
            for tier, r in results.items()
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        console.print(f"\n[green]Research saved to {output_file}[/green]")

    return results


def main():
    """Run research on all topics."""
    import argparse

    parser = argparse.ArgumentParser(description="Research sales psychology using Perplexity")
    parser.add_argument("--objections", action="store_true", help="Research objection handling")
    parser.add_argument("--tiers", action="store_true", help="Research tier-specific selling")
    parser.add_argument("--topic", type=str, help="Research a custom topic")
    parser.add_argument("--output", type=str, default="data/insights/research", help="Output directory")

    args = parser.parse_args()
    output_dir = Path(args.output)

    if args.topic:
        researcher = PerplexityResearcher()
        result = researcher.research(args.topic)
        console.print(Panel(result.findings, title=f"Research: {args.topic}"))

    if args.objections or (not args.topic and not args.tiers):
        research_all_objection_types(output_dir)

    if args.tiers:
        research_all_tiers(output_dir)


if __name__ == "__main__":
    main()
