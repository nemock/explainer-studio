# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/media/common.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""Shared helpers for the narrate stage (Kokoro + operator voiceover + the recorder)."""


def effective_segments(proj, script):
    """The full segment list narrated/recorded: the authored script segments plus an
    auto-appended CTA segment from the brand (so Kokoro, the operator recorder, and the
    operator-narrate path all agree on the same list + ids)."""
    segments = list(script["segments"])
    brand = proj.brand or {}
    spoken_cta = (brand.get("cta") or {}).get("spoken")
    # `auto_cta` (default true) gates the spoken CTA, mirroring the deck CTA slide in deckbuild —
    # set false (scaffold --no-cta) so a branded act sub-segment isn't narrated with a CTA tail.
    if spoken_cta and proj.data.get("auto_cta", True) and not any(s.get("slide") == "cta" for s in segments):
        next_id = (max(s["id"] for s in segments) + 1) if segments else 0
        segments.append({"id": next_id, "slide": "cta", "text": spoken_cta})
    return segments
