#!/usr/bin/env python3
"""login_alert.py: when an unattended `claude -p` dies because Claude is logged out,
open a Chrome tab that says so, and leave it there until someone reads it.

Why (operator, 2026-11-27): an expired headless login stopped publishing at least four
times (2026-08-14, 09-14, 11-10, 11-12), once for ~52 hours. The only signal was a macOS
banner that lives for a few seconds, often at 5 a.m. A tab is still on screen when the
operator sits down. The fix is always the same: open Terminal, run `claude auth login`.

One page, shared by every unattended spawner (the recording watcher's publish runs, the
Long View passes, the Shorts-card worker). Incident state and the page live OUTSIDE any
repo, in ~/Library/Application Support/brg-login-alert/ (override: LOGIN_ALERT_DIR).

  * check <log> --source NAME   Read a finished (or long-running) worker log. Logged-out
                                signature: raise the alert, exit 3. Otherwise: clear
                                any open incident, exit 0.
  * raise --source NAME [--detail TEXT] [--log PATH]
  * clear [--source NAME]       Mark resolved. An open tab refreshes itself every 30 s
                                and turns green.
  * status                      Print the incident state.
  * preview                     Write the page from sample data and print its path
                                (opens nothing, touches no real incident).

The tab opens once per incident, then again only if the incident is still open
REOPEN_AFTER_S later (closed without fixing). LOGIN_ALERT_NO_OPEN=1 suppresses opening
(tests). Stdlib only, so any python3 runs it.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

STATE_DIR = Path(os.environ.get("LOGIN_ALERT_DIR")
                 or Path.home() / "Library" / "Application Support" / "brg-login-alert")
STATE = STATE_DIR / "state.json"
PAGE = STATE_DIR / "claude-login-alert.html"
REOPEN_AFTER_S = 12 * 60 * 60
LOGIN_CMD = "claude auth login"

# A logged-out `claude -p` prints one of these AT THE START OF A LINE and exits within
# seconds, before any work. Seen across 1,194 failed publish logs (2026-08 to 11):
#   Failed to authenticate: OAuth session expired and could not be refreshed   (1,002)
#   Failed to authenticate: this login reached its time limit and cannot be…   (191)
#   Not logged in · Please run /login                                         (1)
# A healthy publish log is ~2 KB of model prose that may mention logins in passing, so
# the patterns are anchored to the line start, and a log over 4 KB never counts.
SIGNATURES = re.compile(
    r"^(?:Failed to authenticate\b|Not logged in\b.*(?:/login|auth login)"
    r"|Invalid API key\b.*(?:/login|auth login)|OAuth token has expired"
    r"|API Error: 401\b)", re.I)
MAX_FAILURE_LOG_BYTES = 4096


def auth_failure(log_path):
    """The matching line if `log_path` is a logged-out failure, else None."""
    p = Path(log_path)
    try:
        if p.stat().st_size > MAX_FAILURE_LOG_BYTES:
            return None
        text = p.read_text(errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        if SIGNATURES.search(line):
            return line.strip()[:400]
    return None


def _load():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def _save(st):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(st, indent=2))
    tmp.replace(STATE)


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _when(stamp):
    """'Thu 27 Nov, 5:04 AM' from a _now() stamp."""
    try:
        d = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return stamp or ""
    return d.strftime("%a %-d %b, %-I:%M %p")


def _open_tab():
    if os.environ.get("LOGIN_ALERT_NO_OPEN"):
        return False
    r = subprocess.run(["/usr/bin/open", "-a", "Google Chrome", str(PAGE)],
                       capture_output=True, text=True)
    if r.returncode != 0:                          # no Chrome: the default browser
        r = subprocess.run(["/usr/bin/open", str(PAGE)], capture_output=True, text=True)
    return r.returncode == 0


def _banner(text):
    if os.environ.get("LOGIN_ALERT_NO_OPEN"):
        return
    safe = text.replace("\\", " ").replace('"', "'")
    subprocess.run(["/usr/bin/osascript", "-e",
                    f'display notification "{safe[:200]}" with title "Claude is logged out"'],
                   check=False, capture_output=True)


def raise_alert(source, detail="", log_path=""):
    """Record an occurrence. Opens the tab on a new incident, or again if the incident
    has stayed open REOPEN_AFTER_S since the tab last opened. Returns True if it opened."""
    st = _load()
    if not st.get("active"):
        st = {"active": True, "first_seen": _now(), "count": 0, "sources": {},
              "opened_at": 0}
    st["count"] = st.get("count", 0) + 1
    st["last_seen"] = _now()
    if detail:
        st["detail"] = detail[:400]
    if log_path:
        st["log"] = str(log_path)
    src = st["sources"].setdefault(source, {"count": 0, "first_seen": _now()})
    src["count"] += 1
    src["last_seen"] = _now()
    _write_page(st)
    opened = False
    if time.time() - st.get("opened_at", 0) >= REOPEN_AFTER_S:
        opened = _open_tab()
        if opened or os.environ.get("LOGIN_ALERT_NO_OPEN"):
            st["opened_at"] = time.time()
        _banner(f"{source} could not run. Open Terminal and run: {LOGIN_CMD}")
    _save(st)
    return opened


def clear(source=""):
    """Close an open incident. Returns True if there was one."""
    st = _load()
    if not st.get("active"):
        return False
    st["active"] = False
    st["resolved_at"] = _now()
    st["resolved_by"] = source or "manual"
    _write_page(st)
    _save(st)
    return True


def check(log_path, source):
    """3 if the log is a logged-out failure (alert raised), else 0 (incident cleared)."""
    line = auth_failure(log_path)
    if line:
        raise_alert(source, line, log_path)
        return 3
    clear(source)
    return 0


# ---- the page ------------------------------------------------------------------

CSS = """
:root { --navy:#13284b; --ink:#1d2433; --muted:#5b6474; --red:#c8312b; --green:#1f8a4c;
        --paper:#f6f1e7; --card:#fffdf8; --line:#e4dccb; }
* { box-sizing:border-box; }
html,body { margin:0; height:100%; }
body { background:var(--paper); color:var(--ink);
       font:20px/1.5 -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", sans-serif;
       display:flex; align-items:center; justify-content:center; padding:48px 24px; }
main { width:min(920px,100%); background:var(--card); border:1px solid var(--line);
       border-radius:22px; box-shadow:0 24px 60px rgba(19,40,75,.14); overflow:hidden; }
.band { padding:40px 56px 34px; color:#fff; }
.down .band { background:linear-gradient(135deg,#a3221d,var(--red)); }
.ok .band { background:linear-gradient(135deg,#176a3a,var(--green)); }
.kicker { font-size:17px; letter-spacing:.14em; text-transform:uppercase; opacity:.85;
          font-weight:600; }
h1 { font-size:60px; line-height:1.05; margin:10px 0 12px; letter-spacing:-.02em; }
.lede { font-size:25px; margin:0; opacity:.95; max-width:34em; }
.body { padding:38px 56px 44px; }
h2 { font-size:18px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted);
     margin:0 0 16px; }
ol.steps { margin:0 0 30px; padding:0; list-style:none; counter-reset:s; }
ol.steps li { counter-increment:s; display:flex; gap:18px; align-items:flex-start;
              margin:0 0 18px; font-size:24px; }
ol.steps li::before { content:counter(s); flex:none; width:44px; height:44px; border-radius:50%;
              background:var(--navy); color:#fff; display:grid; place-items:center;
              font-weight:700; font-size:21px; margin-top:-2px; }
.cmd { display:flex; align-items:center; gap:14px; margin-top:12px; }
code.big { font:600 30px/1 "SF Mono", ui-monospace, Menlo, monospace; background:var(--navy);
           color:#fff; padding:18px 24px; border-radius:12px; letter-spacing:.01em; }
button { font:600 18px/1 -apple-system, sans-serif; border:2px solid var(--navy);
         color:var(--navy); background:#fff; border-radius:10px; padding:14px 18px;
         cursor:pointer; }
button:hover { background:var(--navy); color:#fff; }
.note { color:var(--muted); font-size:19px; margin:4px 0 0; }
.facts { border-top:1px solid var(--line); padding-top:24px; display:grid;
         grid-template-columns:max-content 1fr; gap:8px 22px; font-size:18px; }
.facts dt { color:var(--muted); }
.facts dd { margin:0; overflow-wrap:anywhere; }
.facts code { font:15px/1.4 "SF Mono", ui-monospace, Menlo, monospace; color:var(--ink); }
footer { color:var(--muted); font-size:15px; margin-top:26px; }
"""


def _sources_text(st):
    parts = []
    for name, s in (st.get("sources") or {}).items():
        n = s.get("count", 0)
        parts.append(f"{name} ({n} {'try' if n == 1 else 'tries'})")
    return ", ".join(parts) or "unknown"


def _write_page(st):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    e = html.escape
    if st.get("active"):
        state_cls, kicker, title = "down", "Unattended jobs are paused", "Claude is logged out"
        lede = ("Publishing and the other background jobs can't run until you sign in "
                "again. Nothing is lost: they pick up where they stopped.")
        body = f"""
  <h2>To fix it</h2>
  <ol class="steps">
    <li><div>Open <b>Terminal</b>.</div></li>
    <li><div>Run this, and sign in when the browser opens:
      <div class="cmd"><code class="big" id="cmd">{e(LOGIN_CMD)}</code>
      <button id="copy" type="button">Copy</button></div></div></li>
    <li><div>That's all. The watchers retry on their own within about 30 minutes,
      and this page turns green when the next job gets through.</div></li>
  </ol>"""
    else:
        state_cls, kicker, title = "ok", "Resolved", "Claude is signed in again"
        lede = f"A job got through at {e(_when(st.get('resolved_at')))}. You can close this tab."
        body = ""
    facts = [("First failed", _when(st.get("first_seen"))),
             ("Last failed", _when(st.get("last_seen"))),
             ("Jobs affected", _sources_text(st))]
    if st.get("detail"):
        facts.append(("Error", st["detail"]))
    if st.get("log"):
        facts.append(("Log", st["log"]))
    dl = "".join(f"<dt>{e(k)}</dt><dd>{'<code>' + e(v) + '</code>' if k in ('Error', 'Log') else e(v)}</dd>"
                 for k, v in facts if v)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="30">
<title>{'⚠️ ' if st.get('active') else '✅ '}{e(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>{CSS}</style></head>
<body class="{state_cls}"><main>
<div class="band"><div class="kicker">{e(kicker)}</div><h1>{e(title)}</h1>
<p class="lede">{lede}</p></div>
<div class="body">{body}
  <dl class="facts">{dl}</dl>
  <footer>Written by explainer2/tools/login_alert.py · updated {e(_when(_now()))} ·
  this page refreshes itself every 30 seconds.</footer>
</div></main>
<script>
const b = document.getElementById('copy');
if (b) b.addEventListener('click', async () => {{
  const t = document.getElementById('cmd').textContent;
  try {{ await navigator.clipboard.writeText(t); }}
  catch (_) {{ const r = document.createRange(); r.selectNodeContents(document.getElementById('cmd'));
    const s = getSelection(); s.removeAllRanges(); s.addRange(r); document.execCommand('copy'); }}
  b.textContent = 'Copied'; setTimeout(() => b.textContent = 'Copy', 2000);
}});
</script></body></html>
"""
    tmp = PAGE.with_suffix(".tmp")
    tmp.write_text(page)
    tmp.replace(PAGE)


def main():
    global STATE, PAGE
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check"); c.add_argument("log"); c.add_argument("--source", required=True)
    r = sub.add_parser("raise"); r.add_argument("--source", required=True)
    r.add_argument("--detail", default=""); r.add_argument("--log", default="")
    k = sub.add_parser("clear"); k.add_argument("--source", default="")
    sub.add_parser("status")
    sub.add_parser("preview")
    a = ap.parse_args()
    if a.cmd == "check":
        return check(a.log, a.source)
    if a.cmd == "raise":
        raise_alert(a.source, a.detail, a.log)
        print(PAGE)
        return 0
    if a.cmd == "clear":
        print("cleared" if clear(a.source) else "no open incident")
        return 0
    if a.cmd == "status":
        print(json.dumps(_load(), indent=2) or "{}")
        return 0
    if a.cmd == "preview":
        STATE, PAGE = STATE_DIR / "preview-state.json", STATE_DIR / "preview.html"
        _write_page({"active": True, "first_seen": "2026-11-10 05:04:12",
                     "last_seen": "2026-11-10 07:51:40", "count": 7,
                     "sources": {"Publish (Founder Tip Tuesday)": {"count": 5},
                                 "Shorts card": {"count": 2}},
                     "detail": "Failed to authenticate: this login reached its time limit "
                               "and cannot be renewed. Run `claude auth login` to sign in again.",
                     "log": "make_money/recording_watcher/logs/"
                            "founder-tip-tuesday_20261110_104049_completion.log"})
        print(PAGE)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
