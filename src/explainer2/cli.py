# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/cli.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""explainer CLI — scaffolds a project and runs the pure-Python media pipeline.
The LLM generation stages (research/script/deck authoring) are done by the
/explainer skill, NOT here. This CLI never calls an LLM (PRD §5)."""
import argparse, json, re, sys, time
from datetime import date, datetime
from pathlib import Path

from .project import Project, ASPECTS
from . import deckbuild, manifest, wiki, ingest, themes, qa, presets, validate, handoff, brand, talktime, stills, renderlock, contenttypes, childproc
from .media import synth, align, render, mux, scriptguard, timelineguard

STAGES = [("narrate", synth.run), ("align", align.run), ("deck", deckbuild.run),
          ("render", render.run), ("mux", mux.run), ("manifest", manifest.run),
          ("qa", qa.run)]
STAGE_MAP = dict(STAGES)

# Channel music beds are PER-CHANNEL (operator 2026-07-16), parallel to the theme-branding
# isolation: each channel/theme owns its bed so changing one never disrupts another. Scaffold
# resolves the bed from the project's --theme via THEME_MUSIC; a theme not listed falls back to
# DEFAULT_MUSIC/DEFAULT_MUSIC_GAIN. --music/--music-gain override everything; a project's own
# project.json `music` wins at render time. Paths resolve relative to the repo root so they
# survive a move off /Volumes.
_REPO_ROOT = Path(__file__).resolve().parents[2]

# Fallback bed for any theme without its own THEME_MUSIC entry.
# Operator, 2026-08-14: "I don't want to use the licensed music from the Pixabay website
# anymore." The Magnific "sophisticated" bed becomes the default for EVERY theme, not just
# the two that named it in THEME_MUSIC. Provenance is Dave's Magnific subscription output,
# so the per-project Pixabay licence auto-copy (_copy_music_license) will not fire for it —
# that is expected, not a missing step. The old Pixabay beds stay in library/music/ because
# the back catalogue still references them from its own project.json files.
DEFAULT_MUSIC = _REPO_ROOT / "library/music/11-magnific_generate-a-sophisticated-_LU1wnIYswO.mp3"
DEFAULT_MUSIC_GAIN = 0.22   # 0.12 was measured inaudible under narration

# Per-channel beds. Keep beds FLAT at render (no sidechain ducking — the gaps between spoken
# lines are too short, so ducking pumps; operator 2026-07-16). NOTE nemock-deep-dive's bed is
# operator-generated Magnific (NOT Pixabay): the per-project license auto-copy won't fire for
# it; monetization rights come from the Magnific subscription. Magnific caps generated audio at
# 5:00, so this bed loops (~5:00/10:00 seams under an ~11-min deep dive) — accepted.
THEME_MUSIC = {
    "nemock-deep-dive": {
        "path": _REPO_ROOT / "library/music/11-magnific_generate-a-sophisticated-_LU1wnIYswO.mp3",
        "gain": 0.22,
    },
    # The Operator's Guide to Product Leadership rides alongside the deep dives on the
    # same channel, so it gets the same bed rather than the global fallback. Added
    # 2026-08-12, after module 1 rendered on the fallback Pixabay bed at 0.12 — which is
    # the DESIGNED behaviour for an unlisted theme, not a bug, but 0.12 was already found
    # inaudible under narration (that is why nemock moved to 0.22).
    "plg-guide": {
        "path": _REPO_ROOT / "library/music/11-magnific_generate-a-sophisticated-_LU1wnIYswO.mp3",
        "gain": 0.22,
    },
}


def _log(proj, msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    with (proj.work / "run.log").open("a") as f:
        f.write(line + "\n")
    print(line)


# --- canonical project numbering (folder is the source of truth, never a hand-typed counter) ---
_PROJ_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(\d+)_")


def _scan_projects(outdir):
    """Numbered channel projects in outdir as sorted (number:int, Path). Non-numbered
    dirs (e.g. phase0-parity, or another routine's week-based outputs) are ignored."""
    d = Path(outdir).resolve()
    rows = []
    if d.exists():
        for p in sorted(d.iterdir()):
            if p.is_dir():
                m = _PROJ_RE.match(p.name)
                if m:
                    rows.append((int(m.group(1)), p))
    return rows


def _project_state(p):
    if (p / "package").is_dir():
        return "packaged"
    if (p / "video").is_dir() or any(p.glob("video*/*.mp4")):
        return "rendered"
    if (p / "script.json").exists():
        return "scripted"
    if (p / "intel" / "intel.json").exists():
        return "intel"
    return "scaffolded"


def _catalog_path(outdir):
    return Path(outdir).resolve().parent / "channel" / "CATALOG.md"


def _refresh_catalog_counter(outdir):
    """Regenerate the single counter line in channel/CATALOG.md from the folder scan.
    Returns True if the file existed and was updated. No-op (False) when there's no
    channel/CATALOG.md next to outdir (e.g. a non-channel scaffold). Best-effort."""
    cat = _catalog_path(outdir)
    if not cat.exists():
        return False
    rows = _scan_projects(outdir)
    count = len(rows)
    nxt = (max(n for n, _ in rows) + 1) if rows else 1
    line = (f"**Projects to date: {count}**  ·  next canonical number: **{nxt}**  "
            f"_(auto-derived from `projects/` by `explainer2 catalog` — do not hand-edit)_")
    txt = cat.read_text(encoding="utf-8")
    new = re.sub(r"(?m)^\*\*(?:Lifetime videos generated|Projects to date):.*$", line, txt, count=1)
    if new == txt:
        return False
    cat.write_text(new, encoding="utf-8")
    return True


def cmd_catalog(args):
    """Derive the canonical project count/next number + per-project state from the
    projects/ folder. The folder is the source of truth; this never trusts a stored counter."""
    rows = _scan_projects(args.outdir)
    highest = max((n for n, _ in rows), default=0)
    print(f"Projects to date: {len(rows)}   |   highest #: {highest}   |   next #: {highest + 1}\n")
    for n, p in rows:
        print(f"  #{n:02d}  {_project_state(p):<10}  {p.name}")
    if args.write:
        ok = _refresh_catalog_counter(args.outdir)
        print(f"\nCATALOG.md counter {'refreshed' if ok else 'NOT updated (counter line / channel/CATALOG.md not found)'}.")


def cmd_scaffold(args):
    aspect, safe_bottom, min_length = args.aspect, 0.14, args.min_length
    aspects = [a.strip() for a in args.aspects.split(",")] if args.aspects else None
    if args.platform:
        pre = presets.resolve(args.platform)
        if pre:
            aspect = pre["aspect"]
            safe_bottom = pre.get("safe_bottom", 0.14)
            if pre.get("min_length") and not min_length:
                min_length = pre["min_length"]
    if not aspects:
        aspects = [aspect]
    primary = aspects[0]
    w, h = ASPECTS[primary]
    ctype = args.content_type or contenttypes.infer_from_aspect(primary)
    if ctype == "masterclass":
        if not args.series or args.episode is None:
            sys.exit("content-type masterclass needs --series <slug> and --episode <n> "
                     "(the series outline is the source of both; see masterclass-playbook.md)")
    elif args.series or args.episode is not None:
        sys.exit(f"--series/--episode are masterclass-only flags (content type here: {ctype}); "
                 "pass --content-type masterclass")
    if ctype == "promo" and not args.promotes:
        sys.exit("content-type promo needs --promotes \"<the one offer this video sells>\" "
                 "(a promo with no named offer is a failed promo; see promo-playbook.md)")
    if args.promotes and ctype != "promo":
        sys.exit(f"--promotes is a promo-only flag (content type here: {ctype}); "
                 "pass --content-type promo")
    # Auto-number ONLY for the numbered channel `projects/` collection. Other routines
    # (Monday MedTech, Founder Tip Tuesday) scaffold into their own non-numbered outdirs;
    # leave those exactly as before. Trigger auto-numbering when the outdir already holds
    # numbered projects, OR is literally named "projects", OR --number was passed.
    existing = _scan_projects(args.outdir)
    autonum = (args.number is not None) or bool(existing) or Path(args.outdir).resolve().name == "projects"
    if autonum:
        raw_slug = re.sub(r"^\d+[-_]+", "", args.slug)  # drop a number if the caller baked one in
        slug = wiki.slugify(raw_slug)
        nums = {n for n, _ in existing}
        num = args.number if args.number is not None else (max(nums) + 1 if nums else 1)
        if num in nums and not args.force:
            sys.exit(f"project #{num} already exists in {args.outdir}; auto-number gives "
                     f"#{(max(nums) + 1) if nums else 1}. Pass --number to override or --force to duplicate.")
        out = Path(args.outdir).resolve() / f"{date.today().isoformat()}_{num:02d}_{slug}"
    else:
        slug = wiki.slugify(args.slug)
        num = None
        out = Path(args.outdir).resolve() / f"{date.today().isoformat()}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    # `--theme paper` is a legacy shorthand for Dave's nemock paper world. The standalone
    # "paper" theme key is NOT recognized as a paper theme by the Remotion engine
    # (PAPER_THEMES = nemock-deep-dive / cut-bond / brg-paper), so it renders in the MIDNIGHT
    # navy look — a silent off-brand bug (caught on #47, 2026-07-24). Normalize it here so the
    # project.json theme + the theme's music bed both resolve to the real paper channel.
    if args.theme == "paper":
        args.theme = "nemock-deep-dive"
    proj = {"title": args.title or args.slug, "slug": slug, "aspect": primary,
            "aspects": aspects, "width": w, "height": h, "fps": args.fps,
            "voice": args.voice, "voice_source": args.voice_source,
            "language": "en", "theme": args.theme, "safe_bottom": safe_bottom,
            "content_type": ctype}
    if ctype == "masterclass":
        proj["series"] = {"slug": wiki.slugify(args.series), "title": args.series_title,
                          "episode": args.episode, "episodes_total": args.episodes_total,
                          "distribution": args.distribution,
                          "brand_label": contenttypes.brand_label(args.distribution)}
    if args.promotes:
        proj["promotes"] = args.promotes
    if num is not None:
        proj["number"] = num
    if min_length:
        proj["min_length"] = min_length
    if not args.no_music:
        # Resolve the bed PER CHANNEL: explicit --music wins; else the theme's own bed
        # (THEME_MUSIC); else the global fallback. --music-gain (when given) overrides the
        # resolved gain. Keeps each channel's music isolated from the others.
        if args.music:
            music_path, theme_gain = Path(args.music).resolve(), DEFAULT_MUSIC_GAIN
        else:
            tm = THEME_MUSIC.get(args.theme)
            if tm:
                music_path, theme_gain = Path(tm["path"]), tm["gain"]
            else:
                music_path, theme_gain = DEFAULT_MUSIC, DEFAULT_MUSIC_GAIN
        proj["music"] = str(music_path)
        proj["music_gain"] = args.music_gain if args.music_gain is not None else theme_gain
    if args.no_cta:
        proj["auto_cta"] = False  # branded but no CTA tail (deep-dive act sub-segments)
    brand_note = None
    if args.brand:
        bdir, bdata = brand.resolve(args.brand)
        if bdir:
            proj["brand"] = brand.copy_into(out, bdir, bdata, args.brand, cta_variant=args.cta)
            cv = proj["brand"].get("cta_variant")
            cta_part = "watermark only (no CTA, --no-cta)" if args.no_cta else "watermark + CTA auto-added"
            brand_note = (f"brand '{args.brand}' ({proj['brand']['name']}) — {cta_part}"
                          + (f" [cta: {cv}]" if (cv and not args.no_cta) else ""))
        else:
            brand_note = f"brand '{args.brand}' NOT FOUND in ./brand/ or ~/.claude/explainer-brands/ — skipped"
    (out / "project.json").write_text(json.dumps(proj, indent=2))
    # ORIGINATING SENTINEL (2026-08-25). Between this scaffold and the routine's
    # booth-open step there is a 5-10 minute authoring window in which the project
    # already looks bookable to the launchd recording watcher: today's date in the
    # dir name, a script.json on disk, no README yet. The watcher's NOT_OPEN safety
    # net fired inside that window and opened a booth on a HALF-AUTHORED script,
    # then the routine's own Step 7 popped a second Chrome tab on top of it (FTT
    # 2026-08-25 09:15:42, MMT 2026-08-24 09:23:02, and four earlier shows). Drop a
    # sentinel here so the watcher knows a live run still owns the project; the
    # launcher clears it the moment the booth is opened for real. It carries a
    # timestamp because the watcher expires it — a run that dies mid-authoring must
    # not disable the safety net forever. See
    # make_money/routine_changes/2026-08-25-booth-originating-sentinel.md
    (out / "work").mkdir(exist_ok=True)
    (out / "work" / "originating.json").write_text(json.dumps({
        "written_by": "explainer2 scaffold",
        "written_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "meaning": "a run is authoring this project; the recording watcher must not "
                   "open a booth for it yet. Cleared by tools/launch_booth.py on open.",
    }, indent=2))
    try:
        catalog_updated = _refresh_catalog_counter(args.outdir)
    except Exception:
        catalog_updated = False
    print(json.dumps({"project_dir": str(out), "number": num, "aspects": aspects,
                      "content_type": ctype, "series": proj.get("series"), "brand": brand_note,
                      "catalog_counter_updated": catalog_updated,
                      "next": "author script.json + deck.json, then `explainer media <dir>`"}, indent=2))


def cmd_media(args):
    proj = Project.load(args.project_dir)

    # SCRIPT/AUDIO STALENESS GUARD (scriptguard.py, 2026-08-10). Runs BEFORE any
    # stage and regardless of --only, because the detached `render` path skips
    # narrate entirely and would otherwise render a cached, stale segments.json.
    # A mismatch writes BLOCKED.md and exits non-zero, so Phase 1 never writes
    # render_complete.json and the watcher's Phase 2 never publishes.
    try:
        guard = scriptguard.enforce(proj, log=lambda m: _log(proj, m),
                                    allow_stale=getattr(args, "allow_stale_script", False))
    except scriptguard.StaleScriptError as e:
        print(json.dumps({"blocked": "stale_script", "reason": e.report["reason"],
                          "stale_segments": e.report["stale"],
                          "unstamped_segments": e.report["unstamped"],
                          "blocked_file": str(scriptguard.blocked_path(proj))}, indent=2))
        return 1
    if getattr(args, "recheck", False):
        print(json.dumps({"ok": True, "reason": guard["reason"],
                          "checked": len([s for s in guard["segments"]
                                          if s["status"] in ("match", "exempt")]),
                          "unstamped": guard["unstamped"],
                          "not_recorded": guard["not_recorded"]}, indent=2))
        return 0

    only = set(args.only.split(",")) if args.only else None

    # TIMELINE STALENESS GUARD (timelineguard.py, 2026-08-12). The scriptguard above
    # proves the TEXT matches; this proves the AUDIO does. `render` dispatches
    # --only render,mux,manifest,qa and never re-aligns, so a take re-recorded after
    # the last align used to render against the previous timeline — succeeding, and
    # producing a video desynced from the card onward. No-op when this run includes
    # align, which is about to rebuild the timeline anyway.
    try:
        timelineguard.enforce(proj, only=only, log=lambda m: _log(proj, m),
                              allow_stale=getattr(args, "allow_stale_timeline", False))
    except timelineguard.StaleTimelineError as e:
        print(json.dumps({"blocked": "stale_timeline", "reason": e.report["reason"],
                          "changed": e.report.get("changed", []),
                          "fix": "explainer2 media <dir> --only narrate,align, then render"},
                         indent=2))
        return 1

    engine = getattr(args, "engine", "deck")
    results, t0 = {}, time.time()
    lock = None  # machine-global render lock, held across render→mux (renderlock.py)
    # Trap termination so a killed render takes its remotion/chrome tree with it and
    # releases the render lock, instead of orphaning an encode that keeps writing
    # frames under a lockfile whose recorded pid is already dead (2026-08-10).
    childproc.on_terminate(lambda: renderlock.release(lock))
    childproc.install_handlers(log=lambda m: _log(proj, m))
    try:
        for name, fn in STAGES:
            if only and name not in only:
                continue
            # the Remotion engine outputs the final muxed mp4 itself — no deck/mux stages
            if engine == "remotion" and name in ("deck", "mux"):
                continue
            # Serialize the memory-heavy stages across every project and background
            # routine on this Mac (the #10-vs-CVG collision, 2026-06-21).
            # Taken from NARRATE onward (2026-08-26), not from render: the two
            # torch stages in front of the encode are the real peak. `narrate`
            # loads Kokoro (media/synth.py) and `align` loads torchaudio MMS_FA plus
            # the whole narration.wav (media/align.py) — 2.5-3.3 GB apiece. With the
            # lock starting at `render`, both ran unguarded, so N concurrent jobs
            # stacked N torch heaps while the lock dutifully serialized the encode
            # behind them. Four `shorts` jobs peaked at ~12 GB on this 16 GB Mac and
            # tripped the macOS out-of-memory dialog. Operator directive: a
            # background render must never make the machine unusable interactively,
            # even if serializing makes each run take longer.
            if name in ("narrate", "align", "render", "mux") and lock is None:
                lock = renderlock.acquire(proj, log=lambda m: _log(proj, m))
            ts = time.time()
            _log(proj, f"START {name}{' (remotion)' if engine == 'remotion' and name == 'render' else ''}")
            try:
                if engine == "remotion" and name == "render":
                    from . import remotion_engine
                    results[name] = remotion_engine.render(proj, log=lambda m: _log(proj, m))
                else:
                    results[name] = fn(proj)
            except Exception as e:
                _log(proj, f"FAIL  {name}: {type(e).__name__}: {e}")
                print(json.dumps({"failed_stage": name, "error": str(e)}))
                return 1
            _log(proj, f"OK    {name} ({time.time()-ts:.1f}s) {json.dumps(results[name])}")
            if lock is not None and (name == "mux" or (engine == "remotion" and name == "render")):
                renderlock.release(lock); lock = None
    finally:
        renderlock.release(lock)
    results["wall_clock_s"] = round(time.time() - t0, 2)
    proj.write_json(proj.work / "results.json", results)
    print("\n=== RESULTS ===")
    print(json.dumps(results, indent=2))
    return 0


def cmd_stage(args):
    proj = Project.load(args.project_dir)
    # Same guard as cmd_media — a single-stage invocation must not be the way a
    # stale narrate/align sneaks through (scriptguard.py).
    try:
        scriptguard.enforce(proj, log=lambda m: _log(proj, m))
    except scriptguard.StaleScriptError as e:
        print(json.dumps({"blocked": "stale_script", "reason": e.report["reason"],
                          "stale_segments": e.report["stale"]}, indent=2))
        return 1
    fn = STAGE_MAP[args.stage]
    print(json.dumps(fn(proj), indent=2))


def cmd_render(args):
    """Launch render→mux→manifest→qa DETACHED (survives Claude-session
    suspension) and serialized via the machine-global render lock."""
    Project.load(args.project_dir)  # validate the project exists before detaching
    res = renderlock.launch_detached(args.project_dir, only=args.only, engine=args.engine, log=print)
    print(json.dumps(res, indent=2))
    return 0


def cmd_render_status(args):
    print(renderlock.status())
    return 0


def cmd_intel(args):
    from .intel import run as intel_run
    proj_dir = Path(args.project_dir).resolve()
    topic = args.topic
    if not topic:
        pj = proj_dir / "project.json"
        if pj.exists():
            topic = json.loads(pj.read_text()).get("title")
    if not topic:
        print("no topic: pass --topic or scaffold the project with a --title")
        return 1
    queries = [q.strip() for q in args.queries.split(";")] if args.queries else None
    print(json.dumps(intel_run.run(proj_dir, topic, queries=queries,
                                   max_finalists=args.max_finalists,
                                   per_query=args.per_query), indent=2))


def cmd_ingest(args):
    proj = Project.load(args.project_dir)
    if args.pdf:
        print(json.dumps(ingest.ingest_pdf(proj, args.pdf, pages=args.pages), indent=2))
    elif args.url:
        print(json.dumps(ingest.ingest_url(proj, args.url, full_page=args.full_page), indent=2))
    else:
        print("provide --pdf <path> or --url <url>")
        return 1


def cmd_validate(args):
    print(json.dumps(validate.run(Project.load(args.project_dir)), indent=2))


def cmd_handoff(args):
    print(json.dumps(handoff.run(Project.load(args.project_dir)), indent=2))


def cmd_record(args):
    from . import recorder
    print(json.dumps(recorder.run(Project.load(args.project_dir), open_browser=not args.no_open), indent=2))


def cmd_adlib(args):
    from .media import adlib
    print(json.dumps(adlib.run(Project.load(args.project_dir), apply=args.apply), indent=2))


def cmd_shorts(args):
    # Admission gate FIRST, before `shorts` (and through it torch) is imported:
    # a refused job must cost nothing. See renderlock.py "job admission control"
    # for the 2026-08-26 incident this exists to prevent — a forked Claude session
    # launched two `shorts` jobs per module from each half, and the two on the same
    # module rendered the identical cut twice while four torch heaps sat resident.
    # Refuse rather than queue: a waiting process still holds everything it has
    # already imported, which is the cost we are trying not to pay.
    # wait=False: an interactive/ad-hoc shorts run should say so and stop rather
    # than sit in a queue. Unattended callers that must not drop a run pass
    # wait=True (daily_beats does).
    claim = renderlock.claim_job(args.project_dir, kind="shorts", wait=False)
    if claim is None:
        return 1
    try:
        from . import shorts
        print(json.dumps(shorts.run(args.project_dir, plan_path=args.plan,
                                    only=args.only_slug, engine=args.engine), indent=2))
    finally:
        renderlock.release_job(claim)
    return 0


def cmd_assets(args):
    from . import stockassist
    print(json.dumps(stockassist.run(Project.load(args.project_dir), args.action,
                                     slide=args.slide), indent=2))


def cmd_stills(args):
    proj = Project.load(args.project_dir)
    print(json.dumps(stills.run(proj, aspect=args.aspect), indent=2))


def cmd_promote(args):
    from . import promote
    print(json.dumps(promote.run(args.projects_dir, args.action, video=args.video,
                                 short=args.short, record=args.record,
                                 plan=args.plan, fire=args.fire), indent=2))


def cmd_publish(args):
    from . import publish
    if args.set_privacy:
        print(json.dumps(publish.set_privacy(video_id=args.video_id, project_dir=args.project_dir,
                                             channel=args.channel, privacy=args.set_privacy,
                                             when=args.when), indent=2))
        return
    if not args.authorize and not args.project_dir:
        print("publish needs a project_dir (or --authorize --channel <key>, or --set-privacy)")
        return 1
    print(json.dumps(publish.run(args.project_dir, fire=args.fire, privacy=args.privacy,
                                 when=args.when, channel=args.channel,
                                 do_authorize=args.authorize, force_rebind=args.force_rebind), indent=2))


def cmd_talktime(args):
    tag, library = args.tag, args.library
    if args.brand and not (tag and library):
        _, bdata = brand.resolve(args.brand)
        tt = (bdata or {}).get("talk_time", {}) if bdata else {}
        tag = tag or tt.get("tag")
        library = library or tt.get("library")
    topics = [t.strip() for t in args.topics.split(",")] if args.topics else None
    try:
        print(talktime.run(library=library, tag=tag, topics=topics))
    except FileNotFoundError as e:
        print(e)
        return 1


def cmd_learn(args):
    from . import learn
    if args.action == "refresh":
        return learn.refresh(args.projects_dir)
    if args.action == "ingest":
        if not args.csv:
            print("ingest needs --csv <YouTube Studio content export>")
            return 1
        return learn.ingest(args.csv)
    return learn.report()


def cmd_wiki(args):
    if args.kind == "source":
        path = wiki.add_node(args.root, "source", args.name, args.body or args.name,
                             topic=args.topic, ref=args.ref)
    else:
        # Facts follow references/research-wiki.md: topic-scoped under
        # explainer-content/research/, not the project-local wiki/ tree.
        try:
            path = wiki.add_claim(args.research_root, args.topic, args.name, args.body,
                                  status=args.status, source=args.source, url=args.url,
                                  source_date=args.source_date, tier=args.tier)
        except ValueError as e:
            print(f"wiki fact: {e}")
            return 1
    print(json.dumps({"node": path}))


def main(argv=None):
    p = argparse.ArgumentParser(prog="explainer2")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scaffold", help="create a project dir + project.json")
    s.add_argument("slug", help="slug WITHOUT a number; the canonical number is auto-assigned "
                               "from projects/ (highest + 1). A leading number is stripped if present.")
    s.add_argument("--number", type=int, default=None,
                   help="force a specific canonical number (default: auto = highest in projects/ + 1)")
    s.add_argument("--force", action="store_true", help="allow a duplicate canonical number")
    s.add_argument("--title", default=None)
    s.add_argument("--outdir", default="projects")
    s.add_argument("--aspect", default="9:16", choices=list(ASPECTS))
    s.add_argument("--fps", type=int, default=30)
    s.add_argument("--voice", default="af_heart", help="Kokoro voice (when voice-source=kokoro)")
    s.add_argument("--voice-source", default="kokoro", choices=["kokoro", "operator"], dest="voice_source",
                   help="kokoro = local TTS; operator = your recorded voiceover (`explainer record`)")
    s.add_argument("--content-type", default=None, choices=list(contenttypes.CONTENT_TYPES),
                   dest="content_type",
                   help="canonical content type (contenttypes.py); default: inferred from the "
                        "primary aspect (16:9 = deepdive, else short)")
    s.add_argument("--series", default=None,
                   help="masterclass only: series slug (e.g. iso-14971); groups the episodes")
    s.add_argument("--series-title", default=None, dest="series_title",
                   help="masterclass only: the public series title (e.g. \"The Operator's Guide to ISO 14971\")")
    s.add_argument("--episode", type=int, default=None,
                   help="masterclass only: episode number within the series (1-based)")
    s.add_argument("--episodes-total", type=int, default=None, dest="episodes_total",
                   help="masterclass only: planned episode count (optional; from the series outline)")
    s.add_argument("--distribution", default="youtube", choices=list(contenttypes.DISTRIBUTIONS),
                   help="masterclass only: youtube = free, branded \"The Operator's Guide\"; "
                        "paywalled = paid, branded \"Masterclass\" (2026-07-05 naming rule)")
    s.add_argument("--promotes", default=None,
                   help="promo only: the ONE offer this video sells (e.g. \"Plan to Market cohort, "
                        "Sept 2026\"); recorded in project.json + manifest")
    s.add_argument("--theme", default="midnight", choices=list(themes.THEMES))
    s.add_argument("--platform", default=None, choices=list(presets.PLATFORMS),
                   help="sets aspect + safe-zone (+ min length) from a platform preset")
    s.add_argument("--aspects", default=None, help="comma list to render simultaneously, e.g. '9:16,1:1'")
    s.add_argument("--min-length", type=int, default=None, dest="min_length",
                   help="minimum playback seconds (sets manifest length_warning if unmet)")
    s.add_argument("--music", default=None,
                   help="background music path (default: the channel's own bed, resolved from --theme)")
    s.add_argument("--music-gain", type=float, default=None, dest="music_gain",
                   help="music bed gain (default: the channel's own gain, resolved from --theme)")
    s.add_argument("--no-music", action="store_true", dest="no_music",
                   help="scaffold without a music bed")
    s.add_argument("--brand", default=None,
                   help="brand slug (e.g. ACME); adds watermark + auto CTA end slide from the brand library")
    s.add_argument("--cta", default=None,
                   help="CTA variant name from the brand's cta_library.json (else the library default / brand.json cta)")
    s.add_argument("--no-cta", action="store_true", dest="no_cta",
                   help="keep the brand watermark but DON'T auto-append a CTA slide/narration "
                        "(for deep-dive act sub-segments — the CTA is the film's closing segment)")
    s.set_defaults(func=cmd_scaffold)

    c = sub.add_parser("catalog", help="derive the canonical project count + next number from projects/ (source of truth)")
    c.add_argument("--outdir", default="projects")
    c.add_argument("--write", action="store_true", help="refresh the counter line in channel/CATALOG.md")
    c.set_defaults(func=cmd_catalog)

    m = sub.add_parser("media", help="run the pure-Python media pipeline on a project dir")
    m.add_argument("project_dir")
    m.add_argument("--only", default=None, help="comma list: narrate,align,deck,render,mux,manifest")
    m.add_argument("--engine", default="remotion", choices=["deck", "remotion"],
                   help="remotion = motion-graphics engine (DEFAULT, skips deck/mux); deck = JS deck engine (fallback)")
    m.add_argument("--recheck", action="store_true",
                   help="run the script/audio staleness guard ONLY and exit (0 clean, 1 blocked); "
                        "renders nothing. Clears a resolved BLOCKED.md.")
    m.add_argument("--allow-stale-script", action="store_true", dest="allow_stale_script",
                   help="render even though the recorded audio disagrees with script.json "
                        "(same as EXPLAINER_ALLOW_STALE_SCRIPT=1). Logged loudly; the video "
                        "will say something other than what the script says.")
    m.add_argument("--allow-stale-timeline", action="store_true", dest="allow_stale_timeline",
                   help="render even though a take was re-recorded since the last align "
                        "(same as EXPLAINER_ALLOW_STALE_TIMELINE=1). Logged loudly; slides "
                        "and captions will drift out of sync with the narration.")
    m.set_defaults(func=cmd_media)

    rn = sub.add_parser("render", help="launch render→mux→manifest→qa DETACHED (survives session "
                                       "suspension) + serialized via the machine-global render lock")
    rn.add_argument("project_dir")
    rn.add_argument("--only", default=None,
                    help=f"stage list to run detached (default: {renderlock.DEFAULT_STAGES})")
    rn.add_argument("--engine", default="remotion", choices=["deck", "remotion"],
                    help="remotion = motion-graphics engine (DEFAULT, motion-playbook.md); deck = JS deck engine (fallback)")
    rn.set_defaults(func=cmd_render)

    rs = sub.add_parser("render-status", help="show the render-lock holder + every live render on this Mac")
    rs.set_defaults(func=cmd_render_status)

    for st in STAGE_MAP:
        if st == "render":
            continue  # 'render' is the detached launcher above; inline stage = `media --only render`
        sp = sub.add_parser(st, help=f"run only the {st} stage")
        sp.add_argument("project_dir")
        sp.set_defaults(func=cmd_stage, stage=st)

    it = sub.add_parser("intel", help="YouTube competitive intelligence sweep → intel/intel.json (no API key; yt-dlp)")
    it.add_argument("project_dir")
    it.add_argument("--topic", default=None, help="topic to research (default: project.json title)")
    it.add_argument("--queries", default=None,
                    help="semicolon-separated search queries (default: auto-derived from topic; "
                         "the /explainer2 skill usually supplies richer ones)")
    it.add_argument("--max-finalists", type=int, default=12, dest="max_finalists")
    it.add_argument("--per-query", type=int, default=15, dest="per_query")
    it.set_defaults(func=cmd_intel)

    ing = sub.add_parser("ingest", help="ingest source material (PDF/URL) into sources/")
    ing.add_argument("project_dir")
    ing.add_argument("--pdf", default=None, help="path to a PDF to ingest")
    ing.add_argument("--url", default=None, help="URL to screenshot + extract")
    ing.add_argument("--pages", default=None, help="PDF pages to render, e.g. '1-3,5' (default first 4)")
    ing.add_argument("--full-page", action="store_true", help="full-page URL screenshot")
    ing.set_defaults(func=cmd_ingest)

    rc = sub.add_parser("record", help="launch the integrated voiceover recorder (browser teleprompter)")
    rc.add_argument("project_dir")
    rc.add_argument("--no-open", action="store_true", help="don't auto-open the browser")
    rc.set_defaults(func=cmd_record)

    ad = sub.add_parser("adlib", help="FALLBACK drift check: the booth now ASR-checks takes live and writes "
                                      "work/adlib_report.json at Finish; run this only when that report is "
                                      "missing or has 'unchecked' segments. --apply rewrites drifted segment "
                                      "text to raw ASR (normally avoid)")
    ad.add_argument("project_dir")
    ad.add_argument("--apply", action="store_true")
    ad.set_defaults(func=cmd_adlib)

    sh = sub.add_parser("shorts", help="cut 9:16 Shorts from a finished deep dive per shorts/plan.json (reuses operator narration)")
    sh.add_argument("project_dir")
    sh.add_argument("--plan", default=None, help="path to plan.json (default <project>/shorts/plan.json)")
    sh.add_argument("--only", default=None, dest="only_slug", help="render just one cut by slug")
    sh.add_argument("--engine", default="remotion", choices=["deck", "remotion"],
                    help="remotion = the motion-graphics engine (DEFAULT, motion-playbook.md); deck = the JS deck engine (fallback)")
    sh.set_defaults(func=cmd_shorts)

    ass = sub.add_parser("assets", help="Adobe Stock assist: open suggested searches / ingest the inbox / status")
    ass.add_argument("project_dir")
    ass.add_argument("action", choices=["open", "ingest", "status"])
    ass.add_argument("--slide", default=None, help="limit `open` to one slide id (e.g. s21)")
    ass.set_defaults(func=cmd_assets)

    pr = sub.add_parser("promote", help="pick the next produced video + Short to re-share "
                                        "(rotation: never-promoted first, then least-recent) and "
                                        "track promotions in the global ledger")
    pr.add_argument("action", choices=["select", "status", "log", "report", "post"])
    pr.add_argument("--projects-dir", default="projects", dest="projects_dir",
                    help="projects root (default: projects); the ledger sits beside it")
    pr.add_argument("--video", default=None, help="override video selection by folder slug")
    pr.add_argument("--short", default=None, help="override short selection by slug")
    pr.add_argument("--record", default=None, help="path to a JSON promotion record (for `log`)")
    pr.add_argument("--plan", default=None, help="path to a promotion plan JSON (for `post`)")
    pr.add_argument("--fire", action="store_true",
                    help="actually publish (default is a dry-run preview of the Blotato payloads)")
    pr.set_defaults(func=cmd_promote)

    pub = sub.add_parser("publish", help="hybrid YouTube upload of the PRIMARY video via the "
                         "operator's own OAuth (dry-run default; --fire to upload). API sets "
                         "file+metadata+thumbnail+playlist+schedule; prints a Chrome checklist for "
                         "the API-blind steps (end screen, pinned comment, altered-content disclosure)")
    pub.add_argument("project_dir", nargs="?", help="omit only with --authorize")
    pub.add_argument("--fire", action="store_true", help="actually upload (default: dry-run plan)")
    pub.add_argument("--privacy", choices=["public", "unlisted", "private"], default="private",
                     help="visibility on --fire (default: private — pass public to go live)")
    pub.add_argument("--when", help="RFC3339 UTC timestamp to schedule (forces private + publishAt)")
    pub.add_argument("--channel", default=None,
                     help="target channel KEY; overrides project.json 'youtube_channel' "
                          "(default: nemock). With --authorize, the key to bind.")
    pub.add_argument("--force-rebind", action="store_true", dest="force_rebind",
                     help="with --authorize: allow re-binding a channel key to a DIFFERENT channel "
                          "than it is currently bound to (default: abort + restore on mismatch, so an "
                          "accidental wrong-channel pick can't clobber a working binding)")
    pub.add_argument("--authorize", action="store_true",
                     help="one-time: run OAuth consent for --channel <key>, bind its token + "
                          "record the channel in the registry (pick the right channel on Google's screen)")
    pub.add_argument("--set-privacy", choices=["public", "unlisted", "private"], default=None,
                     help="change privacy of an ALREADY-uploaded video (the 'validate unlisted, "
                          "then flip public' flip). Target via project_dir (uses its meta youtube_url) "
                          "or --video-id. Same channel guard as --fire.")
    pub.add_argument("--video-id", default=None,
                     help="explicit video id for --set-privacy (else read from the project's meta.json)")
    pub.set_defaults(func=cmd_publish)

    va = sub.add_parser("validate", help="check the manifest is a complete handoff contract")
    va.add_argument("project_dir")
    va.set_defaults(func=cmd_validate)

    ho = sub.add_parser("handoff", help="emit per-platform blotato-ready post specs from the manifest")
    ho.add_argument("project_dir")
    ho.set_defaults(func=cmd_handoff)

    stl = sub.add_parser("stills", help="export one PNG per slide from the rendered deck (for repurposing)")
    stl.add_argument("project_dir")
    stl.add_argument("--aspect", default=None, choices=list(ASPECTS), help="aspect to capture (default: project primary)")
    stl.set_defaults(func=cmd_stills)

    tt = sub.add_parser("talktime", help="surface the operator's talk-time takes (read-only) to write the script in their voice")
    tt.add_argument("--brand", default=None, help="brand slug; pulls talk_time.tag (+library) from brand.json")
    tt.add_argument("--tag", default=None, help="brand tag to filter by (e.g. brg, fwf); overrides --brand")
    tt.add_argument("--topics", default=None, help="comma list of topic keywords to narrow candidates")
    tt.add_argument("--library", default=None, help="override the talk-time library path")
    tt.set_defaults(func=cmd_talktime)

    ln = sub.add_parser("learn", help="channel feedback loop: snapshot published-video performance "
                                      "(yt-dlp public stats / YouTube Studio CSV) and report what's working")
    ln.add_argument("action", choices=["refresh", "ingest", "report"])
    ln.add_argument("--csv", default=None, help="YouTube Studio content export (for `ingest`)")
    ln.add_argument("--projects-dir", default=str(_REPO_ROOT / "projects"), dest="projects_dir",
                    help="projects root scanned for published meta.json files")
    ln.set_defaults(func=cmd_learn)

    wk = sub.add_parser("wiki", help="add a wiki node")
    wk.add_argument("kind", choices=["source", "fact"],
                    help="fact = a research-wiki claim node (references/research-wiki.md); "
                         "source = a Phase-1 project-local source node")
    wk.add_argument("name", help="fact: the claim_id, e.g. klarna-700-is-an-equivalence")
    wk.add_argument("--root", default=".", help="source nodes only: project-local wiki/ root")
    wk.add_argument("--research-root", dest="research_root",
                    default=str(_REPO_ROOT / "research"),
                    help="fact nodes only; defaults to explainer-content/research/ via the "
                         "repo symlink, so the node lands correctly from any cwd")
    wk.add_argument("--topic", default="",
                    help="fact: REQUIRED, the topic-slug directory the claim lives in")
    wk.add_argument("--body", default="")
    wk.add_argument("--ref", default="")
    wk.add_argument("--source", default="", help="human-readable source name")
    wk.add_argument("--url", default="", help="fact: the source URL")
    wk.add_argument("--source-date", dest="source_date", default="",
                    help="fact: date the SOURCE is dated (not today)")
    wk.add_argument("--tier", default="", choices=("",) + wiki.TIERS,
                    help="fact: REQUIRED. SECONDARY-SUMMARY means an outlet summarizing "
                         "another outlet, which is how a soft claim hardens into a fact")
    wk.add_argument("--status", default="",
                    help="fact: REQUIRED, must start with one of: "
                         + " | ".join(wiki.STATUS_PREFIXES))
    wk.set_defaults(func=cmd_wiki)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
