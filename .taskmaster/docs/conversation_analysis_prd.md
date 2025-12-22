# Chatter Training Data Analysis PRD

## Executive Summary

Analyze 13,579 parsed OnlyFans conversation screenshots to extract actionable training insights for chatters. The data consists of successful sales conversations submitted by chatters as examples of their work.

---

## 1. Data Understanding & Limitations

### 1.1 What We Have

| Field | Description | Example Values |
|-------|-------------|----------------|
| `messages[]` | Array of messages with role, text, timestamp | creator/subscriber roles |
| `subscriber_stats.total_spent` | Lifetime spend on this creator | $0 - $50,000+ |
| `subscriber_stats.tips` | Total tips given | $0 - $10,000+ |
| `subscriber_stats.subscription_status` | Current sub status | free, active, expired |
| `subscriber_stats.last_paid` | Last transaction date | Date string |
| `subscriber_stats.renew` | Auto-renew status | On/Off |
| `subscriber_stats.highest_purchase` | Largest single purchase | $5 - $500+ |
| `outcome.sale_in_screenshot` | Whether sale occurred | true/false |
| `outcome.sale_amount` | Amount of sale | $5 - $500+ |
| `outcome.tip_received` | Whether tip was received | true/false |
| `outcome.tip_amount` | Amount of tip | $5 - $500+ |
| `outcome.ppv_sent` | Whether PPV was sent | true/false |
| `outcome.technique_observed` | Technique used | teasing, transactional, etc. |
| `context.conversation_stage` | Current stage | opening, pitching, closing, etc. |
| `context.subscriber_mood` | Detected mood | eager, hesitant, flirty, etc. |
| `context.creator_approach` | Creator's approach | playful, teasing, romantic, etc. |

### 1.2 Critical Data Limitations

**Selection Bias (CRITICAL)**
- Instructions were: "Send a screenshot of a sale you made"
- This means **100% of data represents successful outcomes**
- We CANNOT calculate true conversion rates
- We can only analyze "what success looks like", not "what works vs what doesn't"

**Snapshot vs Full Conversation**
- Each screenshot is a snippet, not the full conversation thread
- Screenshots in the same folder likely represent the same conversation
- Subscriber stats show relationship context (months subscribed, total spent)

**Relationship Context**
- Many subscribers have existing relationships (high total_spent)
- A "sale" to a $10,000 whale is different from a sale to a new subscriber
- Must segment by subscriber tier to get meaningful insights

### 1.3 Folder Structure (Conversation Grouping)

```
data/parsed_conversations/
├── Example conversations/
│   ├── [Chatter Name]/
│   │   ├── [Conversation Title]/
│   │   │   ├── image.parsed.json
│   │   │   ├── image 1.parsed.json
│   │   │   ├── image 2.parsed.json  # Same folder = same conversation thread
│   │   │   └── ...
├── Ideas and tactics/
└── Selling/
```

---

## 2. Subscriber Segmentation

### 2.1 Tier Definitions

| Tier | total_spent Range | Description |
|------|-------------------|-------------|
| **New** | $0 or null | First-time or free subscriber |
| **Low** | $1 - $199 | Occasional buyer |
| **Medium** | $200 - $999 | Regular buyer |
| **High** | $1,000 - $4,999 | High-value subscriber |
| **Whale** | $5,000+ | Top-tier VIP |

### 2.2 Additional Segmentation Dimensions

- **Subscription Status**: free vs paid subscriber
- **Renew Status**: auto-renew on vs off (loyalty indicator)
- **Recency**: time since last_paid
- **Highest Purchase**: indicates price tolerance

---

## 3. Analysis Framework

### 3.1 Phase 1: Data Aggregation & Cleaning

**Task 1.1: Load All Parsed Conversations**
- Read all 13,579+ parsed JSON files
- Filter out empty/failed parses
- Validate required fields exist

**Task 1.2: Group by Conversation Thread**
- Group files by folder path (same folder = same conversation)
- Create conversation-level aggregates
- Track multi-screenshot conversations as single threads

**Task 1.3: Segment by Subscriber Tier**
- Classify each conversation by subscriber tier
- Create tier-specific datasets
- Track distribution across tiers

**Task 1.4: Data Quality Report**
- Count valid vs empty conversations
- Field completeness rates
- Tier distribution statistics

### 3.2 Phase 2: Statistical Analysis (No AI)

**Task 2.1: Tier Distribution Analysis**
- How many conversations per tier?
- Average sale amount per tier
- Tip frequency per tier
- Highest purchase per tier

**Task 2.2: Approach Distribution by Tier**
- What approaches (playful, teasing, transactional) are used for each tier?
- Do chatters change approach based on subscriber value?
- Which approaches appear most often in high-value sales?

**Task 2.3: Stage Distribution Analysis**
- What stage do most successful conversations happen in?
- Stage distribution by tier
- Correlation between stage and sale amount

**Task 2.4: Mood-Approach Correlation**
- What approaches are used for each subscriber mood?
- Mood distribution by tier
- Technique frequency by mood

**Task 2.5: Sale Amount Analysis**
- Average, median, min, max sale amounts per tier
- Sale amount distribution (histogram)
- Tip vs PPV sale distribution
- Upselling patterns (sale_amount vs highest_purchase)

### 3.3 Phase 3: Message Content Analysis

**Task 3.1: Message Length Analysis**
- Average message length by role (creator vs subscriber)
- Message count per conversation
- Creator talk-to-listen ratio (message count ratio)

**Task 3.2: Keyword Extraction**
- Most frequent words/phrases by role
- Keywords correlated with high-value sales
- Tier-specific language patterns

**Task 3.3: Opener Analysis**
- First creator message patterns
- Greeting styles by tier
- Opening hooks that lead to sales

**Task 3.4: Closing Language Analysis**
- How do creators ask for money?
- Tip request phrasing patterns
- PPV pitch language patterns

**Task 3.5: Objection Handling Analysis**
- Identify hesitant subscriber messages
- Creator responses to hesitation
- Price negotiation patterns

### 3.4 Phase 4: AI Pattern Recognition

**Task 4.1: Full Conversation Thread Analysis**
- For multi-screenshot conversations, analyze the full thread
- Identify conversation arc patterns
- Track escalation patterns (rapport -> pitch -> close)

**Task 4.2: Tier-Specific Playbook Extraction**
Using GPT-5.2, analyze each tier separately:

**For New Subscribers:**
- What openers work?
- How quickly do chatters pitch?
- What's the typical first sale amount?

**For Low/Medium Spenders:**
- What builds repeat purchases?
- How do chatters identify price tolerance?
- Upselling patterns

**For High Spenders:**
- What keeps them engaged?
- Premium content patterns
- Custom content requests

**For Whales:**
- Relationship maintenance patterns
- High-ticket sale patterns
- VIP treatment language

**Task 4.3: Technique Deep Dives**
- Analyze top techniques (teasing, transactional, playful)
- Extract specific script templates
- Identify when each technique is appropriate

**Task 4.4: Failure Mode Analysis**
- Look for conversations where sale_amount is low relative to subscriber tier
- Identify potential underperformance patterns
- What could be improved?

### 3.5 Phase 5: Actionable Output Generation

**Task 5.1: Tier-Specific Playbooks**
Create separate guides for:
- New subscriber onboarding
- Low spender conversion
- Medium spender upselling
- High spender maintenance
- Whale VIP treatment

**Task 5.2: Script Templates**
Extract and templatize:
- Opening messages
- Tip requests
- PPV pitches
- Objection handlers
- Upselling sequences

**Task 5.3: Quick Reference Cards**
- Mood-to-approach mapping
- Price anchoring guidelines
- Do's and Don'ts per tier

**Task 5.4: Training Metrics Dashboard Data**
- Export structured data for frontend visualization
- Key metrics by tier
- Trend analysis data

---

## 4. Technical Implementation

### 4.1 Analysis Script Structure

```
scripts/
├── analysis/
│   ├── __init__.py
│   ├── data_loader.py         # Task 1.1-1.4
│   ├── statistical_analysis.py # Task 2.1-2.5
│   ├── message_analysis.py     # Task 3.1-3.5
│   ├── ai_pattern_analysis.py  # Task 4.1-4.4
│   └── output_generator.py     # Task 5.1-5.4
├── run_full_analysis.py        # Master script
└── generate_insights.py        # Existing (to be refactored)
```

### 4.2 Output Structure

```
data/insights/
├── raw/
│   ├── tier_statistics.json
│   ├── approach_distribution.json
│   ├── message_analysis.json
│   └── conversation_threads.json
├── playbooks/
│   ├── new_subscriber_playbook.md
│   ├── low_spender_playbook.md
│   ├── medium_spender_playbook.md
│   ├── high_spender_playbook.md
│   └── whale_playbook.md
├── templates/
│   ├── openers.json
│   ├── tip_requests.json
│   ├── ppv_pitches.json
│   └── objection_handlers.json
├── training_summary.md
└── dashboard_data.json
```

### 4.3 AI Model Usage

| Task | Model | Reason |
|------|-------|--------|
| Pattern extraction | GPT-5.2 | Deep analysis capability |
| Large batch analysis | GPT-4o-mini | Cost efficiency |
| Template generation | GPT-5.2 | Quality output |

### 4.4 Performance Considerations

- Process ALL 13,579 conversations - no sampling unless explicitly stated
- Use batch processing for AI calls (chunks of 50-100)
- Checkpoint progress for resumability
- Parallel processing where possible

---

## 5. Success Criteria

### 5.1 Completeness
- [ ] All 13,579 conversations processed
- [ ] All subscriber tiers analyzed
- [ ] All specified outputs generated

### 5.2 Accuracy
- [ ] No fake conversion rates (acknowledge selection bias)
- [ ] Proper tier segmentation
- [ ] Conversation threading correct

### 5.3 Actionability
- [ ] Playbooks are specific and usable
- [ ] Script templates are copy-paste ready
- [ ] Metrics are meaningful for training

---

## 6. Non-Goals

- **NOT** calculating conversion rates (we only have success data)
- **NOT** comparing to industry benchmarks
- **NOT** making predictions about what will work
- **ONLY** describing what successful sales look like, segmented properly

---

## 7. Research References

This analysis methodology is informed by:

1. **Conversation Intelligence Platforms** (Gong, Chorus, Clari)
   - Talk-to-listen ratio analysis
   - Sentiment scoring
   - Objection handling detection
   - Keyword extraction

2. **Qualitative Research Coding**
   - Thematic analysis
   - Conversation Analysis (CA) methodology
   - Coding scheme development

3. **One-Class Classification Methodology**
   - Appropriate for success-only data
   - Focus on characterizing the positive class
   - No false comparisons to non-existent negatives

4. **Sales Linguistics Research**
   - Language pattern analysis
   - Persuasion technique identification
   - Customer-centric orientation

---

## 8. Timeline & Dependencies

### Dependencies
- Parsed conversation data (COMPLETE: 13,579 files)
- OpenAI API access for GPT-5.2/GPT-4o-mini
- Python environment with required packages

### Phases
1. Phase 1 (Data Aggregation): Build foundation
2. Phase 2 (Statistical): No AI required
3. Phase 3 (Message Content): Lightweight analysis
4. Phase 4 (AI Patterns): Heavy AI usage
5. Phase 5 (Output): Generate deliverables
