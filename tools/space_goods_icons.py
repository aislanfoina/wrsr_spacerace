"""48 x 48 icons for the goods the resources plugin adds, in the style of the game's own
(media_soviet/resources/*.png: a simple object on transparency).

    python tools/space_goods_icons.py      # -> mod/plugins/spacerace/data/goods/<name>.png
"""
import os
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'mod', 'plugins', 'spacerace', 'data', 'goods')
S = 4                     # drawn 4x, then scaled down for smooth edges


def canvas():
    im = Image.new('RGBA', (48 * S, 48 * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def box(d, x0, y0, x1, y1, fill, outline=(40, 40, 40, 255)):
    d.rectangle([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill, outline=outline, width=S)


def ellipse(d, x0, y0, x1, y1, fill, outline=(40, 40, 40, 255)):
    d.ellipse([x0 * S, y0 * S, x1 * S, y1 * S], fill=fill, outline=outline, width=S)


def poly(d, pts, fill, outline=(40, 40, 40, 255)):
    d.polygon([(x * S, y * S) for x, y in pts], fill=fill, outline=outline)


def rocket_stage():
    im, d = canvas()
    box(d, 17, 4, 31, 40, (214, 218, 222, 255))                    # a white core stage with its red band
    box(d, 17, 14, 31, 18, (190, 40, 36, 255))
    poly(d, [(17, 40), (31, 40), (35, 46), (13, 46)], (120, 124, 128, 255))
    return im


def rocket_engine():
    im, d = canvas()
    box(d, 16, 4, 32, 16, (150, 154, 158, 255))                    # turbopump block over four nozzles
    for x in (14, 20, 26, 32):
        poly(d, [(x - 1, 16), (x + 3, 16), (x + 5, 44), (x - 3, 44)], (96, 90, 84, 255))
    return im


def avionics():
    im, d = canvas()
    box(d, 8, 10, 40, 38, (70, 110, 70, 255))                      # a green circuit board with chips
    for x, y in ((12, 14), (24, 14), (12, 26), (24, 26)):
        box(d, x, y, x + 9, y + 8, (30, 30, 30, 255), outline=(200, 200, 200, 255))
    ellipse(d, 34, 16, 38, 20, (220, 190, 60, 255))
    return im


def lox():
    im, d = canvas()
    ellipse(d, 8, 6, 40, 42, (190, 220, 245, 255))                 # a frosted blue sphere tank
    ellipse(d, 14, 11, 24, 20, (240, 250, 255, 255), outline=None)
    box(d, 20, 40, 28, 46, (120, 124, 128, 255))
    return im


def hypergolic():
    im, d = canvas()
    box(d, 12, 8, 36, 44, (210, 150, 40, 255))                     # an orange drum with a hazard stripe
    box(d, 12, 22, 36, 28, (30, 30, 30, 255))
    ellipse(d, 12, 4, 36, 12, (230, 175, 70, 255))
    return im


def spacecraft():
    im, d = canvas()
    ellipse(d, 12, 4, 36, 28, (160, 164, 150, 255))                # a Vostok ball on its service module
    poly(d, [(14, 26), (34, 26), (38, 42), (10, 42)], (120, 124, 110, 255))
    for x in (16, 30):
        box(d, x, 12, x + 3, 15, (40, 60, 90, 255), outline=None)
    return im


ICONS = {'rocket_stage': rocket_stage, 'rocket_engine': rocket_engine, 'avionics': avionics,
         'lox': lox, 'hypergolic': hypergolic, 'spacecraft': spacecraft}

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for name, fn in ICONS.items():
        fn().resize((48, 48), Image.LANCZOS).save(os.path.join(OUT, name + '.png'))
    sheet = Image.new('RGBA', (48 * len(ICONS) * 2, 96), (90, 90, 90, 255))
    for i, name in enumerate(ICONS):
        sheet.alpha_composite(Image.open(os.path.join(OUT, name + '.png')).resize((96, 96), Image.NEAREST), (i * 96, 0))
    os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
    sheet.save(os.path.join(ROOT, 'build', 'space_goods_icons.png'))
    print('icons ->', OUT)
