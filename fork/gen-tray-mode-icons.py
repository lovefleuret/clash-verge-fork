"""Generate outbound-mode tray icon variants (R = rule, G = global, D = direct).

Each variant is the existing per-size ICO frame with a letter badge in the
bottom-right corner. Letters are drawn geometrically (no font dependency).

usage: python fork/gen-tray-mode-icons.py src-tauri/icons <out_dir>

Requires Pillow and ImageMagick (`magick`) on PATH. Base icons are the
original tray-icon*.ico files, which must therefore stay in src-tauri/icons.
"""
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

SS = 8  # supersampling factor
BADGE = 0.47  # badge diameter relative to icon size
GAP = 0.06  # transparent ring around badge relative to icon size

MODE_COLOR = {"rule": (13, 148, 136, 255), "global": (37, 99, 235, 255), "direct": (71, 85, 105, 255)}

# base file -> (output stem, is_mono)
BASES = {
    "tray-icon.ico": ("tray-icon", False),
    "tray-icon-sys.ico": ("tray-icon-sys", False),
    "tray-icon-tun.ico": ("tray-icon-tun", False),
    "tray-icon-mono.ico": ("tray-icon-mono", True),
    "tray-icon-sys-mono.ico": ("tray-icon-sys-mono", True),
    "tray-icon-tun-mono.ico": ("tray-icon-tun-mono", True),
}


def letter_mask(letter: str, box: int) -> Image.Image:
    """Bold geometric letter centred in a box x box mask."""
    m = Image.new("L", (box, box), 0)
    h = box * 0.62
    w = box * {"D": 0.52, "R": 0.5}.get(letter, 0.58)
    x0, y0 = (box - w) / 2, (box - h) / 2
    x1, y1 = x0 + w, y0 + h
    s = h * 0.24  # stroke
    d = ImageDraw.Draw(m)
    if letter == "D":
        rx = w * 0.5
        d.rectangle([x0, y0, x1 - rx, y1], fill=255)
        d.ellipse([x1 - 2 * rx, y0, x1, y1], fill=255)
        inner = Image.new("L", (box, box), 0)
        di = ImageDraw.Draw(inner)
        di.rectangle([x0 + s, y0 + s, x1 - rx, y1 - s], fill=255)
        di.ellipse([x1 - 2 * rx + s, y0 + s, x1 - s, y1 - s], fill=255)
        m = ImageChops.subtract(m, inner)
    elif letter == "R":
        ym = y0 + h * 0.56  # bowl bottom
        rb = (ym - y0) / 2
        d.rectangle([x0, y0, x0 + s, y1], fill=255)
        d.rectangle([x0, y0, x1 - rb, ym], fill=255)
        d.ellipse([x1 - 2 * rb, y0, x1, ym], fill=255)
        inner = Image.new("L", (box, box), 0)
        di = ImageDraw.Draw(inner)
        di.rectangle([x0 + s, y0 + s, x1 - rb, ym - s], fill=255)
        di.ellipse([x1 - 2 * rb + s, y0 + s, x1 - s, ym - s], fill=255)
        m = ImageChops.subtract(m, inner)
        d = ImageDraw.Draw(m)
        lx = x0 + w * 0.38
        d.polygon([(lx, ym - s), (lx + s * 1.15, ym - s), (x1, y1), (x1 - s * 1.2, y1)], fill=255)
    else:  # G
        d.ellipse([x0, y0, x1, y1], fill=255)
        d.ellipse([x0 + s, y0 + s, x1 - s, y1 - s], fill=0)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        # opening on the upper right
        d.pieslice([x0 - s, y0 - s, x1 + s, y1 + s], -62, 2, fill=0)
        # crossbar
        d.rectangle([cx - s * 0.1, cy - s * 0.1, x1, cy + s * 0.9], fill=255)
    return m


def badge_layers(size: int, letter: str, mono: bool, color):
    """Return (erase_mask, badge_rgba) at `size`, rendered with supersampling."""
    big = size * SS
    dia = round(size * BADGE) * SS
    gap = max(1, round(size * GAP)) * SS
    cx = cy = big - dia / 2

    erase = Image.new("L", (big, big), 0)
    ImageDraw.Draw(erase).ellipse(
        [cx - dia / 2 - gap, cy - dia / 2 - gap, cx + dia / 2 + gap, cy + dia / 2 + gap], fill=255
    )

    disc = Image.new("L", (big, big), 0)
    ImageDraw.Draw(disc).ellipse([cx - dia / 2, cy - dia / 2, cx + dia / 2, cy + dia / 2], fill=255)
    let = Image.new("L", (big, big), 0)
    let.paste(letter_mask(letter, dia), (round(cx - dia / 2), round(cy - dia / 2)))

    if mono:
        # template icon: only alpha matters, letter is cut out of a white disc
        alpha = ImageChops.subtract(disc, let)
        badge = Image.new("RGBA", (big, big), (255, 255, 255, 0))
        badge.putalpha(alpha)
    else:
        badge = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        badge.paste(Image.new("RGBA", (big, big), color), mask=disc)
        badge.paste(Image.new("RGBA", (big, big), (255, 255, 255, 255)), mask=let)

    return erase.resize((size, size), Image.LANCZOS), badge.resize((size, size), Image.LANCZOS)


def compose(frame: Image.Image, letter: str, mono: bool, color) -> Image.Image:
    frame = frame.convert("RGBA")
    size = frame.width
    erase, badge = badge_layers(size, letter, mono, color)
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


def main(src: Path, out: Path):
    out.mkdir(parents=True, exist_ok=True)
    png_dir = out / "_png"
    png_dir.mkdir(exist_ok=True)
    for base, (stem, mono) in BASES.items():
        frames = ico_frames(src / base)
        for mode, letter in (("rule", "R"), ("global", "G"), ("direct", "D")):
            pngs = []
            for f in frames:
                img = compose(f, letter, mono, MODE_COLOR[mode])
                p = png_dir / f"{stem}-{mode}-{img.width}.png"
                img.save(p)
                pngs.append(str(p))
            # largest frame last keeps the ICO directory order like the originals don't matter
            target = out / f"{stem}-{mode}.ico"
            subprocess.run(["magick", *pngs, str(target)], check=True)
            print(target.name, [f.width for f in frames])


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
