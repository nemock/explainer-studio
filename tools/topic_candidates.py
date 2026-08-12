#!/usr/bin/env python3
"""Mine the daily-research-ingest corpus for deep-dive topic candidates.

WHY THIS EXISTS (2026-08-12). The channel's two biggest videos share one shape:
a named party, a specific number, and a documented turn (CBA at 24.4 views/day,
Ford, METR). Topic ideas were being generated from recall, while
`daily-research-ingest` had been quietly collecting exactly that kind of story
every day into `make_money/talk_time/external_voices/<date>/_nodes.jsonl` from 59
sources — Reddit niches, Stratechery, Hacker News, MedCity, The Robot Report, and
The Deep View (an AI-focused daily, operator-requested 2026-08-09).

Nobody was reading it for video topics. This does.

It SCORES rather than filters, because the formula is a conjunction:

  + a named company/institution     (the "who")
  + a concrete number               (the "how much")
  + reversal / turn language        (the "what changed")
  + AI relevance                    (the lane that runs 3x channel median)
  - already covered by a project    (dedup against projects/)

Output is a ranked shortlist to take INTO an intel sweep. It is not evidence and
it decides nothing: every candidate still goes through `intel` and the blueprint
gate, where the story gets verified or dropped. Treat a high score as "worth a
sweep," never as "this happened."

  python3 tools/topic_candidates.py            # last 14 days, top 20
  python3 tools/topic_candidates.py --days 30 --top 40
"""
import argparse
import json
import pathlib
import re
import sys

INGEST = pathlib.Path("/Volumes/Casima/claudeCode/make_money/talk_time/external_voices")
PROJECTS = pathlib.Path("/Volumes/Casima/claudeCode/explainer-content/projects")

AI = re.compile(r"\bAI\b|\bLLM\b|agent|chatgpt|claude|openai|anthropic|automat|copilot|"
                r"machine learning|neural|model", re.I)
# Capitalised multi-word orgs, plus a floor of known names so a lowercase mention still counts.
ORG_KNOWN = re.compile(r"\b(Klarna|Duolingo|IBM|Amazon|Google|Microsoft|Meta|Salesforce|Walmart|"
                       r"Intel|Apple|Oracle|Accenture|Deloitte|McKinsey|Shopify|UPS|FedEx|Nvidia|"
                       r"Tesla|Uber|Airbnb|Spotify|Stripe|Cursor|Replit|Lovable|OpenAI|Anthropic|"
                       r"DeepMind|Hugging Face|New Orleans|FDA|EEOC|NHS|Medicare)\b")
ORG_SHAPE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\s+(?:Inc|Corp|Ltd|LLC|Health|Bank|"
                       r"Labs|AI|Systems|Group|Technologies)\b")
NUM = re.compile(r"\b\d[\d,]*(?:\.\d+)?\s*(?:%|percent|million|billion|thousand|k\b|x\b)|"
                 r"\$\s?\d|\b\d{2,}\b")
TURN = re.compile(r"\breversed?\b|\brehir|\bhired .* back\b|\bwalked back\b|\bu-turn\b|\bbacktrack|"
                  r"\bthen\b|\bafter all\b|\bturns out\b|\bquietly\b|\bscrapp?ed\b|\bpaused\b|"
                  r"\bturned off\b|\bcancell?ed\b|\bretract|\babandon|\bshut down\b|\bwithdrew\b",
                  re.I)


def covered_terms():
    """Slugs + titles already scaffolded, so we don't re-pitch a project that exists."""
    terms = set()
    for p in PROJECTS.glob("*/project.json"):
        terms.update(w for w in re.split(r"[^a-z0-9]+", p.parent.name.lower()) if len(w) > 4)
        try:
            t = json.loads(p.read_text()).get("title", "")
            terms.update(w for w in re.split(r"[^a-z0-9]+", t.lower()) if len(w) > 5)
        except Exception:
            pass
    return terms


def score(text):
    s, why = 0, []
    if AI.search(text):
        s += 3; why.append("AI")
    orgs = set(ORG_KNOWN.findall(text)) | set(m.strip() for m in ORG_SHAPE.findall(text))
    if orgs:
        s += 3; why.append("named:" + ",".join(sorted(orgs)[:2]))
    if NUM.search(text):
        s += 2; why.append("number")
    if TURN.search(text):
        s += 3; why.append("turn")
    return s, why


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()

    days = sorted([d for d in INGEST.iterdir() if d.is_dir()])[-a.days:]
    if not days:
        sys.exit(f"no ingest days under {INGEST}")
    cov = covered_terms()
    seen, rows = set(), []
    for d in days:
        f = d / "_nodes.jsonl"
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            try:
                n = json.loads(line)
            except Exception:
                continue
            title = (n.get("title") or n.get("headline") or "").strip()
            if not title or title.lower() in seen:
                continue
            seen.add(title.lower())
            blob = title + " " + str(n.get("summary") or n.get("body") or "")[:600]
            sc, why = score(blob)
            if sc < 6:
                continue
            words = {w for w in re.split(r"[^a-z0-9]+", title.lower()) if len(w) > 5}
            if len(words & cov) >= 2:
                why.append("~already covered")
                sc -= 3
            rows.append((sc, d.name, n.get("source_name") or n.get("source") or "?", title, why,
                         n.get("url", "")))
    rows.sort(key=lambda r: (-r[0], r[1]))
    print(f"{len(rows)} candidates from {len(days)} ingest days "
          f"(score >= 6; AI+named+number+turn = 11)\n")
    for sc, day, src, title, why, url in rows[:a.top]:
        print(f"  [{sc:>2}] {day}  {str(src)[:16]:<16} {title[:78]}")
        print(f"       {' · '.join(why)}")
    print("\nA score is a REASON TO SWEEP, not a finding. Verify at intel + blueprint.")


if __name__ == "__main__":
    main()
