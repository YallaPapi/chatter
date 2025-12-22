"""
Conversation Parser - Extracts structured data from OCR output using LLM.

Parses raw OCR text into structured conversations with:
- Individual messages (role, text, timestamp)
- Subscriber metadata (total spent, tips, buy rate)
- Conversation outcomes (sale made, amount, technique)
"""

import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

console = Console()

PARSE_PROMPT = """Analyze this chat screenshot text and extract structured data.

RAW TEXT:
{raw_text}

Extract the following JSON structure:
{{
  "messages": [
    {{"role": "creator" or "subscriber", "text": "message content", "timestamp": "time if visible"}}
  ],
  "subscriber_stats": {{
    "total_spent": number or null,
    "tips": number or null,
    "messages_spent": number or null,
    "buy_rate": "percentage string" or null,
    "subscription_status": "free/paying/expired" or null,
    "subscription_price": number or null,
    "highest_purchase": number or null,
    "last_paid": "date string" or null,
    "renew": "on/off" or null
  }},
  "outcome": {{
    "sale_in_screenshot": true/false,
    "sale_amount": number or null,
    "tip_received": true/false,
    "tip_amount": number or null,
    "ppv_sent": true/false,
    "ppv_price": number or null,
    "technique_observed": "description of sales technique if visible" or null
  }},
  "context": {{
    "conversation_stage": "opening/building_rapport/qualifying/pitching/closing/post_sale",
    "subscriber_mood": "engaged/hesitant/eager/cold/flirty",
    "creator_approach": "teasing/direct/playful/romantic/transactional"
  }}
}}

Rules:
- "creator" = the OnlyFans model/chatter (usually sends PPVs, asks for tips)
- "subscriber" = the fan/customer (usually tips, buys content)
- Extract ALL messages visible in order
- Parse dollar amounts as numbers (e.g., "$60" -> 60)
- If text is empty or unreadable, return {{"empty": true}}
- Return ONLY valid JSON, no explanation"""


@dataclass
class ParseResult:
    """Result from parsing a single OCR file."""
    source_file: str
    parsed_data: dict
    success: bool
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ParseStats:
    """Statistics for parsing run."""
    total_files: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    empty: int = 0
    total_cost_estimate: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "total_files": self.total_files,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "empty": self.empty,
            "success_rate": f"{(self.successful / max(self.processed, 1)) * 100:.1f}%",
            "total_cost_estimate": f"${self.total_cost_estimate:.2f}",
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time else 0
            ),
        }


class CheckpointManager:
    """Thread-safe checkpoint manager for resumable processing."""

    def __init__(self, checkpoint_file: str | Path):
        self.checkpoint_file = Path(checkpoint_file)
        self.processed_files: set[str] = set()
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)
                self.processed_files = set(data.get("processed_files", []))
            console.print(f"[yellow]Resuming from checkpoint: {len(self.processed_files)} files already processed[/yellow]")

    def save(self) -> None:
        with self._lock:
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_file, "w") as f:
                json.dump({"processed_files": list(self.processed_files)}, f)

    def is_processed(self, file_path: str) -> bool:
        with self._lock:
            return file_path in self.processed_files

    def mark_processed(self, file_path: str) -> None:
        with self._lock:
            self.processed_files.add(file_path)

    def count(self) -> int:
        with self._lock:
            return len(self.processed_files)


class ConversationParser:
    """Parses OCR output using LLM."""

    COST_PER_CALL = 0.0005  # Estimate for gpt-5-mini

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI()
        return self._client

    def parse(self, ocr_data: dict) -> ParseResult:
        """Parse OCR data into structured conversation."""
        start_time = time.time()
        source_file = ocr_data.get("source_image", "unknown")
        raw_text = ocr_data.get("raw_text", "")

        # Skip empty OCR results
        if not raw_text or not raw_text.strip():
            return ParseResult(
                source_file=source_file,
                parsed_data={"empty": True},
                success=True,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        try:
            client = self._get_client()

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a JSON extraction assistant. Always respond with valid JSON only, no markdown or explanation."
                    },
                    {
                        "role": "user",
                        "content": PARSE_PROMPT.format(raw_text=raw_text)
                    }
                ],
                max_completion_tokens=2000,
            )

            result_text = response.choices[0].message.content.strip()

            # Try to extract JSON from response (handle markdown code blocks)
            if result_text.startswith("```"):
                # Extract from code block
                lines = result_text.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_block = not in_block
                        continue
                    if in_block:
                        json_lines.append(line)
                result_text = "\n".join(json_lines)

            parsed_data = json.loads(result_text)

            return ParseResult(
                source_file=source_file,
                parsed_data=parsed_data,
                success=True,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return ParseResult(
                source_file=source_file,
                parsed_data={},
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )


class ParsePipeline:
    """Main parsing pipeline with parallel workers."""

    def __init__(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        batch_size: int = 50,
        workers: int = 10,
        model: str = "gpt-4o-mini",
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.workers = workers
        self.model = model

        self.checkpoint = CheckpointManager(self.output_dir / ".parse_checkpoint.json")
        self.stats = ParseStats()
        self._stats_lock = threading.Lock()

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _find_ocr_files(self) -> list[Path]:
        """Find all OCR JSON files."""
        files = list(self.input_dir.rglob("*.json"))
        # Exclude checkpoint files
        files = [f for f in files if not f.name.startswith(".")]
        return sorted(files)

    def _get_relative_path(self, file_path: Path) -> str:
        return str(file_path.relative_to(self.input_dir))

    def _create_parser(self) -> ConversationParser:
        return ConversationParser(model=self.model)

    def _update_stats(self, result: ParseResult) -> None:
        with self._stats_lock:
            self.stats.processed += 1
            if result.success:
                self.stats.successful += 1
                self.stats.total_cost_estimate += ConversationParser.COST_PER_CALL
                if result.parsed_data.get("empty"):
                    self.stats.empty += 1
            else:
                self.stats.failed += 1

    def _save_result(self, ocr_file: Path, result: ParseResult) -> None:
        """Save parsed result to JSON file."""
        relative_path = self._get_relative_path(ocr_file)
        # Change extension from .png.json to .parsed.json
        output_path = self.output_dir / relative_path.replace(".png.json", ".parsed.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "source_file": result.source_file,
                "parsed_data": result.parsed_data,
                "success": result.success,
                "error": result.error,
                "processing_time_ms": result.processing_time_ms,
                "timestamp": result.timestamp,
            }, f, indent=2, ensure_ascii=False)

    def run(self, limit: Optional[int] = None) -> ParseStats:
        """Run the parsing pipeline."""
        self.stats.start_time = datetime.now()

        # Find all OCR files
        all_files = self._find_ocr_files()
        self.stats.total_files = len(all_files)
        console.print(f"[green]Found {len(all_files)} OCR files[/green]")

        # Filter already processed
        to_process = [
            f for f in all_files
            if not self.checkpoint.is_processed(self._get_relative_path(f))
        ]

        if limit:
            to_process = to_process[:limit]

        self.stats.skipped = len(all_files) - len(to_process)

        if not to_process:
            console.print("[yellow]No new files to process.[/yellow]")
            return self.stats

        console.print(f"[blue]Processing {len(to_process)} files with {self.workers} workers...[/blue]")

        # Process with thread pool
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Parsing conversations...", total=len(to_process))

            thread_local = threading.local()

            def get_parser():
                if not hasattr(thread_local, 'parser'):
                    thread_local.parser = self._create_parser()
                return thread_local.parser

            def process_file(ocr_file: Path) -> tuple[Path, ParseResult]:
                parser = get_parser()
                with open(ocr_file, "r", encoding="utf-8") as f:
                    ocr_data = json.load(f)
                result = parser.parse(ocr_data)
                return ocr_file, result

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                futures = {executor.submit(process_file, f): f for f in to_process}
                completed = 0

                for future in as_completed(futures):
                    ocr_file, result = future.result()

                    self._save_result(ocr_file, result)
                    self._update_stats(result)

                    if not result.success:
                        console.print(f"[red]Failed: {ocr_file.name} - {result.error}[/red]")

                    self.checkpoint.mark_processed(self._get_relative_path(ocr_file))

                    completed += 1
                    progress.update(task, completed=completed)

                    if completed % self.batch_size == 0:
                        self.checkpoint.save()

        self.checkpoint.save()
        self.stats.end_time = datetime.now()
        self._print_summary()

        return self.stats

    def _print_summary(self) -> None:
        stats_dict = self.stats.to_dict()
        console.print("\n[bold green]Parsing Complete![/bold green]")
        console.print(f"  Total files:      {stats_dict['total_files']}")
        console.print(f"  Processed:        {stats_dict['processed']}")
        console.print(f"  Successful:       {stats_dict['successful']}")
        console.print(f"  Empty (no text):  {stats_dict['empty']}")
        console.print(f"  Failed:           {stats_dict['failed']}")
        console.print(f"  Skipped:          {stats_dict['skipped']}")
        console.print(f"  Success rate:     {stats_dict['success_rate']}")
        console.print(f"  Est. cost:        {stats_dict['total_cost_estimate']}")
        console.print(f"  Duration:         {stats_dict['duration_seconds']:.1f}s")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Parse OCR output into structured conversations")
    parser.add_argument(
        "--input-dir",
        default="data/ocr_output",
        help="Directory containing OCR JSON files",
    )
    parser.add_argument(
        "--output-dir",
        default="data/parsed_conversations",
        help="Output directory for parsed results",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Checkpoint save frequency",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel workers",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="Model to use for parsing",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of files to process",
    )

    args = parser.parse_args()

    pipeline = ParsePipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        workers=args.workers,
        model=args.model,
    )

    pipeline.run(limit=args.limit)


if __name__ == "__main__":
    main()
