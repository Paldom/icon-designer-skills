#!/usr/bin/env python3
"""render_icon.py — rasterize an icon SVG at review sizes, any machine.

Autodetects an SVG renderer (rsvg-convert → resvg → cairosvg → inkscape →
ImageMagick → macOS qlmanage) and renders the given SVG at each requested
size. Validates every output PNG's real dimensions. Pure stdlib; exits
non-zero when no renderer exists or any render fails, printing per-tool
install hints so the agent/user can fix the environment.

Usage:
    python3 render_icon.py ICON.svg [--sizes 512,64,32,16] [--out DIR] [--html]

Output lines:  RENDERED <size> <path>   then  OK: n file(s) in DIR
"""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

DEFAULT_SIZES = "512,64,32,16"

INSTALL_HINTS = [
    ("rsvg-convert", "brew install librsvg          # or: apt install librsvg2-bin"),
    ("resvg", "cargo install resvg           # or: brew install resvg"),
    ("cairosvg", "pip install cairosvg          # needs system cairo"),
    ("inkscape", "brew install --cask inkscape  # or: apt install inkscape"),
    ("magick", "brew install imagemagick      # or: apt install imagemagick"),
    ("qlmanage", "built into macOS (fallback; used automatically)"),
]


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        with open(path, "rb") as fh:
            head = fh.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", head[16:24])
    return (w, h)


def png_luma(path: Path) -> tuple[int, int, list[int]] | None:
    """Decode an 8-bit RGB/RGBA PNG to luminance. Pure stdlib (zlib + unfilter)."""
    try:
        d = path.read_bytes()
    except OSError:
        return None
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    i, idat, w = 8, b"", None
    while i + 12 <= len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        typ = d[i + 4:i + 8]
        if typ == b"IHDR":
            w, h = struct.unpack(">II", d[i + 8:i + 16])
            depth, ctype = d[i + 16], d[i + 17]
            if depth != 8 or ctype not in (2, 6):
                return None
        elif typ == b"IDAT":
            idat += d[i + 8:i + 8 + ln]
        i += 12 + ln
        if typ == b"IEND":
            break
    if w is None or not idat:
        return None
    try:
        raw = zlib.decompress(idat)
    except zlib.error:
        return None
    nch = 4 if ctype == 6 else 3
    stride = w * nch
    out, prev, pos = [], bytearray(stride), 0
    for _ in range(h):
        if pos >= len(raw):
            return None
        f = raw[pos]; pos += 1
        line = bytearray(raw[pos:pos + stride]); pos += stride
        for x in range(stride):
            a = line[x - nch] if x >= nch else 0
            bb = prev[x]
            c = prev[x - nch] if x >= nch else 0
            if f == 1:   line[x] = (line[x] + a) & 0xFF
            elif f == 2: line[x] = (line[x] + bb) & 0xFF
            elif f == 3: line[x] = (line[x] + (a + bb) // 2) & 0xFF
            elif f == 4:
                pp = a + bb - c
                pa, pb, pc = abs(pp - a), abs(pp - bb), abs(pp - c)
                pr = a if (pa <= pb and pa <= pc) else (bb if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        for x in range(0, stride, nch):
            out.append((line[x] * 299 + line[x + 1] * 587 + line[x + 2] * 114) // 1000)
        prev = line
    return w, h, out


def ink_coverage(path: Path) -> float | None:
    """Share of the canvas the glyph actually inks, on a dark house background.

    The strongest single predictor of which mark a human keeps: in this repo's
    22-repo bake-off, the heaviest third of candidates had a zero rejection
    rate and the thinnest third was rejected at twice the base rate. Reported
    so the critique loop can see mass rather than guess at it.
    """
    got = png_luma(path)
    if got is None:
        return None
    w, h, g = got
    return sum(1 for v in g if v > 128) / (w * h)


def run(cmd: list[str]) -> bool:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"  note: {cmd[0]} failed to run: {exc}", file=sys.stderr)
        return False
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip().splitlines()
        print(f"  note: {cmd[0]} exited {proc.returncode}: {msg[-1] if msg else ''}", file=sys.stderr)
        return False
    return True


def render_qlmanage(svg: Path, size: int, out: Path) -> bool:
    """macOS QuickLook fallback: writes <name>.svg.png into a temp dir."""
    with tempfile.TemporaryDirectory() as td:
        if not run(["qlmanage", "-t", "-s", str(size), "-o", td, str(svg)]):
            return False
        produced = Path(td) / (svg.name + ".png")
        if not produced.is_file():
            return False
        shutil.move(str(produced), out)
    return True


def make_renderer(tool: str):
    if tool == "rsvg-convert":
        return lambda svg, size, out: run(
            ["rsvg-convert", "--width", str(size), "--height", str(size),
             "--keep-aspect-ratio", str(svg), "-o", str(out)])
    if tool == "resvg":
        return lambda svg, size, out: run(
            ["resvg", "--width", str(size), "--height", str(size), str(svg), str(out)])
    if tool == "cairosvg":
        return lambda svg, size, out: run(
            ["cairosvg", str(svg), "-o", str(out),
             "--output-width", str(size), "--output-height", str(size)])
    if tool == "cairosvg-module":
        return lambda svg, size, out: run(
            [sys.executable, "-m", "cairosvg", str(svg), "-o", str(out),
             "--output-width", str(size), "--output-height", str(size)])
    if tool == "inkscape":
        return lambda svg, size, out: run(
            ["inkscape", "--export-type=png", f"--export-filename={out}",
             f"--export-width={size}", f"--export-height={size}", str(svg)])
    if tool == "magick":
        return lambda svg, size, out: run(
            ["magick", "-background", "none", str(svg),
             "-resize", f"{size}x{size}", str(out)])
    if tool == "qlmanage":
        return render_qlmanage
    raise ValueError(tool)


def detect() -> tuple[str, object] | None:
    for tool in ("rsvg-convert", "resvg", "cairosvg", "inkscape", "magick", "qlmanage"):
        if shutil.which(tool):
            return tool, make_renderer(tool)
    try:
        import cairosvg  # noqa: F401
        return "cairosvg-module", make_renderer("cairosvg-module")
    except ImportError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("file", type=Path)
    ap.add_argument("--sizes", default=DEFAULT_SIZES,
                    help=f"comma-separated px sizes (default: {DEFAULT_SIZES})")
    ap.add_argument("--out", type=Path, default=None,
                    help="output dir (default: icon-design/renders/<stem>/)")
    ap.add_argument("--html", action="store_true",
                    help="also write preview.html (light/dark strips)")
    args = ap.parse_args()

    if not args.file.is_file():
        print(f"ERROR: no such file: {args.file}", file=sys.stderr)
        return 1
    try:
        sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    except ValueError:
        print(f"ERROR: bad --sizes value: {args.sizes!r}", file=sys.stderr)
        return 1
    if not sizes:
        print("ERROR: --sizes is empty", file=sys.stderr)
        return 1

    found = detect()
    if found is None:
        print("ERROR: no SVG renderer found. Install one of:", file=sys.stderr)
        for tool, hint in INSTALL_HINTS:
            print(f"  {tool:13s} {hint}", file=sys.stderr)
        return 2
    tool, renderer = found
    if tool == "qlmanage":
        print("note: using macOS qlmanage fallback (fine for review; install "
              "librsvg or resvg for pixel-exact export work)", file=sys.stderr)

    out_dir = args.out or Path("icon-design/renders") / args.file.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    rendered: list[tuple[int, Path]] = []
    for size in sizes:
        out = out_dir / f"{args.file.stem}-{size}.png"
        if not renderer(args.file, size, out):
            print(f"ERROR: {tool} failed to render {args.file} at {size}px", file=sys.stderr)
            failures += 1
            continue
        dims = png_size(out)
        if dims is None:
            print(f"ERROR: {out} is not a valid PNG", file=sys.stderr)
            failures += 1
            continue
        if dims != (size, size):
            print(f"ERROR: {out} is {dims[0]}x{dims[1]}, expected {size}x{size}", file=sys.stderr)
            failures += 1
            continue
        rendered.append((size, out))
        cov = ink_coverage(out)
        note = ""
        if cov is not None and size == 64:
            flag = ("  <- thin: the thinnest third of a 66-mark ballot was rejected "
                    "at 2x the base rate" if cov < 0.165 else
                    "  <- heavy: the heaviest third had a zero rejection rate"
                    if cov > 0.21 else "")
            note = f"  ink={cov:.1%}{flag}"
        elif cov is not None:
            note = f"  ink={cov:.1%}"
        print(f"RENDERED {size} {out}{note}")

    if args.html and rendered:
        html = out_dir / "preview.html"
        rows = []
        for bg, label in (("#ffffff", "light"), ("#1e1e22", "dark")):
            imgs = "".join(
                f'<figure><img src="{p.name}" width="{min(s, 256)}" alt="{s}px">'
                f"<figcaption>{s}px</figcaption></figure>"
                for s, p in rendered)
            # pixel-doubled views of the small sizes (nearest-neighbor via CSS)
            imgs += "".join(
                f'<figure><img src="{p.name}" width="{s * 4}" alt="{s}px zoomed" '
                f'style="image-rendering:pixelated">'
                f"<figcaption>{s}px ×4</figcaption></figure>"
                for s, p in rendered if s <= 32)
            rows.append(f'<section style="background:{bg}"><h2>{label}</h2>{imgs}</section>')
        html.write_text(
            "<!doctype html><meta charset='utf-8'><title>icon preview</title>"
            "<style>body{font-family:sans-serif;margin:0}section{padding:16px}"
            "h2{color:#888;font-size:12px;text-transform:uppercase}"
            "figure{display:inline-block;text-align:center;margin:8px}"
            "figcaption{color:#888;font-size:11px}img{image-rendering:auto}</style>"
            + "".join(rows), encoding="utf-8")
        print(f"PREVIEW {html}")

    if failures:
        print(f"FAIL: {failures} of {len(sizes)} renders failed (renderer: {tool})")
        return 1
    print(f"OK: {len(rendered)} file(s) in {out_dir} (renderer: {tool})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
