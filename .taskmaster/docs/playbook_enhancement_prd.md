# Playbook Enhancement PRD: Evidence-Based Training Materials

## Overview

Enhance all existing playbooks with concrete evidence:
1. **Real conversation examples** from the parsed data (most valuable)
2. **Statistical backing** with sample sizes and confidence
3. **Psychological research** citations where applicable

Current playbooks are outlines - they need to become training materials that chatters can actually learn from.

## Goals

1. Every claim backed by data or research
2. Real conversation excerpts showing techniques in action
3. "What to say" with actual successful examples
4. "What not to say" with actual failed examples
5. Context around examples (what came before/after)

## Playbooks to Enhance

### 1. Objection Handling Playbook
**Current state:** Has success rates and some response snippets
**Needs:**
- Full conversation context (5-10 messages before and after objection)
- Multiple examples per objection type
- Side-by-side comparison: successful vs failed responses
- Pattern analysis: what do successful responses have in common?

### 2. Tier-Specific Playbooks (NEW/LOW/MEDIUM/HIGH/WHALE)
**Current state:** Basic recommendations
**Needs:**
- Example conversations from each tier showing successful sales
- Price points that worked (with evidence)
- Opener → Sale full conversation flows
- Tier-specific language patterns

### 3. Chatter Style Playbooks (NEW)
**Current state:** chatter_analysis.md has stats but no examples
**Needs:**
- Top performer deep-dives (Arvin, Leonel, Billy)
- Their actual conversation techniques
- Side-by-side style comparison
- What makes them effective (with examples)

## Implementation Plan

### Phase 1: Conversation Example Extraction

Create a module to extract full conversation context:

```python
class ConversationExampleExtractor:
    def get_objection_with_context(objection_id, context_messages=5):
        """Get full conversation around an objection."""
        # Returns: messages before, objection, response, outcome

    def get_successful_sale_flow(tier, min_sale_amount):
        """Get full opener-to-close conversation for tier."""

    def get_technique_examples(technique_name, n=5):
        """Get examples of specific technique in action."""

    def compare_responses(objection_type, successful=True):
        """Get successful vs failed response comparisons."""
```

### Phase 2: Evidence Database

Create structured JSON with all evidence:

```json
{
  "objection_examples": {
    "price": {
      "successful": [
        {
          "context": ["msg1", "msg2", "msg3"],
          "objection": "I can't afford that",
          "response": "how much can u babe?",
          "outcome": {"sale": true, "amount": 2000},
          "chatter": "Mikko",
          "tier": "MEDIUM",
          "analysis": "Asked budget instead of defending price"
        }
      ],
      "failed": [...]
    }
  },
  "tier_examples": {...},
  "technique_examples": {...}
}
```

### Phase 3: Enhanced Playbook Generation

For each playbook section:

1. **Claim** → What we're recommending
2. **Data** → Statistics backing it (n=X, success rate, avg sale)
3. **Example** → Real conversation showing it in action
4. **Counter-example** → What NOT to do (with real failed attempt)
5. **Why it works** → Psychological principle or pattern analysis

Example enhanced section:

```markdown
## Handling "I can't afford it"

**Success Rate:** 45.8% (n=277 instances)
**Best Tier:** LOW (52.8%)

### The Technique: Ask Their Budget

Instead of defending your price, ask what they CAN afford.

**Example (Mikko, $2000 sale):**
> SUB: that's expensive...
> SUB: I don't have that much
> CREATOR: how much can u babe?
> SUB: I could do 500
> CREATOR: ok let me see what I can put together for you
> [... 3 messages later ...]
> SUB: ok 2000 works
> [SALE: $2000]

**Why it works:** Shifts from rejection to negotiation. Based on
Cialdini's commitment principle - once they state a number, they're
more likely to follow through.

**Counter-example (failed):**
> SUB: too expensive
> CREATOR: but it's really worth it I promise
> CREATOR: please?
> [NO SALE]

**Analysis:** Begging devalues the content and shows desperation.
```

### Phase 4: Research Integration

Add citations to psychological research:

- Cialdini's principles (reciprocity, scarcity, etc.)
- SPIN selling methodology (Situation, Problem, Implication, Need-payoff)
- Objection handling frameworks (Feel-Felt-Found, Acknowledge-Bridge-Close)
- Text-based persuasion research

### Phase 5: Validation

Before finalizing:
1. Verify all examples are real (from parsed data)
2. Confirm statistics with sample sizes
3. Have multiple examples per technique (not cherry-picked)
4. Include failure examples to show what doesn't work

## Technical Requirements

### New Scripts

1. `scripts/analysis/example_extractor.py`
   - Extract full conversation context
   - Find examples by criteria (tier, approach, outcome)
   - Format for playbook inclusion

2. `scripts/analysis/playbook_generator.py`
   - Generate enhanced playbooks from evidence database
   - Include markdown formatting for examples
   - Add statistics and citations

### Data Structures

```python
@dataclass
class ConversationExample:
    messages: List[Message]  # Full conversation
    highlight_start: int     # Where key technique starts
    highlight_end: int       # Where it ends
    outcome: Outcome
    tier: str
    chatter: str
    technique: str
    analysis: str            # Why this worked/failed

@dataclass
class PlaybookSection:
    title: str
    claim: str
    statistics: Dict         # n, success_rate, avg_sale
    examples: List[ConversationExample]
    counter_examples: List[ConversationExample]
    psychology: str          # Research backing
    templates: List[str]     # Suggested response templates
```

## Output Deliverables

### 1. Enhanced Objection Playbook
- 5 objection types, each with:
  - 3-5 successful examples with full context
  - 2-3 failed examples for contrast
  - Tier-specific variations
  - Psychology backing

### 2. Enhanced Tier Playbooks
- Each tier (NEW/LOW/MEDIUM/HIGH/WHALE) with:
  - 3-5 full sale conversation examples
  - Price point evidence
  - Opener analysis with examples
  - Closer analysis with examples

### 3. Chatter Technique Deep-Dives
- Top 3 performers (Arvin, Leonel, Billy):
  - 5+ conversation examples each
  - What makes their style effective
  - Teachable patterns

### 4. Evidence Database (JSON)
- All examples in structured format
- Enables future analysis and searching
- Can be used for AI training

## Success Criteria

1. Every recommendation has at least 3 real examples
2. All statistics include sample size (n=X)
3. Failed examples shown for each technique
4. Playbooks are long-form training materials, not outlines
5. New chatter could learn from reading them alone

## Priority Order

1. **Objection playbook enhancement** - You specifically asked for this
2. **Example extractor module** - Enables all other work
3. **Tier playbook enhancement** - High value
4. **Chatter deep-dives** - Learn from the best
