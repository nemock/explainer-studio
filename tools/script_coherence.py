#!/usr/bin/env python3
"""script_coherence.py — the mechanical half of the pre-booth COHERENCE pass
(references/spoken-humanizer.md §C4).

Exists because §C4 said "go card by card and check that every sentence is complete" and
trusted the author's eye, and on #56 the eye passed eight verbless noun-stacks and two
bare numerals straight to the operator, who caught them on card one:

    "Game development, product design, architecture, data analysis, video animation."
    "Real job, ordinary week."
    "deal with these forty"          <- forty WHAT

Every one is invisible to a rhythm check (they are not short) and to a blocklist (the
words are fine). They need a parser, so this runs one.

COVERS EVERY CARD THE BOOTH WILL SHOW, not just script.json. The first version checked
the script alone and a defective Short hook went straight past it to the operator
(card 88, #56). Dave's ruling, and it is the general rule:

    "Of course it should apply to shorts. It should apply to all writing. That is
    literally the point of writing a script. Putting an intro and an outro on a portion
    of the script to construct a short doesn't eliminate the need to write well."

So the card list here mirrors recorder.py's: script.json segments, then each Short's
hook and outro from shorts/plan.json, in booth order. Card numbers in this report ARE
the booth's card numbers, so a hit can be found where the operator would see it.

Usage:  python3 tools/script_coherence.py <project_dir>
Exit:   0 = clean, 1 = something to fix, 2 = the check could not run

Requires spaCy + en_core_web_sm. If they are missing this exits 2 rather than passing:
a coherence gate that silently degrades is how the defect it catches got shipped.
"""
import json
import re
import sys
from pathlib import Path

# The real test the VO dial states is "if a sentence needs a breath MID-CLAUSE, split it" —
# which is about unbroken runs, not total length. A flat 23-word cap was standing in for
# that, and the substitution backfired (operator directive 2026-08-11): capping length
# produced exactly the staccato the checker exists to prevent. Module 1's first draft came
# out at a 10.4-word mean with 52% of sentences at ten words or under and NOT ONE over 23,
# because the cap wrote the prose. Dave: "these are effectively long-form spoken essays...
# not just a series of one-liners, missing verbs and pronouns that don't appear to point at
# anything, staccato language that doesn't feel natural."
#
# So measure the thing the dial actually cares about: the longest stretch with no internal
# punctuation to breathe at. A 40-word sentence with three commas is comfortable aloud; a
# 26-word sentence with none is not.
MAX_UNBROKEN = 24   # words in a row with no comma/semicolon/colon/dash to breathe at
MAX_WORDS = 45      # a genuine outlier even for a flowing spoken essay

# Recorded cold, one card per take, so an opening PRONOUN has nothing to attach to. The #55
# verdict was specifically about that: "a pronoun at the start of a section, hanging in
# space... lazy writing I'd expect from a 9th grader." Existential "there's" is fine.
#
# CONNECTIVES were removed from this set 2026-08-11. They were never the #55 defect, and
# banning them forbids ordinary conversational English — humaner's own FORMATS.md VO dial
# says the opposite in as many words: "Keep the spoken texture that survives naturally:
# sentence-initial And/So." A card opening "And the meeting feels fine" names its subject
# immediately and hangs in nothing.
BAD_OPENERS = {"it", "this", "that", "these", "those", "they", "them", "he", "she"}

NUMBER_WORDS = ("forty", "fifty", "sixty", "seventy", "eighty", "ninety", "hundred",
                "thousand", "million", "dozen")


# U.S. English is a hard constraint on everything under the byline (humaner VOICE.md
# §4.0). It lived only in an operator memory until 2026-08-28 — and that memory wrongly
# claimed it was already codified — so nothing in the drafting path enforced it and
# `-ise` spellings reached a recorded script, the burned-in captions and an on-screen
# card. A prose rule fires on recall, and recall fails exactly when attention is on the
# argument. This is the mechanical half.
#
# Spelling only. The singular-verb half of the rule ("Google runs", never "Google run")
# needs a parser and a company list, and a naive check flags far more good prose than bad.
BRITISH = {
    "optimise": "optimize", "optimised": "optimized", "optimising": "optimizing",
    "recognise": "recognize", "recognised": "recognized", "recognising": "recognizing",
    "realise": "realize", "realised": "realized", "realising": "realizing",
    "organise": "organize", "organised": "organized", "organising": "organizing",
    "prioritise": "prioritize", "prioritised": "prioritized",
    "apologise": "apologize", "apologised": "apologized",
    "analyse": "analyze", "analysed": "analyzed", "analysing": "analyzing",
    "summarise": "summarize", "summarised": "summarized",
    "categorise": "categorize", "emphasise": "emphasize", "utilise": "utilize",
    "behaviour": "behavior", "colour": "color", "favour": "favor", "honour": "honor",
    "labour": "labor", "rumour": "rumor", "neighbour": "neighbor",
    "centre": "center", "centred": "centered", "metre": "meter", "theatre": "theater",
    "defence": "defense", "offence": "offense", "licence": "license",
    "travelled": "traveled", "cancelled": "canceled", "modelling": "modeling",
    "labelled": "labeled", "whilst": "while", "amongst": "among", "learnt": "learned",
    "practise": "practice", "programme": "program", "grey": "gray",
}


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def words(text):
    return re.findall(r"[A-Za-z0-9''\-]+", text)


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip())
    try:
        import spacy
    except ImportError:
        sys.exit("[2] spaCy not installed — cannot run the coherence check.\n"
                 "    pip install spacy && python -m spacy download en_core_web_sm")
    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        sys.exit("[2] en_core_web_sm missing — python -m spacy download en_core_web_sm")

    pdir = Path(sys.argv[1]).resolve()
    script = pdir / "script.json"
    if not script.exists():
        sys.exit(f"[2] no script.json in {pdir}")
    segs = json.loads(script.read_text())["segments"]

    # The booth's card list, in the booth's order (recorder.py _cards): every script
    # segment, then each Short's hook and outro. Everything here gets read aloud, so
    # everything here gets checked.
    cards = [(f"card {s['id'] + 1} (seg {s['id']})", s.get("text", "")) for s in segs]
    plan_path = pdir / "shorts" / "plan.json"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        if isinstance(plan, list):
            for cut in plan:
                for role in ("hook", "outro"):
                    if cut.get(role):
                        cards.append((f"card {len(cards) + 1} ({cut.get('slug', '?')} {role})",
                                      cut[role]))

    fragments, openers, longs, colons, bare, british = [], [], [], [], [], []

    for card, text in cards:

        for w_ in re.findall(r"[A-Za-z]+", text):
            us = BRITISH.get(w_.lower())
            if us:
                british.append(f"{card}: {w_!r} -> {us!r}")

        # A demonstrative followed by its own noun ("That meeting feels fine") is not a
        # pronoun hanging in space — it names the thing in the same breath. Only flag the
        # bare form, which is the #55 defect.
        w = words(text)
        # Strip the apostrophe too: "It's" must match "it". It did not, which is why the
        # canonical #55 defect ("It's doing its actual job...") walked past this check
        # for its whole life. Caught by a regression test 2026-08-11.
        first = re.sub(r"[^a-z]", "", (w or [""])[0].lower())
        second = re.sub(r"[^a-z']", "", w[1].lower()) if len(w) > 1 else ""
        names_its_noun = first in {"this", "that", "these", "those"} and second not in {
            "is", "isn't", "was", "wasn't", "means", "meant", "sits", "sounds", "makes",
            "tells", "leaves", "looks", "keeps", "gets", "brings", "does", "doesn't"}
        if first in BAD_OPENERS and not names_its_noun:
            openers.append(f"{card}: opens on '{w[0]}' — a bare pronoun with nothing to attach to")

        # (?!-) so "the ninety-six percent" isn't read as a bare "the ninety"
        for m in re.finditer(r"\b(?:the|these|those)\s+(" + "|".join(NUMBER_WORDS) + r")\b(?!-)", text):
            tail = text[m.end():m.end() + 18].lstrip()
            if not tail or not re.match(r"[a-z]", tail):
                bare.append(f"{card}: '{m.group(0)}' — a count standing in for a noun")

        for sent in sentences(text):
            n = len(words(sent))
            # The breath test: the longest stretch with no punctuation to pause at.
            runs = [len(words(chunk)) for chunk in re.split(r"[,;:]| - ", sent)]
            unbroken = max(runs) if runs else 0
            if n > MAX_WORDS:
                longs.append(f"{card} ({n}w, outlier): {sent}")
            elif unbroken > MAX_UNBROKEN:
                longs.append(f"{card} ({unbroken}w unbroken): {sent}")
            if ":" in sent:
                colons.append(f"{card}: {sent}   (no sound for a colon)")

            doc = nlp(sent)
            finite = [t for t in doc if t.pos_ in ("VERB", "AUX")
                      and "Ger" not in t.morph.get("VerbForm", [])
                      and "Inf" not in t.morph.get("VerbForm", [])]
            imperative = any(t.pos_ == "VERB" and t.dep_ == "ROOT"
                             and not [c for c in t.children if c.dep_.startswith("nsubj")]
                             for t in doc)
            if not finite and not imperative:
                fragments.append(f"{card}: {sent}")

    n_sent = sum(len(sentences(t)) for _, t in cards)
    n_short = len(cards) - len(segs)
    print(f"script coherence — {pdir.name}  ({len(cards)} booth cards "
          f"[{len(segs)} script + {n_short} shorts hook/outro], {n_sent} sentences)")

    groups = [
        ("VERBLESS SENTENCES (a noun-stack where a sentence belongs)", fragments),
        ("BARE NUMERALS (a count with no noun)", bare),
        ("COLD-OPEN VIOLATIONS (card opens on a bare pronoun)", openers),
        (f"BREATHLESS (over {MAX_UNBROKEN}w with no pause, or over {MAX_WORDS}w total)", longs),
        ("MID-SENTENCE COLONS", colons),
        ("BRITISH SPELLING (U.S. English is binding, VOICE.md 4.0)", british),
    ]
    bad = 0
    for label, hits in groups:
        bad += len(hits)
        print(f"\n  [{'FAIL' if hits else 'PASS'}] {label}: {len(hits)}")
        for h in hits:
            print(f"      {h}")

    if fragments:
        print("\n  NOTE: the parser mis-tags the odd verb as a noun ('span', 'promises'),")
        print("  so expect one or two false positives here. Read each one; do NOT add an")
        print("  auto-filter — every filter tried on this list also hid real fragments.")

    print(f"\n  {'CLEAN' if not bad else f'{bad} to fix before the booth'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
