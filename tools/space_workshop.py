"""The Space Race's seven Steam Workshop items: ids, names and store-page descriptions (Steam BBCode).

    python tools/space_workshop.py
    python tools/space_workshop.py new     # preview + description files for the game's "create new item" form

Rewrites workshopconfig.ini of the package (plugins), the building kit and the five rockets, and
spacerace.ini's kit_item, from ITEMS below. Run it after tools/build_space.py (the kit and vehicle
stages write their own short configs).

Publishing (the game's uploader: main menu -> Workshop -> Your items (WIP)). A new item is created
in the game first with the green +, which asks for a preview PNG (under 1 MB), a name and a UTF-8
TXT description (`new` writes them to build/workshop_new/space_race) and gives the item its Steam
id and a media_soviet/workshop_wip/<id> folder; put that id in ITEMS, run this, then
`build.ps1 -Install` fills the folders and the game uploads them. $VISIBILITY is the game's, not
Steam's: 0 unpublished, 1 friends only, 2 PUBLIC (what 71 of 81 published items carry).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OWNER = 76561198165729857
VISIBILITY = 0                  # unpublished; switch to public on Steam once the items are checked
REPO = 'https://github.com/aislanfoina/wrsr_spacerace'
ITEM_URL = 'https://steamcommunity.com/sharedfiles/filedetails/?id=%d'
RML = ITEM_URL % 3787969749

# key: (folder, Steam item id, item type, name). Created in the game on 2026-10-05 (dev ids were 90001xx).
ITEMS = {
    'package': ('mod/packages/space_race', 3814051864, 'WORKSHOP_ITEMTYPE_SCRIPT', 'Space Race [1.1.1.9]'),
    'kit': ('mod/buildings/space_kit', 3814049784, 'WORKSHOP_ITEMTYPE_BUILDING', 'Space Race Kit'),
    'sr_sputnik': ('mod/vehicles/sr_sputnik', 3814050253, 'WORKSHOP_ITEMTYPE_VEHICLE', 'Space Race: R-7 Sputnik'),
    'sr_vostok': ('mod/vehicles/sr_vostok', 3814050457, 'WORKSHOP_ITEMTYPE_VEHICLE', 'Space Race: Vostok-K'),
    'sr_soyuz': ('mod/vehicles/sr_soyuz', 3814052488, 'WORKSHOP_ITEMTYPE_VEHICLE', 'Space Race: Soyuz'),
    'sr_proton': ('mod/vehicles/sr_proton', 3814050971, 'WORKSHOP_ITEMTYPE_VEHICLE', 'Space Race: Proton'),
    'sr_n1': ('mod/vehicles/sr_n1', 3814051385, 'WORKSHOP_ITEMTYPE_VEHICLE', 'Space Race: N1-L3'),
}
KIT_OBJECTS = ('pad_r7', 'pad_n1', 'mik', 'rocket_plant', 'engine_plant', 'test_stand', 'lox_plant', 'propellant',
               'instruments', 'spacecraft', 'tracking', 'training', 'bureau', 'recovery', 'monument', 'gagarin')

FOOTER = '''[h2]LICENCE AND CREDITS[/h2]
GPL-3.0, source code on GitHub: [url=%(repo)s]%(repo)s[/url]. The goods plugin is a port of the one in TesmioLoader by MaxLegend; the plugins run on [url=%(rml)s]Republic Mod Loader[/url] by UltimateUniverse, whose Workshop pages also inspired the tone of this one.

Workers & Resources: Soviet Republic is (c) 3Division. This is an independent fan-made mod, not affiliated with or endorsed by 3Division or Hooded Horse.''' % {'repo': REPO, 'rml': RML}

PACKAGE = '''[h1]COMRADE, THE AMERICANS ARE BUILDING A ROCKET![/h1]
Your republic pours concrete by the thousand tonnes, bakes bread for a million citizens and runs trains on time, and yet the night sky above it contains [b]nothing Soviet whatsoever?[/b]

Your best graduates are wasting their education in a distribution office when they could be orbiting the planet?

[b]THE STATE COMMISSION HAS REVIEWED THIS SITUATION AND FOUND IT IDEOLOGICALLY UNACCEPTABLE.[/b]

The Ministry of General Machine Building (a name chosen so that nobody would guess what it builds) therefore presents the [b]Space Race[/b]: your republic becomes a spacefaring power, one satellite, cosmonaut and extremely large explosion at a time.

The objective is simple: [b]put a Soviet cosmonaut on the Moon before 20 July 1969.[/b] The Americans have a head start, a larger budget and Apollo 11. You have kerosene, liquid oxygen and a Five-Year Plan.

[h2]WHAT THE STATE HAS APPROVED[/h2]
[list]
[*][b]A space branch in the research tree[/b]: 17 entries from 1946 to 1966, each unlocking its buildings.
[*][b]16 buildings[/b] modelled on the real ones (the Space Race Kit): Gagarin's Start, the N1 complex, the MIK, the rocket, engine, oxygen and propellant plants, a test stand, instrument works, a spacecraft hall, the Pluton tracking station, Star City, OKB-1, a recovery field and two monuments.
[*][b]Five rockets[/b]: R-7 Sputnik, Vostok-K, Soyuz, Proton and the N1, built at the MIK and rolled out onto its launch pad.
[*][b]Launches[/b]: the propellant and payload are taken from storages near the pad, and the rocket climbs away on flame and smoke. Or it explodes.
[*][b]Cosmonauts, a fourth education tier[/b]: graduates who work at Star City become experts; OKB-1 trains chief designers.
[*][b]The programme[/b]: eight milestones against the real American timeline. Coming first pays in dollars and loyalty.
[*][b]Six new goods, if the republic wants them[/b]: rocket stages, rocket engines, avionics, liquid oxygen, hypergolic propellant and spacecraft.
[/list]
The programme sleeps until you research the Rocket Research Institute, so it waits politely in any ordinary republic.

[h2]HOW TO JOIN THE RACE[/h2]
[olist]
[*]Subscribe to this item, the [b]Space Race Kit[/b] and the five rockets (the Required Items on this page), and to [url=%(rml)s]Republic Mod Loader[/url].
[*]Run Republic Mod Loader, enable the Space Race items and their plugins (spacerace, experts, resources), and launch the game.
[*]Load your republic or start a new one. Research the Rocket Research Institute and the programme takes it from there.
[/olist]
Requires Workers & Resources: Soviet Republic [b]1.1.1.9[/b]: the plugins patch this exact build.

[h2]SAVES[/h2]
Out of the box ([b]new_goods = 0[/b]) the mod adds no goods, and your existing republic can join the race as it is: liquid oxygen travels as chemicals, rocket parts as mechanical components and spacecraft as electronics. The six new goods ([b]new_goods = 1[/b]) can be switched on for an existing republic too: load it and they join the economy. Switched off again, whatever is in stock becomes its stand-in and the next save is a plain one. Save once after each switch, and keep a backup: the Party always does.

[h2]THE PLAN IS NEGOTIABLE[/h2]
Every number is a recommendation from the Central Committee, not a law of physics. [b]plugins\\spacerace.ini[/b] in this item's folder holds them all, explained: research years and costs, the day the Americans reach each milestone (or never), failure chances, cosmonauts and tracking stations, launch loads, rocket parts, rewards, and the cost, staff and recipes of every building. A running republic keeps the programme rules it began with, so tampering with the timeline cannot break a race already under way. (Steam replaces the file when the mod updates: keep a copy of your changes.)

[h2]STATUS[/h2]
Early access. Every feature has run in the game, but nobody has played the whole race through yet. Reports are welcome, especially from comrades who reached the Moon.

[h2]REPORTING A LAUNCH FAILURE[/h2]
Tell us what happened, what you were doing, and attach the Republic Mod Loader log. Unlike TASS, we want to hear about failures.

''' % {'rml': RML} + FOOTER + '''

[b]Build the rockets. Train the cosmonauts. Beat Apollo 11. The Motherland is watching, Comrade, and so, unfortunately, are the Americans.[/b]'''

KIT = '''[h1]COMRADE, A COSMODROME DOES NOT BUILD ITSELF.[/h1]
It does, however, come as a kit. Sixteen buildings of the Soviet space programme, modelled on the real ones:
[list]
[*][b]Launch[/b]: the R-7 launch complex (Gagarin's Start), the N1 heavy complex (Site 110) and the MIK assembly building.
[*][b]Rockets and parts[/b]: the Progress rocket plant, the OKB-456 engine works, an engine test stand, the oxygen-nitrogen plant, a propellant plant, instrument works and a spacecraft assembly hall.
[*][b]Flight and crew[/b]: the Pluton deep space tracking station, Star City, OKB-1 and a landing and recovery field.
[*][b]Glory[/b]: the Monument to the Conquerors of Space and the Gagarin column.
[/list]
Part of the [b]Space Race[/b]: subscribe to [url=%s]the Space Race item[/url] too, which unlocks these buildings through its research branch and makes the rockets fly. See that item for how to play.

''' % (ITEM_URL % ITEMS['package'][1]) + FOOTER

ROCKETS = {
    'sr_sputnik': 'The Semyorka that opened the space age: Sputnik 1 on 4 October 1957, Laika a month later. Flies the first two milestones from the R-7 launch complex.',
    'sr_vostok': 'The R-7 with the Blok E upper stage: Luna probes to the Moon, then Gagarin. One cosmonaut.',
    'sr_soyuz': 'The workhorse: the Soyuz spacecraft and its escape tower. The spacewalk and the first docking.',
    'sr_proton': 'Chelomei\'s hypergolic heavy lifter. Flies Zond around the Moon, with tortoises aboard. Historically, they came back.',
    'sr_n1': 'The Moon rocket: 30 engines, 105 m, and the only rocket that fits the heavy launch complex. Historically it launched four times and exploded four times. Research the NK-33 engines first.',
}


def rocket_desc(key):
    return ('[h1]%s[/h1]\n%s\n\nBuilt at the MIK from rocket stages, engines and avionics, rolled out onto its launch pad and '
            'launched by the Space Race programme. Part of the [b]Space Race[/b]: subscribe to [url=%s]the Space Race item[/url] '
            'and [url=%s]the Space Race Kit[/url] too.\n\n'
            % (ITEMS[key][3].replace('Space Race: ', ''), ROCKETS[key], ITEM_URL % ITEMS['package'][1], ITEM_URL % ITEMS['kit'][1])) + FOOTER


def config(key, desc, objects):
    folder, item, typ, name = ITEMS[key]
    assert len(desc) < 8000, '%s: Steam descriptions stop at 8000 characters (%d)' % (key, len(desc))
    assert '"' not in desc, '%s: no double quotes inside $ITEM_DESC' % key
    lines = ['$ITEM_ID %d' % item, '', '$OWNER_ID %d' % OWNER, '', '$ITEM_TYPE %s' % typ, '', '$VISIBILITY %d' % VISIBILITY, '']
    lines += objects + ([''] if objects else [])
    lines += ['$ITEM_NAME "%s"' % name, '', '$ITEM_DESC "%s"' % desc.replace('\n', '\r\n'), '', '$END', '']
    path = os.path.join(ROOT, folder, 'workshopconfig.ini')
    open(path, 'w', encoding='utf-8', newline='').write('\r\n'.join(lines))
    print('%-11s %d  %-28s %5d chars  %s' % (key, item, name, len(desc), os.path.relpath(path, ROOT)))


def new_items(out):
    """What the game's "create new item" form asks for, one PNG + one UTF-8 TXT per item, numbered in upload order."""
    import shutil
    os.makedirs(out, exist_ok=True)
    descs = {'package': PACKAGE, 'kit': KIT}
    descs.update((k, rocket_desc(k)) for k in ROCKETS)
    order = ['kit'] + list(ROCKETS) + ['package']
    lines = ['Create each item in the game (Workshop -> Your items (WIP) -> green +), visibility Unpublished:', '']
    for n, key in enumerate(order, 1):
        folder, _item, typ, name = ITEMS[key]
        base = '%d_%s' % (n, key)
        png = os.path.join(ROOT, folder, 'previewimage.png')
        assert os.path.getsize(png) < 1 << 20, '%s: the game refuses previews of 1 MB or more' % key
        shutil.copy2(png, os.path.join(out, base + '.png'))
        open(os.path.join(out, base + '.txt'), 'w', encoding='utf-8', newline='').write(descs[key].replace('\n', '\r\n'))
        lines.append('%d. %-26s type %-8s image %s.png  description %s.txt'
                     % (n, name, typ.replace('WORKSHOP_ITEMTYPE_', '').title(), base, base))
    open(os.path.join(out, 'ITEMS.txt'), 'w', encoding='utf-8', newline='').write('\r\n'.join(lines + ['']))
    print('\n'.join(lines) + '\n-> ' + out)


def main():
    if sys.argv[1:2] == ['new']:
        return new_items(os.path.join(ROOT, 'build', 'workshop_new', 'space_race'))
    config('package', PACKAGE, [])
    config('kit', KIT, ['$OBJECT_BUILDING sr_%s' % k for k in KIT_OBJECTS])
    for key in ROCKETS:
        config(key, rocket_desc(key), ['$OBJECT_VEHICLE %s' % key])
    # the research branch unlocks the kit's buildings by its item id
    ini = os.path.join(ROOT, 'mod', 'plugins', 'spacerace', 'spacerace.ini')
    text = open(ini, encoding='utf-8', newline='').read()
    new = re.sub(r'(?m)^kit_item[ \t]*=[^\r\n]*', 'kit_item  = %d' % ITEMS['kit'][1], text)
    if new != text:
        open(ini, 'w', encoding='utf-8', newline='').write(new)
    print('spacerace.ini kit_item = %d' % ITEMS['kit'][1])


if __name__ == '__main__':
    main()
