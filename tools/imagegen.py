#!/usr/bin/env python3
"""imagegen.py — thin shell-side helpers for the OPTIONAL Magnific image-gen capability.

The Magnific MCP calls (simulate_cost / images_generate / creations_* / remove_background)
are made by Claude as tool calls; this helper owns only the two non-MCP mechanics —
the local-file PUT and the result download — plus provenance recording so the
AI-disclosure flag can be set honestly at packaging.

Stdlib only (no third-party deps), so any python3 runs it. See
docs/magnific-imagegen-plan.md for the full flow and guardrails.

Subcommands:
  put   <local_file> <presigned_put_url>
        PUT the file bytes to a presigned URL from creations_request_upload.

  fetch <result_url> <out_path> [--project DIR] [--model M] [--prompt P]
        [--tool T] [--refs R ...] [--in-video]
        Download a finished creation URL to out_path. With --project, append a
        provenance record to <DIR>/assets/imagegen/provenance.json. Pass
        --in-video for imagery that appears INSIDE the video (must be stylized);
        omit it for thumbnail bases.

  disclosure --project DIR
        Read provenance.json and report whether any in-video AI imagery exists,
        with the ai_generated_visuals value packaging should use.
"""
import argparse
import json
import mimetypes
import os
import sys
import urllib.request
from datetime import datetime, timezone


def _content_type(path: str) -> str:
    return mimetypes.guess_type(path)[0] or "application/octet-stream"


def cmd_put(args) -> int:
    src = os.path.abspath(os.path.expanduser(args.local_file))
    if not os.path.isfile(src):
        print(f"ERROR: no such file: {src}", file=sys.stderr)
        return 2
    with open(src, "rb") as f:
        body = f.read()
    req = urllib.request.Request(
        args.url, data=body, method="PUT",
        headers={"Content-Type": _content_type(src), "Content-Length": str(len(body))},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            code = resp.getcode()
            print(f"PUT {len(body)} bytes -> HTTP {code}")
            return 0 if 200 <= code < 300 else 1
    except urllib.error.HTTPError as e:
        print(f"ERROR: PUT failed HTTP {e.code}: {e.reason} "
              f"(don't re-PUT this target; request a fresh one)", file=sys.stderr)
        return 1
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: PUT failed: {e}", file=sys.stderr)
        return 1


def _record_provenance(project: str, out_path: str, args) -> None:
    prov_dir = os.path.join(project, "assets", "imagegen")
    os.makedirs(prov_dir, exist_ok=True)
    prov_path = os.path.join(prov_dir, "provenance.json")
    records = []
    if os.path.isfile(prov_path):
        try:
            records = json.load(open(prov_path))
        except (ValueError, OSError):
            records = []
    try:
        rel = os.path.relpath(os.path.abspath(out_path), os.path.abspath(project))
    except ValueError:
        rel = os.path.abspath(out_path)
    records.append({
        "file": rel,
        "generator": "magnific",
        "tool": args.tool,
        "model": args.model,
        "prompt": args.prompt,
        "references": args.refs or [],
        "in_video": bool(args.in_video),
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    })
    with open(prov_path, "w") as f:
        json.dump(records, f, indent=2)
    print(f"provenance += {rel} (in_video={bool(args.in_video)}) -> {prov_path}")


def cmd_fetch(args) -> int:
    out_path = os.path.abspath(os.path.expanduser(args.out_path))
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    try:
        with urllib.request.urlopen(args.url, timeout=180) as resp:
            code = resp.getcode()
            data = resp.read()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: download failed: {e}", file=sys.stderr)
        return 1
    if code and not (200 <= code < 300):
        print(f"ERROR: download HTTP {code}", file=sys.stderr)
        return 1
    with open(out_path, "wb") as f:
        f.write(data)
    print(f"fetched {len(data)} bytes -> {out_path}")
    if args.project:
        _record_provenance(args.project, out_path, args)
    return 0


def cmd_disclosure(args) -> int:
    prov_path = os.path.join(args.project, "assets", "imagegen", "provenance.json")
    if not os.path.isfile(prov_path):
        print(json.dumps({"has_ai_imagegen": False, "in_video": False,
                          "ai_generated_visuals": False,
                          "note": "no Magnific image-gen used"}, indent=2))
        return 0
    records = json.load(open(prov_path))
    in_video = any(r.get("in_video") for r in records)
    thumb_only = bool(records) and not in_video
    result = {
        "has_ai_imagegen": bool(records),
        "count": len(records),
        "in_video": in_video,
        "thumbnail_only": thumb_only,
        # in-video AI imagery -> flag true; thumbnail-only base -> false (video isn't synthetic)
        "ai_generated_visuals": in_video,
        "youtube_altered_content": "No",  # stylized, non-deceptive; still verify per plan doc
        "note": ("stylized non-photoreal AI illustrations animated deterministically"
                 if in_video else
                 "AI only in thumbnail base; video visuals are deterministic Remotion"),
    }
    print(json.dumps(result, indent=2))
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Magnific image-gen shell-side helpers")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("put", help="PUT a local file to a presigned upload URL")
    pp.add_argument("local_file")
    pp.add_argument("url")
    pp.set_defaults(func=cmd_put)

    pf = sub.add_parser("fetch", help="download a creation URL (+ record provenance)")
    pf.add_argument("url")
    pf.add_argument("out_path")
    pf.add_argument("--project", help="project dir; records provenance under assets/imagegen/")
    pf.add_argument("--model", default=None)
    pf.add_argument("--prompt", default=None)
    pf.add_argument("--tool", default="images_generate")
    pf.add_argument("--refs", nargs="*", default=None)
    pf.add_argument("--in-video", action="store_true",
                    help="imagery appears INSIDE the video (must be stylized)")
    pf.set_defaults(func=cmd_fetch)

    pd = sub.add_parser("disclosure", help="report AI-disclosure status from provenance")
    pd.add_argument("--project", required=True)
    pd.set_defaults(func=cmd_disclosure)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
