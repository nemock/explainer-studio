#!/usr/bin/env python3
"""render_queue.py — the launchd runner for the render queue (src/explainer2/jobqueue.py).

Drains the spool one job at a time and exits. launchd starts it when a job is submitted
(WatchPaths on <spool>/trigger) and on an interval as a backstop, so every job runs
outside any Claude session and survives the desktop app being quit.

Usage:
  render_queue.py                run: drain the spool, then exit (what launchd calls)
  render_queue.py --status       print the queue and the engine lock
  render_queue.py --plist LABEL  print a LaunchAgent plist for this checkout
  render_queue.py --enable LABEL create the spool and switch the queue on for this machine
  render_queue.py --disable      switch it off (verbs run inline again; queued jobs stay on disk)

Installing (once per machine):
  1. render_queue.py --plist com.example.render-queue > ~/Library/LaunchAgents/com.example.render-queue.plist
  2. launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.example.render-queue.plist
  3. render_queue.py --enable com.example.render-queue

The plist's stdout/stderr MUST stay on the boot volume (~/Library/Logs). A launchd job
whose stdio points at an external volume dies silently with exit 78 when the volume is
not mounted yet.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from explainer2 import jobqueue                    # noqa: E402

PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{script}</string>
    </array>
    <key>WatchPaths</key>
    <array>
        <string>{trigger}</string>
    </array>
    <key>StartInterval</key>
    <integer>120</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log}</string>
    <key>StandardErrorPath</key>
    <string>{log}</string>
</dict>
</plist>
"""


def _log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}", flush=True)


def main():
    a = sys.argv[1:]
    if a[:1] == ["--status"]:
        print(jobqueue.status_text())
        return 0
    if a[:1] == ["--plist"] and len(a) == 2:
        print(PLIST.format(label=a[1], python=sys.executable, script=Path(__file__).resolve(),
                           trigger=jobqueue.spool() / "trigger",
                           log=Path.home() / "Library" / "Logs" / f"{a[1]}.log"), end="")
        return 0
    if a[:1] == ["--enable"] and len(a) == 2:
        sp = jobqueue.spool()
        (sp / "jobs").mkdir(parents=True, exist_ok=True)
        (sp / "logs").mkdir(parents=True, exist_ok=True)
        (sp / "trigger").touch()
        (sp / "enabled").write_text(json.dumps({"label": a[1], "enabled_at": time.strftime("%Y-%m-%dT%H:%M:%S")}))
        print(f"render queue enabled: {sp}")
        return 0
    if a[:1] == ["--disable"]:
        try:
            (jobqueue.spool() / "enabled").unlink()
        except OSError:
            pass
        print("render queue disabled: heavy verbs run inline again")
        return 0
    if a:
        sys.exit(__doc__.strip())
    return jobqueue.run_forever(log=_log)


if __name__ == "__main__":
    sys.exit(main())
