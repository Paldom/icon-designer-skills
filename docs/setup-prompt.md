# Setup prompt: run the whole icon pipeline against a repo

Paste the `/goal` block below into a Claude Code session **inside the target
repository** (the project that needs an icon) with these skills installed —
either as the plugin (`/plugin install icon-designer-skills@icon-designer-skills`)
or by copying the four `skills/*` folders into the target's `.claude/skills/`.

Requirements on the target machine: `python3` (all pipeline scripts are
stdlib-only). An SVG renderer (librsvg's `rsvg-convert`, `resvg`, `cairosvg`,
Inkscape, or ImageMagick) is picked up automatically; on macOS the built-in
`qlmanage` works as a zero-install fallback.

---

```text
/goal Design and ship this repository's icon end-to-end with the icon-designer
skills, keeping every artifact under icon-design/ until the final wiring step.

Pipeline (strict order; parallelism only where stated):
1. BRIEF — use the icon-brief skill on this repo's context.
   Gate: icon-design/brief.md exists with 3-5 concepts, each naming exactly one
   Gestalt device, a symmetry axis, a 16px risk, and distinctiveness notes
   against named category clichés; palette is dark grey background + off-white
   glyph + at most one accent.
2. DRAW — use the icon-draw skill to produce one candidate per brief concept
   (2-4 total) in icon-design/candidates/. Concepts MAY be drawn by parallel
   subagents (disjoint files): pre-assign each agent its candidate number and
   concept before spawning; agents touch nothing outside their own candidate
   file. Gate per candidate: icon-draw's scripts/check_svg.py exits 0; every
   warning is either fixed or justified in one line.
3. CRITIQUE — use the icon-critique skill: lint, then render each candidate
   (512/64/32/16 + preview.html) and score it against the rubric. Candidates
   MAY be critiqued by parallel subagents (disjoint icon-design/renders/<name>/
   dirs), but all fixes to a given candidate happen in that candidate's agent
   as -rN revision files, max 3 iterations. Gate: render script exit 0 per
   candidate; a ranked score table exists with per-axis pixel-grounded reasons.
4. APPROVAL — present the score table and preview.html paths, then STOP for my
   pick. Only if I have explicitly said this run is unattended: promote the top
   scorer yourself when every axis ≥ 3 and 16px silhouette ≥ 4, and say you
   did. Winner becomes icon-design/icon.svg.
5. EXPORT — use the icon-export skill on icon-design/icon.svg (default
   --targets all). Wire assets into the repo (public/, site head tags,
   manifest) only if I asked for wiring; overwriting existing files needs my
   explicit go-ahead (--force). Gate: exporter exit code 0 and its WROTE table
   shows every expected file/size; relay any alpha-channel warning verbatim.
6. RE-AUDIT — after export: re-run check_svg.py on icon-design/icon.svg,
   re-read the final 16px render next to the brief's chosen concept, confirm
   the export table matches references/platform-targets.md expectations, and
   list residual warnings honestly.
7. COMMIT — one commit at the end from the orchestrator only (no per-phase
   commits): icon-design/ plus any wired assets, message describing the chosen
   concept and the gates passed. Do not commit if any gate above is red.

Definition of Done: brief.md present; ≥2 lint-clean candidates; critique table
+ renders on disk; approved icon-design/icon.svg; export directory validated
with exit 0; single commit created (or explicitly skipped because a gate is
red and reported).
```

---

## Fact-check notes (kept in sync with the skills)

- `check_svg.py` and `render_icon.py`/`export_icons.py` exit non-zero on any
  failure — the "exit 0" gates above are real, scriptable checks.
- The exporter **refuses to overwrite** existing outputs without `--force`
  (exit 3) and prints a `WROTE <file> (WxH)` line per validated asset.
- The critique promote bar (every axis ≥ 3, 16 px ≥ 4) is the same bar written
  into `icon-critique`'s SKILL.md for headless runs.
- Ordering is load-bearing: draw reads `brief.md`; critique reads candidates;
  export reads the approved `icon-design/icon.svg` and stops if it's missing.
- Parallel agents never share a file: one candidate file per draw agent, one
  `renders/<candidate>/` dir per critique agent.
