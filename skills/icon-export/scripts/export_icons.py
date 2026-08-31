#!/usr/bin/env python3
"""export_icons.py — turn an approved master icon SVG into platform assets.

Input: the 1024x1024 master SVG (rounded-rect background, per icon-draw).
Outputs, grouped by --targets (default: all):

  web     favicon.ico (16+32+48), icon.svg, apple-touch-icon.png (180, square),
          icon-192.png, icon-512.png (rounded), icon-mask-512.png (square,
          maskable), snippet.html, manifest.webmanifest
  apple   appstore-1024.png (square, for App Store/Icon Composer),
          icon.iconset/ (10 PNGs, iconutil naming) [+ icon.icns on macOS]
  android play-store-512.png (square, opaque)
  github  social-preview-1280x640.png, avatar-512.png (rounded)

Platform-masked targets (App Store, Play, apple-touch-icon, maskable) are
rendered from a derived FULL-SQUARE variant — the master's rounded background
is replaced by a plain full-bleed square — so the platform's own mask is the
only rounding. Self-rendered surfaces keep the master's squircle.

Pure stdlib. Autodetects a renderer (rsvg-convert → resvg → cairosvg →
inkscape → ImageMagick → macOS qlmanage). Refuses to overwrite existing files
without --force. Validates every PNG's dimensions and the ICO structure.
Exits non-zero on any failure.

Usage:
    python3 export_icons.py MASTER.svg [--out DIR] [--targets web,apple,android,github]
                            [--name icon] [--force]
"""

from __future__ import annotations

import argparse
import copy
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ALL_TARGETS = ("web", "apple", "android", "github")
ICO_SIZES = (16, 32, 48)
ICONSET = [  # (filename, pixel size) — iconutil naming convention
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
]
INSTALL_HINTS = [
    ("rsvg-convert", "brew install librsvg          # or: apt install librsvg2-bin"),
    ("resvg", "cargo install resvg           # or: brew install resvg"),
    ("cairosvg", "pip install cairosvg          # needs system cairo"),
    ("inkscape", "brew install --cask inkscape  # or: apt install inkscape"),
    ("magick", "brew install imagemagick      # or: apt install imagemagick"),
    ("qlmanage", "built into macOS (fallback; used automatically)"),
]

SNIPPET_HTML = """<!-- head tags for the exported icon set -->
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/icon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<link rel="manifest" href="/manifest.webmanifest">
"""

MANIFEST = """{
  "icons": [
    { "src": "/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/icon-mask-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
"""


def fail(msg: str, code: int = 1) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return code


def run(cmd: list[str]) -> bool:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"  note: {cmd[0]}: {exc}", file=sys.stderr)
        return False
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()
        print(
            f"  note: {cmd[0]} exited {proc.returncode}: {tail[-1] if tail else ''}",
            file=sys.stderr,
        )
        return False
    return True


def render_qlmanage(svg: Path, w: int, h: int, out: Path) -> bool:
    """qlmanage only makes square thumbnails and zoom-fills non-square SVGs.
    For w != h, letterbox the SVG into a square (content centered), render the
    square, then center-crop with sips (also built into macOS)."""
    with tempfile.TemporaryDirectory() as td:
        src = svg
        if w != h:
            side = max(w, h)
            try:
                ET.register_namespace("", SVG_NS)
                inner = ET.parse(svg).getroot()  # noqa: S314 - parses a local file the caller supplies; defusedxml would add a runtime dependency a skill must not have
            except (ET.ParseError, OSError):
                return False
            box = ET.Element(
                f"{{{SVG_NS}}}svg",
                {"viewBox": f"0 0 {side} {side}", "width": str(side), "height": str(side)},
            )
            g = ET.SubElement(
                box,
                f"{{{SVG_NS}}}g",
                {"transform": f"translate({(side - w) / 2:g},{(side - h) / 2:g})"},
            )
            for child in inner:
                g.append(copy.deepcopy(child))
            src = Path(td) / "boxed.svg"
            ET.ElementTree(box).write(src, encoding="utf-8", xml_declaration=False)
        if not run(["qlmanage", "-t", "-s", str(max(w, h)), "-o", td, str(src)]):
            return False
        produced = Path(td) / (src.name + ".png")
        if not produced.is_file():
            return False
        if w != h and not run(
            ["sips", "-c", str(h), str(w), str(produced), "--out", str(produced)]
        ):
            return False
        shutil.move(str(produced), out)
    return True


def make_renderer(tool: str):
    if tool == "rsvg-convert":
        return lambda svg, w, h, out: run(
            [
                "rsvg-convert",
                "--width",
                str(w),
                "--height",
                str(h),
                "--keep-aspect-ratio",
                str(svg),
                "-o",
                str(out),
            ]
        )
    if tool == "resvg":
        return lambda svg, w, h, out: run(
            ["resvg", "--width", str(w), "--height", str(h), str(svg), str(out)]
        )
    if tool in ("cairosvg", "cairosvg-module"):
        base = ["cairosvg"] if tool == "cairosvg" else [sys.executable, "-m", "cairosvg"]
        return lambda svg, w, h, out: run(
            [*base, str(svg), "-o", str(out), "--output-width", str(w), "--output-height", str(h)]
        )
    if tool == "inkscape":
        return lambda svg, w, h, out: run(
            [
                "inkscape",
                "--export-type=png",
                f"--export-filename={out}",
                f"--export-width={w}",
                f"--export-height={h}",
                str(svg),
            ]
        )
    if tool == "magick":
        return lambda svg, w, h, out: run(
            ["magick", "-background", "none", str(svg), "-resize", f"{w}x{h}", str(out)]
        )
    if tool == "qlmanage":
        return render_qlmanage
    raise ValueError(tool)


def stripping(render):
    """Wrap a renderer so no PNG leaves this exporter carrying metadata."""

    def wrapped(svg, w, h, out):
        ok = render(svg, w, h, out)
        if ok:
            strip_png_metadata(Path(out))
        return ok

    return wrapped


def detect():
    for tool in ("rsvg-convert", "resvg", "cairosvg", "inkscape", "magick", "qlmanage"):
        if shutil.which(tool):
            return tool, stripping(make_renderer(tool))
    try:
        import cairosvg  # noqa: F401

        return "cairosvg-module", stripping(make_renderer("cairosvg-module"))
    except ImportError:
        return None


PNG_SIG = b"\x89PNG\r\n\x1a\n"
# Ancillary PNG chunks that carry provenance/authoring metadata rather than
# pixels. Renderers inject these silently — macOS qlmanage/sips writes an eXIf
# chunk into every PNG and an Adobe XMP iTXt packet into some. caBX is where a
# C2PA manifest would live if raster tooling ever entered the pipeline.
# Colour-critical chunks (sRGB/gAMA/cHRM/iCCP/tRNS/PLTE/bKGD/sBIT) are kept:
# dropping those changes how the image renders.
PNG_META_CHUNKS = {b"eXIf", b"tEXt", b"iTXt", b"zTXt", b"tIME", b"caBX", b"dSIG"}
STRIPPED = [0, 0]  # files touched, bytes removed — reported at the end


def strip_png_metadata(path: Path) -> int:
    """Remove metadata chunks from a PNG in place; return bytes removed.

    PNG CRCs are per-chunk, so whole chunks can be dropped without recomputing
    anything. Any malformed/truncated file is left untouched.
    """
    try:
        d = path.read_bytes()
    except OSError:
        return 0
    if not d.startswith(PNG_SIG):
        return 0
    out = bytearray(d[:8])
    i, removed = 8, 0
    while i + 12 <= len(d):
        ln = struct.unpack(">I", d[i : i + 4])[0]
        typ = d[i + 4 : i + 8]
        end = i + 12 + ln
        if end > len(d):
            return 0  # truncated — do not rewrite
        if typ in PNG_META_CHUNKS:
            removed += end - i
        else:
            out += d[i:end]
        i = end
        if typ == b"IEND":
            break
    if not removed:
        return 0
    path.write_bytes(bytes(out))
    STRIPPED[0] += 1
    STRIPPED[1] += removed
    return removed


def clean_svg_copy(src: Path, dest: Path) -> None:
    """Ship the master without authoring comments or <metadata> blocks."""
    text = src.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"<metadata\b[^>]*>.*?</metadata>", "", text, flags=re.S)
    text = re.sub(r"[ \t]+$", "", text, flags=re.M)
    text = re.sub(r"\n{2,}", "\n", text)
    dest.write_text(text.strip() + "\n", encoding="utf-8")


def png_size(path: Path) -> tuple[int, int] | None:
    try:
        head = path.read_bytes()[:24]
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def png_has_alpha_channel(path: Path) -> bool:
    """IHDR color type 4 (grey+alpha) or 6 (RGBA)."""
    try:
        head = path.read_bytes()[:26]
    except OSError:
        return False
    return len(head) >= 26 and head[25] in (4, 6)


def flatten_appstore_png(path: Path, bg_fill: str) -> None:
    """App Store artwork must carry no alpha channel. Flatten in place when
    ImageMagick is available; otherwise warn loudly with the exact command."""
    if not png_has_alpha_channel(path):
        return
    if (
        shutil.which("magick")
        and run(
            [
                "magick",
                str(path),
                "-background",
                bg_fill,
                "-alpha",
                "remove",
                "-alpha",
                "off",
                str(path),
            ]
        )
        and not png_has_alpha_channel(path)
    ):
        strip_png_metadata(path)
        print(
            f"note: flattened alpha channel on {path.name} (App Store requires no alpha)",
            file=sys.stderr,
        )
        return
    print(
        f"WARN: {path} has an alpha channel; App Store uploads may reject it. "
        f'Flatten with: magick {path.name} -background "{bg_fill}" '
        f"-alpha remove -alpha off {path.name}",
        file=sys.stderr,
    )


def write_ico(pngs: list[tuple[int, bytes]], out: Path) -> None:
    """ICO container with PNG-compressed entries (supported since Vista)."""
    header = struct.pack("<HHH", 0, 1, len(pngs))
    entries, blobs = b"", b""
    offset = 6 + 16 * len(pngs)
    for size, data in pngs:
        entries += struct.pack(
            "<BBBBHHII",
            0 if size >= 256 else size,
            0 if size >= 256 else size,
            0,
            0,
            1,
            32,
            len(data),
            offset,
        )
        blobs += data
        offset += len(data)
    out.write_bytes(header + entries + blobs)


def check_ico(path: Path, expected: int) -> bool:
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if len(data) < 6 or struct.unpack("<HHH", data[:6]) != (0, 1, expected):
        return False
    for i in range(expected):
        length, off = struct.unpack("<II", data[6 + 16 * i + 8 : 6 + 16 * i + 16])
        if data[off : off + 8] != b"\x89PNG\r\n\x1a\n" or off + length > len(data):
            return False
    return True


UNSAFE_PATTERNS = (
    "<!doctype",
    "<!entity",
    "<script",
    "javascript:",
    "<foreignobject",
    "<image",
    "url(",
    "data:",
    "http://",
    "https://",
)


def load_master(path: Path):
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, f"cannot read master SVG: {exc}"
    # Security preflight: only house-subset masters are rendered. Renderers are
    # an attack surface; refuse active/external content outright.
    lowered = re.sub(r'xmlns(?::[a-z]+)?="[^"]*"', "", text.lower())
    for pat in UNSAFE_PATTERNS:
        if pat in lowered:
            return None, (
                f"master contains banned content ({pat!r}) — this exporter "
                "only accepts icon-draw house-subset SVGs; run check_svg.py"
            )
    ET.register_namespace("", SVG_NS)
    try:
        tree = ET.ElementTree(ET.fromstring(text))  # noqa: S314 - parses a local file the caller supplies; defusedxml would add a runtime dependency a skill must not have
    except ET.ParseError as exc:
        return None, f"cannot parse master SVG: {exc}"
    root = tree.getroot()
    if (root.get("viewBox") or "").split() != ["0", "0", "1024", "1024"]:
        return (
            None,
            f'master viewBox must be "0 0 1024 1024" (found {root.get("viewBox")!r}) — run icon-draw/check_svg.py first',
        )
    return tree, None


def square_variant(tree: ET.ElementTree, dest: Path) -> str | None:
    """Copy of the master with the rounded background replaced by a full square.

    Platform-masked targets (App Store, apple-touch-icon, Play, maskable PWA,
    Icon Composer) apply their own corner mask; feeding them pre-rounded art
    double-masks it. The master's background is either the generated squircle
    <path id="bg"> or a legacy rounded <rect> — both become a plain square here.
    """
    t = copy.deepcopy(tree)
    root = t.getroot()
    bg = None
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if tag == "path" and el.get("id") == "bg":
            bg = el
            break
        if tag == "rect" and el.get("width") == "1024":
            bg = el
            break
    if bg is None:
        return (
            'master has no background <path id="bg"> or full-canvas <rect> '
            "— not an icon-draw master"
        )
    if bg.tag.rsplit("}", 1)[-1] == "path":
        fill = bg.get("fill", "#2A2A2E")
        bg.tag = f"{{{SVG_NS}}}rect"
        bg.attrib.clear()
        bg.set("id", "bg")
        bg.set("width", "1024")
        bg.set("height", "1024")
        bg.set("fill", fill)
    else:
        bg.set("rx", "0")
        bg.set("ry", "0")
    root.set("width", "1024")
    root.set("height", "1024")
    t.write(dest, encoding="utf-8", xml_declaration=False)
    return None


def social_variant(tree: ET.ElementTree, dest: Path) -> str | None:
    """1280x640 banner: dark field + the icon (512px) centered."""
    root = tree.getroot()
    bg = root.find(f"{{{SVG_NS}}}rect")
    fill = (bg.get("fill") if bg is not None else None) or "#2A2A2E"
    banner = ET.Element(
        f"{{{SVG_NS}}}svg", {"viewBox": "0 0 1280 640", "width": "1280", "height": "640"}
    )
    ET.SubElement(banner, f"{{{SVG_NS}}}rect", {"width": "1280", "height": "640", "fill": fill})
    g = ET.SubElement(banner, f"{{{SVG_NS}}}g", {"transform": "translate(384,64) scale(0.5)"})
    for child in root:
        g.append(copy.deepcopy(child))
    ET.ElementTree(banner).write(dest, encoding="utf-8", xml_declaration=False)
    return None


def selfcheck() -> int:
    """PNG chunk surgery must drop metadata and keep everything that renders."""
    import zlib

    def chunk(typ: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + typ
            + payload
            + struct.pack(">I", zlib.crc32(typ + payload) & 0xFFFFFFFF)
        )

    png = (
        PNG_SIG
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
        + chunk(b"sRGB", b"\x00")
        + chunk(b"gAMA", struct.pack(">I", 45455))
        + chunk(b"eXIf", b"MM\x00*deadbeef")
        + chunk(b"tEXt", b"Software\x00qlmanage")
        + chunk(b"iTXt", b"XML:com.adobe.xmp\x00\x00\x00\x00\x00<x:xmpmeta/>")
        + chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff\xff"))
        + chunk(b"IEND", b"")
    )
    with tempfile.TemporaryDirectory() as td:
        f = Path(td) / "t.png"
        f.write_bytes(png)
        before = STRIPPED[1]
        removed = strip_png_metadata(f)
        got = f.read_bytes()
        assert removed > 0 and STRIPPED[1] == before + removed
        for gone in (b"eXIf", b"tEXt", b"iTXt", b"adobe.xmp", b"qlmanage"):
            assert gone not in got, gone
        for kept in (PNG_SIG, b"IHDR", b"sRGB", b"gAMA", b"IDAT", b"IEND"):
            assert kept in got, kept
        assert png_size(f) == (1, 1)  # pixels untouched
        assert strip_png_metadata(f) == 0  # idempotent
        f.write_bytes(png[:20])  # truncated
        assert strip_png_metadata(f) == 0 and f.read_bytes() == png[:20]

        svg = Path(td) / "m.svg"
        svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg">\n  <!-- note -->\n'
            '  <metadata><rdf/></metadata>\n  <rect width="1"/>\n</svg>\n'
        )
        dest = Path(td) / "out.svg"
        clean_svg_copy(svg, dest)
        t = dest.read_text()
        assert "<!--" not in t and "metadata" not in t and "<rect" in t, t
    print("selfcheck OK")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "master", type=Path, nargs="?", help="approved master SVG (icon-design/icon.svg)"
    )
    ap.add_argument("--out", type=Path, default=Path("icon-design/export"))
    ap.add_argument(
        "--targets", default="all", help="comma list of web,apple,android,github (default: all)"
    )
    ap.add_argument("--name", default="icon", help="basename for icon.svg/iconset")
    ap.add_argument(
        "--selfcheck", action="store_true", help="run the built-in metadata-strip checks and exit"
    )
    ap.add_argument("--force", action="store_true", help="allow overwriting existing files")
    args = ap.parse_args()

    if args.selfcheck:
        return selfcheck()
    if args.master is None:
        return fail("MASTER.svg is required (or pass --selfcheck)", 2)
    if not args.master.is_file():
        return fail(f"no such file: {args.master} — approve a master via icon-critique first")
    targets = (
        ALL_TARGETS
        if args.targets == "all"
        else tuple(t.strip() for t in args.targets.split(",") if t.strip())
    )
    bad = [t for t in targets if t not in ALL_TARGETS]
    if bad:
        return fail(f"unknown target(s) {bad}; valid: {ALL_TARGETS}")

    tree, err = load_master(args.master)
    if err:
        return fail(err)

    found = detect()
    if found is None:
        print("ERROR: no SVG renderer found. Install one of:", file=sys.stderr)
        for tool, hint in INSTALL_HINTS:
            print(f"  {tool:13s} {hint}", file=sys.stderr)
        return 2
    tool, render = found

    out = args.out
    # Build the render plan: (relpath, source_kind, w, h)
    plan: list[tuple[str, str, int, int]] = []
    if "web" in targets:
        plan += [
            ("apple-touch-icon.png", "square", 180, 180),
            ("icon-192.png", "rounded", 192, 192),
            ("icon-512.png", "rounded", 512, 512),
            ("icon-mask-512.png", "square", 512, 512),
        ]
    if "apple" in targets:
        plan += [("appstore-1024.png", "square", 1024, 1024)]
        plan += [(f"{args.name}.iconset/{fn}", "rounded", s, s) for fn, s in ICONSET]
    if "android" in targets:
        plan += [("play-store-512.png", "square", 512, 512)]
    if "github" in targets:
        # avatar from the square variant: GitHub masks avatars itself
        plan += [
            ("social-preview-1280x640.png", "social", 1280, 640),
            ("avatar-512.png", "square", 512, 512),
        ]

    text_outputs = []
    if "web" in targets:
        text_outputs = [
            ("favicon.ico", None),
            (f"{args.name}.svg", None),
            ("snippet.html", SNIPPET_HTML),
            ("manifest.webmanifest", MANIFEST),
        ]

    # Overwrite guard: check every planned path up front.
    planned = [out / rel for rel, *_ in plan] + [out / rel for rel, _ in text_outputs]
    existing = [p for p in planned if p.exists()]
    if existing and not args.force:
        print(
            "ERROR: refusing to overwrite existing files (pass --force to allow):", file=sys.stderr
        )
        for p in existing:
            print(f"  {p}", file=sys.stderr)
        return 3

    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        sources = {"rounded": args.master}
        sq = Path(td) / "square.svg"
        err = square_variant(tree, sq)
        if err:
            return fail(err)
        sources["square"] = sq
        if "github" in targets:
            so = Path(td) / "social.svg"
            err = social_variant(tree, so)
            if err:
                return fail(err)
            sources["social"] = so

        failures = 0
        written: list[tuple[Path, tuple[int, int]]] = []
        for rel, kind, w, h in plan:
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not render(sources[kind], w, h, dest):
                print(f"ERROR: render failed: {rel}", file=sys.stderr)
                failures += 1
                continue
            dims = png_size(dest)
            if dims != (w, h):
                print(f"ERROR: {rel} is {dims}, expected {(w, h)}", file=sys.stderr)
                failures += 1
                continue
            written.append((dest, dims))
            print(f"WROTE {dest} ({w}x{h})")
            if rel in ("appstore-1024.png", "play-store-512.png"):
                bg = tree.getroot().find(f"{{{SVG_NS}}}rect")
                flatten_appstore_png(
                    dest, (bg.get("fill") if bg is not None else None) or "#2A2A2E"
                )

        if "web" in targets and not failures:
            ico_parts = []
            for s in ICO_SIZES:
                p = Path(td) / f"fav-{s}.png"
                if not render(sources["rounded"], s, s, p) or png_size(p) != (s, s):
                    print(f"ERROR: favicon source render failed at {s}px", file=sys.stderr)
                    failures += 1
                    break
                ico_parts.append((s, p.read_bytes()))
            if len(ico_parts) == len(ICO_SIZES):
                ico = out / "favicon.ico"
                write_ico(ico_parts, ico)
                if not check_ico(ico, len(ICO_SIZES)):
                    print("ERROR: favicon.ico failed structural validation", file=sys.stderr)
                    failures += 1
                else:
                    print(f"WROTE {ico} (sizes {'/'.join(map(str, ICO_SIZES))})")
            clean_svg_copy(args.master, out / f"{args.name}.svg")
            print(f"WROTE {out / (args.name + '.svg')} (master copy, comments stripped)")
            for rel, content in (
                ("snippet.html", SNIPPET_HTML),
                ("manifest.webmanifest", MANIFEST),
            ):
                (out / rel).write_text(content, encoding="utf-8")
                print(f"WROTE {out / rel}")

    if "apple" in targets and not failures:
        iconset = out / f"{args.name}.iconset"
        if sys.platform == "darwin" and shutil.which("iconutil"):
            icns = out / f"{args.name}.icns"
            if run(["iconutil", "-c", "icns", str(iconset), "-o", str(icns)]) and icns.is_file():
                print(f"WROTE {icns}")
            else:
                print(
                    "WARN: iconutil failed — .iconset left for manual conversion", file=sys.stderr
                )
        else:
            print(
                f"note: not macOS or no iconutil — convert {iconset} with "
                f"`iconutil -c icns {iconset.name}` on a Mac",
                file=sys.stderr,
            )

    if failures:
        print(f"FAIL: {failures} asset(s) failed (renderer: {tool})")
        return 1
    if STRIPPED[0]:
        print(
            f"STRIPPED metadata from {STRIPPED[0]} PNG(s) ({STRIPPED[1]} bytes: "
            f"{'/'.join(c.decode() for c in sorted(PNG_META_CHUNKS))} chunks)"
        )
    print(f"OK: export complete in {out} (renderer: {tool})")
    if tool == "qlmanage":
        print(
            "note: rendered via macOS qlmanage fallback — install librsvg "
            "(brew install librsvg) and re-run for production-grade rasters",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
