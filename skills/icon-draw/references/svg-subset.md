# Safe static-SVG subset for icons

Why the linter allows what it allows. Two goals: **identical rendering across
rasterizers** and **no active/external content** in generated markup. Sources
accessed 2026-07.

## Allowed

| What | Notes |
| --- | --- |
| Elements | `svg g rect circle ellipse line polyline polygon path use defs title desc` |
| Geometry attrs | `x y rx ry cx cy r x1 y1 x2 y2 points d width height viewBox` |
| Paint attrs | `fill stroke stroke-width stroke-linecap stroke-linejoin stroke-dasharray fill-rule` — colors as `#hex` or `none` only |
| Structure | `id`, local `href="#id"` (for the mirror idiom), `transform` limited to `translate/scale/rotate` |

## Banned, and why

| Banned | Reason |
| --- | --- |
| `<text>`, `<textPath>` | Font availability differs per renderer/machine → non-deterministic output; house style is glyph marks, not wordmarks |
| Gradients, patterns, filters, masks, `url(...)` | House style is flat; filters force slow raster paths and diverge across renderers |
| `<style>`, `class`, `style=""`, CSS | Presentation attributes render identically everywhere; CSS support varies — and `@media` (e.g. `prefers-color-scheme`) is **not supported by librsvg or resvg**, so theme-aware CSS silently renders wrong in exports (librsvg feature docs, <https://gnome.pages.gitlab.gnome.org/librsvg/devel-docs/features.html>; resvg targets the static subset only, <https://github.com/linebender/resvg>). Theme variants are separate files, not media queries |
| `<script>`, `on*` attributes, `<foreignObject>` | Active content in generated markup is an XSS/exec surface |
| `<image>`, `data:`/`http(s):` references, `DOCTYPE`/entities | Raster smuggling (the classic fake-vector failure), external loads at render time, XXE/entity-expansion |
| `matrix()`/`skew()` transforms | Unauditable geometry; symmetry can't be verified |

## Renderer reality (why determinism wins)

- Rasterizers in the wild: `rsvg-convert` (librsvg), `resvg`, CairoSVG,
  Inkscape, ImageMagick, macOS `qlmanage`. Each supports a different SVG
  slice; the subset above renders identically on all of them.
- Browsers *do* support `@media` inside SVG favicons — if a theme-adaptive
  **favicon** is ever wanted, that is an `icon-export` concern layered onto a
  copy, never part of the master.
- `currentColor` is useful for inline-in-HTML logos but resolves to black in
  standalone rasterization; the master uses explicit hex so renders are
  self-contained.
