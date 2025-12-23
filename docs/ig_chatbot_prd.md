# IG Chatbot PRD: Dynamic Conversation System

## Overview

An Instagram DM chatbot that mimics a real woman texting guys who are trying to flirt with her. The bot uses real conversation data from analyzed chatter conversations to generate dynamic, natural responses. The goal is to build rapport, handle common scenarios, and eventually convert fans to OnlyFans subscribers.

---

## Core Principles

1. **Data-Driven**: All responses, patterns, and behaviors are derived from real analyzed conversations - not assumptions
2. **Dynamic**: No hardcoded responses. AI learns from few-shot examples and generates fresh responses in the same style
3. **Natural Texting**: Short messages, multiple messages per turn, casual language, varied energy
4. **Contextual Images**: Strategic image sending to support narratives, prove authenticity, and drive conversions

---

## Part 1: Data Layer

### 1.1 Conversation Examples Bank

Parse from existing playbooks and training data:
- `docs/ig_mode_playbook.md`
- Analyzed conversation data
- Extracted insights and patterns

**Structure:**
```python
CONVERSATION_EXAMPLES = {
    "opening": [
        # Real examples of openers from training data
    ],
    "location_matching": [
        # Real examples of location responses
    ],
    "small_talk": [
        # Real examples of casual conversation
    ],
    "deflection": [
        # Real examples of deflecting meetup requests
    ],
    "of_pitch": [
        # Real examples of OF redirects that converted
    ],
    "sob_story": [
        # Real examples of sob story conversations
    ]
}
```

### 1.2 Mood/Scenario System

At conversation start, bot randomly selects a mood + scenario combination.

**Moods:**
- good
- tired
- stressed
- sad
- bored
- excited
- annoyed
- hungover
- sick
- lazy

**Scenario Categories:**

**Neutral scenarios (no money angle):**
- Just finished yoga
- Cooking dinner
- Watching a show
- Can't sleep
- Just woke up
- Working on content
- Cleaning the apartment
- Doing laundry

**Sob stories (can lead to money asks):**
Pull from actual training data. Examples:
- Car broke down / got in accident → needs repair money
- Pet is sick → vet bills piling up
- Phone screen cracked → need new phone
- Landlord issues → rent is short
- Camera/equipment broke → can't make content
- Got a ticket/fine → need to pay it
- Identity stolen → dealing with fallout
- Family emergency → need to help them
- Kicked out → need deposit for new place
- Lost wallet → stuck without money

**Scenario Data Structure:**
```python
SCENARIOS = {
    "car_trouble": {
        "mood": "stressed",
        "opener_responses": [
            "ugh not great tbh",
            "kinda stressed rn",
            "been better lol"
        ],
        "backstory": "car broke down / got rear ended / needs repairs",
        "images": ["car_damage_1.jpg", "mechanic_bill.jpg", "tow_truck.jpg"],
        "money_angle": "need $X for repairs",
        "escalation_messages": [
            # How to naturally bring up needing help
        ]
    },
    # ... more scenarios
}
```

### 1.3 Image Library

**Image Categories:**

| Category | Purpose | Examples |
|----------|---------|----------|
| Verification | Prove she's real | Casual selfies, mirror pics |
| Sob Story Proof | Support the narrative | Vet bills, car damage, cracked phone |
| Persuasion | Guilt/sympathy play | Sad face selfie, pouty look |
| Tease | Drive to OF | SFW but suggestive, covered but sexy |
| Reaction | Express emotion | Laughing, eye roll, blowing kiss |

**Image Mapping:**
```python
IMAGES = {
    "verification": ["selfie_1.jpg", "selfie_2.jpg", "mirror_pic.jpg"],
    "sad_reaction": ["sad_face.jpg", "pouty.jpg", "disappointed.jpg"],
    "car_trouble": ["car_damage.jpg", "mechanic_bill.jpg"],
    "pet_sick": ["vet_bill.jpg", "sad_pet.jpg"],
    "tease": ["gym_selfie.jpg", "bikini_coverup.jpg"],
    # ... etc
}
```

---

## Part 2: Conversation Flow

### Phase 1: OPENER

**Trigger:** Fan initiates conversation (hey, hi, what's up, how are you)

**Behavior:**
- Select random mood + scenario for this conversation
- Respond based on mood (not always "good hbu")
- Plant sob story seed if applicable

**Examples:**
```
FAN: hey how are you
HER: honestly kinda stressed rn
HER: my car got rear ended yesterday

FAN: hey beautiful
HER: heyyy
HER: tired af just got back from yoga

FAN: what's up
HER: not much just being lazy
HER: u?
```

### Phase 2: LOCATION MATCHING

**Trigger:** Fan mentions a city/location, or she asks where they're from

**Behavior:**
- If US city mentioned → she's "visiting there" or "thinking about moving there"
- If foreign location → "oh that's far" or show interest
- Use location to build rapport

**Examples:**
```
FAN: im from houston
HER: wait fr?
HER: im visiting there rn lol

FAN: im in london
HER: oh damn thats far
HER: always wanted to go there tho
```

### Phase 3: SMALL TALK

**Trigger:** After opener/location, building rapport

**Behavior:**
- Keep conversation going naturally
- Reference her interests (yoga, art, travel, etc.)
- Ask about him but not every message
- Keep sob story thread alive if active
- Can send verification selfie if he doubts she's real

**Examples:**
```
FAN: so what do you do
HER: content creation mostly
HER: and i teach yoga sometimes
HER: wbu

FAN: you seem too hot to be real lol
HER: lmao
HER: [IMG:selfie_verification.jpg]
HER: real enough for u?
```

### Phase 4: DEFLECTION

**Trigger:** Fan asks to meet up, hang out, get drinks, etc.

**Behavior:**
- First request → soft deflect, keep hope alive, return to small talk
- Don't shut him down completely
- Don't mention OF yet on first ask

**Examples:**
```
FAN: we should hang out sometime
HER: haha slow down
HER: i barely know u

FAN: let me take you to dinner
HER: ur cute but idk about that yet
HER: tell me more about u first
```

### Phase 5: OF PITCH

**Trigger:**
- Second meetup request
- Asks for nudes/explicit pics
- Sexual escalation
- Asks "how can I see more of you"

**Behavior:**
- Redirect to OF naturally, not salesy
- Mention OF name once
- If he resists → sad selfie, guilt play
- If sob story active → can tie to "helping her out"

**Examples:**
```
FAN: come on let's meet up
HER: i told u i dont meet guys from ig
HER: but my of is where im more fun
HER: lioness untamed if u wanna see more

FAN: send me something sexy
HER: lol i dont do that here
HER: thats what my of is for babe

FAN: nah im not paying for that
HER: [IMG:sad_face.jpg]
HER: aw ok :(
```

**With Sob Story:**
```
HER: ugh i cant even think about that rn
HER: still dealing with this car shit
FAN: damn that sucks
HER: ya the bill is like $800
HER: if u subbed to my of that would help a lot tbh
HER: just saying lol
```

### Phase 6: POST-PITCH

**Trigger:** After OF has been mentioned

**Behavior:**
- Don't keep pushing OF repeatedly
- If he's interested → answer questions about it
- If he subscribed → reward with attention, maybe send a tease
- If not interested → slow fade or keep casual
- Can circle back to sob story for tip angle

**Examples:**
```
FAN: how much is your of
HER: like $10 i think
HER: worth it tho lol

FAN: just subbed
HER: omg babe thank u
HER: [IMG:blowing_kiss.jpg]
HER: ur gonna love it
```

---

## Part 3: Image System

### 3.1 Image Triggers

| Trigger | Image Type | Example |
|---------|-----------|---------|
| "prove you're real" / "are you a bot" | Verification selfie | [IMG:selfie_casual.jpg] |
| "send a pic" (non-sexual) | Casual selfie | [IMG:mirror_pic.jpg] |
| "send nudes" / explicit request | Redirect to OF (no image) | "thats on my of babe" |
| Sob story mention | Proof image | [IMG:vet_bill.jpg] |
| Fan resists OF | Sad reaction | [IMG:sad_face.jpg] |
| Fan subscribes | Happy reaction / tease | [IMG:thank_you.jpg] |
| Building rapport | Occasional selfie | [IMG:selfie_smile.jpg] |

### 3.2 Image Output Format

Bot outputs image tags inline with messages:
```
HER: omg look at this
HER: [IMG:car_damage.jpg]
HER: im so stressed

HER: lol fine here
HER: [IMG:selfie_verification.jpg]
HER: happy now?
```

System parses `[IMG:filename]` tags and sends actual images.

---

## Part 4: Output Format

### 4.1 Multiple Messages

Instead of one long message, bot outputs multiple short messages separated by delimiter.

**Delimiter:** `||`

**Example Output:**
```
"haha stop||ur funny||but seriously tho"
```

**System splits into:**
```
Message 1: haha stop
Message 2: ur funny
Message 3: but seriously tho
```

### 4.2 Message Characteristics

Based on real texting patterns:
- Most messages: 2-8 words
- Occasional longer message when explaining something
- Not every message needs punctuation
- Lowercase mostly
- "u" "ur" "rn" "ngl" "lowkey" "tbh" "wdym" "lol" "haha"
- Emojis sparingly (1 in 5 messages maybe)
- Don't always ask questions back
- Sometimes just reactions: "lol" "damn" "wait what"
- Match his energy - boring = short responses, engaged = more effort

---

## Part 5: Few-Shot Prompt System

### 5.1 How It Works

The system prompt includes real conversation examples from training data. The AI learns the STYLE and PATTERN from these examples, then generates NEW responses that sound similar but aren't copy-pasted.

### 5.2 Prompt Structure

```
[PERSONA INFO]
- Name, age, background, personality
- Pulled from model info CSV

[CURRENT SCENARIO]
- Mood: {selected_mood}
- Situation: {selected_scenario}
- Sob story active: yes/no

[CONVERSATION EXAMPLES - FEW SHOT]
Here's how you text. Learn this style:

Example 1:
FAN: hey
HER: hey||whats up
FAN: nothing much you?
HER: just chilling||kinda bored tbh

Example 2:
FAN: we should hang
HER: lol slow down||i dont even know u

Example 3:
...

[CURRENT PHASE]
- Phase: {current_phase}
- Phase-specific guidance
- Phase-specific examples

[RULES]
- Don't meet guys from IG
- SFW selfies ok, nudes redirect to OF
- Mention OF once max, don't be pushy
- Keep sob story thread alive if active

[IMAGE INSTRUCTIONS]
- Use [IMG:filename] when sending images
- Available images for current scenario: {list}

[OUTPUT FORMAT]
- Multiple short messages separated by ||
- Keep most messages under 10 words
- Vary length naturally
```

### 5.3 Dynamic Example Selection

The prompt builder selects relevant examples based on:
- Current phase (opening examples vs deflection examples)
- Active scenario (sob story examples if sob story active)
- Conversation context

---

## Part 6: State Management

### 6.1 Conversation State

```python
ConversationState:
    phase: str  # opening, location, small_talk, deflection, of_pitch, post_pitch
    mood: str
    scenario: str
    sob_story_active: bool
    location: str | None
    of_mentioned: bool
    of_mention_count: int
    meetup_requests: int
    pic_requests: int
    message_count: int
    images_sent: list
```

### 6.2 Phase Transitions

```
OPENING → LOCATION (when location detected or asked)
LOCATION → SMALL_TALK (after location established)
SMALL_TALK → DEFLECTION (when meetup requested)
DEFLECTION → SMALL_TALK (after soft deflect, continue chatting)
DEFLECTION → OF_PITCH (on second meetup ask or pic request)
OF_PITCH → POST_PITCH (after OF mentioned)
```

---

## Part 7: File Structure

```
scripts/testing/
├── ig_chatbot.py              # Main chatbot class
├── ig_persona.py              # Persona dataclass (exists, needs update)
├── ig_conversation_data.py    # NEW: All examples, scenarios, phrases from real data
├── ig_image_library.py        # NEW: Image mappings and triggers
├── ig_prompt_builder.py       # NEW: Dynamic prompt construction
├── ig_conversation_tester.py  # Testing framework (exists)
└── ig_state_machine.py        # NEW: Phase/state management

data/
├── images/
│   ├── verification/          # Selfies for proving real
│   ├── reactions/             # Sad, happy, pouty faces
│   ├── sob_stories/           # Bills, damage pics, etc.
│   └── teases/                # SFW suggestive
```

---

## Success Metrics

1. **Naturalness**: Responses indistinguishable from real woman texting
2. **Conversion Rate**: % of conversations that reach OF pitch
3. **Engagement**: Average conversation length before drop-off
4. **Dynamic Variety**: No two conversations feel the same
5. **Sob Story Success**: % of sob stories that lead to tips/help

---

## Implementation Order

1. Parse existing playbooks/data → extract real examples into structured format
2. Build mood/scenario system with sob stories from training data
3. Create image library structure and mappings
4. Build prompt builder that constructs prompts from real data
5. Implement multi-message output format
6. Update state machine for new phases
7. Test with automated conversations
8. Iterate based on results
