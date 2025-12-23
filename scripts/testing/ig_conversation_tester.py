# -*- coding: utf-8 -*-
"""
IG Conversation Tester

Two modes:
1. Manual: You play the guy, AI plays the girl
2. Automated: AI plays both sides, generates thousands of conversations

For testing and validating the IG bot flow.
"""

import os
import sys
import json
import random
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

# Load .env from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")
console = Console()

# Add project root to path for imports
import sys
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# US cities for simulation
US_CITIES = [
    "Miami", "Tampa", "Orlando", "Jacksonville",
    "New York", "Brooklyn", "Queens", "Manhattan",
    "Los Angeles", "San Diego", "San Francisco", "Oakland",
    "Chicago", "Houston", "Dallas", "Austin", "San Antonio",
    "Phoenix", "Denver", "Seattle", "Portland", "Atlanta",
    "Boston", "Philadelphia", "Detroit", "Minneapolis",
    "Las Vegas", "Nashville", "Charlotte", "Columbus"
]

# Guy opener types for simulation
GUY_OPENER_TYPES = [
    "location_question",      # "You're in Miami?"
    "simple_hey",             # "Hey" / "Hi"
    "compliment",             # "Damn you're fine"
    "direct_meetup",          # "Let's hang out"
    "sexual",                 # Gets sexual immediately
]


class ConversationPhase(Enum):
    OPENER = "opener"
    LOCATION = "location"
    SMALL_TALK = "small_talk"
    MEETUP_DEFLECT_1 = "meetup_deflect_1"
    MORE_TALK = "more_talk"
    MEETUP_DEFLECT_2 = "meetup_deflect_2"
    OF_REDIRECT = "of_redirect"
    COMPLETED = "completed"
    DROPPED = "dropped"


class ConversationOutcome(Enum):
    SUCCESS = "success"           # Got to OF redirect
    DROP_EARLY = "drop_early"     # Guy stopped responding early
    DROP_LATE = "drop_late"       # Guy stopped after deflection
    WEIRD = "weird"               # Conversation went off rails
    ERROR = "error"               # Technical error


@dataclass
class TestConversation:
    """A single test conversation."""
    id: str
    location: Optional[str] = None
    messages: List[Dict] = field(default_factory=list)
    phase: ConversationPhase = ConversationPhase.OPENER
    outcome: Optional[ConversationOutcome] = None
    score: Optional[float] = None
    issues: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

    def add_message(self, role: str, text: str):
        self.messages.append({
            "role": role,
            "text": text,
            "timestamp": datetime.now().isoformat()
        })

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "phase": self.phase.value,
            "outcome": self.outcome.value if self.outcome else None
        }


class IGBotSimulator:
    """Simulates the IG bot (the girl's side)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.location: Optional[str] = None

        # Import persona system
        from scripts.testing.ig_persona import Persona, ConvoState, get_phase_guidance, DEFAULT_PERSONA
        self.persona = DEFAULT_PERSONA
        self.state = ConvoState()

    def get_system_prompt(self) -> str:
        from scripts.testing.ig_persona import get_phase_guidance, ConvoPhase

        location_context = f"You said you're visiting {self.location}." if self.location else ""
        phase_guidance = get_phase_guidance(self.state)

        # Strict OF rules based on phase
        of_rule = ""
        if self.state.phase in [ConvoPhase.OPENING, ConvoPhase.BUILDING_RAPPORT]:
            of_rule = "STRICT RULE: Do NOT mention OF/OnlyFans yet. Too early. Just chat."
        elif self.state.phase == ConvoPhase.QUALIFYING:
            of_rule = "STRICT RULE: Do NOT mention OF yet. Deflect meetup softly, keep hope alive, go back to chatting."
        elif self.state.phase == ConvoPhase.PITCHING:
            of_rule = "NOW you can mention OF casually. Just once, dont be pushy."
        elif self.state.of_mentioned:
            of_rule = "Already mentioned OF. Dont bring it up again unless he asks."

        return f"""{self.persona.to_prompt()}

{location_context}

CURRENT PHASE: {self.state.phase.value}
{phase_guidance}

{of_rule}

Stats: meetup asks={self.state.meetup_requests}, pic asks={self.state.pic_requests}, OF mentioned={self.state.of_mentioned}
"""

    async def generate_response(self, conversation: TestConversation) -> str:
        """Generate bot response using Grok (xAI)."""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

        # Pre-update state based on guy's last message BEFORE generating response
        last_guy_msg = conversation.messages[-1]["text"] if conversation.messages else ""
        self._pre_update_state(last_guy_msg)

        # Build message history
        messages = [{"role": "system", "content": self.get_system_prompt()}]
        for msg in conversation.messages:
            role = "user" if msg["role"] == "guy" else "assistant"
            messages.append({"role": role, "content": msg["text"]})

        response = client.chat.completions.create(
            model="grok-4-1-fast",
            max_tokens=200,
            temperature=0.85,
            messages=messages
        )

        girl_response = response.choices[0].message.content

        # Post-update state after response (track OF mentions, etc)
        self._post_update_state(girl_response)

        return girl_response

    def _pre_update_state(self, guy_message: str):
        """Update state based on guy's message BEFORE generating response."""
        from scripts.testing.ig_persona import ConvoPhase

        msg_lower = guy_message.lower()
        self.state.guy_messages += 1

        # Detect meetup request - more patterns
        meetup_patterns = [
            "meet", "hang", "drinks", "date", "link up", "take you out",
            "grab", "chill together", "show you around", "get lunch",
            "get dinner", "get coffee", "get food", "go out", "come over",
            "come by", "stop by", "visit", "see you", "hook up", "link",
            "get together", "should we", "wanna hang", "lets hang",
            "when can i see", "when can we", "lets go", "take u out"
        ]
        # Persistence patterns (pushing after deflection)
        persistence_patterns = [
            "come on", "why not", "give me a chance", "just once",
            "one time", "scared", "what u scared", "dont be shy",
            "not scared", "just saying", "think about it"
        ]
        if any(p in msg_lower for p in meetup_patterns):
            self.state.meetup_requests += 1
        elif self.state.meetup_requests >= 1 and any(p in msg_lower for p in persistence_patterns):
            self.state.meetup_requests += 1

        # Detect explicit pic/sexual request (not just asking for a selfie)
        explicit_pic_patterns = ["nudes", "naked", "show me ur body", "send something sexy", "what u wearing"]
        sfw_pic_patterns = ["selfie", "pic of you", "photo of u", "see your face", "prove ur real"]

        if any(p in msg_lower for p in explicit_pic_patterns):
            self.state.pic_requests += 1  # Explicit = redirect to OF

        sexual_patterns = ["titties", "tits", "ass", "pussy", "dick", "boobs", "nude"]
        if any(p in msg_lower for p in sexual_patterns) and self.state.guy_messages > 2:
            self.state.sexual_escalation = True

        # Update phase based on current state
        if self.state.of_mentioned:
            self.state.phase = ConvoPhase.POST_PITCH
        elif self.state.meetup_requests >= 2 or self.state.pic_requests > 0 or self.state.sexual_escalation:
            self.state.phase = ConvoPhase.PITCHING
        elif self.state.meetup_requests == 1:
            self.state.phase = ConvoPhase.QUALIFYING
        elif self.state.guy_messages <= 2:
            self.state.phase = ConvoPhase.OPENING
        else:
            self.state.phase = ConvoPhase.BUILDING_RAPPORT

    def _post_update_state(self, girl_response: str):
        """Update state after response (track OF mentions)."""
        from scripts.testing.ig_persona import ConvoPhase

        if "of" in girl_response.lower() or "onlyfans" in girl_response.lower():
            self.state.of_mentioned = True
            self.state.of_mention_count += 1
            self.state.phase = ConvoPhase.POST_PITCH

        self.state.message_count += 2

    def extract_location(self, text: str) -> Optional[str]:
        """Extract city name from message."""
        text_lower = text.lower()
        for city in US_CITIES:
            if city.lower() in text_lower:
                return city
        return None


class GuySimulator:
    """Simulates the guy's side for automated testing."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("XAI_API_KEY")
        self.persona: Dict = {}

    def generate_persona(self) -> Dict:
        """Generate a random guy persona."""
        self.persona = {
            "city": random.choice(US_CITIES),
            "age": random.randint(22, 55),
            "job": random.choice([
                "software engineer", "accountant", "nurse", "teacher",
                "sales rep", "contractor", "manager", "student",
                "lawyer", "realtor", "marketing", "owns a business"
            ]),
            "opener_type": random.choice(GUY_OPENER_TYPES),
            "persistence": random.choice(["low", "medium", "high"]),
            "patience": random.randint(3, 12),  # messages before giving up
        }
        return self.persona

    def get_system_prompt(self) -> str:
        return f"""You are a {self.persona['age']} year old guy from {self.persona['city']}
who works as a {self.persona['job']}. You're chatting with an attractive woman on Instagram.

Your personality:
- Persistence level: {self.persona['persistence']}
- You'll try to meet up with her
- You might get flirty/sexual
- If she keeps deflecting, you might lose interest after a few tries
- You're skeptical she's real at first

Opener style: {self.persona['opener_type']}

Respond naturally as this guy would. One message at a time. Keep it casual and realistic.
If she mentions OF, you might:
- Ask what's on there
- Ask how much it costs
- Say you'll check it out
- Or lose interest

Don't be too eager or too hostile. Be realistic."""

    async def generate_response(self, conversation: TestConversation) -> str:
        """Generate guy response using Grok (xAI)."""
        from openai import OpenAI

        client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )

        # Build message history (reversed roles for guy's perspective)
        messages = [{"role": "system", "content": self.get_system_prompt()}]
        for msg in conversation.messages:
            role = "assistant" if msg["role"] == "guy" else "user"
            messages.append({"role": role, "content": msg["text"]})

        response = client.chat.completions.create(
            model="grok-4-1-fast",
            max_tokens=100,
            messages=messages
        )

        return response.choices[0].message.content

    def generate_opener(self) -> str:
        """Generate opening message based on persona."""
        city = self.persona["city"]
        opener_type = self.persona["opener_type"]

        openers = {
            "location_question": [
                f"You're in {city}?",
                f"No way you're actually in {city}",
                f"Wait you're really in {city}?",
            ],
            "simple_hey": [
                "Hey",
                "Hi there",
                "Hey what's up",
                "Heyy",
            ],
            "compliment": [
                "Damn you're fine",
                "You're gorgeous",
                "Wow you're beautiful",
                "You're really pretty",
            ],
            "direct_meetup": [
                "We should hang out",
                "Let's get drinks sometime",
                "You trying to link?",
            ],
            "sexual": [
                "You're so hot 🔥",
                "Damn what I would do to you",
                "You're sexy af",
            ],
        }

        return random.choice(openers.get(opener_type, openers["simple_hey"]))


class ConversationEvaluator:
    """Evaluates conversation quality."""

    def __init__(self):
        self.criteria = [
            "location_handled",
            "natural_flow",
            "meetup_deflected",
            "of_redirect_achieved",
            "no_weird_responses",
            "consistent_persona",
            "appropriate_length",
        ]

    def evaluate(self, conversation: TestConversation) -> Tuple[float, List[str]]:
        """
        Evaluate a conversation.
        Returns (score 0-100, list of issues)
        """
        score = 100.0
        issues = []

        messages = conversation.messages
        girl_messages = [m for m in messages if m["role"] == "girl"]
        guy_messages = [m for m in messages if m["role"] == "guy"]

        # Check location handling
        if not conversation.location:
            # Check if location was mentioned but not captured
            all_text = " ".join(m["text"] for m in messages)
            for city in US_CITIES:
                if city.lower() in all_text.lower():
                    issues.append(f"Location '{city}' mentioned but not captured")
                    score -= 10
                    break

        # Check conversation length
        if len(messages) < 4:
            issues.append("Conversation too short")
            score -= 15
        elif len(messages) > 25:
            issues.append("Conversation too long without resolution")
            score -= 10

        # Check for OF redirect
        of_mentioned = any(
            "of" in m["text"].lower() or "onlyfans" in m["text"].lower()
            for m in girl_messages
        )
        if not of_mentioned and len(messages) > 8:
            issues.append("No OF redirect despite long conversation")
            score -= 20

        # Check for weird responses (too long, too formal)
        for msg in girl_messages:
            if len(msg["text"]) > 200:
                issues.append("Girl response too long")
                score -= 5
            if any(formal in msg["text"].lower() for formal in
                   ["therefore", "however", "additionally", "furthermore"]):
                issues.append("Response too formal")
                score -= 10

        # Check meetup handling
        meetup_words = ["meet", "hang", "drinks", "date", "link up", "get together", "take you out"]
        meetup_requested = any(
            any(w in m["text"].lower() for w in meetup_words)
            for m in guy_messages
        )
        if meetup_requested:
            # Check if properly deflected - expanded patterns
            deflect_phrases = [
                "barely know", "don't meet", "don't really", "maybe", "slow down",
                "idk about that", "not from here", "just chatting", "keep things online",
                "don't do that", "not usually", "not my thing", "keeping it chill",
                "just started talking", "don't know you", "random guys", "from ig"
            ]
            deflected = any(
                any(p in m["text"].lower() for p in deflect_phrases)
                for m in girl_messages
            )
            # Also count OF redirect as handling the meetup
            of_redirected = any(
                "of" in m["text"].lower() or "onlyfans" in m["text"].lower()
                for m in girl_messages
            )
            if not deflected and not of_redirected:
                issues.append("Meetup request not properly deflected")
                score -= 15

        return max(0, score), issues

    async def evaluate_with_ai(self, conversation: TestConversation, api_key: str) -> Tuple[float, List[str]]:
        """Use AI to evaluate conversation quality."""
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1"
        )

        convo_text = "\n".join([
            f"{'GUY' if m['role'] == 'guy' else 'GIRL'}: {m['text']}"
            for m in conversation.messages
        ])

        response = client.chat.completions.create(
            model="grok-4-1-fast",
            max_tokens=500,
            messages=[{
                "role": "user",
                "content": f"""Evaluate this Instagram DM conversation where a girl is trying to
get a guy to subscribe to her OnlyFans.

Conversation:
{convo_text}

Rate on these criteria (each 0-20 points):
1. Natural/believable flow
2. Location handling (if applicable)
3. Meetup deflection (if applicable)
4. OF redirect execution
5. Overall authenticity

Respond in JSON format:
{{"score": <total 0-100>, "issues": ["list", "of", "issues"], "notes": "brief notes"}}"""
            }]
        )

        try:
            result = json.loads(response.choices[0].message.content)
            return result.get("score", 50), result.get("issues", [])
        except:
            return 50, ["Failed to parse AI evaluation"]


async def run_manual_test():
    """Run interactive manual testing - you play the guy."""
    console.print(Panel.fit(
        "[bold cyan]IG Bot Manual Tester[/bold cyan]\n"
        "You play the guy. The AI plays the girl.\n"
        "Type 'quit' to exit, 'score' to evaluate current convo.",
        title="Manual Testing Mode"
    ))

    bot = IGBotSimulator()
    evaluator = ConversationEvaluator()

    conversation = TestConversation(
        id=f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )

    console.print("\n[dim]Start the conversation as a guy would on IG...[/dim]\n")

    while True:
        # Get guy input
        guy_msg = Prompt.ask("[bold blue]YOU (guy)[/bold blue]")

        if guy_msg.lower() == "quit":
            break

        if guy_msg.lower() == "score":
            score, issues = evaluator.evaluate(conversation)
            console.print(f"\n[yellow]Score: {score}/100[/yellow]")
            if issues:
                console.print(f"[red]Issues: {', '.join(issues)}[/red]")
            continue

        conversation.add_message("guy", guy_msg)

        # Check for location
        location = bot.extract_location(guy_msg)
        if location and not conversation.location:
            conversation.location = location
            bot.location = location
            console.print(f"[dim]📍 Location detected: {location}[/dim]")

        # Generate bot response
        try:
            response = await bot.generate_response(conversation)
            conversation.add_message("girl", response)
            console.print(f"[bold magenta]GIRL[/bold magenta]: {response}\n")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

    # Final evaluation
    console.print("\n[bold]Final Evaluation:[/bold]")
    score, issues = evaluator.evaluate(conversation)
    console.print(f"Score: {score}/100")
    if issues:
        for issue in issues:
            console.print(f"  - {issue}")

    # Save conversation
    save_path = Path("data/test_conversations")
    save_path.mkdir(parents=True, exist_ok=True)
    with open(save_path / f"{conversation.id}.json", "w") as f:
        json.dump(conversation.to_dict(), f, indent=2)
    console.print(f"\n[green]Saved to {save_path / conversation.id}.json[/green]")


async def run_automated_test(num_conversations: int = 10, parallel: int = 5):
    """Run automated testing with AI playing both sides."""
    console.print(Panel.fit(
        f"[bold cyan]IG Bot Automated Tester[/bold cyan]\n"
        f"Running {num_conversations} simulated conversations\n"
        f"Parallel workers: {parallel}",
        title="Automated Testing Mode"
    ))

    results = {
        "total": num_conversations,
        "completed": 0,
        "success": 0,
        "dropped": 0,
        "errors": 0,
        "avg_score": 0,
        "conversations": []
    }

    semaphore = asyncio.Semaphore(parallel)

    async def run_single_conversation(conv_id: int) -> TestConversation:
        async with semaphore:
            bot = IGBotSimulator()
            guy = GuySimulator()
            evaluator = ConversationEvaluator()

            guy.generate_persona()

            conversation = TestConversation(
                id=f"auto_{conv_id}_{datetime.now().strftime('%H%M%S')}",
                metadata={"guy_persona": guy.persona}
            )

            try:
                # Guy opens
                opener = guy.generate_opener()
                conversation.add_message("guy", opener)

                # Check for location in opener
                location = bot.extract_location(opener)
                if location:
                    conversation.location = location
                    bot.location = location

                # Run conversation loop
                max_turns = 15
                for turn in range(max_turns):
                    # Girl responds
                    girl_response = await bot.generate_response(conversation)
                    conversation.add_message("girl", girl_response)

                    # Check for location in response
                    if not conversation.location:
                        location = bot.extract_location(girl_response)
                        if location:
                            conversation.location = location
                            bot.location = location

                    # Check if OF redirect happened
                    if "onlyfans" in girl_response.lower() or "my of" in girl_response.lower():
                        conversation.phase = ConversationPhase.OF_REDIRECT

                    # Guy responds (or drops)
                    if turn >= guy.persona["patience"]:
                        conversation.outcome = ConversationOutcome.DROP_LATE
                        break

                    guy_response = await guy.generate_response(conversation)
                    conversation.add_message("guy", guy_response)

                    # Check for conversation end signals
                    end_signals = ["bye", "later", "not interested", "nah", "pass"]
                    if any(s in guy_response.lower() for s in end_signals):
                        conversation.outcome = ConversationOutcome.DROP_LATE
                        break

                    # Check if he's interested in OF
                    if conversation.phase == ConversationPhase.OF_REDIRECT:
                        if any(w in guy_response.lower() for w in ["subscribe", "check it out", "how much", "link"]):
                            conversation.outcome = ConversationOutcome.SUCCESS
                            break

                if not conversation.outcome:
                    conversation.outcome = ConversationOutcome.SUCCESS if \
                        conversation.phase == ConversationPhase.OF_REDIRECT else \
                        ConversationOutcome.DROP_LATE

                # Evaluate
                score, issues = evaluator.evaluate(conversation)
                conversation.score = score
                conversation.issues = issues

            except Exception as e:
                conversation.outcome = ConversationOutcome.ERROR
                conversation.issues = [str(e)]
                conversation.score = 0

            return conversation

    # Run all conversations
    tasks = [run_single_conversation(i) for i in range(num_conversations)]
    conversations = await asyncio.gather(*tasks)

    # Aggregate results
    scores = []
    for conv in conversations:
        results["completed"] += 1
        results["conversations"].append(conv.to_dict())

        if conv.outcome == ConversationOutcome.SUCCESS:
            results["success"] += 1
        elif conv.outcome == ConversationOutcome.ERROR:
            results["errors"] += 1
        else:
            results["dropped"] += 1

        if conv.score:
            scores.append(conv.score)

    results["avg_score"] = sum(scores) / len(scores) if scores else 0

    # Display results
    table = Table(title="Test Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Total Conversations", str(results["total"]))
    table.add_row("Completed", str(results["completed"]))
    table.add_row("Success (OF redirect)", str(results["success"]))
    table.add_row("Dropped", str(results["dropped"]))
    table.add_row("Errors", str(results["errors"]))
    table.add_row("Average Score", f"{results['avg_score']:.1f}/100")
    table.add_row("Success Rate", f"{results['success']/results['completed']*100:.1f}%")

    console.print(table)

    # Show common issues
    all_issues = []
    for conv in conversations:
        all_issues.extend(conv.issues)

    if all_issues:
        console.print("\n[bold]Common Issues:[/bold]")
        from collections import Counter
        for issue, count in Counter(all_issues).most_common(10):
            console.print(f"  [{count}x] {issue}")

    # Save results
    save_path = Path("data/test_conversations")
    save_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    with open(save_path / f"batch_{timestamp}.json", "w") as f:
        json.dump(results, f, indent=2)

    console.print(f"\n[green]Results saved to {save_path}/batch_{timestamp}.json[/green]")

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="IG Conversation Tester")
    parser.add_argument("--mode", choices=["manual", "auto"], default="manual",
                       help="Testing mode: manual (you play guy) or auto (AI plays both)")
    parser.add_argument("--num", type=int, default=10,
                       help="Number of conversations for auto mode")
    parser.add_argument("--parallel", type=int, default=5,
                       help="Parallel conversations for auto mode")

    args = parser.parse_args()

    if args.mode == "manual":
        asyncio.run(run_manual_test())
    else:
        asyncio.run(run_automated_test(args.num, args.parallel))


if __name__ == "__main__":
    main()
