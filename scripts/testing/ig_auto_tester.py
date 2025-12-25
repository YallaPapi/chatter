# -*- coding: utf-8 -*-
"""
IG Auto Tester

Automated testing with AI-powered analysis:
1. AI simulates different fan personas
2. Chatbot responds
3. AI analyzes conversation for coherence + authenticity
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from openai import OpenAI

# Import chatbot
from ig_chatbot import IGChatbot, ChatbotConfig

# Test output directory
TEST_DIR = Path(__file__).parent.parent.parent / "data" / "tests"
TEST_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# FAN PERSONAS FOR TESTING
# =============================================================================

FAN_PERSONAS = {
    "horny_direct": {
        "name": "Horny Direct Guy",
        "description": "Jumps straight to sexual content, wants nudes fast",
        "behavior": "Opens with compliments about her body, quickly asks for pics/nudes, pushes for sexual content",
        "messages_style": "short, direct, sexual undertones",
    },
    "nice_guy": {
        "name": "Nice Guy",
        "description": "Polite, asks questions, genuinely interested in conversation",
        "behavior": "Asks about her day, interests, tries to build rapport, eventually asks to meet",
        "messages_style": "polite, longer messages, asks questions",
    },
    "skeptic": {
        "name": "Skeptical Guy",
        "description": "Thinks she's a bot or catfish, needs convincing",
        "behavior": "Questions if she's real, asks for proof, suspicious of everything",
        "messages_style": "doubtful, questioning, wants verification",
    },
    "cheap_guy": {
        "name": "Cheap Guy",
        "description": "Interested but doesn't want to pay for anything",
        "behavior": "Engages well but balks at any mention of paying, wants free content",
        "messages_style": "engaged but resistant to spending money",
    },
    "pushy_meetup": {
        "name": "Pushy Meetup Guy",
        "description": "Really wants to meet in person, keeps pushing",
        "behavior": "Asks to meet repeatedly, offers dinner/drinks, doesn't take soft no",
        "messages_style": "persistent about meeting, offers plans",
    },
    "slow_burn": {
        "name": "Slow Burn Guy",
        "description": "Takes his time, casual conversation",
        "behavior": "Chats casually, no rush, might take many messages before any escalation",
        "messages_style": "relaxed, casual, no pressure",
    },
    "wants_snap": {
        "name": "Snap Hunter",
        "description": "Wants to move to Snapchat or get her number",
        "behavior": "Asks for snap/number early, prefers other platforms",
        "messages_style": "asks for other contact methods",
    },
    "emotional": {
        "name": "Emotional Guy",
        "description": "Opens up about personal problems, seeks connection",
        "behavior": "Shares personal struggles, looking for someone to talk to",
        "messages_style": "vulnerable, shares feelings, seeks empathy",
    },
}


# =============================================================================
# FAN SIMULATOR
# =============================================================================

class FanSimulator:
    """Simulates a fan using AI"""

    def __init__(self, persona_id: str, api_key: str = None):
        self.persona = FAN_PERSONAS.get(persona_id, FAN_PERSONAS["nice_guy"])
        self.api_key = api_key or os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.x.ai/v1")
        self.message_count = 0

    def generate_message(self, conversation_history: List[Dict[str, str]], her_last_message: str = None) -> str:
        """Generate next fan message based on persona and conversation"""

        system_prompt = f"""You are simulating a guy DMing a hot girl on Instagram for testing purposes.

PERSONA: {self.persona['name']}
DESCRIPTION: {self.persona['description']}
BEHAVIOR: {self.persona['behavior']}
STYLE: {self.persona['messages_style']}

RULES:
- Write SHORT messages like a real guy texting (1-15 words typically)
- Stay in character for this persona
- React naturally to what she says
- Don't be too articulate or formal
- Use casual spelling: u, ur, wyd, etc.
- This is message #{self.message_count + 1} in the conversation

If this is the first message, open naturally (hey, what's up, etc.)
If she mentioned OF, react according to your persona.
If she deflected meeting, react according to your persona."""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in conversation_history:
            role = "assistant" if msg["role"] == "fan" else "user"
            messages.append({"role": role, "content": msg["content"]})

        # Add her last message if provided
        if her_last_message:
            messages.append({"role": "user", "content": f"She said: {her_last_message}\n\nNow write your next message as the fan:"})
        else:
            messages.append({"role": "user", "content": "Start the conversation. Send your opening message:"})

        response = self.client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=messages,
            max_tokens=50,
            temperature=0.9,
        )

        self.message_count += 1
        return response.choices[0].message.content.strip().strip('"')


# =============================================================================
# CONVERSATION ANALYZER
# =============================================================================

class ConversationAnalyzer:
    """Analyzes conversations for quality"""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key, base_url="https://api.x.ai/v1")

    def analyze(self, conversation: List[Dict[str, str]], fan_persona: str) -> Dict[str, Any]:
        """Analyze a conversation for coherence and authenticity"""

        # Format conversation for analysis
        convo_text = "\n".join([
            f"{'FAN' if msg['role'] == 'fan' else 'HER'}: {msg['content']}"
            for msg in conversation
        ])

        analysis_prompt = f"""You are evaluating an Instagram DM chatbot. The fan persona was: {fan_persona}

THE GOAL: Have a natural conversation that convinces the fan she's a real person and charms him enough to subscribe to her OnlyFans. That's it.

CONVERSATION:
{convo_text}

Evaluate this conversation against THE GOAL. Does she seem like a real woman? Would this guy subscribe?

Score these (1-10):

1. HUMAN (1-10): Does she pass as a real woman texting on her phone?
   - Would a normal person suspect this is a bot?
   - Does she text like an actual person or like a customer service script?

2. CHARM (1-10): Is she likeable? Engaging? Would he want to keep talking and eventually subscribe?
   - Is there personality, wit, humor?
   - Would he tell his friends about this girl or forget her immediately?

3. GOAL (1-10): Did the conversation move toward OnlyFans subscription?
   - Did she mention OF naturally, not desperately?
   - If he objected, did she handle it well?
   - By the end, is he more or less likely to subscribe?

4. PROBLEMS: What specific moments broke the illusion or hurt the goal?

5. FIXES: What would make this conversation better?

Respond in JSON:
{{
    "human": {{"score": X, "notes": "..."}},
    "charm": {{"score": X, "notes": "..."}},
    "goal": {{"score": X, "notes": "..."}},
    "problems": ["...", "..."],
    "fixes": ["...", "..."],
    "overall_score": X,
    "would_subscribe": true/false,
    "verdict": "PASS/FAIL/NEEDS_WORK"
}}"""

        response = self.client.chat.completions.create(
            model="grok-4-1-fast-non-reasoning",
            messages=[{"role": "user", "content": analysis_prompt}],
            max_tokens=1000,
            temperature=0.3,
        )

        # Parse JSON response
        try:
            # Extract JSON from response
            content = response.choices[0].message.content
            # Find JSON in response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(content[start:end])
        except json.JSONDecodeError:
            pass

        return {"error": "Failed to parse analysis", "raw": response.choices[0].message.content}


# =============================================================================
# TEST RUNNER
# =============================================================================

@dataclass
class TestResult:
    """Result of a single test conversation"""
    test_id: str
    fan_persona: str
    conversation: List[Dict[str, str]]
    analysis: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "test_id": self.test_id,
            "fan_persona": self.fan_persona,
            "conversation": self.conversation,
            "analysis": self.analysis,
            "timestamp": self.timestamp,
        }


class TestRunner:
    """Runs automated conversation tests"""

    def __init__(self):
        self.chatbot = IGChatbot()
        self.analyzer = ConversationAnalyzer()
        self.results: List[TestResult] = []

    def run_test(self, fan_persona_id: str, max_messages: int = 50) -> TestResult:
        """Run a single test conversation"""
        # Handle encoding for Windows console
        def safe_print(text):
            try:
                print(text)
            except UnicodeEncodeError:
                print(text.encode('ascii', 'replace').decode('ascii'))

        safe_print(f"\n{'='*50}")
        safe_print(f"Testing with persona: {FAN_PERSONAS[fan_persona_id]['name']}")
        safe_print(f"{'='*50}")

        # Initialize
        fan = FanSimulator(fan_persona_id)
        self.chatbot.start_conversation()
        conversation = []

        # Run conversation up to max
        for i in range(max_messages):
            # Fan sends message
            her_last = conversation[-1]["content"] if conversation and conversation[-1]["role"] == "her" else None
            fan_msg = fan.generate_message(conversation, her_last)

            safe_print(f"\nFAN: {fan_msg}")
            conversation.append({"role": "fan", "content": fan_msg})

            # Bot responds
            responses = self.chatbot.respond(fan_msg)
            her_response = "||".join([r.text for r in responses if r.text])

            # Add images to response text for logging
            for r in responses:
                if r.has_image():
                    her_response += f" [IMG:{r.image}]"

            safe_print(f"HER: {her_response}")
            conversation.append({"role": "her", "content": her_response})

        # Analyze conversation
        safe_print(f"\n{'='*50}")
        safe_print("Analyzing conversation...")
        analysis = self.analyzer.analyze(conversation, FAN_PERSONAS[fan_persona_id]['name'])

        # Create result
        test_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{fan_persona_id}"
        result = TestResult(
            test_id=test_id,
            fan_persona=fan_persona_id,
            conversation=conversation,
            analysis=analysis,
        )

        self.results.append(result)
        return result

    def run_all_personas(self, max_messages: int = 10) -> List[TestResult]:
        """Run tests for all fan personas"""
        results = []
        for persona_id in FAN_PERSONAS.keys():
            result = self.run_test(persona_id, max_messages)
            results.append(result)
        return results

    def save_results(self, filename: str = None):
        """Save all results to file"""
        if not filename:
            filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = TEST_DIR / filename
        with open(filepath, 'w') as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)

        print(f"\nResults saved to: {filepath}")
        return filepath

    def print_summary(self):
        """Print summary of all test results"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        total_score = 0
        for result in self.results:
            analysis = result.analysis
            if "error" not in analysis:
                score = analysis.get("overall_score", 0)
                verdict = analysis.get("verdict", "N/A")
                print(f"\n{FAN_PERSONAS[result.fan_persona]['name']}:")
                print(f"  Overall Score: {score}/10")
                print(f"  Verdict: {verdict}")
                print(f"  Coherence: {analysis.get('coherence', {}).get('score', 'N/A')}/10")
                print(f"  Authenticity: {analysis.get('authenticity', {}).get('score', 'N/A')}/10")
                print(f"  Bot Detection: {analysis.get('bot_detection', {}).get('score', 'N/A')}/10")

                if analysis.get("red_flags"):
                    print(f"  Red Flags: {', '.join(analysis['red_flags'][:3])}")

                total_score += score

        avg_score = total_score / len(self.results) if self.results else 0
        print(f"\n{'='*60}")
        print(f"AVERAGE SCORE: {avg_score:.1f}/10")
        print("="*60)


# =============================================================================
# QUICK TEST FUNCTIONS
# =============================================================================

def run_single_test(persona: str = "nice_guy", messages: int = 10):
    """Run a single test"""
    runner = TestRunner()
    result = runner.run_test(persona, messages)

    print("\n" + "="*60)
    print("ANALYSIS RESULTS")
    print("="*60)
    print(json.dumps(result.analysis, indent=2))

    runner.save_results()
    return result


def run_full_test_suite(messages_per_test: int = 10):
    """Run tests for all personas"""
    runner = TestRunner()
    runner.run_all_personas(messages_per_test)
    runner.print_summary()
    runner.save_results()
    return runner.results


def run_all_batch_tests(num_tests: int = 10, messages_per_test: int = 10):
    """Run batch tests for ALL personas and compare results"""
    print(f"\n{'='*60}")
    print(f"FULL BATCH TEST: {num_tests} tests x {len(FAN_PERSONAS)} personas = {num_tests * len(FAN_PERSONAS)} total")
    print(f"{'='*60}")

    all_results = {}
    for persona_id in FAN_PERSONAS.keys():
        result = run_batch_test(persona_id, num_tests, messages_per_test)
        if result:
            all_results[persona_id] = result

    # Print comparison
    print(f"\n{'='*60}")
    print("PERSONA COMPARISON")
    print(f"{'='*60}")
    print(f"\n{'PERSONA':<20} {'HUMAN':>8} {'CHARM':>8} {'GOAL':>8} {'OVERALL':>8} {'PASS%':>8}")
    print("-" * 60)

    sorted_results = sorted(all_results.items(), key=lambda x: -x[1]["scores"]["overall"])
    for persona_id, result in sorted_results:
        scores = result["scores"]
        verdicts = result["verdicts"]
        pass_pct = (verdicts.get("PASS", 0) / num_tests * 100) if num_tests > 0 else 0
        print(f"{FAN_PERSONAS[persona_id]['name']:<20} {scores['human']:>8.1f} {scores['charm']:>8.1f} {scores['goal']:>8.1f} {scores['overall']:>8.1f} {pass_pct:>7.0f}%")

    # Save combined results
    combined_file = TEST_DIR / f"full_batch_{num_tests}tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(combined_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nCombined results saved to: {combined_file}")

    return all_results


def run_batch_test(persona: str, num_tests: int = 10, messages_per_test: int = 10):
    """Run multiple tests for a single persona and aggregate results"""
    if persona not in FAN_PERSONAS:
        print(f"Unknown persona: {persona}")
        print(f"Available: {', '.join(FAN_PERSONAS.keys())}")
        return None

    print(f"\n{'='*60}")
    print(f"BATCH TEST: {num_tests} conversations with {FAN_PERSONAS[persona]['name']}")
    print(f"{'='*60}")

    runner = TestRunner()

    for i in range(num_tests):
        print(f"\n--- Test {i+1}/{num_tests} ---")
        runner.run_test(persona, messages_per_test)

    # Aggregate results
    print(f"\n{'='*60}")
    print(f"BATCH RESULTS: {persona}")
    print(f"{'='*60}")

    scores = {"human": [], "charm": [], "goal": [], "overall": []}
    problems_count = {}
    fixes_count = {}
    verdicts = {"PASS": 0, "FAIL": 0, "NEEDS_WORK": 0}

    for result in runner.results:
        analysis = result.analysis
        if "error" in analysis:
            continue

        # Collect scores
        if "human" in analysis:
            scores["human"].append(analysis["human"].get("score", 0))
        if "charm" in analysis:
            scores["charm"].append(analysis["charm"].get("score", 0))
        if "goal" in analysis:
            scores["goal"].append(analysis["goal"].get("score", 0))
        scores["overall"].append(analysis.get("overall_score", 0))

        # Count problems
        for problem in analysis.get("problems", []):
            problems_count[problem] = problems_count.get(problem, 0) + 1

        # Count fixes
        for fix in analysis.get("fixes", []):
            fixes_count[fix] = fixes_count.get(fix, 0) + 1

        # Count verdicts
        verdict = analysis.get("verdict", "NEEDS_WORK")
        verdicts[verdict] = verdicts.get(verdict, 0) + 1

    # Print aggregated results
    print(f"\nSCORES (avg of {len(scores['overall'])} tests):")
    for key, vals in scores.items():
        if vals:
            avg = sum(vals) / len(vals)
            print(f"  {key.upper():12}: {avg:.1f}/10  (range: {min(vals)}-{max(vals)})")

    print(f"\nVERDICTS:")
    for verdict, count in verdicts.items():
        pct = (count / num_tests * 100) if num_tests > 0 else 0
        print(f"  {verdict}: {count} ({pct:.0f}%)")

    print(f"\nTOP PROBLEMS (by frequency):")
    sorted_problems = sorted(problems_count.items(), key=lambda x: -x[1])[:5]
    for problem, count in sorted_problems:
        # Handle Unicode for Windows console
        safe_problem = problem[:70].encode('ascii', 'replace').decode('ascii')
        print(f"  [{count}x] {safe_problem}...")

    print(f"\nTOP SUGGESTED FIXES (by frequency):")
    sorted_fixes = sorted(fixes_count.items(), key=lambda x: -x[1])[:5]
    for fix, count in sorted_fixes:
        safe_fix = fix[:70].encode('ascii', 'replace').decode('ascii')
        print(f"  [{count}x] {safe_fix}...")

    # Save results
    runner.save_results(f"batch_{persona}_{num_tests}tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

    return {
        "persona": persona,
        "num_tests": num_tests,
        "scores": {k: sum(v)/len(v) if v else 0 for k, v in scores.items()},
        "verdicts": verdicts,
        "top_problems": sorted_problems,
        "top_fixes": sorted_fixes,
    }


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        arg1 = sys.argv[1]

        # Check for batch mode: --batch <persona> <num_tests>
        if arg1 == "--batch":
            persona = sys.argv[2] if len(sys.argv) > 2 else "nice_guy"
            num_tests = int(sys.argv[3]) if len(sys.argv) > 3 else 10
            run_batch_test(persona, num_tests)
        elif arg1 == "--batch-all":
            num_tests = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            run_all_batch_tests(num_tests)
        elif arg1 == "--all":
            run_full_test_suite()
        elif arg1 in FAN_PERSONAS:
            run_single_test(arg1)
        else:
            print(f"Unknown option: {arg1}")
            print(f"\nUsage:")
            print(f"  python ig_auto_tester.py                        # Single nice_guy test")
            print(f"  python ig_auto_tester.py <persona>              # Single test with persona")
            print(f"  python ig_auto_tester.py --batch <persona> <N>  # N tests with persona")
            print(f"  python ig_auto_tester.py --batch-all <N>        # N tests x ALL personas")
            print(f"  python ig_auto_tester.py --all                  # All personas, 1 test each")
            print(f"\nPersonas: {', '.join(FAN_PERSONAS.keys())}")
    else:
        # Default: run nice_guy test
        print("Running single test with 'nice_guy' persona...")
        print("Use --batch nice_guy 10 for batch testing")
        print(f"Available personas: {', '.join(FAN_PERSONAS.keys())}")
        print()
        run_single_test("nice_guy")
