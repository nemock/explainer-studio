# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/presets.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""Per-platform presets (PRD §13) — map a platform to its aspect, a render
resolution, and a safe-zone bottom inset (fraction of height) so captions clear
the platform's UI chrome. `safe_bottom` pushes the kinetic-caption band up.

Caption/hashtag norms (title vs caption, fold length, hashtag caps, link
placement) live in each run's meta.json per-platform object, authored by the skill."""

PLATFORMS = {
    # vertical
    "tiktok":  {"aspect": "9:16", "safe_bottom": 0.20, "min_length": 60},
    "reels":   {"aspect": "9:16", "safe_bottom": 0.22},
    "shorts":  {"aspect": "9:16", "safe_bottom": 0.16},
    "threads": {"aspect": "9:16", "safe_bottom": 0.16},
    # in-feed / horizontal
    "linkedin": {"aspect": "4:5", "safe_bottom": 0.10},
    "youtube":  {"aspect": "16:9", "safe_bottom": 0.08},
    "square":   {"aspect": "1:1", "safe_bottom": 0.12},
}


def resolve(name):
    return PLATFORMS.get(name)
