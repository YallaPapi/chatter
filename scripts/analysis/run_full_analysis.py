"""
Master Analysis Pipeline Script

Runs all analysis modules in sequence and generates complete training insights.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel

console = Console()


def run_full_pipeline(
    input_dir: str = "data/parsed_conversations",
    output_dir: str = "data/insights",
    model: str = "gpt-5.2",
    skip_ai: bool = False,
    quiet: bool = False
):
    """
    Run the complete analysis pipeline.

    Args:
        input_dir: Path to parsed conversations
        output_dir: Path for output
        model: OpenAI model for AI analysis
        skip_ai: Skip AI analysis (faster, cheaper)
        quiet: Suppress progress output
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    console.print(Panel.fit(
        "[bold cyan]CHATTER TRAINING DATA ANALYSIS PIPELINE[/bold cyan]\n\n"
        f"Input: {input_path}\n"
        f"Output: {output_path}\n"
        f"Model: {model}\n"
        f"Skip AI: {skip_ai}",
        title="Configuration"
    ))

    results = {
        "pipeline_run": datetime.now().isoformat(),
        "input_dir": str(input_path),
        "output_dir": str(output_path),
        "stages": {}
    }

    # Stage 1: Data Loading
    console.print("\n[bold cyan]=== STAGE 1: DATA LOADING ===[/bold cyan]")
    from scripts.analysis.data_loader import load_and_prepare_data, get_threads_by_tier

    threads, report = load_and_prepare_data(
        input_path,
        show_progress=not quiet,
        print_report=not quiet
    )
    threads_by_tier = get_threads_by_tier(threads)

    results["stages"]["data_loading"] = {
        "status": "complete",
        "total_threads": len(threads),
        "total_screenshots": report.total_files_loaded,
        "valid_conversations": report.valid_conversations
    }

    # Stage 2: Statistical Analysis
    console.print("\n[bold cyan]=== STAGE 2: STATISTICAL ANALYSIS ===[/bold cyan]")
    from scripts.analysis.statistical_analysis import run_statistical_analysis

    stats = run_statistical_analysis(
        parsed_dir=input_path,
        output_dir=output_path / "raw",
        show_output=not quiet
    )

    results["stages"]["statistical_analysis"] = {
        "status": "complete",
        "output_file": str(output_path / "raw" / "tier_statistics.json")
    }

    # Stage 3: Message Content Analysis
    console.print("\n[bold cyan]=== STAGE 3: MESSAGE CONTENT ANALYSIS ===[/bold cyan]")
    from scripts.analysis.message_analysis import run_message_analysis

    msg_analysis = run_message_analysis(
        parsed_dir=input_path,
        output_dir=output_path / "raw",
        show_output=not quiet
    )

    results["stages"]["message_analysis"] = {
        "status": "complete",
        "output_file": str(output_path / "raw" / "message_analysis.json")
    }

    # Stage 4: AI Pattern Analysis (optional)
    if not skip_ai:
        console.print("\n[bold cyan]=== STAGE 4: AI PATTERN ANALYSIS ===[/bold cyan]")
        from scripts.analysis.ai_pattern_analysis import run_ai_analysis

        ai_results = run_ai_analysis(
            parsed_dir=input_path,
            output_dir=output_path,
            model=model
        )

        results["stages"]["ai_analysis"] = {
            "status": "complete",
            "model": model,
            "playbooks_generated": list(ai_results.get("playbooks", {}).keys()),
            "output_file": str(output_path / "raw" / "ai_analysis.json")
        }
    else:
        console.print("\n[yellow]Skipping AI analysis (--skip-ai flag set)[/yellow]")
        results["stages"]["ai_analysis"] = {"status": "skipped"}

    # Save pipeline results
    pipeline_results_path = output_path / "pipeline_results.json"
    with open(pipeline_results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Final summary
    console.print("\n" + "=" * 60)

    ai_files = ""
    if not skip_ai:
        ai_files = (
            "  - raw/ai_analysis.json\n"
            "  - playbooks/*.md (5 tier playbooks)\n"
            "  - templates/script_templates.json\n"
        )

    console.print(Panel.fit(
        "[bold green]ANALYSIS COMPLETE![/bold green]\n\n"
        f"Total threads analyzed: {len(threads)}\n"
        f"Outputs saved to: {output_path}\n\n"
        "Generated files:\n"
        "  - raw/data_quality_report.json\n"
        "  - raw/tier_statistics.json\n"
        "  - raw/message_analysis.json\n"
        f"{ai_files}"
        "  - training_summary.md\n"
        "  - pipeline_results.json",
        title="Summary"
    ))

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run complete chatter training data analysis pipeline"
    )
    parser.add_argument(
        "--input-dir",
        default="data/parsed_conversations",
        help="Path to parsed conversations directory"
    )
    parser.add_argument(
        "--output-dir",
        default="data/insights",
        help="Path for output files"
    )
    parser.add_argument(
        "--model",
        default="gpt-5.2",
        help="OpenAI model for AI analysis (default: gpt-5.2)"
    )
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Skip AI analysis stage (faster, no API costs)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress detailed progress output"
    )

    args = parser.parse_args()

    run_full_pipeline(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        model=args.model,
        skip_ai=args.skip_ai,
        quiet=args.quiet
    )
