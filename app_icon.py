"""Generates Irestrem app icon and creates AppIcon.icns for the .app bundle."""
import subprocess
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter


def draw_eye_icon(size: int) -> Image.Image:
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dark rounded-square background
    r = size // 5
    draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=r,
                            fill=(20, 20, 40, 255))

    cx, cy = size // 2, size // 2

    # Subtle inner glow ring (slightly lighter)
    glow_pad = size // 14
    draw.rounded_rectangle([glow_pad, glow_pad,
                             size - glow_pad - 1, size - glow_pad - 1],
                            radius=r - glow_pad // 2,
                            fill=(30, 30, 55, 255))

    # ── Eye ──────────────────────────────────────────────────────────────
    # Sclera (white part) — horizontal lens/almond shape
    ew = int(size * 0.66)
    eh = int(size * 0.36)
    # Soft shadow behind sclera
    shadow = img.copy()
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([cx - ew // 2 + 2, cy - eh // 2 + 4,
                   cx + ew // 2 + 2, cy + eh // 2 + 4],
                  fill=(0, 0, 0, 80))
    img = Image.alpha_composite(img, shadow)
    draw = ImageDraw.Draw(img)

    draw.ellipse([cx - ew // 2, cy - eh // 2,
                  cx + ew // 2, cy + eh // 2],
                 fill=(230, 232, 245, 255))

    # Iris
    ir = int(size * 0.155)
    draw.ellipse([cx - ir, cy - ir, cx + ir, cy + ir],
                 fill=(200, 45, 75, 255))      # darker ring
    ir2 = int(size * 0.13)
    draw.ellipse([cx - ir2, cy - ir2, cx + ir2, cy + ir2],
                 fill=(233, 69, 96, 255))       # accent red

    # Pupil
    pr = int(size * 0.075)
    draw.ellipse([cx - pr, cy - pr, cx + pr, cy + pr],
                 fill=(12, 12, 25, 255))

    # Specular highlight
    hr = int(size * 0.028)
    hx = cx + int(size * 0.048)
    hy = cy - int(size * 0.048)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr],
                 fill=(255, 255, 255, 220))

    # Tiny secondary highlight
    hr2 = int(size * 0.013)
    draw.ellipse([cx - hr2, cy + int(size * 0.04) - hr2,
                  cx + hr2, cy + int(size * 0.04) + hr2],
                 fill=(255, 255, 255, 120))

    return img


def create_icns(dest: Path) -> bool:
    iconset = dest.parent / 'AppIcon.iconset'
    iconset.mkdir(exist_ok=True)

    mapping = {
        16:   ['icon_16x16.png'],
        32:   ['icon_16x16@2x.png', 'icon_32x32.png'],
        64:   ['icon_32x32@2x.png'],
        128:  ['icon_128x128.png'],
        256:  ['icon_128x128@2x.png', 'icon_256x256.png'],
        512:  ['icon_256x256@2x.png', 'icon_512x512.png'],
        1024: ['icon_512x512@2x.png'],
    }

    for px, names in mapping.items():
        icon = draw_eye_icon(px)
        for name in names:
            icon.save(iconset / name, 'PNG')

    ok = subprocess.run(
        ['iconutil', '-c', 'icns', str(iconset), '-o', str(dest)],
        capture_output=True,
    ).returncode == 0

    shutil.rmtree(iconset, ignore_errors=True)
    return ok


if __name__ == '__main__':
    base = Path(__file__).parent
    icns_path = base / 'AppIcon.icns'
    png_path  = base / 'AppIcon.png'

    # Always save a PNG for tkinter window icon
    draw_eye_icon(512).save(png_path, 'PNG')
    print(f'PNG saved: {png_path}')

    if create_icns(icns_path):
        print(f'ICNS saved: {icns_path}')
    else:
        print('iconutil not available — PNG only')
