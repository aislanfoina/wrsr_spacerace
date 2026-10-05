"""Space Race kit: the buildings of the Soviet space programme.

    blender -b --python tools/space_scene.py -- <texdir> <kitdir> <previewdir> [only,keys]

Every model follows a real site (dimensions in metres, simplified):
    pad_r7        Gagarin's Start, Baikonur Site 1 (R-7 pad, flame duct, tulip arms)
    pad_n1        Baikonur Site 110 (N1 pad: 145 m gantry, 180 m lightning towers)
    mik           the assembly and testing building (MIK) with its rail gates
    rocket_plant  the Progress plant at Kuibyshev (stage production)
    engine_plant  Glushko's OKB-456 engine works
    test_stand    a vertical engine test stand (NII-229 Zagorsk)
    lox_plant     the oxygen-nitrogen plant
    propellant    a hypergolic propellant plant (UDMH / N2O4)
    instruments   an instrument / avionics works
    spacecraft    the spacecraft assembly hall with its vacuum chamber
    tracking      the Pluton deep space antenna (eight 16 m dishes)
    training      the cosmonaut training centre (Star City, TsF-18 centrifuge)
    bureau        the design bureau (OKB-1, Podlipki)
    recovery      a landing and recovery field with a Vostok capsule
    monument      the Monument to the Conquerors of Space (107 m)
    gagarin       the Gagarin column

Every building is written twice. building.ini uses vanilla stand-ins for the six
new goods (lox and hypergolic propellant as chemicals, rocket parts as mechanical
components, avionics and spacecraft as electronics), so the kit loads in any save
and without the plugins. mod/plugins/spacerace/data/goods_buildings/sr_<key>.ini
has the new goods; the spacerace plugin serves it in place of building.ini when
spacerace.ini says new_goods = 1.

    blender -b --python tools/space_scene.py -- <texdir> <kitdir> <previewdir> "" inis
writes only those building files (no models, no renders).
"""
import math
import os
import shutil
import sys

import bpy
import bmesh

TOOLS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TOOLS)
import nmf  # noqa: E402
import mmkit  # noqa: E402
import srkit as K  # noqa: E402
from srkit import (CONC, SCORCH, WHITE, GREY, GREEN, RED, STRIPES, GLASS, STUCCO, BRICK, ROOF, ASPH,  # noqa: E402
                   GROUND, METAL, DARK, GLOW, CORR, HAZARD, TITAN, FROST, BLUE)
from space_palette import MATS, EMISSIVE  # noqa: E402

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
TEXDIR = argv[0] if len(argv) > 0 else 'build/space_textures'
KITDIR = argv[1] if len(argv) > 1 else 'mod/buildings/space_kit'
PREVIEW = argv[2] if len(argv) > 2 else 'build/space'
ONLY = set(argv[3].split(',')) if len(argv) > 3 and argv[3] else None
INIS_ONLY = len(argv) > 4 and argv[4] == 'inis'
from space_workshop import ITEMS, VISIBILITY  # noqa: E402
ITEM_ID = ITEMS['kit'][1]
import space_goods as G  # noqa: E402  (shared with space_scenario.py; G.USE_NEW_GOODS picks the variant being written)
from space_goods import CLASS, good  # noqa: E402
GOODS_INIS = os.path.join(os.path.dirname(TOOLS), 'mod', 'plugins', 'spacerace', 'data', 'goods_buildings')


# =================================================================== pads ==

def pad_r7(b):
    """Gagarin's Start. The R-7 hangs in the launch system's four arms over a flame
    duct; here the pit is a raised deck (terrain covers anything below ground) with
    the duct opening to +x onto a scorched apron."""
    K.lot(b, CONC, 120, 96, cx=0)
    H = 6.0
    # the deck around a 9 x 9 m opening, the duct running out to +x under a roof slab
    K.slab(b, CONC, -24, -18, -4.5, 18, 0, H)
    K.slab(b, CONC, -4.5, -18, 4.5, -4.5, 0, H); K.slab(b, CONC, -4.5, 4.5, 4.5, 18, 0, H)
    K.slab(b, CONC, 4.5, -18, 24, -6.5, 0, H); K.slab(b, CONC, 4.5, 6.5, 24, 18, 0, H)
    K.slab(b, CONC, 4.5, -6.5, 24, 6.5, 4.2, H)
    for (x0, z0, x1, z1) in ((-4.5, -4.5, 4.5, -4.3), (-4.5, 4.3, 4.5, 4.5), (-4.5, -4.5, -4.3, 4.5), (4.5, -6.5, 24, -6.3), (4.5, 6.3, 24, 6.5)):
        K.slab(b, SCORCH, x0, z0, x1, z1, 0, H - 0.05)
    K.slab(b, SCORCH, -4.5, -6.5, 24, 6.5, 0, 0.25)
    b.box(SCORCH, (1.5, 2.2, 0), (7.0, 0.5, 8.6), roll=-32)          # the deflector wedge under the rocket
    K.slab(b, SCORCH, 24, -14, 58, 14, 0, 0.2)                     # blackened apron where the flame leaves
    K.slab(b, CONC, -24.3, -18.3, 24.3, 18.3, H, H + 0.3)
    K.slab(b, SCORCH, -4.5, -4.5, 4.5, 4.5, H - 0.1, H + 0.35)
    # launch system: the ring, four counterweighted support arms swung open, the cable mast
    b.torus(GREY, (0, H + 0.6, 0), 5.8, 0.45, segs=24, rings=6)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        ca, sa = math.cos(a), math.sin(a)
        K.lattice_girder(b, GREY, (5.6 * ca, H + 0.8, 5.6 * sa), (7.6 * ca, H + 16.0, 7.6 * sa), 1.2, 0.9, n=6, beam=0.12)
        b.box(DARK, (8.0 * ca, H + 16.3, 8.0 * sa), (1.6, 1.0, 1.6), yaw=-math.degrees(a))
        b.box(GREY, (6.6 * ca, H + 1.4, 6.6 * sa), (2.4, 2.2, 2.0), yaw=-math.degrees(a))      # counterweight
    # two service towers in their working position, platforms reaching in
    for s in (-1, 1):
        zc = s * 12.5
        K.lattice_column(b, GREY, (0, H, zc), 6.0, 3.6, 44.0, levels=11, beam=0.22, legs_mat=RED)
        for k in range(1, 9):
            y = H + 4.5 * k
            K.slab(b, GREY, -3.0, zc - s * 2.2, 3.0, zc - s * 6.4, y, y + 0.3)
            b.rod(METAL, (-3.0, y + 1.1, zc - s * 6.4), (3.0, y + 1.1, zc - s * 6.4), 0.05, segs=4)
        K.slab(b, WHITE, -2.6, zc - 1.6, 2.6, zc + 1.6, H + 44.0, H + 47.0)
        K.star(b, (0, H + 45.5, zc + s * 1.65), 1.2, depth=0.2, yaw=0 if s > 0 else 180)
    K.lattice_column(b, GREEN, (-11.0, H, 0), 2.6, 1.6, 34.0, levels=9, beam=0.18)
    K.lattice_girder(b, GREEN, (-10.0, H + 32.0, 0), (-2.0, H + 30.5, 0), 1.0, 0.8, n=6, beam=0.1)
    K.pipe(b, METAL, [(-10.5, H + 30.0, 0.5), (-2.4, H + 28.5, 0.5)], 0.15)
    K.lattice_column(b, GREEN, (-8.0, H, -8.5), 2.0, 1.4, 20.0, levels=5, beam=0.16)
    # rail line up an embankment ramp from -x: the transporter-erector's way in
    K.wedge(b, CONC, -64.0, -24.0, H, -4.5, 4.5)
    for s in (-1, 1):
        b.box(METAL, (-44.0, H / 2 + 0.1, s * 0.76), (40.5, 0.16, 0.08), roll=math.degrees(math.atan2(H, 40.0)))
    K.slab(b, METAL, -24.0, -0.84, -4.6, -0.68, H + 0.3, H + 0.46); K.slab(b, METAL, -24.0, 0.68, -4.6, 0.84, H + 0.3, H + 0.46)
    # propellants: two LOX tanks, a kerosene tank, the pipes to the deck
    K.tank_h(b, FROST, (34.0, 2.3, 30.0), 2.0, 16.0); K.tank_h(b, FROST, (34.0, 2.3, 36.0), 2.0, 16.0)
    K.tank_v(b, GREY, (-40.0, 0, 30.0), 4.0, 9.0)
    K.pipe_rack(b, 22.0, 30.0, 22.0, 18.5, h=4.0, n=3); K.pipe_rack(b, -34.0, 30.0, -24.0, 20.0, h=4.0, n=2)
    # command bunker: a grassed mound with its concrete head and periscopes
    b.box(GROUND, (-40.0, 2.0, -32.0), (20.0, 4.0, 14.0), pitch=0)
    b.box(GROUND, (-40.0, 3.0, -32.0), (14.0, 2.0, 9.0))
    K.slab(b, CONC, -33.0, -27.0, -29.5, -24.0, 0, 3.2); b.box(DARK, (-31.2, 1.2, -23.95), (1.8, 2.2, 0.1))
    for dx in (-2.0, 2.0):
        b.rod(DARK, (-40.0 + dx, 4.0, -32.0), (-40.0 + dx, 6.0, -32.0), 0.2, segs=6)
    # lightning masts and floodlights at the corners
    for x, z in ((-30, -28), (30, -28), (30, 26), (-30, 20)):
        K.lattice_column(b, STRIPES, (x, 0, z), 2.4, 0.6, 52.0, levels=12, beam=0.14)
        b.rod(METAL, (x, 52.0, z), (x, 58.0, z), 0.08, segs=4)
    K.lamp_mast(b, -52.0, 40.0, h=26.0); K.lamp_mast(b, 52.0, -40.0, h=26.0)
    K.flagpole(b, -12.0, 42.0)
    b.fire += [(34.0, 2.5, 30.0), (-40.0, 5.0, 30.0)]
    return 'Launch Complex (R-7)'


def pad_n1(b):
    """Site 110: the N1 stood on a launch table over a three-way flame deflector;
    a 145 m gantry rolled round on a circular rail, four 180 m lightning towers."""
    K.lot(b, CONC, 200, 180, cx=0)
    H = 14.0
    # the plateau, cut by three roofed flame trenches (+x, -z, +z)
    K.slab(b, CONC, -42, -42, -10, 42, 0, H)
    K.slab(b, CONC, 10, -42, 42, -8, 0, H); K.slab(b, CONC, 10, 8, 42, 42, 0, H)
    K.slab(b, CONC, -10, -42, 10, -10, 0, H); K.slab(b, CONC, -10, 10, 10, 42, 0, H)
    K.slab(b, CONC, 10, -8, 42, 8, 9.0, H)
    for (x0, z0, x1, z1) in ((-10, -10, 10, -9.8), (-10, 9.8, 10, 10), (-10, -10, -9.8, 10), (10, -8, 42, -7.8), (10, 7.8, 42, 8)):
        K.slab(b, SCORCH, x0, z0, x1, z1, 0, H - 0.05)
    K.slab(b, SCORCH, -10, -10, 42, 10, 0, 0.3)
    b.box(SCORCH, (0, 4.0, 0), (16.0, 0.8, 16.0), roll=-28)
    K.slab(b, SCORCH, 42, -20, 96, 20, 0, 0.2)
    K.slab(b, CONC, -42.3, -42.3, 42.3, 42.3, H, H + 0.4)
    # launch table: a ring on columns round the 20 m opening
    b.torus(GREY, (0, H + 3.2, 0), 9.4, 0.8, segs=36, rings=6)
    for k in range(24):
        a = 2 * math.pi * k / 24
        b.rod(GREY, (10.2 * math.cos(a), H, 10.2 * math.sin(a)), (9.4 * math.cos(a), H + 3.0, 9.4 * math.sin(a)), 0.35, segs=6)
    # the rotating service gantry parked on its circular rail
    tx, tz = -70.0, -40.0
    K.lattice_column(b, GREY, (tx, 0, tz), 22.0, 14.0, 145.0, levels=29, beam=0.35, legs_mat=RED)
    for k in range(6):
        y = 20.0 + k * 20.0
        K.slab(b, WHITE, tx - 6.0, tz + 4.0, tx + 6.0, tz + 14.0, y, y + 9.0)
        b.box(GLASS, (tx, y + 5.4, tz + 14.05), (10.0, 3.6, 0.1))
    K.lattice_girder(b, GREY, (tx, 142.0, tz), (tx + 26.0, 138.0, tz + 22.0), 3.0, 3.0, n=10, beam=0.2)
    for a in range(0, 100, 6):
        r = 81.0
        aa = math.radians(180 + a - 30)
        b.box(METAL, (r * math.cos(aa), 0.25, r * math.sin(aa)), (6.0, 0.3, 0.3), yaw=-math.degrees(aa) + 90)
    # four lightning towers
    for x, z in ((-80, -75), (80, -75), (80, 75), (-80, 75)):
        K.lattice_column(b, STRIPES, (x, 0, z), 6.0, 1.6, 180.0, levels=30, beam=0.22)
        b.rod(METAL, (x, 180.0, z), (x, 190.0, z), 0.12, segs=4)
    # the double track of the N1 transporter-erector climbing to the table
    ang = math.degrees(math.atan2(H, 55.0))
    K.wedge(b, CONC, -97.0, -42.0, H, -14.0, 14.0)
    for zz in (-9.0, -7.5, 7.5, 9.0):
        b.box(METAL, (-69.5, H / 2 + 0.1, zz), (56.5, 0.18, 0.1), roll=ang)
        K.slab(b, METAL, -42.0, zz - 0.05, -11.0, zz + 0.05, H + 0.4, H + 0.58)
    # propellant farm: three LOX spheres, kerosene tanks, pipes up the plateau
    for k, z in enumerate((40.0, 58.0, 76.0)):
        K.sphere_tank(b, FROST, (72.0, 8.0, z), 7.0)
    K.tank_v(b, GREY, (60.0, 0, -58.0), 8.0, 14.0); K.tank_v(b, GREY, (82.0, 0, -58.0), 8.0, 14.0)
    K.pipe_rack(b, 62.0, 40.0, 42.0, 30.0, h=6.0, n=4); K.pipe_rack(b, 62.0, -48.0, 42.0, -30.0, h=6.0, n=3)
    K.lamp_mast(b, 60.0, 0.0, h=40.0, head=5.0); K.lamp_mast(b, -30.0, 70.0, h=40.0, head=5.0); K.lamp_mast(b, 30.0, -70.0, h=40.0, head=5.0)
    b.box(GROUND, (40.0, 2.5, 72.0), (22.0, 5.0, 14.0))
    K.slab(b, CONC, 30.0, 62.0, 34.0, 66.0, 0, 3.4); b.box(DARK, (32.0, 1.4, 66.05), (2.0, 2.4, 0.1))
    b.fire += [(72.0, 8.0, 40.0), (60.0, 10.0, -58.0)]
    return 'Heavy Launch Complex (N1)'


# ============================================================ assembly ==

def mik(b):
    K.lot(b, ASPH, 190, 80, cx=10.0)
    K.hall(b, -62, -20, 62, 16, 30.0, wall=CONC, roof=ROOF, kind='flat', plinth=CONC)
    K.hall(b, -62, 16, 30, 30, 16.0, wall=CONC, roof=ROOF, kind='flat', plinth=CONC)
    K.block(b, 30, 16, 62, 34, 4, wall=GLASS)
    for x in range(-56, 60, 8):                                  # pilasters on the high bay
        K.slab(b, CONC, x - 0.5, -20.6, x + 0.5, -20.0, 1.8, 30.0)
    for e in (-1, 1):
        K.door(b, e * 62.15, -2.0, 14.0, 22.0, facing='x')
        K.slab(b, GREY, e * 62.1 - 0.3, -10.0, e * 62.1 + 0.3, 6.0, 22.0, 23.0)
    for x in range(-50, 51, 20):
        K.slab(b, GREY, x - 4, -12, x + 4, 8, 30.4, 32.4)
    K.sign(b, 'МИК', (-20.0, 17.5, 30.15), 5.0, board=(22.0, 6.5, WHITE))
    K.star(b, (5.0, 20.0, 30.2), 2.4)
    for x0, x1 in ((-85.0, -62.0), (62.0, 104.0)):
        K.rail_track(b, x0, -2.0, x1, -2.0)
    K.rail_track(b, -62.0, -2.0, 62.0, -2.0, sleepers=False)
    # an R-7 waiting on its transporter-erector outside the east gate
    K.slab(b, GREEN, 64.0, -3.6, 100.0, -0.4, 0.6, 1.6)
    for x in (66.0, 70.0, 88.0, 92.0, 96.0):
        for zz in (-3.3, -0.7):
            b.torus(DARK, (x, 0.8, zz), 0.45, 0.14, segs=10, rings=5, axis='z')
    K.lattice_girder(b, GREEN, (64.5, 3.2, -2.0), (100.0, 3.2, -2.0), 3.0, 1.2, n=14, beam=0.1)
    K.place(b, K.rocket_r7, center=(63.5, 4.6, -2.0), yaw=90, pitch=90, variant='vostok')
    K.lamp_mast(b, 0.0, -34.0, h=22.0)
    b.fire += [(40.0, 6.0, 25.0)]
    return 'Assembly and Testing Building (MIK)'


# ============================================================ industry ==

def rocket_plant(b):
    K.lot(b, ASPH, 170, 110, cx=0)
    K.hall(b, -70, -45, 30, 14, 16.0, wall=CORR, kind='sawtooth', axis='x')
    K.hall(b, 30, -45, 70, 14, 26.0, wall=CONC, kind='gable', axis='z', ridge=5.0)
    K.door(b, 50.0, 14.2, 16.0, 18.0)
    K.block(b, -70, 24, -24, 40, 4, wall=STUCCO)
    for x in range(-66, -26, 5):
        b.cyl(CONC, (x, 0, 41.0), 0.5, 7.2, segs=10)
    K.slab(b, CONC, -68, 40, -26, 42.5, 7.2, 8.0)
    K.sign(b, 'ПРОГРЕСС', (-47.0, 15.2, 40.1), 2.6, board=(26.0, 3.6, WHITE))
    K.star(b, (-47.0, 19.5, 40.2), 1.8)
    b.cyl(BRICK, (60.0, 0, 34.0), 2.4, 42.0, segs=14, r2=1.5); b.torus(STRIPES, (60.0, 40.0, 34.0), 1.62, 0.25, segs=14, rings=4)
    b.fire.append((60.0, 42.0, 34.0))
    b.cyl(GREY, (-80.0 + 12, 0, -30.0), 0.6, 22.0, segs=8); b.cyl(GREY, (-68.0, 22.0, -30.0), 4.0, 5.0, segs=16, r2=4.2)
    # a finished core stage on its road trailer
    K.slab(b, GREEN, 0.0, 22.0, 30.0, 26.0, 0.8, 1.5)
    K.place(b, lambda t: K._stage(t, WHITE, 0, 26.0, 1.475, 1.2) or K._nozzles(t, 0, 0, 0, 4, 0.65, 0.42, 1.8),
            center=(1.0, 3.1, 24.0), yaw=90, pitch=90)
    K.lamp_mast(b, 0.0, -52.0, h=18.0); K.flagpole(b, -20.0, 48.0)
    return 'Rocket Plant (Progress)'


def engine_plant(b):
    K.lot(b, ASPH, 120, 90, cx=0)
    K.hall(b, -50, -38, 0, 10, 14.0, wall=BRICK, kind='gable', axis='x', ridge=4.0)
    K.hall(b, 0, -38, 40, 10, 18.0, wall=CORR, kind='barrel', axis='x', ridge=5.0)
    K.block(b, -50, 18, -10, 32, 3, wall=GLASS)
    K.sign(b, 'ОКБ-456', (-30.0, 11.6, 32.12), 2.4, board=(20.0, 3.2, WHITE))
    # test cell with its sound-suppressed exhaust stack
    K.slab(b, CONC, 42, -30, 56, -10, 0, 12.0)
    b.cyl(CONC, (49.0, 12.0, -20.0), 4.0, 22.0, segs=18, r2=3.4); b.cyl(GREY, (49.0, 34.0, -20.0), 3.6, 2.0, segs=18, r2=3.8)
    b.fire.append((49.0, 34.0, -20.0))
    K.tank_v(b, WHITE, (30.0, 0, 26.0), 3.0, 10.0); K.sphere_tank(b, FROST, (42.0, 6.0, 26.0), 4.5)
    # an RD-107 on a plinth by the gate: four chambers and two verniers
    K.slab(b, CONC, -5.0, 24.0, 1.0, 30.0, 0, 1.2)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        b.cyl(DARK, (-2.0 + 0.7 * math.cos(a), 1.2, 27.0 + 0.7 * math.sin(a)), 0.55, 2.0, segs=12, r2=0.32)
        b.cyl(METAL, (-2.0 + 0.7 * math.cos(a), 3.2, 27.0 + 0.7 * math.sin(a)), 0.32, 1.0, segs=10)
    b.cyl(GREY, (-2.0, 4.2, 27.0), 1.3, 1.6, segs=12)
    K.lamp_mast(b, 20.0, -44.0, h=18.0)
    return 'Rocket Engine Works (OKB-456)'


def test_stand(b):
    K.lot(b, CONC, 100, 100, cx=0)
    # the concrete tower with the stage in its steel frame, flame channel out to +x
    K.slab(b, CONC, -14, -12, 14, -4, 0, 42.0); K.slab(b, CONC, -14, 4, 14, 12, 0, 42.0)
    K.slab(b, CONC, -14, -4, -4, 4, 0, 42.0)
    K.slab(b, CONC, -4, -4, 14, 4, 18.0, 42.0)
    K.slab(b, SCORCH, -4, -4, 14, -3.8, 0, 18.0); K.slab(b, SCORCH, -4, 3.8, 14, 4, 0, 18.0); K.slab(b, SCORCH, -4, -4, 14, 4, 0, 0.3)
    b.box(SCORCH, (8.0, 9.0, 0), (14.0, 0.6, 8.0), roll=-40)
    K.slab(b, SCORCH, 14, -10, 48, 10, 0, 0.2)
    K.lattice_column(b, GREY, (0, 42.0, 0), 10.0, 10.0, 24.0, levels=6, beam=0.25)
    K._stage(b, WHITE, 44.0, 64.0, 3.0, 3.0)
    b.cyl(DARK, (0, 41.0, 0), 3.0, 3.0, segs=18, r2=2.2)
    K.lattice_girder(b, GREY, (-4.0, 66.0, 0), (22.0, 66.0, 0), 2.0, 2.0, n=10, beam=0.14)
    K.slab(b, GREY, -6, -6, 6, 6, 66.0, 67.0)
    # propellant, cooling water, the control bunker with its slit windows
    K.sphere_tank(b, FROST, (-30.0, 7.0, -30.0), 6.0); K.tank_v(b, GREY, (-32.0, 0, 28.0), 5.0, 12.0)
    b.cyl(CONC, (30.0, 0, 34.0), 1.0, 20.0, segs=8); b.cyl(GREY, (30.0, 20.0, 34.0), 5.0, 6.0, segs=16)
    K.pipe_rack(b, -24.0, -30.0, -14.0, -8.0, h=5.0, n=2)
    b.box(GROUND, (-36.0, 2.5, 0.0), (18.0, 5.0, 26.0))
    K.slab(b, CONC, -28.0, -6.0, -26.0, 6.0, 0, 4.4)
    b.box(DARK, (-25.95, 3.2, 0.0), (0.1, 0.5, 9.0))
    for x, z in ((-40, -44), (40, -44), (40, 44)):
        K.lattice_column(b, STRIPES, (x, 0, z), 2.2, 0.6, 60.0, levels=14, beam=0.14)
    return 'Engine Test Stand'


def lox_plant(b):
    K.lot(b, ASPH, 100, 80, cx=0)
    K.hall(b, -44, -32, 0, 0, 12.0, wall=CORR, kind='gable', axis='x', ridge=3.0)
    for k in range(3):
        x = 10.0 + k * 9.0
        K.slab(b, WHITE, x - 3.0, -28.0, x + 3.0, -20.0, 0, 32.0)
        K.slab(b, GREY, x - 3.2, -28.2, x + 3.2, -19.8, 32.0, 33.0)
        b.rod(METAL, (x, 33.0, -24.0), (x, 38.0, -24.0), 0.25, segs=8)
        b.cyl(METAL, (x + 4.2, 0, -24.0), 1.1, 26.0, segs=14)
    K.pipe_rack(b, 0.0, -10.0, 36.0, -10.0, h=6.0, n=4)
    for k, z in enumerate((6.0, 22.0)):
        K.sphere_tank(b, FROST, (30.0, 6.0, z), 5.5)
    K.tank_h(b, FROST, (6.0, 2.3, 22.0), 2.0, 14.0); K.tank_h(b, FROST, (6.0, 2.3, 28.0), 2.0, 14.0)
    # a small cooling tower
    b.cyl(CONC, (-30.0, 0, 24.0), 9.0, 10.0, segs=24, r2=6.5); b.cyl(CONC, (-30.0, 10.0, 24.0), 6.5, 8.0, segs=24, r2=7.4)
    b.cyl(DARK, (-30.0, 17.8, 24.0), 7.2, 0.2, segs=24)
    K.block(b, -44, 6, -24, 14, 2, wall=GLASS)
    K.sign(b, 'КИСЛОРОД', (-34.0, 7.6, 14.12), 1.4, board=(14.0, 2.0, WHITE))
    return 'Oxygen-Nitrogen Plant'


def propellant(b):
    K.lot(b, ASPH, 110, 90, cx=0)
    cols = [(-30.0, -24.0, 2.2, 34.0), (-20.0, -24.0, 1.8, 28.0), (-10.0, -24.0, 2.6, 38.0), (0.0, -24.0, 1.6, 24.0), (10.0, -26.0, 2.0, 30.0)]
    for x, z, r, h in cols:
        b.cyl(GREY, (x, 0, z), r, h, segs=16)
        b.cyl(GREY, (x, h, z), r, r * 0.5, segs=16, r2=r * 0.3)
        for k in range(1, int(h / 6)):
            b.torus(METAL, (x, k * 6.0, z), r + 0.5, 0.08, segs=16, rings=4)
            K.slab(b, GREY, x - r - 1.0, z - 0.6, x - r, z + 0.6, k * 6.0 - 0.1, k * 6.0)
    K.lattice_column(b, GREY, (-10.0, 0, -24.0), 30.0, 30.0, 18.0, levels=4, beam=0.2, diag=False)
    # the bunded tank farm: UDMH and nitrogen tetroxide, hazard striped
    K.slab(b, CONC, 14.0, 4.0, 48.0, 38.0, 0, 1.4)
    K.slab(b, CONC, 15.0, 5.0, 47.0, 37.0, 0, 1.45)
    for k, (x, z) in enumerate(((22.0, 12.0), (38.0, 12.0), (22.0, 29.0), (38.0, 29.0))):
        K.tank_v(b, WHITE if k % 2 == 0 else GREY, (x, 0, z), 5.5, 11.0)
        b.cyl(HAZARD, (x, 1.0, z), 5.55, 0.8, segs=18)
    K.sphere_tank(b, GREY, (-34.0, 6.0, 20.0), 5.0); K.sphere_tank(b, GREY, (-20.0, 6.0, 20.0), 5.0)
    K.pipe_rack(b, -30.0, 6.0, 14.0, 6.0, h=6.0, n=4); K.pipe_rack(b, 0.0, -12.0, 0.0, 6.0, h=6.0, n=3)
    b.rod(GREY, (44.0, 0, -30.0), (44.0, 44.0, -30.0), 0.6, segs=8); b.cyl(GLOW, (44.0, 44.0, -30.0), 0.7, 1.2, segs=8)
    for k in range(3):
        b.beam(GREY, (44.0, 10.0 + k * 12, -30.0), (40.0, 0, -34.0 + k * 3), 0.12)
    b.fire.append((44.0, 45.0, -30.0))
    K.block(b, -48, 26, -30, 40, 2, wall=BRICK)
    K.sign(b, 'ГЕПТИЛ', (-39.0, 7.8, 40.12), 1.4, board=(12.0, 2.0, HAZARD))
    b.fire += [(22.0, 11.0, 12.0), (38.0, 11.0, 29.0)]
    return 'Propellant Plant (UDMH / N2O4)'


def instruments(b):
    K.lot(b, ASPH, 96, 70, cx=0)
    K.block(b, -44, 6, 14, 24, 5, wall=GLASS)
    K.hall(b, -44, -30, 44, 2, 10.0, wall=WHITE, kind='sawtooth', axis='x', plinth=CONC)
    K.slab(b, CONC, 14, 6, 44, 18, 0, 7.2)
    K.sign(b, 'НИИ', (-15.0, 18.2, 24.12), 3.0, board=(12.0, 4.0, WHITE))
    K.dish(b, (0.0, 19.0, 15.0), 5.0, elev=40.0, az=180)
    for x in (-40.0, -20.0):
        b.rod(METAL, (x, 18.25, 20.0), (x, 30.0, 20.0), 0.1, segs=4)
    K.lamp_mast(b, 40.0, 30.0, h=16.0)
    return 'Instrument Works'


def spacecraft(b):
    K.lot(b, ASPH, 90, 70, cx=0)
    K.hall(b, -30, -28, 18, 12, 24.0, wall=CONC, kind='flat', plinth=CONC)
    K.door(b, -6.0, 12.2, 16.0, 18.0)
    K.block(b, 18, -10, 40, 12, 3, wall=GLASS)
    # thermal vacuum chamber
    K.tank_h(b, METAL, (28.0, 5.8, -22.0), 5.0, 18.0)
    b.cyl(DARK, (37.2, 5.8, -22.0), 5.1, 0.5, segs=16, pitch=90, yaw=90)
    # a Vostok on its display stand, a Soyuz orbital module on a trailer
    K.slab(b, CONC, -36.0, 18.0, -26.0, 28.0, 0, 1.0)
    K.vostok_capsule(b, (-31.0, 3.4, 23.0))
    K.slab(b, GREEN, 4.0, 20.0, 16.0, 24.0, 0.8, 1.4)
    K.sphere(b, GREEN, (10.0, 2.9, 22.0), 1.4, segs=14, rings=8)
    K.sign(b, 'КОСМОС', (-6.0, 20.6, 12.15), 2.2, board=(18.0, 3.2, WHITE))
    K.star(b, (-6.0, 25.5, 12.2), 1.6)
    return 'Spacecraft Assembly Hall'


# ============================================================= science ==

def tracking(b):
    """Pluton (ADU-1000): eight 16 m dishes on a bridge-truss frame, on a turret."""
    K.lot(b, GROUND, 100, 80, cx=0)
    e = 35.0
    C = (0.0, 26.0, -8.0)
    bore = (0.0, math.sin(math.radians(e)), math.cos(math.radians(e)))
    up = (0.0, math.cos(math.radians(e)), -math.sin(math.radians(e)))

    def at(dx, dv, db=0.0):
        return (C[0] + dx, C[1] + up[1] * dv + bore[1] * db, C[2] + up[2] * dv + bore[2] * db)
    cols = (-25.5, -8.5, 8.5, 25.5)
    rows = (-8.5, 8.5)
    for dx in cols:
        for dv in rows:
            K.dish(b, at(dx, dv, 0.2), 16.0, elev=e, az=0, depth=0.12, mat=WHITE, segs=20, rings=4)
    for dv in rows:
        K.lattice_girder(b, GREY, at(-34.0, dv, -1.5), at(34.0, dv, -1.5), 2.2, 2.2, n=16, beam=0.16)
    for dx in cols:
        K.lattice_girder(b, GREY, at(dx, -9.0, -1.5), at(dx, 9.0, -1.5), 1.8, 1.8, n=4, beam=0.14)
    K.lattice_girder(b, GREY, at(-20.0, 0, -4.0), at(20.0, 0, -4.0), 3.0, 3.0, n=10, beam=0.2)   # the elevation axle
    # the turret: a gun-mount ring on a concrete drum, A-frames up to the axle
    b.cyl(CONC, (0, 0, -8.0), 9.0, 6.0, segs=28); b.cyl(GREY, (0, 6.0, -8.0), 8.0, 2.4, segs=28)
    ax = at(0, 0, -4.0)
    for sx in (-14.0, 14.0):
        for dz in (-5.0, 5.0):
            b.beam(GREY, (sx * 0.5, 8.4, -8.0 + dz), (sx, ax[1], ax[2]), 0.8)
    # the control building, a service dish and masts
    K.block(b, -44, 18, -12, 34, 2, wall=BRICK)
    K.sign(b, 'ПЛУТОН', (-28.0, 7.6, 34.12), 1.8, board=(16.0, 2.6, WHITE))
    b.cyl(CONC, (30.0, 0, 26.0), 1.8, 7.0, segs=12)
    K.dish(b, (30.0, 8.0, 26.0), 7.0, elev=55.0, az=150, depth=0.14)
    for x, z in ((-46, -34), (46, -34)):
        K.lattice_column(b, STRIPES, (x, 0, z), 1.6, 0.5, 36.0, levels=9, beam=0.12)
    return 'Deep Space Tracking Station (Pluton)'


def training(b):
    K.lot(b, GROUND, 110, 90, cx=0)
    K.block(b, -50, 8, 8, 26, 4, wall=GLASS)
    K.sign(b, 'ЦПК', (-21.0, 15.0, 26.12), 3.0, board=(12.0, 4.0, WHITE))
    # the TsF-18 centrifuge: a round hall with a shallow dome
    b.cyl(CONC, (28.0, 0, -14.0), 22.0, 14.0, segs=40)
    K.dome(b, METAL, (28.0, 14.0, -14.0), 22.0, h=6.5, segs=40, rings=6)
    b.torus(GREY, (28.0, 14.0, -14.0), 22.0, 0.35, segs=40, rings=4)
    for k in range(12):
        a = 2 * math.pi * k / 12
        b.box(GLASS, (28.0 + 22.05 * math.cos(a), 10.8, -14.0 + 22.05 * math.sin(a)), (0.1, 3.6, 5.0), yaw=-math.degrees(a))
    # hydro laboratory under a barrel roof, the sports field
    K.hall(b, -50, -38, -8, -12, 10.0, wall=BRICK, kind='barrel', axis='x', ridge=4.0)
    K.slab(b, GREEN, -4.0, 30.0, 40.0, 44.0, 0, 0.18)
    for x in (-3.5, 39.5):
        b.rod(WHITE, (x, 0, 35.0), (x, 2.4, 35.0), 0.06, segs=4); b.rod(WHITE, (x, 0, 39.0), (x, 2.4, 39.0), 0.06, segs=4)
        b.rod(WHITE, (x, 2.4, 35.0), (x, 2.4, 39.0), 0.06, segs=4)
    # Gagarin, walking forward, on a granite plinth
    gx, gz = -20.0, 38.0
    K.slab(b, DARK, gx - 2.5, gz - 2.5, gx + 2.5, gz + 2.5, 0, 3.0)
    for s in (-1, 1):
        b.cyl(TITAN, (gx + s * 0.3, 3.0, gz + s * 0.25), 0.28, 2.2, segs=8, r2=0.24)
    b.box(TITAN, (gx, 6.0, gz), (1.2, 2.0, 0.7)); K.sphere(b, TITAN, (gx, 7.5, gz), 0.45, segs=10, rings=8)
    b.box(TITAN, (gx + 0.9, 6.5, gz + 0.2), (0.3, 1.6, 0.3), roll=-35)
    b.box(TITAN, (gx - 0.9, 6.5, gz + 0.2), (0.3, 1.6, 0.3), roll=20)
    K.flagpole(b, 8.0, 36.0)
    return 'Cosmonaut Training Centre'


def bureau(b):
    K.lot(b, ASPH, 84, 56, cx=0)
    K.block(b, -36, -14, 36, 6, 5, wall=STUCCO)
    K.block(b, -9, -14, 9, 6, 7, wall=STUCCO)
    for x in range(-7, 8, 2):
        b.cyl(CONC, (x, 0, 7.6), 0.55, 10.8, segs=10)
    K.slab(b, CONC, -8.5, 6.0, 8.5, 9.0, 10.8, 12.0)
    K.sign(b, 'ОКБ-1', (0.0, 12.6, 9.05), 2.2, board=(12.0, 3.0, STUCCO))
    K.star(b, (0.0, 27.6, -4.0), 2.2)
    b.rod(METAL, (0, 25.5, -4.0), (0, 26.3, -4.0), 0.3, segs=6)
    # Sputnik on its column in the forecourt (shown at three times life size)
    K.slab(b, DARK, -2.0, 16.0, 2.0, 20.0, 0, 5.0)
    K.sphere(b, METAL, (0.0, 6.4, 18.0), 1.4, segs=16, rings=10)
    for k in range(4):
        a = math.radians(45 + 90 * k)
        # the four whip antennas sweep back from the sphere
        b.rod(METAL, (0.9 * math.cos(a), 6.4 + 0.9 * math.sin(a), 17.0), (2.0 * math.cos(a), 6.4 + 2.0 * math.sin(a), 10.5), 0.05, segs=4)
    K.flagpole(b, -24.0, 20.0); K.flagpole(b, 24.0, 20.0)
    return 'Design Bureau (OKB-1)'


def recovery(b):
    K.lot(b, GROUND, 80, 80, cx=0)
    b.cyl(CONC, (-12.0, 0, -10.0), 11.0, 0.25, segs=28)
    for dx in (-3.0, 3.0):
        b.box(WHITE, (-12.0 + dx, 0.27, -10.0), (0.9, 0.05, 7.0))
    b.box(WHITE, (-12.0, 0.27, -10.0), (6.0, 0.05, 0.9))
    # the charred descent sphere where it came down, the canopy dragged out behind it
    K.vostok_capsule(b, (14.0, -0.1, 12.0), charred=True, instrument_module=False)
    pts = [(0.0, 0.0)]
    for k in range(13):
        a = math.radians(-60 + k * 10)
        pts.append((22.0 * math.cos(a), 22.0 * math.sin(a)))
    K.ngon_prism(b, RED, [(p[0] * 0.6, p[1] * 0.6) for p in pts], 0.14, 0.2, center=(22.0, 0, 12.0))
    K.ngon_prism(b, WHITE, [(p[0] * 0.35, p[1] * 0.35) for p in pts], 0.2, 0.24, center=(22.0, 0, 12.0))
    for k in range(6):
        a = math.radians(-50 + k * 20)
        b.rod(METAL, (15.0, 1.1, 12.0), (22.0 + 13.0 * math.cos(a), 0.1, 12.0 + 13.0 * math.sin(a)), 0.02, segs=3)
    # tents, a radio mast and a recovery truck
    for k, x in enumerate((-28.0, -20.0)):
        b.box(GREEN, (x, 1.3, 24.0), (6.0, 0.08, 3.4), roll=40); b.box(GREEN, (x, 1.3, 26.0), (6.0, 0.08, 3.4), roll=-40)
    K.lattice_column(b, GREY, (-30.0, 0, -30.0), 1.4, 0.4, 24.0, levels=6, beam=0.1)
    K.slab(b, GREEN, 26.0, -26.0, 34.0, -23.0, 0.9, 3.4); K.slab(b, GREEN, 34.0, -26.0, 36.5, -23.0, 0.9, 3.0)
    for x in (27.5, 32.5, 35.3):
        for zz in (-26.1, -22.9):
            b.torus(DARK, (x, 0.6, zz), 0.55, 0.18, segs=10, rings=5, axis='z')
    K.flagpole(b, 0.0, 30.0)
    for x, z in ((-24.0, -24.0), (0.0, -24.0), (-24.0, 4.0)):
        b.rod(GREY, (x, 0, z), (x, 2.5, z), 0.08, segs=6); b.box(GLOW, (x, 2.7, z), (0.4, 0.4, 0.4))
    return 'Landing and Recovery Field'


# ============================================================ monuments ==

def _swept(b, mat, sections, yaw=0.0):
    """Loft a list of (y, x_offset, width, depth) cross-sections into a closed solid."""
    bm = b.master[mat]
    rings = []
    for y, xo, w, d in sections:
        rings.append([bm.verts.new(K.G(xo + sx * w / 2, y, sz * d / 2)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    faces = [bm.faces.new(rings[0][::-1]), bm.faces.new(rings[-1])]
    for lo, hi in zip(rings, rings[1:]):
        for i in range(4):
            faces.append(bm.faces.new((lo[i], lo[(i + 1) % 4], hi[(i + 1) % 4], hi[i])))
    for f in faces:
        f.material_index = mat
        f.smooth = False
    bmesh.ops.recalc_face_normals(bm, faces=faces)


def monument(b):
    """The Monument to the Conquerors of Space: a titanium exhaust trail climbing at
    77 degrees to a rocket 107 m up, over the museum base."""
    K.lot(b, ASPH, 80, 80, cx=0)
    K.slab(b, DARK, -26, -18, 26, 18, 0, 6.0)
    K.slab(b, STUCCO, -26.1, 17.9, 26.1, 18.1, 1.0, 5.2)
    for x in range(-24, 25, 3):
        b.box(TITAN, (x, 3.1, 18.2), (1.8, 3.6, 0.3))
    K.slab(b, DARK, -30, -22, 30, 22, 0, 0.8)
    secs = []
    n = 24
    for k in range(n + 1):
        t = k / n
        y = 6.0 + 96.0 * t
        xo = -10.0 + 26.0 * (t ** 1.35)
        w = 11.0 - 8.4 * t
        d = 3.2 - 1.6 * t
        secs.append((y, xo, w, d))
    _swept(b, TITAN, secs)
    # the rocket riding the top of the trail, aligned with it
    lean = math.degrees(math.atan2(26.0 * 1.35 / 96.0, 1.0))
    K.place(b, lambda t: (t.cyl(TITAN, (0, 0, 0), 1.4, 9.0, segs=16), t.cyl(TITAN, (0, 9.0, 0), 1.4, 4.0, segs=16, r2=0.05),
                          [t.box(TITAN, (1.6 * math.cos(math.radians(a)), 1.2, 1.6 * math.sin(math.radians(a))), (1.4, 2.4, 0.2), yaw=-a)
                           for a in (0, 120, 240)]),
            center=(16.0, 101.0, 0.0), roll=lean)
    # Tsiolkovsky on his chair in front
    K.slab(b, DARK, -3.0, 26.0, 3.0, 32.0, 0, 2.4)
    b.box(TITAN, (0, 3.4, 29.0), (1.8, 2.0, 1.6)); K.sphere(b, TITAN, (0, 5.0, 29.0), 0.6, segs=10, rings=8)
    return 'Monument to the Conquerors of Space'


def gagarin(b):
    """The Gagarin monument (Moscow, 1980): a 42 m fluted column carrying the figure
    with arms spread."""
    K.lot(b, ASPH, 40, 40, cx=0)
    K.slab(b, DARK, -8, -8, 8, 8, 0, 1.2); K.slab(b, DARK, -5, -5, 5, 5, 1.2, 3.6)
    b.cyl(TITAN, (0, 3.6, 0), 2.6, 30.0, segs=24, r2=1.8)
    for k in range(12):
        a = 2 * math.pi * k / 12
        b.box(TITAN, (2.2 * math.cos(a), 18.6, 2.2 * math.sin(a)), (0.35, 30.0, 0.35), yaw=-math.degrees(a))
    b.cyl(TITAN, (0, 33.6, 0), 1.2, 3.0, segs=16, r2=1.0)
    b.box(TITAN, (0, 38.0, 0), (1.6, 5.0, 1.0))
    K.sphere(b, TITAN, (0, 41.3, 0), 0.7, segs=12, rings=8)
    for s in (-1, 1):
        b.box(TITAN, (s * 1.9, 39.2, 0), (2.8, 0.45, 0.45), roll=s * -18)
    b.box(TITAN, (0, 1.8, 7.0), (4.0, 2.0, 0.6))
    K.sphere(b, METAL, (0, 3.4, 7.0), 0.8, segs=12, rings=8)
    return 'Gagarin Monument'


# ================================================================= inis ==

def cost(steel=0.3, concrete=0.6, asphalt=0.5, brick=0.0):
    out = ['-------', '$COST_WORK SOVIET_CONSTRUCTION_GROUNDWORKS 0.0', '$COST_WORK_BUILDING_ALL', '$COST_RESOURCE_AUTO ground_asphalt %.2f' % asphalt,
           '------------------', '$COST_WORK SOVIET_CONSTRUCTION_SKELETON_CASTING 1.0', '$COST_WORK_BUILDING_ALL',
           '$COST_RESOURCE_AUTO wall_concrete %.2f' % concrete]
    if brick:
        out.append('$COST_RESOURCE_AUTO wall_brick %.2f' % brick)
    out += ['------------------', '$COST_WORK SOVIET_CONSTRUCTION_STEEL_LAYING 1.0', '$COST_WORK_BUILDING_ALL',
            '$COST_RESOURCE_AUTO tech_steel %.2f' % steel, '-----------------------', '']
    return out


def road(zf, x=0.0, half=None, xr=None):
    """A road connection on the +z edge at zf, and the dead square covering the lot."""
    xr = xr or half
    return ['$CONNECTIONS_ROAD_DEAD_SQUARE', '%.1f %.1f' % (-xr, zf - 2 * half), '%.1f %.1f' % (xr, zf), '',
            '$CONNECTION_ROAD', '%.1f 0.0 %.1f' % (x, zf + 1.5), '%.1f 0.0 %.1f' % (x, zf), '',
            # outside point first, like the road and vanilla (kino.ini): the arrow points into the lot
            '$CONNECTION_PEDESTRIAN', '%.1f 0.0 %.1f' % (x + 8.0, zf + 1.5), '%.1f 0.0 %.1f' % (x + 8.0, zf), '']


# Every model is built with its ground plate at K.LOT_TOP (0.10) and then lifted by LIFT, so the
# plate becomes a 0.5 m podium with a skirt 2 m into the ground. A placed building sits on terrain
# that is only roughly flat; a plate 10 cm up let the terrain show through in patches (in game,
# 2026-09-29). Vanilla does the same: the cinema's podium is at 0.66, the aluminium plant's at 0.97.
LIFT = 0.40
PODIUM = K.LOT_TOP + LIFT


def stations(xs, z0, z1):
    """Truck bays on the podium; road and path connections stay at terrain height (0)."""
    return ['$VEHICLE_STATION %.1f %.2f %.1f  %.1f %.2f %.1f' % (x, PODIUM, z0, x, PODIUM, z1) for x in xs] + ['']


def merged(pairs):
    """(design good, rate) -> (game good, rate), goods that map to the same game good added up."""
    out = []
    for g, r in pairs:
        gg = good(g)
        for i, (h, s) in enumerate(out):
            if h == gg:
                out[i] = (h, s + r)
                break
        else:
            out.append((gg, r))
    return out


def factory(name, workers, profs, prod, cons, zf, half_x, half_z, st_xs, st_z0, st_z1, extra=(), power=0.4, desc='',
            standin_cons=None):
    """prod/cons: lists of (good, t/worker-day). Storages follow the goods' transport class.
    With vanilla stand-ins an input can turn into the output (rocket engines and the parts made from
    them are both mechanical components): such inputs are dropped, and standin_cons replaces cons
    where nothing would be left."""
    lines = ['$NAME_STR "%s"' % name, '']
    if desc:
        lines += ['; ' + desc, '']
    lines += cost(0.5, 0.8, 0.8, 0.3)
    lines += ['$TYPE_FACTORY', '$WORKERS_NEEDED %d' % workers]
    if profs:
        lines.append('$PROFESORS_NEEDED %d' % profs)
    prod_g = merged(prod)
    outs = [g for g, _ in prod_g]
    cons_g = merged(cons if G.USE_NEW_GOODS or not standin_cons else standin_cons)
    if not G.USE_NEW_GOODS:
        cons_g = [(g, r) for g, r in cons_g if g not in outs]
    assert cons_g, '%s uses nothing with %s goods' % (name, 'new' if G.USE_NEW_GOODS else 'stand-in')
    for g, r in prod_g:
        lines.append('$PRODUCTION %s %.4f' % (g, r))
    for g, r in cons_g:
        lines.append('$CONSUMPTION %s %.4f' % (g, r))
    lines.append('$CONSUMPTION_PER_SECOND eletric %.2f' % power)
    ins = [g for g, _ in cons_g]
    assert not set(ins) & set(outs), '%s makes what it uses (%s) - trucks would shuttle it round in circles' % (name, set(ins) & set(outs))
    for gg in ins:
        lines.append('$STORAGE_IMPORT_SPECIAL RESOURCE_TRANSPORT_%s 40 %s' % (CLASS.get(gg, 'COVERED'), gg))
    for gg in outs:
        lines.append('$STORAGE_EXPORT_SPECIAL RESOURCE_TRANSPORT_%s 60 %s' % (CLASS.get(gg, 'COVERED'), gg))
    lines += list(extra) + ['']
    lines += stations(st_xs, st_z0, st_z1)
    lines += road(zf, half=half_z, xr=half_x)
    lines += ['end', '']
    return '\r\n'.join(lines)


def ini_pad(name, deck_y, half_x, half_z, desc, scale=1.0):
    """scale: construction cost factor. The game prices a building by its model's size, and the N1
    complex (145 m gantry, 180 m lightning towers) came out at ~22 M rubles and a build that never
    ends in a test game; 0.25 brings it to a few R-7 pads."""
    lines = ['$NAME_STR "%s"' % name, '', '; ' + desc, ''] + cost(1.0 * scale, 2.0 * scale, 1.0 * scale) + [
        '$TYPE_AIRPLANE_PARKING', '$WORKING_VEHICLES_NEEDED 1',
        '$HELIPORT_STATION 0.0 %.2f -9.0  0.0 %.2f 9.0' % (deck_y + LIFT, deck_y + LIFT), '',
        '$CONNECTIONS_AIRPORT_DEAD_SQUARE', '%.1f %.1f' % (-half_x, -half_z), '%.1f %.1f' % (half_x, half_z), '',
        '$CONNECTION_ROAD', '0.0 0.0 %.1f' % (half_z + 1.5), '0.0 0.0 %.1f' % half_z, '', 'end', '']
    return '\r\n'.join(lines)


def ini_university(name, workers, profs, zf, half_x, half_z, desc, subtype='$SUBTYPE_TECHNICAL', serve=3):
    lines = ['$NAME_STR "%s"' % name, '', '; ' + desc, ''] + cost(0.3, 1.0, 0.6, 0.6) + [
        '$TYPE_UNIVERSITY', subtype, '$WORKERS_NEEDED %d' % workers, '$PROFESORS_NEEDED %d' % profs,
        '$CITIZEN_ABLE_SERVE %d' % serve, ''] + stations((-half_x + 6.0, -half_x + 10.0), zf - 12.0, zf - 2.0) + road(zf, half=half_z, xr=half_x) + ['end', '']
    return '\r\n'.join(lines)


def ini_training(name, zf, half_x, half_z, desc):
    """Staff only: no students, a handful of support staff and 40 seats for graduates (the
    professor slots), which is what the experts plugin trains. A radio-type building because
    it is the simplest type that employs graduates without admitting students; its numbers
    (6 / 40) differ from the tracking station's (40 / 30), which the programme counts."""
    lines = ['$NAME_STR "%s"' % name, '', '; ' + desc, ''] + cost(0.3, 1.0, 0.6, 0.6) + [
        '$TYPE_BROADCAST', '$SUBTYPE_RADIO', '$WORKERS_NEEDED 6', '$PROFESORS_NEEDED 40', '$CONSUMPTION_PER_SECOND eletric 0.6', '']
    lines += stations((-half_x + 6.0, -half_x + 10.0), zf - 12.0, zf - 2.0) + road(zf, half=half_z, xr=half_x) + ['end', '']
    return '\r\n'.join(lines)


def ini_mik(name, desc):
    """An aircraft production line: the rocket is picked in the building's window and the MIK
    is linked to a launch pad. A production line hands a finished aircraft or helicopter to a
    free station of a linked building (SOVIET64 0x1CA97D), and an airplane-parking building's
    HELIPORT_STATION is such a station, so the rocket appears standing on the pad.

    What a rocket costs comes from the vehicle (its empty weight gives the blueprint's bill of
    parts), and the import warehouse is the engine's fixed vehicle-parts set. $CONSUMPTION must
    still name every part of that bill, as vanilla production_airplane.ini does: in game a part
    the line does not list is reported missing however much of it is in stock (tested
    2026-09-29 - steel, plastics, fabric and ecomponents were "missing" with plastics 5.96 t on
    hand, while the listed mcomponents short by 5 t were not)."""
    lines = ['$NAME_STR "%s"' % name, '', '; ' + desc, ''] + cost(0.8, 1.6, 1.0) + [
        '$TYPE_PRODUCTION_LINE', '$SUBTYPE_AIRPLANE', '$WORKERS_NEEDED 200', '$PROFESORS_NEEDED 100',
        '$ELETRIC_CONSUMPTION_LIVING_WORKER_FACTOR 6.0', '$WASTE_PRODUCTION_DISABLE']
    if G.USE_NEW_GOODS:
        # the spacerace plugin replaces each rocket's bill with these (space_goods.BILL)
        parts = ('rocket_stage', 'rocket_engine', 'avionics')
        lines += ['$STORAGE_IMPORT_SPECIAL RESOURCE_TRANSPORT_%s 150 %s' % (CLASS[g], g) for g in parts]
        lines += ['$CONSUMPTION %s 1.00' % g for g in parts]
    else:
        lines += ['$STORAGE_IMPORT_CARPLANT RESOURCE_TRANSPORT_COVERED 120', '$STORAGE_IMPORT_CARPLANT RESOURCE_TRANSPORT_OPEN 120']
        lines += ['$CONSUMPTION %s 1.00' % g for g in ('steel', 'aluminium', 'plastics', 'mcomponents', 'ecomponents', 'fabric', 'eletronics')]
    lines += ['$PRODUCTION vehicles 1.0', '']
    # truck bays in the east yard, north of the transporter-erector and clear of the halls
    lines += stations((72.0, 76.0, 80.0, 84.0), 12.0, 34.0)
    # the pad is linked to the MIK by the spacerace plugin (see spacerace.cpp, job 5)
    lines += ['$CONNECTIONS_ROAD_DEAD_SQUARE', '66.0 8.0', '104.0 40.0', '',
              '$CONNECTION_ROAD', '78.0 0.0 41.5', '78.0 0.0 40.0', '',
              '$CONNECTION_PEDESTRIAN', '20.0 0.0 41.5', '20.0 0.0 40.0', '', 'end', '']
    return '\r\n'.join(lines)


def ini_broadcast(name, zf, half_x, half_z, desc):
    lines = ['$NAME_STR "%s"' % name, '', '; ' + desc, ''] + cost(0.8, 0.8, 0.5) + [
        '$TYPE_BROADCAST', '$SUBTYPE_RADIO', '$WORKERS_NEEDED 40', '$PROFESORS_NEEDED 30', '$CONSUMPTION_PER_SECOND eletric 1.5', '']
    lines += stations((-4.0, 0.0), zf - 12.0, zf - 2.0) + road(zf, x=-2.0, half=half_z, xr=half_x) + ['end', '']
    return '\r\n'.join(lines)


def ini_monument(name, half, radius, strength, desc):
    lines = ['$NAME_STR "%s"' % name, '', '; ' + desc, '', '$TYPE_MONUMENT',
             '$MONUMENT_GOVERNMENT_LOYALTY_RADIUS %d' % radius, '$MONUMENT_GOVERNMENT_LOYALTY_STRENGTH %.1f' % strength, ''] + cost(0.6, 1.5, 0.5) + [
        '$CONNECTION_PEDESTRIAN', '0.0 0.0 %.1f' % (half + 1.5), '0.0 0.0 %.1f' % half, '', 'end', '']
    return '\r\n'.join(lines)


INIS = {
    'pad_r7': lambda: ini_pad('Launch Complex (R-7)', 6.3, 60, 48,
                              'Gagarin Start. Sputnik, Vostok, Voskhod and Soyuz rockets stand here. Needs the MIK and the propellant plants.'),
    'pad_n1': lambda: ini_pad('Heavy Launch Complex (N1)', 14.4, 100, 90,
                              'Site 110. The only pad an N1 can use. 145 m gantry, three flame trenches, four lightning towers.',
                              scale=0.25),
    'mik': lambda: ini_mik('Assembly and Testing Building (MIK)',
                           'Pick the rocket to build here and link the MIK to a launch pad: stages, engines and spacecraft go in, '
                           'the finished rocket rolls out onto the pad.'),
    'rocket_plant': lambda: factory('Rocket Plant (Progress)', 500, 250, [('rocket_stage', 0.004)],
                                    [('aluminium', 0.012), ('steel', 0.008), ('avionics', 0.001)],
                                    55, 85, 55, (-16.0, -12.0, -8.0, -4.0), 20.0, 50.0,
                                    desc='Stage production, the Kuibyshev plant. Everything a rocket is made of meets here.'),
    'engine_plant': lambda: factory('Rocket Engine Works (OKB-456)', 300, 120, [('rocket_engine', 0.006)],
                                    [('steel', 0.010), ('mcomponents', 0.006), ('chemicals', 0.004)],
                                    45, 60, 45, (0.0, 4.0, 8.0), 14.0, 38.0, desc='Glushko turbopump engines.'),
    'test_stand': lambda: factory('Engine Test Stand', 80, 40, [('mcomponents', 0.004)],
                                  [('rocket_engine', 0.003), ('lox', 0.02), ('fuel', 0.01)],
                                  50, 50, 50, (20.0, 24.0), 26.0, 46.0,
                                  desc='Engines from every batch are fired to destruction; what is learnt goes back to the engine works as parts. '
                                       'While a test stand is working, launches fail less often.'),
    # oxygen comes from the air: power, and a trickle of chemicals for the intake driers (vanilla water
    # arrives only by pipe, and this plant has none; no vanilla factory runs without any input)
    # (with stand-in goods its oxygen is chemicals, so the driers take spare parts instead)
    'lox_plant': lambda: factory('Oxygen-Nitrogen Plant', 60, 20, [('lox', 0.06)], [('chemicals', 0.002)],
                                 40, 50, 40, (16.0, 20.0), 20.0, 38.0, power=4.0,
                                 desc='Liquid oxygen boils off: build it close to the pad and fill just before a launch.',
                                 standin_cons=[('mcomponents', 0.002)]),
    'propellant': lambda: factory('Propellant Plant (UDMH / N2O4)', 90, 30, [('hypergolic', 0.03)],
                                  [('chemicals', 0.02), ('fuel', 0.015)], 45, 55, 45, (-6.0, -2.0, 2.0), 22.0, 43.0,
                                  extra=['$POLLUTION_HIGH'], desc='Toxic hypergolic propellants for Proton and upper stages. Accidents happen.'),
    'instruments': lambda: factory('Instrument Works', 200, 150, [('avionics', 0.008)],
                                   [('eletronics', 0.008), ('ecomponents', 0.006), ('plastics', 0.004)],
                                   35, 48, 35, (20.0, 24.0, 28.0), 20.0, 33.0, desc='Guidance, telemetry and radio for rockets and spacecraft.'),
    'spacecraft': lambda: factory('Spacecraft Assembly Hall', 250, 200, [('spacecraft', 0.003)],
                                  [('avionics', 0.004), ('heat_shield', 0.004), ('fabric', 0.003), ('space_food', 0.002)],
                                  35, 45, 35, (22.0, 26.0, 30.0), 14.0, 33.0, desc='Vostok, Voskhod, Soyuz and the lunar craft.'),
    'tracking': lambda: ini_broadcast('Deep Space Tracking Station (Pluton)', 40, 50, 40,
                                      'Crewed flights and probes need the tracking network.'),
    'training': lambda: ini_training('Cosmonaut Training Centre', 45, 55, 45,
                                     'Star City. Its 40 trainee seats take graduates (education 2 or more); the experts plugin turns a graduate aged 23-35 in good health into a cosmonaut in about a year.'),
    'bureau': lambda: ini_university('Design Bureau (OKB-1)', 80, 120, 28, 42, 28,
                                     'The chief designers. Space research runs here.'),
    'recovery': lambda: ini_pad('Landing and Recovery Field', K.LOT_TOP, 40, 40, 'Where the descent capsules come down in the steppe.'),
    'monument': lambda: ini_monument('Monument to the Conquerors of Space', 40, 420, 4.5, 'Raised after the first man in space.'),
    'gagarin': lambda: ini_monument('Gagarin Monument', 20, 260, 3.2, 'The first man in space.'),
}

ASSETS = [('pad_r7', pad_r7), ('pad_n1', pad_n1), ('mik', mik), ('rocket_plant', rocket_plant), ('engine_plant', engine_plant),
          ('test_stand', test_stand), ('lox_plant', lox_plant), ('propellant', propellant), ('instruments', instruments),
          ('spacecraft', spacecraft), ('tracking', tracking), ('training', training), ('bureau', bureau),
          ('recovery', recovery), ('monument', monument), ('gagarin', gagarin)]

RENDERCONFIG = '''$TYPE_WORKSHOP
 MODEL model.nmf
 MATERIAL ../material/%(n)s.mtl
 MATERIALEMISSIVE ../material/%(n)s_e.mtl
 LIFE 4000.000000
 EXPLOSION_GROUP 0
 DERBIS_FALLING_FX buildingfall1 1.000000
 DERBIS_FALLED_FX buildingfall2 1.400000
 DERBIS_FALLED_SFX collapse
 DERBIS_NUM 8
 DERBIS_FALLING_FX_MAXTIME 3.000000
 DERBIS_SCALE 0.900000
 DERBIS_MESH buildings/buildingwreck1.nmf buildings/buildingwreck.mtl
 END
'''.replace('\n', '\r\n')


def mtl(names, emissive=False):
    out = []
    for name in names:
        out.append('$SUBMATERIAL %s' % name)
        out.append('$TEXTURE_MTL 0 %s.dds' % name)
        if emissive:
            out.append('$TEXTURE_MTL 1 %s.dds' % EMISSIVE.get(name, 'sr_black'))
        else:
            out.append('$TEXTURE 1 buildings/blankspecular.dds')
        out += ['$TEXTURE 2 buildings/blankbump.dds', '', '$DIFFUSECOLOR 0.92 0.92 0.92 1.0',
                '$SPECULARCOLOR %s 1.0' % ('0.8 0.8 0.8' if name in ('sr_titanium', 'sr_metal', 'sr_frost', 'sr_white') else '0.3 0.3 0.3'),
                '$AMBIENTCOLOR 1.0 1.0 1.0 1.0', '', '$SPECULARPOWER %s' % ('24.0' if name == 'sr_titanium' else '4.0'), '']
    out += ['$END', '']
    return '\r\n'.join(out)


# preview camera per asset: azimuth, elevation, fill, target height (None = bbox centre)
VIEW = {'pad_r7': (-35, 28, 1.0, 14.0), 'pad_n1': (-40, 18, 1.6, 75.0), 'test_stand': (-35, 20, 1.0, 26.0),
        'monument': (-35, 12, 1.6, 55.0), 'gagarin': (-35, 12, 1.6, 21.0), 'mik': (-30, 30, 0.9, None)}


def view(bbox, az, el, fill, ty):
    pos, tgt = mmkit.frame_camera(bbox, azimuth_deg=az, elevation_deg=el, fill=fill)
    if ty is None:
        return pos, tgt
    dy = ty - tgt[1]
    return (pos[0], pos[1] + dy, pos[2]), (tgt[0], ty, tgt[2])


def write_inis(key, adir):
    """building.ini with vanilla stand-ins, and the new-goods variant for the spacerace plugin."""
    saved = G.USE_NEW_GOODS
    try:
        G.USE_NEW_GOODS = False
        mmkit.write_text(os.path.join(adir, 'building.ini'), INIS[key]())
        G.USE_NEW_GOODS = True
        os.makedirs(GOODS_INIS, exist_ok=True)
        mmkit.write_text(os.path.join(GOODS_INIS, 'sr_%s.ini' % key), INIS[key]())
    finally:
        G.USE_NEW_GOODS = saved


def main():
    if INIS_ONLY:
        for key, _fn in ASSETS:
            if not ONLY or key in ONLY:
                write_inis(key, os.path.join(KITDIR, 'sr_' + key))
        print('building files (stand-in and new goods) written for %d buildings' % len(ASSETS))
        return
    mmkit.clear_scene()
    os.makedirs(KITDIR, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    matdir = os.path.join(KITDIR, 'material')
    os.makedirs(matdir, exist_ok=True)
    for name in MATS + ['sr_black', 'sr_glass_e', 'sr_stucco_e']:
        shutil.copy(os.path.join(TEXDIR, name + '.dds'), os.path.join(matdir, name + '.dds'))
    bmats = mmkit.blender_materials(TEXDIR, MATS)
    mmkit.lighting()
    cfg = ['$ITEM_ID %d' % ITEM_ID, '', '$OWNER_ID 76561198165729857', '', '$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING', '', '$VISIBILITY %d' % VISIBILITY, '']
    summary = []
    for key, fn in ASSETS:
        cfg.append('$OBJECT_BUILDING sr_%s' % key)
        if ONLY and key not in ONLY:
            continue
        b = K.builder(seed=sum(map(ord, key)))
        title = fn(b)
        for bm in b.master.values():          # the podium lift (Blender z = game up)
            for v in bm.verts:
                v.co.z += LIFT
        b.fire = [(x, y + LIFT, z) for x, y, z in b.fire]
        shapes, used = b.export_shapes(prefix='sr_')
        model = nmf.Model(); model.materials = used; model.shapes = shapes
        adir = os.path.join(KITDIR, 'sr_' + key)
        os.makedirs(adir, exist_ok=True)
        nmf.write(model, os.path.join(adir, 'model.nmf'))
        bbox = mmkit.model_bbox(shapes)
        mmkit.write_bbox_file(os.path.join(adir, 'building.bbox'), shapes)
        mmkit.write_fire_file(os.path.join(adir, 'building.fire'), b.fire)
        write_inis(key, adir)
        mmkit.write_text(os.path.join(adir, 'renderconfig.ini'), RENDERCONFIG % {'n': 'sr_' + key})
        mmkit.write_text(os.path.join(matdir, 'sr_%s.mtl' % key), mtl(used))
        mmkit.write_text(os.path.join(matdir, 'sr_%s_e.mtl' % key), mtl(used, emissive=True))
        obs = b.preview_objects(bmats, key)
        az, el, fill, ty = VIEW.get(key, (-35, 26, 0.95, None))
        pos, tgt = view(bbox, az, el, fill, ty)
        mmkit.render(os.path.join(PREVIEW, key + '.png'), pos, tgt, (1400, 900), samples=32)
        pos, tgt = view(bbox, az + 5, el + 6, fill * 1.05, ty)
        mmkit.render(os.path.join(PREVIEW, key + '_icon.png'), pos, tgt, (384, 384), transparent=True, samples=24)
        mmkit.save_scaled_png(os.path.join(PREVIEW, key + '_icon.png'), os.path.join(adir, 'imagegui.png'), 96, 96)
        for ob in obs:
            bpy.data.objects.remove(ob)
        tris = sum(s.nt for s in shapes)
        b.free()
        summary.append('%-14s %-40s tris=%6d nodes=%2d bbox=%s' % (key, title, tris, len(shapes), ['%.0f' % v for v in bbox]))
        print(summary[-1])
    cfg += ['', '$ITEM_NAME "Space Race Kit"', '',
            '$ITEM_DESC "The Soviet space programme: launch complexes for the R-7 and the N1, the MIK, rocket, engine and propellant plants, test stand, tracking, Star City, OKB-1 and the monuments."',
            '', '$END', '']
    mmkit.write_text(os.path.join(KITDIR, 'workshopconfig.ini'), '\r\n'.join(cfg))
    print('\n'.join(summary))
    print('space kit done')


main()
