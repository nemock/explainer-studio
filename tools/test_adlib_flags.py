#!/usr/bin/env python3
"""The re-record flag holds a render and texts the operator's phone, so it has to mean the
take really needs the mic. Every case below is a real card from the catalog's reports.

Run: PYTHONPATH=src ~/myenv/bin/python3.12 tools/test_adlib_flags.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from explainer2.media.adlib import _drift, classify, rerecord_confirmed  # noqa: E402

CARD_11 = ("Even something as short as two plus two equals four becomes seven tokens. Longer "
           "numbers get chopped into chunks, counting from the left. One million, two hundred "
           "thirty-four thousand, five hundred sixty-seven becomes one-two-three, four-five-six, "
           "and seven. Your calculator sees every digit in its own column, and the chatbot sees "
           "three chunks that don't line up with the columns at all.")
CARD_11_ASR = ("Even something as short as 2 plus 2 equals 4 becomes 7 tokens. Longer numbers get "
               "chopped into chunks counting from the left. 1,234,567 becomes 1,2,3,4,5,6,7. Your "
               "calculator sees every digit in its own column, and the chatbot sees three chunks "
               "that don't line up with the columns at all.")

# Clean takes the old drift-only rule flagged: none of these should ask for the mic.
NOT_RERECORD = [
    (CARD_11, CARD_11_ASR),
    ("The F-D-A approved Edwards Lifesciences' Sapien 3 platform for asymptomatic patients.",
     "The FDA approved Edwards Life Sciences' Sapien III platforms for asymptomatic patients."),
    ("A license is enforceable. A promise is not.", "A license is enforceable, a promise isn't."),
    ("Home Depot runs about two point two three. Best Buy, one point eight two.",
     "Home Depot runs about 2.23, Best Buy 1.82."),
    ("Stripe bought the position.", "Straight bought the position."),
    ("Expired.", "All expired."),
    ("The American Medical Association gave CaRi-Heart two CPT codes, effective January first, "
     "twenty twenty-six. Oh nine nine two T, and oh nine nine three T.",
     "The American Medical Association gave Cara Hart two CPT codes effective January 1st, 2026, "
     "0992T and 0993T."),
    ("Ten x faster is when people actually switch.", "10x faster is when people actually switch."),
    ("Twenty-five hundred units sold, by one person.", "2500 units sold by one person."),
]

# Takes that lost the card's words: these must still flag.
RERECORD = [
    # #59 card 1: the take cut off after the first sentence.
    ("Sometime in the last year, you repeated a statistic you never checked. So did I. You saw a "
     "number in a headline, it matched something you already suspected, and a week later you said "
     "it in a meeting as if you had read the study yourself. Nobody asked you where it came from.",
     "Sometime in the last year you repeated a statistic you never checked."),
    # The wrong card read into the booth.
    ("Lean checks exactly the statement it's given.", "Your calculator adds with one fixed method."),
]


def main():
    bad = 0
    for script, asr in NOT_RERECORD:
        status = classify(_drift(script, asr), script, asr)
        if status == "rerecord":
            print(f"FALSE ALARM: {script[:60]!r} -> {rerecord_confirmed(script, asr)[1]}")
            bad += 1
    for script, asr in RERECORD:
        status = classify(_drift(script, asr), script, asr)
        if status != "rerecord":
            print(f"MISSED: {script[:60]!r} -> {status}, drift {_drift(script, asr)}")
            bad += 1
    drift = _drift(CARD_11, CARD_11_ASR)
    if drift >= 0.15:
        print(f"NUMBER NORMALIZER: card 11 still scores {drift}")
        bad += 1
    assert _drift("one million two hundred thirty four thousand five hundred sixty seven",
                  "1,234,567") == 0.0
    print("FAILED" if bad else f"OK: {len(NOT_RERECORD)} clean takes, {len(RERECORD)} real re-records")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
