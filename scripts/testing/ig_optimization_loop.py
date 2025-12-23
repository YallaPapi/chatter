# -*- coding: utf-8 -*-
"""
IG Chatbot Optimization Loop

Runs large-scale automated testing with AI-powered analysis and prompt adjustment.
Goal: Run 5000+ tests, analyze patterns, auto-adjust prompts until quality targets met.

Architecture:
1. Batch Test - Run N conversations across all personas
2. Aggregate - Collect patterns across all tests
3. Meta-Analyze - AI identifies systematic issues
4. Adjust - AI modifies prompts/examples
5. Repeat until target score or max iterations
"""

import os
import json
import time
import random
import concurrent.futures
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from openai import OpenAI

# Local imports
from ig_auto_tester import (
    FanSimulator,
    ConversationAnalyzer,
    TestResult,
    FAN_PERSONAS,
    TEST_DIR,
)
from ig_chatbot import IGChatbot, ChatbotConfig
from ig_prompt_builder import PromptBuilder


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class OptimizationConfig:
    """Configuration for the optimization loop"""
    # Test settings
    tests_per_batch: int = 50  # Conversations per batch
    max_messages_per_test: int = 50  # MAX messages - conversation can end naturally before this
    max_iterations: int = 100  # Max optimization cycles
    target_score: float = 8.5  # Stop when avg score hits this

    # Parallel execution
    max_workers: int = 5  # Concurrent test conversations

    # Model settings
    chatbot_model: str = "grok-4-1-fast-non-reasoning"  # Latest fast model
    analyzer_model: str = "grok-4-1-fast-non-reasoning"  # Same for analysis
    optimizer_model: str = "grok-4"  # Full model for prompt writing

    # API
    api_key: Optional[str] = None
    api_base: str = "https://api.x.ai/v1"

    # Output
    output_dir: Path = field(default_factory=lambda: TEST_DIR / "optimization_runs")

    def __post_init__(self):
        if not self.api_key:
            self.api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        self.output_dir.mkdir(parents=True, exist_ok=True)


# =============================================================================
# BATCH TEST RUNNER
# =============================================================================

class BatchTestRunner:
    """Runs batches of test conversations"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.analyzer = ConversationAnalyzer(api_key=config.api_key)

    def run_single_test(self, persona_id: str, test_id: str) -> Dict[str, Any]:
        """Run a single test conversation and return results"""
        try:
            # Create fresh chatbot for each test
            chatbot_config = ChatbotConfig(
                model=self.config.chatbot_model,
                api_key=self.config.api_key,
            )
            chatbot = IGChatbot(config=chatbot_config)
            chatbot.start_conversation()

            # Create fan simulator
            fan = FanSimulator(persona_id, api_key=self.config.api_key)

            conversation = []

            # Run conversation up to max
            for i in range(self.config.max_messages_per_test):
                # Fan message
                her_last = conversation[-1]["content"] if conversation and conversation[-1]["role"] == "her" else None
                fan_msg = fan.generate_message(conversation, her_last)
                conversation.append({"role": "fan", "content": fan_msg})

                # Bot response
                responses = chatbot.respond(fan_msg)
                her_response = "||".join([r.text for r in responses if r.text])
                for r in responses:
                    if r.has_image():
                        her_response += f" [IMG:{r.image}]"
                conversation.append({"role": "her", "content": her_response})

            # Analyze
            analysis = self.analyzer.analyze(conversation, FAN_PERSONAS[persona_id]['name'])

            return {
                "test_id": test_id,
                "persona": persona_id,
                "conversation": conversation,
                "analysis": analysis,
                "success": True,
                "error": None,
            }

        except Exception as e:
            return {
                "test_id": test_id,
                "persona": persona_id,
                "conversation": [],
                "analysis": {},
                "success": False,
                "error": str(e),
            }

    def run_batch(self, batch_num: int) -> List[Dict[str, Any]]:
        """Run a batch of tests across all personas"""
        results = []
        personas = list(FAN_PERSONAS.keys())

        # Create test tasks
        tasks = []
        tests_per_persona = self.config.tests_per_batch // len(personas)

        for persona_id in personas:
            for i in range(tests_per_persona):
                test_id = f"batch{batch_num}_{persona_id}_{i}"
                tasks.append((persona_id, test_id))

        # Run in parallel
        print(f"\nRunning batch {batch_num}: {len(tasks)} tests...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            futures = {
                executor.submit(self.run_single_test, persona_id, test_id): (persona_id, test_id)
                for persona_id, test_id in tasks
            }

            completed = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                completed += 1
                if completed % 10 == 0:
                    print(f"  Completed {completed}/{len(tasks)} tests...")

        return results


# =============================================================================
# RESULTS AGGREGATOR
# =============================================================================

@dataclass
class AggregatedResults:
    """Aggregated results from a batch of tests"""
    batch_num: int
    total_tests: int
    successful_tests: int
    failed_tests: int

    # Score aggregates (goal-focused)
    avg_overall_score: float
    avg_human: float  # Does she pass as real?
    avg_charm: float  # Is she likeable?
    avg_goal: float   # Did it move toward subscription?

    # Breakdown by persona
    scores_by_persona: Dict[str, float]

    # Would subscribe count
    would_subscribe_count: int
    would_subscribe_rate: float

    # Common issues
    all_problems: List[str]
    problem_counts: Dict[str, int]
    all_fixes: List[str]
    fix_counts: Dict[str, int]

    # Verdicts
    verdict_counts: Dict[str, int]

    # Raw results for reference
    raw_results: List[Dict[str, Any]] = field(default_factory=list)


class ResultsAggregator:
    """Aggregates results from batch tests"""

    def aggregate(self, results: List[Dict[str, Any]], batch_num: int) -> AggregatedResults:
        """Aggregate results into summary statistics"""
        successful = [r for r in results if r["success"] and "error" not in r.get("analysis", {})]
        failed = [r for r in results if not r["success"] or "error" in r.get("analysis", {})]

        # Score extraction helper
        def get_score(analysis: Dict, key: str) -> float:
            if key == "overall":
                return analysis.get("overall_score", 0)
            return analysis.get(key, {}).get("score", 0) if isinstance(analysis.get(key), dict) else 0

        # Calculate averages (goal-focused metrics)
        if successful:
            avg_overall = sum(get_score(r["analysis"], "overall") for r in successful) / len(successful)
            avg_human = sum(get_score(r["analysis"], "human") for r in successful) / len(successful)
            avg_charm = sum(get_score(r["analysis"], "charm") for r in successful) / len(successful)
            avg_goal = sum(get_score(r["analysis"], "goal") for r in successful) / len(successful)
            would_subscribe_count = sum(1 for r in successful if r["analysis"].get("would_subscribe", False))
        else:
            avg_overall = avg_human = avg_charm = avg_goal = 0
            would_subscribe_count = 0

        # Scores by persona
        scores_by_persona = {}
        for persona_id in FAN_PERSONAS.keys():
            persona_results = [r for r in successful if r["persona"] == persona_id]
            if persona_results:
                scores_by_persona[persona_id] = sum(get_score(r["analysis"], "overall") for r in persona_results) / len(persona_results)
            else:
                scores_by_persona[persona_id] = 0

        # Collect problems and fixes
        all_problems = []
        all_fixes = []
        verdict_counts = {"PASS": 0, "FAIL": 0, "NEEDS_WORK": 0}

        for r in successful:
            analysis = r["analysis"]
            all_problems.extend(analysis.get("problems", []))
            all_fixes.extend(analysis.get("fixes", []))
            verdict = analysis.get("verdict", "NEEDS_WORK")
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

        # Count occurrences
        problem_counts = {}
        for prob in all_problems:
            prob_lower = prob.lower()[:50]
            problem_counts[prob_lower] = problem_counts.get(prob_lower, 0) + 1

        fix_counts = {}
        for fix in all_fixes:
            fix_lower = fix.lower()[:50]
            fix_counts[fix_lower] = fix_counts.get(fix_lower, 0) + 1

        would_subscribe_rate = would_subscribe_count / len(successful) if successful else 0

        return AggregatedResults(
            batch_num=batch_num,
            total_tests=len(results),
            successful_tests=len(successful),
            failed_tests=len(failed),
            avg_overall_score=avg_overall,
            avg_human=avg_human,
            avg_charm=avg_charm,
            avg_goal=avg_goal,
            scores_by_persona=scores_by_persona,
            would_subscribe_count=would_subscribe_count,
            would_subscribe_rate=would_subscribe_rate,
            all_problems=all_problems,
            problem_counts=dict(sorted(problem_counts.items(), key=lambda x: -x[1])[:20]),
            all_fixes=all_fixes,
            fix_counts=dict(sorted(fix_counts.items(), key=lambda x: -x[1])[:20]),
            verdict_counts=verdict_counts,
            raw_results=results,
        )


# =============================================================================
# META ANALYZER - AI analyzes patterns across all tests
# =============================================================================

class MetaAnalyzer:
    """AI-powered analysis of aggregated test results"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.api_base)

    def analyze_patterns(self, aggregated: AggregatedResults) -> Dict[str, Any]:
        """Analyze patterns across all test results"""

        # Build analysis prompt
        prompt = f"""Analyze these aggregated test results from {aggregated.total_tests} chatbot conversations.

THE GOAL: Sound like a real woman and charm fans into subscribing to OnlyFans.

RESULTS:
- Overall Score: {aggregated.avg_overall_score:.2f}/10
- Human (passes as real): {aggregated.avg_human:.2f}/10
- Charm (likeable/engaging): {aggregated.avg_charm:.2f}/10
- Goal (moves toward subscription): {aggregated.avg_goal:.2f}/10
- Would Subscribe Rate: {aggregated.would_subscribe_rate:.1%} ({aggregated.would_subscribe_count}/{aggregated.successful_tests})

SCORES BY FAN TYPE:
{json.dumps(aggregated.scores_by_persona, indent=2)}

VERDICT BREAKDOWN:
{json.dumps(aggregated.verdict_counts, indent=2)}

MOST COMMON PROBLEMS:
{json.dumps(aggregated.problem_counts, indent=2)}

MOST SUGGESTED FIXES:
{json.dumps(aggregated.fix_counts, indent=2)}

What's stopping this bot from achieving the goal? Identify the top issues and specific fixes.

Respond in JSON:
{{
    "top_issues": [
        {{"problem": "...", "evidence": "...", "fix": "..."}},
        {{"problem": "...", "evidence": "...", "fix": "..."}},
        {{"problem": "...", "evidence": "...", "fix": "..."}}
    ],
    "worst_persona": {{"persona": "...", "score": X, "why": "..."}},
    "best_persona": {{"persona": "...", "score": X, "why": "..."}},
    "prompt_changes": ["Specific change 1", "Specific change 2"],
    "why_not_subscribing": "Main reason fans wouldn't subscribe..."
}}"""

        response = self.client.chat.completions.create(
            model=self.config.optimizer_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3,
        )

        # Parse JSON response
        content = response.choices[0].message.content
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass

        return {"error": "Failed to parse analysis", "raw": content}


# =============================================================================
# PROMPT ADJUSTER - AI modifies prompts based on analysis
# =============================================================================

class PromptAdjuster:
    """AI-powered prompt adjustment - actually rewrites prompt sections"""

    def __init__(self, config: OptimizationConfig):
        self.config = config
        self.client = OpenAI(api_key=config.api_key, base_url=config.api_base)

        # Paths to prompt files
        self.prompt_builder_path = Path(__file__).parent / "ig_prompt_builder.py"
        self.conversation_data_path = Path(__file__).parent / "ig_conversation_data.py"

    def _extract_section(self, content: str, start_marker: str, end_marker: str = '"""') -> Tuple[str, int, int]:
        """Extract a section from file content, return (section, start_idx, end_idx)"""
        start = content.find(start_marker)
        if start == -1:
            return "", -1, -1
        end = content.find(end_marker, start + len(start_marker) + 10) + len(end_marker)
        return content[start:end], start, end

    def read_current_prompts(self) -> Dict[str, Any]:
        """Read and parse current prompt files into sections"""
        prompts = {}

        if self.prompt_builder_path.exists():
            content = self.prompt_builder_path.read_text(encoding="utf-8")
            prompts["prompt_builder_full"] = content

            # Extract TEXTING_RULES
            section, start, end = self._extract_section(content, 'TEXTING_RULES = """')
            if start != -1:
                prompts["texting_rules"] = section
                prompts["texting_rules_pos"] = (start, end)

            # Extract PHASE_GUIDANCE
            section, start, end = self._extract_section(content, 'PHASE_GUIDANCE = {', '}')
            if start != -1:
                # Find the actual end of the dict
                brace_count = 0
                for i, c in enumerate(content[start:], start):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                prompts["phase_guidance"] = content[start:end]
                prompts["phase_guidance_pos"] = (start, end)

        if self.conversation_data_path.exists():
            content = self.conversation_data_path.read_text(encoding="utf-8")
            prompts["conversation_data_full"] = content

            # Extract CONVERSATION_EXAMPLES
            section, start, end = self._extract_section(content, 'CONVERSATION_EXAMPLES = {', '}')
            if start != -1:
                brace_count = 0
                for i, c in enumerate(content[start:], start):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i + 1
                            break
                prompts["conversation_examples"] = content[start:end]
                prompts["conversation_examples_pos"] = (start, end)

        return prompts

    def generate_adjustments(
        self,
        meta_analysis: Dict[str, Any],
        current_prompts: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Generate rewritten prompt sections based on analysis"""

        current_texting_rules = current_prompts.get("texting_rules", "")

        # Get recent problems for context
        recent_problems = []
        for h in history[-3:]:
            recent_problems.extend(h.get("top_problems", []))

        prompt = f"""You are optimizing an Instagram DM chatbot. The goal: sound like a real woman and charm fans into subscribing to OnlyFans.

CURRENT PROBLEMS FROM TESTING:
{json.dumps(meta_analysis, indent=2)}

RECENT ISSUES WE'VE SEEN:
{json.dumps(recent_problems[:10], indent=2)}

CURRENT TEXTING_RULES:
{current_texting_rules}

Rewrite the TEXTING_RULES section to fix the problems. The rules should teach the AI HOW to text naturally while achieving the goal (getting OF subscribers).

Key issues to address:
1. If "goal" score is low: Add guidance on when/how to naturally mention OF
2. If "human" score is low: Add rules about sounding more natural
3. If "charm" score is low: Add rules about being more engaging/witty

IMPORTANT:
- Keep the same format (TEXTING_RULES = \"\"\"...\"\"\")
- Don't add arbitrary percentage rules
- Focus on principles, not rigid patterns
- The bot should NOT always try to keep conversation going
- The bot should mention OF naturally when appropriate

Respond with ONLY the new TEXTING_RULES section, nothing else. Start with TEXTING_RULES = \"\"\""""

        response = self.client.chat.completions.create(
            model=self.config.optimizer_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.5,
        )

        new_texting_rules = response.choices[0].message.content.strip()

        # Validate it starts correctly
        if not new_texting_rules.startswith('TEXTING_RULES = """'):
            # Try to fix common issues
            if 'TEXTING_RULES' in new_texting_rules:
                start = new_texting_rules.find('TEXTING_RULES')
                new_texting_rules = new_texting_rules[start:]
            else:
                return {"error": "Invalid format", "raw": new_texting_rules}

        # Make sure it ends properly
        if not new_texting_rules.rstrip().endswith('"""'):
            new_texting_rules = new_texting_rules.rstrip() + '"""'

        return {
            "new_texting_rules": new_texting_rules,
            "rationale": f"Rewrote TEXTING_RULES to address: {meta_analysis.get('why_not_subscribing', 'unknown issues')[:100]}"
        }

    def apply_adjustments(self, adjustments: Dict[str, Any]) -> bool:
        """Apply the rewritten sections to prompt files"""
        if "error" in adjustments:
            print(f"  Skipping adjustments: {adjustments.get('error')}")
            return False

        try:
            # Read current file
            content = self.prompt_builder_path.read_text(encoding="utf-8")

            # Replace TEXTING_RULES section
            new_rules = adjustments.get("new_texting_rules")
            if new_rules:
                # Find current TEXTING_RULES
                start = content.find('TEXTING_RULES = """')
                if start != -1:
                    # Find the closing """ by counting - it's the first """ after the opening
                    search_start = start + len('TEXTING_RULES = """')
                    end = content.find('"""', search_start)
                    if end != -1:
                        end += 3  # Include the closing """

                        # Validate we're not eating into the next section
                        next_section = content.find('# ===', end)
                        next_def = content.find('\ndef ', end)

                        # Make sure new_rules ends with """
                        if not new_rules.rstrip().endswith('"""'):
                            new_rules = new_rules.rstrip() + '"""'

                        # Replace just the TEXTING_RULES section
                        content = content[:start] + new_rules + content[end:]

                        # Verify the file is still valid Python (basic check)
                        if 'def build_image_instructions' not in content:
                            print("  ERROR: Replacement would corrupt file, aborting")
                            return False

                        # Write back
                        self.prompt_builder_path.write_text(content, encoding="utf-8")
                        print(f"  Rewrote TEXTING_RULES section ({len(new_rules)} chars)")
                        return True

            print("  No changes to apply")
            return False

        except Exception as e:
            print(f"  Failed to apply adjustments: {e}")
            import traceback
            traceback.print_exc()
            return False


# =============================================================================
# MAIN OPTIMIZATION LOOP
# =============================================================================

class OptimizationLoop:
    """Main optimization loop orchestrator"""

    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or OptimizationConfig()

        # Components
        self.batch_runner = BatchTestRunner(self.config)
        self.aggregator = ResultsAggregator()
        self.meta_analyzer = MetaAnalyzer(self.config)
        self.prompt_adjuster = PromptAdjuster(self.config)

        # State
        self.iteration = 0
        self.history: List[Dict[str, Any]] = []
        self.best_score = 0.0
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Output directory for this run
        self.run_dir = self.config.output_dir / f"run_{self.run_id}"
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def run(self, max_tests: int = 5000) -> Dict[str, Any]:
        """Run the full optimization loop"""
        print("=" * 70)
        print(f"OPTIMIZATION LOOP STARTED - Run ID: {self.run_id}")
        print(f"Target: {max_tests} tests, target score: {self.config.target_score}")
        print("=" * 70)

        total_tests = 0
        start_time = time.time()

        while total_tests < max_tests and self.iteration < self.config.max_iterations:
            self.iteration += 1
            print(f"\n{'='*70}")
            print(f"ITERATION {self.iteration}")
            print(f"{'='*70}")

            # 1. Run batch of tests
            results = self.batch_runner.run_batch(self.iteration)
            total_tests += len(results)

            # 2. Aggregate results
            aggregated = self.aggregator.aggregate(results, self.iteration)
            print(f"\nBatch Results:")
            print(f"  Tests: {aggregated.successful_tests}/{aggregated.total_tests} successful")
            print(f"  Overall: {aggregated.avg_overall_score:.2f}/10 | Human: {aggregated.avg_human:.2f} | Charm: {aggregated.avg_charm:.2f} | Goal: {aggregated.avg_goal:.2f}")
            print(f"  Would Subscribe: {aggregated.would_subscribe_rate:.1%} ({aggregated.would_subscribe_count}/{aggregated.successful_tests})")
            print(f"  Verdicts: {aggregated.verdict_counts}")

            # 3. Check if we hit target
            if aggregated.avg_overall_score >= self.config.target_score:
                print(f"\n*** TARGET SCORE REACHED: {aggregated.avg_overall_score:.2f} >= {self.config.target_score} ***")
                break

            # 4. Meta-analyze patterns
            print("\nAnalyzing patterns...")
            meta_analysis = self.meta_analyzer.analyze_patterns(aggregated)

            if "error" not in meta_analysis:
                top_issues = meta_analysis.get('top_issues', [])
                if top_issues:
                    print(f"  Top Issue: {top_issues[0].get('problem', 'N/A')}")
                print(f"  Why Not Subscribing: {meta_analysis.get('why_not_subscribing', 'N/A')[:80]}")
                print(f"  Worst Persona: {meta_analysis.get('worst_persona', {}).get('persona', 'N/A')}")

            # 5. Generate and apply adjustments
            print("\nGenerating prompt adjustments...")
            current_prompts = self.prompt_adjuster.read_current_prompts()
            adjustments = self.prompt_adjuster.generate_adjustments(
                meta_analysis, current_prompts, self.history
            )

            if "error" not in adjustments:
                print(f"  Adjustments: {adjustments.get('rationale', 'N/A')[:100]}...")
                self.prompt_adjuster.apply_adjustments(adjustments)

            # 6. Record history
            iteration_record = {
                "iteration": self.iteration,
                "timestamp": datetime.now().isoformat(),
                "total_tests": total_tests,
                "batch_size": len(results),
                "avg_score": aggregated.avg_overall_score,
                "avg_human": aggregated.avg_human,
                "avg_charm": aggregated.avg_charm,
                "avg_goal": aggregated.avg_goal,
                "would_subscribe_rate": aggregated.would_subscribe_rate,
                "verdicts": aggregated.verdict_counts,
                "scores_by_persona": aggregated.scores_by_persona,
                "top_problems": list(aggregated.problem_counts.keys())[:5],
                "meta_analysis": meta_analysis,
                "adjustments_made": adjustments.get("rationale", ""),
            }
            self.history.append(iteration_record)

            # Track best score
            if aggregated.avg_overall_score > self.best_score:
                self.best_score = aggregated.avg_overall_score
                print(f"  New best score: {self.best_score:.2f}")

            # 7. Save iteration results
            self._save_iteration(iteration_record, aggregated)

            # Brief pause to avoid rate limits
            time.sleep(2)

        # Final summary
        elapsed = time.time() - start_time
        final_summary = {
            "run_id": self.run_id,
            "total_iterations": self.iteration,
            "total_tests": total_tests,
            "elapsed_seconds": elapsed,
            "best_score": self.best_score,
            "target_reached": self.best_score >= self.config.target_score,
            "history": self.history,
        }

        self._save_final_summary(final_summary)
        self._print_final_summary(final_summary)

        return final_summary

    def _save_iteration(self, record: Dict[str, Any], aggregated: AggregatedResults):
        """Save iteration results to file"""
        filepath = self.run_dir / f"iteration_{self.iteration:03d}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "record": record,
                "problem_counts": aggregated.problem_counts,
                "fix_counts": aggregated.fix_counts,
            }, f, indent=2)

    def _save_final_summary(self, summary: Dict[str, Any]):
        """Save final summary"""
        filepath = self.run_dir / "final_summary.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        print(f"\nResults saved to: {self.run_dir}")

    def _print_final_summary(self, summary: Dict[str, Any]):
        """Print final summary"""
        print("\n" + "=" * 70)
        print("OPTIMIZATION COMPLETE")
        print("=" * 70)
        print(f"Run ID: {summary['run_id']}")
        print(f"Iterations: {summary['total_iterations']}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Time: {summary['elapsed_seconds']:.1f} seconds")
        print(f"Best Score: {summary['best_score']:.2f}/10")
        print(f"Target Reached: {summary['target_reached']}")

        # Score progression
        if self.history:
            print("\nScore Progression:")
            for h in self.history:
                print(f"  Iteration {h['iteration']}: {h['avg_score']:.2f}")

        print("=" * 70)


# =============================================================================
# CLI INTERFACE
# =============================================================================

def run_optimization(
    tests: int = 500,
    batch_size: int = 50,
    target_score: float = 8.0,
    model: str = "grok-4-1-fast-non-reasoning",
):
    """Run optimization loop with specified parameters"""
    config = OptimizationConfig(
        tests_per_batch=batch_size,
        target_score=target_score,
        chatbot_model=model,
    )

    loop = OptimizationLoop(config)
    return loop.run(max_tests=tests)


if __name__ == "__main__":
    import sys

    # Parse arguments
    tests = 500
    batch_size = 50
    target = 8.5
    model = "grok-4-1-fast-non-reasoning"

    for arg in sys.argv[1:]:
        if arg.startswith("--tests="):
            tests = int(arg.split("=")[1])
        elif arg.startswith("--batch="):
            batch_size = int(arg.split("=")[1])
        elif arg.startswith("--target="):
            target = float(arg.split("=")[1])
        elif arg.startswith("--model="):
            model = arg.split("=")[1]

    print(f"Starting optimization: {tests} tests, batch size {batch_size}, target {target}")
    print(f"Model: {model}")
    print()

    run_optimization(
        tests=tests,
        batch_size=batch_size,
        target_score=target,
        model=model,
    )
