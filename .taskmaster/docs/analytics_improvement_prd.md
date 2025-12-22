# Analytics Improvement PRD: Deep Conversation Analysis

## Overview

Enhance the Chatter Copilot analytics pipeline to extract actionable insights from 13,582 parsed OnlyFans conversation screenshots. Focus on objection handling, conversation flow optimization, and evidence-based sales techniques.

## Goals

1. Build an objection → response playbook showing what actually works
2. Identify high-converting openers, closers, and phrases
3. Optimize pricing strategies by subscriber tier
4. Extract trainable patterns from top performers (Arvin, Leonel)

## Research Requirements

Before implementation, research the following to inform our analysis:

### Research Task 1: Text-Based Sales Psychology
- What psychological principles drive text/chat sales? (scarcity, social proof, reciprocity, etc.)
- How do these apply differently in intimate/adult content contexts?
- What makes someone buy via text vs in-person?

### Research Task 2: Objection Handling Best Practices
- Common sales objection categories (price, timing, trust, need)
- Proven response frameworks (feel-felt-found, acknowledge-bridge-close, etc.)
- How top salespeople handle "I can't afford it" or "maybe later"

### Research Task 3: OnlyFans/Creator Economy Sales Tactics
- What tactics do successful OnlyFans creators/agencies use?
- PPV pricing strategies that convert
- How do top agencies train their chatters?
- GFE (girlfriend experience) selling techniques

## Implementation Phases

### Phase 1: Data Quality Fixes

#### 1.1 Fix Tip Data Parsing
- Current bug: `outcome.tip_amount` contains lifetime tips from subscriber panel, not per-screenshot tips
- Solution: Create validation script to detect and flag suspicious tip values
- Flag conversations where tip_amount equals subscriber_stats.tips (indicates parsing error)
- For now, mark tip data as unreliable in all reports

#### 1.2 Approach Classification Refinement
- Current approaches are ambiguous (playful vs teasing unclear)
- Define clear criteria:
  - **Playful**: Light humor, jokes, casual banter, non-sexual fun
  - **Teasing**: Flirty, suggestive, withholding content to build desire, sexual tension
  - **Transactional**: Direct business talk, clear pricing, "here's what I have"
  - **Romantic**: GFE emotional connection, "I miss you", relationship simulation
  - **Direct**: Blunt, minimal buildup, straight to the offer
- Re-analyze a sample of conversations to validate classification accuracy

### Phase 2: Objection → Response Analysis (HIGH PRIORITY)

#### 2.1 Objection Pattern Extraction
Extract all subscriber messages containing objection indicators:
- **Price objections**: "too expensive", "can't afford", "too much", "that's a lot", "broke", "no money"
- **Timing objections**: "maybe later", "not now", "next time", "after payday", "when I get paid"
- **Trust objections**: "is it worth it", "how do I know", "what if", "scam"
- **Need objections**: "I don't need", "already have", "not interested"
- **Commitment objections**: "I'll think about it", "let me see", "not sure"

#### 2.2 Response Effectiveness Analysis
For each objection found:
1. Capture the creator's response(s) following the objection
2. Track whether a sale occurred within the next 5 messages
3. Calculate success rate per response pattern
4. Identify which chatters handle which objections best

#### 2.3 Build Objection Playbook
Create structured output:
```
Objection: "I can't afford it"
- Best Response (73% success): [example from Arvin]
- Alternative (61% success): [example from Leonel]
- What NOT to do (12% success): [example pattern]
- Tier-specific notes: Works better on MEDIUM tier, less on LOW
```

### Phase 3: Conversation Flow Analysis

#### 3.1 Opener Effectiveness Study
- Extract first creator message from each conversation thread
- Categorize opener types:
  - Question openers ("How's your day?")
  - Compliment openers ("I was thinking about you")
  - Teaser openers ("I have something special...")
  - Direct openers ("Want to see something?")
  - Re-engagement openers ("Haven't heard from you...")
- Calculate: opener type → sale conversion rate by tier

#### 3.2 Closing Phrase Analysis
- Find the last creator message before "unlocked" or sale confirmation
- Extract common closing patterns:
  - Scarcity closes ("Only sending this to you")
  - Urgency closes ("Just filmed this")
  - Value closes ("You're going to love this")
  - Soft closes ("Let me know if you want it")
- Calculate effectiveness by tier and approach

#### 3.3 Conversation Length Optimization
- Messages to first sale (by tier, by chatter)
- Optimal conversation length before pitching
- Point of diminishing returns (too much chat = no sale?)
- Compare: Arvin's 22.5 msgs/thread vs Billy's 93.4 msgs/thread

#### 3.4 Upsell Pattern Recognition
- After first sale, what triggers second sale?
- Time between sales
- What phrases/topics precede upsells?
- Multi-sale conversation analysis

### Phase 4: Price Point Optimization

#### 4.1 Price Distribution Analysis
- What PPV prices appear most frequently?
- Price vs conversion rate curve
- Optimal price points by tier:
  - NEW: What's the "gateway" price?
  - LOW: Maximum comfortable spend?
  - MEDIUM: Sweet spot range?
  - HIGH/WHALE: Premium pricing that works?

#### 4.2 Discount/Negotiation Analysis
- How often do chatters offer discounts?
- "I'll do it for $X" - success rate?
- Does negotiating hurt or help overall revenue?
- Best discount framing

#### 4.3 Bundle vs Single Analysis
- Bundle pricing ($50 for 3 videos) vs single ($25 each)
- Which converts better by tier?
- Bundle composition that works

### Phase 5: Language Pattern Extraction

#### 5.1 High-Conversion Phrase Mining
- Extract creator phrases that appear within 3 messages before sales
- Frequency analysis + success correlation
- Build "power phrases" dictionary
- Examples to find: urgency words, exclusivity language, desire triggers

#### 5.2 Subscriber Mood Indicators
- What subscriber words indicate buying intent? ("I want", "show me", "how much")
- What words indicate they won't buy? ("just looking", "maybe", "idk")
- Build qualification keyword lists

#### 5.3 Conversation Topic Analysis
- What topics lead to sales? (compliments, fantasies, personal connection)
- Topic progression patterns in successful conversations
- What do top chatters talk about vs low performers?

## Output Deliverables

### 1. Objection Handling Playbook (Markdown + JSON)
- Categorized objections with best responses
- Success rates and examples
- Chatter-specific techniques

### 2. Conversation Flow Guide
- Opener templates by tier
- Closing phrase templates
- Optimal conversation structure

### 3. Pricing Strategy Guide
- Price point recommendations by tier
- Discount strategy
- Bundle recommendations

### 4. Language Pattern Database (JSON)
- High-conversion phrases
- Qualification keywords
- Red flag indicators

### 5. Enhanced Chatter Profiles
- Per-chatter strengths (who handles which objections best)
- Style recommendations based on data

## Technical Implementation

### New Scripts to Create
- `scripts/analysis/objection_analysis.py` - Phase 2 implementation
- `scripts/analysis/conversation_flow.py` - Phase 3 implementation
- `scripts/analysis/pricing_analysis.py` - Phase 4 implementation
- `scripts/analysis/phrase_extraction.py` - Phase 5 implementation

### Data Structures
```python
@dataclass
class ObjectionInstance:
    objection_text: str
    objection_type: str  # price, timing, trust, need, commitment
    response_text: str
    response_chatter: str
    resulted_in_sale: bool
    messages_to_sale: int
    subscriber_tier: str

@dataclass
class ConversationFlow:
    opener_type: str
    opener_text: str
    messages_to_first_sale: int
    closing_phrase: str
    total_sales: float
    subscriber_tier: str
```

## Success Metrics

- Objection playbook covers 80%+ of observed objections
- Can identify statistically significant patterns (n>30 per category)
- Actionable recommendations for each subscriber tier
- Clear "do this, not that" guidance based on data

## Dependencies

- Existing parsed conversation data (13,582 screenshots, 1,295 threads)
- Current analysis infrastructure (data_loader, statistical_analysis)
- Research findings to inform pattern recognition
