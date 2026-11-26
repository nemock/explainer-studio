#!/usr/bin/env python3
"""The booth marks every card that needs re-recording, and the operator can approve a take.

Run:  PYTHONPATH=src ~/myenv/bin/python3.12 tools/test_booth_rerecord_marks.py

Operator, 2026-11-25: a text said "re-record card 1" and he had to find a session to open
the booth; once it was open, nothing showed which card it meant. And twice a transcript
misheard a take he had recorded correctly, with no way for him to say so. Covers:
  * the three markers (a watcher request, a stale text stamp, words missing from the take)
  * a newer take clearing the request marker
  * "Approve take": outranks the transcript at Finish, stamps the text for the render's
    script guard, and lapses when the take is replaced
  * the watcher reading booth card numbers out of a publish block
"""
import importlib.util
import json
import os
import socket
import sys
import tempfile
import threading
import time
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
os.environ["EXPLAINER_RENDER_LOCK_HELD"] = "1"
os.environ.pop("EXPLAINER_BOOTH_NO_DRIFT", None)

from explainer2 import recorder                     # noqa: E402
from explainer2.media import adlib, scriptguard     # noqa: E402
from explainer2.project import Project              # noqa: E402

CARDS = {
    0: "Rockwell Automation has agreed to buy an Austrian company that builds robots for pallets.",
    1: ("This card holds thirty words so that a take which stops early loses a long run of them, "
        "and the check can see plainly that the rest of the card never reached the microphone."),
    2: "The last card is short and clean, and nothing about it should ever change at all.",
}
TEXT = {}

recorder._transcribe_isolated = lambda path, model, timeout: TEXT[Path(path).stem]
recorder._announce_finish = lambda *a: None
recorder._render_active = lambda: False


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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
    def __init__(self, proj):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        os.environ["EXPLAINER_RECORDER_PORT"] = str(self.port)
        self.thread = threading.Thread(target=recorder.run, args=(proj, False), daemon=True)
        self.thread.start()
        self.wait(lambda: self.get("/session"))

    def get(self, path):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}", timeout=5) as r:
                return json.loads(r.read())
        except OSError:
            return None

    def post(self, path, body=b""):
        if isinstance(body, dict):
            body = json.dumps(body).encode()
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body,
                                     method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return json.loads(e.read() or b"{}") | {"http": e.code}

    def wait(self, cond, what="the booth"):
        deadline = time.time() + 30
        while time.time() < deadline:
            if cond():
                return
            time.sleep(0.05)
        raise AssertionError(f"timed out waiting for {what}")

    def segs(self):
        return self.get("/segments")

    def wait_checked(self):
        self.wait(lambda: all((c.get("drift") or {}).get("status") == "done"
                              for c in self.segs() if c["recorded"]), "the drift checks")

    def finish(self):
        self.post("/done")
        self.thread.join(30)
        assert not self.thread.is_alive(), "the booth did not exit on Finish"


def main():
    rw = _load("recording_watcher")

    # The watcher reads card numbers from a publish block: the field first, prose second.
    assert rw.publish_block_cards({"rerecord_cards": [1, 4], "reason": "r"}) == {0: "r", 3: "r"}
    prose = {"operator_action": "Robot Roundup: re-record booth card 1. The take says "
                                "'Australian'.", "reason": "card 1 says Australian"}
    assert rw.publish_block_cards(prose) == {0: "card 1 says Australian"}
    assert set(rw.publish_block_cards({"operator_action": "cut cards 3, 5 and 7"})) == {2, 4, 6}
    assert rw.publish_block_cards({"operator_action": "cut 20 seconds"}) == {}

    with tempfile.TemporaryDirectory() as td:
        pdir = Path(td) / "2026-11-25_rrp-test"
        vdir, work = pdir / "voiceover", pdir / "work"
        vdir.mkdir(parents=True)
        work.mkdir()
        (pdir / "project.json").write_text(json.dumps({"title": "t", "voice_source": "operator"}))
        (pdir / "deck.json").write_text("{}")
        (pdir / "script.json").write_text(json.dumps({"segments": [
            {"id": i, "slide": f"s{i}", "text": t} for i, t in CARDS.items()]}))
        for i, t in CARDS.items():
            (vdir / f"seg_{i:03d}.wav").write_bytes(wav_bytes(1.0))
            scriptguard.stamp(vdir, f"seg_{i:03d}", t, seg_id=i, slide=f"s{i}")
            TEXT[f"seg_{i:03d}"] = t
        # card 1 (booth card 2): the transcript lost most of the card
        TEXT["seg_001"] = "This card holds thirty words so that"
        # card 2 (booth card 3): recorded against older text
        scriptguard.stamp(vdir, "seg_002", "An older wording of the last card.", seg_id=2)
        # card 0 (booth card 1): the watcher reopened the booth for it, after this take
        (work / "rerecord_request.json").write_text(json.dumps(
            {"at": time.time() + 1, "cards": {"0": "card 1 says Australian"}}))
        proj = Project.load(pdir)

        b = Booth(proj)
        b.wait_checked()
        s = b.segs()
        assert s[0]["needs"] == ["card 1 says Australian"], s[0]["needs"]
        assert s[1]["needs"] == ["words from the card are missing from the take"], s[1]["needs"]
        assert s[2]["needs"] == ["recorded against older card text"], s[2]["needs"]
        assert not any(c["approved"] for c in s)

        # A newer take of card 0 clears the request marker.
        time.sleep(1.1)
        b.post("/save?seg=0", wav_bytes(1.3))
        b.wait_checked()
        assert b.segs()[0]["needs"] == [], b.segs()[0]["needs"]

        # Approving card 1: the transcript no longer holds it, and Finish reports it approved.
        assert b.post("/approve", {"seg": 1, "on": True})["ok"]
        s = b.segs()
        assert s[1]["approved"] and s[1]["needs"], "the reason stays listed; the UI shows approved"
        assert adlib.is_approved(work, vdir / "seg_001.wav")

        # Approving the stale card stamps the current text, so the script guard passes it.
        assert b.post("/approve", {"seg": 2, "on": True})["ok"]
        assert b.segs()[2]["needs"] == []
        assert scriptguard.read_meta(vdir, "seg_002")["source"] == "booth-approved"

        # Withdrawing works; approving an unrecorded or unknown card does not.
        assert b.post("/approve", {"seg": 2, "on": False})["ok"]
        assert not b.segs()[2]["approved"]
        assert b.post("/approve", {"seg": 2, "on": True})["ok"]
        assert b.post("/approve", {"seg": 9, "on": True}).get("http") == 400

        b.finish()
        rep = json.loads((work / "adlib_report.json").read_text())
        st = {r["id"]: r["status"] for r in rep["segments"]}
        assert st[1] == "approved" and rep["rerecord"] == [], rep
        sess = json.loads((work / "booth_session.json").read_text())
        assert sess["cards"][1]["approved"] is True
        assert scriptguard.check(Project.load(pdir))["stale"] == []

        # The render-side check honors it too (phase 1's adlib --unchecked path).
        rep["segments"][1]["status"] = "unchecked"
        (work / "adlib_report.json").write_text(json.dumps(rep))
        adlib.run_unchecked(Project.load(pdir))
        rep = json.loads((work / "adlib_report.json").read_text())
        assert rep["segments"][1]["status"] == "approved" and rep["rerecord"] == [], rep

        # A new take of an approved card starts unapproved.
        b = Booth(Project.load(pdir))
        time.sleep(1.1)
        b.post("/save?seg=1", wav_bytes(1.4))
        b.wait_checked()
        s = b.segs()
        assert not s[1]["approved"] and s[1]["needs"], s[1]
        b.finish()

    print("OK — test_booth_rerecord_marks")


if __name__ == "__main__":
    sys.exit(main())
