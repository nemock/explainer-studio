# The on-camera cold open — real Dave, inside the paper world

**Operator directive, 2026-08-12.** Dave appears on camera for the cold open of a deep
dive, and the paper world stays on screen around him so it does not read as a hard cut
between two filming styles.

His framing, verbatim:

> "perhaps we create a little bit of a scene, maybe not a theater, but maybe a desk with
> a monitor on it or something like that. We want it to take up most of the screen, but
> it'll be me speaking. It will actually be me, but we'll still have the paper craft
> motif so it doesn't look like a complete cut between two different filming styles. I
> think that would be very visually fun to do."

**Correction on the record:** the existing on-camera material is **Daily Beats**, where
Dave reacts to things on camera and the output is cut into Shorts. That is a separate
product. This is new, and it is deep-dive-native.

## The idea in one line

The paper world builds a **set**, and the monitor on that set is the only real-video
surface in the frame. Everything around it is papercraft. Dave is the footage inside it.

## Why this shape rather than a full-frame talking head

A full-frame cut to camera is exactly the "two different filming styles" problem Dave
named. Framing the footage inside a papercraft object solves it structurally: the eye
reads one continuous world with a screen in it, not a jump between a cartoon and a
webcam. It also means the transition into the first slide is a **camera move**, not a
cut — the shot can pull back from the monitor into the wider paper scene, which is the
motion library's home turf.

## Build spec

- **The set is papercraft, generated in Magnific**, same recipe as the rest of the
  world: cream ground, navy ink, the existing pastel range. A desk seen slightly
  three-quarter on, a monitor, and two or three props with real edges (a mug, a stack of
  paper, a plant). Deckle edges and torn paper, not vector shapes. Nothing photoreal.
- **The monitor's screen is a cutout** — a hole in the papercraft with the real video
  behind it, inset a couple of pixels so the paper bezel casts its usual soft shadow
  over the footage edge. The seam is the whole illusion; do not butt them flush.
- **Screen occupies roughly 55–70% of frame width.** Dave's brief is "most of the
  screen" while still reading as a set. Below about half it becomes a picture-in-picture
  gimmick; above about three quarters the paper stops registering.
- **Shoot flat and slightly wide** so the crop into the monitor's aspect does not cut
  his head. Frame him centre; the paper bezel will crop the edges.
- **Grade the footage toward the world**, lightly: warm it, lift the blacks a touch so
  it sits against cream rather than punching a hole in it. Do not stylise or posterise —
  he said "it will actually be me."
- **Length: 20–40 seconds**, the felt-moment open only. It hands off before the first
  argument beat.

## The exit

Do not cut. **Pull back and out**: the camera retreats from the monitor to reveal more
of the desk, and the first slide assembles in the space that opens up. Alternatively the
paper scene tears away along an existing act-boundary tear. Both keep continuity; a hard
cut throws away the reason for building the set.

## The chibi presenter is EXCLUDED (operator, 2026-08-12)

Dave is experimenting with a set of chibi papercraft figures that resemble him, and they
are **not to appear in these renders** while that experiment is unsettled. The library is
wired up (`remotion_engine.CHIBI_DIR`, refs of the form `chibi/<pose>`) and it is easy to
reach for, so this is a live risk rather than a theoretical one.

It matters most precisely here: a cold open with **real Dave** on the monitor and a
**chibi Dave** standing in the corner puts two competing representations of the same
person in one frame. Even once the experiment settles, that combination needs deciding
deliberately rather than arriving by default.

## What this is NOT

- Not a talking-head video with paper decoration.
- Not the whole runtime. Cold open only, unless a later test says otherwise.
- Not Daily Beats. Different product, different brand, different length.
- Not an excuse to add the chibi presenter. See above — excluded for now.
- Not a reason to skip the felt-moment discipline — the cold open still has to pass
  script-playbook §4.1's three tests. Being on camera makes a weak open worse, not
  better, because there is now a face selling it.

## BUILT 2026-08-12 — how to actually use it

The set, the keyer and the component all exist now. Three pieces:

**1. The plate.** `remotion/public/papercraft/desk_monitor.png` — a reusable asset, not a
one-off (a mug, a stack of paper, a plant; desk three-quarter, monitor face-on). Generate
new ones with the STYLE.md recipe and **the screen as a flat bright-green paper panel**,
which is the one place green is allowed in that plate.

> **`remotion/public/` is gitignored** (`.gitignore` line 4, `public/`), so this plate is
> not in the repo — same as every sting and papercraft asset before it. On a fresh clone
> it has to be regenerated: run the recipe below, then the keyer. The prompt is kept here
> for exactly that reason.
>
> *Prompt used for the current plate (gpt-2, 16:9), on top of the STYLE.md recipe:* a desk
> seen slightly three-quarter on with a large monitor facing the viewer straight on, the
> screen a completely flat plain empty bright green paper rectangle with nothing on it,
> navy bezel and stand, plus a paper mug, a small stack of paper sheets and a potted plant
> — everything else navy and cream, green used ONLY for the screen.

**2. The keyer.** `tools/key_screen.py` cuts the green to a genuinely transparent hole:

```bash
python3 tools/key_screen.py in.png remotion/public/papercraft/desk_monitor.png
```

It centre-crops to 16:9 first, erodes the hole a few pixels so the antialiasing and green
spill stay as opaque paper, feathers the edge, despills toward the bezel navy, and writes a
sidecar JSON with the **measured** screen rect. Copy that rect into the slide; never eyeball
it. Two things it exists to prevent, both of which bit during the build:

- despilling weighted by alpha leaves the eroded lip at full green (10,576 emerald pixels
  ringing the footage), because the lip is fully opaque and so gets a weight of zero;
- a plate that is not exactly the comp's aspect makes image fractions and frame fractions
  disagree by however much `objectFit: cover` crops, so every authored coordinate is off.

**3. The slide.** Deck type `oncamera`, one per script segment as usual:

```jsonc
{"id": "s01", "type": "oncamera", "video": "oncamera/57_cold_open.mp4",
 "screen": {"x0": 0.2423, "y0": 0.1463, "x1": 0.7562, "y1": 0.6356},
 "set": "papercraft/desk_monitor.png"}
```

`screen_width_frac` (default 0.62) sets how much of the frame the screen fills at rest —
Dave's 55-70%. The engine fills in the rest:

- **`startAtSec`**, so consecutive `oncamera` scenes play *one continuous take* instead of
  restarting the file on every slide. The deck is 1:1 with segments and the cold open spans
  several, so without this Dave jumps back to his first word four times.
- **`pullBack`** on the last scene of the run — the no-cut exit.
- **The chibi presenter is dropped** on these scenes by the engine, not by author discipline.

Author no `marks` on them; there is nothing to point at but Dave.

**The one non-obvious trap, for whoever touches the component next.** The footage layer is
absolutely positioned and the plate is an in-flow `<Img>`, and **CSS paints positioned boxes
above in-flow ones no matter the source order** — so without explicit `zIndex` the video
renders *on top of* the paper and the bezel never overlaps it. It looks like a geometry bug
and it is not. The tell: widening the bleed makes the leak *worse*, not better.

**Verify with a rendered still, not by reading the code.** Put a coloured border on a
placeholder take and count how many of those pixels survive the composite; zero means the
bezel covers the footage edge, which is the seam the whole idea rests on.

## Still open

**Dave's footage.** Drop the take at `remotion/public/oncamera/<slug>.mp4` and point the
slide's `video` at it. `remotion/public/oncamera/placeholder.mp4` is a burned-in timecode
clip for checking geometry and continuity — it is not for broadcast. A slide with no
`video` renders a blank paper screen and logs a warning rather than failing the render.

## How to test it honestly

Two videos on camera, the rest of the slate on paper, then compare. The confound to
avoid is topic: pick one story-led and one evidence-led so the format is the only
variable that moves. **#57 (Klarna, story-led)** and **#59 (the pilot-number
investigation, evidence-led)** are the natural pair.

And state the limit up front: with a channel median of 0.59 views/day, two videos will
not produce a statistically meaningful result. What they will produce is a look at
whether it is worth doing more of, plus a reusable asset if the set is any good.
