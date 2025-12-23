# -*- coding: utf-8 -*-
"""
IG Image Library

Image mappings, triggers, and file path management for the IG chatbot.
Handles [IMG:filename] parsing and image selection based on conversation context.
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import random
import re


# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
IMAGES_ROOT = PROJECT_ROOT / "data" / "images"


# =============================================================================
# IMAGE CATEGORIES
# =============================================================================

@dataclass
class ImageCategory:
    """An image category with paths and metadata"""
    name: str
    folder: str
    files: List[str]
    description: str

    def get_paths(self) -> List[Path]:
        """Get full paths to all images in this category"""
        return [IMAGES_ROOT / self.folder / f for f in self.files]

    def get_random(self) -> Optional[str]:
        """Get a random filename from this category"""
        if self.files:
            return random.choice(self.files)
        return None


# All image categories
IMAGE_CATEGORIES: Dict[str, ImageCategory] = {
    # Verification - prove she's real
    "verification": ImageCategory(
        name="Verification",
        folder="verification",
        files=[
            "selfie_casual.jpg",
            "selfie_smile.jpg",
            "selfie_peace.jpg",
            "mirror_pic.jpg",
            "selfie_wave.jpg",
        ],
        description="Selfies to prove she's a real person",
    ),

    # Reactions - emotional responses
    "sad_reaction": ImageCategory(
        name="Sad Reaction",
        folder="reactions",
        files=[
            "sad_face.jpg",
            "pouty.jpg",
            "disappointed.jpg",
            "upset.jpg",
        ],
        description="Sad/pouty reactions (e.g., when fan won't subscribe)",
    ),
    "happy_reaction": ImageCategory(
        name="Happy Reaction",
        folder="reactions",
        files=[
            "smile.jpg",
            "blowing_kiss.jpg",
            "wink.jpg",
            "excited.jpg",
            "thank_you.jpg",
        ],
        description="Happy reactions (e.g., when fan subscribes)",
    ),

    # Sob story proof images
    "car_trouble": ImageCategory(
        name="Car Trouble",
        folder="sob_stories",
        files=["car_damage.jpg", "mechanic_bill.jpg", "tow_truck.jpg"],
        description="Car accident/breakdown proof",
    ),
    "sick_pet": ImageCategory(
        name="Sick Pet",
        folder="sob_stories",
        files=["vet_bill.jpg", "sad_pet.jpg", "pet_meds.jpg"],
        description="Sick pet vet bills",
    ),
    "broken_phone": ImageCategory(
        name="Broken Phone",
        folder="sob_stories",
        files=["cracked_phone.jpg", "repair_quote.jpg"],
        description="Cracked phone screen",
    ),
    "rent_trouble": ImageCategory(
        name="Rent Trouble",
        folder="sob_stories",
        files=["eviction_notice.jpg", "landlord_text.jpg"],
        description="Late rent/eviction threat",
    ),
    "phone_bill": ImageCategory(
        name="Phone Bill",
        folder="sob_stories",
        files=["phone_bill.jpg", "shutoff_warning.jpg"],
        description="Phone bill overdue",
    ),
    "medical": ImageCategory(
        name="Medical",
        folder="sob_stories",
        files=["hospital_bill.jpg", "er_bracelet.jpg", "prescription.jpg"],
        description="Medical/ER bills",
    ),
    "hacked": ImageCategory(
        name="Hacked",
        folder="sob_stories",
        files=["bank_statement.jpg", "fraud_alert.jpg"],
        description="Bank account hacked",
    ),
    "empty_fridge": ImageCategory(
        name="Empty Fridge",
        folder="sob_stories",
        files=["empty_fridge.jpg", "empty_pantry.jpg"],
        description="No money for food",
    ),

    # Teases - SFW but suggestive
    "tease": ImageCategory(
        name="Tease",
        folder="teases",
        files=[
            "gym_selfie.jpg",
            "bikini_coverup.jpg",
            "towel_pic.jpg",
            "yoga_pose.jpg",
            "sundress.jpg",
        ],
        description="SFW suggestive teases",
    ),
}


# =============================================================================
# IMAGE TRIGGERS - What triggers sending an image
# =============================================================================

# Mapping from trigger patterns to image categories
IMAGE_TRIGGERS: Dict[str, Tuple[str, List[str]]] = {
    # Verification triggers
    "prove_real": ("verification", [
        r"(are\s+you|u)\s+(real|a\s+bot|fake)",
        r"prove\s+(you\'?re?|ur)\s+real",
        r"(bot|fake|scam)",
        r"too\s+(hot|good)\s+to\s+be\s+real",
        r"catfish",
    ]),
    "casual_pic": ("verification", [
        r"send\s+(a|me\s+a)?\s*pic",
        r"(got\s+)?more\s+pics",
        r"what\s+do\s+you\s+look\s+like",
    ]),

    # Sad reaction triggers
    "fan_refuses": ("sad_reaction", [
        r"(not|no(t)?)\s+(paying|subscribing|gonna|going\s+to)",
        r"i\'?m\s+(good|okay|alright)\s+(on\s+that|thanks)",
        r"(nah|no)\s+(i\'?m|im)\s+(not|good)",
        r"maybe\s+later",
        r"that\'?s\s+(expensive|too\s+much)",
    ]),

    # Happy reaction triggers
    "fan_subscribes": ("happy_reaction", [
        r"(just\s+)?subscribed",
        r"(just\s+)?subbed",
        r"(i\'?ll|will)\s+(check|subscribe|sub)",
        r"signed\s+up",
        r"bought\s+it",
    ]),

    # Sob story triggers (scenario-specific)
    "car_accident": ("car_trouble", [
        r"car",
        r"accident",
        r"crashed",
        r"mechanic",
    ]),
    "sick_pet": ("sick_pet", [
        r"pet|dog|cat|puppy|kitten",
        r"vet",
        r"sick",
    ]),
    "broken_phone": ("broken_phone", [
        r"phone",
        r"screen",
        r"cracked",
        r"broken",
    ]),
    "late_rent": ("rent_trouble", [
        r"rent",
        r"landlord",
        r"evict",
        r"apartment",
    ]),
    "phone_bill": ("phone_bill", [
        r"phone\s+bill",
        r"cut\s+off",
        r"shut\s+off",
    ]),
    "medical_emergency": ("medical", [
        r"hospital",
        r"er|emergency\s+room",
        r"medical",
        r"doctor",
    ]),
    "got_hacked": ("hacked", [
        r"hacked",
        r"bank",
        r"fraud",
        r"stolen",
    ]),
    "no_food": ("empty_fridge", [
        r"food",
        r"groceries",
        r"hungry",
        r"eat",
    ]),
}


# =============================================================================
# SCENARIO TO IMAGE CATEGORY MAPPING
# =============================================================================

SCENARIO_TO_IMAGE: Dict[str, str] = {
    "car_accident": "car_trouble",
    "sick_pet": "sick_pet",
    "broken_phone": "broken_phone",
    "late_rent": "rent_trouble",
    "phone_bill": "phone_bill",
    "medical_emergency": "medical",
    "got_hacked": "hacked",
    "no_food": "empty_fridge",
}


# =============================================================================
# IMAGE FUNCTIONS
# =============================================================================

def get_image_category(category_name: str) -> Optional[ImageCategory]:
    """Get an image category by name"""
    return IMAGE_CATEGORIES.get(category_name)


def get_random_image(category_name: str) -> Optional[str]:
    """Get a random image filename from a category"""
    category = IMAGE_CATEGORIES.get(category_name)
    if category:
        return category.get_random()
    return None


def get_images_for_trigger(trigger_name: str) -> List[str]:
    """Get all image filenames for a specific trigger"""
    if trigger_name in IMAGE_TRIGGERS:
        category_name, _ = IMAGE_TRIGGERS[trigger_name]
        category = IMAGE_CATEGORIES.get(category_name)
        if category:
            return category.files
    return []


def detect_image_trigger(message: str) -> Optional[str]:
    """Detect if a message matches any image trigger pattern"""
    message_lower = message.lower()

    for trigger_name, (category, patterns) in IMAGE_TRIGGERS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower, re.IGNORECASE):
                return trigger_name

    return None


def get_image_for_trigger(message: str) -> Optional[str]:
    """Get a random image based on message trigger detection"""
    trigger = detect_image_trigger(message)
    if trigger:
        return get_random_image(IMAGE_TRIGGERS[trigger][0])
    return None


def get_image_for_scenario(scenario_id: str) -> Optional[str]:
    """Get a random image for a sob story scenario"""
    category_name = SCENARIO_TO_IMAGE.get(scenario_id)
    if category_name:
        return get_random_image(category_name)
    return None


def get_verification_image() -> str:
    """Get a random verification selfie"""
    return get_random_image("verification") or "selfie_casual.jpg"


def get_sad_reaction() -> str:
    """Get a random sad reaction image"""
    return get_random_image("sad_reaction") or "sad_face.jpg"


def get_happy_reaction() -> str:
    """Get a random happy reaction image"""
    return get_random_image("happy_reaction") or "smile.jpg"


def get_tease_image() -> str:
    """Get a random tease image"""
    return get_random_image("tease") or "gym_selfie.jpg"


# =============================================================================
# [IMG:filename] PARSING
# =============================================================================

IMG_TAG_PATTERN = re.compile(r'\[IMG:([^\]]+)\]')


def parse_image_tags(text: str) -> List[Tuple[str, str]]:
    """
    Parse [IMG:filename] tags from text.

    Returns list of (full_tag, filename) tuples.
    """
    matches = []
    for match in IMG_TAG_PATTERN.finditer(text):
        full_tag = match.group(0)  # [IMG:filename.jpg]
        filename = match.group(1)  # filename.jpg
        matches.append((full_tag, filename))
    return matches


def extract_images_from_response(response: str) -> Tuple[str, List[str]]:
    """
    Extract image tags from a response.

    Returns (clean_text, list_of_image_filenames).
    The clean text has the [IMG:...] tags removed.
    """
    images = []
    clean_text = response

    for full_tag, filename in parse_image_tags(response):
        images.append(filename)
        clean_text = clean_text.replace(full_tag, "").strip()

    # Clean up any double spaces or leading/trailing ||
    clean_text = re.sub(r'\|\|\s*\|\|', '||', clean_text)
    clean_text = clean_text.strip('|').strip()

    return clean_text, images


def resolve_image_path(filename: str) -> Optional[Path]:
    """
    Resolve a filename to its full path.

    Searches through all category folders to find the file.
    """
    for category in IMAGE_CATEGORIES.values():
        if filename in category.files:
            path = IMAGES_ROOT / category.folder / filename
            return path

    # Fallback: check if file exists directly in images root
    direct_path = IMAGES_ROOT / filename
    if direct_path.exists():
        return direct_path

    return None


def validate_image_exists(filename: str) -> bool:
    """Check if an image file exists"""
    path = resolve_image_path(filename)
    return path is not None and path.exists()


# =============================================================================
# DIRECTORY SETUP
# =============================================================================

def setup_image_directories():
    """Create the image directory structure if it doesn't exist"""
    folders = set()
    for category in IMAGE_CATEGORIES.values():
        folders.add(category.folder)

    for folder in folders:
        folder_path = IMAGES_ROOT / folder
        folder_path.mkdir(parents=True, exist_ok=True)


# =============================================================================
# TESTING
# =============================================================================

if __name__ == "__main__":
    print("=== IMAGE LIBRARY TEST ===\n")

    # Test categories
    print(f"Image categories: {len(IMAGE_CATEGORIES)}")
    for name, cat in IMAGE_CATEGORIES.items():
        print(f"  - {name}: {len(cat.files)} images")

    # Test triggers
    print(f"\nImage triggers: {len(IMAGE_TRIGGERS)}")

    # Test trigger detection
    test_messages = [
        "are you real?",
        "prove you're real",
        "you're too hot to be real lol",
        "nah im not paying for that",
        "just subscribed!",
        "can you send me a pic",
    ]

    print("\n--- Trigger Detection ---")
    for msg in test_messages:
        trigger = detect_image_trigger(msg)
        img = get_image_for_trigger(msg) if trigger else None
        print(f"  '{msg}' -> trigger={trigger}, image={img}")

    # Test [IMG:] parsing
    print("\n--- Image Tag Parsing ---")
    test_response = "lol here||[IMG:selfie_casual.jpg]||happy now?"
    clean, images = extract_images_from_response(test_response)
    print(f"  Input: {test_response}")
    print(f"  Clean text: {clean}")
    print(f"  Images: {images}")

    # Test scenario images
    print("\n--- Scenario Images ---")
    for scenario_id in SCENARIO_TO_IMAGE.keys():
        img = get_image_for_scenario(scenario_id)
        print(f"  {scenario_id} -> {img}")

    print("\n=== TEST COMPLETE ===")
