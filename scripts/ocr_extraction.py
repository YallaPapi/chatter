"""
OCR Extraction Pipeline for Chatter Marines Field Handbook

Extracts text from PNG screenshots using OpenAI Vision or Tesseract.
Supports batch processing, rate limiting, resumability, cost tracking, and parallel workers.
"""

import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

console = Console()


@dataclass
class OCRResult:
    """Result from OCR extraction for a single image."""
    source_image: str
    raw_text: str
    success: bool
    error: Optional[str] = None
    processing_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class OCRStats:
    """Statistics for OCR processing run."""
    total_images: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    total_cost_estimate: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "total_images": self.total_images,
            "processed": self.processed,
            "successful": self.successful,
            "failed": self.failed,
            "skipped": self.skipped,
            "success_rate": f"{(self.successful / max(self.processed, 1)) * 100:.1f}%",
            "total_cost_estimate": f"${self.total_cost_estimate:.2f}",
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time else 0
            ),
        }


class PNGDiscovery:
    """Discovers PNG files in a directory structure."""

    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path)

    def find_all_pngs(self) -> list[Path]:
        """Recursively find all PNG files."""
        if not self.root_path.exists():
            raise FileNotFoundError(f"Root path does not exist: {self.root_path}")

        pngs = list(self.root_path.rglob("*.png"))
        console.print(f"[green]Found {len(pngs)} PNG files in {self.root_path}[/green]")
        return sorted(pngs)

    def get_relative_path(self, png_path: Path) -> str:
        """Get path relative to root for consistent naming."""
        return str(png_path.relative_to(self.root_path))


class CheckpointManager:
    """Thread-safe checkpoint manager for resumable processing."""

    def __init__(self, checkpoint_file: str | Path):
        self.checkpoint_file = Path(checkpoint_file)
        self.processed_files: set[str] = set()
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Load checkpoint from disk."""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, "r") as f:
                data = json.load(f)
                self.processed_files = set(data.get("processed_files", []))
            console.print(f"[yellow]Resuming from checkpoint: {len(self.processed_files)} files already processed[/yellow]")

    def save(self) -> None:
        """Save checkpoint to disk (thread-safe)."""
        with self._lock:
            self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_file, "w") as f:
                json.dump({"processed_files": list(self.processed_files)}, f)

    def is_processed(self, file_path: str) -> bool:
        """Check if a file has already been processed."""
        with self._lock:
            return file_path in self.processed_files

    def mark_processed(self, file_path: str) -> None:
        """Mark a file as processed (thread-safe)."""
        with self._lock:
            self.processed_files.add(file_path)

    def count(self) -> int:
        """Get count of processed files."""
        with self._lock:
            return len(self.processed_files)


class OCRExtractor:
    """
    Extracts text from images using OCR.

    Supports multiple backends:
    - OpenAI Vision (gpt-4o-mini, gpt-5-mini, etc.) - DEFAULT
    - Tesseract (free, local)
    - Mock extractor (for testing)
    """

    # Estimated cost per image (OpenAI vision is cheap)
    COST_PER_IMAGE = 0.001  # ~$0.001 per image for gpt-5-mini

    def __init__(self, use_mock: bool = False, backend: str = "openai", model: str = "gpt-5-mini"):
        self.use_mock = use_mock
        self.backend = backend
        self.model = model
        self._openai_client = None

    def _get_openai_client(self):
        """Get OpenAI client."""
        if self._openai_client is None:
            import openai
            self._openai_client = openai.OpenAI()
        return self._openai_client

    def extract_text(self, image_path: Path) -> OCRResult:
        """Extract text from a single image."""
        start_time = time.time()

        if self.use_mock:
            return self._mock_extract(image_path, start_time)

        if self.backend == "openai":
            return self._openai_extract(image_path, start_time)
        elif self.backend == "tesseract":
            return self._tesseract_extract(image_path, start_time)
        else:
            return self._mock_extract(image_path, start_time)

    def _mock_extract(self, image_path: Path, start_time: float) -> OCRResult:
        """Mock extraction for testing."""
        time.sleep(0.05)
        return OCRResult(
            source_image=str(image_path),
            raw_text=f"[MOCK OCR] Text extracted from {image_path.name}",
            success=True,
            processing_time_ms=(time.time() - start_time) * 1000,
        )

    def _openai_extract(self, image_path: Path, start_time: float) -> OCRResult:
        """Extract text using OpenAI Vision API."""
        try:
            import base64

            client = self._get_openai_client()

            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Determine mime type
            suffix = image_path.suffix.lower()
            mime_type = "image/png" if suffix == ".png" else "image/jpeg"

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract ALL text from this chat screenshot. Include timestamps, usernames, message content, and any metadata visible. Return ONLY the extracted text, no commentary."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_completion_tokens=4000
            )

            raw_text = response.choices[0].message.content

            return OCRResult(
                source_image=str(image_path),
                raw_text=raw_text.strip(),
                success=True,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return OCRResult(
                source_image=str(image_path),
                raw_text="",
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )

    def _tesseract_extract(self, image_path: Path, start_time: float) -> OCRResult:
        """Extract text using Tesseract OCR (free, local)."""
        try:
            import pytesseract
            from PIL import Image

            img = Image.open(image_path)
            raw_text = pytesseract.image_to_string(img)

            return OCRResult(
                source_image=str(image_path),
                raw_text=raw_text.strip(),
                success=True,
                processing_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            return OCRResult(
                source_image=str(image_path),
                raw_text="",
                success=False,
                error=str(e),
                processing_time_ms=(time.time() - start_time) * 1000,
            )


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_minute: int = 1800):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0.0

    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call_time = time.time()


class OCRPipeline:
    """Main OCR extraction pipeline with parallel worker support."""

    def __init__(
        self,
        input_dir: str | Path,
        output_dir: str | Path,
        batch_size: int = 50,
        rate_limit: int = 1800,
        use_mock: bool = False,
        backend: str = "openai",
        model: str = "gpt-5-mini",
        workers: int = 10,
    ):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.batch_size = batch_size
        self.use_mock = use_mock
        self.workers = workers
        self.backend = backend
        self.model = model

        # Initialize components
        self.discovery = PNGDiscovery(self.input_dir)
        self.rate_limiter = RateLimiter(calls_per_minute=rate_limit)
        self.checkpoint = CheckpointManager(self.output_dir / ".checkpoint.json")
        self.stats = OCRStats()
        self._stats_lock = threading.Lock()

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _create_extractor(self) -> OCRExtractor:
        """Create a new extractor instance (each thread gets its own)."""
        return OCRExtractor(use_mock=self.use_mock, backend=self.backend, model=self.model)

    def _process_single(self, png_path: Path, extractor: OCRExtractor) -> tuple[Path, OCRResult]:
        """Process a single image (called by worker threads)."""
        result = extractor.extract_text(png_path)
        return png_path, result

    def _update_stats(self, result: OCRResult, png_path: Path) -> None:
        """Thread-safe stats update."""
        with self._stats_lock:
            self.stats.processed += 1
            if result.success:
                self.stats.successful += 1
                self.stats.total_cost_estimate += OCRExtractor.COST_PER_IMAGE
            else:
                self.stats.failed += 1

    def run(self, limit: Optional[int] = None) -> OCRStats:
        """
        Run the OCR extraction pipeline with parallel workers.

        Args:
            limit: Optional limit on number of images to process (for testing)

        Returns:
            OCRStats with processing statistics
        """
        self.stats.start_time = datetime.now()

        # Discover all PNG files
        all_pngs = self.discovery.find_all_pngs()
        self.stats.total_images = len(all_pngs)

        # Filter out already processed files
        to_process = [
            p for p in all_pngs
            if not self.checkpoint.is_processed(self.discovery.get_relative_path(p))
        ]

        if limit:
            to_process = to_process[:limit]

        self.stats.skipped = len(all_pngs) - len(to_process)

        if not to_process:
            console.print("[yellow]No new images to process.[/yellow]")
            return self.stats

        console.print(f"[blue]Processing {len(to_process)} images with {self.workers} workers...[/blue]")

        # Process with thread pool
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting text...", total=len(to_process))

            # Create thread-local extractors
            thread_local = threading.local()

            def get_extractor():
                if not hasattr(thread_local, 'extractor'):
                    thread_local.extractor = self._create_extractor()
                return thread_local.extractor

            def process_image(png_path: Path) -> tuple[Path, OCRResult]:
                extractor = get_extractor()
                return self._process_single(png_path, extractor)

            with ThreadPoolExecutor(max_workers=self.workers) as executor:
                # Submit all tasks
                futures = {executor.submit(process_image, p): p for p in to_process}
                completed = 0

                for future in as_completed(futures):
                    png_path, result = future.result()

                    # Save result
                    self._save_result(png_path, result)

                    # Update stats
                    self._update_stats(result, png_path)

                    if not result.success:
                        console.print(f"[red]Failed: {png_path.name} - {result.error}[/red]")

                    # Update checkpoint
                    self.checkpoint.mark_processed(self.discovery.get_relative_path(png_path))

                    completed += 1
                    progress.update(task, completed=completed)

                    # Save checkpoint periodically
                    if completed % self.batch_size == 0:
                        self.checkpoint.save()

        # Final checkpoint save
        self.checkpoint.save()
        self.stats.end_time = datetime.now()

        # Print summary
        self._print_summary()

        return self.stats

    def _save_result(self, png_path: Path, result: OCRResult) -> None:
        """Save OCR result to JSON file."""
        relative_path = self.discovery.get_relative_path(png_path)
        output_path = self.output_dir / f"{relative_path}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({
                "source_image": relative_path,
                "raw_text": result.raw_text,
                "success": result.success,
                "error": result.error,
                "processing_time_ms": result.processing_time_ms,
                "timestamp": result.timestamp,
            }, f, indent=2, ensure_ascii=False)

    def _print_summary(self) -> None:
        """Print processing summary."""
        stats_dict = self.stats.to_dict()
        console.print("\n[bold green]OCR Extraction Complete![/bold green]")
        console.print(f"  Total images:     {stats_dict['total_images']}")
        console.print(f"  Processed:        {stats_dict['processed']}")
        console.print(f"  Successful:       {stats_dict['successful']}")
        console.print(f"  Failed:           {stats_dict['failed']}")
        console.print(f"  Skipped:          {stats_dict['skipped']}")
        console.print(f"  Success rate:     {stats_dict['success_rate']}")
        console.print(f"  Est. cost:        {stats_dict['total_cost_estimate']}")
        console.print(f"  Duration:         {stats_dict['duration_seconds']:.1f}s")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract text from PNG screenshots using OCR")
    parser.add_argument(
        "--input-dir",
        default="Chatter Marines Field Handbook",
        help="Input directory containing PNG files",
    )
    parser.add_argument(
        "--output-dir",
        default="data/ocr_output",
        help="Output directory for JSON results",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Number of images to process before saving checkpoint",
    )
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=500,
        help="Maximum API calls per minute",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of images to process (for testing)",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock extractor (no API calls)",
    )
    parser.add_argument(
        "--backend",
        default="openai",
        choices=["openai", "tesseract"],
        help="OCR backend to use (default: openai)",
    )
    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="Model to use for OpenAI backend (default: gpt-5-mini)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
        help="Number of parallel workers (default: 10)",
    )

    args = parser.parse_args()

    pipeline = OCRPipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        rate_limit=args.rate_limit,
        use_mock=args.mock,
        backend=args.backend,
        model=args.model,
        workers=args.workers,
    )

    pipeline.run(limit=args.limit)


if __name__ == "__main__":
    main()
