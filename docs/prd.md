# Chatter Copilot - Product Requirements Document

## Overview

Chatter Copilot is an AI-powered assistant that helps OnlyFans chatters make more sales by providing real-time recommendations based on a proprietary training methodology and 13,000+ real conversation examples.

**The core value proposition:** New chatters perform like experienced ones. Experienced chatters never get stuck.

### What We Have

| Asset | Count | Description |
|-------|-------|-------------|
| Training handbook | ~70 pages | Structured methodology: Mindset → Opening → Qualifying → Transitioning → Selling |
| Gambits library | 25+ templates | Pre-written conversation sequences with clear phases |
| Conversation screenshots | 13,582 | Real OF chats with subscriber metadata and chatter annotations |
| Markdown documentation | 1,586 files | Organized Notion export with tactics from top performers |

### What We're Building

A web-based copilot that chatters use alongside OnlyFans. They describe their current situation, and the AI recommends:
- What phase of the funnel they're in
- Which gambit or technique to use next
- Relevant examples from real conversations
- Pricing guidance based on subscriber profile

---

## Phase 0: Data Processing Pipeline

**This must be completed before any product development.**

### 0.1 OCR Extraction

**Input:** 13,582 PNG screenshots from `Chatter Marines Field Handbook/`

**Process:**
1. Run all images through OCR API (Google Cloud Vision or AWS Textract)
2. Extract raw text from each image
3. Store raw output with source file reference

**Output:** JSON files with raw OCR text mapped to original image paths

**Estimated cost:** ~$20-25 in API fees
**Estimated time:** 2-4 hours (automated)

### 0.2 Conversation Parsing

**Input:** Raw OCR output

**Process:**
1. Identify message boundaries (blue bubbles = model, white = subscriber)
2. Extract timestamps
3. Parse fan metadata panel (subscription length, tips, total spent, buy rate, location)
4. Extract sequence numbers from hand-drawn annotations
5. Handle edge cases (PPV "View message" links, system messages)

**Output:** Structured conversation objects:
```json
{
  "source_image": "Example conversations/Arvin/Executing discounted sales/image 3.png",
  "messages": [
    {"speaker": "model", "text": "Do you have any plans for Thanksgiving my love?", "timestamp": "1:38 PM"},
    {"speaker": "subscriber", "text": "Ill probably just spend it at the house...", "timestamp": "1:40 PM"}
  ],
  "subscriber_profile": {
    "months_subscribed": 11,
    "total_tips": 4250,
    "total_spent": 8670,
    "buy_rate": 0.52,
    "location": "Georgia, US",
    "local_time": "1:08 AM",
    "last_paid": "7/30"
  },
  "fan_notes": "HE SAID HE's NOT GONNA SPEND for a while AFTER HE TIPPED THE 400$...",
  "sequence_number": 3
}
```

**Estimated time:** 2-3 days development + testing

### 0.3 Context Linking

**Input:** Parsed conversations + markdown documentation

**Process:**
1. Match screenshot sequences to their parent markdown files
2. Extract chatter annotations/explanations from surrounding text
3. Group related screenshots into complete conversation flows

**Output:** Conversations with full context:
```json
{
  "conversation_id": "arvin_discounted_sales_001",
  "title": "Executing discounted sales",
  "chatter": "Arvin",
  "screenshots": [...],  // array of parsed conversations in sequence
  "chatter_explanation": "Still working this VIP and closing a deal for a Black Friday customized request...",
  "category": "selling/discounts"
}
```

**Estimated time:** 1-2 days

### 0.4 LLM Enrichment

**Input:** Structured conversations with context

**Process:**
1. Send each conversation to LLM for analysis
2. Extract: technique used, funnel stage, outcome, key moments
3. Map to handbook sections and gambits
4. Generate searchable tags

**Output:** Enriched conversation records:
```json
{
  "conversation_id": "arvin_discounted_sales_001",
  "analysis": {
    "funnel_stage": "selling",
    "techniques_used": ["discount_framing", "urgency", "payment_plan"],
    "outcome": "sale",
    "sale_amount": 600,
    "subscriber_type": "whale",
    "key_insight": "Offered payment plan for high-value custom, secured $200 deposit"
  },
  "related_handbook_sections": ["Selling/Whales", "Selling/Creating the scenario"],
  "related_gambits": [],
  "tags": ["vip", "custom_content", "black_friday", "payment_plan", "high_ticket"]
}
```

**Estimated cost:** ~$50-100 in API fees (depending on model)
**Estimated time:** 1-2 days (mostly automated)

### 0.5 Knowledge Base Construction

**Input:** All enriched data + handbook markdown + gambits

**Process:**
1. Parse all handbook markdown into structured sections
2. Parse all gambits into templates with phases
3. Generate embeddings for semantic search
4. Build vector database index
5. Create relational links (technique → examples, gambit → conversations)

**Output:** Searchable knowledge base with:
- Handbook content (chunked and embedded)
- Gambit templates (structured)
- Conversation examples (enriched and embedded)
- Subscriber profile patterns

**Estimated time:** 2-3 days

---

## Phase 1: MVP Product

### 1.1 Core User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  CHATTER COPILOT - MVP                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [Describe your situation]                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ "He's been subbed for 3 months, spent $200 total,       │   │
│  │  we've been flirting for 20 mins, he asked what I'm     │   │
│  │  doing tonight"                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  [Get Recommendations]                                          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ASSESSMENT                                                     │
│  ├─ Funnel Stage: Qualifying → Ready to Transition              │
│  ├─ Subscriber Type: Mid-tier ($200 in 3mo = engaged)           │
│  └─ Opportunity: His question is a natural transition point     │
│                                                                 │
│  RECOMMENDED ACTION                                             │
│  Use a transitional gambit. "What are you doing tonight"        │
│  is a perfect opening for the "Gentle or Rough" gambit.         │
│                                                                 │
│  GAMBIT: Gentle or Rough                                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Opening: "random q but do u think it's better when      │   │
│  │ someone is super gentle or when they get a little       │   │
│  │ rough?"                                                  │   │
│  │                                                          │   │
│  │ Rooting: "i saw this scene where the guy went from      │   │
│  │ being all soft n gentle to kinda rough..."              │   │
│  │ [See full gambit...]                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  SIMILAR SUCCESSFUL CONVERSATION                                │
│  Arvin with subscriber (11mo, $8.6K spent, 52% buy rate)       │
│  [View conversation →]                                          │
│                                                                 │
│  PRICING GUIDANCE                                               │
│  First sale: $5-10 (he hasn't bought yet)                      │
│  After first purchase: Increase slowly per handbook             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 MVP Features

| Feature | Description | Priority |
|---------|-------------|----------|
| Situation input | Free-text description of current conversation state | P0 |
| Funnel assessment | AI identifies current stage and subscriber type | P0 |
| Gambit recommendations | Suggests relevant gambits with full templates | P0 |
| Example conversations | Shows similar successful conversations | P0 |
| Pricing guidance | Recommends pricing based on subscriber profile | P1 |
| Handbook search | Search training material directly | P1 |
| Gambit browser | Browse all gambits by category | P1 |

### 1.3 Technical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│                    (Next.js / React)                            │
│         Simple web app, works in browser tab                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                          API                                    │
│                   (Python / FastAPI)                            │
│                                                                 │
│  /recommend    - Main copilot endpoint                          │
│  /gambits      - List/search gambits                            │
│  /examples     - Search conversation examples                   │
│  /handbook     - Search handbook content                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     KNOWLEDGE BASE                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Vector DB  │  │  PostgreSQL  │  │     LLM      │          │
│  │  (Embeddings │  │  (Structured │  │  (Analysis   │          │
│  │   + Search)  │  │    Data)     │  │   + Recs)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                 │
│  - Handbook chunks          - Conversations      - Claude/GPT   │
│  - Gambit templates         - Subscriber data    - For recs     │
│  - Conversation text        - Outcomes           - For analysis │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 1.4 Tech Stack (Recommended)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Frontend | Next.js 14 | Fast, simple, good DX |
| Backend | Python + FastAPI | Good for AI/ML, fast APIs |
| Vector DB | ChromaDB or Pinecone | Semantic search over content |
| Database | PostgreSQL | Structured data, relationships |
| LLM | Claude API (Anthropic) | Best for nuanced recommendations |
| Hosting | Vercel (FE) + Railway (BE) | Simple deployment |

---

## Phase 2: Enhanced Features

*After MVP is validated with team*

### 2.1 Conversation Paste Mode

Instead of describing the situation, chatter pastes the actual conversation text. AI parses and analyzes directly.

### 2.2 Quick Actions

Pre-built buttons for common scenarios:
- "He says he's broke"
- "He went silent after my pitch"
- "He's asking for free content"
- "He wants to negotiate price"

### 2.3 Subscriber Profile Input

Structured input for subscriber data:
- Months subscribed
- Total spent
- Buy rate
- Last purchase

More accurate recommendations based on profile matching.

### 2.4 Favorites & History

- Save favorite gambits
- Track which recommendations were used
- View conversation history

### 2.5 Performance Analytics

- Which gambits are being used most
- Success rate tracking (if outcome is logged)
- Team-wide insights

---

## Phase 3: Future Possibilities

*Only if Phase 1-2 succeed*

| Feature | Description |
|---------|-------------|
| Mobile app | iOS/Android for chatters on the go |
| Browser extension | Overlay on OF that reads conversations directly |
| API licensing | Let other agencies integrate your methodology |
| Training mode | AI roleplays as subscriber, chatter practices |
| Team management | Admin dashboard, multiple users, permissions |

---

## Success Metrics

### MVP Success Criteria

| Metric | Target |
|--------|--------|
| Chatters using daily | 80%+ of team |
| Time to first sale (new chatters) | Reduce by 30% |
| Average sale value | Increase by 10% |
| Chatter satisfaction | "Would not want to work without it" |

### Qualitative Signals

- Chatters reference it during shifts without being told
- New hires ask for access immediately
- Experienced chatters discover gambits they forgot about
- Reduction in "I don't know what to say" moments

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| OCR quality issues | Data is unusable | Test on sample first, build error handling |
| Chatters become copy-paste robots | Quality drops | Include "adapt this to your voice" guidance |
| Recommendations are generic | No value added | Heavy focus on specific examples, not just theory |
| Tool is too slow | Chatters won't use it | Optimize response time < 2 seconds |
| Data is too messy to structure | Phase 0 fails | Manual review of sample set, adjust parsing |

---

## Timeline Overview

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 0: Data Processing | 2 weeks | Structured knowledge base |
| Phase 1: MVP | 2 weeks | Working copilot for team |
| Testing & Iteration | 1-2 weeks | Refined based on feedback |
| Phase 2: Enhancements | 2-3 weeks | Full feature set |

**Total to production MVP: 4-6 weeks**

---

## Immediate Next Steps

1. **Sample OCR Test**: Run 50 screenshots through OCR, validate quality
2. **Parser Prototype**: Build conversation parser, test on sample
3. **Validate Data Quality**: Review parsed output, identify edge cases
4. **Knowledge Base Schema**: Finalize data structures
5. **Begin Phase 0**: Full data processing pipeline

---

## Appendix A: Handbook Structure

```
Chatter Marines Field Handbook/
├── Mindset/                    # 9 articles on psychology
├── Opening/                    # 3 articles on openers
├── Qualifying, Commonalities/  # 10 articles on building rapport
├── Transitioning to selling/   # 7 articles on moving to sales
├── Selling/                    # 13 articles on closing
├── Gambits/                    # 25+ conversation templates
│   ├── Transitional gambits/   # 8 templates
│   ├── Captain Save A Ho/      # 10 templates
│   └── Emotional connection/   # 7 templates
├── Example conversations/      # Real conversations by chatter
│   ├── Arvin/
│   ├── Leonel/
│   ├── Marvin/
│   └── ...
└── Ideas and tactics/          # Per-chatter tactics
```

## Appendix B: Gambit Structure

Each gambit follows this format:

```
1. Opening Question     - Hook to start the conversation thread
2. Rooting             - Reason for asking (makes it feel natural)
3. Request for Input   - Get them engaged/responding
4. Hypnotic Afterthought - Sensory/emotional escalation
5. Seductive Tease     - Transition to potential sale
```

## Appendix C: Subscriber Metadata Fields

Available from OF screenshots:
- `months_subscribed`: Duration of subscription
- `total_tips`: Sum of all tips
- `total_spent`: Total money spent (tips + PPV)
- `buy_rate`: Percentage of PPV purchased (e.g., 116/224 = 52%)
- `location`: Country/region and timezone
- `local_time`: Current time for subscriber
- `last_paid`: Date of last payment
- `fan_notes`: Chatter's notes about this subscriber
- `renew_status`: Whether auto-renew is on/off
