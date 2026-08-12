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

## How to test it honestly

Two videos on camera, the rest of the slate on paper, then compare. The confound to
avoid is topic: pick one story-led and one evidence-led so the format is the only
variable that moves. **#57 (Klarna, story-led)** and **#59 (the pilot-number
investigation, evidence-led)** are the natural pair.

And state the limit up front: with a channel median of 0.59 views/day, two videos will
not produce a statistically meaningful result. What they will produce is a look at
whether it is worth doing more of, plus a reusable asset if the set is any good.
