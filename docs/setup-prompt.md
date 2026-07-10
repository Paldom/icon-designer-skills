# Setup prompt: run the whole icon pipeline against a repo

One paste-ready `/goal` that runs brief → draw → critique → export in strict order — the order is load-bearing: draw reads `brief.md`, critique reads the candidates, export reads the approved `icon-design/icon.svg` and stops if it's missing.

## Prerequisites

- In the target repo's Claude Code session: `/plugin marketplace add Paldom/icon-designer-skills` then `/plugin install icon-designer-skills@icon-designer-skills` (or copy the four `skills/*` folders into the target's `.claude/skills/`).
- `python3` (all pipeline scripts are stdlib-only) and an SVG renderer — `rsvg-convert`, `resvg`, `cairosvg`, Inkscape, or ImageMagick; macOS's built-in `qlmanage` is a zero-install fallback.

## The prompt

```text
/goal Design and ship this repository's icon end-to-end with the icon-designer
skills, keeping every artifact under icon-design/ until the final wiring step.

Pipeline (strict order; parallelism only where stated):
1. BRIEF — use the icon-brief skill on this repo's context. Gate:
   icon-design/brief.md exists with 3-5 concepts, each naming exactly one
   Gestalt device, a symmetry axis, a 16px risk, and distinctiveness notes
   against named category clichés; palette is dark grey background + off-white
   glyph + at most one accent.
2. DRAW — use the icon-draw skill: one candidate per brief concept (2-4 total)
   in icon-design/candidates/. Concepts MAY be drawn by parallel subagents
   (disjoint files): pre-assign each agent its candidate number and concept;
   agents touch nothing outside their own candidate file. Gate per candidate:
   icon-draw's scripts/check_svg.py exits 0; every warning fixed or justified
   in one line.
3. CRITIQUE — use the icon-critique skill: lint, then render each candidate
   (512/64/32/16 + preview.html) and score it against the rubric. Candidates
   MAY be critiqued by parallel subagents (disjoint icon-design/renders/<name>/
   dirs); all fixes to a candidate happen in that candidate's agent as -rN
   revision files, max 3 iterations. Gate: render script exit 0 per candidate;
   a ranked score table with per-axis pixel-grounded reasons.
4. APPROVAL — present the score table and preview.html paths, then STOP for my
   pick. Only if I explicitly said this run is unattended: promote the top
   scorer when every axis ≥ 3 and 16px silhouette ≥ 4, and say you did.
   Winner becomes icon-design/icon.svg.
5. EXPORT — use the icon-export skill on icon-design/icon.svg (default
   --targets all). Wire assets into the repo (public/, head tags, manifest)
   only if I asked; overwriting existing files needs my explicit go-ahead
   (--force). Gate: exporter exit 0 and its WROTE table shows every expected
   file/size; relay any alpha-channel warning verbatim.
6. RE-AUDIT — re-run check_svg.py on icon-design/icon.svg, re-read the final
   16px render next to the brief's chosen concept, confirm the export table
   matches references/platform-targets.md, and list residual warnings honestly.
7. HANDOFF — never run git commit or git push: leave icon-design/ and any
   wired assets in the working tree; report the chosen concept, gates passed,
   and the changed-file list for my review.

Definition of Done: brief.md present; ≥2 lint-clean candidates; critique table
+ renders on disk; approved icon-design/icon.svg; export directory validated
with exit 0; nothing committed — change-set reported for my review (with any
red gates called out honestly).
```

## Notes

- The "exit 0" gates are real: `check_svg.py`, `render_icon.py`, and `export_icons.py` all exit non-zero on failure; the exporter refuses to overwrite without `--force` (exit 3) and prints a `WROTE <file> (WxH)` line per validated asset.
- The promote bar (every axis ≥ 3, 16px ≥ 4) matches icon-critique's SKILL.md headless rule.
- Parallel agents never share a file: one candidate file per draw agent, one `renders/<candidate>/` dir per critique agent.
