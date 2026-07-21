"""
Hero catalog (Phase 2/3) -- the single source of truth for which heroes
exist, their gender, and what their powerup actually does mechanically.

frontend/lib/sprites/heroSprites.js mirrors the *display* metadata (name,
gender, powerup description, pixel sprite) for these same hero ids -- keep
the id strings in sync between both files if you add/rename a hero.
"""

HEROES = {
    "titan_warrior": {
        "name": "Titan Warrick",
        "gender": "male",
        "powerup_name": "Titan's Smash",
        "powerup_description": "Empowers your next answer to land as a guaranteed critical hit.",
        "effect": "force_correct",
    },
    "sage_mage": {
        "name": "Zephyr the Sage",
        "gender": "male",
        "powerup_name": "Arcane Surge",
        "powerup_description": "Doubles the XP earned from your next answer.",
        "effect": "double_xp_next",
    },
    "shadow_rogue": {
        "name": "Kael Shadowstep",
        "gender": "male",
        "powerup_name": "Shadow Step",
        "powerup_description": "Your next imperfect answer is upgraded one tier (incorrect -> partial, partial -> correct).",
        "effect": "verdict_boost_next",
    },
    "valkyrie_warrior": {
        "name": "Freya Ironheart",
        "gender": "female",
        "powerup_name": "Valkyrie's Charge",
        "powerup_description": "Guarantees your next answer lands as a critical hit and heals you to full HP.",
        "effect": "force_correct_heal",
    },
    "mindweave_mage": {
        "name": "Lyra Mindweave",
        "gender": "female",
        "powerup_name": "Mind's Eye",
        "powerup_description": "Reveals a free hint at no token cost and grants bonus XP.",
        "effect": "free_hint_bonus_xp",
        "xp": 20,
    },
    "quickblade_rogue": {
        "name": "Nyx Quickblade",
        "gender": "female",
        "powerup_name": "Silver Tongue",
        "powerup_description": "Instantly restores all of your hint tokens.",
        "effect": "refill_hints",
    },
}

DEFAULT_HERO_ID = "titan_warrior"
POWERUP_MAX_USES_PER_WINDOW = 3
POWERUP_WINDOW_HOURS = 1


def hero_or_default(hero_id: str | None) -> dict:
    return HEROES.get(hero_id, HEROES[DEFAULT_HERO_ID])
