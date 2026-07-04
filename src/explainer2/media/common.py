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
    # already_covered: the script-playbook has authors copy the CTA verbatim into their own
    # closing segment, but that segment is numbered s21/s30/etc, never the literal "cta"
    # sentinel — so also check the text itself, or every branded project double-reads its CTA.
    already_covered = any(
        s.get("slide") == "cta" or (spoken_cta and spoken_cta in s.get("text", ""))
        for s in segments
    )
    if spoken_cta and proj.data.get("auto_cta", True) and not already_covered:
        next_id = (max(s["id"] for s in segments) + 1) if segments else 0
        segments.append({"id": next_id, "slide": "cta", "text": spoken_cta})
    return segments
