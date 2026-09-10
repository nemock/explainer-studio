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


# U.S. English is a hard constraint on everything under the byline (humaner CONSTRAINTS.md
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
    # VOCABULARY, not spelling (added 2026-08-31, module 4). The -ise/-our/-re list
    # above passed a script that opened card two on "a fortnight later", because
    # "fortnight" is spelled the same on both sides of the Atlantic and is simply not
    # a word Americans say. Idiom is the other half of U.S. English and the checker
    # was only covering one.
    "fortnight": "two weeks", "fortnightly": "every two weeks",
    "maths": "math", "aeroplane": "airplane", "aluminium": "aluminum",
    "sceptic": "skeptic", "sceptical": "skeptical", "storey": "story (floor)",
    "kerb": "curb", "tyre": "tire", "pyjamas": "pajamas", "cheque": "check",
    "chuffed": "pleased", "rubbish": "garbage / nonsense",
    "straightaway": "right away", "queueing": "lining up",
}

# The OTHER other half of U.S. English: multi-word CONSTRUCTION. BRITISH above is a
# single-word lookup, so it cannot see an idiom, and on #59 (2026-09-10) the operator
# rejected a cold open reading "I'm not being clever about that" — every word of which
# is spelled identically on both sides of the Atlantic. Dave: "I don't think I've ever
# said that in my life. Maybe that's something that someone in the UK might say, but
# definitely not very common from an American English standpoint."
#
# HONEST LIMIT, stated here so nobody trusts this check further than it goes: a
# blocklist catches PHRASES SOMEBODY ALREADY SHIPPED. It would not have caught that
# cold open before the fact, because "being clever about" is not a standard British
# idiom — it is just an odd construction. The general class ("does this sound like an
# American said it out loud") needs the fresh-eyes reviewer, whose brief now asks for
# it. This table is the mechanical half, and like BRITISH it earns its keep by
# accreting whatever actually reaches a script.
IDIOM = {
    r"\bbeing clever about\b": "just say the thing (#59, 2026-09-10)",
    r"\bdifferent to\b": "different from",
    r"\bin future\b": "in the future",
    r"\btakes? a decision\b": "make a decision",
    r"\btook a decision\b": "made a decision",
    r"\bin hospital\b": "in the hospital",
    r"\bat university\b": "in college",
    r"\bon the cards\b": "in the cards",
    r"\bhave a go\b": "give it a try",
    r"\bspot on\b": "exactly right",
    r"\bstraight away\b": "right away",
    r"\bw(?:as|ere) sat\b": "was sitting",
    r"\bw(?:as|ere) stood\b": "was standing",
    r"\b(?:I|you|we|they)'ve not\b": "haven't",
    r"\bfull stop\b": "period",
    r"\bgone missing\b": "disappeared",
    r"\bdid wonder\b": "emphatic-do reads British; 'I wondered', or make it active",
    r"\bkeen to\b": "eager to",
    r"\bcar park\b": "parking lot",
    r"\blorry\b": "truck",
    r"\bpetrol\b": "gas",
}


# LINT.md §8: negative parallelism in its three shapes. All of them stage a misconception
# and then correct it, which implies the reader was thinking wrong, so the rule is **at most
# one per piece** and only where a real misconception is being corrected.
#
# The rule existed long before this check. What did not exist was anything that COUNTS, and
# a cap nobody counts is not a cap: #59 reached the booth with five instances, and the
# operator caught it by ear on card 3 ("The problem isn't the report. The problem is what
# happened to it on the way to you."). LINT names the shape; every instance is individually
# legal; nothing added them up.
#
# The third shape is the one that needs a sentence PAIR, because it stacks across a period
# ("It is not being wrong. It's being convenient."), and that is the form our scripts
# actually reach for.
#
# CARVE-OUT, and it must be declared rather than guessed. A segment may carry
# "lint_allow": ["negative-parallelism"] to exempt itself; those are reported separately and
# do not count against the cap. This exists because #59 card 28 quotes the source report's
# own wording ("directionally accurate, based on individual interviews rather than official
# company reporting") — a real exemption that no heuristic could distinguish from an authored
# reframe, since a spoken script carries no quotation marks. Declaring it puts the judgment
# in the script where a reader can audit it.
NEGPAR_CAP = 1
NEGPAR_INLINE = [
    (r"\bnot (?:only|just|merely)\b[^.!?]*?(?:,\s*)?\b(?:but|it's|it is)\b", "not only X, but Y"),
    (r"\b(?:isn't|is not|aren't|are not|wasn't|was not)\b[^.!?]*?\bbut\b", "not X, but Y"),
    (r"\brather than\b", "X rather than Y"),
]
# sentence A negates a copula; sentence B immediately re-asserts one
NEGPAR_A = re.compile(r"\b(?:isn't|is not|aren't|are not|wasn't|was not|not)\b", re.I)
NEGPAR_B = re.compile(r"^(?:it's|it is|that's|that is|the \w+ is|the \w+'s)\b", re.I)


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

    # keyed exactly as the card list above, so a declared carve-out lands on the right card
    allow_by_card = {f"card {sg['id'] + 1} (seg {sg['id']})": sg["lint_allow"]
                     for sg in segs if sg.get("lint_allow")}
    fragments, openers, longs, colons, bare, british, doubled, idiom = [], [], [], [], [], [], [], []
    negpar, negpar_declared = [], []
    empty = []

    for card, text in cards:

        # A card with no words at all. Every other check in this file asks whether the
        # sentences on a card are any good; not one of them asked whether the card HAS a
        # sentence, so an empty card sailed through all of them and reached the booth,
        # where the operator was shown a blank card to read (module 4 card 52,
        # 2026-08-31). The cause was an edit that blanked a card's text instead of
        # deleting the card, which is invisible to a parser looking at sentences: there
        # were none to look at. Cheap check, and it fires before anyone stands at a mic.
        if not text.strip():
            empty.append(f"{card}: no text at all — blanked by an edit instead of deleted?")
            continue

        # a repeated word or two-word phrase back to back, which is almost always a
        # leftover from an edit rather than emphasis. Real emphasis repeats ACROSS a
        # sentence break ("...the ladder. The ladder was measuring..."), so only flag a
        # repeat with no punctuation between the two halves.
        for m_ in re.finditer(r"\b(\w+(?:\s+\w+)?)\s+\1\b", text, re.I):
            if m_.group(1).lower() not in ("that", "had", "so"):
                doubled.append(f"{card}: {m_.group(0)!r}")

        for w_ in re.findall(r"[A-Za-z]+", text):
            us = BRITISH.get(w_.lower())
            if us:
                british.append(f"{card}: {w_!r} -> {us!r}")

        for pat, us in IDIOM.items():
            for m_ in re.finditer(pat, text, re.I):
                idiom.append(f"{card}: {m_.group(0)!r} -> {us}")

        # LINT.md §8 negative parallelism, counted against a cap of one per script.
        np_hits = []
        for pat, shape in NEGPAR_INLINE:
            for m_ in re.finditer(pat, text, re.I):
                np_hits.append(f"{shape}: {m_.group(0).strip()!r}")
        sents = sentences(text)
        for a_, b_ in zip(sents, sents[1:]):
            if NEGPAR_A.search(a_) and NEGPAR_B.match(b_.strip()):
                np_hits.append(f"stacked across a period: {a_.strip()!r} / {b_.strip()!r}")
        if np_hits:
            declared = "negative-parallelism" in (allow_by_card.get(card) or [])
            for h in np_hits:
                (negpar_declared if declared else negpar).append(f"{card}: {h}")

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
        ("EMPTY CARDS (a card with no words on it)", empty),
        ("VERBLESS SENTENCES (a noun-stack where a sentence belongs)", fragments),
        ("BARE NUMERALS (a count with no noun)", bare),
        ("COLD-OPEN VIOLATIONS (card opens on a bare pronoun)", openers),
        (f"BREATHLESS (over {MAX_UNBROKEN}w with no pause, or over {MAX_WORDS}w total)", longs),
        ("MID-SENTENCE COLONS", colons),
        ("BRITISH SPELLING (U.S. English is binding, CONSTRAINTS.md 4.0)", british),
        ("BRITISH IDIOM/CONSTRUCTION (a blocklist of what has actually shipped)", idiom),        ("DOUBLED WORD/PHRASE (an edit artifact, not emphasis)", doubled),
    ]
    bad = 0
    for label, hits in groups:
        bad += len(hits)
        print(f"\n  [{'FAIL' if hits else 'PASS'}] {label}: {len(hits)}")
        for h in hits:
            print(f"      {h}")

    # A CAP, not a zero check: LINT.md §8 allows exactly one, so only the OVERAGE is a
    # failure. Every instance is printed regardless, because the author has to choose which
    # one survives, and that choice needs the list in front of them.
    over = max(0, len(negpar) - NEGPAR_CAP)
    bad += over
    print(f"\n  [{'FAIL' if over else 'PASS'}] NEGATIVE PARALLELISM "
          f"(LINT.md 8: at most {NEGPAR_CAP} per script): {len(negpar)}")
    for h in negpar:
        print(f"      {h}")
    if over:
        print(f"      -> {over} over the cap. Keep the one that corrects a real")
        print("         misconception; rewrite the rest with an active verb and a concrete")
        print("         noun (CRAFT.md 4), or state the fact and let the reader compare (6).")
    for h in negpar_declared:
        print(f"      [declared carve-out, not counted] {h}")

    if fragments:
        print("\n  NOTE: the parser mis-tags the odd verb as a noun ('span', 'promises'),")
        print("  so expect one or two false positives here. Read each one; do NOT add an")
        print("  auto-filter — every filter tried on this list also hid real fragments.")

    print(f"\n  {'CLEAN' if not bad else f'{bad} to fix before the booth'}")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
