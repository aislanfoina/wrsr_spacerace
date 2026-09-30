"""README pictures: the kit's buildings and the rockets standing on game-like terrain - grass and
steppe to the horizon, forests, a hazy sky - instead of the grey preview backdrop.

    blender -b --python tools/readme_scene.py -- <texdir> <kitdir> <outdir>

Uses the kit's own models (model.nmf) and builds the rockets as space_vehicles.py does. Writes
PNGs to <outdir>; tools/readme_images.py mirrors them the way the game shows models, lays out
the building grid and writes docs/images/*.jpg. Coordinates are game coordinates (x right,
y up, z towards a building's road side); mmkit.G converts them for Blender.
"""
import math
import os
import random
import sys

import bpy
import bmesh

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402
import mmkit  # noqa: E402
import srkit as K  # noqa: E402
from mmkit import G  # noqa: E402
from space_palette import MATS  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TEXDIR = argv[0] if len(argv) > 0 else 'build/space_textures'
KITDIR = argv[1] if len(argv) > 1 else 'mod/buildings/space_kit'
OUT = argv[2] if len(argv) > 2 else 'build/readme'

HORIZON = (0.70, 0.74, 0.78)
ZENITH = (0.30, 0.46, 0.72)
# camera per building, as space_scene.py frames its previews: azimuth, elevation, fill, target height
VIEW = {'pad_r7': (-35, 28, 1.0, 14.0), 'pad_n1': (-40, 18, 1.6, 75.0), 'test_stand': (-35, 20, 1.0, 26.0),
        'monument': (-35, 12, 1.6, 55.0), 'gagarin': (-35, 12, 1.6, 21.0), 'mik': (-30, 30, 0.9, None)}
BUILDINGS = ('pad_r7', 'pad_n1', 'mik', 'rocket_plant', 'engine_plant', 'test_stand', 'lox_plant', 'propellant',
             'instruments', 'spacecraft', 'tracking', 'training', 'bureau', 'recovery', 'monument', 'gagarin')


def rocket_fns():
    return {'sputnik': lambda b: K.rocket_r7(b, variant='sputnik'), 'vostok': lambda b: K.rocket_r7(b, variant='vostok'),
            'soyuz': lambda b: K.rocket_r7(b, variant='soyuz'), 'proton': lambda b: K.rocket_proton(b), 'n1': lambda b: K.rocket_n1(b)}


# ------------------------------------------------------------------ world --

def sky():
    """A gradient sky: haze at the horizon, blue overhead. The terrain fades into the same haze."""
    w = bpy.context.scene.world
    nt = w.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    bg = nt.nodes.new('ShaderNodeBackground')
    out = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(coord.outputs['Generated'], sep.inputs[0])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = HORIZON + (1.0,)
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = ZENITH + (1.0,)
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    nt.links.new(bg.outputs['Background'], out.inputs['Surface'])


def socket(sockets, name, kind):
    return [s for s in sockets if s.name == name and s.type == kind][0]


def terrain(size=12000.0):
    """The map: grass and dry steppe in broad patches, fine bumps, fading into haze with distance."""
    me = bpy.data.meshes.new('terrain')
    h = size / 2
    me.from_pydata([(-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0)], [], [(0, 1, 2, 3)])
    m = bpy.data.materials.new('terrain')
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value = 0.95
    tc = nt.nodes.new('ShaderNodeTexCoord')
    patch = nt.nodes.new('ShaderNodeTexNoise')
    patch.inputs['Scale'].default_value = 0.012
    patch.inputs['Detail'].default_value = 8.0
    patch.inputs['Roughness'].default_value = 0.62
    nt.links.new(tc.outputs['Object'], patch.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.30, (0.06, 0.12, 0.03, 1.0)
    cr.elements[1].position, cr.elements[1].color = 0.74, (0.30, 0.27, 0.11, 1.0)
    e = cr.elements.new(0.50)
    e.color = (0.10, 0.17, 0.04, 1.0)
    e = cr.elements.new(0.63)
    e.color = (0.18, 0.22, 0.07, 1.0)
    nt.links.new(patch.outputs['Fac'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    fine = nt.nodes.new('ShaderNodeTexNoise')
    fine.inputs['Scale'].default_value = 1.5
    fine.inputs['Detail'].default_value = 4.0
    nt.links.new(tc.outputs['Object'], fine.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.25
    nt.links.new(fine.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    # aerial perspective: mix towards the horizon haze with distance from the camera
    cam = nt.nodes.new('ShaderNodeCameraData')
    rng = nt.nodes.new('ShaderNodeMapRange')
    rng.inputs['From Min'].default_value = 900.0
    rng.inputs['From Max'].default_value = 7000.0
    rng.inputs['To Min'].default_value = 0.0
    rng.inputs['To Max'].default_value = 0.9
    nt.links.new(cam.outputs['View Distance'], rng.inputs['Value'])
    haze = nt.nodes.new('ShaderNodeEmission')
    haze.inputs['Color'].default_value = HORIZON + (1.0,)
    haze.inputs['Strength'].default_value = 1.0
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(rng.outputs['Result'], mix.inputs['Fac'])
    nt.links.new(bsdf.outputs['BSDF'], mix.inputs[1])
    nt.links.new(haze.outputs['Emission'], mix.inputs[2])
    out = nt.nodes.get('Material Output')
    nt.links.new(mix.outputs['Shader'], out.inputs['Surface'])
    me.materials.append(m)
    ob = bpy.data.objects.new('terrain', me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def flat_material(name, rgb, roughness=0.9):
    m = bpy.data.materials.get(name)
    if m is None:
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes.get('Principled BSDF')
        b.inputs['Base Color'].default_value = rgb + (1.0,)
        b.inputs['Roughness'].default_value = roughness
    return m


def forest(clear, seed=11, clusters=70, reach=2600.0):
    """Clusters of conifers, one mesh. clear = (xmin, xmax, zmin, zmax) in game coordinates, kept free."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    x0, x1, z0, z1 = clear
    placed = 0
    for _ in range(clusters * 6):
        if placed >= clusters:
            break
        cx, cz = rnd.uniform(-reach, reach), rnd.uniform(-reach, reach)
        if x0 - 90 < cx < x1 + 90 and z0 - 90 < cz < z1 + 90:
            continue
        placed += 1
        rad = rnd.uniform(35, 110)
        for _t in range(int(rad * rnd.uniform(0.5, 0.9))):
            tx, tz = cx + rnd.gauss(0, rad * 0.5), cz + rnd.gauss(0, rad * 0.5)
            if x0 - 25 < tx < x1 + 25 and z0 - 25 < tz < z1 + 25:
                continue
            hgt = rnd.uniform(9.0, 17.0)
            r = hgt * rnd.uniform(0.22, 0.30)
            crown = bmesh.ops.create_cone(bm, cap_ends=True, segments=7, radius1=r, radius2=0.0, depth=hgt * 0.85)
            for v in crown['verts']:
                v.co.z += hgt * 0.575
                v.co.x += tx
                v.co.y -= tz
            for f in {f for v in crown['verts'] for f in v.link_faces}:
                f.material_index = 0
            trunk = bmesh.ops.create_cone(bm, cap_ends=True, segments=5, radius1=0.3, radius2=0.25, depth=hgt * 0.3)
            for v in trunk['verts']:
                v.co.z += hgt * 0.15
                v.co.x += tx
                v.co.y -= tz
            for f in {f for v in trunk['verts'] for f in v.link_faces}:
                f.material_index = 1
    me = bpy.data.meshes.new('forest')
    bm.to_mesh(me)
    bm.free()
    me.materials.append(flat_material('pine', (0.07, 0.14, 0.05)))
    me.materials.append(flat_material('bark', (0.20, 0.13, 0.08)))
    ob = bpy.data.objects.new('forest', me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def render(path, cam_pos, target, res, fov=42.0, samples=48):
    """mmkit.render with a far clip: the terrain runs to the horizon."""
    sc = bpy.context.scene
    cam = bpy.data.cameras.new('cam')
    cam.angle = math.radians(fov)
    cam.clip_start = 0.5
    cam.clip_end = 20000.0
    co = bpy.data.objects.new('cam', cam)
    sc.collection.objects.link(co)
    co.location = G(*cam_pos)
    co.rotation_euler = (G(*target) - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGB'
    sc.render.filepath = os.path.abspath(path)
    sc.render.engine = 'BLENDER_EEVEE'
    sc.eevee.taa_render_samples = samples
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co)
    bpy.data.cameras.remove(cam)
    print('rendered', path)


# ------------------------------------------------------------------ scene --

BMATS = None


def building(key, x=0.0, z=0.0, turn=False):
    """A kit building from its model.nmf at game (x, 0, z), turned round if turn. Returns (objects, bbox)."""
    model = nmf.read(os.path.join(KITDIR, 'sr_' + key, 'model.nmf'))
    lookup = {i: BMATS[MATS.index(nm)] for i, nm in enumerate(model.materials)}
    obs = mmkit.add_nmf_object(model, key, lambda i: lookup[i])
    for ob in obs:
        ob.location = G(x, 0.0, z)
        ob.rotation_euler = (0.0, 0.0, math.pi if turn else 0.0)
    return obs, mmkit.model_bbox(model.shapes)


def deck(key):
    """Height of the pad's rocket station, from its building.ini."""
    for line in open(os.path.join(KITDIR, 'sr_' + key, 'building.ini'), encoding='utf-8', errors='replace'):
        t = line.split()
        if t and t[0] == '$HELIPORT_STATION':
            return float(t[2])
    return 0.5


def rocket(name, x=0.0, y=0.0, z=0.0):
    b = K.builder(seed=5)
    K.place(b, rocket_fns()[name], center=(x, y, z))
    obs = b.preview_objects(BMATS, 'rk_' + name)
    return obs, b


def clear(obs, builders=()):
    for ob in obs:
        bpy.data.objects.remove(ob)
    for b in builders:
        b.free()


def tiles():
    """Each building on its own, framed as its in-game preview."""
    for key in BUILDINGS:
        obs, bbox = building(key)
        extra, bs = [], []
        if key in ('pad_r7', 'pad_n1'):
            o, b = rocket('vostok' if key == 'pad_r7' else 'n1', y=deck(key))
            extra += o
            bs.append(b)
        trees = forest((bbox[0], bbox[3], bbox[2], bbox[5]), seed=sum(map(ord, key)))
        az, el, fill, ty = VIEW.get(key, (-35, 26, 0.95, None))
        pos, tgt = mmkit.frame_camera(bbox, azimuth_deg=az, elevation_deg=el, fill=fill)
        if ty is not None:
            dy = ty - tgt[1]
            pos, tgt = (pos[0], pos[1] + dy, pos[2]), (tgt[0], ty, tgt[2])
        render(os.path.join(OUT, 'b_%s.png' % key), pos, tgt, (1000, 640), samples=32)
        clear(obs + extra + [trees], bs)


def pads():
    """The two launch complexes with their rockets, close up."""
    for key, name, cam, tgt in (('pad_r7', 'vostok', (-70.0, 34.0, 80.0), (0.0, 18.0, 0.0)),
                                ('pad_n1', 'n1', (-230.0, 80.0, 250.0), (0.0, 62.0, 0.0))):
        obs, bbox = building(key)
        o, b = rocket(name, y=deck(key))
        trees = forest((bbox[0], bbox[3], bbox[2], bbox[5]), seed=3)
        render(os.path.join(OUT, key + '.png'), cam, tgt, (1600, 1000), samples=48, fov=45)
        clear(obs + o + [trees], [b])


def lineup():
    """The five rockets side by side on open ground, a 1.8 m figure for scale."""
    b = K.builder(seed=3)
    x = 0.0
    for name in ('sputnik', 'vostok', 'soyuz', 'proton', 'n1'):
        K.place(b, rocket_fns()[name], center=(x, 0.0, 0.0))
        x += 22.0
    b.box(K.RED, (-8.0, 0.9, 6.0), (0.5, 1.8, 0.3))
    obs = b.preview_objects(BMATS, 'lineup')
    trees = forest((-30.0, 120.0, -40.0, 40.0), seed=5)
    render(os.path.join(OUT, 'rockets.png'), (44.0, 28.0, 240.0), (44.0, 52.0, 0.0), (1600, 900), samples=48, fov=50)
    clear(obs + [trees], [b])


def cosmodrome():
    """A small cosmodrome along one road: the pad with a Vostok, the MIK and the plants that feed it."""
    road_half, gap, space = 7.0, 6.0, 14.0
    north = ('tracking', 'pad_r7', 'mik', 'lox_plant')
    south = ('propellant', 'engine_plant', 'rocket_plant', 'test_stand')
    placed = []                                    # (key, x, z, turn, bbox)
    for row, turn in ((north, False), (south, True)):
        cursor = 0.0
        for key in row:
            bbox = mmkit.model_bbox(nmf.read(os.path.join(KITDIR, 'sr_' + key, 'model.nmf')).shapes)
            if not turn:                           # front (+z) faces the road at z = 0
                x = cursor - bbox[0]
                z = -(road_half + gap) - bbox[5]
                cursor = x + bbox[3] + space
            else:                                  # turned round: its front faces the road too
                x = cursor + bbox[3]
                z = road_half + gap + bbox[5]
                cursor = x - bbox[0] + space
            placed.append((key, x, z, turn, bbox))
    xs = [x + (b[0] if not t else -b[3]) for _k, x, _z, t, b in placed] + [x + (b[3] if not t else -b[0]) for _k, x, _z, t, b in placed]
    shift = -(min(xs) + max(xs)) / 2
    obs, bs = [], []
    zs = []
    for key, x, z, turn, bbox in placed:
        o, _bb = building(key, x + shift, z, turn)
        obs += o
        zs += [z + bbox[2], z + bbox[5]] if not turn else [z - bbox[5], z - bbox[2]]
        if key == 'pad_r7':
            o, b = rocket('vostok', x + shift, deck(key), z)
            obs += o
            bs.append(b)
    length = max(xs) - min(xs)
    rb = K.builder(seed=9)
    rb.box(K.ASPH, (0.0, -0.1, 0.0), (length + 160.0, 0.3, road_half * 2))
    obs += rb.preview_objects(BMATS, 'road')
    bs.append(rb)
    trees = forest((-length / 2 - 40, length / 2 + 40, min(zs) - 30, max(zs) + 30), seed=21, clusters=90)
    pad_x = [x + shift for k, x, _z, _t, _b in placed if k == 'pad_r7'][0]
    cam = (pad_x - 170.0, 105.0, 300.0)
    render(os.path.join(OUT, 'cosmodrome.png'), cam, (pad_x + 60.0, 28.0, -60.0), (1600, 900), samples=48, fov=46)
    clear(obs + [trees], bs)


def main():
    global BMATS
    os.makedirs(OUT, exist_ok=True)
    mmkit.clear_scene()
    BMATS = mmkit.blender_materials(TEXDIR, MATS)
    mmkit.lighting()
    sky()
    terrain()
    only = set(argv[3].split(',')) if len(argv) > 3 and argv[3] else None
    for name, fn in (('cosmodrome', cosmodrome), ('pads', pads), ('rockets', lineup), ('tiles', tiles)):
        if not only or name in only:
            fn()


main()
