# Changelog

All notable changes to this repository's skills are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [SemVer](https://semver.org) on the plugin manifest
(breaking skill-interface change → major, new skill → minor, fix → patch).

## [Unreleased]

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
