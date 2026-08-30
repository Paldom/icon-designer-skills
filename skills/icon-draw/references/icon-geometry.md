# Icon canvas geometry

Verified facts and house conventions for the master icon SVG. Sources accessed
2026-07. Tags: [primary] Apple/vendor docs, [community] measured/reverse-
engineered consensus, [house] this repo's own convention.

**Contents:** Canvas & background · Apple corner geometry · Apple's icon grid ·
Grid & glyph proportions · Safe zones · Optical centering · Current Apple
pipeline notes

## Canvas & background [house]

- Master canvas: `viewBox="0 0 1024 1024"` — matches the largest size every
  platform asks for, divides cleanly into 16/32/64… exports.
- Background: a **squircle `<path id="bg">`**, generated — never hand-written —
  by `scripts/squircle.py`. Flat fill, dark grey band `#26262B`–`#2E2E33`, no
  gradient, no stroke. Defaults: radius **25.78%** of the side, corner
  smoothing **0.6**. `--legacy` emits the iOS 7–18 22.37% shape; `--size`
  rescales for non-1024 canvases.
- The rounded-rect background ships on **self-rendered surfaces** (favicons,
  PWA non-maskable, GitHub, docs). Platform-masked targets (iOS/App Store,
  apple-touch-icon, Play Store, maskable PWA) receive the **full-square
  variant** (same file with `rx=0`) because those platforms apply their own
  mask — pre-rounding double-masks and leaves transparent corner slivers.

## Apple corner geometry

- Developers submit **full-square** 1024×1024 icons; the platform applies the
  mask itself, and Icon Composer states plainly that you should not round the
  corners yourself (<https://developer.apple.com/icon-composer/>). [primary]
- The corner is a **continuous curve**, not a circular arc: curvature ramps in
  and out instead of jumping at the tangent point. It is also **not a pure
  superellipse** — Figma's own investigation found a "small but systematic
  discrepancy" for every exponent `n`, and the shape was ultimately
  reverse-engineered as tuned Béziers from `UIBezierPath`
  (<https://www.figma.com/blog/desperately-seeking-squircles/>,
  <https://liamrosenfeld.com/posts/apple_icon_quest/>). [community]
- The practical reproduction everyone converged on is **Figma's corner
  smoothing at 0.6** (Figma's own `iOS` preset) applied to a given corner
  radius (<https://help.figma.com/hc/en-us/articles/360050986854>,
  <https://squircle.js.org/blog/squircles-in-apple-design>). That construction
  is what `scripts/squircle.py` implements. [community]
- **The radius changed in the 26 generation.** Legacy iOS 7–18 measured
  ≈ **22.37%** of the side (≈229 on 1024). iOS/iPadOS/macOS 26+ ("Liquid
  Glass") is visibly rounder: measured at **16.5 on a 64 pt icon = 25.78%**
  (≈264 on 1024) in Apple's updated design resources
  (<https://mastodon.social/@yanlu/114657809111058699>). Apple has never
  published either number — both are measurements, and they are the reason the
  radius lives in one generator script instead of scattered literals.
  [community]
- House ruling (revised): **generate the squircle path.** The previous ruling
  used a plain `rx` rect on the grounds that the difference was sub-pixel; at
  the 26-generation radius it is not — the smoothed corner departs visibly from
  the arc across the whole quarter-turn, which is precisely the "subtly wrong"
  look beside real icons. A script makes the path maintainable, so the argument
  for approximating it is gone. [house]

## Apple's icon grid [primary]

- WWDC25 introduced a new icon grid: **1024 px for iPhone, iPad and Mac; 1088 px
  for Apple Watch** — the Watch canvas is larger to carry the same grid plus
  extra padding for its circular mask (<https://developer.apple.com/icon-composer/>).
- The grid is built from circles, rectangles and diagonals, with the **primary
  circle at ~80% of the canvas width**. Following it is not mandatory, but
  aligned icons sit better among system icons. On the 1024 canvas that circle
  is exactly this repo's **r=409** safe circle — the grid guide and the mask
  safe zone coincide, which is convenient and not a coincidence.
- Icon Composer wants a flat, square, **opaque 1024 PNG with no alpha** and no
  baked corners; it produces the layered `.icon` and all platform variants.

## Grid & glyph proportions [house]

- Work on a **64-unit grid** (1024/16); snap to 32/16 where finer detail is
  unavoidable. Round everything to ≤ 2 decimals — over-precision is invisible
  complexity and a known LLM failure smell.
- Glyph max dimension: **460–655 units (45–64%)** of the canvas. Under ~35%
  reads empty at 512 px; over ~64% crowds the corners and breaks safe zones.
- Stroke widths: one value, ≥ 48 units (48/1024 ≈ 0.75 px at 16 px — the
  practical floor for favicon survival); a second weight only when the concept
  demands hierarchy.

## Safe zones

- **PWA maskable / Android adaptive:** the guaranteed-visible region is a
  centered circle with radius **40% of the icon width** (Android: 66dp safe
  diameter on a 108dp canvas — same 61%…80% band) (web.dev,
  <https://web.dev/articles/maskable-icon>; Android adaptive icon docs). [primary]
- Keep the whole glyph inside the centered **r=409** circle on the 1024 canvas;
  the background may bleed to the edges (that's its job). `check_svg.py` warns
  when the glyph bbox risks the zone. The circle **overrides the 45–64% size
  band**: a square-ish bbox fits the circle only up to ~578 units
  (409·√2), so glyphs whose filled geometry reaches the bbox corners must stay
  below that even though the band allows 655.

## Optical centering [community]

- Geometric centering of asymmetric-weight glyphs (triangles, arrows) looks
  low/off; nudge toward visual balance ≤ 8 units, or better, rebalance the
  shapes. White-on-dark marks read slightly smaller/cramped versus dark-on-
  light — check the render, not the math (Dansky reversal test).

## Current Apple pipeline notes (2026) [primary]

- iOS 26/macOS 26 introduced **Icon Composer** and layered "Liquid Glass"
  icons with six appearance modes (Default, Dark, Clear Light, Clear Dark,
  Tinted Light, Tinted Dark) driven from one layered file; a flat opaque 1024
  PNG remains a valid input and fallback
  (<https://developer.apple.com/icon-composer/>). These are version-sensitive
  facts — treat the flat 1024 master as the durable baseline and Icon Composer
  as an optional last-mile step done in Apple tooling, not in SVG.
