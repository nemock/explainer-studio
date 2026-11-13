#!/usr/bin/env python3
"""face_light.py: is Dave's face lit well enough on a thumbnail base?

Operator, 2026-11-13: the thumbnails were "starting to get a little bit too dark. I look like I'm standing in the
shadows." Measured across 43 bases: a well-lit face averages 110-135 (mean luma, 0-255, inside the detected face box);
the dark ones were #82 thumb A 83, #63 86, #75 88, #40 93, #41 96, #80 97, all from prompts asking for "moody low light".

    python3 tools/face_light.py <base.png> [more.png ...]

Prints the face luma per image and exits 1 if any face is under FLOOR (or no face is found, which usually means the
face is too dark or too small to read). Run it on every base before the headline goes on (thumbnail-playbook §2d, §7,
§10). Needs OpenCV: run with /Users/davesaunders/myenv/bin/python3.12.
"""
import sys

import cv2
import numpy as np

FLOOR = 100      # below this the face reads as "in the shadows" at thumbnail size
TARGET = (110, 140)

_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


def face_luma(path):
    """Mean luma inside the most confident detected face, or None when no face is found."""
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"face_light: cannot read {path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    side = gray.shape[1] // 12
    faces, _, weights = _cascade.detectMultiScale3(gray, 1.1, 6, minSize=(side, side), outputRejectLevels=True)
    if len(faces) == 0:
        return None
    # the most confident detection, not the largest: a big false hit on a dark background reads as a dark face
    x, y, w, h = faces[int(np.argmax(np.ravel(weights)))]
    return float(np.mean(gray[y:y + h, x:x + w]))


def main(paths):
    bad = 0
    for p in paths:
        v = face_luma(p)
        if v is None:
            print(f"NO FACE  {p}  (too dark or too small to detect; look at it)")
            bad += 1
        elif v < FLOOR:
            print(f"TOO DARK {round(v):>3}  {p}  (floor {FLOOR}, aim {TARGET[0]}-{TARGET[1]}: regenerate with the face lit)")
            bad += 1
        else:
            print(f"OK       {round(v):>3}  {p}")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1:]))
