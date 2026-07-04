# Icon canvas geometry

Verified facts and house conventions for the master icon SVG. Sources accessed
2026-07. Tags: [primary] Apple/vendor docs, [community] measured/reverse-
engineered consensus, [house] this repo's own convention.

**Contents:** Canvas & background · Apple corner radius facts · Grid & glyph
proportions · Safe zones · Optical centering · Current Apple pipeline notes

## Canvas & background [house]

- Master canvas: `viewBox="0 0 1024 1024"` — matches the largest size every
  platform asks for, divides cleanly into 16/32/64… exports.
- Background: `<rect width="1024" height="1024" rx="229" fill="#2A2A2E"/>`.
  Flat fill, dark grey band `#26262B`–`#2E2E33`, no gradient, no stroke.
- The rounded-rect background ships on **self-rendered surfaces** (favicons,
  PWA non-maskable, GitHub, docs). Platform-masked targets (iOS/App Store,
  apple-touch-icon, Play Store, maskable PWA) receive the **full-square
  variant** (same file with `rx=0`) because those platforms apply their own
  mask — pre-rounding double-masks and leaves transparent corner slivers.

## Apple corner radius facts

- Developers submit **full-square** 1024×1024 icons; iOS applies the mask
  itself (Apple HIG / Icon Composer docs,
  <https://developer.apple.com/documentation/Xcode/creating-your-app-icon-using-icon-composer>). [primary]
- The mask's corner radius ≈ **22.37% of the icon side** (≈229/1024). Apple has
  never published the number; it is community-measured and stable across
  analyses (<https://squircle.js.org/blog/squircles-in-apple-design>,
  <https://liamrosenfeld.com/posts/apple_icon_quest/>). [community]
- The true Apple corner is a **continuous-curvature Bézier** (a reverse-
  engineered `UIBezierPath` rounded rect, ≈ Figma "corner smoothing 60%"), not
  a superellipse and not a plain arc. A plain `rx="229"` rounded rect is the
  accepted approximation for icons rendered outside Apple's own masking — the
  difference is invisible at ≤512 px. [community]
- House ruling: use `rx="229"`. Do not hand-build squircle paths; the payoff is
  sub-pixel and the path is unmaintainable. [house]

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
  icons with six appearance modes (default/dark/clear/tinted variants); a flat
  opaque 1024 PNG remains a valid input and fallback
  (<https://developer.apple.com/icon-composer/>). These are version-sensitive
  facts — treat the flat 1024 master as the durable baseline and Icon Composer
  as an optional last-mile step done in Apple tooling, not in SVG.
