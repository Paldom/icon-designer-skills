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
        print(f"RENDERED {size} {out}")

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
