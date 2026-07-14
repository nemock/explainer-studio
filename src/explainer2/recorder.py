# VENDORED_FROM: nemock/video-explainer-system @ d593aa41dc32d04e3b714b4731b1763f6e31843e (src/explainer/recorder.py) — copied 2026-06-10; diverges freely (v1 is frozen).
"""Integrated voiceover recorder (PRD §18.2). `explainer record <dir>` launches a local
browser teleprompter that records the mic per segment (MediaRecorder), saves each clip
straight into the project's voiceover/ folder, and supports re-recording — no external app.

Booth 2.0 (docs/booth-upgrade-plan.md):
  Batch 1 — Focus Mode teleprompter; HOT RELOAD (/segments re-reads the script from disk);
            INLINE EDIT (/edit writes back to script.json / shorts/plan.json with a
            one-time .pre-booth.bak per file per session).
  Batch 2 — instant take QC (/save analyzes the wav: peak, mean level, duration vs the
            ~150wpm estimate → green/amber/red badge); room-tone check (/roomtone);
            session wrap report (work/booth_session.json on Finish).
  Batch 4 — per-take DRIFT check (serialized mlx_whisper worker; defers while a render
            holds the machine render lock); take manager (/takes, /takefile, /promote);
            continuity playback is client-side.
  Batch 5 — /deckslide serves per-card slide JSON from deck.json for the in-booth
            mini-preview (rendered client-side; the true frames are Remotion's, so the
            booth shows an honest stylized cue, not a fake "exact" render).

Run it in the background; it returns when the operator clicks "Finish" in the browser."""
import fcntl
import json, os, queue, re, shutil, subprocess, sys, threading, time, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ASSETS = Path(__file__).parent / "assets"
WPM = 150                    # matches the client + script-playbook read-rate math
RENDER_LOCKFILE = "/tmp/explainer-render.lock"   # renderlock.LOCKFILE (shared, fixed)
DRIFT_TIMEOUT_S = 150            # hard cap on a drift transcription; a hung mlx_whisper must never hold this server's GIL


def _transcribe_isolated(wav_path, model, timeout):
    """Transcribe one take in a CHILD process with a hard timeout.

    mlx_whisper runs on the Metal GPU and holds the Python GIL, so a single hung
    transcription froze the entire booth (0% CPU, every /save and /clip wedged
    behind the stuck GIL). Running it in a subprocess means a hang is killed by the
    timeout and the server never notices, and each take gets a clean process free of
    any Metal/GPU state that accumulates across runs. Raises subprocess.TimeoutExpired
    on hang (the caller marks the take errored and moves on)."""
    code = ("import sys, json, mlx_whisper; "
            "print(json.dumps(mlx_whisper.transcribe(sys.argv[1], path_or_hf_repo=sys.argv[2])['text']))")
    r = subprocess.run([sys.executable, "-c", code, wav_path, model],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "transcribe failed").strip()[:200])
    return json.loads(r.stdout.strip()).strip()


def _load_segments(proj):
    """Build the card list fresh from disk (script.json + shorts/plan.json).

    Called on every /segments request so mid-session edits — inline or external —
    show up on a page refresh instead of requiring a server restart. Returns
    (seg_list, stem) where stem maps card id -> clip filename stem."""
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
                    # where an inline edit of this card writes back to:
                    "plan_slug": _slug, "plan_role": _role,
                })
                _next += 1
    stem = {s["id"]: (s.get("clip") or f"seg_{s['id']:03d}") for s in seg_list}
    return seg_list, stem


# ---------------------------------------------------------------- audio analysis

def _probe_wav(path: Path):
    """Duration + level stats via ffprobe/ffmpeg volumedetect. Cheap (<300ms)."""
    try:
        dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip())
    except (ValueError, TypeError):
        return None
    vd = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(path),
                         "-af", "volumedetect", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    mean = peak = None
    m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", vd)
    if m: mean = float(m.group(1))
    m = re.search(r"max_volume:\s*(-?[\d.]+)\s*dB", vd)
    if m: peak = float(m.group(1))
    return {"dur_s": round(dur, 2), "mean_db": mean, "peak_db": peak}


def _expected_s(text):
    w = len(re.findall(r"\S+", text or ""))
    return max(1, round(w / WPM * 60))


def _qc(text, probe):
    """Turn raw stats into a verdict the operator can act on while still in the chair.
    Thresholds are deliberately forgiving — amber is 'glance at it', red is 'retake'."""
    if not probe:
        return None
    notes, level = [], "good"
    exp = _expected_s(text)
    peak, mean, dur = probe.get("peak_db"), probe.get("mean_db"), probe.get("dur_s", 0)
    if peak is not None and peak > -0.5:
        notes.append(f"hot — peak {peak:g} dB (clipping risk)"); level = "bad"
    elif peak is not None and peak > -2.0:
        notes.append(f"near-hot — peak {peak:g} dB"); level = "warn"
    if mean is not None and mean < -34:
        notes.append(f"quiet — mean {mean:g} dB (raise input gain)")
        level = "warn" if level == "good" else level
    if dur and exp and dur > exp * 1.6:
        notes.append(f"long — {dur:g}s vs ~{exp}s expected")
        level = "warn" if level == "good" else level
    elif dur and exp and dur < exp * 0.5:
        notes.append(f"short — {dur:g}s vs ~{exp}s expected (false start?)")
        level = "warn" if level == "good" else level
    return {**probe, "expected_s": exp, "level": level, "notes": notes}


def _render_active():
    """True while a render holds the machine-global render lock — the drift worker
    backs off so whisper never competes with an encode for the 16 GB budget."""
    try:
        fd = open(RENDER_LOCKFILE, "a+")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            return False
        except BlockingIOError:
            return True
        finally:
            fd.close()
    except OSError:
        return False


def run(proj, open_browser=True):
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
    state = {"done": False, "t0": time.time()}
    lock = threading.Lock()          # serialize disk load/edit against each other
    cur = {}                         # latest {"segs": [...], "stem": {...}}
    edited = set()                   # card ids edited this session (chip in the UI)
    backed_up = set()                # files already snapshotted to .pre-booth.bak this session
    qc_cache = {}                    # stem -> (mtime, qc dict)
    drift_state = {}                 # stem -> {"status": ..., "drift": float, "asr_text": str}
    drift_q = queue.Queue()
    drift_enabled = os.environ.get("EXPLAINER_BOOTH_NO_DRIFT", "") != "1"
    roomtone = {}                    # analysis of voiceover/roomtone.wav

    def refresh():
        with lock:
            cur["segs"], cur["stem"] = _load_segments(proj)
        return cur["segs"]

    refresh()

    def wav(sid): return vdir / f"{cur['stem'][sid]}.wav"
    def recorded(sid): return wav(sid).exists()

    def takes(sid):
        return len(list(vdir.glob(f"{cur['stem'][sid]}.take*.wav"))) + (1 if recorded(sid) else 0)

    def _take_nums(sid):
        out = []
        for f in vdir.glob(f"{cur['stem'][sid]}.take*.wav"):
            m = re.search(r"\.take(\d+)\.wav$", f.name)
            if m:
                out.append(int(m.group(1)))
        return sorted(out)

    def archive_take(sid):
        """Keep the previous take before overwriting (retake history, PRD §5.3).
        Numbered max+1, NOT count+1 — /promote consumes an archive slot, and a
        count-based number would collide with (and silently overwrite) a
        surviving archive on the next save."""
        if recorded(sid):
            nums = _take_nums(sid)
            n = (nums[-1] + 1) if nums else 1
            wav(sid).rename(vdir / f"{cur['stem'][sid]}.take{n}.wav")
            return n
        return 0

    def card(sid):
        return next((s for s in cur["segs"] if s["id"] == sid), None)

    def qc_for(sid, force=False):
        """Cached QC keyed on (stem, mtime) so re-takes re-analyze automatically."""
        f = wav(sid)
        if not f.exists():
            return None
        st = cur["stem"][sid]
        mt = f.stat().st_mtime
        hit = qc_cache.get(st)
        if hit and hit[0] == mt and not force:
            return hit[1]
        c = card(sid)
        q = _qc(c["text"] if c else "", _probe_wav(f))
        qc_cache[st] = (mt, q)
        return q

    # ---------------- drift worker (Batch 4) ----------------
    def drift_enqueue(sid):
        if not drift_enabled or not recorded(sid):
            return
        st = cur["stem"][sid]
        cs = drift_state.get(st, {})
        if cs.get("status") in ("queued", "running"):
            return
        drift_state[st] = {"status": "queued"}
        drift_q.put(sid)

    def drift_worker():
        from .media.adlib import MODEL, _drift   # shared thresholds + normalizer
        while True:
            sid = drift_q.get()
            if sid is None:
                return
            st = cur["stem"].get(sid)
            if st is None or not recorded(sid):
                continue
            if _render_active():
                # never run whisper against an active encode (16 GB budget) — requeue
                drift_state[st] = {"status": "deferred"}
                time.sleep(20)
                drift_q.put(sid)
                continue
            drift_state[st] = {"status": "running"}
            try:
                f = wav(sid)
                mtime = f.stat().st_mtime
                # transcribe in a child process (see _transcribe_isolated): a hung
                # mlx_whisper must never hold this server's GIL and freeze the booth.
                asr = _transcribe_isolated(str(f), MODEL, DRIFT_TIMEOUT_S)
                c = card(sid)
                d = _drift(c["text"] if c else "", asr)
                # a re-take may have landed mid-transcription — only publish if still current
                if f.exists() and f.stat().st_mtime == mtime:
                    drift_state[st] = {"status": "done", "drift": d, "asr_text": asr}
            except subprocess.TimeoutExpired:
                drift_state[st] = {"status": "error",
                                   "error": f"drift transcription exceeded {DRIFT_TIMEOUT_S}s — skipped (booth unaffected)"}
            except Exception as e:
                drift_state[st] = {"status": "error", "error": str(e)[:200]}

    threading.Thread(target=drift_worker, daemon=True).start()

    def backfill():
        """Analyze takes that already exist (resumed session): QC sync, drift queued."""
        for s in list(cur["segs"]):
            if recorded(s["id"]):
                qc_for(s["id"])
                st = cur["stem"][s["id"]]
                if st not in drift_state:
                    drift_enqueue(s["id"])
        rt = vdir / "roomtone.wav"
        if rt.exists():
            roomtone.update(_roomtone_verdict(_probe_wav(rt)))

    def _roomtone_verdict(probe):
        if not probe or probe.get("mean_db") is None:
            return {"level": "unknown", "notes": ["analysis failed"]}
        mean = probe["mean_db"]
        if mean < -55:
            return {**probe, "level": "good", "notes": [f"quiet room ({mean:g} dB floor)"]}
        if mean < -45:
            return {**probe, "level": "warn",
                    "notes": [f"audible noise floor ({mean:g} dB) — fan/HVAC? OK but not ideal"]}
        return {**probe, "level": "bad",
                "notes": [f"noisy room ({mean:g} dB) — find the source before recording"]}

    threading.Thread(target=backfill, daemon=True).start()

    def backup_once(path: Path):
        """One pre-edit snapshot per file per booth session — cheap undo, no clutter."""
        if str(path) not in backed_up and path.exists():
            shutil.copy2(path, path.with_name(path.name + ".pre-booth.bak"))
            backed_up.add(str(path))

    def apply_edit(sid, new_text):
        """Write an inline edit back to its source of truth. Main cards -> script.json
        segments[].text; short hook/outro cards -> shorts/plan.json cut[role]."""
        c = card(sid)
        if c is None or not new_text.strip():
            return False
        new_text = new_text.strip()
        with lock:
            if c.get("plan_slug"):
                plan_path = proj.dir / "shorts" / "plan.json"
                plan = json.loads(plan_path.read_text())
                hit = False
                for cut in plan:
                    if cut.get("slug") == c["plan_slug"] and cut.get(c["plan_role"]):
                        backup_once(plan_path)
                        cut[c["plan_role"]] = new_text
                        hit = True
                        break
                if not hit:
                    return False
                plan_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n")
            else:
                sp = proj.script_json
                script = json.loads(sp.read_text())
                hit = False
                for seg in script.get("segments", []):
                    if seg.get("id") == sid:
                        backup_once(sp)
                        seg["text"] = new_text
                        hit = True
                        break
                if not hit:
                    return False
                sp.write_text(json.dumps(script, indent=2, ensure_ascii=False) + "\n")
        edited.add(sid)
        refresh()
        # text changed → the old drift verdict no longer applies to this card
        st = cur["stem"].get(sid)
        if st and drift_state.get(st, {}).get("status") == "done":
            drift_enqueue(sid)
        return True

    def take_list(sid):
        st = cur["stem"][sid]
        out = []
        if recorded(sid):
            out.append({"take": 0, "label": "current", "mtime": wav(sid).stat().st_mtime})
        for f in sorted(vdir.glob(f"{st}.take*.wav")):
            m = re.search(r"\.take(\d+)\.wav$", f.name)
            if m:
                out.append({"take": int(m.group(1)), "label": f"take {m.group(1)}",
                            "mtime": f.stat().st_mtime})
        return out

    def promote_take(sid, n):
        """Make an archived take the primary clip (current becomes a new archive)."""
        st = cur["stem"][sid]
        src = vdir / f"{st}.take{n}.wav"
        if not src.exists():
            return False
        with lock:
            archive_take(sid)               # current -> next take number
            src.rename(wav(sid))
        qc_cache.pop(st, None)
        drift_state.pop(st, None)
        qc_for(sid)
        drift_enqueue(sid)
        return True

    def wrap_report():
        segs = refresh()
        cards = []
        total_audio = total_takes = 0
        qc_warn = drift_flag = 0
        for s in segs:
            sid = s["id"]; st = cur["stem"][sid]
            q = qc_for(sid) if recorded(sid) else None
            dr = drift_state.get(st)
            t = takes(sid)
            total_takes += t
            if q:
                total_audio += q.get("dur_s") or 0
                if q["level"] != "good":
                    qc_warn += 1
            if dr and dr.get("status") == "done" and dr.get("drift", 0) >= 0.15:
                drift_flag += 1
            cards.append({"id": sid, "slide": s["slide"], "recorded": recorded(sid),
                          "takes": t, "edited": sid in edited,
                          "qc": q, "drift": (dr or {}).get("drift"),
                          "drift_status": (dr or {}).get("status")})
        rec_n = sum(1 for c in cards if c["recorded"])
        rep = {"cards": cards, "recorded": rec_n, "total_cards": len(cards),
               "total_takes": total_takes, "retakes": max(0, total_takes - rec_n),
               "audio_s": round(total_audio, 1), "qc_flags": qc_warn,
               "drift_flags": drift_flag, "edited_cards": len(edited),
               "session_s": round(time.time() - state["t0"], 1),
               "roomtone": roomtone or None}
        (work_dir / "booth_session.json").write_text(json.dumps(rep, indent=2))
        # Adlib-stage retirement (2026-07-03): emit the same artifact media/adlib.run
        # produces, straight from the in-session drift results — no second whisper
        # pass needed after recording. Cards whose drift check didn't complete are
        # "unchecked"; `explainer2 adlib` remains as the FALLBACK for those only.
        if drift_enabled:
            from .media.adlib import MODEL, MINOR, MAJOR
            rows, worst = [], 0.0
            for s in segs:
                sid = s["id"]; st = cur["stem"][sid]
                if not recorded(sid):
                    rows.append({"id": sid, "status": "not_recorded"}); continue
                dr = drift_state.get(st) or {}
                if dr.get("status") != "done":
                    rows.append({"id": sid, "status": "unchecked"}); continue
                d = dr.get("drift", 0.0); worst = max(worst, d)
                status = "verbatim" if d < MINOR else ("adlib" if d < MAJOR else "rerecord")
                rows.append({"id": sid, "status": status, "drift": d,
                             "script_text": s["text"], "asr_text": dr.get("asr_text", "")})
            (work_dir / "adlib_report.json").write_text(json.dumps(
                {"model": MODEL, "segments": rows, "worst_drift": worst,
                 "rerecord": [r["id"] for r in rows if r.get("status") == "rerecord"],
                 "unchecked": [r["id"] for r in rows if r.get("status") == "unchecked"],
                 "applied": [], "source": "booth"}, indent=2))
        return rep

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

        def _q(self, key, default="-1"):
            return parse_qs(urlparse(self.path).query).get(key, [default])[0]

        def do_GET(self):
            p = urlparse(self.path)
            if p.path == "/":
                self._send(200, html, "text/html; charset=utf-8")
            elif p.path == "/segments":
                segs = refresh()   # HOT RELOAD: always reflect what's on disk right now
                out = []
                for s in segs:
                    st = cur["stem"][s["id"]]
                    out.append({**s, "recorded": recorded(s["id"]), "takes": takes(s["id"]),
                                "edited": s["id"] in edited,
                                "qc": qc_cache.get(st, (None, None))[1] if recorded(s["id"]) else None,
                                "drift": drift_state.get(st)})
                self._send(200, json.dumps(out))
            elif p.path == "/session":
                self._send(200, json.dumps({
                    "roomtone": roomtone or None,
                    "drift_enabled": drift_enabled,
                    "render_active": _render_active()}))
            elif p.path == "/clip":
                sid = int(self._q("seg"))
                f = wav(sid) if sid in cur["stem"] else None
                self._send(200, f.read_bytes(), "audio/wav") if (f and f.exists()) else self._send(404, b"")
            elif p.path == "/takes":
                sid = int(self._q("seg"))
                self._send(200, json.dumps(take_list(sid) if sid in cur["stem"] else []))
            elif p.path == "/takefile":
                sid = int(self._q("seg")); n = int(self._q("n", "0"))
                if sid not in cur["stem"]:
                    return self._send(404, b"")
                f = wav(sid) if n == 0 else vdir / f"{cur['stem'][sid]}.take{n}.wav"
                self._send(200, f.read_bytes(), "audio/wav") if f.exists() else self._send(404, b"")
            elif p.path == "/deckslide":
                slide_id = self._q("slide", "")
                dj = proj.dir / "deck.json"
                if not dj.exists():
                    return self._send(404, b"{}")
                try:
                    slides = json.loads(dj.read_text()).get("slides", [])
                    hit = next((s for s in slides if s.get("id") == slide_id), None)
                    self._send(200, json.dumps(hit)) if hit else self._send(404, b"{}")
                except Exception:
                    self._send(404, b"{}")
            else:
                self._send(404, b"{}")

        def do_POST(self):
            p = urlparse(self.path)
            if p.path == "/save":
                sid = int(self._q("seg"))
                if sid not in cur["stem"]:
                    return self._send(404, json.dumps({"ok": False}))
                blob = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                webm = vdir / f"{cur['stem'][sid]}.webm"
                webm.write_bytes(blob)
                archive_take(sid)
                r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(webm),
                                    "-ar", "48000", "-ac", "1", str(wav(sid))], capture_output=True)
                webm.unlink(missing_ok=True)
                ok = r.returncode == 0 and wav(sid).exists()
                q = qc_for(sid, force=True) if ok else None
                if ok:
                    drift_enqueue(sid)
                self._send(200 if ok else 500,
                           json.dumps({"ok": ok, "seg": sid, "takes": takes(sid), "qc": q}))
            elif p.path == "/roomtone":
                blob = self.rfile.read(int(self.headers.get("Content-Length", 0)))
                tmp = vdir / "roomtone.webm"
                tmp.write_bytes(blob)
                out = vdir / "roomtone.wav"
                r = subprocess.run(["ffmpeg", "-hide_banner", "-y", "-i", str(tmp),
                                    "-ar", "48000", "-ac", "1", str(out)], capture_output=True)
                tmp.unlink(missing_ok=True)
                if r.returncode == 0 and out.exists():
                    roomtone.clear()
                    roomtone.update(_roomtone_verdict(_probe_wav(out)))
                    self._send(200, json.dumps(roomtone))
                else:
                    self._send(500, json.dumps({"level": "unknown"}))
            elif p.path == "/promote":
                try:
                    body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                    ok = promote_take(int(body["seg"]), int(body["take"]))
                except Exception:
                    ok = False
                self._send(200 if ok else 400, json.dumps({"ok": ok}))
            elif p.path == "/edit":
                try:
                    body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                    ok = apply_edit(int(body["seg"]), str(body.get("text", "")))
                except Exception:
                    ok = False
                self._send(200 if ok else 400, json.dumps({"ok": ok}))
            elif p.path == "/done":
                state["done"] = True
                self._send(200, json.dumps({"ok": True, "report": wrap_report()}))
            else:
                self._send(404, b"{}")

    # FIXED port so the origin (host:port) is stable across segments — Chrome scopes the mic
    # permission to the exact origin, so a random port re-prompts every tab. Override with
    # EXPLAINER_RECORDER_PORT, but keep it fixed so the grant persists.
    port = int(os.environ.get("EXPLAINER_RECORDER_PORT", "8765"))
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", port), H)   # threaded: /clip, /segments don't queue behind a /save's ffmpeg call
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
    drift_q.put(None)    # stop the drift worker
    seg_list = refresh()
    rec = [s["id"] for s in seg_list if recorded(s["id"])]
    miss = [s["id"] for s in seg_list if not recorded(s["id"])]
    result = {"recorded": rec, "missing": miss, "segments": len(seg_list)}
    done_marker.write_text(json.dumps({**result, "done": True}))  # durable Finish signal
    print("RECORD DONE:", json.dumps(result))
    return result
