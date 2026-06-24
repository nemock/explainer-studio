# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/recorder.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""Integrated voiceover recorder (PRD §18.2). `explainer record <dir>` launches a local
browser teleprompter that records the mic per segment (MediaRecorder), saves each clip
straight into the project's voiceover/ folder, and supports re-recording — no external app.

Run it in the background; it returns when the operator clicks "Finish" in the browser."""
import json, os, subprocess, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ASSETS = Path(__file__).parent / "assets"


def run(proj, open_browser=True):
    from .media.common import effective_segments
    script = json.loads(proj.script_json.read_text())
    seg_list = [{"id": s["id"], "slide": s["slide"], "text": s["text"],
                 # optional v2 script fields — teleprompter context cues
                 "beat": s.get("beat"), "device": s.get("device"), "note": s.get("note")}
                for s in effective_segments(proj, script)]
    # Append the per-Short hook/outro lines from shorts/plan.json so the operator records
    # them in the SAME booth session (short-form best practices: a native 3–8s hook + a
    # short outro, recorded separately — NEVER lifted from the long-form). These save to
    # their own clip files (short_<slug>_{hook,outro}.wav), not seg_NNN.wav, so the shorts
    # cutter can find them. Additive: a cut with no hook/outro adds no cards.
    _next = (max(s["id"] for s in seg_list) + 1) if seg_list else 0
    _plan_path = proj.dir / "shorts" / "plan.json"
    if _plan_path.exists():
        try:
            _plan = json.loads(_plan_path.read_text())
        except Exception:
            _plan = []
        for _i, _cut in enumerate(_plan, 1):
            _slug = _cut.get("slug", f"cut{_i}")
            for _role in ("hook", "outro"):
                _line = _cut.get(_role)
                if not _line:
                    continue
                seg_list.append({
                    "id": _next, "slide": f"SHORT {_i} · {_role.upper()}", "text": _line,
                    "beat": None,
                    "device": f"⏩ SHORT {_i}/{len(_plan)} · {_role.upper()} — {_slug}",
                    "note": ("Punchy 3–8s. The very first words ARE the hook; no runway. "
                             "This is short-form only — do NOT reuse it in the long-form."
                             if _role == "hook" else
                             "Short outro (loops back into this Short's hook). Keep it tight; no sign-off."),
                    "clip": f"short_{_slug}_{_role}",
                })
                _next += 1
    vdir = proj.voiceover_dir
    # Finish signal (operator directive 2026-06-23): the booth runs DETACHED so it survives
    # the operator going AFK, which hides the old "process returns on Finish" signal from the
    # harness. So drop a durable sentinel file when the green button is clicked — a waiter
    # (tools/launch_booth.py --wait) watches for it and notifies. Clear any stale one now so
    # the waiter only fires for THIS session.
    work_dir = proj.dir / "work"; work_dir.mkdir(exist_ok=True)
    done_marker = work_dir / "record_done.json"
    done_marker.unlink(missing_ok=True)
    html = (ASSETS / "recorder.html").read_text().replace("{{TITLE}}", str(proj.data.get("title", "Voiceover")))
    state = {"done": False}

    # filename stem per card id: short hook/outro cards save to their own clip, everything
    # else to seg_NNN (the parent narrate/align path keys off seg_NNN).
    stem = {s["id"]: (s.get("clip") or f"seg_{s['id']:03d}") for s in seg_list}

    def wav(sid): return vdir / f"{stem[sid]}.wav"
    def recorded(sid): return wav(sid).exists()

    def takes(sid):
        return len(list(vdir.glob(f"{stem[sid]}.take*.wav"))) + (1 if recorded(sid) else 0)

    def archive_take(sid):
        """Keep the previous take before overwriting (retake history, PRD §5.3)."""
        if recorded(sid):
            n = len(list(vdir.glob(f"{stem[sid]}.take*.wav"))) + 1
            wav(sid).rename(vdir / f"{stem[sid]}.take{n}.wav")

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, (bytes, bytearray)) else str(body).encode()
            try:
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (ConnectionResetError, BrokenPipeError):
                pass  # browser aborted a clip playback request — routine, not an error

        def do_GET(self):
            p = urlparse(self.path)
            if p.path == "/":
                self._send(200, html, "text/html; charset=utf-8")
            elif p.path == "/segments":
                self._send(200, json.dumps([{**s, "recorded": recorded(s["id"]),
                                             "takes": takes(s["id"])} for s in seg_list]))
            elif p.path == "/clip":
                sid = int(parse_qs(p.query).get("seg", ["-1"])[0])
                f = wav(sid) if sid in stem else None
                self._send(200, f.read_bytes(), "audio/wav") if (f and f.exists()) else self._send(404, b"")
            else:
                self._send(404, b"{}")

        def do_POST(self):
            p = urlparse(self.path)
            if p.path == "/save":
                sid = int(parse_qs(p.query).get("seg", ["-1"])[0])
                if sid not in stem:
                    return self._send(404, json.dumps({"ok": False}))
                blob = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                webm = vdir / f"{stem[sid]}.webm"
                webm.write_bytes(blob)
                archive_take(sid)
                r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(webm),
                                    "-ar", "48000", "-ac", "1", str(wav(sid))], capture_output=True)
                webm.unlink(missing_ok=True)
                ok = r.returncode == 0 and wav(sid).exists()
                self._send(200 if ok else 500, json.dumps({"ok": ok, "seg": sid, "takes": takes(sid)}))
            elif p.path == "/done":
                state["done"] = True
                self._send(200, json.dumps({"ok": True}))
            else:
                self._send(404, b"{}")

    # FIXED port so the origin (host:port) is stable across segments — Chrome scopes the mic
    # permission to the exact origin, so a random port re-prompts every tab. Override with
    # EXPLAINER_RECORDER_PORT, but keep it fixed so the grant persists.
    port = int(os.environ.get("EXPLAINER_RECORDER_PORT", "8765"))
    try:
        srv = HTTPServer(("127.0.0.1", port), H)   # HTTPServer sets SO_REUSEADDR -> frees fast
    except OSError as e:
        raise RuntimeError(f"recorder port {port} is unavailable ({e}). A previous recorder may "
                           f"still be open — close that tab/process, or set EXPLAINER_RECORDER_PORT "
                           f"to another FIXED free port (keep it fixed so the mic grant persists).") from e
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"RECORDER READY → {url}\nRecord each segment in the browser, then click 'Finish & render'.", flush=True)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        while not state["done"]:
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    srv.shutdown()
    srv.server_close()   # release the fixed port promptly so the next segment can rebind it
    rec = [s["id"] for s in seg_list if recorded(s["id"])]
    miss = [s["id"] for s in seg_list if not recorded(s["id"])]
    result = {"recorded": rec, "missing": miss, "segments": len(seg_list)}
    done_marker.write_text(json.dumps({**result, "done": True}))  # durable Finish signal
    print("RECORD DONE:", json.dumps(result))
    return result
