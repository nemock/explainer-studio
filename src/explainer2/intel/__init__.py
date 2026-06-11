"""YouTube Intelligence Engine (PRD §5.1) — pure-Python fetch plane.

Shells out to the system yt-dlp binary (no API key, no quota, nothing added to
the media venv). Claude never runs here; this package only gathers and shapes
data. The Blueprint itself is written by the generation plane from intel.json.
"""
