---
name: icon-draw
description: Draws a minimalist app or OSS package icon as a master 1024x1024 SVG - symmetric glyph on a dark grey rounded-rectangle (Apple-style radius). Use when the user asks to design, create, draw, generate, or make an app icon, package icon, or simple logo mark. Not for icon concept brainstorming, critiquing renders, exporting favicon/assets, UI icon sets, or vectorizing images.
license: MIT
argument-hint: <brief path, concept name, or one-line product description>
---

# icon-draw

Construct candidate icons as clean SVG code: **symmetric glyph on a dark grey
rounded rectangle**, geometry so disciplined that every candidate passes a
deterministic linter before a human ever sees it. LLM one-shot SVG fails in
known ways (bloated paths, fake `<image>` vectors, over-precise coords) — this
skill exists to prevent exactly those failures.

## When NOT to use

- Concept exploration / "what should the icon be" → `icon-brief`.
- Reviewing renders or fixing an existing icon's small-size problems → `icon-critique`.
- Producing favicon/store/asset files → `icon-export`.
- UI icon sets, illustrations, wordmarks, or converting/vectorizing raster logos.

## Workflow

1. **Get the brief.** Read `icon-design/brief.md` if it exists. If not, write a
   5-line quick brief (product, concept + one Gestalt device, symmetry axis,
   palette) to `icon-design/brief.md` marked "quick brief" — so critique/export
   have provenance — and state it to the user; for anything ambitious,
   recommend `icon-brief` instead. Never draw without a stated concept.
2. **Start from the template.** Copy `assets/master-template.svg` (relative to
   this skill) mentally or literally: square `viewBox="0 0 1024 1024"`,
   background `<rect width="1024" height="1024" rx="229" fill="#2A2A2E"/>`.
   rx 229 ≈ 22.37% of the side — the community-measured approximation of
   Apple's icon mask; see `references/icon-geometry.md` before changing it.
3. **Construct the glyph on the 64-unit grid.** Coordinates land on multiples
   of 64/32/16 wherever possible; max 2 decimals ever. Prefer primitives
   (`rect`, `circle`, `line`, `polygon`) over `<path>`; use paths only for
   shapes primitives can't express, with absolute commands. Budget: ≤ 5 major
   shapes, 1 stroke width (2 max, ≥ 48 units), ≤ 3 colors total.
   - **Symmetry by construction** (vertical axis): draw axis-straddling parts
     centered on x=512, put off-axis parts in `<defs><g id="half">…</g></defs>`
     and render with
     `<use href="#half"/><use href="#half" transform="translate(1024,0) scale(-1,1)"/>`.
     For a horizontal axis use `translate(0,1024) scale(1,-1)`.
   - Glyph size: max dimension ~460–655 units (45–64% of canvas), but the
     centered r=409 safe circle **overrides the band**: a square-ish glyph
     bbox must stay ≤ ~578 units unless its filled geometry avoids the bbox
     corners — this is what keeps the full-square export alive under
     PWA/Android masking.
   - Stay inside the safe static subset (`references/svg-subset.md`): no text,
     gradients, filters, CSS, `@media`, scripts, external refs, or raster images.
4. **Draw 2–4 candidates** — one per brief concept (or deliberate variations of
   one concept), each a separate file: `icon-design/candidates/<n>-<slug>.svg`.
   Never overwrite an existing candidate — continue from the next free number.
   Vary silhouette between candidates, not just sizes of the same idea.
5. **Lint every candidate** and fix every error before presenting:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/check_svg.py" icon-design/candidates/1-<slug>.svg --axis v
   ```

   (`--axis h` for horizontal symmetry, `--axis none` only when the brief
   explicitly waives symmetry.) The linter also warns on thin strokes, glyph
   too small/large, and maskable-safe-zone risk — resolve or justify each.
6. **Hand off.** Present the candidates (paths + one-line rationale each) and
   recommend `icon-critique` to render and review them. Do not declare the icon
   final and do not export — approval happens after critique.

## Output spec

- `icon-design/candidates/<n>-<slug>.svg` — 2–4 files, each passing
  `check_svg.py` with 0 errors; warnings resolved or explained.
- Each candidate ≤ ~40 lines of SVG; human-readable ids (`bg`, `glyph`, `half`).
- A short summary: per candidate, concept + Gestalt device + expected 16px risk.

## Gotchas

- **The rounded-rect background is for self-rendered surfaces** (favicons,
  README, GitHub). iOS/App Store submissions need the full-square variant —
  `icon-export` derives it by setting the background `rx` to 0. Never bake a
  second rounding into exports.
- Mirrored `<use>` halves: keep fills fully opaque — semi-transparent overlaps
  double up where halves meet; and don't let the half cross the axis (the
  mirror doubles anything that straddles it).
- `fill="none"` without a `stroke` renders nothing — a classic blank-icon cause.
- Pure geometric centering can look off; optical centering (nudge visually heavy
  side ≤ 8 units) is allowed but keep the bbox center within the linter's ±6
  tolerance — prefer shape rebalancing over nudges.
- Don't imitate existing marks (Docker whale, GitHub cat…): trademark risk —
  flag it and propose a distinct silhouette for the same metaphor.
- Letterform glyphs: `<text>` is banned (font availability breaks renders);
  drawing a letter as paths is allowed but costs legibility at 16px — say so.
- The linter can't judge beauty: passing it means *valid*, not *good*. Critique
  is a separate, mandatory step.
- If the linter can't run (no `python3`, missing script), **fail closed**:
  label the candidates UNVALIDATED, report the gap, and don't hand them to
  critique/export as if they had passed.
