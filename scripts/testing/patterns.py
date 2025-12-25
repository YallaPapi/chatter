# -*- coding: utf-8 -*-
"""
Pre-compiled Regex Patterns

All regex patterns used across the chatbot, pre-compiled at module load
for better performance. Eliminates ~15ms overhead from recompilation per message.
"""

import re
from typing import Dict, List, Pattern


# =============================================================================
# INTENT PATTERNS (from ig_intent_detector.py)
# =============================================================================

INTENT_PATTERNS: Dict[str, List[Pattern]] = {
    "SUBSCRIBED": [
        re.compile(r"(?:i\s+)?(?:just\s+)?(?:subbed|subscribed)", re.IGNORECASE),
        re.compile(r"(?:i\s+)?signed\s+up", re.IGNORECASE),
        re.compile(r"(?:bought|got|joined)\s+(?:your|ur|the)\s+(?:of|onlyfans)", re.IGNORECASE),
        re.compile(r"im\s+(?:on\s+)?(?:your|ur)\s+of\s+now", re.IGNORECASE),
    ],
    "HOSTILE": [
        re.compile(r"(?:fuck|screw)\s+(?:this|that|u|you|off)", re.IGNORECASE),
        re.compile(r"block(?:ed|ing)?", re.IGNORECASE),
        re.compile(r"bye\s+(?:bitch|fake)", re.IGNORECASE),
        re.compile(r"waste\s+of\s+time", re.IGNORECASE),
        re.compile(r"im\s+(?:out|done|leaving)", re.IGNORECASE),
        re.compile(r"(?:go|fuck)\s+away", re.IGNORECASE),
    ],
    "OBJECTION": [
        re.compile(r"(?:not|no[t]?)\s+(?:paying|subscribing|gonna\s+(?:pay|sub)|going\s+to\s+(?:pay|sub))", re.IGNORECASE),
        re.compile(r"(?:nah|no)\s+(?:i'?m|im)\s+(?:good|ok(?:ay)?|alright)", re.IGNORECASE),
        re.compile(r"i'?m\s+(?:good|okay|alright)\s+(?:on\s+that|thanks?|thx)", re.IGNORECASE),
        re.compile(r"maybe\s+later", re.IGNORECASE),
        re.compile(r"(?:that'?s|thats?)\s+(?:too\s+)?(?:expensive|much|pricey)", re.IGNORECASE),
        re.compile(r"(?:too\s+)?(?:expensive|pricey|much)", re.IGNORECASE),
        re.compile(r"(?:no\s+thanks?|pass|hard\s+pass)", re.IGNORECASE),
        re.compile(r"(?:can'?t|cant)\s+afford", re.IGNORECASE),
        re.compile(r"(?:not|no)\s+(?:interested|into\s+(?:that|paying))", re.IGNORECASE),
        re.compile(r"i\s+don'?t\s+pay\s+for", re.IGNORECASE),
        re.compile(r"(?:broke|no\s+money)", re.IGNORECASE),
        re.compile(r"(?:i'?ll|ill)\s+(?:think\s+about\s+it|pass)", re.IGNORECASE),
        # Additional patterns for cheap_guy scenarios
        re.compile(r"not\s+sub(?:b?ing|scrib)", re.IGNORECASE),
        re.compile(r"(?:any|got)\s+free", re.IGNORECASE),
        re.compile(r"free\s+(?:pics?|vids?|teasers?|stuff|content|preview)", re.IGNORECASE),
        re.compile(r"nah\s+(?:of|onlyfans)", re.IGNORECASE),
        re.compile(r"(?:of|onlyfans)\??\s*nah", re.IGNORECASE),
    ],
    "PIC_REQUEST": [
        re.compile(r"send\s+(?:me\s+)?(?:a\s+)?(?:pic|photo|pics|nudes?|something|more|one|vid)", re.IGNORECASE),
        re.compile(r"(?:got|have|show)\s+(?:any\s+)?(?:more\s+)?pics?", re.IGNORECASE),
        re.compile(r"show\s+me", re.IGNORECASE),
        re.compile(r"let\s+me\s+see", re.IGNORECASE),
        re.compile(r"can\s+i\s+see", re.IGNORECASE),
        re.compile(r"(?:more|another)\s+pic", re.IGNORECASE),
        re.compile(r"just\s+(?:one|a)\s+(?:pic|nude|tit|ass)", re.IGNORECASE),
        re.compile(r"gimme\s+(?:a\s+)?(?:pic|nudes?)", re.IGNORECASE),
        re.compile(r"(?:pics?|nudes?)\s+(?:plz|pls|please|now|\?)", re.IGNORECASE),
        re.compile(r"one\s+nude", re.IGNORECASE),
        re.compile(r"just\s+tits", re.IGNORECASE),
    ],
    "SEXUAL": [
        re.compile(r"what\s+(?:are\s+)?(?:you|u)\s+wearing", re.IGNORECASE),
        re.compile(r"send\s+(?:me\s+)?nudes?", re.IGNORECASE),
        re.compile(r"(?:wanna|want\s+to)\s+(?:fuck|bang|smash|hook\s*up)", re.IGNORECASE),
        re.compile(r"(?:so\s+)?(?:horny|hard|wet)", re.IGNORECASE),
        re.compile(r"(?:suck|lick|eat)", re.IGNORECASE),
        re.compile(r"naked", re.IGNORECASE),
        re.compile(r"come\s+sit\s+on", re.IGNORECASE),
        re.compile(r"(?:cum|cumming|jerking|stroke|stroking)", re.IGNORECASE),
        re.compile(r"(?:tits?|ass|pussy|dick|cock)\s", re.IGNORECASE),
        re.compile(r"(?:ur|your)\s+(?:tits?|ass|body|pussy)", re.IGNORECASE),
        re.compile(r"(?:naughty|dirty|freaky)", re.IGNORECASE),
    ],
    "MEETUP_REQUEST": [
        re.compile(r"(?:let'?s?|we\s+should|can\s+we|wanna)\s+(?:meet|hang|chill|link|grab)", re.IGNORECASE),
        re.compile(r"(?:take|bring)\s+(?:you|u)\s+out", re.IGNORECASE),
        re.compile(r"(?:get|grab)\s+(?:dinner|lunch|drinks?|coffee|food)", re.IGNORECASE),
        re.compile(r"come\s+(?:over|thru|through)", re.IGNORECASE),
        re.compile(r"pull\s+up", re.IGNORECASE),
        re.compile(r"when\s+can\s+(?:i|we)\s+(?:see|meet)\s+(?:you|u)", re.IGNORECASE),
        re.compile(r"(?:free|available|down)\s+(?:tonight|later|this\s+weekend|to\s+hang)", re.IGNORECASE),
        re.compile(r"(?:wanna|want\s+to)\s+(?:see|meet)\s+(?:you|u)", re.IGNORECASE),
        re.compile(r"hang\s*out", re.IGNORECASE),
        re.compile(r"link\s*up", re.IGNORECASE),
    ],
    "SKEPTICAL": [
        re.compile(r"(?:are\s+)?(?:you|u)\s+(?:a\s+)?(?:bot|real|fake)", re.IGNORECASE),
        re.compile(r"prove\s+(?:it|(?:you'?re?|ur|u\s+are)\s+real)", re.IGNORECASE),
        re.compile(r"send\s+(?:a\s+)?vid", re.IGNORECASE),
        re.compile(r"catfish", re.IGNORECASE),
        re.compile(r"too\s+good\s+to\s+be", re.IGNORECASE),
        re.compile(r"(?:you|u)\s+(?:a\s+)?(?:bot|scam)", re.IGNORECASE),
        re.compile(r"is\s+this\s+(?:actually\s+)?(?:you|u)", re.IGNORECASE),
        re.compile(r"how\s+do\s+i\s+know\s+(?:you'?re?|ur)\s+real", re.IGNORECASE),
    ],
    "CONTACT_REQUEST": [
        re.compile(r"(?:what'?s?|give\s+me)\s+(?:your|ur)\s+(?:snap|snapchat|number|insta|ig)", re.IGNORECASE),
        re.compile(r"add\s+me\s+on\s+snap", re.IGNORECASE),
        re.compile(r"(?:got|have)\s+(?:snap|snapchat)", re.IGNORECASE),
        re.compile(r"snap\s*(?:me|chat)?[\s\?]", re.IGNORECASE),
        re.compile(r"(?:whats?|give)\s+(?:ur|your)\s+(?:number|#)", re.IGNORECASE),
    ],
    "OF_QUESTION": [
        re.compile(r"(?:what'?s?|how\s+much)\s+(?:is\s+)?(?:your|ur|the)\s+(?:of|onlyfans)", re.IGNORECASE),
        re.compile(r"what\s+(?:do\s+)?(?:you|u)\s+post\s+(?:on\s+)?(?:there|of)", re.IGNORECASE),
        re.compile(r"is\s+(?:it|your\s+of)\s+worth", re.IGNORECASE),
        re.compile(r"what'?s?\s+on\s+(?:your|ur)\s+(?:of|page)", re.IGNORECASE),
        re.compile(r"(?:do\s+)?(?:you|u)\s+(?:have|got)\s+(?:an?\s+)?(?:of|onlyfans)", re.IGNORECASE),
    ],
    "EMOTIONAL": [
        re.compile(r"(?:rough|bad|hard|shit+y?)\s+(?:day|week|time)", re.IGNORECASE),
        re.compile(r"(?:feeling|feel)\s+(?:down|sad|lonely|depressed|empty|lost)", re.IGNORECASE),
        re.compile(r"no\s+one\s+(?:gets|understands)", re.IGNORECASE),
        re.compile(r"(?:need|want)\s+(?:someone\s+)?to\s+talk", re.IGNORECASE),
        re.compile(r"going\s+through\s+(?:a\s+lot|some\s+stuff|shit)", re.IGNORECASE),
        re.compile(r"(?:stressed|anxious|worried)", re.IGNORECASE),
    ],
    "COMPLIMENT": [
        re.compile(r"(?:you'?re?|ur)\s+(?:so\s+)?(?:hot|sexy|beautiful|gorgeous|fine|cute|pretty|stunning|fire|insane)", re.IGNORECASE),
        re.compile(r"(?:damn|omg|wow)\s+(?:you'?re?|ur)", re.IGNORECASE),
        re.compile(r"(?:nice|great|amazing)\s+(?:pics?|body|ass|tits)", re.IGNORECASE),
        re.compile(r"(?:you|u)\s+(?:look|are)\s+(?:incredible|amazing|perfect)", re.IGNORECASE),
        re.compile(r"i\s+(?:like|love)\s+(?:your|ur)", re.IGNORECASE),
        re.compile(r"(?:body|pics?|tits?|ass)\s+(?:is|are|looks?)\s+(?:fire|insane|perfect|hot|amazing)", re.IGNORECASE),
        re.compile(r"(?:fire|insane|perf|perfect)\s*$", re.IGNORECASE),
    ],
    "LOCATION_SHARE": [
        re.compile(r"(?:i'?m|im)\s+(?:from|in|at)\s+\w+", re.IGNORECASE),
        re.compile(r"i\s+live\s+(?:in|near)\s+\w+", re.IGNORECASE),
        re.compile(r"(?:from|based\s+in)\s+\w+(?:\s+\w+)?", re.IGNORECASE),
    ],
    "LOCATION_ASK": [
        re.compile(r"where\s+(?:are\s+)?(?:you|u)\s+(?:at|from|located)", re.IGNORECASE),
        re.compile(r"(?:you|u)\s+(?:near|close|around)", re.IGNORECASE),
        re.compile(r"what\s+(?:city|area|state)", re.IGNORECASE),
    ],
    "GREETING": [
        re.compile(r"^hey+\s*$", re.IGNORECASE),
        re.compile(r"^hi+\s*$", re.IGNORECASE),
        re.compile(r"^hello+\s*$", re.IGNORECASE),
        re.compile(r"^sup\s*$", re.IGNORECASE),
        re.compile(r"^yo+\s*$", re.IGNORECASE),
        re.compile(r"^what'?s?\s*up", re.IGNORECASE),
        re.compile(r"^wyd\s*$", re.IGNORECASE),
        re.compile(r"^how'?s?\s*it\s*going", re.IGNORECASE),
        re.compile(r"^how\s+(?:are\s+)?(?:you|u)", re.IGNORECASE),
    ],
}

# Priority order for intent detection
INTENT_PRIORITY = [
    "SUBSCRIBED",
    "HOSTILE",
    "OBJECTION",
    "PIC_REQUEST",
    "SEXUAL",
    "MEETUP_REQUEST",
    "SKEPTICAL",
    "CONTACT_REQUEST",
    "OF_QUESTION",
    "EMOTIONAL",
    "COMPLIMENT",
    "LOCATION_SHARE",
    "LOCATION_ASK",
    "GREETING",
]


# =============================================================================
# STATE MACHINE PATTERNS (from ig_state_machine.py)
# =============================================================================

LOCATION_PATTERNS: List[Pattern] = [
    re.compile(r"(?:i\'?m\s+)?(?:from|in|live\s+in|based\s+in)\s+(\w+(?:\s+\w+)?)", re.IGNORECASE),
    re.compile(r"(\w+(?:\s+\w+)?)\s+(?:area|city)", re.IGNORECASE),
    re.compile(r"i\s+live\s+(?:in|near)\s+(\w+(?:\s+\w+)?)", re.IGNORECASE),
]

STATE_MEETUP_PATTERNS: List[Pattern] = [
    re.compile(r"(?:let\'?s?|we\s+should|can\s+we|wanna)\s+(?:meet|hang|link|chill|grab\s+drinks?)", re.IGNORECASE),
    re.compile(r"(?:take\s+you|bring\s+you)\s+(?:out|to\s+dinner)", re.IGNORECASE),
    re.compile(r"(?:get|grab)\s+(?:dinner|lunch|drinks?|coffee|food)", re.IGNORECASE),
    re.compile(r"(?:show\s+you\s+around|hang\s+out|link\s+up)", re.IGNORECASE),
    re.compile(r"when\s+(?:can|will)\s+(?:i|we)\s+(?:see|meet)\s+you", re.IGNORECASE),
    re.compile(r"(?:come\s+)?over", re.IGNORECASE),
    re.compile(r"let\s+me\s+(?:take|see)\s+you", re.IGNORECASE),
    re.compile(r"wanna\s+(?:chill|hang|kick\s+it|vibe)", re.IGNORECASE),
    re.compile(r"(?:lets?|we\s+should)\s+(?:kick\s+it|get\s+together|do\s+something)", re.IGNORECASE),
    re.compile(r"(?:pull\s+up|slide\s+through|come\s+thru)", re.IGNORECASE),
    re.compile(r"(?:what\s+(?:are\s+)?(?:you|u)\s+doing|wyd)\s+(?:later|tonight|this\s+weekend)", re.IGNORECASE),
    re.compile(r"(?:free|available|down)\s+(?:tonight|later|this\s+weekend|to\s+hang)", re.IGNORECASE),
    re.compile(r"(?:i\s+)?(?:wanna|want\s+to)\s+(?:see|meet)\s+(?:you|u)", re.IGNORECASE),
    re.compile(r"(?:come|swing)\s+by", re.IGNORECASE),
    re.compile(r"(?:netflix|movie)\s+and\s+chill", re.IGNORECASE),
]

STATE_PIC_REQUEST_PATTERNS: List[Pattern] = [
    re.compile(r"send\s+(?:me\s+)?(?:a\s+|some\s+)?(?:pic|photo|nudes?|something\s+sexy|pics)", re.IGNORECASE),
    re.compile(r"(?:got|have)\s+(?:any\s+)?(?:more\s+)?pics?", re.IGNORECASE),
    re.compile(r"show\s+me\s+(?:something|more)", re.IGNORECASE),
]

STATE_SEXUAL_PATTERNS: List[Pattern] = [
    re.compile(r"what\s+(?:are\s+)?(?:you|u)\s+wearing", re.IGNORECASE),
    re.compile(r"(?:so\s+)?(?:hot|sexy|fine|beautiful|gorgeous)", re.IGNORECASE),
    re.compile(r"(?:your\s+)?body", re.IGNORECASE),
    re.compile(r"naked", re.IGNORECASE),
    re.compile(r"bedroom", re.IGNORECASE),
    re.compile(r"(?:what\s+would\s+you|wanna)\s+do\s+(?:to\s+me|together)", re.IGNORECASE),
]

OF_PATTERNS: List[Pattern] = [
    re.compile(r"\bof\b", re.IGNORECASE),
    re.compile(r"onlyfans", re.IGNORECASE),
    re.compile(r"only\s*fans", re.IGNORECASE),
    re.compile(r"subscribe", re.IGNORECASE),
    re.compile(r"sub\b", re.IGNORECASE),
]

SUBSCRIPTION_PATTERNS: List[Pattern] = [
    re.compile(r"(?:i\s+)?(?:just\s+)?(?:subbed|subscribed)", re.IGNORECASE),
    re.compile(r"(?:signed|sign)\s+up", re.IGNORECASE),
    re.compile(r"joined\s+(?:your|ur|the)\s+(?:of|onlyfans)", re.IGNORECASE),
    re.compile(r"bought\s+(?:it|your)", re.IGNORECASE),
]


# =============================================================================
# IMAGE TRIGGER PATTERNS (from ig_image_library.py)
# =============================================================================

IMAGE_TRIGGER_PATTERNS: Dict[str, tuple] = {
    # Verification triggers
    "prove_real": ("verification", [
        re.compile(r"(are\s+you|u)\s+(real|a\s+bot|fake)", re.IGNORECASE),
        re.compile(r"prove\s+(you\'?re?|ur)\s+real", re.IGNORECASE),
        re.compile(r"(bot|fake|scam)", re.IGNORECASE),
        re.compile(r"too\s+(hot|good)\s+to\s+be\s+real", re.IGNORECASE),
        re.compile(r"catfish", re.IGNORECASE),
    ]),
    "casual_pic": ("verification", [
        re.compile(r"send\s+(a|me\s+a)?\s*pic", re.IGNORECASE),
        re.compile(r"(got\s+)?more\s+pics", re.IGNORECASE),
        re.compile(r"what\s+do\s+you\s+look\s+like", re.IGNORECASE),
    ]),

    # Sad reaction triggers
    "fan_refuses": ("sad_reaction", [
        re.compile(r"(not|no(t)?)\s+(paying|subscribing|gonna|going\s+to)", re.IGNORECASE),
        re.compile(r"i\'?m\s+(good|okay|alright)\s+(on\s+that|thanks)", re.IGNORECASE),
        re.compile(r"(nah|no)\s+(i\'?m|im)\s+(not|good)", re.IGNORECASE),
        re.compile(r"maybe\s+later", re.IGNORECASE),
        re.compile(r"that\'?s\s+(expensive|too\s+much)", re.IGNORECASE),
    ]),

    # Happy reaction triggers
    "fan_subscribes": ("happy_reaction", [
        re.compile(r"(just\s+)?subscribed", re.IGNORECASE),
        re.compile(r"(just\s+)?subbed", re.IGNORECASE),
        re.compile(r"(i\'?ll|will)\s+(subscribe|sub)\s+(?:to|now|rn)", re.IGNORECASE),
        re.compile(r"signed\s+up\s+(?:to|for|on)\s+(?:your|ur|the)?\s*(?:of|onlyfans)", re.IGNORECASE),
        re.compile(r"bought\s+(?:it|ur|your)\s+(?:of|subscription)", re.IGNORECASE),
    ]),
}


# =============================================================================
# WARMUP & VISITING PATTERNS (from ig_state_machine.py)
# =============================================================================

WARMUP_PATTERNS: List[Pattern] = [
    re.compile(r"(?:ok|okay)\s+(?:fine|bet|deal)", re.IGNORECASE),
    re.compile(r"(?:alright|aight)\s+(?:maybe|ill?\s+check)", re.IGNORECASE),
    re.compile(r"(?:thinking|thought)\s+(?:about\s+it|abt\s+it)", re.IGNORECASE),
    re.compile(r"(?:might|may)\s+(?:sub|subscribe|check\s+it)", re.IGNORECASE),
    re.compile(r"(?:how\s+much|whats?\s+(?:the\s+)?price)", re.IGNORECASE),
    re.compile(r"(?:whats?\s+(?:on\s+)?(?:your|ur)\s+of|what\s+do\s+(?:you|u)\s+post)", re.IGNORECASE),
]

VISITING_PATTERNS: List[Pattern] = [
    re.compile(r"visiting", re.IGNORECASE),
    re.compile(r"just here", re.IGNORECASE),
    re.compile(r"in the area", re.IGNORECASE),
    re.compile(r"in town", re.IGNORECASE),
    re.compile(r"there too", re.IGNORECASE),
    re.compile(r"here too", re.IGNORECASE),
    re.compile(r"around here", re.IGNORECASE),
    re.compile(r"nearby", re.IGNORECASE),
    re.compile(r"same spot", re.IGNORECASE),
    re.compile(r"same area", re.IGNORECASE),
    re.compile(r"close by", re.IGNORECASE),
    re.compile(r"im in", re.IGNORECASE),
    re.compile(r"im around", re.IGNORECASE),
    re.compile(r"passing thru", re.IGNORECASE),
    re.compile(r"passin thru", re.IGNORECASE),
]


# =============================================================================
# UTILITY PATTERNS
# =============================================================================

# Message parsing
SPLIT_PATTERN: Pattern = re.compile(r'\s*\|\|\s*')
IMG_TAG_PATTERN: Pattern = re.compile(r'\[IMG:([^\]]+)\]')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def search_patterns(patterns: List[Pattern], text: str) -> bool:
    """Check if any pattern matches the text"""
    for pattern in patterns:
        if pattern.search(text):
            return True
    return False


def find_first_match(patterns: List[Pattern], text: str):
    """Find first matching pattern, return match object or None"""
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            return match
    return None
