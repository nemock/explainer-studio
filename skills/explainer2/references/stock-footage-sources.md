# Stock Footage & Image Sources — free B-roll to augment Adobe Stock

A tracked list of **free** stock-footage and stock-photo sources for B-roll
(`type: footage` / `type: figure` slides — see [deck-playbook.md](deck-playbook.md) §4),
used **in addition to** the operator's paid **stock.adobe.com** membership (the
PRD-declared primary, human-in-the-loop via the `assets` assist flow). Curated
from the Flurdeh/Youtube-Resources list (2026-06-24).

## Hard rule — verify the license per clip, every time

Free does NOT mean unconditional. **Check the license on the specific clip's own
page before using it** — even on a CC0-leaning site, individual items can carry a
different license or an attribution requirement. When a clip is used:

- Record its **source, URL, and license** in the project (the `assets` ingest
  flow writes provenance into `manifest.json → assets.licensed`; if hand-placing
  a clip, add the same record by hand).
- Default to **CC0 / no-attribution-required** sources for the cleanest footing;
  treat anything else as attribution-required until its page proves otherwise.
- Same posture as the rest of the studio: licensed assets are tracked; we never
  republish a competitor's media (PRD boundary).

## Stock video (free)

- **[Pexels Videos](https://videos.pexels.com/)** — CC0, completely free. *(strong default)*
- **[Pixabay](https://pixabay.com/)** — large library; per-item license varies, check each.
- **[Mixkit](https://mixkit.co/)** — video, music, SFX, templates; many no-attribution, check the page.
- **[Coverr](https://coverr.co/)** — CC0; new clips weekly.
- **[Life of Vids](https://www.lifeofvids.com/)** — clips & loops, CC0-style.
- **[Mazwai](https://mazwai.com/)** — CC HD clips; **per-clip licensing — check each**.
- **[Pond5 Free](https://www.pond5.com/free)** — public-domain historic media.
- **[VYOO (Veed)](https://www.veed.io/vyoo)** — free vertical videos (handy for Shorts B-roll).

## Stock photos (free) — for `figure`/`footage` stills

- **[Unsplash](https://unsplash.com/)**, **[Pexels](https://www.pexels.com/)**, **[Pixabay](https://pixabay.com/)** — the big three; mostly CC0, check each.
- **[StockSnap](https://stocksnap.io/)**, **[Negative Space](https://negativespace.co/)**, **[Gratisography](https://gratisography.com/)**, **[Snappy Goat](https://snappygoat.com/)** (12M+ CC0), **[Skitter Photo](https://skitterphoto.com/)**, **[Barn Images](https://barnimages.com/)**, **[LibreShot](https://libreshot.com/)**, **[ABSFreePic](http://absfreepic.com/)**.
- **[Creative Commons Search](https://search.creativecommons.org/)** — searches many libraries at once.

## Paid (primary + alternates)

- **[Adobe Stock](https://stock.adobe.com/)** — the operator's membership; **primary** for extensive/specific B-roll, via the `assets` assist flow (guided searches + watched inbox). PRD-declared exception; human-in-the-loop, never an API dependency.
- Others (only if ever needed): Shutterstock, Stocksy, Fotolia.

Source list: [Flurdeh/Youtube-Resources](https://github.com/Flurdeh/Youtube-Resources#stock-footage).
