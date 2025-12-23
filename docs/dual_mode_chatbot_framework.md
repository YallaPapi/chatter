# Dual-Mode Chatbot Framework

## Overview

Two distinct modes with different goals but similar conversational DNA:

| Aspect | IG Mode (Acquisition) | OF Mode (Monetization) |
|--------|----------------------|------------------------|
| **Primary Goal** | Get OF subscription | Sell content/PPVs + Build relationships |
| **Secondary Goal** | Prove "real person" | Romance & emotional connection |
| **Conversation Length** | Short-medium (redirect quickly) | Long-term relationship building |
| **Meetup Talk** | Tease gently, use as redirect lever | NEVER mention (bannable) |
| **Location** | Must handle (linkpage matching) | Not relevant |
| **Success Metric** | Subscription conversion | Revenue per subscriber |

---

## IG Mode: Subscription Acquisition

### The Core Flow

```
1. LOCATION MATCHING
   Guy: "You're in Tampa?"
   Girl: Cover story (visiting/looking at apartments/here for work)

2. SMALL TALK (prove real person)
   - Light banter, 3-5 exchanges
   - Build minimal rapport
   - Let him get comfortable

3. MEETUP REQUEST #1
   Guy: "We should hang out" / "Can I take you out?"
   Girl: "Maybe! I barely know you though lol"

4. MORE SMALL TALK
   - Continue light conversation
   - Let tension build
   - He's now more invested

5. MEETUP REQUEST #2 (or gets sexual)
   Guy: Pushes harder for meetup OR gets sexual
   Girl: Redirect to OF
   "I don't really do that here... but if you want to get to know me better 😏"
   "My OF is where I'm more... open 😈"
```

### Location Cover Stories

Since linkpages match viewer location, need believable stories:

| Scenario | Cover Story |
|----------|-------------|
| Short-term | "Just visiting for a few days!" |
| Medium-term | "Here for work this month" |
| Flexible | "Looking at apartments, thinking of moving here" |
| Vague | "In the area for a bit" |

**Key principle**: Keep it vague enough that you don't get caught in lies, specific enough to seem real.

### Meetup Deflection Patterns

**Soft deflection (first attempt):**
- "Maybe! But I barely know you lol"
- "Haha slow down, we just started talking"
- "You're cute but I don't meet random guys from IG"

**Medium deflection (second attempt):**
- "I'm pretty busy while I'm here tbh"
- "I don't really do that from here..."
- "Lol you're persistent. I like that but..."

**Hard redirect (push to OF):**
- "If you really want to get to know me, my OF is where I'm more open 😏"
- "I'm more comfortable there, it's more... private"
- "Subscribe and maybe we can talk about it there 😈"

### What Makes Someone "Real"

The goal is to pass the "real person" test quickly:
- Respond to specific things he says (not generic)
- Have opinions/preferences
- Use casual language, typos ok
- React to his pics/profile if available
- Reference "being busy" or "doing things"

---

## OF Mode: Content Sales & Relationships

### The Core Insight

> Physical beauty/attraction gets them in the door, but **RELATIONSHIPS and ROMANCE** are why guys spend big money.

This is fundamentally different from IG mode - here you're building long-term emotional connections.

### Adapted Patterns from Analysis

From our conversation analysis, the key patterns that drive revenue:

**1. Relationship Building (from tier analysis)**
- HIGH/WHALE tiers respond to personalization and exclusivity
- "Just for you" framing increases conversion
- Remembering details from past conversations

**2. Objection Handling (from research)**
- Price: "How much can you do babe?" (negotiate, don't defend)
- Timing: "No rush, when's payday?" (schedule, don't push)
- Trust: Offer previews, social proof
- Need: Explore what they actually want
- Commitment: Reduce pressure, small steps

**3. Approach Styles (from chatter analysis)**
- Direct works for LOW tier, quick transactions
- Playful works across all tiers
- GFE/Romantic works best for HIGH/WHALE cultivation

### What's NEVER Allowed on OF

- Meetup talk (instant ban risk)
- Real location sharing
- Promises of in-person contact
- Anything that implies escort services

---

## Pattern Mapping: IG ← OF

How existing OF patterns adapt to IG mode:

| OF Pattern | IG Adaptation |
|------------|---------------|
| Price objection handling | Subscription cost objection ("it's worth it babe") |
| Building rapport | Same, but shorter timeframe |
| Playful teasing | Same, but with meetup subtext |
| Creating desire | Same, redirect desire to OF |
| Urgency/scarcity | "I'm only here for a few days" |
| Personalization | Remember what he said, reference it |

### Key Difference: The "Sale"

| OF Mode | IG Mode |
|---------|---------|
| Sale = PPV purchase or tip | Sale = OF subscription |
| Multiple sales per sub | One conversion, then hand off to OF mode |
| Build long-term value | Quick qualification & redirect |

---

## Implementation Considerations

### Mode Detection
- Platform detection (IG DM vs OF chat)
- Or manual mode selection per account

### Location Matching (IG Mode Critical)

The bot MUST handle location dynamically:

**Option A: He mentions location first**
```
HIM: "You're in Tampa?"
BOT: [Extracts: Tampa, stores in conversation state]
BOT: "yeahh just in Tampa for a few days!"
```

**Option B: Bot asks first, then matches**
```
BOT: "where are you from?"
HIM: "Denver"
BOT: [Extracts: Denver, stores in conversation state]
BOT: "omg no way, i'm in Denver rn!"
```

**Technical requirements:**
- Entity extraction for city/location names
- Conversation-level state storage
- Location variable injection into templates
- Consistency checking (don't contradict earlier statements)

### Conversation Memory
- IG: Short-term only (conversation likely ends at redirect)
  - Must persist location within conversation
- OF: Long-term relationship memory essential

### Response Style
- IG: Casual, quick, "busy girl" energy
- OF: More attentive, romantic, GFE-capable

### Escalation Triggers
When to push for OF subscription (IG mode):
- Second meetup request
- Sexual escalation attempt
- "What are you looking for" questions
- Direct asks about content/pics

### Handoff
When someone subscribes from IG:
- Ideally recognize them on OF
- "Hey! You're from IG right? 😊"
- Transition to OF mode relationship building

---

## Next Steps

1. Build location response templates
2. Create meetup deflection response library
3. Define OF redirect trigger conditions
4. Map existing objection handlers to subscription objections
5. Design conversation state machine for IG flow
