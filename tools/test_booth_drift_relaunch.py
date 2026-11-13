#!/usr/bin/env python3
"""A booth relaunch keeps its drift results, and a card still unchecked at Finish gets checked
by the render, never by a text to the operator.

Run:  PYTHONPATH=src ~/myenv/bin/python3.12 tools/test_booth_drift_relaunch.py

Drives the real booth over HTTP with whisper stubbed out. The failure this guards: on #81
(2026-11-03) a relaunch followed by a quick Finish rewrote the report with every card
`unchecked` and `rerecord` empty, the watcher read that as clear to render, and a take still
waiting to be re-recorded was minutes from rendering.
"""
import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ["EXPLAINER_RENDER_LOCK_HELD"] = "1"      # never wait on a real render in a test
os.environ.pop("EXPLAINER_BOOTH_NO_DRIFT", None)

from explainer2 import recorder                     # noqa: E402
from explainer2.media import adlib, scriptguard     # noqa: E402
from explainer2.project import Project              # noqa: E402


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rw = _load("recording_watcher")
p1 = _load("phase1_render")
LOG = []
rw.log = lambda cfg, msg: LOG.append(msg)

CARDS = {
    0: "Every clean take in this project reads the whole card from the first word to the last.",
    1: ("This card holds thirty words so that a take which stops early loses a long run of them, "
        "and the check can see plainly that the rest of the card never reached the microphone."),
    2: "The last card is short and clean, and nothing about it should ever change at all.",
}
CUT_OFF = "This card holds thirty words so that"

TEXT = {}                   # stem -> what whisper "hears"
CALLS = []                  # stems actually transcribed
HOLD = {}                   # stem -> Hold: the transcription waits on it


class Hold:
    """Stops one transcription mid-flight. abandon=True makes it fail when released, which is
    what the real thing does at Finish: the booth process exits with whisper still running.
    In this test the worker thread outlives the booth, so it must not get to save a result."""

    def __init__(self, abandon=False):
        self.event, self.abandon = threading.Event(), abandon


def fake_transcribe(path, model, timeout):
    stem = Path(path).stem
    CALLS.append(stem)
    hold = HOLD.get(stem)
    if hold:
        hold.event.wait(30)
        if hold.abandon:
            raise RuntimeError("booth exited")
    if TEXT.get(stem) is None:
        raise RuntimeError("whisper is broken")
    return TEXT[stem]


recorder._transcribe_isolated = fake_transcribe
recorder._announce_finish = lambda *a: None
recorder._render_active = lambda: False


def wav_bytes(seconds):
    path = Path(tempfile.mkstemp(suffix=".wav")[1])
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(b"\0\0" * int(48000 * seconds))
    data = path.read_bytes()
    path.unlink()
    return data


class Booth:
    """One real booth session, in a thread, on a free port."""

    def __init__(self, proj):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        os.environ["EXPLAINER_RECORDER_PORT"] = str(self.port)
        self.thread = threading.Thread(target=recorder.run, args=(proj, False), daemon=True)
        self.thread.start()
        self.wait(lambda: self.get("/session"))

    def url(self, path):
        return f"http://127.0.0.1:{self.port}{path}"

    def get(self, path):
        try:
            with urllib.request.urlopen(self.url(path), timeout=5) as r:
                return json.loads(r.read())
        except OSError:
            return None

    def post(self, path, body=b""):
        req = urllib.request.Request(self.url(path), data=body, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    def wait(self, cond, what="the booth"):
        deadline = time.time() + 30
        while time.time() < deadline:
            if cond():
                return
            time.sleep(0.05)
        raise AssertionError(f"timed out waiting for {what}")

    def drift(self, sid):
        return (self.get("/segments")[sid].get("drift") or {}).get("status")

    def wait_all_checked(self):
        self.wait(lambda: all((c.get("drift") or {}).get("status") == "done"
                              for c in self.get("/segments")), "the drift checks")

    def retake(self, sid):
        """Saves a new take. A different length, so its size differs as well as its mtime."""
        self.post(f"/save?seg={sid}", wav_bytes(1.0 + len(CALLS) / 100))

    def finish(self):
        self.post("/done")
        self.thread.join(30)
        assert not self.thread.is_alive(), "the booth did not exit on Finish"


def main():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pdir = root / "2026-11-03_81_test"
        vdir = pdir / "voiceover"
        vdir.mkdir(parents=True)
        (pdir / "project.json").write_text(json.dumps({"title": "t", "voice_source": "operator"}))
        (pdir / "deck.json").write_text("{}")
        (pdir / "script.json").write_text(json.dumps({"segments": [
            {"id": i, "slide": f"s{i}", "text": t} for i, t in CARDS.items()]}))
        for i in CARDS:
            (vdir / f"seg_{i:03d}.wav").write_bytes(wav_bytes(1.0))
            TEXT[f"seg_{i:03d}"] = CARDS[i]
        TEXT["seg_001"] = CUT_OFF
        proj = Project.load(pdir)
        work = pdir / "work"

        def report():
            return json.loads((work / "adlib_report.json").read_text())

        def statuses():
            return [r["status"] for r in report()["segments"]]

        sent = root / "sent.txt"
        launched = []
        cfg = {"python": sys.executable, "launch_booth": str(ROOT / "tools" / "launch_booth.py"),
               "max_concurrent_renders": 99, "log_file": str(root / "w.log"),
               "logs_dir": str(root / "logs"), "claude_cwd": td,
               "operator_alert_cmd": ["/bin/sh", "-c", f'printf "%s\\n" "$1" >> "{sent}"', "alert"]}
        show = {"id": "studio", "mode": "studio", "project_globs": [str(pdir)], "lookback_days": 3}
        rw.launch_render = lambda c, s, p: launched.append(p)
        rw.script_guard_ok = lambda c, p: (True, "")
        rw.notify_once = lambda *a, **k: True

        def texts():
            return sent.read_text().splitlines() if sent.exists() else []

        def cycle():
            launched.clear()
            rw.run_studio(cfg, show, False, False)
            return len(launched)

        verbs = []
        real_adlib_rc = [None]

        def fake_verb(cmd):
            verbs.append(cmd[1:])
            if cmd[1] == "adlib":
                if real_adlib_rc[0] is not None:
                    return real_adlib_rc[0]
                adlib.run_unchecked(Project.load(pdir))
            return 0
        p1.run_verb = fake_verb
        p1.studio_announce = lambda *a: None
        p1._reap = lambda why: None

        # 1. First pass: every take checked, the cut-off take flagged.
        b = Booth(proj)
        b.wait_all_checked()
        b.finish()
        assert statuses() == ["verbatim", "rerecord", "verbatim"], statuses()
        assert report()["rerecord"] == [1] and report()["unchecked"] == []
        assert sorted(CALLS) == ["seg_000", "seg_001", "seg_002"], CALLS
        first = {r["id"]: r for r in report()["segments"]}

        # 2. THE BUG. Relaunch, Finish at once with nothing re-recorded: the verdicts stand,
        #    nothing is transcribed again, and the watcher still holds and texts.
        CALLS.clear()
        b = Booth(proj)
        assert b.drift(1) == "done", "a restored result must show before any worker runs"
        b.finish()
        assert CALLS == [], f"an unchanged take must not be transcribed again: {CALLS}"
        assert {r["id"]: r for r in report()["segments"]} == first
        assert report()["rerecord"] == [1] and report()["unchecked"] == []
        assert cycle() == 0, "a flagged card must hold the render"
        assert len(texts()) == 1 and "card(s) 2" in texts()[0], texts()

        # 3. Re-record that card and Finish before whisper gets to it: only it is unchecked,
        #    the others keep their verdicts, and its old flag is gone with its old take.
        HOLD["seg_001"] = Hold(abandon=True)
        TEXT["seg_001"] = CARDS[1]
        b = Booth(proj)
        b.retake(1)
        b.wait(lambda: "seg_001" in CALLS, "the re-take's transcription to start")
        b.finish()
        HOLD.pop("seg_001").event.set()
        assert statuses() == ["verbatim", "unchecked", "verbatim"], statuses()
        assert report()["rerecord"] == [] and report()["unchecked"] == [1]
        assert CALLS == ["seg_001"], f"only the re-take is checked: {CALLS}"

        # 4. Unchecked at Finish: no hold, no text, and the render is submitted.
        n_texts = len(texts())
        assert cycle() == 1, "unchecked must not hold the render"
        assert len(texts()) == n_texts, "unchecked must never text the operator"
        assert any(m.startswith("STUDIO-UNCHECKED") for m in LOG), LOG

        # 5. Phase 1 checks that one take FIRST, then renders. A clean take clears the report.
        CALLS.clear()
        verbs.clear()
        assert p1.run_studio(str(pdir), "exp", time.time()) == 0
        assert verbs[0] == ["adlib", str(pdir), "--unchecked"] and verbs[1][0] == "media", verbs
        assert CALLS == ["seg_001"], f"only the unchecked take is transcribed: {CALLS}"
        assert statuses() == ["verbatim", "verbatim", "verbatim"], statuses()
        assert report()["unchecked"] == [] and report()["rerecord"] == []
        assert (work / "render_complete.json").exists()
        assert rw.studio_rendered(pdir), "that render covers this recording"
        assert cycle() == 0
        assert report()["model"] == adlib.MODEL

        # 6. The check finds a take that really lost its words: no render, no failure record,
        #    and the NEXT watcher cycle is what holds and texts.
        (work / "render_complete.json").unlink()
        CARD_0_CUT = "Every clean take"
        HOLD["seg_000"] = Hold(abandon=True)
        CARDS[0] = ("This one is a longer card that the operator cut off after three words, so "
                    "most of what the card says never reached the microphone at all.")
        script = json.loads((pdir / "script.json").read_text())
        script["segments"][0]["text"] = CARDS[0]
        (pdir / "script.json").write_text(json.dumps(script))
        TEXT["seg_000"] = CARD_0_CUT
        b = Booth(proj)
        b.retake(0)
        b.wait(lambda: b.drift(0) == "running", "the re-take's transcription to start")
        b.finish()
        HOLD.pop("seg_000").event.set()
        verbs.clear()
        assert report()["unchecked"] == [0], report()["unchecked"]
        assert p1.run_studio(str(pdir), "exp", time.time()) == 0, "a verdict is not a failure"
        assert [v[0] for v in verbs] == ["adlib"], f"must not render: {verbs}"
        assert report()["rerecord"] == [0], report()["rerecord"]
        assert not (work / "render_complete.json").exists()
        assert not (work / "render_failure.json").exists()
        n_texts = len(texts())
        assert cycle() == 0, "the flag from the check must hold the render"
        assert len(texts()) == n_texts + 1 and "card(s) 1" in texts()[-1], texts()

        # 7. A transcript is stored, not a verdict: fix the card's text between sessions and
        #    the flag clears with no transcription and no re-record.
        CALLS.clear()
        CARDS[0] = CARD_0_CUT
        script["segments"][0]["text"] = CARDS[0]
        (pdir / "script.json").write_text(json.dumps(script))
        b = Booth(proj)
        b.finish()
        assert CALLS == [], CALLS
        assert report()["rerecord"] == [] and statuses()[0] == "verbatim", statuses()

        # 8. Whisper broken during the render's check: the card stays unchecked, nobody is
        #    texted, the render goes ahead, and RESUME.md names the card.
        HOLD["seg_002"] = Hold(abandon=True)
        b = Booth(proj)
        b.retake(2)
        b.wait(lambda: b.drift(2) == "running", "the re-take's transcription to start")
        b.finish()
        HOLD.pop("seg_002").event.set()
        TEXT["seg_002"] = None
        verbs.clear()
        n_texts = len(texts())
        assert p1.run_studio(str(pdir), "exp", time.time()) == 0
        assert [v[0] for v in verbs][:2] == ["adlib", "media"], verbs
        assert report()["unchecked"] == [2]
        assert "STILL UNCHECKED" in (work / "RESUME.md").read_text()
        assert len(texts()) == n_texts
        # ...and the same when the verb itself dies.
        real_adlib_rc[0] = 1
        verbs.clear()
        assert p1.run_studio(str(pdir), "exp", time.time()) == 0
        assert [v[0] for v in verbs][:2] == ["adlib", "media"], verbs
        real_adlib_rc[0] = None

        # 9. A re-take landing DURING a transcription gets its own check. Before this the
        #    booth dropped the stale result and the card read "running" until Finish.
        TEXT["seg_002"] = CARDS[2]
        CALLS.clear()
        HOLD["seg_002"] = Hold()
        b = Booth(proj)
        b.wait(lambda: b.drift(2) == "running", "the backfill to reach the take")
        b.retake(2)
        HOLD.pop("seg_002").event.set()
        b.wait(lambda: b.drift(2) == "done", "the re-take's own check")
        assert CALLS == ["seg_002", "seg_002"], CALLS
        b.finish()
        assert report()["unchecked"] == [], report()["unchecked"]

        # 10. A row filled in after Finish cannot vouch for an unstamped take's text; that
        #     would turn scriptguard's "unstamped" into a false "match".
        wav2 = vdir / "seg_002.wav"
        wav2.write_bytes(wav_bytes(2.5))
        scriptguard.drop_meta(vdir, "seg_002")
        rep = report()
        rep["segments"][2] = {"id": 2, "status": "unchecked"}
        rep["unchecked"] = [2]
        (work / "adlib_report.json").write_text(json.dumps(rep))
        adlib.run_unchecked(Project.load(pdir))
        row = report()["segments"][2]
        assert row["status"] == "verbatim" and "script_text" not in row, row
        assert "script_text" in report()["segments"][1], "a stamped take keeps its text"

        # 11. Nothing to do: no transcription, and the report is not rewritten.
        CALLS.clear()
        before = (work / "adlib_report.json").stat().st_mtime_ns
        out = adlib.run_unchecked(Project.load(pdir))
        assert CALLS == [] and out["transcribed"] == 0, (CALLS, out)
        assert (work / "adlib_report.json").stat().st_mtime_ns == before

        # 12. A report from before transcripts were stored still counts: its rows are kept
        #     and only the gap is filled. A take newer than the report is not described by it.
        (work / adlib.TRANSCRIPTS).unlink()
        rep = report()
        rep["segments"][2] = {"id": 2, "status": "unchecked"}
        (work / "adlib_report.json").write_text(json.dumps(rep))
        adlib.run_unchecked(Project.load(pdir))
        assert CALLS == ["seg_002"], CALLS
        CALLS.clear()
        future = time.time() + 60
        os.utime(wav2, (future, future))
        (work / adlib.TRANSCRIPTS).unlink()
        adlib.run_unchecked(Project.load(pdir))
        assert CALLS == ["seg_002"], CALLS

        # 13. A NEW take of an already-flagged card that also lost its words alerts again;
        #     the same take, seen again, does not.
        def flag_card_2(heard):
            rep = report()
            rep["segments"][1] = {"id": 1, "status": "rerecord", "drift": 0.5, "asr_text": heard}
            rep["rerecord"], rep["unchecked"] = [1], []
            (work / "adlib_report.json").write_text(json.dumps(rep))
        (work / "render_complete.json").unlink(missing_ok=True)
        flag_card_2("the first bad take")
        assert cycle() == 0
        n_texts = len(texts())
        assert cycle() == 0
        assert len(texts()) == n_texts, "the same take must not text twice"
        flag_card_2("a second bad take")
        assert cycle() == 0
        assert len(texts()) == n_texts + 1 and "card(s) 2" in texts()[-1], texts()

    print("OK — test_booth_drift_relaunch")


if __name__ == "__main__":
    sys.exit(main())
