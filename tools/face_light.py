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
import glob
import sys
from pathlib import Path

import cv2
import numpy as np

FLOOR = 100      # below this the face reads as "in the shadows" at thumbnail size
TARGET = (110, 140)

_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# --- which face is Dave's (2026-11-13) -------------------------------------------------------------
# Bases put Dave in a scene, often beside a second character (thumbnail-playbook's foil rule) or in a
# crowd. "Most confident" (this tool) picked a shopper behind him on #84 and called him too dark at 128;
# "largest" (shorts_thumbnail.py) tied him with a false hit on his sweatshirt. A size rule cannot fix
# both: the foil is sometimes bigger than he is (#45's support rep, #47's clock, #81's robot). So the
# face is RECOGNIZED: OpenCV's YuNet finds faces with landmarks, SFace compares each to his real
# photos in dave_selfies/, and the best match above SFace's published same-person threshold is him.
# The models live in library/models/face/ (gitignored, from github.com/opencv/opencv_zoo). If they
# are missing or nobody matches, each caller falls back to its old rule, so nothing gets worse.
REPO = Path(__file__).resolve().parent.parent
MODELS = REPO / "library" / "models" / "face"
YUNET = MODELS / "face_detection_yunet_2023mar.onnx"
SFACE = MODELS / "face_recognition_sface_2021dec.onnx"
REFERENCE = [REPO / "dave_selfies" / "dave_*_clean.png", REPO / "dave_selfies" / "Dave Saunders Headshot*"]
MATCH = 0.363    # SFace cosine similarity at or above which two faces are the same person (OpenCV's value)

_det = _rec = _ref = None


def _load():
    """Lazy-load the detector, recognizer and Dave's reference features; False if unavailable."""
    global _det, _rec, _ref
    if _ref is not None:
        return len(_ref) > 0
    _ref = []
    if not (YUNET.exists() and SFACE.exists()):
        return False
    _det = cv2.FaceDetectorYN.create(str(YUNET), "", (320, 320), 0.8, 0.3, 5000)
    _rec = cv2.FaceRecognizerSF.create(str(SFACE), "")
    for pattern in REFERENCE:
        for p in sorted(glob.glob(str(pattern))):
            img = cv2.imread(p)
            if img is None:
                continue
            faces = _yunet(img)
            if len(faces):
                big = max(faces, key=lambda f: f[2] * f[3])
                _ref.append(_rec.feature(_rec.alignCrop(img, big)))
    return len(_ref) > 0


def _yunet(img, max_side=1024):
    """YuNet faces in full-resolution coordinates. Detection runs on a copy at most `max_side` px:
    YuNet misses a face that fills a large frame (most of the selfie portraits at 1,700-3,000 px)."""
    h, w = img.shape[:2]
    s = min(1.0, max_side / max(h, w))
    small = img if s == 1.0 else cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    _det.setInputSize((small.shape[1], small.shape[0]))
    _, faces = _det.detect(small)
    if faces is None:
        return []
    faces = faces.copy()
    faces[:, :14] /= s          # box and the five landmarks back to full-resolution pixels
    return list(faces)


def find_dave(img):
    """(box (x, y, w, h), similarity) of the face that matches Dave's photos, or (None, best) when none
    matches or the models are missing (best is then the closest similarity seen, or None)."""
    if img is None or not _load():
        return None, None
    best, best_sim = None, None
    for f in _yunet(img):
        feat = _rec.feature(_rec.alignCrop(img, f))
        sim = max(_rec.match(feat, r, cv2.FaceRecognizerSF_FR_COSINE) for r in _ref)
        if best_sim is None or sim > best_sim:
            best, best_sim = f, sim
    if best is None or best_sim < MATCH:
        return None, best_sim
    return tuple(int(v) for v in best[:4]), float(best_sim)


def _iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ix = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    iy = max(0, min(ay + ah, by + bh) - max(ay, by))
    inter = ix * iy
    return inter / float(aw * ah + bw * bh - inter) if inter else 0.0


def dave_face(img, min_side, fallback="confident"):
    """Dave's face box (x, y, w, h) in `img` (BGR), or None.

    The Haar box overlapping the recognized face is returned, so the luma FLOOR (calibrated on Haar
    boxes) and the callers' box geometry mean what they always meant. With no recognized face, the old
    rule: `fallback="confident"` (this tool) or `"largest"` (shorts_thumbnail.py)."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces, _, weights = _cascade.detectMultiScale3(gray, 1.1, 6, minSize=(min_side, min_side),
                                                   outputRejectLevels=True)
    faces = [tuple(int(v) for v in f) for f in faces]
    weights = np.ravel(weights) if len(faces) else []
    dave, _ = find_dave(img)
    if dave is not None:
        overlap = [(_iou(f, dave), f) for f in faces]
        hit = max(overlap, default=(0, None))
        return hit[1] if hit[0] >= 0.2 else dave
    if not faces:
        return None
    if fallback == "largest":
        return max(faces, key=lambda f: f[2] * f[3])
    # the most confident detection, not the largest: a big false hit on a dark background reads as a dark face
    return faces[int(np.argmax(weights))]


def face_luma(path):
    """Mean luma inside Dave's face (dave_face), or None when no face is found."""
    img = cv2.imread(str(path))
    if img is None:
        raise SystemExit(f"face_light: cannot read {path}")
    box = dave_face(img, img.shape[1] // 12)
    if box is None:
        return None
    x, y, w, h = box
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
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
