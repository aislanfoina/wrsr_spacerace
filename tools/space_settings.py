"""The Space Race's balance settings: every value a player may change, with its default.

    python tools/space_settings.py

Writes
    mod/plugins/spacerace/data/defaults.ini   every value; the plugin reads it before spacerace.ini,
                                              so a line a player deletes falls back to its default
    mod/plugins/spacerace/spacerace.ini       the part below the balance marker (the [general]
                                              part above it is kept as it is)
from space_research.TREE, space_scenario (milestones, loads, launches, rewards), space_goods.BILL
and the kit's generated building.ini files. Run it after space_scene.py and space_scenario.py.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import space_goods as G  # noqa: E402
import space_research as SR  # noqa: E402
import space_scenario as SC  # noqa: E402

ROOT = SC.ROOT
PLUGIN = os.path.join(ROOT, 'mod', 'plugins', 'spacerace')
INI = os.path.join(PLUGIN, 'spacerace.ini')
DEFAULTS = os.path.join(PLUGIN, 'data', 'defaults.ini')
MARKER = '; ---- balance: written by tools/space_settings.py from the generators\' defaults ----'

# the kit in the order a player meets it
KIT_ORDER = ('sr_pad_r7', 'sr_pad_n1', 'sr_mik', 'sr_rocket_plant', 'sr_engine_plant', 'sr_test_stand', 'sr_lox_plant',
             'sr_propellant', 'sr_instruments', 'sr_spacecraft', 'sr_tracking', 'sr_training', 'sr_bureau',
             'sr_recovery', 'sr_monument', 'sr_gagarin')


def num(v):
    return ('%.4f' % v).rstrip('0').rstrip('.') if isinstance(v, float) else '%d' % v


def pairs(items):
    return ', '.join('%s %s' % (k, num(v)) for k, v in items)


def line(key, value, note=None, width=34):
    s = '%s = %s' % (key, value)
    return '%-*s ; %s' % (width, s, note) if note else s


def building(obj):
    """What a kit building says with the new goods (the settings name them; the plugin maps them to
    stand-ins when new_goods = 0): name, type, staff, production, consumption."""
    b = dict(name=obj, type='', workers=None, educated=None, production=[], consumption=[])
    for raw in open(os.path.join(PLUGIN, 'data', 'goods_buildings', obj + '.ini'), encoding='utf-8', errors='replace'):
        t = raw.split()
        if not t:
            continue
        if t[0] == '$NAME_STR' and b['name'] == obj:
            b['name'] = raw.split('"')[1] if '"' in raw else obj
        elif t[0].startswith('$TYPE_') and not b['type']:
            b['type'] = t[0][6:]
        elif t[0] == '$WORKERS_NEEDED':
            b['workers'] = int(t[1])
        elif t[0] == '$PROFESORS_NEEDED':
            b['educated'] = int(t[1])
        elif t[0] == '$PRODUCTION':
            b['production'].append((t[1], float(t[2])))
        elif t[0] == '$CONSUMPTION':
            b['consumption'].append((t[1], float(t[2])))
    return b


def balance():
    """The balance part, as lines."""
    out = []
    a = out.append
    a('; Change any value and restart the game. Research, buildings and rocket parts apply to every')
    a('; game, saves included. The programme\'s rules - [america], [milestones], [rockets], [launches]')
    a('; and [rewards] - are fixed when a game starts: a running game keeps the rules it began with,')
    a('; and new games take the current ones. (The plugin writes each set of rules as a mission of its')
    a('; own, media_soviet\\scenarios\\spacerace\\race_<code>, and leaves every one it wrote in place.)')
    a('; Cosmonaut and chief-designer training - how long, how many, who - is in experts.ini.')

    a('')
    a('[research]')
    a('; <entry> = year <first year it can be researched>, cost <research points>')
    a(line('year_shift', 0, 'added to every year: -10 starts the space age a decade early'))
    a(line('cost_scale', '1.0', 'multiplies every cost'))
    for rid, typ, cost, year, parents, blds, name, *_r in SR.TREE:
        a(line(rid, 'year %d, cost %d' % (year, cost), name, 40))

    a('')
    a('[america]')
    a('; the day the United States reaches each milestone (YYYY-MM-DD), or never')
    a(line('year_shift', 0, 'added to every year: 5 gives the Americans five slower years'))
    for m in SC.MILESTONES:
        a(line(m['key'], m['us_date'], '%s (%s)' % (m['us_what'], m['title'])))

    a('')
    a('[milestones]')
    a('; failure  % chance the launch fails, before any earlier success of its rocket')
    a('; crew     cosmonauts (experts) the republic needs; tracking  tracking stations it needs')
    for m in SC.MILESTONES:
        a(line(m['key'], 'failure %d, crew %d, tracking %d' % (m['fail'], m['crew'], m['track']),
               '%s (%s)' % (m['title'], m['rocket']), 40))

    a('')
    a('[rockets]')
    a('; what a launch takes from storage buildings near its pad, in tonnes: fuel, lox, hypergolic,')
    a('; spacecraft and food (the programme checks those five). With new_goods = 0 their stand-ins')
    a('; are taken: chemicals for lox and hypergolic, electronics for spacecraft.')
    names = {}
    for m in SC.MILESTONES:
        names.setdefault(SC.ROCKET_OF[m['power']], m['rocket'])
    for obj, load in SC.LOADS.items():
        a(line(obj, pairs((SC.GOOD[k], load[k]) for k, _ in SC.LOAD_KEYS if load[k]), names[obj], 52))

    a('')
    a('[rocket_parts]')
    a('; what the MIK builds each rocket from, in tonnes (the workdays stay the game\'s); the MIK')
    a('; takes in rocket stages, rocket engines and avionics. new_goods = 1 only: with stand-ins the')
    a('; MIK takes the game\'s own vehicle parts, worked out from each rocket\'s weight.')
    for obj, bill in G.BILL.items():
        a(line(obj, pairs(bill), names[obj], 52))

    a('')
    a('[launches]')
    for k, v, note in SC.LAUNCHES:
        a(line(k, v, note, 26))

    a('')
    a('[rewards]')
    for k, v, note in SC.REWARDS:
        a(line(k, v, note, 30))

    a('')
    a('[buildings]')
    a(line('cost_scale', '1.0', 'multiplies the construction cost of every Space Race building', 26))
    a(';')
    a('; [building:<object>] for each one:')
    a(';   cost         auto = sized from the model, the way the kit ships; or absolute amounts,')
    a(';                e.g. workers 20000, concrete 900, steel 350, asphalt 60 (workers = workdays)')
    a(';   cost_scale   multiplies this building\'s cost')
    a(';   workers      staff it needs; educated = how many of them need a university education')
    a(';   production   <good> <tonnes per worker per day>, ...  (factories)')
    a(';   consumption  <good> <tonnes per worker per day>, ...  (a new good also needs a storage')
    a(';                slot in the building, which only the kit generator can add)')
    a('; Recipes name the new goods; with new_goods = 0 each is read as its stand-in, and an input')
    a('; that becomes the factory\'s own output is left out.')
    for obj in KIT_ORDER:
        b = building(obj)
        a('')
        a('[building:%s]%s; %s' % (obj, ' ' * max(1, 26 - len(obj)), b['name']))
        a('cost = auto')
        if b['workers'] is not None:
            a('workers = %d' % b['workers'])
        if b['educated'] is not None:
            a('educated = %d' % b['educated'])
        if b['type'] == 'FACTORY':
            if b['production']:
                a('production = ' + pairs(b['production']))
            if b['consumption']:
                a('consumption = ' + pairs(b['consumption']))
    return out


def main():
    body = balance()
    kit = sorted(d for d in os.listdir(SC.KIT) if d.startswith('sr_'))
    assert sorted(KIT_ORDER) == kit, 'KIT_ORDER misses %s' % sorted(set(kit) ^ set(KIT_ORDER))
    open(DEFAULTS, 'w', encoding='utf-8', newline='').write('\r\n'.join(
        ['; generated by tools/space_settings.py - the defaults of every spacerace.ini balance value.',
         '; The plugin reads this first and spacerace.ini second. Edit spacerace.ini, not this.', ''] + body) + '\r\n')
    text = open(INI, encoding='utf-8').read().replace('\r\n', '\n')
    head = text.split(MARKER)[0].rstrip('\n') if MARKER in text else text.rstrip('\n')
    open(INI, 'w', encoding='utf-8', newline='').write('\r\n'.join(head.split('\n') + ['', MARKER, ''] + body) + '\r\n')
    print('settings: %d lines -> %s and %s' % (len(body), os.path.relpath(INI, ROOT), os.path.relpath(DEFAULTS, ROOT)))


if __name__ == '__main__':
    main()
