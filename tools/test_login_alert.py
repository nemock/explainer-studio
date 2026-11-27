#!/usr/bin/env python3
"""Logged-out alert (2026-11-27): an unattended `claude -p` that dies on auth opens a
Chrome tab that stays until the operator signs in again, then turns green.

Run:  python3 tools/test_login_alert.py

The failure it guards: 2026-11-10 to 11-12, every publish died in ~2 s on an expired
login, the watcher logged 652 crashloop lines, and the only signal was a macOS banner.
Episodes waited up to ~52 hours.
"""
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="login-alert-test-"))
os.environ["LOGIN_ALERT_DIR"] = str(TMP / "state")
os.environ["LOGIN_ALERT_NO_OPEN"] = "1"
os.environ["CLAUDE_HEADLESS_TOKEN_FILE"] = str(TMP / "headless-token")
os.environ.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
os.environ["EXPLAINER_QUEUE_DIR"] = str(TMP / "spool")
os.environ["EXPLAINER_QUEUE_QUIET"] = "1"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


la = _load("login_alert")
rw = _load("recording_watcher")
FAILS = []


def check(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond:
        FAILS.append(what)


# The real 2026-11-10 log: a settings warning, then the auth line.
REAL = ("Permission allow rule (.claude/settings.local.json): Bash(cp …) has a wildcard "
        "before the rest of the command, so it also matches any options.\n"
        "Failed to authenticate: this login reached its time limit and cannot be renewed. "
        "Run `claude auth login` to sign in again, or use `claude setup-token` and set "
        "CLAUDE_CODE_OAUTH_TOKEN for unattended jobs\n")

logs = TMP / "logs"
logs.mkdir()
bad = logs / "founder-tip-tuesday_20261110_104049_completion.log"
bad.write_text(REAL)
check(la.auth_failure(bad) and "time limit" in la.auth_failure(bad),
      "the real 11-10 log reads as logged out")

prose = logs / "prose.log"
prose.write_text("Published. Note: Blotato said Not logged in to Threads, so I skipped it.\n"
                 "The upload Failed to authenticate once on X, then went through.\n")
check(la.auth_failure(prose) is None,
      "a short healthy log that mentions logins mid-sentence does not raise")
old_wording = logs / "old.log"
old_wording.write_text("Failed to authenticate: OAuth session expired and could not be refreshed\n")
check(la.auth_failure(old_wording), "the older 'OAuth session expired' wording raises")
slash = logs / "slash.log"
slash.write_text("Not logged in · Please run /login\n")
check(la.auth_failure(slash), "'Not logged in · Please run /login' raises")

big = logs / "big.log"
big.write_text("Published. The X post said: Not logged in to Blotato, retried.\n" * 200)
check(la.auth_failure(big) is None,
      "a long healthy log that quotes 'Not logged in' does not raise")
check(la.auth_failure(logs / "missing.log") is None, "a missing log does not raise")

# raise → active, page says logged out, tab counted as opened once
la.raise_alert("Publish (founder-tip-tuesday)", "Failed to authenticate", bad)
st = la._load()
check(st.get("active") and st.get("opened_at", 0) > 0, "first failure opens an incident")
check("Claude is logged out" in la.PAGE.read_text() and la.LOGIN_CMD in la.PAGE.read_text(),
      "the page names the problem and the command")
first_open = st["opened_at"]
la.raise_alert("Shorts card", "Not logged in")
st = la._load()
check(st["opened_at"] == first_open, "a second failure does not open a second tab")
check(set(st["sources"]) == {"Publish (founder-tip-tuesday)", "Shorts card"},
      "every affected job is listed")

st["opened_at"] = time.time() - la.REOPEN_AFTER_S - 5
la._save(st)
la.raise_alert("Shorts card", "Not logged in")
check(la._load()["opened_at"] > first_open, "still logged out 12 h later reopens the tab")

check(la.clear("test") and not la._load()["active"], "clear closes the incident")
check("signed in again" in la.PAGE.read_text(), "the page turns green")
check(la.clear("test") is False, "clearing twice is a no-op")

# check(): exit 3 on failure, 0 and clear otherwise
check(la.check(bad, "Shorts card") == 3 and la._load()["active"], "check raises on failure")
ok = logs / "ok.log"
ok.write_text("Carded https://youtu.be/abc\n")
check(la.check(ok, "Shorts card") == 0 and not la._load()["active"], "check clears on success")

# The watcher: newest completion log decides, counted once per log.
cfg = {"logs_dir": str(logs), "log_file": str(TMP / "watcher.log")}
for p in logs.glob("*.log"):
    if p != bad:
        p.unlink()
os.utime(bad, None)
rw.check_login(cfg)
c1 = la._load()
check(c1.get("active") and "Publish (founder-tip-tuesday)" in c1["sources"],
      "watcher raises on a logged-out publish log")
rw.check_login(cfg)
check(la._load()["count"] == c1["count"], "the same log is not counted every cycle")

fresh = logs / "the-teardown_20261111_090000_completion.log"
fresh.write_text("")                                  # a healthy run, still working
rw.check_login(cfg)
check(la._load()["active"], "a run that only just started does not clear yet")
old = time.time() - rw.LOGIN_SETTLE_S - 5
os.utime(bad, (old - 600, old - 600))                 # the failure came first
os.utime(fresh, (old, old))
rw.check_login(cfg)
check(not la._load()["active"], "a run past the settle time clears the alert")
check("LOGIN-OK" in (TMP / "watcher.log").read_text(), "the watcher logs the recovery")

# The dedicated headless token (2026-11-27): absent = inherited env, present = exported.
tokf = TMP / "headless-token"
check(la.headless_token() is None and "CLAUDE_CODE_OAUTH_TOKEN" not in la.headless_env(),
      "no token file: the env is left alone")
tokf.write_text("")
check(la.headless_token() is None, "an empty token file counts as no token")
tokf.write_text("pbpaste > ~/.claude-headless-token && chmod 600 ~/.claude-headless-token\n")
check(la.headless_token() is None and "CLAUDE_CODE_OAUTH_TOKEN" not in la.headless_env(),
      "a file holding the save command (the 2026-11-27 mistake) is not exported")
TOK = "sk-ant-oat01-" + "A1b2C3d4E5" * 5
tokf.write_text("  " + TOK + "\n")
check(la.headless_env().get("CLAUDE_CODE_OAUTH_TOKEN") == TOK,
      "a token file is exported, whitespace stripped")

la.raise_alert("Publish (x)", "Failed to authenticate")
page = la.PAGE.read_text()
check(la.MINT_CMD in page and "claude-headless-token" in page,
      "with a dedicated token, the page says to make a new token, not to log in")
la.clear("test")

# The watcher's publish run gets that env.
proj = TMP / "proj"
(proj / "work").mkdir(parents=True)
seen = []


class FakeChild:
    pid = 424242


real_popen = rw.subprocess.Popen
rw.subprocess.Popen = lambda cmd, **k: (seen.append(k.get("env") or {}), FakeChild())[1]
try:
    rw.spawn_completion(dict(cfg, claude_bin="/usr/bin/true", claude_cwd=str(TMP)),
                        {"id": "t", "skill": "/x/SKILL.md", "completion_steps": "Step 8"},
                        proj, dry=False)
finally:
    rw.subprocess.Popen = real_popen
check(seen and seen[0].get("CLAUDE_CODE_OAUTH_TOKEN") == TOK,
      "the watcher's publish run is spawned with the dedicated token")
tokf.unlink()

print()
if FAILS:
    print(f"{len(FAILS)} FAILED")
    sys.exit(1)
print("all passed")
