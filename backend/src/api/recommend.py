"""
Recommendation API endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from ..services.recommendation_engine import RecommendationEngine, FunnelStage, SubscriberType

router = APIRouter(prefix="/recommend", tags=["recommendations"])

# Initialize the recommendation engine
engine = RecommendationEngine()


class RecommendationRequest(BaseModel):
    """Request for a recommendation."""
    situation: str = Field(
        ...,
        description="Description of your current situation with the subscriber",
        examples=["He's been subbed for 3 months, spent $200, we've been flirting for 20 mins"]
    )
    subscriber_months: Optional[int] = Field(
        None,
        description="Months the subscriber has been subscribed"
    )
    subscriber_spent: Optional[float] = Field(
        None,
        description="Total amount the subscriber has spent"
    )
    has_bought_before: Optional[bool] = Field(
        None,
        description="Whether the subscriber has made a purchase before"
    )


class QuickActionRequest(BaseModel):
    """Request for a quick action recommendation."""
    scenario: str = Field(
        ...,
        description="Common scenario identifier",
        examples=["broke", "silent", "wants_free", "negotiating"]
    )


@router.post("/")
async def get_recommendation(request: RecommendationRequest) -> dict:
    """
    Get AI-powered recommendations for your current situation.

    Returns:
    - Assessment of the funnel stage and subscriber type
    - Recommended next action
    - Relevant gambits to try
    - Pricing guidance
    - Tips from the handbook
    """
    try:
        response = engine.get_recommendation(request.situation)
        return engine.to_dict(response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quick")
async def quick_action(request: QuickActionRequest) -> dict:
    """
    Get quick recommendations for common scenarios.

    Supported scenarios:
    - broke: Subscriber says they're broke
    - silent: Subscriber went silent
    - wants_free: Subscriber asking for free content
    - negotiating: Subscriber trying to negotiate price
    - not_interested: Subscriber seems uninterested
    - after_sale: Just made a sale, what's next
    """
    scenario_prompts = {
        "broke": "The subscriber says they're broke and can't afford to buy anything right now",
        "silent": "The subscriber went silent after I pitched content, they're not responding",
        "wants_free": "The subscriber is asking for free content and won't pay",
        "negotiating": "The subscriber is trying to negotiate the price down significantly",
        "not_interested": "The subscriber says they're just looking and not interested in buying",
        "after_sale": "I just made a sale and the subscriber bought my content, what should I do now for aftercare",
    }

    prompt = scenario_prompts.get(request.scenario)
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown scenario: {request.scenario}. Supported: {list(scenario_prompts.keys())}"
        )

    response = engine.get_recommendation(prompt)
    return engine.to_dict(response)


@router.get("/gambits")
async def list_gambits(category: Optional[str] = None) -> dict:
    """
    List available gambits.

    Optional filter by category:
    - transitional
    - captain_save_a_ho
    - emotional_connection
    """
    gambits = engine.kb.get_all_gambits()

    if category:
        gambits = [g for g in gambits if g.get("category") == category]

    return {
        "total": len(gambits),
        "gambits": [
            {
                "id": g.get("id"),
                "name": g.get("name"),
                "category": g.get("category"),
                "phases": list(g.get("phases", {}).keys()),
            }
            for g in gambits
        ]
    }


@router.get("/gambits/{gambit_id}")
async def get_gambit(gambit_id: str) -> dict:
    """Get a specific gambit by ID with full content."""
    gambits = engine.kb.get_all_gambits()
    gambit = next((g for g in gambits if g.get("id") == gambit_id), None)

    if not gambit:
        raise HTTPException(status_code=404, detail=f"Gambit not found: {gambit_id}")

    return gambit


@router.get("/handbook/search")
async def search_handbook(q: str, limit: int = 5) -> dict:
    """
    Search the handbook for relevant content.

    Args:
        q: Search query
        limit: Max results to return (default 5)
    """
    results = engine.kb.search_handbook(q, limit=limit)
    return {
        "query": q,
        "total": len(results),
        "results": [
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "category": r.get("category"),
                "key_points": r.get("key_points", [])[:3],
                "word_count": r.get("word_count"),
            }
            for r in results
        ]
    }


@router.get("/pricing/{subscriber_type}")
async def get_pricing(subscriber_type: str) -> dict:
    """
    Get pricing guidance for a subscriber type.

    Subscriber types:
    - new
    - low_spender
    - mid_tier
    - high_roller
    - whale
    - inactive
    """
    try:
        sub_type = SubscriberType(subscriber_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid subscriber type: {subscriber_type}. Valid types: {[t.value for t in SubscriberType]}"
        )

    pricing = engine.pricing_advisor.get_pricing(sub_type)
    return {
        "subscriber_type": subscriber_type,
        "recommended_first_price": pricing.recommended_first_price,
        "recommended_range": list(pricing.recommended_range),
        "reasoning": pricing.reasoning,
        "tips": pricing.tips,
    }
