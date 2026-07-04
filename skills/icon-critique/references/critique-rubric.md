# Icon critique rubric

Fixed rubric for scoring rendered icon candidates. Judge renders, not source.
Score each axis 1–5 with a one-line, pixel-grounded reason. Sources accessed
2026-07; the ladder and axes distill the converged practice of shipped icon
pipelines (brand-logo skill's distinctiveness/scalability/simplicity rubric,
the 64/32/16 strip pattern) and the logo-design corpus ("test at 20px, not
2000px", <https://www.reddit.com/r/logodesign/comments/1rushl7/stop_testing_your_logos_at_2000px_test_them_at/>).

## Gate order (stop at the first hard failure)

1. **Renders at all sizes?** Blank/broken render = automatic fail; check the
   render script's errors, then the SVG.
2. **16 px silhouette** — is the mark still *this mark* at favicon size? The
   overall shape must be identifiable; interior detail may simplify away
   gracefully but must not turn to mud. Hard gate: score ≥ 4 to ship.
3. **One dominant Gestalt device** — at 512 px, can you name the single device
   (figure-ground / closure / continuity / proximity / similarity-break) in
   one sentence? Two competing devices = muddled; zero = generic.
4. **Stroke & geometry consistency** — one stroke weight (two max), even
   visual weight, no accidental gaps/overshoots at 64 px.
5. **Optical centering & balance** — glyph looks centered in the rounded
   square (geometric centering of pointy/asymmetric-weight glyphs looks off;
   white-on-dark reads smaller than the math suggests).
6. **Distinctiveness** — silhouette differs from the category clichés named in
   the brief; a competitor could not wear this mark unchanged.
7. **Contrast on dark** — glyph tones hold against the dark grey background at
   every size; thin light strokes on dark die first.

## Targeted fixes, in order of preference

1. Delete the detail that dies smallest (a hidden element must read at 16-32px
   or vanish gracefully — never half-read).
2. Thicken strokes (≥ 48/1024 units; step in 8s) / widen counters and gaps.
3. Enlarge the glyph within the 45–64% band; re-check the r=409 safe circle.
4. Rebalance shapes for optical centering (move weight, not just position).
5. Simplify the silhouette (last resort — re-check distinctiveness after:
   simplification pulls toward generic).

One fix per iteration where possible; re-render the whole 512/64/32/16 ladder
after each; **3 iterations max per candidate**, then report residuals.

## Scoring sheet template

| Candidate | 16px | Gestalt | Stroke | Centering | Distinct | Contrast | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1-slug | 4 | 5 | 4 | 4 | 3 | 5 | one line |

Ship bar: 16px ≥ 4, every other axis ≥ 3, and a human approval (headless runs:
state that the bar was applied automatically).

## Known limits (say them, don't hide them)

- **Self-serving bias**: the drawer grading its own work scores high. Ground
  scores in visible pixels; prefer a fresh session/subagent or the human for
  final judgment. Shipped pipelines that separate generator from critic do so
  deliberately.
- **Taste is out of scope**: operational axes above are checkable; "beautiful"
  is not. VLM aesthetic judgment against creative-director standards is an
  unsolved problem — never present rubric scores as proof of beauty.
- Renderer differences (qlmanage vs librsvg antialiasing) can shift a
  borderline 16 px call; when in doubt, install librsvg and re-render.
