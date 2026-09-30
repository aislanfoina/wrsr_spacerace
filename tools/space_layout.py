"""Top-down layout check for the space kit: each building's footprint with its ini's
truck bays, road and path connections, dead squares and launch stations drawn on top.

    python tools/space_layout.py [kitdir] [outdir]

Grey is geometry taller than 1.5 m (walls, tanks, gantries), light grey the rest.
Red lines are $VEHICLE_STATION bays, blue the road connection (arrow into the lot) and
dead square, green the pedestrian connection, yellow the heliport station. Prints the
bays that run through tall geometry, which is what trucks cannot reach.
"""
import glob
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nmf  # noqa: E402

KIT = sys.argv[1] if len(sys.argv) > 1 else 'mod/buildings/space_kit'
OUT = sys.argv[2] if len(sys.argv) > 2 else 'build/space_layout'
PX = 4          # pixels per metre
TALL = 1.9       # 1.5 m above the ground plate, which models now carry 0.4 m up (space_scene.LIFT)


def floats(line):
    out = []
    for t in line.split():
        try:
            out.append(float(t))
        except ValueError:
            pass
    return out


def parse_ini(path):
    lines = [l.split(';')[0].strip() for l in open(path, encoding='utf-8', errors='ignore')]
    items = {'station': [], 'road': [], 'ped': [], 'dead': [], 'heli': []}
    i = 0
    while i < len(lines):
        l = lines[i]
        if l.startswith('$VEHICLE_STATION ') or l.startswith('$HELIPORT_STATION '):
            v = floats(l)
            items['station' if l.startswith('$VEHICLE') else 'heli'].append(((v[0], v[2]), (v[3], v[5])))
        elif l in ('$CONNECTION_ROAD', '$CONNECTION_PEDESTRIAN'):
            a, b = floats(lines[i + 1]), floats(lines[i + 2])
            items['road' if l == '$CONNECTION_ROAD' else 'ped'].append(((a[0], a[2]), (b[0], b[2])))
            i += 2
        elif l.endswith('DEAD_SQUARE'):
            a, b = floats(lines[i + 1]), floats(lines[i + 2])
            items['dead'].append(((a[0], a[1]), (b[0], b[1])))
            i += 2
        i += 1
    return items


def triangles(model):
    for s in model.shapes:
        p = s.pos
        for k in range(0, len(s.indices), 3):
            yield [(p[3 * j], p[3 * j + 1], p[3 * j + 2]) for j in s.indices[k:k + 3]]


def check(folder):
    name = os.path.basename(folder)
    model = nmf.read(os.path.join(folder, 'model.nmf'))
    ini = parse_ini(os.path.join(folder, 'building.ini'))
    tris = list(triangles(model))
    xs = [v[0] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    x0, x1, z0, z1 = min(xs) - 6, max(xs) + 6, min(zs) - 6, max(zs) + 6
    W, H = int((x1 - x0) * PX), int((z1 - z0) * PX)
    img = Image.new('RGB', (W, H), (250, 250, 245))
    tall = Image.new('L', (W, H), 0)
    d, dt = ImageDraw.Draw(img), ImageDraw.Draw(tall)

    def P(x, z):
        return ((x - x0) * PX, (z - z0) * PX)

    for t in sorted(tris, key=lambda t: max(v[1] for v in t)):
        poly = [P(v[0], v[2]) for v in t]
        hi = max(v[1] for v in t) > TALL
        d.polygon(poly, fill=(120, 120, 120) if hi else (215, 215, 205))
        if hi:
            dt.polygon(poly, fill=255)
    for (ax, az), (bx, bz) in ini['dead']:
        d.rectangle([P(min(ax, bx), min(az, bz)), P(max(ax, bx), max(az, bz))], outline=(40, 90, 230), width=2)
    blocked = []
    for n, (a, b) in enumerate(ini['station']):
        d.line([P(*a), P(*b)], fill=(220, 30, 30), width=5)
        d.ellipse([P(a[0] - 0.8, a[1] - 0.8), P(a[0] + 0.8, a[1] + 0.8)], fill=(120, 0, 0))
        hits = 0
        for k in range(21):
            px, pz = P(a[0] + (b[0] - a[0]) * k / 20, a[1] + (b[1] - a[1]) * k / 20)
            if 0 <= px < W and 0 <= pz < H and tall.getpixel((int(px), int(pz))):
                hits += 1
        if hits:
            blocked.append((n, hits))
    for (a, b) in ini['heli']:
        d.line([P(*a), P(*b)], fill=(230, 190, 0), width=6)
    for key, col in (('road', (40, 90, 230)), ('ped', (30, 160, 60))):
        for a, b in ini[key]:
            d.line([P(*a), P(*b)], fill=col, width=6)
            d.ellipse([P(b[0] - 1.2, b[1] - 1.2), P(b[0] + 1.2, b[1] + 1.2)], fill=col)   # the inner end
    os.makedirs(OUT, exist_ok=True)
    img.save(os.path.join(OUT, name + '.png'))
    msg = '%-16s bays %d, road %d, path %d, dead %d, heli %d' % (name, len(ini['station']), len(ini['road']), len(ini['ped']),
                                                                 len(ini['dead']), len(ini['heli']))
    if blocked:
        msg += '   BAYS THROUGH WALLS: ' + ', '.join('#%d (%d/21)' % b for b in blocked)
    print(msg)
    return not blocked


if __name__ == '__main__':
    ok = all([check(f) for f in sorted(glob.glob(os.path.join(KIT, 'sr_*'))) if os.path.exists(os.path.join(f, 'building.ini'))])
    print('all bays clear' if ok else 'some bays run through buildings')
