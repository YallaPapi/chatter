"""
Handbook Content Parser

Parses the Chatter Marines Field Handbook markdown files into structured
training content for the knowledge base.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()


@dataclass
class HandbookSection:
    """A section of the handbook."""
    id: str
    title: str
    content: str
    category: str
    parent_category: Optional[str] = None
    source_file: str = ""
    word_count: int = 0
    has_examples: bool = False
    key_points: list[str] = field(default_factory=list)


@dataclass
class GambitTemplate:
    """A structured gambit conversation template."""
    id: str
    name: str
    category: str  # transitional, emotional_connection, captain_save_a_ho
    phases: dict[str, str] = field(default_factory=dict)  # phase_name -> text
    source_file: str = ""
    description: Optional[str] = None
    tags: list[str] = field(default_factory=list)


class MarkdownParser:
    """Parses markdown files into structured content."""

    # Standard gambit phase names
    GAMBIT_PHASES = [
        "opening question",
        "opening",
        "rooting",
        "request for input",
        "hypnotic afterthought",
        "hypnosis",
        "seductive tease",
        "tease",
    ]

    def parse_markdown(self, file_path: Path) -> tuple[str, str, list[str]]:
        """
        Parse a markdown file and extract title, content, and key points.

        Returns:
            (title, content, key_points)
        """
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract title from first H1
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem

        # Clean content
        # Remove image links
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        # Remove regular links but keep text
        content = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', content)

        # Extract key points (bullet points and numbered lists)
        key_points = []
        for match in re.finditer(r'^[\s]*[-*\d.]+\s+(.+)$', content, re.MULTILINE):
            point = match.group(1).strip()
            if len(point) > 10 and len(point) < 200:  # Reasonable length
                key_points.append(point)

        return title, content.strip(), key_points[:10]  # Limit to 10 key points

    def is_gambit_file(self, content: str) -> bool:
        """Check if the content looks like a gambit template."""
        content_lower = content.lower()
        phase_count = sum(1 for phase in self.GAMBIT_PHASES if phase in content_lower)
        return phase_count >= 2  # At least 2 gambit phases present

    def parse_gambit(self, file_path: Path, content: str, title: str) -> Optional[GambitTemplate]:
        """Parse a gambit file into structured phases."""
        phases = {}

        # Try to extract each phase
        lines = content.split('\n')
        current_phase = None
        current_text = []

        for line in lines:
            line_lower = line.lower().strip()

            # Check if this line starts a new phase
            found_phase = None
            for phase in self.GAMBIT_PHASES:
                if phase in line_lower and ('*' in line or '#' in line or line_lower.startswith(phase)):
                    found_phase = phase
                    break

            if found_phase:
                # Save previous phase
                if current_phase and current_text:
                    phases[current_phase] = '\n'.join(current_text).strip()
                current_phase = found_phase
                current_text = []
            elif current_phase:
                # Clean the line and add to current phase
                cleaned = line.strip()
                cleaned = re.sub(r'^[-*]+\s*', '', cleaned)  # Remove bullet points
                cleaned = re.sub(r'^\*\*\*?', '', cleaned)  # Remove bold markers
                cleaned = re.sub(r'\*\*\*?$', '', cleaned)
                cleaned = cleaned.strip()
                if cleaned and not cleaned.startswith('#'):
                    current_text.append(cleaned)

        # Don't forget last phase
        if current_phase and current_text:
            phases[current_phase] = '\n'.join(current_text).strip()

        if not phases:
            return None

        # Normalize phase names
        normalized_phases = {}
        phase_mapping = {
            "opening question": "opening",
            "opening": "opening",
            "rooting": "rooting",
            "request for input": "request_for_input",
            "hypnotic afterthought": "hypnosis",
            "hypnosis": "hypnosis",
            "seductive tease": "tease",
            "tease": "tease",
        }
        for phase, text in phases.items():
            normalized = phase_mapping.get(phase, phase.replace(" ", "_"))
            normalized_phases[normalized] = text

        # Determine category from path
        category = "general"
        path_str = str(file_path).lower()
        if "transitional" in path_str:
            category = "transitional"
        elif "captain" in path_str or "save" in path_str:
            category = "captain_save_a_ho"
        elif "emotional" in path_str:
            category = "emotional_connection"

        # Generate ID
        gambit_id = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')

        return GambitTemplate(
            id=gambit_id,
            name=title,
            category=category,
            phases=normalized_phases,
            source_file=str(file_path),
            tags=[category],
        )


class HandbookParser:
    """Main handbook parser that processes all markdown files."""

    # Category mapping based on folder structure
    CATEGORY_MAPPING = {
        "mindset": "mindset",
        "opening": "opening",
        "qualifying": "qualifying",
        "commonalities": "qualifying",
        "fluff": "qualifying",
        "transitioning": "transitioning",
        "selling": "selling",
        "gambits": "gambits",
        "example conversations": "examples",
        "ideas and tactics": "tactics",
    }

    def __init__(self, handbook_dir: str | Path):
        self.handbook_dir = Path(handbook_dir)
        self.markdown_parser = MarkdownParser()

    def get_category(self, file_path: Path) -> tuple[str, Optional[str]]:
        """Determine category and parent category from file path."""
        relative = file_path.relative_to(self.handbook_dir)
        parts = [p.lower() for p in relative.parts]

        category = "general"
        parent_category = None

        for part in parts:
            for key, cat in self.CATEGORY_MAPPING.items():
                if key in part:
                    if category != "general":
                        parent_category = category
                    category = cat
                    break

        return category, parent_category

    def parse_all(self) -> tuple[list[HandbookSection], list[GambitTemplate]]:
        """Parse all markdown files in the handbook directory."""
        sections = []
        gambits = []

        # Find all markdown files
        md_files = list(self.handbook_dir.rglob("*.md"))
        console.print(f"[blue]Found {len(md_files)} markdown files[/blue]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Parsing handbook...", total=len(md_files))

            for md_file in md_files:
                try:
                    title, content, key_points = self.markdown_parser.parse_markdown(md_file)
                    category, parent_category = self.get_category(md_file)

                    # Check if it's a gambit
                    if self.markdown_parser.is_gambit_file(content):
                        gambit = self.markdown_parser.parse_gambit(md_file, content, title)
                        if gambit:
                            gambits.append(gambit)

                    # Always create a section entry
                    section_id = re.sub(r'[^a-z0-9]+', '_', title.lower()).strip('_')
                    section = HandbookSection(
                        id=section_id,
                        title=title,
                        content=content,
                        category=category,
                        parent_category=parent_category,
                        source_file=str(md_file),
                        word_count=len(content.split()),
                        has_examples="example" in content.lower(),
                        key_points=key_points,
                    )
                    sections.append(section)

                except Exception as e:
                    console.print(f"[red]Error parsing {md_file}: {e}[/red]")

                progress.update(task, advance=1)

        return sections, gambits

    def to_dict(self, section: HandbookSection) -> dict:
        """Convert section to dictionary for JSON serialization."""
        return {
            "id": section.id,
            "title": section.title,
            "content": section.content,
            "category": section.category,
            "parent_category": section.parent_category,
            "source_file": section.source_file,
            "word_count": section.word_count,
            "has_examples": section.has_examples,
            "key_points": section.key_points,
        }

    def gambit_to_dict(self, gambit: GambitTemplate) -> dict:
        """Convert gambit to dictionary for JSON serialization."""
        return {
            "id": gambit.id,
            "name": gambit.name,
            "category": gambit.category,
            "phases": gambit.phases,
            "source_file": gambit.source_file,
            "description": gambit.description,
            "tags": gambit.tags,
        }


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse handbook markdown files")
    parser.add_argument(
        "--handbook-dir",
        default="Chatter Marines Field Handbook",
        help="Directory containing handbook markdown files",
    )
    parser.add_argument(
        "--output-dir",
        default="data/knowledge_base",
        help="Output directory for parsed content",
    )

    args = parser.parse_args()

    # Parse handbook
    handbook_parser = HandbookParser(args.handbook_dir)
    sections, gambits = handbook_parser.parse_all()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save sections
    sections_data = [handbook_parser.to_dict(s) for s in sections]
    with open(output_dir / "handbook_sections.json", "w", encoding="utf-8") as f:
        json.dump(sections_data, f, indent=2, ensure_ascii=False)

    # Save gambits
    gambits_data = [handbook_parser.gambit_to_dict(g) for g in gambits]
    with open(output_dir / "gambits.json", "w", encoding="utf-8") as f:
        json.dump(gambits_data, f, indent=2, ensure_ascii=False)

    # Print summary
    console.print("\n[bold green]Handbook Parsing Complete![/bold green]")
    console.print(f"  Total sections:   {len(sections)}")
    console.print(f"  Total gambits:    {len(gambits)}")

    # Category breakdown
    categories = {}
    for section in sections:
        categories[section.category] = categories.get(section.category, 0) + 1

    console.print("\n  [bold]Sections by category:[/bold]")
    for cat, count in sorted(categories.items()):
        console.print(f"    {cat}: {count}")

    # Gambit breakdown
    gambit_categories = {}
    for gambit in gambits:
        gambit_categories[gambit.category] = gambit_categories.get(gambit.category, 0) + 1

    console.print("\n  [bold]Gambits by category:[/bold]")
    for cat, count in sorted(gambit_categories.items()):
        console.print(f"    {cat}: {count}")


if __name__ == "__main__":
    main()
