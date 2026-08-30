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
   this skill): square `viewBox="0 0 1024 1024"` and a background
   `<path id="bg">` that is a real **squircle** — Apple's corner is a
   continuous curve, not a circular arc, so a plain `rx` rect renders subtly
   wrong beside system icons. Never hand-write or hand-edit that path;
   regenerate it:

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/squircle.py"            # iOS 26+ (radius 25.78%, smoothing 0.6)
   python3 "${CLAUDE_SKILL_DIR}/scripts/squircle.py" --legacy   # iOS 7-18 (22.37%)
   ```

   Both radii are community measurements, not Apple-published constants —
   `references/icon-geometry.md` has the provenance. Read it before changing
   the shape.
3. **Draw the object the brief names**, on the 64-unit grid. Coordinates land
   on multiples of 64/32/16 wherever possible; max 2 decimals ever. Use a
   primitive when the shape *is* a primitive (a disc is a `<circle>`, a bar is
   a `<rect>`) and a `<path>` with absolute commands when the subject has a
   silhouette — one well-made path that reads as a drop, an arch or a bird
   beats five primitives arranged into something that only reads as an
   arrangement. Budget: 1 stroke width (2 max, ≥ 48 units), ≤ 3 colors total.
   **There is no shape-count budget** — element count was measured against a
   66-mark ballot and predicted nothing. What predicts survival is *mass*:
   - **Fill, don't outline.** A filled silhouette with knockout details beats
     an outline of the same object. Pure-fill marks were rejected at half the
     rate of marks carrying a stroked element.
   - **Aim for ~20% ink coverage** at 64 px. `render_icon.py` prints `ink=`
     for every render; the heaviest third of that ballot had a *zero*
     rejection rate, the thinnest third was rejected at twice the base rate.
   - **Cut detail out of the mass** rather than adding parts beside it —
     background-coloured knockouts inside a solid body (figure-ground) is the
     construction that won most often.
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
5. **Lint every candidate:**

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/check_svg.py" icon-design/candidates/1-<slug>.svg --axis v
   ```

   (`--axis h` for horizontal symmetry, `--axis none` when the brief declares
   an organic subject.) **Fix every ERROR** — those are the safe-subset and
   output-contract checks, and a candidate that trips one is unusable.
   **Weigh the WARNs** — symmetry, centring, glyph size, stroke weight and
   maskable safe zone are house guidance, not truth. Report each one you leave
   standing and why. Deforming a mark that reads well in order to silence a
   geometry warning is the wrong trade; `--strict` promotes them all to errors
   if you want the old fail-closed behaviour for a batch.
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
- The linter can't judge beauty: passing it means *valid*, not *good*. Worse,
  the correlation can run backwards — in this repo's own bake-off the
  lint-cleanest candidates were ranked last by a human and the two that failed
  the linter placed first and second. Use it to catch what would break, never
  as evidence that a mark is working. Critique is a separate, mandatory step.
- **Symmetry is a default, not a virtue.** It buys stability and cheap
  construction on geometric subjects. On an organic subject it deforms the
  silhouette into something abstract — take `--axis none` from the brief and
  draw the animal.
- If the linter can't run (no `python3`, missing script), **fail closed**:
  label the candidates UNVALIDATED, report the gap, and don't hand them to
  critique/export as if they had passed.
