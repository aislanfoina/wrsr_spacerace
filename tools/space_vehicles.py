"""Space Race rockets as helicopter-class vehicles, plus showcase renders.

    blender -b --python tools/space_vehicles.py -- <texdir> <outroot> <previewdir> <kitdir>

A rocket is a VEHICLETYPE_HELICOPTER: it stands on a pad's HELIPORT_STATION and
lifts off vertically. The engine wants at least one rotor, so each rocket ships a
40 cm block as its only propeller (screwcon/hi/lo.nmf + material_propeler.mtl in
its own folder; workshop paths resolve there) and hides it inside the body.
Crew are passengers.
Writes one workshop vehicle item per rocket under <outroot>/<key>/ and PNG
previews to <previewdir> (tools/build_space.py turns those into the .dds the
purchase window wants).
"""
import math
import os
import shutil
import struct
import sys

import bpy

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402
import mmkit  # noqa: E402
import srkit as K  # noqa: E402
from space_palette import MATS  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TEXDIR = argv[0] if len(argv) > 0 else 'build/space_textures'
OUTROOT = argv[1] if len(argv) > 1 else 'mod/vehicles'
PREVIEW = argv[2] if len(argv) > 2 else 'build/space_vehicles'
KITDIR = argv[3] if len(argv) > 3 else 'mod/buildings/space_kit'

# key, builder, item id, name, description, years, crew, hub height
ROCKETS = [
    ('sr_sputnik', lambda b: K.rocket_r7(b, variant='sputnik'), 9000111, 'R-7 Sputnik (8K71PS)',
     'The Semyorka that opened the space age: Sputnik 1 on 4 October 1957, Laika a month later.', (1957, 1960), 1, 8.0),
    ('sr_vostok', lambda b: K.rocket_r7(b, variant='vostok'), 9000112, 'Vostok-K (8K72K)',
     'R-7 with the Blok E upper stage. Gagarin, Titov, Tereshkova. One cosmonaut.', (1960, 1965), 1, 8.0),
    ('sr_soyuz', lambda b: K.rocket_r7(b, variant='soyuz'), 9000113, 'Soyuz (11A511)',
     'The workhorse: Soyuz spacecraft with its escape tower. Three cosmonauts.', (1966, 1995), 3, 8.0),
    ('sr_proton', lambda b: K.rocket_proton(b), 9000114, 'Proton (UR-500K)',
     'Chelomei\'s hypergolic heavy lifter: Zond round the Moon, Luna sample return, Salyut stations.', (1965, 2000), 1, 10.0),
    ('sr_n1', lambda b: K.rocket_n1(b), 9000115, 'N1-L3',
     'The Moon rocket. 30 engines, 105 m. It has to fly before Apollo does. Two cosmonauts.', (1969, 1976), 2, 20.0),
]


def mtl(names):
    out = []
    for name in names:
        out += ['$SUBMATERIAL %s' % name, '$TEXTURE_MTL 0 %s.dds' % name, '$TEXTURE 1 blankspecular.dds', '$TEXTURE 2 blankbump.dds', '',
                '$DIFFUSECOLOR 1.0 1.0 1.0 1.0', '$SPECULARCOLOR 0.8 0.8 0.8 1.0', '$AMBIENTCOLOR 1.0 1.0 1.0 1.0', '',
                '$SPECULARPOWER 6.0', '']
    out += ['$END', '']
    return '\r\n'.join(out)


# the programme script recognises each rocket by its engine power (the VM's Vehicle has no type name)
POWER = {'sr_sputnik': 9001, 'sr_vostok': 9002, 'sr_soyuz': 9003, 'sr_proton': 9004, 'sr_n1': 9005}
# dry mass in tonnes: the production line's bill of parts scales with it (30 t = 6,600 workdays,
# 22 t aluminium, 11 t mechanical components ... in game), so an N1 costs about seven Soyuz
EMPTY_WEIGHT = {'sr_sputnik': 25.0, 'sr_vostok': 30.0, 'sr_soyuz': 40.0, 'sr_proton': 70.0, 'sr_n1': 180.0}


def script(key, name, desc, years, crew, hub, height):
    return '\r\n'.join([
        '$TYPE VEHICLETYPE_HELICOPTER',
        '$SOUND_PARAMS sounds/helicopters/mi6.ini',
        '$NAME_STR "%s"' % name,
        '$DESCRIPTION_STR "%s"' % desc,
        '$COST_RUB %d' % int(40000 + height * 2500),
        '$MOVEMENT_CONSPUMPTION 0',
        '$MOVEMENT_SPEED 420',
        '$MOVEMENT_POWER_KW %d' % POWER[key],
        '$MOVEMENT_EMPTY_WEIGHT %.1f' % EMPTY_WEIGHT[key],
        '$RESOURCE_CAPACITY %d' % crew,
        '$RESOURCE_TRANSPORT_TYPE RESOURCE_TRANSPORT_PASSANGER',
        '$AVAILABLE %d %d' % years,
        '$COUNTRY 39011',
        '$MOVEMENT_WHEEL_FRONT 0.0 0.0 1.0',
        '$MOVEMENT_WHEEL_BACK 0.0 0.0 -1.0',
        # four paths or the tokenizer eats the next line as file names
        '$PROPELER_HELICOPTER 1 screwcon.nmf screwhi.nmf screwlo.nmf material_propeler.mtl',
        '$PROPELER_HELICOPTER_POINT_DIR 0.0 %.1f 0.0 0.0 0.0 0.0' % hub,
        'end', ''])


def write_hidden_rotor(vdir, mat):
    """The propeller the helicopter class insists on: a small block, placed inside the body by POINT_DIR."""
    rb = K.builder(seed=7)
    rb.box(MATS.index(mat), (0.0, 0.0, 0.0), (0.4, 0.4, 0.4))
    shapes, used = rb.export_shapes(prefix='rotor_')
    for lod in ('con', 'hi', 'lo'):
        model = nmf.Model(); model.materials = used; model.shapes = shapes
        nmf.write(model, os.path.join(vdir, 'screw%s.nmf' % lod))
    mmkit.write_text(os.path.join(vdir, 'material_propeler.mtl'), mtl(used))
    rb.free()


def workshopconfig(key, item, name, desc):
    return '\r\n'.join(['$ITEM_ID %d' % item, '', '$OWNER_ID 76561198165729857', '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_VEHICLE', '',
                        '$VISIBILITY 2', '', '$OBJECT_VEHICLE %s' % key, '', '$ITEM_NAME "%s"' % name, '', '$ITEM_DESC "%s"' % desc, '', '$END', ''])


def main():
    mmkit.clear_scene()
    os.makedirs(PREVIEW, exist_ok=True)
    bmats = mmkit.blender_materials(TEXDIR, MATS)
    mmkit.lighting()
    heights = {}
    for key, fn, item, name, desc, years, crew, hub in ROCKETS:
        b = K.builder(seed=item)
        h = fn(b)
        heights[key] = h
        shapes, used = b.export_shapes(prefix='rk_')
        model = nmf.Model(); model.materials = used; model.shapes = shapes
        root = os.path.join(OUTROOT, key)
        vdir = os.path.join(root, key)
        if os.path.isdir(vdir):
            shutil.rmtree(vdir)
        os.makedirs(vdir)
        nmf.write(model, os.path.join(vdir, 'main.nmf'))
        bbox = mmkit.model_bbox(shapes)
        with open(os.path.join(vdir, 'bbox.bin'), 'wb') as f:
            f.write(struct.pack('<6f', *bbox))
        for m in used:
            shutil.copy(os.path.join(TEXDIR, m + '.dds'), os.path.join(vdir, m + '.dds'))
        mmkit.write_text(os.path.join(vdir, 'material.mtl'), mtl(used))
        write_hidden_rotor(vdir, used[0])
        mmkit.write_text(os.path.join(vdir, 'script.ini'), script(key, name, desc, years, crew, hub, h))
        mmkit.write_text(os.path.join(root, 'workshopconfig.ini'), workshopconfig(key, item, name, desc))
        obs = b.preview_objects(bmats, key)
        # purchase-window previews: 3/4 view and a side view, transparent
        cy = h * 0.5
        d = h * 1.25
        mmkit.render(os.path.join(PREVIEW, key + '_preview.png'), (d * 0.55, cy + h * 0.1, d * 0.8), (0, cy, 0), (512, 512),
                     transparent=True, samples=24, fov=40)
        mmkit.render(os.path.join(PREVIEW, key + '_preview_side.png'), (0, cy, d * 1.3), (0, cy, 0), (512, 256),
                     transparent=True, samples=16, ortho=h * 1.1)
        mmkit.render(os.path.join(PREVIEW, key + '_item.png'), (d * 0.5, cy + h * 0.15, d * 0.75), (0, cy, 0), (640, 640), samples=24, fov=40)
        for ob in obs:
            bpy.data.objects.remove(ob)
        b.free()
        print('%-11s %-22s h=%5.1f tris=%6d nodes=%d bbox=%s' % (key, name, h, sum(s.nt for s in shapes), len(shapes), ['%.1f' % v for v in bbox]))
    showcase(bmats, heights)


def showcase(bmats, heights):
    """Rockets on their pads and in a line-up - for the design review, not the game."""
    # the line-up with a 1.8 m figure for scale
    b = K.builder(seed=3)
    b.box(K.GROUND, (40.0, -0.25, 0), (150, 0.5, 40))
    x = 0.0
    for key, fn, *_ in ROCKETS:
        K.place(b, fn, center=(x, 0, 0))
        x += 22.0
    b.box(K.RED, (-8.0, 0.9, 6.0), (0.5, 1.8, 0.3))
    obs = b.preview_objects(bmats, 'lineup')
    mmkit.render(os.path.join(PREVIEW, 'showcase_lineup.png'), (44.0, 40.0, 190.0), (44.0, 50.0, 0.0), (1600, 900), samples=32, fov=50)
    for ob in obs:
        bpy.data.objects.remove(ob)
    b.free()
    # the R-7 pad with a Vostok on it and the N1 on Site 110, built from the kit's own models
    for pad, rocket, y0, cam, tgt in (('sr_pad_r7', ROCKETS[1][1], 6.35, (-70.0, 38.0, 80.0), (0.0, 18.0, 0.0)),
                                      ('sr_pad_n1', ROCKETS[4][1], 17.6, (-230.0, 95.0, 250.0), (0.0, 62.0, 0.0))):
        path = os.path.join(KITDIR, pad, 'model.nmf')
        if not os.path.exists(path):
            continue
        model = nmf.read(path)
        lookup = {i: bmats[MATS.index(nm)] for i, nm in enumerate(model.materials)}
        obs = mmkit.add_nmf_object(model, pad, lambda i: lookup[i])
        b = K.builder(seed=5)
        K.place(b, rocket, center=(0.0, y0, 0.0))
        obs += b.preview_objects(bmats, pad + '_rocket')
        mmkit.render(os.path.join(PREVIEW, 'showcase_%s.png' % pad), cam, tgt, (1600, 1000), samples=40, fov=45)
        for ob in obs:
            bpy.data.objects.remove(ob)
        b.free()
    print('showcase renders done')


main()
