#!/usr/bin/env python3
"""squircle.py — emit Apple-style icon background geometry as an SVG path.

Apple's app-icon outline is not a rounded rectangle. It is a *continuous*
corner: curvature ramps in and out instead of jumping from a straight edge to a
circular arc. A plain `rx` rect gets the radius right and the curvature wrong,
which is exactly the "close but subtly off" look next to real icons.

This implements Figma's corner-smoothing construction (the one whose `iOS`
preset is smoothing = 0.6), which is the accepted practical reproduction of the
shape. Apple's true outline is a hand-tuned Bézier, not any closed-form curve —
see references/icon-geometry.md for provenance and the exact citations.

    RADIUS_PCT_IOS26 = 0.2578   # iOS/iPadOS/macOS 26+ ("Liquid Glass") — rounder
    RADIUS_PCT_LEGACY = 0.2237  # iOS 7-18
    SMOOTHING = 0.6             # Figma's iOS preset

Usage:
    python3 squircle.py [--size 1024] [--radius-pct 0.2578] [--smoothing 0.6]
                        [--fill '#2A2A2E'] [--path-only] [--legacy]
    python3 squircle.py --selfcheck
"""

from __future__ import annotations

import argparse
import math
import sys

RADIUS_PCT_IOS26 = 0.2578
RADIUS_PCT_LEGACY = 0.2237
SMOOTHING = 0.6


def corner_params(radius: float, smoothing: float, budget: float) -> dict:
    """The a/b/c/d/p decomposition of one smoothed corner (Figma's figure 11.1).

    `budget` is min(width, height)/2 — the room a corner has to work in. For
    square icons at sane radii it never binds, so we assert rather than carry
    figma-squircle's radius-shrinking fallback.
    """
    p = (1 + smoothing) * radius
    if radius <= 0:
        raise ValueError("radius must be > 0")
    if p > budget or smoothing > budget / radius - 1:
        raise ValueError(
            f"radius {radius:g} + smoothing {smoothing:g} exceed the corner budget "
            f"{budget:g}; use a smaller radius"
        )

    arc_measure = 90 * (1 - smoothing)
    arc_section = math.sin(math.radians(arc_measure / 2)) * radius * math.sqrt(2)
    angle_alpha = (90 - arc_measure) / 2
    p3_to_p4 = radius * math.tan(math.radians(angle_alpha / 2))
    angle_beta = 45 * smoothing
    c = p3_to_p4 * math.cos(math.radians(angle_beta))
    d = c * math.tan(math.radians(angle_beta))
    b = (p - arc_section - c - d) / 3
    a = 2 * b
    return {"a": a, "b": b, "c": c, "d": d, "p": p, "arc": arc_section, "r": radius}


def n(v: float) -> str:
    return f"{round(v, 2):g}"


def squircle_path(
    size: float = 1024.0, radius_pct: float = RADIUS_PCT_IOS26, smoothing: float = SMOOTHING
) -> str:
    """SVG `d` for a square squircle from (0,0) to (size,size)."""
    q = corner_params(size * radius_pct, smoothing, size / 2)
    a, b, c, d, p, arc, r = (q["a"], q["b"], q["c"], q["d"], q["p"], q["arc"], q["r"])
    abc = a + b + c
    return " ".join(
        [
            f"M {n(size - p)} 0",
            f"c {n(a)} 0 {n(a + b)} 0 {n(abc)} {n(d)}",
            f"a {n(r)} {n(r)} 0 0 1 {n(arc)} {n(arc)}",
            f"c {n(d)} {n(c)} {n(d)} {n(b + c)} {n(d)} {n(abc)}",
            f"L {n(size)} {n(size - p)}",
            f"c 0 {n(a)} 0 {n(a + b)} {n(-d)} {n(abc)}",
            f"a {n(r)} {n(r)} 0 0 1 {n(-arc)} {n(arc)}",
            f"c {n(-c)} {n(d)} {n(-(b + c))} {n(d)} {n(-abc)} {n(d)}",
            f"L {n(p)} {n(size)}",
            f"c {n(-a)} 0 {n(-(a + b))} 0 {n(-abc)} {n(-d)}",
            f"a {n(r)} {n(r)} 0 0 1 {n(-arc)} {n(-arc)}",
            f"c {n(-d)} {n(-c)} {n(-d)} {n(-(b + c))} {n(-d)} {n(-abc)}",
            f"L 0 {n(p)}",
            f"c 0 {n(-a)} 0 {n(-(a + b))} {n(d)} {n(-abc)}",
            f"a {n(r)} {n(r)} 0 0 1 {n(arc)} {n(-arc)}",
            f"c {n(c)} {n(-d)} {n(b + c)} {n(-d)} {n(abc)} {n(-d)}",
            "Z",
        ]
    )


def selfcheck() -> int:
    """The corner decomposition must exactly span the canvas edge."""
    for pct in (RADIUS_PCT_IOS26, RADIUS_PCT_LEGACY):
        for size in (1024.0, 512.0, 64.0):
            q = corner_params(size * pct, SMOOTHING, size / 2)
            # walking one corner must consume exactly p in both axes
            span = q["a"] + q["b"] + q["c"] + q["arc"] + q["d"]
            assert abs(span - q["p"]) < 1e-9, (pct, size, span, q["p"])
    d = squircle_path()
    start = 1024 - corner_params(1024 * RADIUS_PCT_IOS26, SMOOTHING, 512)["p"]
    assert d.startswith(f"M {n(start)} 0") and d.endswith("Z"), d[:40]
    assert d.count(" a ") == 4 and d.count(" c ") == 8  # 4 arcs, 8 easing curves
    # a plain rect and the squircle share a radius but not a shape
    legacy = squircle_path(1024, RADIUS_PCT_LEGACY)
    assert legacy != d
    try:
        corner_params(600, 0.6, 512)  # over budget must refuse, not fudge
    except ValueError:
        pass
    else:
        raise AssertionError("over-budget radius was accepted")
    print("selfcheck OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--size", type=float, default=1024.0)
    ap.add_argument("--radius-pct", type=float, default=None)
    ap.add_argument(
        "--legacy",
        action="store_true",
        help=f"use the iOS 7-18 radius ({RADIUS_PCT_LEGACY}) instead of 26+",
    )
    ap.add_argument("--smoothing", type=float, default=SMOOTHING)
    ap.add_argument("--fill", default="#2A2A2E")
    ap.add_argument("--path-only", action="store_true", help="print just the d= value")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    if args.selfcheck:
        return selfcheck()
    pct = (
        args.radius_pct
        if args.radius_pct is not None
        else (RADIUS_PCT_LEGACY if args.legacy else RADIUS_PCT_IOS26)
    )
    d = squircle_path(args.size, pct, args.smoothing)
    if args.path_only:
        print(d)
    else:
        print(f'<path id="bg" d="{d}" fill="{args.fill}"/>')
    return 0


if __name__ == "__main__":
    sys.exit(main())
