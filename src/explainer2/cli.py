# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/cli.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""explainer CLI — scaffolds a project and runs the pure-Python media pipeline.
The LLM generation stages (research/script/deck authoring) are done by the
/explainer skill, NOT here. This CLI never calls an LLM (PRD §5)."""
import argparse, json, re, sys, time
from datetime import date
from pathlib import Path

from .project import Project, ASPECTS
from . import deckbuild, manifest, wiki, ingest, themes, qa, presets, validate, handoff, brand, talktime, stills, renderlock, contenttypes
from .media import synth, align, render, mux

STAGES = [("narrate", synth.run), ("align", align.run), ("deck", deckbuild.run),
          ("render", render.run), ("mux", mux.run), ("manifest", manifest.run),
          ("qa", qa.run)]
STAGE_MAP = dict(STAGES)

# Standing channel music bed: the default for every scaffold so it's never
# forgotten. Pixabay-licensed (cert in library/music); the benign Content ID
# claim is accepted. Override with --music <path>/--music-gain, or --no-music.
# Path resolves relative to the repo root so it survives a move off /Volumes.
# Operator decision 2026-06-29: switched from the café bed to the more upbeat
# "presentation background" track (same Alex Morgan / Pixabay library). The old
# café bed (alex-morgan-cafe-warm-background-music-541034.mp3) stays in the
# library for back-catalogue consistency.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MUSIC = _REPO_ROOT / "library/music/07-alex-morgan-presentation-background-music-548620.mp3"
DEFAULT_MUSIC_GAIN = 0.12


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
        music_path = Path(args.music).resolve() if args.music else DEFAULT_MUSIC
        proj["music"] = str(music_path)
        proj["music_gain"] = args.music_gain
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
    only = set(args.only.split(",")) if args.only else None
    engine = getattr(args, "engine", "deck")
    results, t0 = {}, time.time()
    lock = None  # machine-global render lock, held across render→mux (renderlock.py)
    try:
        for name, fn in STAGES:
            if only and name not in only:
                continue
            # the Remotion engine outputs the final muxed mp4 itself — no deck/mux stages
            if engine == "remotion" and name in ("deck", "mux"):
                continue
            # Serialize the memory-heavy capture+encode across every project and
            # background routine on this Mac (the #10-vs-CVG collision, 2026-06-21).
            if name in ("render", "mux") and lock is None:
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
    from . import shorts
    print(json.dumps(shorts.run(args.project_dir, plan_path=args.plan, only=args.only_slug, engine=args.engine), indent=2))


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
    if not args.authorize and not args.project_dir:
        print("publish needs a project_dir (or --authorize --channel <key>)")
        return 1
    print(json.dumps(publish.run(args.project_dir, fire=args.fire, privacy=args.privacy,
                                 when=args.when, channel=args.channel,
                                 do_authorize=args.authorize), indent=2))


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
        path = wiki.add_node(args.root, "source-fact", args.name, args.body,
                             topic=args.topic, source=args.source,
                             confidence=args.confidence)
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
                   help="background music path (default: the channel café bed in library/music)")
    s.add_argument("--music-gain", type=float, default=DEFAULT_MUSIC_GAIN, dest="music_gain",
                   help=f"music bed gain (default {DEFAULT_MUSIC_GAIN})")
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
                   help="deck = JS deck engine (default); remotion = motion-graphics engine (skips deck/mux)")
    m.set_defaults(func=cmd_media)

    rn = sub.add_parser("render", help="launch render→mux→manifest→qa DETACHED (survives session "
                                       "suspension) + serialized via the machine-global render lock")
    rn.add_argument("project_dir")
    rn.add_argument("--only", default=None,
                    help=f"stage list to run detached (default: {renderlock.DEFAULT_STAGES})")
    rn.add_argument("--engine", default="remotion", choices=["deck", "remotion"],
                    help="deck = JS deck engine (default); remotion = motion-graphics engine (motion-playbook.md)")
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
                    help="deck = the JS deck engine (default); remotion = the motion-graphics engine (motion-playbook.md)")
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
                         "the API-blind steps (A/B thumbs, title A/B, end screen, pinned comment)")
    pub.add_argument("project_dir", nargs="?", help="omit only with --authorize")
    pub.add_argument("--fire", action="store_true", help="actually upload (default: dry-run plan)")
    pub.add_argument("--privacy", choices=["public", "unlisted", "private"], default="private",
                     help="visibility on --fire (default: private — pass public to go live)")
    pub.add_argument("--when", help="RFC3339 UTC timestamp to schedule (forces private + publishAt)")
    pub.add_argument("--channel", default=None,
                     help="target channel KEY; overrides project.json 'youtube_channel' "
                          "(default: nemock). With --authorize, the key to bind.")
    pub.add_argument("--authorize", action="store_true",
                     help="one-time: run OAuth consent for --channel <key>, bind its token + "
                          "record the channel in the registry (pick the right channel on Google's screen)")
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
    wk.add_argument("kind", choices=["source", "fact"])
    wk.add_argument("name")
    wk.add_argument("--root", default=".")
    wk.add_argument("--topic", default="")
    wk.add_argument("--body", default="")
    wk.add_argument("--ref", default="")
    wk.add_argument("--source", default="")
    wk.add_argument("--confidence", default="medium")
    wk.set_defaults(func=cmd_wiki)

    args = p.parse_args(argv)
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
