"""Render a review sheet: rows = proxy state, cols = rule/global/direct.

usage: python fork/preview-tray-mode-icons.py src-tauri/icons src-tauri/icons <out_png>
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROWS = [
    ("color", "tray-icon", "tray-icon"),
    ("color", "tray-icon-sys", "tray-icon-sys"),
    ("color", "tray-icon-tun", "tray-icon-tun"),
    ("mono", "tray-icon-mono", "tray-icon-mono"),
    ("mono", "tray-icon-sys-mono", "tray-icon-sys-mono"),
    ("mono", "tray-icon-tun-mono", "tray-icon-tun-mono"),
]
MODES = ["rule", "global", "direct"]
BIG, CELL = 128, 300


def frame(path: Path, size: int) -> Image.Image:
    ico = Image.open(path)
    ico.size = (size, size)
    return ico.copy().convert("RGBA")


def tint(img: Image.Image, rgb) -> Image.Image:
    out = Image.new("RGBA", img.size, rgb + (0,))
    out.putalpha(img.getchannel("A"))
    return out


def main(src: Path, gen: Path, out: Path):
    W, H = CELL * 3 + 40, CELL * len(ROWS) + 60
    sheet = Image.new("RGBA", (W, H), (245, 245, 245, 255))
    d = ImageDraw.Draw(sheet)
    for c, m in enumerate(MODES):
        d.text((40 + c * CELL + 110, 20), m.upper(), fill=(30, 30, 30, 255))
    for r, (kind, base, stem) in enumerate(ROWS):
        for c, mode in enumerate(MODES):
            path = gen / f"{stem}-{mode}.ico"
            x0, y0 = 40 + c * CELL, 50 + r * CELL
            # large preview on mid grey
            d.rectangle([x0, y0, x0 + CELL - 20, y0 + 150], fill=(150, 150, 150, 255))
            big = frame(path, 256).resize((BIG, BIG), Image.LANCZOS)
            if kind == "mono":
                big = tint(big, (20, 20, 20))
            sheet.alpha_composite(big, (x0 + (CELL - 20 - BIG) // 2, y0 + 11))
            # real-size strips: light and dark taskbar, 16/24/32 px at 2x zoom (nearest)
            for i, (bg, fg) in enumerate((((240, 240, 240), (20, 20, 20)), ((32, 32, 32), (240, 240, 240)))):
                yy = y0 + 160 + i * 60
                d.rectangle([x0, yy, x0 + CELL - 20, yy + 54], fill=bg + (255,))
                xx = x0 + 10
                for sz in (16, 24, 32):
                    f = frame(path, sz)
                    if kind == "mono":
                        f = tint(f, fg)  # emulate macOS template rendering
                    f = f.resize((sz * 2, sz * 2), Image.NEAREST)
                    sheet.alpha_composite(f, (xx, yy + (54 - sz * 2) // 2))
                    xx += sz * 2 + 18
    sheet.save(out)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
