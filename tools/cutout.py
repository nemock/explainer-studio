"""Local background removal for thumbnail headshots (rembg / U2-Net, runs on
the M3 — no cloud, no subscription). Light-background selfies become
transparent-PNG cutouts that composite onto any deck-theme thumbnail.

Usage: python tools/cutout.py <in.jpg> <out.png>
First run downloads the U2-Net weights (~170 MB) to ~/.u2net once.
"""
import sys
from pathlib import Path


def cutout(src, dst):
    from rembg import remove
    src, dst = Path(src), Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(remove(src.read_bytes(), post_process_mask=True))
    return str(dst)


if __name__ == "__main__":
    print(cutout(sys.argv[1], sys.argv[2]))
