#!/usr/bin/env python3
"""check_svg.py — deterministic lint for house-style icon SVGs.

ERRORs are the hard contract: the safe static-SVG subset (no scripts, external
refs, DOCTYPE, raster, text, CSS), a square 1024 viewBox, the dark rounded-rect
background, and the palette/stroke/precision budgets. A candidate that trips
one is unusable.

WARNs are house guidance: symmetry, bbox centring, glyph size band, stroke
weight, maskable safe zone. These are advisory on purpose — geometry
cleanliness turned out to be a poor predictor of which mark a human picks, so
they must not silently suppress a candidate. Use --strict to promote them.

Pure stdlib; exits non-zero on any error (or warning with --strict).

Usage:
    python3 check_svg.py ICON.svg [--axis v|h|none] [--strict]

Output: one `ERROR:`/`WARN:` line per finding + a final OK/FAIL summary line.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

CANVAS = 1024.0
TOL = 6.0                 # geometric tolerance (units) for symmetry matching
OFF_AXIS_TOL = 24.0       # slack for the axis with no symmetry to pin it
BG_RX_RANGE = (180.0, 290.0)   # 22.37% legacy (229) .. 25.78% iOS 26+ (264), with slack
BG_MAX_LUMINANCE = 0.25   # background must be dark
MASKABLE_SAFE_RADIUS = 0.40 * CANVAS   # PWA maskable safe zone (circle)
GLYPH_MIN = 0.35 * CANVAS  # glyph bbox max-dimension guidance
GLYPH_MAX = 0.66 * CANVAS

ALLOWED_ELEMENTS = {
    "svg", "g", "rect", "circle", "ellipse", "line",
    "polyline", "polygon", "path", "use", "defs", "title", "desc",
}
SHAPE_ELEMENTS = {"rect", "circle", "ellipse", "line", "polyline", "polygon", "path"}
ALLOWED_ATTRS = {
    "id", "viewBox", "width", "height", "x", "y", "rx", "ry",
    "cx", "cy", "r", "x1", "y1", "x2", "y2", "points", "d",
    "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin",
    "stroke-dasharray", "fill-rule", "transform", "href",
}
NUMERIC_ATTRS = {
    "x", "y", "rx", "ry", "cx", "cy", "r", "x1", "y1", "x2", "y2",
    "width", "height", "stroke-width", "points", "d",
}
COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
NUM_RE = re.compile(r"[-+]?(?:\d+\.\d+|\.\d+|\d+\.?)(?:[eE][-+]?\d+)?")
MIRROR_V_RE = re.compile(r"translate\(\s*1024(?:\.0*)?\s*(?:[, ]\s*0(?:\.0*)?\s*)?\)\s*scale\(\s*-1(?:\.0*)?\s*(?:[, ]\s*1(?:\.0*)?\s*)?\)")
MIRROR_H_RE = re.compile(r"translate\(\s*0(?:\.0*)?\s*[, ]\s*1024(?:\.0*)?\s*\)\s*scale\(\s*1(?:\.0*)?\s*[, ]\s*-1(?:\.0*)?\s*\)")

errors: list[str] = []
warnings: list[str] = []


def err(msg: str) -> None:
    errors.append(f"ERROR: {msg}")


def warn(msg: str) -> None:
    warnings.append(f"WARN: {msg}")


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def floats(text: str) -> list[float]:
    return [float(t) for t in NUM_RE.findall(text or "")]


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def check_raw(text: str) -> None:
    lowered = text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        err("DOCTYPE/ENTITY declarations are banned (XXE/billion-laughs surface)")
    for pat, msg in (
        ("<script", "script elements are banned"),
        ("javascript:", "javascript: URLs are banned"),
        ("<foreignobject", "foreignObject is banned"),
        ("<image", "raster <image> elements are banned (icons must be pure vector)"),
        ("<text", "<text>/<textPath> are banned (draw letterforms as paths if needed)"),
        ("<style", "style elements are banned (presentation attributes only)"),
        ("@media", "CSS media queries are banned (librsvg/resvg do not support them)"),
        ("url(", "url(...) references are banned (no gradients/patterns/filters/external loads)"),
        ("data:", "data: URLs are banned"),
        ("http://", "external references are banned (http)"),
        ("https://", "external references are banned (https)"),
    ):
        # xmlns declarations legitimately contain w3.org URLs; strip them first.
        stripped = re.sub(r'xmlns(?::[a-z]+)?="[^"]*"', "", lowered)
        if pat in stripped:
            err(msg)


def parse_transform_kinds(value: str) -> set[str]:
    return set(re.findall(r"([a-zA-Z]+)\s*\(", value or ""))


class Shape:
    """A drawable element reduced to a comparable geometric signature."""

    def __init__(self, elem: ET.Element, transformed: bool):
        self.tag = local(elem.tag)
        self.elem = elem
        self.transformed = transformed
        self.points: list[tuple[float, float]] = []
        self.bbox: tuple[float, float, float, float] | None = None
        self.exact = False
        self._extract()

    def _extract(self) -> None:
        e, get = self.elem, self.elem.get
        try:
            if self.tag == "rect":
                x, y = float(get("x", "0")), float(get("y", "0"))
                w, h = float(get("width", "0")), float(get("height", "0"))
                self.bbox = (x, y, x + w, y + h)
                self.exact = True
            elif self.tag == "circle":
                cx, cy, r = float(get("cx", "0")), float(get("cy", "0")), float(get("r", "0"))
                self.bbox = (cx - r, cy - r, cx + r, cy + r)
                self.exact = True
            elif self.tag == "ellipse":
                cx, cy = float(get("cx", "0")), float(get("cy", "0"))
                rx, ry = float(get("rx", "0")), float(get("ry", "0"))
                self.bbox = (cx - rx, cy - ry, cx + rx, cy + ry)
                self.exact = True
            elif self.tag == "line":
                pts = [(float(get("x1", "0")), float(get("y1", "0"))),
                       (float(get("x2", "0")), float(get("y2", "0")))]
                self.points = pts
                self.bbox = bbox_of(pts)
                self.exact = True
            elif self.tag in ("polyline", "polygon"):
                nums = floats(get("points", ""))
                pts = list(zip(nums[0::2], nums[1::2]))
                self.points = pts
                self.bbox = bbox_of(pts)
                self.exact = True
            elif self.tag == "path":
                self.bbox = path_bbox(get("d", ""))
        except ValueError:
            pass
        if self.transformed:
            self.exact = False

    def signature(self) -> tuple:
        b = self.bbox or (0, 0, 0, 0)
        return (self.tag, round(b[0] / TOL), round(b[1] / TOL),
                round(b[2] / TOL), round(b[3] / TOL))

    def mirrored_signature(self, axis: str) -> tuple:
        b = self.bbox or (0, 0, 0, 0)
        if axis == "v":
            b = (CANVAS - b[2], b[1], CANVAS - b[0], b[3])
        else:
            b = (b[0], CANVAS - b[3], b[2], CANVAS - b[1])
        return (self.tag, round(b[0] / TOL), round(b[1] / TOL),
                round(b[2] / TOL), round(b[3] / TOL))


def bbox_of(pts: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


PATH_TOKEN_RE = re.compile(
    r"([MmZzLlHhVvCcSsQqTtAa])|([-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?)")
PATH_ARGC = {"m": 2, "l": 2, "h": 1, "v": 1, "c": 6, "s": 4, "q": 4, "t": 2, "a": 7, "z": 0}


def path_bbox(d: str) -> tuple[float, float, float, float] | None:
    """Approximate bbox of a path by walking it properly.

    Naively pairing every number in `d` treats relative deltas, arc radii and
    sweep flags as coordinates and yields nonsense. This walks the command
    stream with a current point instead. Bezier control points are included,
    so the box is a superset for curves; arcs contribute only their endpoints,
    so a bulging arc can be under-measured. That accuracy is enough for the
    size/centring *guidance* this linter gives — returns None (callers skip
    the geometry checks) rather than a fabricated box when the path is
    unparseable.
    """
    stream: list = []
    for letter, num in PATH_TOKEN_RE.findall(d or ""):
        stream.append(letter or float(num))
    pts: list[tuple[float, float]] = []
    x = y = sx = sy = 0.0
    cmd: str | None = None
    i = 0
    while i < len(stream):
        tok = stream[i]
        if isinstance(tok, str):
            cmd, i = tok, i + 1
            if cmd in "Zz":
                x, y, cmd = sx, sy, None
                pts.append((x, y))
            continue
        if cmd is None:
            return None                       # numbers before any command
        n = PATH_ARGC[cmd.lower()]
        if i + n > len(stream) or any(isinstance(v, str) for v in stream[i:i + n]):
            return None
        a = stream[i:i + n]
        i += n
        c, rel = cmd.lower(), cmd.islower()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if c == "h":
            x = ox + a[0]
        elif c == "v":
            y = oy + a[0]
        elif c in ("m", "l", "t"):
            x, y = ox + a[0], oy + a[1]
            if c == "m":
                sx, sy = x, y
                cmd = "l" if rel else "L"     # extra pairs after M are implicit lineto
        elif c == "c":
            pts += [(ox + a[0], oy + a[1]), (ox + a[2], oy + a[3])]
            x, y = ox + a[4], oy + a[5]
        elif c in ("s", "q"):
            pts.append((ox + a[0], oy + a[1]))
            x, y = ox + a[2], oy + a[3]
        elif c == "a":
            x, y = ox + a[5], oy + a[6]
        pts.append((x, y))
    return bbox_of(pts) if pts else None


def mirror_box(b: tuple[float, float, float, float], axis: str):
    if axis == "v":
        return (CANVAS - b[2], b[1], CANVAS - b[0], b[3])
    return (b[0], CANVAS - b[3], b[2], CANVAS - b[1])


def defs_group_boxes(root: ET.Element) -> dict[str, list[tuple]]:
    """id -> bboxes of the shapes inside each <defs> group.

    The house symmetry idiom parks half the glyph in <defs> and renders it via
    a mirrored <use>; without this the glyph bbox (and every size, centring and
    safe-zone check built on it) sees only the on-axis half.
    """
    groups: dict[str, list[tuple]] = {}
    for defs in root.iter():
        if local(defs.tag) != "defs":
            continue
        for g in defs.iter():
            gid = g.get("id")
            if not gid:
                continue
            boxes = [s.bbox for s in
                     (Shape(e, False) for e in g.iter() if local(e.tag) in SHAPE_ELEMENTS)
                     if s.bbox]
            if boxes:
                groups[gid] = boxes
    return groups


def merge_bbox(boxes: list[tuple[float, float, float, float]]):
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def selfcheck() -> int:
    """Smallest runnable check on the geometry logic. `check_svg.py --selfcheck`"""
    # absolute + relative + curves + arcs: every number is NOT a coordinate
    assert path_bbox("M100 100 L 300 100 L 300 300 Z") == (100, 100, 300, 300)
    assert path_bbox("M100 100 h 200 v 200 h -200 z") == (100, 100, 300, 300)
    b = path_bbox("M512 268 C 620 400 664 468 664 528 A 152 152 0 0 1 360 528 Z")
    assert b is not None and 300 < b[0] and b[2] < 700 and b[3] < 600, b
    assert path_bbox("M0 0 c 10 0 20 0 30 0") == (0, 0, 30, 0)   # relative cubic
    assert path_bbox("10 20 L 30 40") is None                    # no opening command
    assert path_bbox("M10 20 L 30") is None                      # truncated args

    # a mirrored <use> of a defs half must land in the glyph bbox
    doc = ET.fromstring(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024">'
        '<defs><g id="half"><rect x="224" y="400" width="80" height="224"/></g></defs>'
        '<use href="#half"/>'
        '<use href="#half" transform="translate(1024,0) scale(-1,1)"/></svg>')
    boxes = defs_group_boxes(doc)["half"]
    assert boxes == [(224.0, 400.0, 304.0, 624.0)], boxes
    assert mirror_box(boxes[0], "v") == (720.0, 400.0, 800.0, 624.0)
    print("selfcheck OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path, nargs="?")
    ap.add_argument("--axis", choices=("v", "h", "none"), default="v",
                    help="glyph symmetry axis to verify (default: v)")
    ap.add_argument("--strict", action="store_true", help="warnings become errors")
    ap.add_argument("--selfcheck", action="store_true",
                    help="run the built-in geometry checks and exit")
    args = ap.parse_args()
    if args.selfcheck:
        return selfcheck()
    if args.file is None:
        ap.error("ICON.svg required (or --selfcheck)")

    try:
        text = args.file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"ERROR: cannot read {args.file}: {exc}")
        print("FAIL: 1 error(s)")
        return 1

    check_raw(text)

    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        err(f"not well-formed XML: {exc}")
        report(args)
        return 1

    if local(root.tag) != "svg":
        err(f"root element is <{local(root.tag)}>, expected <svg>")
        report(args)
        return 1

    vb = floats(root.get("viewBox", ""))
    if vb != [0.0, 0.0, CANVAS, CANVAS]:
        err(f'viewBox must be "0 0 1024 1024", found {root.get("viewBox")!r}')

    ids: set[str] = set()
    hrefs: list[str] = []
    paints: set[str] = set()
    stroke_widths: set[float] = set()
    rendered: list[Shape] = []   # document-order drawable shapes (outside defs)
    mirror_use: str | None = None
    uses: list[tuple[str, str]] = []   # (href, transform) for <use> outside defs

    def visit(elem: ET.Element, in_defs: bool, inherited_transform: bool) -> None:
        nonlocal mirror_use
        tag = local(elem.tag)
        if tag not in ALLOWED_ELEMENTS:
            err(f"element <{tag}> is not in the safe subset")
            return
        transformed = inherited_transform
        for raw_name, value in elem.attrib.items():
            name = raw_name
            if raw_name.startswith("{"):
                ns, _, ln = raw_name[1:].partition("}")
                if ns == XLINK_NS and ln == "href":
                    name = "href"
                elif ns == SVG_NS:
                    name = ln
                else:
                    err(f"<{tag}> uses attribute from unexpected namespace: {raw_name}")
                    continue
            if name.startswith("on"):
                err(f"event handler attribute {name!r} is banned")
                continue
            if name in ("class", "style"):
                err(f"{name!r} attribute is banned — use presentation attributes")
                continue
            if name not in ALLOWED_ATTRS:
                warn(f"<{tag}> attribute {name!r} is outside the safe subset")
            if name == "id":
                ids.add(value)
            if name == "href":
                hrefs.append(value)
                if not value.startswith("#"):
                    err(f"href {value!r} — only local #id references are allowed")
            if name == "transform":
                kinds = parse_transform_kinds(value)
                bad = kinds - {"translate", "scale", "rotate"}
                if bad:
                    err(f"transform kind(s) {sorted(bad)} banned (translate/scale/rotate only)")
                transformed = True
            if name in ("fill", "stroke"):
                v = value.strip()
                if v != "none":
                    if COLOR_RE.match(v):
                        paints.add(v.lower())
                    else:
                        err(f"{name}={v!r} — colors must be hex (#rgb/#rrggbb) or 'none'")
            if name == "stroke-width":
                try:
                    stroke_widths.add(float(value))
                except ValueError:
                    err(f"stroke-width {value!r} is not numeric")
            if name in NUMERIC_ATTRS:
                for tok in NUM_RE.findall(value):
                    if "." in tok and len(tok.split(".")[1].rstrip("0")) > 2:
                        err(f"<{tag}> {name} value {tok} has >2 decimals — round coordinates")
                        break
        if tag == "use":
            t = elem.get("transform", "")
            if MIRROR_V_RE.search(t):
                mirror_use = "v"
            elif MIRROR_H_RE.search(t):
                mirror_use = "h"
            if not in_defs:
                href = elem.get("href") or elem.get(f"{{{XLINK_NS}}}href") or ""
                uses.append((href, t))
        if tag in SHAPE_ELEMENTS and not in_defs:
            rendered.append(Shape(elem, transformed))
        for child in elem:
            visit(child, in_defs or tag == "defs", transformed)

    for child in root:
        visit(child, False, False)

    for href in hrefs:
        if href.startswith("#") and href[1:] not in ids:
            err(f"use href {href!r} points to a missing id")

    # --- background ---
    if not rendered:
        err("no drawable shapes found")
        report(args)
        return 1
    bg = rendered[0]
    e = bg.elem
    if bg.tag == "path":
        # House default: the generated squircle from scripts/squircle.py.
        box = bg.bbox
        if box is None:
            err("background <path> has an unparseable d — regenerate with scripts/squircle.py")
        elif (abs(box[0]) > TOL or abs(box[1]) > TOL
              or abs(box[2] - CANVAS) > TOL or abs(box[3] - CANVAS) > TOL):
            err(f"background <path> spans {tuple(round(v) for v in box)} — it must cover "
                "the full 0 0 1024 1024 canvas")
        if e.get("id") != "bg":
            warn('background <path> should carry id="bg" so the exporter can find it')
    elif bg.tag == "rect":
        if float(e.get("x", "0")) != 0 or float(e.get("y", "0")) != 0 or \
           float(e.get("width", "0")) != CANVAS or float(e.get("height", "0")) != CANVAS:
            err("background rect must cover the full canvas (x=0 y=0 width=1024 height=1024)")
        rx = e.get("rx")
        ry = e.get("ry", rx)
        if rx is None:
            err("background rect needs rx (house style: rounded corners)")
        else:
            rxf = float(rx)
            if not (BG_RX_RANGE[0] <= rxf <= BG_RX_RANGE[1]):
                err(f"background rx={rxf} outside house range {BG_RX_RANGE} "
                    "(22.37% legacy ≈229 … 25.78% iOS 26+ ≈264)")
            if ry is not None and float(ry) != rxf:
                err("background ry must equal rx")
            warn("background is a plain rounded rect — a circular-arc corner, not Apple's "
                 "continuous one; prefer the generated squircle path (scripts/squircle.py)")
    else:
        err(f"first rendered element must be the background <path> or <rect>, found <{bg.tag}>")
    fill = (e.get("fill") or "").lower()
    if COLOR_RE.match(fill) and luminance(fill) > BG_MAX_LUMINANCE:
        err(f"background fill {fill} is too light (luminance {luminance(fill):.2f} > {BG_MAX_LUMINANCE}) — house style is dark grey")
    if e.get("stroke") not in (None, "none"):
        warn("background has a stroke — usually unwanted")

    # --- budgets ---
    if len(paints) > 3:
        err(f"{len(paints)} distinct colors used ({sorted(paints)}) — max 3")
    if len(stroke_widths) > 2:
        err(f"{len(stroke_widths)} distinct stroke widths ({sorted(stroke_widths)}) — max 2")
    for w in stroke_widths:
        if w < 40:
            warn(f"stroke-width {w} < 40/1024 units (~0.6px at 16px) — thin strokes vanish at favicon size")

    # --- glyph geometry ---
    glyph = rendered[1:]
    boxes = [s.bbox for s in glyph if s.bbox]
    groups = defs_group_boxes(root)
    for href, tval in uses:
        gboxes = groups.get(href.lstrip("#"))
        if not gboxes:
            continue
        if MIRROR_V_RE.search(tval):
            boxes += [mirror_box(b, "v") for b in gboxes]
        elif MIRROR_H_RE.search(tval):
            boxes += [mirror_box(b, "h") for b in gboxes]
        elif tval.strip():
            warn(f"<use href={href!r}> has an unrecognised transform — its geometry "
                 "is excluded from the glyph bbox; check renders visually")
        else:
            boxes += gboxes
    gb = merge_bbox([b for b in boxes if b])
    if gb:
        gw, gh = gb[2] - gb[0], gb[3] - gb[1]
        cx, cy = (gb[0] + gb[2]) / 2, (gb[1] + gb[3]) / 2
        half_diag = ((max(gw, gh) / 2) ** 2 * 2) ** 0.5
        if max(gw, gh) > GLYPH_MAX:
            warn(f"glyph bbox {gw:.0f}x{gh:.0f} exceeds {GLYPH_MAX:.0f} (64% of canvas) — crowds the background")
        if max(gw, gh) < GLYPH_MIN:
            warn(f"glyph bbox {gw:.0f}x{gh:.0f} under {GLYPH_MIN:.0f} (35% of canvas) — reads empty")
        if half_diag > MASKABLE_SAFE_RADIUS:
            warn(f"glyph may exceed the maskable safe zone (circle r={MASKABLE_SAFE_RADIUS:.0f}); corners could be cropped on the full-square export")
        axis = args.axis
        if axis == "v" and abs(cx - CANVAS / 2) > TOL:
            warn(f"glyph bbox center x={cx:.1f} is off the vertical axis (512±{TOL})")
        if axis == "h" and abs(cy - CANVAS / 2) > TOL:
            warn(f"glyph bbox center y={cy:.1f} is off the horizontal axis (512±{TOL})")
        # The off-axis direction has no symmetry to pin it: a glyph can sit at
        # the bottom of the canvas and still pass. Optical centring legitimately
        # moves it a little, so this is a loose warning, not an error.
        off = cy if axis in ("v", "none") else cx
        if abs(off - CANVAS / 2) > OFF_AXIS_TOL:
            name = "y" if axis in ("v", "none") else "x"
            err_dist = abs(off - CANVAS / 2)
            warn(f"glyph bbox center {name}={off:.0f} sits {err_dist:.0f} units off "
                 f"canvas centre (>{OFF_AXIS_TOL:.0f}) — optical centring should stay small")

    # --- per-element symmetry ---
    axis = args.axis
    if axis != "none" and glyph:
        if mirror_use == axis:
            pass  # symmetric by construction via the mirrored <use> idiom
        elif any(s.transformed or not s.exact for s in glyph):
            warn("transforms or paths present — symmetry verified by bbox only; check renders visually")
        else:
            sigs: dict[tuple, int] = {}
            for s in glyph:
                sigs[s.signature()] = sigs.get(s.signature(), 0) + 1
            for s in glyph:
                m = s.mirrored_signature(axis)
                if sigs.get(m, 0) < 1:
                    warn(f"<{s.tag}> bbox {tuple(round(v, 1) for v in (s.bbox or ()))} has no mirror partner across axis '{axis}'")

    return report(args)


def report(args) -> int:
    for line in errors + warnings:
        print(line)
    n = len(errors) + (len(warnings) if args.strict else 0)
    print(f"{'FAIL' if n else 'OK'}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
