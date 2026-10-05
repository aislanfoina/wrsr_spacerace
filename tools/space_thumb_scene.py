"""Cut-outs for the Workshop thumbnails: each rocket on its own, the five in a row and a few kit
buildings on their lots, rendered on a transparent background for tools/space_thumbs.py to put on
posters.

    blender -b --python tools/space_thumb_scene.py -- <texdir> <kitdir> <outdir> [only]

only: comma-separated subset of sputnik,vostok,soyuz,proton,n1,lineup,pad_r7,mik,tracking,monument.
The rockets render whole, top to bottom, with a long lens so their proportions stay true. Reuses
tools/readme_scene.py's model helpers.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import mmkit  # noqa: E402
import readme_scene as R  # noqa: E402  (reads the same argv: texdir, kitdir, outdir)
import srkit as K  # noqa: E402
from space_palette import MATS  # noqa: E402

ROCKETS = ('sputnik', 'vostok', 'soyuz', 'proton', 'n1')


def bounds(obs):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for ob in obs:
        if ob.type != 'MESH':
            continue
        for c in ob.bound_box:
            w = ob.matrix_world @ Vector(c)
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
    return lo, hi


def shoot(path, obs, res, azimuth=-30.0, elevation=6.0, fov=14.0, margin=1.08, look=0.5, cycles=False, samples=64):
    """Frame obs (Blender space, z up) from azimuth/elevation degrees and render RGBA to path.
    look: height of the aim point between the bottom (0) and the top (1) of the objects."""
    sc = bpy.context.scene
    lo, hi = bounds(obs)
    c = (lo + hi) / 2
    c.z = lo.z + (hi.z - lo.z) * look
    radius = (hi - lo).length / 2
    aspect = res[0] / res[1]
    half = math.radians(fov) / 2                          # fov spans the longer side (sensor fit auto)
    vhalf = half if aspect <= 1 else math.atan(math.tan(half) / aspect)
    hhalf = half if aspect >= 1 else math.atan(math.tan(half) * aspect)
    need = max((hi.z - lo.z) / 2 / math.tan(vhalf), max(hi.x - lo.x, hi.y - lo.y) / 2 / math.tan(hhalf))
    dist = need * margin + radius * 0.5
    az, el = math.radians(azimuth), math.radians(elevation)
    cam = bpy.data.cameras.new('thumbcam')
    cam.angle = math.radians(fov)
    cam.clip_start = 1.0
    cam.clip_end = dist * 4 + 1000.0
    co = bpy.data.objects.new('thumbcam', cam)
    sc.collection.objects.link(co)
    co.location = c + Vector((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el))) * dist
    co.rotation_euler = (c - co.location).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = co
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = 'PNG'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.filepath = os.path.abspath(path)
    if cycles:
        sc.render.engine = 'CYCLES'
        sc.cycles.samples = samples
        sc.cycles.use_denoising = True
    else:
        sc.render.engine = 'BLENDER_EEVEE'
        sc.eevee.taa_render_samples = samples
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(co)
    bpy.data.cameras.remove(cam)
    print('rendered', path)


def one_rocket(name):
    obs, b = R.rocket(name)
    shoot(os.path.join(R.OUT, 'rk_%s.png' % name), obs, (900, 2400), azimuth=-28.0, elevation=4.0, fov=12.0, look=0.5)
    R.clear(obs, [b])


def lineup():
    b = K.builder(seed=3)
    x = 0.0
    for name in reversed(ROCKETS):          # mirrored like the game: Sputnik ends up on the left, the N1 on the right
        K.place(b, R.rocket_fns()[name], center=(x, 0.0, 0.0))
        x += 22.0
    obs = b.preview_objects(R.BMATS, 'lineup')
    shoot(os.path.join(R.OUT, 'lineup.png'), obs, (2000, 2000), azimuth=-12.0, elevation=3.0, fov=16.0, look=0.5)
    R.clear(obs, [b])


# kit buildings as dioramas on their own lots, like the game's building icons: azimuth, elevation, look
DIORAMAS = {'pad_r7': (-35.0, 26.0, 0.34), 'mik': (-32.0, 30.0, 0.45), 'tracking': (-35.0, 30.0, 0.45),
            'monument': (-30.0, 14.0, 0.5)}


def diorama(key):
    obs, _bbox = R.building(key)
    extra, bs = [], []
    if key == 'pad_r7':
        extra, b = R.rocket('vostok', y=R.deck(key))
        bs.append(b)
    az, el, look = DIORAMAS[key]
    shoot(os.path.join(R.OUT, 'b_%s.png' % key), obs + extra, (2000, 2000), azimuth=az, elevation=el, fov=24.0,
          margin=1.02, look=look, samples=64)
    R.clear(obs + extra, bs)


def main():
    os.makedirs(R.OUT, exist_ok=True)
    mmkit.clear_scene()
    R.BMATS = mmkit.blender_materials(R.TEXDIR, MATS)
    sun = mmkit.lighting(sun_energy=6.5)
    sun.rotation_euler = (math.radians(58), math.radians(8), math.radians(-70))    # light from the viewer's left
    bg = bpy.context.scene.world.node_tree.nodes.get('Background')
    bg.inputs[1].default_value = 0.35                     # less ambient: a clear lit and shaded side, poster-like
    vs = bpy.context.scene.view_settings
    vs.view_transform = 'Standard'
    vs.look = 'None'
    only = set(R.argv[3].split(',')) if len(R.argv) > 3 and R.argv[3] else None
    for name in ROCKETS:
        if not only or name in only:
            one_rocket(name)
    if not only or 'lineup' in only:
        lineup()
    for key in DIORAMAS:
        if not only or key in only:
            diorama(key)


main()
