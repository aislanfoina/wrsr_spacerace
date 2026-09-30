"""The space branch of the research tree, its names, its icons.

    python tools/space_research.py

Writes into mod/plugins/spacerace/data/ (the spacerace plugin ships that folder):
    research_space.ini   our $RESEARCH entries, appended to the vanilla tree at run time
    inject.ini           vanilla entries that gain an $UNLOCK_RESEARCH line (the branch's roots)
    strings.txt          id <TAB> text, answered by the plugin's C3D_LANGUAGE::GetString hook
    research/<id>.png    128 x 128 icons, copied into media_soviet/research by the plugin

Building unlocks name workshop idents as {KIT}/<object>; the plugin substitutes
the kit's item id from spacerace.ini (9000101 while it is a local dev item, the
real Steam id once published).
"""
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'mod', 'plugins', 'spacerace', 'data')
ICONS = os.path.join(ROOT, 'build', 'space')
RICONS = os.path.join(ROOT, 'build', 'space_vehicles')
ID0 = 591000   # our language ids: 591000.. (the game's highest is 580231)

# id, type, cost, year, unlocked-by (ours), unlocks buildings, name, description, icon source
TREE = [
    ('sr_rocketry', 'TECHNICAL', 2500, 1946, [], ['bureau'],
     'Rocket Research Institute (NII-88)',
     'The captured V-2 is studied, copied as the R-1 and outgrown. A research institute for long-range rockets opens the space branch of the tree.',
     'r:sr_sputnik'),
    ('sr_liquid_engines', 'TECHNICAL', 3000, 1948, ['sr_rocketry'], ['engine_plant', 'test_stand'],
     'Liquid Rocket Engines',
     'Turbopump-fed kerosene and liquid oxygen engines. Unlocks the Rocket Engine Works and the Engine Test Stand: every engine is fired once before it flies.',
     'engine_plant'),
    ('sr_cryogenics', 'TECHNICAL', 2400, 1949, ['sr_rocketry'], ['lox_plant'],
     'Cryogenic Oxygen',
     'Air separation on an industrial scale. Unlocks the Oxygen-Nitrogen Plant. Liquid oxygen boils away: produce it close to the pad.',
     'lox_plant'),
    ('sr_guidance', 'TECHNICAL', 2800, 1950, ['sr_rocketry'], ['instruments'],
     'Radio Guidance and Telemetry',
     'Gyroscopes, radio control and telemetry. Unlocks the Instrument Works.',
     'instruments'),
    ('sr_r7_icbm', 'TECHNICAL', 4500, 1954, ['sr_liquid_engines', 'sr_guidance'], ['rocket_plant', 'mik', 'pad_r7'],
     'The R-7 Semyorka',
     'Korolev\'s two-stage intercontinental rocket: a core and four strap-on boosters, twenty engines lit on the ground. Unlocks the Rocket Plant, the MIK and the R-7 Launch Complex.',
     'pad_r7'),
    ('sr_satellite', 'TECHNICAL', 3500, 1956, ['sr_r7_icbm', 'sr_cryogenics'], ['spacecraft', 'tracking'],
     'Artificial Earth Satellite',
     'A simple satellite before the Americans fly theirs. Unlocks the Spacecraft Assembly Hall, the Deep Space Tracking Station and the Sputnik mission.',
     'tracking'),
    ('sr_biosatellite', 'MEDICAL', 2500, 1957, ['sr_satellite'], ['recovery'],
     'Biological Satellites',
     'Life support in orbit and a way back: dogs first. Unlocks the Landing and Recovery Field.',
     'recovery'),
    ('sr_lunar_probes', 'TECHNICAL', 3000, 1958, ['sr_satellite'], [],
     'Lunar Probes',
     'The Blok E upper stage reaches escape velocity. Luna probes hit the Moon and photograph its far side.',
     'r:sr_vostok'),
    ('sr_manned_flight', 'MEDICAL', 5000, 1959, ['sr_biosatellite'], ['training'],
     'Manned Spaceflight',
     'The Vostok spacecraft and the cosmonaut corps. Unlocks the Cosmonaut Training Centre: graduates who train there become experts.',
     'training'),
    ('sr_space_glory', 'SOVIET', 1500, 1961, ['sr_manned_flight'], ['monument', 'gagarin'],
     'Glory to the Conquerors of Space',
     'Monuments to the first man in space and to those who follow.',
     'monument'),
    ('sr_hypergolic', 'TECHNICAL', 3000, 1958, ['sr_liquid_engines'], ['propellant'],
     'Storable Propellants',
     'UDMH and nitrogen tetroxide ignite on contact and keep for months. Toxic and dangerous. Unlocks the Propellant Plant.',
     'propellant'),
    ('sr_eva', 'MEDICAL', 3000, 1963, ['sr_manned_flight'], [],
     'Extravehicular Activity',
     'An inflatable airlock and a pressure suit that has to shrink back through it.',
     'r:sr_vostok'),
    ('sr_soyuz', 'TECHNICAL', 4500, 1963, ['sr_manned_flight'], [],
     'The Soyuz Spacecraft',
     'Three cosmonauts, rendezvous and docking. Unlocks the Soyuz rocket.',
     'r:sr_soyuz'),
    ('sr_proton', 'TECHNICAL', 5500, 1962, ['sr_hypergolic', 'sr_r7_icbm'], [],
     'Heavy Launcher (UR-500)',
     'Chelomei\'s hypergolic heavy rocket. Unlocks the Proton for Zond and the lunar probes.',
     'r:sr_proton'),
    ('sr_n1_programme', 'TECHNICAL', 9000, 1964, ['sr_soyuz', 'sr_proton'], ['pad_n1'],
     'The N1 Moon Rocket',
     'Thirty engines in the first stage, 105 m, 2750 t. Unlocks the Heavy Launch Complex. Without the NK-33 engines and a tested first stage it will fail.',
     'pad_n1'),
    ('sr_nk33', 'TECHNICAL', 6000, 1966, ['sr_n1_programme'], [],
     'NK-33 Engines and KORD',
     'Kuznetsov\'s reusable engines and a control system that shuts down a failing engine and its opposite. Makes the N1 far more likely to survive its first stage.',
     'engine_plant'),
    ('sr_lunar_landing', 'TECHNICAL', 7000, 1966, ['sr_n1_programme'], [],
     'Lunar Landing (L3)',
     'The LK lander and the LOK orbiter. With these the N1 carries a cosmonaut to the Moon.',
     'r:sr_n1'),
]
# the branch's roots hang off these vanilla entries
INJECT = {'advanced_engineering': ['sr_rocketry'], 'electronics_1': ['sr_guidance']}


def ids():
    return {rid: (ID0 + 2 * i, ID0 + 2 * i + 1) for i, (rid, *_rest) in enumerate(TREE)}


def research_ini():
    idmap = ids()
    children = {}
    for rid, typ, cost, year, parents, *_r in TREE:
        for p in parents:
            children.setdefault(p, []).append(rid)
    out = []
    for rid, typ, cost, year, parents, blds, name, desc, icon in TREE:
        n, d = idmap[rid]
        out += ['', '$RESEARCH %s' % rid, '-----------------------------------------------', '',
                '$TYPE_%s' % typ, '$COST %d' % cost, '$YEAR %d' % year, '']
        for c in children.get(rid, []):
            out.append('$UNLOCK_RESEARCH %s' % c)
        for bkey in blds:
            out.append('$UNLOCK_BUILDING {KIT}/sr_%s' % bkey)
        out += ['', '$NAME %d' % n, '$DESC %d' % d, '', '$RESEARCH_ADD', '']
    return '\r\n'.join(out) + '\r\n'


def strings():
    idmap = ids()
    lines = []
    for rid, typ, cost, year, parents, blds, name, desc, icon in TREE:
        n, d = idmap[rid]
        lines.append('%d\t%s' % (n, name))
        lines.append('%d\t%s' % (d, desc))
    return '\n'.join(lines) + '\n'


def icon(rid, src):
    """128 x 128 RGBA from a building or rocket render, on a dark disc like the vanilla icons."""
    if src.startswith('r:'):
        p = os.path.join(RICONS, src[2:] + '_preview_side.png')
    else:
        p = os.path.join(ICONS, src + '_icon.png')
    im = Image.open(p).convert('RGBA')
    bb = im.getbbox() or (0, 0) + im.size
    im = im.crop(bb).transpose(Image.FLIP_LEFT_RIGHT)   # the game shows models mirrored
    w, h = im.size
    s = 112.0 / max(w, h)
    im = im.resize((max(1, int(w * s)), max(1, int(h * s))), Image.LANCZOS)
    out = Image.new('RGBA', (128, 128), (0, 0, 0, 0))
    from PIL import ImageDraw
    d = ImageDraw.Draw(out)
    d.ellipse([2, 2, 125, 125], fill=(40, 44, 52, 235), outline=(190, 40, 35, 255), width=4)
    out.alpha_composite(im, ((128 - im.size[0]) // 2, (128 - im.size[1]) // 2))
    out.save(os.path.join(OUT, 'research', rid + '.png'))


def main():
    os.makedirs(os.path.join(OUT, 'research'), exist_ok=True)
    open(os.path.join(OUT, 'research_space.ini'), 'w', encoding='utf-8', newline='').write(research_ini())
    inj = ['; vanilla research entries that unlock the space branch (parent = child, child...)', '[inject]']
    inj += ['%s = %s' % (k, ', '.join(v)) for k, v in INJECT.items()]
    open(os.path.join(OUT, 'inject.ini'), 'w', encoding='utf-8', newline='').write('\r\n'.join(inj) + '\r\n')
    open(os.path.join(OUT, 'strings.txt'), 'w', encoding='utf-8', newline='').write(strings())
    for rid, *_r, src in TREE:
        icon(rid, src)
    print('research: %d entries, %d strings, icons -> %s' % (len(TREE), 2 * len(TREE), os.path.relpath(OUT, ROOT)))


if __name__ == '__main__':
    main()
