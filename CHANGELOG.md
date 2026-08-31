# Changelog

All notable changes to this repository's skills are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org) on the plugin manifest
(breaking skill-interface change → major, new skill → minor, fix → patch).

## [Unreleased]

## [0.4.0] - 2026-08-31

### Added
- Adopted the current skillskit gate: executed trigger evals scoring every trigger
  prompt against every skill description (rank-1 routing accuracy 72.5%), a security
  scan over skill content and bundled scripts, ruff lint and format, README-shape
  validation, pre-commit hooks and a write-time lint hook.

### Changed
- Skill descriptions sharpened where the eval gate showed a sibling outranking a
  skill on its own trigger prompts, or a stated non-trigger matching better than any
  trigger. Fixes changed the scope boundary, not just the wording.

### Fixed
- Findings the new lint gate surfaced in this repo's own scripts, fixed at the
  source; where a rule was wrong for a line it is suppressed there with its reason.


## [0.3.0] - 2026-08-31

### Added
- **`icon-export` strips renderer metadata from every asset it writes.** macOS
  `qlmanage`/`sips` silently injects an `eXIf` chunk into every PNG and an Adobe
  XMP `iTXt` packet into some; a full export was shipping ~1.8 KB of EXIF/XMP
  across 20 files. The exporter now drops `eXIf`/`tEXt`/`iTXt`/`zTXt`/`tIME`/
  `caBX`/`dSIG` chunks (pure stdlib, per-chunk CRCs mean no recompression) while
  keeping every colour-critical chunk — `sRGB`, `gAMA`, `cHRM`, `iCCP`, `tRNS`,
  `PLTE` — so nothing renders differently. Favicon sources are stripped before
  ICO assembly, and the shipped `icon.svg` copy loses its authoring comments and
  any `<metadata>` block. `--selfcheck` covers the chunk surgery.
  Note: this is metadata hygiene, not AI-watermark removal — the pipeline draws
  vectors from code and has never produced a watermarked or AI-generated raster.
- `squircle.py`: new generator for the Apple-style background path, with
  `--selfcheck` on the corner decomposition.

### Changed
- **The mass test: weight, not shape count, decides whether a mark survives.**
  A 66-mark ballot across 22 products was measured with a new stdlib PNG
  decoder in `render_icon.py`, which now reports `ink=` (share of canvas the
  glyph covers) for every render. Against the ballot: the heaviest third of
  candidates had a **0% rejection rate**, the thinnest third was rejected at
  **41%** against a 21% base rate. Pure-fill marks were rejected at 16% vs 30%
  for anything with a stroked element; marks with 2+ figure-ground knockouts at
  14% vs 26% with none. `icon-brief` now screens concepts for whether the
  object has a *body* (a compass, a stethoscope, a scaffold and a caliper were
  all rejected despite naming a perfectly good object); `icon-draw` tells you
  to fill rather than outline and to cut detail out of the mass; the
  `icon-critique` rubric gains a scored **Mass** axis reading the `ink=`
  figure.
- **Removed the "≤ 5 major shapes" budget from `icon-draw`.** Measured against
  the same ballot, element count predicted nothing (≤3 elements rejected at
  14%, ≥6 at 8% — noise). It was a constraint that felt disciplined and
  measured quality not at all.
- **The icon background is now a real squircle, not a rounded rect.** Apple's
  corner is a continuous curve; a plain `rx` arc gets the radius right and the
  curvature wrong, which is the "subtly off beside real icons" look. New
  `icon-draw/scripts/squircle.py` generates the path using Figma's
  corner-smoothing construction (the `iOS` preset, smoothing 0.6), and
  `assets/master-template.svg` ships it as `<path id="bg">`.
- **Radius updated to the 26 generation.** iOS/iPadOS/macOS 26+ is visibly
  rounder than iOS 7–18: **25.78%** of the side (≈264 on 1024) versus the old
  **22.37%** (≈229). Both are community measurements of Apple's design
  resources, not published constants, so they live in the generator rather than
  scattered through the skills; `squircle.py --legacy` emits the old shape.
- `check_svg.py` accepts a full-canvas `<path id="bg">` background and warns
  when a plain rounded `<rect>` is used instead; `rx` range widened to cover
  both radii.
- `icon-export`'s square variant now handles either background — the squircle
  path is swapped for a plain full-bleed square rather than having `rx` zeroed.
  Platform-masked targets are unaffected in behaviour, only in mechanism.
- `references/icon-geometry.md` documents Apple's new icon grid (1024 px for
  iPhone/iPad/Mac, 1088 px for Watch; primary grid circle at ~80% of the canvas,
  which is exactly this repo's existing r=409 safe circle) and records that
  Apple's outline is neither a superellipse nor an arc but a tuned Bézier.
- **The linter stops gating on geometry.** Symmetry and axis-centring findings
  drop from ERROR to WARN in `check_svg.py`; ERROR is now reserved for the safe
  subset and the output contract. `icon-draw` fixes errors and *weighs*
  warnings instead of deforming a mark to silence them (`--strict` restores the
  old fail-closed behaviour). Driven by a blind bake-off of five generation
  approaches over three products: the lint-cleanest candidates ranked last and
  two that failed the linter placed first and second.
- **`icon-brief` concepts must name a depictable object** ("a drop", "an arch",
  "a bird's track") rather than an arrangement of primitives ("two chevrons
  over a bar"). In the same ballot this test separated the top-two from the
  bottom-two finishers six for six across three unrelated topics. Adds the
  naming test to `references/design-principles.md`.
- **`icon-brief` checks silhouettes against universal UI glyphs** (download,
  eject, play, share, refresh, pin, chevron stacks) alongside category clichés
  — a failure that renders perfectly at every size and no linter can see.
- **`icon-brief` may declare `axis: none`** for organic subjects, and
  `icon-draw` honours it; `<path>` is now first-class for drawing a silhouette
  rather than a fallback when primitives can't cope.
- **`icon-critique` never auto-promotes.** The headless "promote the top scorer
  if every axis ≥ 3" rule is gone; every candidate reaches the human with its
  scores, and the ranking is stated as advisory. Adds a "reads as its subject"
  axis and demotes distinctiveness from a gate to a note — in the bake-off the
  candidate this rubric rejected as unrecoverable was the maintainer's first
  pick.

### Fixed
- `icon-draw/scripts/check_svg.py`: paths are now walked as a real command
  stream instead of pairing every number in `d`, so relative deltas, arc radii
  and sweep flags stop being read as coordinates (a hand-drawn path icon could
  report a 1054×1088 bbox on a 1024 canvas, and correctly-centred paths were
  failing the off-axis check). Unparseable paths now yield no bbox and skip the
  geometry checks rather than a fabricated one.
- `icon-draw/scripts/check_svg.py`: `<use>` of a `<defs>` group now contributes
  its (mirrored) geometry to the glyph bbox. The skill's own symmetry idiom
  parks half the glyph in `<defs>`, so the size, centring and maskable
  safe-zone checks were blind for exactly the recommended construction.
- `icon-draw/scripts/check_svg.py`: added a loose (±24 unit) warning on the
  off-axis bbox centre — a glyph could sit at the bottom of the canvas and
  still pass, since only the symmetry axis was checked.

- `check_svg.py --selfcheck`: built-in geometry checks for the path walker and
  `<defs>`/`<use>` bbox resolution.
- skills.sh distribution: `npx skills add Paldom/icon-designer-skills` quick
  start, repo-page grouping (`skills.sh.json`), a `skills-sh` CI job mirroring
  the consumer install, `docs/deploying.md`, and the bundled `publish-repo` skill.

## [0.2.0] - 2026-07-04

### Added
- `docs/setup-prompt.md`: paste-ready `/goal` prompt that orchestrates the four
  skills end-to-end against a target repo (ordering, parallel fan-out on
  disjoint files, per-skill verifier gates, re-audit, single final commit).
- `icon-export` skill: fans the approved master SVG out to favicon.ico
  (16/32/48 PNG-embedded, pure stdlib), SVG favicon, apple-touch-icon, PWA
  192/512 + maskable, App Store 1024/Play Store 512 (full-square variants),
  macOS iconset/icns, and the GitHub 1280×640 social preview — with renderer
  autodetection, overwrite guards, and per-file size validation.
- `icon-critique` skill: renders icon candidates at 512/64/32/16 px with a
  renderer-autodetecting script (rsvg-convert → resvg → cairosvg → inkscape →
  ImageMagick → macOS qlmanage) and reviews the actual pixels against a fixed
  rubric, applying targeted fixes capped at 3 iterations.
- `icon-draw` skill: constructs 2-4 candidate icons as master 1024×1024 SVGs
  (symmetric glyph, dark grey Apple-style rounded rectangle) with a
  deterministic linter (`check_svg.py`) enforcing the safe static-SVG subset,
  house geometry, palette/stroke budgets, and symmetry.
- `icon-brief` skill: derives a decision-ready minimalist icon design brief
  (concepts with one Gestalt device each, symmetry axis, house palette,
  distinctiveness-vs-clichés notes) from a text prompt or repo context.

## [0.1.0] - 2026-07-03

### Added
- Repository scaffolded from the skills template.
