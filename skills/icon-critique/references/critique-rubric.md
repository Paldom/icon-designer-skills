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
2. **Reads as its subject** — at 512 px, can someone who has not read the brief
   name the thing? ("a drop", "an arch", "a bird"). A mark that can only be
   described as an arrangement of primitives ("two chevrons over a bar") scores
   2 or below here no matter how clean its geometry. This axis correlates with
   human preference better than anything else on the list.
3. **Mass** — does the mark put enough ink on the canvas? `render_icon.py`
   prints `ink=` per size; read the 64 px figure. Under ~16% is thin (the
   thinnest third of a 66-mark ballot was rejected at twice the base rate);
   over ~21% is safe (that third was never rejected). A thin mark is usually
   an outline that wants to be a filled silhouette, or linework that wants to
   be a different object — say which.
4. **16 px silhouette** — is the mark still *this mark* at favicon size? The
   overall shape must be identifiable; interior detail may simplify away
   gracefully but must not turn to mud. Hard gate: score ≥ 4 to ship.
5. **One dominant Gestalt device** — at 512 px, can you name the single device
   (figure-ground / closure / continuity / proximity / similarity-break) in
   one sentence? Two competing devices = muddled; zero = generic.
6. **Stroke & geometry consistency** — one stroke weight (two max), even
   visual weight, no accidental gaps/overshoots at 64 px.
7. **Optical centering & balance** — glyph looks centered in the rounded
   square (geometric centering of pointy/asymmetric-weight glyphs looks off;
   white-on-dark reads smaller than the math suggests).
8. **Distinctiveness (note, not gate)** — does the silhouette differ from the
   category clichés named in the brief, and from the universal UI glyphs
   (download, eject, play, share, refresh, pin, chevron stack)? Record the
   collision and show it to the human. Do **not** drop a candidate on this
   axis: in this repo's bake-off the mark rejected here as "reads as a download
   arrow" was the maintainer's first pick.
9. **Contrast on dark** — glyph tones hold against the dark grey background at
   every size; thin light strokes on dark die first.

## Targeted fixes, in order of preference

1. Add mass before anything else: convert an outline to a filled silhouette,
   or cut the detail out of a solid body instead of drawing it alongside.
2. Delete the detail that dies smallest (a hidden element must read at 16-32px
   or vanish gracefully — never half-read).
2. Thicken strokes (≥ 48/1024 units; step in 8s) / widen counters and gaps.
3. Enlarge the glyph within the 45–64% band; re-check the r=409 safe circle.
4. Rebalance shapes for optical centering (move weight, not just position).
5. Simplify the silhouette (last resort — re-check distinctiveness after:
   simplification pulls toward generic).

One fix per iteration where possible; re-render the whole 512/64/32/16 ladder
after each; **3 iterations max per candidate**, then report residuals.

## Scoring sheet template

| Candidate | Subject | Mass (ink) | 16px | Gestalt | Stroke | Centering | Contrast | Distinct (note) | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1-slug | 5 | 4 (22%) | 4 | 5 | 4 | 4 | 5 | reads near "eject" | one line |

Every candidate goes in the table, low scorers included. The scores are input
to a human decision, not a filter applied before it — there is no automatic
ship bar and no headless promotion.

## Known limits (say them, don't hide them)

- **Self-serving bias**: the drawer grading its own work scores high. Ground
  scores in visible pixels; prefer a fresh session/subagent or the human for
  final judgment. Shipped pipelines that separate generator from critic do so
  deliberately.
- **Good at failure, bad at ranking**: scored against a maintainer's blind
  ballot on 15 candidates, this rubric matched the human on every bottom-ranked
  mark and missed on two of three winners. Treat a low score as a real warning
  and a high score as a weak signal.
- **Geometry cleanliness is not quality**: in the same ballot the candidates
  that passed `check_svg.py` cleanest ranked last, and two that failed it
  placed first and second. A lint-clean mark has earned nothing but validity.
- **Taste is out of scope**: operational axes above are checkable; "beautiful"
  is not. VLM aesthetic judgment against creative-director standards is an
  unsolved problem — never present rubric scores as proof of beauty.
- Renderer differences (qlmanage vs librsvg antialiasing) can shift a
  borderline 16 px call; when in doubt, install librsvg and re-render.
