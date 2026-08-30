---
name: icon-export
description: Exports an approved master icon SVG into platform assets - favicon.ico + SVG favicon, apple-touch-icon, PWA 192/512 + maskable, App/Play Store PNGs, macOS icns, GitHub social preview, plus HTML/manifest snippets. Use when the user asks to export, generate, or ship favicons, app icon files, or store icons, or to wire the exported set into a repo. Not for designing, ideating, or critiquing icons.
license: MIT
argument-hint: <master.svg path> [--targets web,apple,android,github]
---

# icon-export

Deterministically fan the approved master (`icon-design/icon.svg`) out into
every platform asset, with the one rule that prevents the classic shipping bug:
**platform-masked targets get the full-square variant; self-rendered surfaces
keep the rounded rectangle.** iOS, Play, apple-touch-icon and PWA-maskable
apply their own mask — feeding them a pre-rounded icon double-masks it and
leaves transparent corner slivers.

## When NOT to use

- No approved master yet → `icon-draw` then `icon-critique` produce and gate
  `icon-design/icon.svg`; don't promote a random SVG yourself.
- Concepting (`icon-brief`), drawing (`icon-draw`), reviewing (`icon-critique`).
- Arbitrary SVG→PNG conversion, photo resizing, og:images for articles.

## Workflow

1. **Locate the master.** Default `icon-design/icon.svg`. If it doesn't exist,
   stop and route to `icon-draw`/`icon-critique` (or ask which file the user
   considers approved). Never silently pick a candidate.
2. **Run the exporter** (deterministic; does everything below itself):

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/export_icons.py" icon-design/icon.svg \
       [--out DIR] [--targets web,apple,android,github] [--name icon] [--force]
   ```

   - Autodetects a renderer (rsvg-convert → resvg → cairosvg → inkscape →
     ImageMagick → macOS qlmanage+sips); exits 2 with install hints if none.
   - Derives the **square variant** (rounded background swapped for a plain
     full-bleed square) and the **1280×640
     social banner** internally.
   - **Refuses to overwrite existing files** (exit 3) unless `--force` — list
     the collisions to the user and get an explicit go-ahead first.
   - Validates every PNG's real dimensions and the ICO structure; exit 1 on
     any failure. Relay failures verbatim; don't hand-render around them.
3. **Wire into the repo if asked.** `--out public/` (or the site's static
   dir) plus the head tags from `snippet.html` and the `icons` array from
   `manifest.webmanifest`. For README use, reference the SVG master directly.
4. **Report.** The WROTE table (file, size), where the snippets go, and the
   platform caveats from the gotchas below that apply.

## Output spec (default `icon-design/export/`)

| Target | Files | Source variant |
| --- | --- | --- |
| web | `favicon.ico` (16+32+48), `icon.svg`, `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png`, `icon-mask-512.png`, `snippet.html`, `manifest.webmanifest` | rounded; square for touch-icon + maskable |
| apple | `appstore-1024.png`, `icon.iconset/` (10 files, iconutil naming), `icon.icns` (macOS only) | square for store; rounded for icns |
| android | `play-store-512.png` | square |
| github | `social-preview-1280x640.png`, `avatar-512.png` | banner / square |

Everything size-validated; exporter exit code 0 is the done signal.

## Gotchas

- **Never round the store assets.** If a platform shows rounded corners it
  applies them itself. The exporter's square variant exists for exactly this
  (the GitHub avatar also ships square — GitHub masks avatars).
- App Store uploads want a **fully opaque, flattened** 1024 PNG. The exporter
  detects an alpha channel on store PNGs and flattens automatically when
  ImageMagick is present; otherwise it prints the exact `magick … -alpha
  remove` command — relay that warning, don't drop it.
- The exporter renders only house-subset masters (it security-scans the SVG
  first and fails closed on scripts/external refs/embedded raster) — "run it
  on this random SVG I found" is out of contract.
- The maskable icon's glyph must sit in the centered 40%-radius safe circle —
  `icon-draw`'s linter warned about this at draw time; if the mask crops the
  glyph, fix the master, not the export.
- qlmanage fallback is fine for previews/dev; for a real release install
  librsvg (`brew install librsvg`) and re-run — antialiasing quality differs.
- iOS 26+ layered "Liquid Glass" icons are built in Apple's Icon Composer from
  the flat 1024 master; that last mile happens in Apple tooling, not here.
- Android **adaptive** icons (launcher, layered 108dp) need foreground/
  background layers in the app project; this skill ships the Play Store 512
  and the maskable web icon — flag adaptive-icon work as app-project work.
- SVGO is optional and not required for the master (hand-authored subset SVG
  is already lean); if you run it, keep the viewBox and re-render afterwards
  to confirm nothing visually changed.
- Every PNG is written **metadata-free**: renderers inject EXIF/XMP silently
  (macOS `sips` puts an `eXIf` chunk in all of them), so the exporter strips
  `eXIf`/`tEXt`/`iTXt`/`zTXt`/`tIME`/`caBX`/`dSIG` and keeps the colour chunks.
  It reports a `STRIPPED` line. This is file hygiene for assets you own — there
  is no AI-generated raster anywhere in this pipeline to watermark.
- Details and citations for every size: `references/platform-targets.md`.
