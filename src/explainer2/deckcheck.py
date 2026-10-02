"""deckcheck — everything about a deck that can be known BEFORE anyone records it.

Why this exists (2026-10-01). Every check that could tell an author "this slide will be
empty" ran against the BUILT render spec, and the spec needs work/segments.json, which
only exists after the narration has been recorded and synthesised. So the first time a
deck was checked was after the operator had spent his time at the microphone:

  * FWF daily 2026-09-29: two compare slides authored as `"sides": [A, B]` rendered
    empty; found after recording, and the episode sat blocked for two days.
  * The same slip shipped, unnoticed, in 22 published dailies (2026-09-03 to 09-28).
  * Robot Roundup 2026-09-23: rendered at 180.37 s against a hard 180 s wall; blocked
    for 30 hours over 0.37 s, after recording.

This builds the same spec the renderer builds, against a stand-in timeline estimated
from the script's word counts, and runs the renderer's own checks on it. Nothing is
rendered, no model is loaded, and nothing is written into the project except
work/deckcheck.json. It takes about a second.

What it reports:
  PROBLEMS (exit 1; do not open the booth)
    - a script segment that names a slide the deck does not have
    - a slide that would render with nothing on it          (slidecheck.check_spec)
    - a malformed figure mark or annotation                 (the render's mark contract)
    - an authored field a paper component never receives    (the render's field contract)
    - a structured field (a list or an object) that ANY component drops: content the
      author wrote that would not reach the screen
    - a projected length over the project's max_length, at this show's usual pace
  WARNINGS (exit 0; read them)
    - a dropped text or cosmetic field (a kicker a component does not draw, an accent)
    - a deck slide no script segment uses
    - a projected length under min_length, or over max_length only at a slow pace

The length projection uses the operator's OWN pace: words per second measured from the
finished episodes in the same outputs directory, falling back to a fixed pace when there
are none. It is a planning check, not a target (length is an outcome of the script).
"""
import json
import re
import statistics
import tempfile
from pathlib import Path

from . import remotion_engine as E
from . import slidecheck

FALLBACK_WPS = 2.5             # words per second when a show has no finished episodes yet
FALLBACK_WPS_WALL = 2.27       # ...and when it also has a hard max_length (measured on RRP #1)
SLOW_FACTOR = 0.9              # "a slow day": 10% under the usual pace
OVERHEAD_S = 3.0               # what the render adds to the narration, absent any history
MAX_MARGIN = 0.97              # a hard wall needs room: the projection must clear it by 3%
SIBLINGS = 10                  # how many finished episodes set the pace
# Dropped fields that are decoration, not content. Losing one is worth a line, not a stop.
COSMETIC = ("accent", "accent2", "accentRed", "kind", "align", "band", "anchor", "ordered",
            "mark")           # a highlight's `mark` styles words that still print
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’.,%$-]*")


def _words(text):
    return len(_WORD.findall(text or ""))


class _DryProject:
    """The real project, with `work` pointed at a scratch directory, so build_spec reads
    the stand-in segments.json and never touches (or needs) the real work/ files."""

    def __init__(self, proj, work):
        self._p = proj
        self._work = Path(work)

    @property
    def work(self):
        return self._work

    def __getattr__(self, name):
        return getattr(self._p, name)


def _dropped_any(sid, slide, theme):
    """Fields authored on `slide` that its component never receives, for EVERY component.
    remotion_engine._dropped_field_problems is the same probe restricted to Paper*, where
    a miss blocks the render; this is the advisory, pre-booth version of it."""
    if not isinstance(slide, dict) or slide.get("component"):
        return []
    emit = lambda s: E._scene_for(s, theme=theme, warn=lambda _m: None)   # noqa: E731
    try:
        base = emit(slide)
    except Exception:
        return []

    def received(k, v):
        try:
            if emit({kk: vv for kk, vv in slide.items() if kk != k}) != base:
                return True
            return emit({**slide, k: E._perturbed(v)}) != base
        except Exception:
            return True

    got, dropped = [], []
    for k, v in slide.items():
        if k in E._READ_OUTSIDE_TYPE_MAP or k.endswith("_9x16") or v in (None, "", [], {}):
            continue
        (got if received(k, v) else dropped).append(k)
    return [(k, base[0]) for k in dropped if not any(slide[k] == slide[g] for g in got)]


def pace(proj):
    """(words per second, seconds the render adds to the narration, episodes measured).

    Both come from the finished episodes beside this one. The second number matters as
    much as the first: the render is longer than the narration by the title panel and
    whatever the show closes on, and that differs by show (about 2.4 s on the FWF daily,
    about 8.4 s on Robot Roundup, which is most of how its first episode landed 0.37 s
    over a 180 s wall).

    With no history, a show that has a hard max_length is projected at the SLOW default:
    a wall is the one place an optimistic guess costs a re-record."""
    rates, extra = [], []
    try:
        siblings = sorted((d for d in proj.dir.parent.iterdir()
                           if d.is_dir() and d != proj.dir), reverse=True)
    except OSError:
        siblings = []
    for d in siblings:
        try:
            seg = json.loads((d / "work" / "segments.json").read_text())
            n = sum(_words(s.get("text", "")) for s in seg["segments"])
            if n < 40 or seg.get("duration", 0) <= 10:
                continue
            rates.append(n / float(seg["duration"]))
        except (OSError, ValueError, KeyError, TypeError):
            continue
        try:
            man = json.loads((d / "manifest.json").read_text())
            dur = man.get("duration_s") or man.get("duration")
            if dur and 0 <= float(dur) - float(seg["duration"]) < 60:
                extra.append(float(dur) - float(seg["duration"]))
        except (OSError, ValueError, TypeError):
            pass
        if len(rates) >= SIBLINGS:
            break
    over = statistics.median(extra) if extra else OVERHEAD_S
    if len(rates) >= 2:
        return statistics.median(rates), over, len(rates)
    return (FALLBACK_WPS_WALL if proj.max_length else FALLBACK_WPS), over, 0


def run(proj):
    problems, warnings = [], []
    try:
        script = json.loads(proj.script_json.read_text())["segments"]
        deck = json.loads(proj.deck_json.read_text())["slides"]
    except (OSError, ValueError, KeyError) as e:
        return {"ok": False, "problems": [f"cannot read script.json / deck.json: {e}"],
                "warnings": [], "projection": None}
    theme = proj.data.get("theme", "")
    by_id = {s.get("id"): s for s in deck}

    used = set()
    for seg in script:
        sid = seg.get("slide")
        used.add(sid)
        if sid not in by_id:
            problems.append(f"segment {seg.get('id')} (booth card {int(seg.get('id', 0)) + 1}) "
                            f"names slide `{sid}`, which deck.json does not have: it would "
                            f"render as an empty card")
    for s in deck:
        # A closing card is appended to the narration by the brand's CTA, not by a
        # script segment, so it is expected to be unused here.
        if s.get("id") not in used and s.get("type") != "cta":
            warnings.append(f"{s.get('id')}: no script segment uses this slide, so it never appears")

    # The stand-in timeline: each segment as long as its words take at this show's pace.
    wps, overhead, measured = pace(proj)
    t, segs = 0.0, []
    for seg in script:
        dur = max(1.0, _words(seg.get("text", "")) / wps)
        segs.append({"id": seg.get("id"), "slide": seg.get("slide"),
                     "text": seg.get("text", ""), "start": round(t, 3), "end": round(t + dur, 3)})
        t += dur
    total_words = sum(_words(s.get("text", "")) for s in script)

    spec = None
    with tempfile.TemporaryDirectory(prefix="deckcheck-") as td:
        (Path(td) / "segments.json").write_text(json.dumps(
            {"sample_rate": 48000, "duration": round(t, 3), "segments": segs}))
        try:
            spec = E.build_spec(_DryProject(proj, td))
        except (E.MalformedMarkError, E.DroppedFieldError) as e:
            problems += list(e.problems)
        except Exception as e:                       # noqa: BLE001
            problems.append(f"the render spec could not be built from this deck "
                            f"({type(e).__name__}: {e}); the render would fail the same way")
    if spec is not None:
        for w in spec.get("_warnings") or []:
            warnings.append(str(w))
    # Empty and overlong slides, checked one scene per SEGMENT rather than on the built
    # spec: the engine inserts a title panel and stings, so a built scene's index is not
    # the booth card's, and a finding that names the wrong card sends the author to fix
    # the wrong slide. Same mapping, same check, 1:1 with what he will read aloud.
    per = []
    for seg in script:
        try:
            comp, fields = E._scene_for(by_id.get(seg.get("slide")) or {}, theme=theme,
                                        warn=lambda _m: None)
        except Exception:                            # noqa: BLE001 - build_spec reported it
            comp, fields = "?", {"headline": "?"}
        per.append({"component": comp, "fields": fields})
    blank, overlong = slidecheck.check_spec({"scenes": per})
    for msg in blank + overlong:
        m = re.match(r"scene (\d+) ", msg)
        i = int(m.group(1)) if m else -1
        if 0 <= i < len(script) and script[i].get("slide") in by_id:
            problems.append(f"{script[i]['slide']} (booth card {i + 1}): {msg}")

    for s in deck:
        for k, comp in _dropped_any(s.get("id"), s, theme):
            structured = isinstance(s.get(k), (list, dict)) and k not in COSMETIC
            line = (f"{s.get('id')}: `{k}` is authored on this {s.get('type') or 'untyped'} "
                    f"slide, but {comp} never receives it, so it would not appear on screen")
            if comp.startswith("Paper"):
                continue                              # build_spec already raised for these
            (problems if structured else warnings).append(line)

    typical = total_words / wps + overhead
    slow = total_words / (wps * SLOW_FACTOR) + overhead
    proj_info = {"words": total_words, "words_per_second": round(wps, 2),
                 "render_adds_s": round(overhead, 1),
                 "measured_from_episodes": measured, "projected_s": round(typical, 1),
                 "projected_slow_s": round(slow, 1),
                 "min_length": proj.min_length, "max_length": proj.max_length}
    basis = (f"{total_words} words at {wps:.2f} words/s "
             + (f"(your pace over the last {measured} episodes here)" if measured
                else "(no finished episodes here yet; a default pace)"))
    if proj.max_length:
        if typical > proj.max_length * MAX_MARGIN:
            problems.append(
                f"projected length {typical:.0f} s is over the {proj.max_length} s limit "
                f"({basis}; the limit needs {100 - int(MAX_MARGIN * 100)}% clearance). Cut "
                f"content from the script now: after recording, the only fix is a re-record.")
        elif slow > proj.max_length:
            warnings.append(
                f"projected length is {typical:.0f} s, but a slow read would reach "
                f"{slow:.0f} s, over the {proj.max_length} s limit ({basis})")
    if proj.min_length and typical < proj.min_length:
        warnings.append(f"projected length {typical:.0f} s is under the {proj.min_length} s "
                        f"minimum ({basis})")

    out = {"ok": not problems, "problems": problems, "warnings": warnings,
           "projection": proj_info}
    try:
        (proj.work / "deckcheck.json").write_text(json.dumps(out, indent=1))
    except OSError:
        pass
    return out


def report(out):
    """Plain text for a terminal or a session; the JSON is in work/deckcheck.json."""
    lines = []
    p = out.get("projection") or {}
    if out["problems"]:
        lines.append(f"DECKCHECK FAILED: {len(out['problems'])} problem(s). Do not open the "
                     f"booth until this passes.")
        lines += [f"  PROBLEM  {x}" for x in out["problems"]]
    else:
        lines.append("DECKCHECK OK: every slide draws something and no authored content is dropped.")
    lines += [f"  warning  {x}" for x in out["warnings"]]
    if p:
        lines.append(f"  length   about {p['projected_s']:.0f} s ({p['words']} words at "
                     f"{p['words_per_second']} words/s"
                     + (f", measured over {p['measured_from_episodes']} episodes" if
                        p["measured_from_episodes"] else ", default pace")
                     + (f"; limits: min {p['min_length']}" if p.get("min_length") else "")
                     + (f", max {p['max_length']}" if p.get("max_length") else "") + ")")
    return "\n".join(lines)
