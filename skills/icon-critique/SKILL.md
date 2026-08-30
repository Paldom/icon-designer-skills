---
name: icon-critique
description: Renders an app/package icon SVG at 512/64/32/16 px and reviews the pixels against a fixed rubric (16px silhouette, Gestalt device, stroke, centering, distinctiveness), with targeted SVG fixes on request. Use when the user asks to review, critique, compare, rate, or fix an icon or whether it reads at small/favicon sizes. Not for designing icons, ideation, exporting assets, or UI icon-set reviews.
license: MIT
argument-hint: <icon.svg path or icon-design/candidates/>
---

# icon-critique

Judge icons by their **renders, never their source code**. An SVG that looks
right as markup routinely dies at 16 px — thin strokes vanish, closure gaps
stop closing, counters fill in. This skill runs the render → critique →
targeted-fix loop that every credible icon pipeline converged on, with a hard
iteration cap.

## When NOT to use

- Creating an icon from scratch → `icon-draw` (after `icon-brief`).
- Producing favicon/asset files or plain SVG→PNG conversion → `icon-export`.
- UI icon-set consistency reviews, page/UX critiques, code review.

## Workflow

1. **Lint before rendering.** Renderers are an attack/crash surface — run the
   safe-subset linter on every input first and refuse to render files that
   fail its security checks (external refs, DOCTYPE, scripts, `<image>`):

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/../icon-draw/scripts/check_svg.py" <file>.svg   # or the skill's installed path
   ```

   If the linter isn't available, say the file is unvetted and get explicit
   user confirmation before rendering. House-geometry errors (off-palette,
   wrong rx) are critique findings, not render blockers — note them.
2. **Render.** For each candidate (a file argument, or every SVG in
   `icon-design/candidates/`):

   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/render_icon.py" <file>.svg --sizes 512,64,32,16 --html
   ```

   The script autodetects a renderer (rsvg-convert → resvg → cairosvg →
   inkscape → ImageMagick → macOS qlmanage) and exits non-zero with install
   hints if none exists — in that case relay the hints and stop; never
   critique unrendered markup.
3. **Read the renders** (the PNG files, with the Read tool) — 512 px for
   craft, the 64/32/16 strip for survival (`preview.html` shows 16 px both
   native and pixel-doubled). Score each candidate against the rubric in
   `references/critique-rubric.md`: **reads as its subject** (can a stranger
   name the thing?), **mass** (the `ink=` figure the renderer prints — under
   ~16% at 64 px is thin, over ~21% is safe), 16 px silhouette, one dominant Gestalt device, stroke
   consistency, optical centering, contrast on dark, plus a distinctiveness
   *note*. Score 1–5 per axis with a one-line reason grounded in what you
   actually see ("the gap between the arcs closes up at 32 px").
   Distinctiveness — including collision with a universal UI glyph — is
   recorded and shown to the human, never used to drop a candidate: that call
   belongs to whoever owns the product.
4. **Fix with targeted edits — only when asked.** Pure review requests
   ("rate", "critique", "compare") end at the verdict; edit only when the
   user asked to fix/improve or approves your proposed fixes. Edits are
   **non-destructive**: write revisions as `<n>-<slug>-r1.svg`, `-r2.svg`…
   next to the original, patching the specific failing element — thicken a
   stroke, widen a counter, drop the detail that dies smallest — never
   regenerate wholesale. Stay inside `icon-draw`'s constraints (its
   `check_svg.py` must pass on every revision). Typical fixes ranked in the
   rubric reference.
5. **Re-render and re-score** each revision. **Hard cap: 3 fix iterations per
   candidate.** If it still fails an axis at the cap, report the residual
   honestly — do not loop, do not lower the bar.
6. **Verdict + human gate.** Present **every** candidate — including the ones
   you scored badly — in a ranked table (candidate, axis scores, one-line
   verdicts), point at `icon-design/renders/*/preview.html`, and **ask the
   human to pick**. Say plainly that the ranking is advisory. On approval,
   copy the winner to `icon-design/icon.svg` — the handoff `icon-export`
   expects — but never replace an existing `icon-design/icon.svg` without
   explicit confirmation. **Never auto-promote**, headless included: report
   the scores, name the top scorer, and stop without writing
   `icon-design/icon.svg`. A run with no human in it produces a
   recommendation, not an approval.

## Output spec

- `icon-design/renders/<candidate>/` — PNGs at 512/64/32/16 + `preview.html`.
- A scored comparison table + recommendation with per-axis reasons.
- On approval: the winner at `icon-design/icon.svg`, passing `check_svg.py`,
  plus its final render set.

## Gotchas

- **Self-review bias is real**: you are grading your own drawing. Ground every
  score in a visible pixel fact, not the intention behind the code. When
  another reviewer is available (subagent, second model, or the human), prefer
  it for the final pass.
- **This rubric is a failure detector, not a ranker.** In this repo's own
  bake-off it agreed with the human on every bottom-ranked mark and disagreed
  on two of three winners — the candidate it declared unrecoverable was the
  human's first pick. Trust it when it says something is broken; do not trust
  it to tell you which working mark is best, and never let it be the thing
  that removes an option from the table.
- Automated taste doesn't exist: VLM judgment of *operational* qualities
  (legibility, contrast, balance) is workable; open-ended "is it beautiful" is
  not — leave taste to the human, and say so when asked to "make it prettier".
- Distinctiveness needs comparators: name the 2-3 category-cliché marks (from
  the brief) and check the silhouette against them; "clean" is not "distinct".
- qlmanage (macOS fallback) antialiases slightly differently than librsvg —
  fine for review; recommend installing librsvg/resvg before pixel-exact work.
- A fix that passes 16 px but breaks the Gestalt device at 512 px is a
  regression — always re-read the whole ladder after an edit.
