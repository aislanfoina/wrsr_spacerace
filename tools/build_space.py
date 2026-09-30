"""Build every Space Race asset: textures, the building kit, the rockets, previews.

    python tools/build_space.py              # textures kit vehicles previews
    python tools/build_space.py kit          # one or more stages: textures | kit | inis | vehicles | previews | research | programme | deploy
    python tools/build_space.py kit pad_r7   # kit stage for some buildings only (comma separated keys)

deploy copies the items into the game's workshop_wip (same as build_madmax.py);
build.ps1 -Install does that too for everything under mod/.
"""
import glob
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# override with the BLENDER and WRSR_GAME environment variables
BLENDER = os.environ.get('BLENDER', r'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe')
GAME = os.environ.get('WRSR_GAME', r'C:\Program Files (x86)\Steam\steamapps\common\SovietRepublic')
WIP = os.path.join(GAME, 'media_soviet', 'workshop_wip')
PY = sys.executable
TEX = 'build/space_textures'
KIT = 'mod/buildings/space_kit'
ROCKETS = ('sr_sputnik', 'sr_vostok', 'sr_soyuz', 'sr_proton', 'sr_n1')


def run(cmd):
    print('>', ' '.join(cmd))
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        sys.exit('failed: %s' % cmd[0])


def stage_textures(_=None):
    run([PY, 'tools/space_textures.py', TEX])


def stage_kit(only=None):
    run([BLENDER, '-b', '--python', 'tools/space_scene.py', '--', TEX, KIT, 'build/space'] + ([only] if only else []))


def stage_inis(only=None):
    """Only the kit's building files, stand-in and new-goods variants (no models, no renders)."""
    run([BLENDER, '-b', '--python', 'tools/space_scene.py', '--', TEX, KIT, 'build/space', only or '', 'inis'])


def stage_vehicles(_=None):
    run([BLENDER, '-b', '--python', 'tools/space_vehicles.py', '--', TEX, 'mod/vehicles', 'build/space_vehicles', KIT])


def stage_previews(_=None):
    """Vehicle purchase previews (DXT5 .dds) and the workshop preview images."""
    from PIL import Image
    sys.path.insert(0, os.path.join(ROOT, 'tools'))
    import tradepost_textures as tt
    for key in ROCKETS:
        vdir = os.path.join(ROOT, 'mod/vehicles', key, key)
        src = os.path.join(ROOT, 'build/space_vehicles', key)
        if not os.path.isdir(vdir):
            continue
        tt.save_dds_mips(Image.open(src + '_preview.png').convert('RGBA').resize((256, 256), Image.LANCZOS),
                         os.path.join(vdir, 'preview.dds'), 'DXT5')
        tt.save_dds_mips(Image.open(src + '_preview_side.png').convert('RGBA').resize((256, 128), Image.LANCZOS),
                         os.path.join(vdir, 'preview_side.dds'), 'DXT5')
        Image.open(src + '_item.png').convert('RGB').resize((512, 512), Image.LANCZOS).save(
            os.path.join(ROOT, 'mod/vehicles', key, 'previewimage.png'))
        print('previews ->', vdir)
    # the engine mirrors models left-right, so the menu icons are flipped to match the game;
    # a text chunk marks a flipped icon so running this stage again leaves it alone
    from PIL.PngImagePlugin import PngInfo
    mark = PngInfo()
    mark.add_text('sr_flipped', '1')
    for icon in glob.glob(os.path.join(ROOT, KIT, 'sr_*', 'imagegui.png')):
        im = Image.open(icon)
        if im.info.get('sr_flipped') != '1':
            im.transpose(Image.FLIP_LEFT_RIGHT).save(icon, pnginfo=mark)
    # the kit's workshop image: a 3 x 3 collage of the building renders
    keys = ['pad_r7', 'pad_n1', 'mik', 'rocket_plant', 'test_stand', 'tracking', 'training', 'bureau', 'monument']
    sheet = Image.new('RGB', (1536, 1536), (40, 40, 40))
    for i, k in enumerate(keys):
        p = os.path.join(ROOT, 'build/space', k + '.png')
        if os.path.exists(p):
            im = Image.open(p).convert('RGB')
            w, h = im.size
            side = min(w, h)
            im = im.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2)).resize((512, 512), Image.LANCZOS).transpose(Image.FLIP_LEFT_RIGHT)
            sheet.paste(im, ((i % 3) * 512, (i // 3) * 512))
    sheet.resize((768, 768), Image.LANCZOS).save(os.path.join(ROOT, KIT, 'previewimage.png'))
    print('kit preview ->', KIT)


def stage_research(_=None):
    run([PY, 'tools/space_research.py'])


def stage_programme(_=None):
    """The programme template and launches.ini, then the balance settings drawn from everything."""
    run([PY, 'tools/space_scenario.py'])
    run([PY, 'tools/space_settings.py'])


def stage_deploy(_=None):
    items = [os.path.join(ROOT, KIT)] + [os.path.join(ROOT, 'mod/vehicles', k) for k in ROCKETS]
    for src in items:
        cfg = os.path.join(src, 'workshopconfig.ini')
        item = None
        for line in open(cfg, encoding='utf-8', errors='ignore'):
            if line.startswith('$ITEM_ID'):
                item = line.split()[1]
        dst = os.path.join(WIP, item)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        print('deployed %s -> %s' % (os.path.relpath(src, ROOT), dst))


STAGES = {'textures': stage_textures, 'kit': stage_kit, 'inis': stage_inis, 'vehicles': stage_vehicles, 'previews': stage_previews,
          'research': stage_research, 'programme': stage_programme, 'deploy': stage_deploy}

if __name__ == '__main__':
    args = sys.argv[1:]
    names = [a for a in args if a in STAGES] or ['textures', 'kit', 'vehicles', 'previews']
    rest = [a for a in args if a not in STAGES]
    for n in names:
        STAGES[n](rest[0] if rest else None)
