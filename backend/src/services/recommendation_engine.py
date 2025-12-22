"""
Recommendation Engine Core

Analyzes chatter situations and provides recommendations based on:
- Training handbook content
- Gambit templates
- Similar conversation examples
- Pricing guidelines
"""

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class FunnelStage(str, Enum):
    """Stages of the sales funnel."""
    OPENING = "opening"
    QUALIFYING = "qualifying"
    TRANSITIONING = "transitioning"
    SELLING = "selling"
    AFTERCARE = "aftercare"
    UNKNOWN = "unknown"


class SubscriberType(str, Enum):
    """Types of subscribers based on spending patterns."""
    NEW = "new"  # Just subscribed, unknown potential
    LOW_SPENDER = "low_spender"  # Spends occasionally, small amounts
    MID_TIER = "mid_tier"  # Regular spender, moderate amounts
    HIGH_ROLLER = "high_roller"  # Consistent big spender
    WHALE = "whale"  # Top tier, spends heavily
    INACTIVE = "inactive"  # Was active, now dormant


@dataclass
class SituationAnalysis:
    """Analysis of a chatter's current situation."""
    funnel_stage: FunnelStage
    subscriber_type: SubscriberType
    opportunity: str
    key_signals: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class GambitRecommendation:
    """A recommended gambit to use."""
    id: str
    name: str
    category: str
    relevance_score: float
    reason: str
    phases: dict[str, str]


@dataclass
class PricingGuidance:
    """Pricing recommendations based on subscriber profile."""
    recommended_first_price: float
    recommended_range: tuple[float, float]
    reasoning: str
    tips: list[str]


@dataclass
class RecommendationResponse:
    """Complete recommendation response."""
    assessment: SituationAnalysis
    recommended_action: str
    gambits: list[GambitRecommendation]
    pricing_guidance: PricingGuidance
    handbook_tips: list[str]


class KnowledgeBase:
    """Loads and manages the knowledge base data."""

    def __init__(self, knowledge_base_dir: str | Path = "data/knowledge_base"):
        self.kb_dir = Path(knowledge_base_dir)
        self.handbook_sections: list[dict] = []
        self.gambits: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Load knowledge base from JSON files."""
        handbook_file = self.kb_dir / "handbook_sections.json"
        gambits_file = self.kb_dir / "gambits.json"

        if handbook_file.exists():
            with open(handbook_file, "r", encoding="utf-8") as f:
                self.handbook_sections = json.load(f)

        if gambits_file.exists():
            with open(gambits_file, "r", encoding="utf-8") as f:
                self.gambits = json.load(f)

    def search_handbook(self, query: str, limit: int = 5) -> list[dict]:
        """Simple keyword search in handbook sections."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored = []
        for section in self.handbook_sections:
            content_lower = section.get("content", "").lower()
            title_lower = section.get("title", "").lower()

            # Score based on keyword matches
            score = 0
            for word in query_words:
                if word in title_lower:
                    score += 3
                if word in content_lower:
                    score += content_lower.count(word)

            if score > 0:
                scored.append((score, section))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored[:limit]]

    def get_gambits_by_category(self, category: str) -> list[dict]:
        """Get gambits filtered by category."""
        return [g for g in self.gambits if g.get("category") == category]

    def get_all_gambits(self) -> list[dict]:
        """Get all gambits."""
        return self.gambits


class SituationAnalyzer:
    """Analyzes user input to determine funnel stage and subscriber type."""

    # Keywords for funnel stage detection
    STAGE_KEYWORDS = {
        FunnelStage.OPENING: [
            "new sub", "just subscribed", "first message", "opener",
            "haven't talked", "introduce", "starting"
        ],
        FunnelStage.QUALIFYING: [
            "getting to know", "asking questions", "building rapport",
            "commonalities", "fluff", "chatting", "learning about"
        ],
        FunnelStage.TRANSITIONING: [
            "ready to sell", "moving to", "transition", "escalate",
            "getting sexual", "flirty", "warming up", "about to pitch"
        ],
        FunnelStage.SELLING: [
            "selling", "ppv", "tip", "sent content", "asking for money",
            "price", "buy", "purchase", "offering", "pitch"
        ],
        FunnelStage.AFTERCARE: [
            "after", "bought", "purchased", "post", "thanked",
            "following up", "check in", "came back"
        ],
    }

    # Keywords for subscriber type detection
    SUBSCRIBER_KEYWORDS = {
        SubscriberType.NEW: [
            "new", "just subscribed", "first time", "never bought",
            "don't know", "haven't spent"
        ],
        SubscriberType.LOW_SPENDER: [
            "rarely buys", "cheap", "broke", "student", "tight budget",
            "only spent a little", "small amounts"
        ],
        SubscriberType.MID_TIER: [
            "regular", "sometimes buys", "moderate", "decent spender",
            "buys occasionally"
        ],
        SubscriberType.HIGH_ROLLER: [
            "good spender", "regular buyer", "spends well", "high value",
            "vip", "loyal spender"
        ],
        SubscriberType.WHALE: [
            "whale", "big spender", "thousands", "huge tipper",
            "drops hundreds", "sugar daddy"
        ],
        SubscriberType.INACTIVE: [
            "inactive", "ghost", "silent", "hasn't responded",
            "went cold", "dormant", "mia"
        ],
    }

    def analyze(self, user_input: str) -> SituationAnalysis:
        """Analyze user input to determine situation."""
        input_lower = user_input.lower()

        # Detect funnel stage
        funnel_stage = self._detect_funnel_stage(input_lower)

        # Detect subscriber type
        subscriber_type = self._detect_subscriber_type(input_lower)

        # Extract key signals
        key_signals = self._extract_signals(input_lower)

        # Identify opportunity
        opportunity = self._identify_opportunity(input_lower, funnel_stage, subscriber_type)

        # Identify risks
        risks = self._identify_risks(input_lower)

        return SituationAnalysis(
            funnel_stage=funnel_stage,
            subscriber_type=subscriber_type,
            opportunity=opportunity,
            key_signals=key_signals,
            risks=risks,
        )

    def _detect_funnel_stage(self, text: str) -> FunnelStage:
        """Detect funnel stage from text."""
        scores = {stage: 0 for stage in FunnelStage}

        for stage, keywords in self.STAGE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[stage] += 1

        max_stage = max(scores, key=scores.get)
        return max_stage if scores[max_stage] > 0 else FunnelStage.UNKNOWN

    def _detect_subscriber_type(self, text: str) -> SubscriberType:
        """Detect subscriber type from text."""
        scores = {stype: 0 for stype in SubscriberType}

        for stype, keywords in self.SUBSCRIBER_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    scores[stype] += 1

        # Also check for spending amounts
        money_match = re.search(r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if money_match:
            amount = float(money_match.group(1).replace(',', ''))
            if amount > 1000:
                scores[SubscriberType.WHALE] += 2
            elif amount > 200:
                scores[SubscriberType.HIGH_ROLLER] += 2
            elif amount > 50:
                scores[SubscriberType.MID_TIER] += 1
            else:
                scores[SubscriberType.LOW_SPENDER] += 1

        max_type = max(scores, key=scores.get)
        return max_type if scores[max_type] > 0 else SubscriberType.NEW

    def _extract_signals(self, text: str) -> list[str]:
        """Extract key signals from the situation."""
        signals = []

        # Duration signals
        if re.search(r'\d+\s*(min|minute|hour)', text):
            signals.append("Active conversation in progress")

        # Engagement signals
        if any(word in text for word in ["engaged", "responding", "interested", "flirty"]):
            signals.append("Subscriber showing engagement")

        # Question signals
        if any(word in text for word in ["asked", "asking", "wants to know", "curious"]):
            signals.append("Subscriber asking questions - good sign")

        # Buying signals
        if any(word in text for word in ["want", "interested in", "can i see", "show me"]):
            signals.append("Potential buying interest detected")

        # Resistance signals
        if any(word in text for word in ["broke", "can't afford", "too expensive", "maybe later"]):
            signals.append("Price resistance - may need to adjust approach")

        return signals[:5]

    def _identify_opportunity(self, text: str, stage: FunnelStage, sub_type: SubscriberType) -> str:
        """Identify the main opportunity in this situation."""
        if stage == FunnelStage.QUALIFYING:
            return "Build connection and identify subscriber preferences"
        elif stage == FunnelStage.TRANSITIONING:
            return "Perfect time to introduce a transitional gambit"
        elif stage == FunnelStage.SELLING:
            if sub_type == SubscriberType.WHALE:
                return "High-value opportunity - focus on premium content"
            else:
                return "Ready for a sale - match offer to subscriber profile"
        elif stage == FunnelStage.OPENING:
            return "Fresh start - focus on making a great first impression"
        else:
            return "Assess subscriber interest and re-engage"

    def _identify_risks(self, text: str) -> list[str]:
        """Identify potential risks in the situation."""
        risks = []

        if any(word in text for word in ["broke", "no money", "can't afford"]):
            risks.append("Subscriber claims financial constraints")

        if any(word in text for word in ["busy", "gtg", "later", "at work"]):
            risks.append("Limited time window - act efficiently")

        if any(word in text for word in ["not interested", "just looking", "maybe"]):
            risks.append("Low buying intent - focus on building value first")

        return risks[:3]


class GambitSelector:
    """Selects appropriate gambits based on situation analysis."""

    def __init__(self, knowledge_base: KnowledgeBase):
        self.kb = knowledge_base

    def select_gambits(
        self,
        analysis: SituationAnalysis,
        limit: int = 3
    ) -> list[GambitRecommendation]:
        """Select the best gambits for the situation."""
        recommendations = []

        all_gambits = self.kb.get_all_gambits()

        # Score each gambit based on relevance to situation
        for gambit in all_gambits:
            score, reason = self._score_gambit(gambit, analysis)
            if score > 0:
                recommendations.append(GambitRecommendation(
                    id=gambit.get("id", ""),
                    name=gambit.get("name", ""),
                    category=gambit.get("category", ""),
                    relevance_score=score,
                    reason=reason,
                    phases=gambit.get("phases", {}),
                ))

        # Sort by score and return top N
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        return recommendations[:limit]

    def _score_gambit(self, gambit: dict, analysis: SituationAnalysis) -> tuple[float, str]:
        """Score a gambit based on how well it matches the situation."""
        score = 0.0
        reasons = []

        category = gambit.get("category", "")

        # Category matching
        if analysis.funnel_stage == FunnelStage.TRANSITIONING:
            if category == "transitional":
                score += 0.5
                reasons.append("Good for transitioning to selling")

        if analysis.subscriber_type == SubscriberType.WHALE:
            if category == "captain_save_a_ho":
                score += 0.4
                reasons.append("Effective with high-value subscribers")

        if analysis.funnel_stage == FunnelStage.QUALIFYING:
            if category == "emotional_connection":
                score += 0.4
                reasons.append("Builds emotional connection during qualifying")

        # Check if gambit has complete phases
        phases = gambit.get("phases", {})
        if len(phases) >= 3:
            score += 0.2
            reasons.append("Complete gambit template")

        # Base score for having any gambit available
        if score == 0 and phases:
            score = 0.1
            reasons.append("Alternative option")

        reason = "; ".join(reasons) if reasons else "General recommendation"
        return score, reason


class PricingAdvisor:
    """Provides pricing recommendations based on handbook guidelines."""

    # Pricing rules from the handbook
    PRICING_RULES = {
        SubscriberType.NEW: {
            "first_price": 5,
            "range": (3, 10),
            "tip": "First sale should be $5 or less to build trust"
        },
        SubscriberType.LOW_SPENDER: {
            "first_price": 10,
            "range": (5, 20),
            "tip": "Keep prices low, build value over time"
        },
        SubscriberType.MID_TIER: {
            "first_price": 15,
            "range": (10, 50),
            "tip": "Can handle moderate prices, match to their spending pattern"
        },
        SubscriberType.HIGH_ROLLER: {
            "first_price": 25,
            "range": (20, 100),
            "tip": "Can handle higher prices, don't undersell yourself"
        },
        SubscriberType.WHALE: {
            "first_price": 50,
            "range": (30, 500),
            "tip": "Premium pricing for premium subscribers"
        },
        SubscriberType.INACTIVE: {
            "first_price": 10,
            "range": (5, 25),
            "tip": "Win-back pricing - offer value to re-engage"
        },
    }

    def get_pricing(self, subscriber_type: SubscriberType, has_bought_before: bool = False) -> PricingGuidance:
        """Get pricing recommendation for subscriber type."""
        rules = self.PRICING_RULES.get(subscriber_type, self.PRICING_RULES[SubscriberType.NEW])

        tips = [
            rules["tip"],
            "Increase prices slowly after successful sales",
            "Never negotiate down more than 20%",
            "Bundle content for better perceived value",
        ]

        if has_bought_before:
            tips.append("Since they've bought before, you can price slightly higher")

        reasoning = f"Based on {subscriber_type.value} profile: {rules['tip']}"

        return PricingGuidance(
            recommended_first_price=rules["first_price"],
            recommended_range=rules["range"],
            reasoning=reasoning,
            tips=tips,
        )


class RecommendationEngine:
    """Main recommendation engine combining all components."""

    def __init__(self, knowledge_base_dir: str | Path = "data/knowledge_base"):
        self.kb = KnowledgeBase(knowledge_base_dir)
        self.analyzer = SituationAnalyzer()
        self.gambit_selector = GambitSelector(self.kb)
        self.pricing_advisor = PricingAdvisor()

    def get_recommendation(self, user_input: str) -> RecommendationResponse:
        """
        Get a complete recommendation based on user input.

        Args:
            user_input: Description of the current situation

        Returns:
            Complete recommendation with assessment, gambits, and pricing
        """
        # Analyze the situation
        analysis = self.analyzer.analyze(user_input)

        # Select gambits
        gambits = self.gambit_selector.select_gambits(analysis)

        # Get pricing guidance
        pricing = self.pricing_advisor.get_pricing(analysis.subscriber_type)

        # Get handbook tips
        handbook_results = self.kb.search_handbook(user_input, limit=3)
        handbook_tips = []
        for result in handbook_results:
            key_points = result.get("key_points", [])
            if key_points:
                handbook_tips.extend(key_points[:2])
        handbook_tips = handbook_tips[:5]

        # Generate recommended action
        recommended_action = self._generate_action(analysis, gambits)

        return RecommendationResponse(
            assessment=analysis,
            recommended_action=recommended_action,
            gambits=gambits,
            pricing_guidance=pricing,
            handbook_tips=handbook_tips,
        )

    def _generate_action(self, analysis: SituationAnalysis, gambits: list[GambitRecommendation]) -> str:
        """Generate a recommended action based on analysis."""
        if analysis.funnel_stage == FunnelStage.OPENING:
            return "Focus on building initial rapport. Send a personalized opener that references something unique about them."

        elif analysis.funnel_stage == FunnelStage.QUALIFYING:
            return "Continue building commonalities. Ask open-ended questions to learn what they're into."

        elif analysis.funnel_stage == FunnelStage.TRANSITIONING:
            if gambits:
                return f"Perfect timing to transition! Try the '{gambits[0].name}' gambit to smoothly move toward selling."
            return "Use a transitional gambit to shift the conversation toward intimacy."

        elif analysis.funnel_stage == FunnelStage.SELLING:
            return f"Ready to close. Offer content at ${analysis.subscriber_type.value} pricing range. Build urgency."

        elif analysis.funnel_stage == FunnelStage.AFTERCARE:
            return "Great job on the sale! Now focus on aftercare - check in, make them feel valued, set up the next purchase."

        return "Assess the situation and re-engage with the subscriber."

    def to_dict(self, response: RecommendationResponse) -> dict:
        """Convert response to dictionary for API."""
        return {
            "assessment": {
                "funnel_stage": response.assessment.funnel_stage.value,
                "subscriber_type": response.assessment.subscriber_type.value,
                "opportunity": response.assessment.opportunity,
                "key_signals": response.assessment.key_signals,
                "risks": response.assessment.risks,
                "confidence": response.assessment.confidence,
            },
            "recommended_action": response.recommended_action,
            "gambits": [
                {
                    "id": g.id,
                    "name": g.name,
                    "category": g.category,
                    "relevance_score": g.relevance_score,
                    "reason": g.reason,
                    "phases": g.phases,
                }
                for g in response.gambits
            ],
            "pricing_guidance": {
                "recommended_first_price": response.pricing_guidance.recommended_first_price,
                "recommended_range": list(response.pricing_guidance.recommended_range),
                "reasoning": response.pricing_guidance.reasoning,
                "tips": response.pricing_guidance.tips,
            },
            "handbook_tips": response.handbook_tips,
        }


# CLI for testing
if __name__ == "__main__":
    import sys

    engine = RecommendationEngine()

    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
    else:
        user_input = "He's been subbed for 3 months, spent $200 total, we've been flirting for 20 mins, he asked what I'm doing tonight"

    print(f"\n[Input]: {user_input}\n")

    response = engine.get_recommendation(user_input)
    result = engine.to_dict(response)

    print(json.dumps(result, indent=2))
