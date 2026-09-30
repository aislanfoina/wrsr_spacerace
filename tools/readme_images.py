"""The README's pictures: renders the kit and the rockets on game-like terrain (tools/readme_scene.py,
in Blender), then mirrors them the way the game shows models, lays out the building grid and
writes docs/images/*.jpg.

    python tools/readme_images.py            # render, then compose
    python tools/readme_images.py compose    # compose from build/readme only

Needs the kit (mod/buildings/space_kit) and the textures (build/space_textures) that
tools/build_space.py makes. Set BLENDER if Blender is not in its default folder.
"""
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLENDER = os.environ.get('BLENDER', r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
RENDERS = os.path.join(ROOT, 'build', 'readme')
IMAGES = os.path.join(ROOT, 'docs', 'images')
KIT = os.path.join(ROOT, 'mod', 'buildings', 'space_kit')
ORDER = ('pad_r7', 'pad_n1', 'mik', 'rocket_plant', 'engine_plant', 'test_stand', 'lox_plant', 'propellant',
         'instruments', 'spacecraft', 'tracking', 'training', 'bureau', 'recovery', 'monument', 'gagarin')


def mirrored(name):
    """A render as the game shows it: the game draws models mirrored left to right."""
    return Image.open(os.path.join(RENDERS, name)).convert('RGB').transpose(Image.FLIP_LEFT_RIGHT)


def save(im, name, width=1600):
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(os.path.join(IMAGES, name), quality=84, optimize=True, progressive=True)
    print('%-18s %4d x %-4d %4d KB' % (name, im.width, im.height, os.path.getsize(os.path.join(IMAGES, name)) // 1024))


def font(size):
    for f in ('segoeuib.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf'):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            pass
    return ImageFont.load_default()


def building_name(key):
    for line in open(os.path.join(KIT, 'sr_' + key, 'building.ini'), encoding='utf-8', errors='replace'):
        if line.startswith('$NAME_STR'):
            return line.split('"')[1]
    return key


def grid(cols=4, tile=(400, 256), label=30):
    """The sixteen buildings in a 4 x 4 grid, each named under its picture."""
    rows = (len(ORDER) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tile[0], rows * (tile[1] + label)), (24, 26, 30))
    d = ImageDraw.Draw(sheet)
    f = font(15)
    for i, key in enumerate(ORDER):
        x, y = (i % cols) * tile[0], (i // cols) * (tile[1] + label)
        im = mirrored('b_%s.png' % key)
        s = max(tile[0] / im.width, tile[1] / im.height)
        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        ox, oy = (im.width - tile[0]) // 2, (im.height - tile[1]) // 2
        sheet.paste(im.crop((ox, oy, ox + tile[0], oy + tile[1])), (x, y))
        name = building_name(key)
        w = d.textlength(name, font=f)
        d.text((x + (tile[0] - w) / 2, y + tile[1] + 6), name, fill=(235, 232, 225), font=f)
    return sheet


def main():
    if 'compose' not in sys.argv[1:]:
        r = subprocess.run([BLENDER, '-b', '--python', os.path.join('tools', 'readme_scene.py'), '--',
                            'build/space_textures', 'mod/buildings/space_kit', 'build/readme'], cwd=ROOT)
        if r.returncode:
            sys.exit('Blender failed')
    os.makedirs(IMAGES, exist_ok=True)
    save(mirrored('cosmodrome.png'), 'cosmodrome.jpg')
    save(mirrored('pad_r7.png'), 'pad_r7.jpg', 1200)
    save(mirrored('pad_n1.png'), 'pad_n1.jpg', 1200)
    save(Image.open(os.path.join(RENDERS, 'rockets.png')).convert('RGB'), 'rockets.jpg')   # smallest to largest, left to right
    save(grid(), 'buildings.jpg')


if __name__ == '__main__':
    main()
