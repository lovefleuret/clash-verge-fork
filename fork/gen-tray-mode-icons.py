"""Generate outbound-mode tray icon variants (rule = fork arrow, global = globe, direct = arrow).

Each variant is the existing per-size ICO frame with a symbol badge in the
bottom-right corner, separated from the base icon by a transparent ring.

usage: python fork/gen-tray-mode-icons.py src-tauri/icons <out_dir>

Requires Pillow. Base icons are the original tray-icon*.ico files, which must
therefore stay in src-tauri/icons.
"""
import io
import struct
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

SS = 16  # supersampling factor

# Badge diameter / transparent gap in px per frame size. Diameters are odd so the
# badge centre sits on a pixel centre and 1px glyph strokes stay crisp at 16px.
BADGE = {16: (9, 1), 24: (13, 1.5), 32: (17, 2), 48: (27, 3), 64: (35, 4), 256: (137, 16)}

MODE_COLOR = {"rule": (13, 148, 136, 255), "global": (37, 99, 235, 255), "direct": (107, 114, 128, 255)}

# base file -> (output stem, is_mono)
BASES = {
    "tray-icon.ico": ("tray-icon", False),
    "tray-icon-sys.ico": ("tray-icon-sys", False),
    "tray-icon-tun.ico": ("tray-icon-tun", False),
    "tray-icon-mono.ico": ("tray-icon-mono", True),
    "tray-icon-sys-mono.ico": ("tray-icon-sys-mono", True),
    "tray-icon-tun-mono.ico": ("tray-icon-tun-mono", True),
}


def glyph_mask(mode: str, size: int, big: int, cx: float, cy: float, unit: float) -> Image.Image:
    """Symbol mask; coordinates are in 16px-frame pixels around the badge centre, scaled by `unit`."""
    m = Image.new("L", (big, big), 0)
    d = ImageDraw.Draw(m)

    def p(x, y):
        return (cx + x * unit, cy + y * unit)

    def w(v):
        return max(1, round(v * unit))

    def ellipse(rx, ry, stroke):
        # PIL strokes inside the bbox; widen it so the stroke is centred on the path
        h = stroke / 2
        d.ellipse([p(-rx - h, -ry - h), p(rx + h, ry + h)], outline=255, width=w(stroke))

    # Tauri hands the largest ICO frame to the OS, which downsamples it for the tray,
    # so large frames get heavier strokes to survive the scaling.
    sw = 1 if size <= 32 else 1.5
    if mode == "direct":
        d.polygon([p(-3.2, -sw / 2), p(-0.5, -sw / 2), p(-0.5, sw / 2), p(-3.2, sw / 2)], fill=255)
        d.polygon([p(-1, -3.1), p(3.1, 0), p(-1, 3.1)], fill=255)
    elif mode == "rule":
        d.line([p(0, 3.3), p(0, -0.2)], fill=255, width=w(sw))
        d.line([p(-1.6, -1.3), p(0, 0.3), p(1.6, -1.3)], fill=255, width=w(sw), joint="curve")
        d.polygon([p(-3, -3), p(-0.4, -3), p(-3, -0.4)], fill=255)
        d.polygon([p(3, -3), p(0.4, -3), p(3, -0.4)], fill=255)
    else:
        # The badge itself is the globe outline; only the equator and one meridian stay legible.
        d.line([p(-4.5, 0), p(4.5, 0)], fill=255, width=w(sw))
        ellipse(1.5 if sw == 1 else 1.75, 4, sw)
    return m


def badge_layers(size: int, mode: str, mono: bool, color):
    """Return (erase_mask, badge_rgba) at `size`, rendered with supersampling."""
    dia, gap = BADGE.get(size) or (round(size * 17 / 32) | 1, size / 16)
    big = size * SS
    r = dia / 2 * SS
    cx = cy = big - r

    erase = Image.new("L", (big, big), 0)
    g = gap * SS
    ImageDraw.Draw(erase).ellipse([cx - r - g, cy - r - g, cx + r + g, cy + r + g], fill=255)

    disc = Image.new("L", (big, big), 0)
    ImageDraw.Draw(disc).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    glyph = ImageChops.multiply(glyph_mask(mode, size, big, cx, cy, dia / 9 * SS), disc)

    if mono:
        # template icon: only alpha matters, symbol is cut out of a white disc
        badge = Image.new("RGBA", (big, big), (255, 255, 255, 0))
        badge.putalpha(ImageChops.subtract(disc, glyph))
    else:
        badge = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        badge.paste(Image.new("RGBA", (big, big), color), mask=disc)
        badge.paste(Image.new("RGBA", (big, big), (255, 255, 255, 255)), mask=glyph)

    return erase.resize((size, size), Image.BOX), badge.resize((size, size), Image.BOX)


def compose(frame: Image.Image, mode: str, mono: bool, color) -> Image.Image:
    frame = frame.convert("RGBA")
    size = frame.width
    erase, badge = badge_layers(size, mode, mono, color)
    r, g, b, a = frame.split()
    a = ImageChops.multiply(a, ImageChops.invert(erase))
    out = Image.merge("RGBA", (r, g, b, a))
    return Image.alpha_composite(out, badge)


def ico_frames(path: Path):
    ico = Image.open(path)
    sizes = sorted(ico.info["sizes"])
    frames = []
    for sz in sizes:
        ico.size = sz
        frames.append(ico.copy().convert("RGBA"))
    return frames


def write_ico(path: Path, frames):
    """PNG-compressed ICO, same layout as the original tray icons."""
    blobs = []
    for f in frames:
        buf = io.BytesIO()
        f.save(buf, "PNG", optimize=True)
        blobs.append(buf.getvalue())
    out = struct.pack("<HHH", 0, 1, len(frames))
    offset = 6 + 16 * len(frames)
    for f, blob in zip(frames, blobs):
        dim = 0 if f.width >= 256 else f.width
        out += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    path.write_bytes(out + b"".join(blobs))


def main(src: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    for base, (stem, mono) in BASES.items():
        frames = ico_frames(src / base)
        for mode in ("rule", "global", "direct"):
            target = out / f"{stem}-{mode}.ico"
            write_ico(target, [compose(f, mode, mono, MODE_COLOR[mode]) for f in frames])
            print(target.name, [f.width for f in frames])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
