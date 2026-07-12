# YouTube `publish` — setup & operation

`bin/explainer2 publish` uploads the **primary long-form video** to YouTube via the
operator's own OAuth against the official **YouTube Data API v3**. No third-party
SaaS, no per-token billing — secrets stay on this Mac. It is a **separate,
operator-invoked step** (like `promote`, but for the main video, not the Shorts);
the generation pipeline still stops at the package.

It is **hybrid**: the API does everything it can, and the command prints a short
Chrome checklist for the four things the API cannot do (there is no public endpoint
for them): **A/B thumbnail Test & Compare, title A/B, end screens, pinned comment.**

---

## One-time machine setup (do this once)

1. **Google Cloud project + API**
   - console.cloud.google.com → create a project (e.g. "explainer2-publish").
   - APIs & Services → Library → enable **YouTube Data API v3**.
2. **OAuth client**
   - APIs & Services → Credentials → Create credentials → **OAuth client ID** →
     application type **Desktop app**.
   - Download the JSON, save it to **`~/.config/explainer2/client_secret.json`**.
   - On the OAuth consent screen, add your Google account (nemock@gmail.com) as a
     **test user** (keeps you out of Google's verification review).
3. **Python libs** (into the shared venv):
   ```
   ~/myenv/bin/pip install google-api-python-client google-auth-oauthlib
   ```
   (Pillow is already present — used to auto-compress thumbnails under the 2MB limit.)

---

## One-time per channel — authorize (the Blotato model, local)

One Google account owns several channels (Dave Saunders `@nemock`, Waveform
`@Waveform-fm`, Circumvent, …). We bind **one token per channel** so uploads can
never leak across channels. For each channel, run authorize and **pick that channel
on Google's consent screen**:

```
bin/explainer2 publish --authorize --channel nemock       # → Dave Saunders (FWF/BRG)
bin/explainer2 publish --authorize --channel waveform      # → Waveform (Binaural)
bin/explainer2 publish --authorize --channel circumvent    # → Circumvent
```

Each writes `~/.config/explainer2/token_<key>.json` and records that channel's real
**id + title + handle** in `~/.config/explainer2/channels.json` (the registry). Pick
any key names you like — they're just labels the projects reference.

> If a channel is a **Brand Account**, Google shows a "Choose a channel" screen after
> the account picker — that is where you select it. The token then acts only as that
> channel; `channels.list(mine=true)` returns just that one.

---

## Per project — declare the target channel

In the project's `project.json`:
```json
"youtube_channel": "waveform"
```
Resolution order: `--channel` flag → `project.json "youtube_channel"` → default
`nemock`. So FWF videos go to Dave Saunders automatically; a Waveform project set to
`"waveform"` can only ever load the Waveform token.

**Channel guard:** before every upload the command re-reads the token's real channel
id and aborts unless it equals the registry id for that key. There is no "active
channel" fallback — the wrong-channel mistake is structurally impossible.

---

## Operating it

```
# dry run — prints the exact API payload + the Chrome checklist (safe, no upload)
bin/explainer2 publish <project_dir>

# upload PRIVATE (default), then finish in Chrome
bin/explainer2 publish <project_dir> --fire

# upload PUBLIC
bin/explainer2 publish <project_dir> --fire --privacy public

# schedule (RFC3339 UTC; forces private + publishAt)
bin/explainer2 publish <project_dir> --fire --when 2026-07-15T13:00:00Z
```

**What `--fire` sets via the API:** file, title, description (with chapters), tags,
category, privacy/schedule, made-for-kids, **thumbnail A** (auto-compressed to <2MB if
needed), and the **Deep Dives** playlist. On success it backfills `youtube_url` +
`posted` into `package/meta.json`.

**What you still do in Chrome** (the command prints these each run):
1. **A/B thumbnails** — A is set; open Test & Compare, add variant B, start the test.
2. **Title A/B** (optional) — add the alternate title.
3. **End screen** — subscribe + Best-for-viewer over the last ~20s.
4. **Pinned comment** — **verify the active channel is the right one** (photo avatar,
   verified badge — not another channel on the same login), then post + pin.

---

## Notes & limits
- **Quota:** ~1,600 units/upload against a default 10,000/day ≈ 6 uploads/day.
- **AI-use / altered-content** disclosure has no API field; the default is "No", which
  is correct for our real-voice + deterministic-motion videos — confirm only.
- Safety: dry-run by default; `--fire` defaults to **private**; it refuses to fire
  while any blocking warning (missing file, unauthorized channel) is unresolved.
