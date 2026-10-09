"""The Space Race programme: a persistent scenario the spacerace plugin starts in
any ordinary game, gated by the space research branch.

    python tools/space_scenario.py

Writes mod/plugins/spacerace/data/ (the plugin ships that folder):
    programme/race.tmpl           the VM script as a template: every number a player may change
                                  is an @token@ the plugin fills in from spacerace.ini
    programme/milestones.txt      the milestones in template order and the rocket each one flies
    programme/script.ini          the mission header every rendered programme gets
    programme/*.png               window images, from the kit's renders
    scenarios/spacerace/          the scenario header and the frozen legacy missions (legacy/)
    launches.ini                  pads, effects, script goods, stand-ins, default loads and rocket bills
and build/space_programme_default_goods0.txt / _goods1.txt, the template rendered with the defaults
for vanilla stand-in goods and for the new goods (checked by tools/vmcheck.py; the plugin's own
rendering of unchanged settings should match the one for its new_goods).

The plugin renders the template at start-up into scenarios/spacerace/race_<hash>/, a mission of
its own for every set of settings: a save keeps the running programme's state, so a game keeps
the rules it began with while new games take the current ones.

How it plays: the script sleeps, invisible, until the republic joins: the Rocket Research
Institute researched and the Design Bureau (OKB-1) built (a hint appears once the research is
done). The American timeline starts from that day: a late programme shifts it or leaves the past
to the Americans without a penalty ([america] start / late_start). Then it walks the milestones
in order. Each milestone waits for its research, a rocket of the right type
parked on a launch pad (a heliport-type building it is assigned to), propellant and payload in
storages near the pad, cosmonauts (experts, education >= 3) and tracking stations. Then it
launches: the goods are consumed, a failure roll decides (it falls with every success of that
rocket; the N1 needs the NK-33 research), a failure burns the pad. The American timeline runs
beside it by date; being first pays in dollars and loyalty, the Americans getting there first
costs loyalty. The last milestone is the N1 landing on the Moon.

Rockets are recognised by their engine power (9001..9005 kW, set in space_vehicles.py) because
the VM's Vehicle struct has no type name. Tracking stations and engine test stands are
recognised by their staff numbers, so those come from the buildings' settings.
"""
import os
import shutil
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'mod', 'plugins', 'spacerace', 'data')
OUT = os.path.join(DATA, 'scenarios', 'spacerace')
PROG = os.path.join(DATA, 'programme')
DEFAULT_RENDER = os.path.join(ROOT, 'build', 'space_programme_default_goods%d.txt')   # new_goods 0 / 1
KIT = os.path.join(ROOT, 'mod', 'buildings', 'space_kit')
import space_goods as G  # noqa: E402  (the goods, shared with space_scene.py)
# design goods a launch uses -> the game good and the script field that reads it
LOAD_KEYS = (('fuel', 'fuel'), ('lox', 'lox'), ('hyper', 'hypergolic'), ('craft', 'spacecraft'), ('food', 'space_food'))
GOOD = {k: G.good(g) for k, g in LOAD_KEYS}          # the new goods' names; the plugin maps them to stand-ins
# Saves that run an older programme keep it: every mission they may run lives on, frozen, in
# mod/plugins/spacerace/legacy/ and is copied in beside the rendered ones.
LEGACY = os.path.join(ROOT, 'mod', 'plugins', 'spacerace', 'legacy')

# ------------------------------------------------------------ settings defaults
# spacerace.ini [launches] and [rewards] (tools/space_settings.py writes them out with these notes)
LAUNCHES = [
    ('radius', 450, 'storage buildings this close to the pad supply a launch (m)'),
    ('park_distance', 90, 'a rocket counts as standing on its pad this close to it (m)'),
    ('climb_seconds', 18, 'how long a rocket climbs before it leaves the map (s)'),
    ('pad_repair_days', 30, 'a failed launch closes the pad this long in games without building fires'),
    ('failure_per_success', 5, 'each earlier success of the same rocket lowers its failure chance (%)'),
    ('failure_test_stand', 10, 'an engine test stand anywhere in the republic lowers every failure chance (%)'),
    ('failure_nk33', 35, 'the NK-33 research lowers the N1\'s failure chance (%)'),
    ('failure_min', 5, 'no launch is ever safer than this (% failure)'),
]
REWARDS = [
    ('first_money', 25000, 'USD for reaching a milestone before the Americans'),
    ('first_loyalty', 12, 'loyalty for every citizen then (%)'),
    ('second_money', 5000, 'USD for reaching it after them'),
    ('second_loyalty', 3, 'loyalty then (%)'),
    ('america_first_loyalty', -5, 'loyalty when the Americans reach a milestone first (%)'),
    ('victory_money', 100000, 'USD for the Moon before the Americans'),
    ('victory_loyalty', 20, 'loyalty then (%)'),
]
L = dict((k, v) for k, v, _ in LAUNCHES)
R = dict((k, v) for k, v, _ in REWARDS)

# power: 9001 Sputnik, 9002 Vostok-K, 9003 Soyuz, 9004 Proton, 9005 N1
MILESTONES = [
    dict(key='sputnik', research='sr_satellite', power=9001, rocket='R-7 Sputnik', crew=0, track=0,
         fuel=8, lox=20, craft=1, food=0, fail=30, icon='sr_satellite',
         title='The first satellite',
         brief='Put an artificial satellite into orbit. Park an R-7 Sputnik rocket on a launch complex, store kerosene, liquid oxygen and the satellite in storage buildings within {radius} m of the pad, and it will fly.',
         win='Beep... beep... beep. Sputnik is in orbit and every radio on Earth can hear it. The space age has begun, and it began here.',
         us_date='1958-01-31', us_what='Explorer 1', us_text='Explorer 1 is in orbit. The Americans have their satellite.'),
    dict(key='laika', research='sr_biosatellite', power=9001, rocket='R-7 Sputnik', crew=0, track=0,
         fuel=8, lox=20, craft=2, food=1, fail=25, icon='sr_biosatellite',
         title='A passenger in orbit',
         brief='Send a living passenger into orbit: a satellite with life support and food for the flight. Belka and Strelka came back; Laika did not.',
         win='A living creature has orbited the Earth. Now we know a cosmonaut can survive up there.',
         us_date='1961-01-31', us_what='Ham the chimpanzee', us_text='Ham the chimpanzee has flown in an American capsule.'),
    dict(key='luna', research='sr_lunar_probes', power=9002, rocket='Vostok-K', crew=0, track=1,
         fuel=10, lox=25, craft=2, food=0, fail=35, icon='sr_lunar_probes',
         title='To the Moon',
         brief='Hit the Moon with a Luna probe. The Vostok-K and its Blok E upper stage can reach escape velocity; a tracking station must follow it.',
         win='Luna has reached the Moon and left the pennant of the Soviet Union on its surface.',
         us_date='1962-04-26', us_what='Ranger 4', us_text='Ranger 4 has struck the far side of the Moon.'),
    dict(key='vostok', research='sr_manned_flight', power=9002, rocket='Vostok-K', crew=1, track=1,
         fuel=10, lox=25, craft=5, food=1, fail=15, icon='sr_manned_flight',
         title='The first man in space',
         brief='Put a cosmonaut into orbit and bring him back. You need a Vostok-K on the pad, the Vostok spacecraft, a trained cosmonaut (an expert from the Cosmonaut Training Centre) and a tracking station.',
         win='Poyekhali! A Soviet cosmonaut has orbited the Earth and landed safely in the steppe. The whole world knows his name.',
         us_date='1962-02-20', us_what='John Glenn', us_text='John Glenn has orbited the Earth in Friendship 7.'),
    dict(key='voskhod', research='sr_eva', power=9003, rocket='Soyuz', crew=2, track=1,
         fuel=12, lox=30, craft=6, food=1, fail=15, icon='sr_eva',
         title='A walk in space',
         brief='Cosmonauts, an inflatable airlock and the first walk outside a spacecraft.',
         win='A cosmonaut has floated outside his ship for twelve minutes, and got back in.',
         us_date='1965-06-03', us_what='Ed White', us_text='Ed White has walked in space from Gemini 4.'),
    dict(key='soyuz', research='sr_soyuz', power=9003, rocket='Soyuz', crew=3, track=2,
         fuel=12, lox=30, craft=7, food=2, fail=15, icon='sr_soyuz',
         title='Rendezvous and docking',
         brief='The Soyuz: a crew of cosmonauts, rendezvous and docking in orbit - everything a Moon flight needs. Tracking stations must follow it.',
         win='Two ships have met and docked in orbit. The road to the Moon is open.',
         us_date='1966-03-16', us_what='Gemini 8', us_text='Gemini 8 has docked with its Agena target.'),
    dict(key='zond', research='sr_proton', power=9004, rocket='Proton', crew=0, track=2,
         fuel=0, lox=0, hyper=60, craft=8, food=0, fail=35, icon='sr_proton',
         title='Around the Moon',
         brief='Send a Zond spacecraft around the Moon and back on the Proton. It burns storable hypergolic propellant.',
         win='Zond has flown round the Moon and splashed down with its tortoises alive.',
         us_date='1968-12-21', us_what='Apollo 8', us_text='Apollo 8 is in orbit around the Moon with three astronauts aboard.'),
    dict(key='moon', research='sr_lunar_landing', power=9005, rocket='N1-L3', crew=2, track=3,
         fuel=80, lox=200, craft=25, food=3, fail=70, icon='sr_lunar_landing',
         title='A Soviet footprint on the Moon',
         brief='The N1 has to fly. Park it on the Heavy Launch Complex with its kerosene, liquid oxygen and the lunar spacecraft in reach, cosmonauts ready and tracking stations to follow it. Without the NK-33 engines most N1s explode.',
         win='The LK has landed. A Soviet cosmonaut stands on the Moon.',
         us_date='1969-07-20', us_what='Apollo 11', us_text='Apollo 11 has landed on the Moon. Neil Armstrong walks on its surface.'),
]


# the rocket each engine-power fingerprint stands for, and the load it takes at lift-off: the
# largest any of its milestones needs, so what the objective asks for is what the plugin takes
ROCKET_OF = {9001: 'sr_sputnik', 9002: 'sr_vostok', 9003: 'sr_soyuz', 9004: 'sr_proton', 9005: 'sr_n1'}
LOADS = {}
for _m in MILESTONES:
    _m.setdefault('hyper', 0)
    _l = LOADS.setdefault(ROCKET_OF[_m['power']], {k: 0 for k, _ in LOAD_KEYS})
    for _k, _ in LOAD_KEYS:
        _l[_k] = max(_l[_k], _m[_k])
for _m in MILESTONES:
    _m.update(LOADS[ROCKET_OF[_m['power']]])
PAD_OF = {'sr_n1': 'sr_pad_n1'}      # every other rocket stands on the R-7 complex

MONTHS = ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
          'November', 'December')
MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

# spacerace.ini [america] start / late_start. The American dates assume the programme opens by
# AMERICA_START. One that opens later (a republic that reaches space in 1975, or a save that gets
# the mod late) either shifts every American date by the delay - a whole race, just later - or
# keeps the real dates: what the Americans did before the programme opened is then history, with
# no loyalty lost for it, and reaching it pays the catch-up reward.
AMERICA_START = '1954-01-01'
LATE_START = 'shift'                  # or 'history'


def day_of_year(date):
    """Year and day (1-365) of a YYYY-MM-DD date in the game's 365-day calendar (Date_GetCurrentDate_D365Y);
    the plugin does the same sum."""
    y, m, d = (int(x) for x in date.split('-'))
    return y, sum(MONTH_DAYS[:m - 1]) + min(d, MONTH_DAYS[m - 1])


def date_text(date):
    y, m, d = (int(x) for x in date.split('-'))
    return '%d %s %d' % (d, MONTHS[m - 1], y)


def day_number(date):
    """A date as the script counts days: year * 365 + day of the year."""
    y, d = day_of_year(date)
    return y * 365 + d


def years_text(days):
    """'in about 16 years' for a span of days; the plugin words it the same way."""
    years = (days + 182) // 365
    return 'in about %d years' % years if years > 1 else 'in about a year' if years == 1 else 'within a year'


def staff(obj):
    """(workers, educated) a kit building needs, from its generated building.ini."""
    w = e = 0
    for line in open(os.path.join(KIT, obj, 'building.ini'), encoding='utf-8', errors='replace'):
        t = line.split()
        if len(t) >= 2 and t[0] == '$WORKERS_NEEDED':
            w = int(t[1])
        elif len(t) >= 2 and t[0] == '$PROFESORS_NEEDED':
            e = int(t[1])
    return w, e


def fmt_float(v):
    """Floats as the plugin writes them: two decimals, a negative one as 0.0 - x (the VM has no
    negative literals)."""
    return '0.0 - %.2f' % -v if v < 0 else '%.2f' % v


class Tok:
    """The numbers a player may change. In the template they are @name@ for the plugin to fill in;
    rendered, they are the defaults (so the script can be checked here). The plugin computes every
    token from spacerace.ini the same way; the names are its contract with this file."""
    def __init__(self, template):
        self.template = template
        self.values = {}

    def _put(self, name, text):
        assert self.values.setdefault(name, text) == text, 'token %s used with two values' % name
        return '@%s@' % name if self.template else text

    def i(self, name, v):
        return self._put(name, '%d' % v)

    def f(self, name, v):
        return self._put(name, fmt_float(v))

    def s(self, name, v):
        return self._put(name, v)


def research_name(key):
    """Display name of a space research entry, from space_research.TREE."""
    import space_research
    for e in space_research.TREE:
        if e[0] == key:
            return e[6]
    return key


def esc(s):
    return s.replace('"', "'")


def fields(new_goods):
    """The Resources field the script reads each load kind from, and the payload's good, with the
    six new goods (spacerace.ini new_goods = 1) or their vanilla stand-ins (0)."""
    saved = G.USE_NEW_GOODS
    G.USE_NEW_GOODS = new_goods
    try:
        return {k: G.field(g) for k, g in LOAD_KEYS}, G.good('spacecraft')
    finally:
        G.USE_NEW_GOODS = saved


def gen_script(t, new_goods=False):
    field, craft_good = fields(new_goods)
    stand_w, stand_e = staff('sr_test_stand')
    track_w, track_e = staff('sr_tracking')
    moon = MILESTONES[-1]
    L_ = []
    a = L_.append
    a('include("SOVIETInstructions.txt");')
    a('')
    for v in ('i', 'j', 'k', 'n', 'r', 'day', 'year', 'winexist', 'bContinue', 'nVeh', 'nPad', 'nExperts', 'nTrack',
              'nResearch', 'fi', 'fj', 'fk', 'fn', 'si', 'sn', 'ti', 'tn', 'bi', 'bn', 'ci', 'cn',
              'li', 'ln', 'lk', 'rr', 'ki', 'kn', 'nCosmo', 'nCosmoShown', 'bObjReady', 'bCosmoObj',
              'nBlockedPad', 'nBlockUntil', 'nNow', 'nPadOK', 'nTest', 'nNeedCrew', 'nNeedTrack',
              'nStart', 'nShift', 'nAhead', 'bHinted', 'nBureau'):
        a('defineVariable(int, %s);' % v)
    for v in ('f', 'f2', 'fFail', 'fFuel', 'fLox', 'fHyper', 'fCraft', 'fFood', 'fDist', 'fLoyal', 'fr', 'fCosmo', 'fUp',
              'fNeed'):
        a('defineVariable(float, %s);' % v)
    a('defineVariable(vec3, padPos);')
    a('defineVariable(vec3, vtmp);')
    a('defineVariable(vec3, cosmoPos);')
    a('defineVariable(GameSetting, gs);')
    a('defineVariable(Building, bui);')
    a('defineVariable(Vehicle, vehi);')
    a('defineVariable(Person, wor);')
    a('defineVariable(Resources, res);')
    a('defineArray(int[%d], srDone);' % len(MILESTONES))
    a('defineArray(int[%d], usDone);' % len(MILESTONES))
    a('defineArray(int[%d], usDue);' % len(MILESTONES))
    a('defineArray(int[6], rocketOK);')
    a('')
    # --- experts: citizens with education >= 3 (the experts plugin makes them)
    a('defineFunction(CountExperts, int)')
    a('{')
    a('\tfn = 0;')
    a('\tScript_SetUpdateFrequency(20000);')
    a('\tPerson_GetNumberOfPeople(cn);')
    a('\tfor (ci=0, ci<cn, ci=ci+1)')
    a('\t{')
    a('\t\twor.GetDataByIndex(ci);')
    a('\t\tif (wor.nValidRead & wor.fEducation > 2.999)')
    a('\t\t{')
    a('\t\t\tfn = fn + 1;')
    a('\t\t}')
    a('\t}')
    a('\tScript_SetUpdateFrequency(5000);')
    a('\treturn(fn);')
    a('}')
    a('')
    # --- engine test stands and tracking stations: known by their type and staff numbers
    a('defineFunction(CountTestStands, int)')
    a('{')
    a('\tfk = 0;')
    a('\tBuilding_GetNumberOfBuildings(bn);')
    a('\tfor (bi=0, bi<bn, bi=bi+1)')
    a('\t{')
    a('\t\tbui.GetDataByIndex(bi);')
    a('\t\tif (bui.nValidRead & bui.nType ? BUILDINGTYPE_FACTORY & bui.nWorkersNeeded ? %s & bui.nProffesorsNeeded ? %s & bui.fPercFinished > 0.9999 & bui.nWorkersNum > 0)'
      % (t.i('stand_workers', stand_w), t.i('stand_educated', stand_e)))
    a('\t\t{')
    a('\t\t\tfk = fk + 1;')
    a('\t\t}')
    a('\t}')
    a('\treturn(fk);')
    a('}')
    a('')
    a('defineFunction(CountTracking, int)')
    a('{')
    a('\tfk = 0;')
    a('\tBuilding_GetNumberOfBuildings(bn);')
    a('\tfor (bi=0, bi<bn, bi=bi+1)')
    a('\t{')
    a('\t\tbui.GetDataByIndex(bi);')
    a('\t\tif (bui.nValidRead & bui.nType ? BUILDINGTYPE_BROADCAST & bui.nProffesorsNeeded ? %s & bui.nWorkersNeeded ? %s & bui.fPercFinished > 0.9999)'
      % (t.i('track_educated', track_e), t.i('track_workers', track_w)))
    a('\t\t{')
    a('\t\t\tfk = fk + 1;')
    a('\t\t}')
    a('\t}')
    a('\treturn(fk);')
    a('}')
    a('')
    # --- the Design Bureau (OKB-1): building it is how a republic joins the race
    bureau_w, bureau_e = staff('sr_bureau')
    a('defineFunction(CountBureaus, int)')
    a('{')
    a('\tfk = 0;')
    a('\tBuilding_GetNumberOfBuildings(bn);')
    a('\tfor (bi=0, bi<bn, bi=bi+1)')
    a('\t{')
    a('\t\tbui.GetDataByIndex(bi);')
    a('\t\tif (bui.nValidRead & bui.nType ? BUILDINGTYPE_UNIVERSITY & bui.nWorkersNeeded ? %s & bui.nProffesorsNeeded ? %s & bui.fPercFinished > 0.9999)'
      % (t.i('bureau_workers', bureau_w), t.i('bureau_educated', bureau_e)))
    a('\t\t{')
    a('\t\t\tfk = fk + 1;')
    a('\t\t}')
    a('\t}')
    a('\treturn(fk);')
    a('}')
    a('')
    # --- a rocket of the wanted power, parked at the heliport-type building it belongs to
    a('defineFunction(FindRocket, int, float:fPowerWanted)')
    a('{')
    a('\tfi = 0 - 1;')
    a('\tVehicle_GetNumberOfVehicles(tn);')
    a('\tfor (ti=0, ti<tn, ti=ti+1)')
    a('\t{')
    a('\t\tvehi.GetDataByIndex(ti);')
    a('\t\tif (vehi.nValidRead & vehi.nVehicleType ? VEHICLETYPE_HELICOPTER & vehi.fType_EnginePower > fPowerWanted - 0.5 & vehi.fType_EnginePower < fPowerWanted + 0.5)')
    a('\t\t{')
    a('\t\t\tfj = vehi.nBuilding_HomeWorkplaceID;')
    a('\t\t\tif (fj > -1)')
    a('\t\t\t{')
    a('\t\t\t\tbui.GetDataByIndex(fj);')
    a('\t\t\t\tif (bui.nValidRead & bui.nType ? BUILDINGTYPE_AIRPLANE_PARKING)')
    a('\t\t\t\t{')
    a('\t\t\t\t\tfDist = DistancePoints2D(vehi.vPosition, bui.vPosition);')
    a('\t\t\t\t\tnPadOK = 1;')
    a('\t\t\t\t\tif (fj ? nBlockedPad)')
    a('\t\t\t\t\t{')
    a('\t\t\t\t\t\tnNow = year * 365 + day;')
    a('\t\t\t\t\t\tif (nNow < nBlockUntil)')
    a('\t\t\t\t\t\t{')
    a('\t\t\t\t\t\t\tnPadOK = 0;')
    a('\t\t\t\t\t\t}')
    a('\t\t\t\t\t}')
    a('\t\t\t\t\tif (fDist < %s & nPadOK)' % t.f('park', L['park_distance']))
    a('\t\t\t\t\t{')
    a('\t\t\t\t\t\tfi = ti;')
    a('\t\t\t\t\t\tnPad = fj;')
    a('\t\t\t\t\t\tpadPos = bui.vPosition;')
    a('\t\t\t\t\t}')
    a('\t\t\t\t}')
    a('\t\t\t}')
    a('\t\t}')
    a('\t}')
    a('\treturn(fi);')
    a('}')
    a('')
    # --- goods stored near the pad
    a('defineFunction(SumNear, void)')
    a('{')
    a('\tfFuel = 0; fLox = 0; fHyper = 0; fCraft = 0; fFood = 0;')
    a('\tScript_SetUpdateFrequency(20000);')
    a('\tBuilding_GetNumberOfBuildings(sn);')
    a('\tfor (si=0, si<sn, si=si+1)')
    a('\t{')
    a('\t\tbui.GetDataByIndex(si);')
    a('\t\tif (bui.nValidRead & bui.nType ? BUILDINGTYPE_STORAGE & bui.nStorageNum > 0)')
    a('\t\t{')
    a('\t\t\tfDist = DistancePoints2D(bui.vPosition, padPos);')
    a('\t\t\tif (fDist < %s)' % t.f('radius', L['radius']))
    a('\t\t\t{')
    a('\t\t\t\tres.ResetAmounts();')
    a('\t\t\t\tres.GetFromBuilding(si);')
    for var, kind in (('fFuel', 'fuel'), ('fLox', 'lox'), ('fHyper', 'hyper'), ('fCraft', 'craft'), ('fFood', 'food')):
        a('\t\t\t\t%s = %s + res.%s;' % (var, var, t.s('field_' + kind, field[kind])))
    a('\t\t\t}')
    a('\t\t}')
    a('\t}')
    a('\tScript_SetUpdateFrequency(5000);')
    a('\treturnVoid();')
    a('}')
    a('')
    # --- research that counts as done: really researched, or research switched off in this game
    a('defineFunction(IsResearched, int, string:sResearchKey)')
    a('{')
    a('\tgs.GetCurrentGameSettigns();')
    a('\tif (!gs.Research)')
    a('\t{')
    a('\t\treturn(1);')
    a('\t}')
    a('\trr = 0;')
    a('\tResearch_IsCompleted(sResearchKey, rr);')
    a('\treturn(rr);')
    a('}')
    a('')
    # --- the rocket being launched: flagged by Vehicle_SetCanSell until the spacerace plugin has
    # --- flown it (lk = 1 while flagged), or already high above its pad
    a('defineFunction(FindLaunched, int, float:fPowerLaunched)')
    a('{')
    a('\tli = 0 - 1;')
    a('\tlk = 0;')
    a('\tVehicle_GetNumberOfVehicles(ln);')
    a('\tfor (ki=0, ki<ln, ki=ki+1)')
    a('\t{')
    a('\t\tvehi.GetDataByIndex(ki);')
    a('\t\tif (vehi.nValidRead & vehi.nVehicleType ? VEHICLETYPE_HELICOPTER & vehi.fType_EnginePower > fPowerLaunched - 0.5 & vehi.fType_EnginePower < fPowerLaunched + 0.5)')
    a('\t\t{')
    a('\t\t\tvtmp = vehi.vPosition;')
    a('\t\t\tfUp = vtmp.y - padPos.y;')
    a('\t\t\tif (vehi.bDisableSell)')
    a('\t\t\t{')
    a('\t\t\t\tli = ki;')
    a('\t\t\t\tlk = 1;')
    a('\t\t\t}')
    a('\t\t\telse()')
    a('\t\t\t{')
    a('\t\t\t\tif (fUp > 20.0)')
    a('\t\t\t\t{')
    a('\t\t\t\t\tli = ki;')
    a('\t\t\t\t}')
    a('\t\t\t}')
    a('\t\t}')
    a('\t}')
    a('\treturn(li);')
    a('}')
    a('')
    # --- experts (education >= 3): a permanent line in the objective and a notice for each new one
    a('defineFunction(CheckCosmonauts, void)')
    a('{')
    a('\tif (bObjReady)')
    a('\t{')
    a('\t\tnCosmo = 0;')
    a('\t\tScript_SetUpdateFrequency(20000);')
    a('\t\tPerson_GetNumberOfPeople(kn);')
    a('\t\tfor (ki=0, ki<kn, ki=ki+1)')
    a('\t\t{')
    a('\t\t\twor.GetDataByIndex(ki);')
    a('\t\t\tif (wor.nValidRead & wor.fEducation > 2.999)')
    a('\t\t\t{')
    a('\t\t\t\tnCosmo = nCosmo + 1;')
    a('\t\t\t\tcosmoPos = wor.vPosition;')
    a('\t\t\t}')
    a('\t\t}')
    a('\t\tScript_SetUpdateFrequency(5000);')
    a('\t\tif (!bCosmoObj)')
    a('\t\t{')
    a('\t\t\tObjectives_CreateNewString("sr_cosmo", "Experts: cosmonauts and chief designers");')
    a('\t\t\tObjective_AddRequirement("sr_cosmo", 3.0, "research/sr_manned_flight.png");')
    a('\t\t\tbCosmoObj = 1;')
    a('\t\t}')
    a('\t\tfCosmo = nCosmo;')
    a('\t\tObjective_UpdateRequirement("sr_cosmo", 0, fCosmo);')
    a('\t\tif (nCosmo > nCosmoShown)')
    a('\t\t{')
    a('\t\t\tNotification_CreateNewStringPic("A new expert", "Star City has trained a cosmonaut, or OKB-1 a chief designer. The objective counts every expert in the republic.", "research/sr_manned_flight.png", cosmoPos);')
    a('\t\t\tnCosmoShown = nCosmo;')
    a('\t\t}')
    a('\t}')
    a('\treturnVoid();')
    a('}')
    a('')
    # --- loyalty for everyone
    a('defineFunction(BoostLoyalty, void, float:fDelta)')
    a('{')
    a('\tScript_SetUpdateFrequency(20000);')
    a('\tPerson_GetNumberOfPeople(cn);')
    a('\tfor (ci=0, ci<cn, ci=ci+1)')
    a('\t{')
    a('\t\twor.GetDataByIndex(ci);')
    a('\t\tif (wor.nValidRead)')
    a('\t\t{')
    a('\t\t\tf2 = wor.fStatusSoviet + fDelta;')
    a('\t\t\tif (f2 > 1.0) { f2 = 1.0; }')
    a('\t\t\tif (f2 < 0.0) { f2 = 0.0; }')
    a('\t\t\tPerson_SetStatus(ci, 3, f2);')
    a('\t\t}')
    a('\t}')
    a('\tScript_SetUpdateFrequency(5000);')
    a('\treturnVoid();')
    a('}')
    a('')
    # --- the American timeline, announced as the dates pass (usDue: set when the programme opens)
    a('defineFunction(CheckUSA, void)')
    a('{')
    a('\tCheckCosmonauts();')
    a('\tDate_GetCurrentDate_D365Y(day, year);')
    a('\tnNow = year * 365 + day;')
    for idx, m in enumerate(MILESTONES):
        a('\tif (!usDone[%d] & nNow + 1 > usDue[%d])' % (idx, idx))
        a('\t{')
        a('\t\tusDone[%d] = 1;' % idx)
        a('\t\tif (srDone[%d])' % idx)
        a('\t\t{')
        a('\t\t\tNotification_CreateNewStringPic("United States", "%s We were there first.", "research/%s.png", padPos);' % (esc(m['us_text']), m['icon']))
        a('\t\t}')
        a('\t\telse()')
        a('\t\t{')
        a('\t\t\tNotification_CreateNewStringPic("United States", "%s The Americans got there first.", "research/%s.png", padPos);' % (esc(m['us_text']), m['icon']))
        a('\t\t\tfLoyal = %s;' % t.f('us_first_loyalty', R['america_first_loyalty'] / 100.0))
        a('\t\t\tBoostLoyalty(fLoyal);')
        a('\t\t}')
        a('\t}')
    a('\treturnVoid();')
    a('}')
    a('')
    # --- main
    moon_when = t.s('moon_when', 'by ' + date_text(moon['us_date']))
    moon_after = t.s('moon_after', years_text(day_number(moon['us_date']) - day_number(AMERICA_START)))
    last = len(MILESTONES) - 1
    a('defineFunction(main, void)')
    a('{')
    a('\tInitConstants();')
    a('\tbObjReady = 0; bCosmoObj = 0; nCosmoShown = 0; nBlockUntil = 0;')
    a('\tnBlockedPad = 0 - 1;')
    a('\tfor (i=0, i<%d, i=i+1) { srDone[i] = 0; usDone[i] = 0; usDue[i] = 0; }' % len(MILESTONES))
    a('\tfor (i=0, i<6, i=i+1) { rocketOK[i] = 0; }')
    a('\t// dormant until the republic joins: the first space research done AND the Design Bureau (OKB-1)')
    a('\t// built. Until then nothing shows and nothing counts - not even the American timeline.')
    a('\tnStart = 0;')
    a('\tbHinted = 0;')
    a('\twhile (!nStart)')
    a('\t{')
    a('\t\tScript_Sleep(30.0);')
    a('\t\tnResearch = IsResearched("sr_rocketry");')
    a('\t\tif (nResearch)')
    a('\t\t{')
    a('\t\t\tnBureau = CountBureaus();')
    a('\t\t\tif (nBureau > 0)')
    a('\t\t\t{')
    a('\t\t\t\tDate_GetCurrentDate_D365Y(day, year);')
    a('\t\t\t\tnStart = year * 365 + day;')
    a('\t\t\t}')
    a('\t\t\telse()')
    a('\t\t\t{')
    a('\t\t\t\tif (!bHinted)')
    a('\t\t\t\t{')
    a('\t\t\t\t\tNotification_CreateNewStringPic("The Space Programme", "The Rocket Research Institute is ready. The Space Race begins when the republic builds the Design Bureau (OKB-1); until then the programme stays on paper.", "research/sr_rocketry.png", padPos);')
    a('\t\t\t\t\tbHinted = 1;')
    a('\t\t\t\t}')
    a('\t\t\t}')
    a('\t\t}')
    a('\t}')
    a('\t// the American timeline from the day the programme opened: a late start shifts it (late_start =')
    a('\t// shift), and whatever the Americans did before that day is history - no loyalty lost for it')
    a('\tnShift = 0;')
    a('\tk = %s;' % t.i('late_shift', 1 if LATE_START == 'shift' else 0))
    a('\tif (k)')
    a('\t{')
    a('\t\tif (nStart > %s) { nShift = nStart - %s; }' % ((t.i('start_day', day_number(AMERICA_START)),) * 2))
    a('\t}')
    a('\tnAhead = 0;')
    for idx, m in enumerate(MILESTONES):
        y, d = day_of_year(m['us_date'])
        a('\tusDue[%d] = %s * 365 + %s + 1 + nShift;' % (idx, t.i('us_year_%d' % idx, y), t.i('us_day0_%d' % idx, d - 1)))
        a('\tif (usDue[%d] < nStart + 1) { usDone[%d] = 1; nAhead = nAhead + 1; }' % (idx, idx))
    opening = ("The Design Bureau (OKB-1) is at work. Korolev's designers promise a satellite before the Americans, then a man "
               "in space, then the Moon. Research the space branch, build the plants, the launch complexes and the cosmonaut corps.")
    goal = 'Reach every milestone before the United States. The last one: an N1 carrying cosmonauts to the Moon before the Americans get there'
    a('\tif (usDone[%d])' % last)
    a('\t{')
    a('\t\tScenario_WindowWithImageLeft("The Space Programme", "%s We start late: the Americans have already been to the Moon. The race is theirs, but the programme is ours - every milestone still pays, and the world is still watching.", "programme.png", 3);' % opening)
    a('\t\twinexist = 1;')
    a('\t\twhile (winexist) { Scenario_WindowExists(winexist); }')
    a('\t\tScenario_ObjectiveCreate("sr_race", "The Space Race", "Fly every milestone of the programme. The last one: an N1 carrying cosmonauts to the Moon.");')
    a('\t}')
    a('\telse()')
    a('\t{')
    a('\t\tif (nShift > 0)')
    a('\t\t{')
    a('\t\t\tScenario_WindowWithImageLeft("The Space Programme", "%s The Americans are only now getting started too, and they will not wait: they mean to land on the Moon %s.", "programme.png", 3);' % (opening, moon_after))
    a('\t\t\twinexist = 1;')
    a('\t\t\twhile (winexist) { Scenario_WindowExists(winexist); }')
    a('\t\t\tScenario_ObjectiveCreate("sr_race", "The Space Race", "%s - they mean to land %s.");' % (goal, moon_after))
    a('\t\t}')
    a('\t\telse()')
    a('\t\t{')
    a('\t\t\tif (nAhead > 0)')
    a('\t\t\t{')
    a('\t\t\t\tScenario_WindowWithImageLeft("The Space Programme", "%s We start late: the Americans have already flown the first milestones, and those are theirs. The rest of the race is open - they mean to land on the Moon %s.", "programme.png", 3);' % (opening, moon_when))
    a('\t\t\t}')
    a('\t\t\telse()')
    a('\t\t\t{')
    a('\t\t\t\tScenario_WindowWithImageLeft("The Space Programme", "%s The Americans will not wait: they mean to land on the Moon %s.", "programme.png", 3);' % (opening, moon_when))
    a('\t\t\t}')
    a('\t\t\twinexist = 1;')
    a('\t\t\twhile (winexist) { Scenario_WindowExists(winexist); }')
    a('\t\t\tScenario_ObjectiveCreate("sr_race", "The Space Race", "%s, %s.");' % (goal, moon_when))
    a('\t\t}')
    a('\t}')
    a('\tbObjReady = 1;')
    for idx, m in enumerate(MILESTONES):
        p = m['power'] - 9001
        fuel, lox, hyper = t.f('fuel_%d' % idx, m['fuel']), t.f('lox_%d' % idx, m['lox']), t.f('hyper_%d' % idx, m['hyper'])
        craft, food = t.f('craft_%d' % idx, m['craft']), t.f('food_%d' % idx, m['food'])
        a('')
        a('\t// ---------------------------------------------------------------- %s' % m['key'])
        a('\tObjectives_CreateNewString("sr_next", "Next: %s - research %s");' % (esc(m['title']), esc(research_name(m['research']))))
        a('\tObjective_AddRequirement("sr_next", 1.0, "research/%s.png");' % m['icon'])
        a('\tnResearch = 0;')
        a('\twhile (!nResearch)')
        a('\t{')
        a('\t\tScript_Sleep(20.0);')
        a('\t\tnResearch = IsResearched("%s");' % m['research'])
        a('\t\tCheckUSA();')
        a('\t}')
        a('\tObjective_Remove("sr_next");')
        brief = m['brief'].replace('{radius}', t.i('radius_m', L['radius']))
        a('\tScenario_WindowWithImageLeft("%s", "%s", "%s.png", 3);' % (esc(m['title']), esc(brief), m['key']))
        a('\twinexist = 1;')
        a('\twhile (winexist) { Scenario_WindowExists(winexist); }')
        a('\tnNeedCrew = %s;' % t.i('crew_%d' % idx, m['crew']))
        a('\tnNeedTrack = %s;' % t.i('track_%d' % idx, m['track']))
        a('\tObjectives_CreateNewString("sr_rocket", "%s on a launch pad");' % m['rocket'])
        a('\tObjective_AddRequirement("sr_rocket", 1.0, "research/%s.png");' % m['icon'])
        a('\tObjectives_CreateNewString("sr_prop", "Propellant near the pad (t)");')
        a('\tObjective_AddRequirement("sr_prop", %s, "resources/fuel.png");' % t.f('prop_%d' % idx, m['fuel'] + m['lox'] + m['hyper']))
        a('\tObjectives_CreateNewString("sr_craft", "Payload near the pad (t)");')
        a('\tObjective_AddRequirement("sr_craft", %s, "resources/%s.png");' % (craft, t.s('craft_icon', craft_good)))
        a('\tif (nNeedCrew > 0)')
        a('\t{')
        a('\t\tObjectives_CreateNewString("sr_crew", "Cosmonauts (experts)");')
        a('\t\tf = nNeedCrew;')
        a('\t\tObjective_AddRequirement("sr_crew", f, "research/sr_manned_flight.png");')
        a('\t}')
        a('\tif (nNeedTrack > 0)')
        a('\t{')
        a('\t\tObjectives_CreateNewString("sr_track", "Tracking stations");')
        a('\t\tf = nNeedTrack;')
        a('\t\tObjective_AddRequirement("sr_track", f, "research/sr_satellite.png");')
        a('\t}')
        a('\twhile (!srDone[%d])' % idx)
        a('\t{')
        a('\t\tScript_Sleep(10.0);')
        a('\t\tCheckUSA();')
        a('\t\tbContinue = 1;')
        a('\t\tnVeh = FindRocket(%d.0);' % m['power'])
        a('\t\tif (nVeh > -1) { Objective_UpdateRequirement("sr_rocket", 0, 1.0); }')
        a('\t\telse() { Objective_UpdateRequirement("sr_rocket", 0, 0.0); bContinue = 0; }')
        a('\t\tif (bContinue)')
        a('\t\t{')
        a('\t\t\tSumNear();')
        a('\t\t\tf = 0;')
        # a need of 0 passes: fNeed is then just below zero
        for need, have in ((fuel, 'fFuel'), (lox, 'fLox'), (hyper, 'fHyper')):
            a('\t\t\tfNeed = %s - 0.01;' % need)
            a('\t\t\tif (%s > fNeed) { f = f + %s; } else() { f = f + %s; bContinue = 0; }' % (have, need, have))
        a('\t\t\tObjective_UpdateRequirement("sr_prop", 0, f);')
        a('\t\t\tf = fCraft;')
        a('\t\t\tif (f > %s) { f = %s; }' % (craft, craft))
        a('\t\t\tObjective_UpdateRequirement("sr_craft", 0, f);')
        a('\t\t\tfNeed = %s - 0.01;' % craft)
        a('\t\t\tif (fCraft < fNeed) { bContinue = 0; }')
        a('\t\t\tfNeed = %s - 0.01;' % food)
        a('\t\t\tif (fFood < fNeed) { bContinue = 0; }')
        a('\t\t}')
        a('\t\tif (nNeedCrew > 0)')
        a('\t\t{')
        a('\t\t\tnExperts = CountExperts();')
        a('\t\t\tf = nExperts;')
        a('\t\t\tObjective_UpdateRequirement("sr_crew", 0, f);')
        a('\t\t\tif (nExperts < nNeedCrew) { bContinue = 0; }')
        a('\t\t}')
        a('\t\tif (nNeedTrack > 0)')
        a('\t\t{')
        a('\t\t\tnTrack = CountTracking();')
        a('\t\t\tf = nTrack;')
        a('\t\t\tObjective_UpdateRequirement("sr_track", 0, f);')
        a('\t\t\tif (nTrack < nNeedTrack) { bContinue = 0; }')
        a('\t\t}')
        a('\t\tif (bContinue)')
        a('\t\t{')
        a('\t\t\t// launch: the spacerace plugin takes the load from the storages and flies the flagged rocket')
        a('\t\t\tScenario_ObjectiveMoveCameraTo(padPos, 260.0);')
        a('\t\t\tNotification_CreateNewStringPic("Launch", "%s ignition... lift-off!", "research/%s.png", padPos);' % (m['rocket'], m['icon']))
        a('\t\t\tScript_Sleep(4.0);')
        a('\t\t\tfFail = %s - %s * rocketOK[%d];' % (t.i('fail_%d' % idx, m['fail']), t.i('per_success', L['failure_per_success']), p))
        if m is moon:
            a('\t\t\tr = IsResearched("sr_nk33");')
            a('\t\t\tif (r) { fFail = fFail - %s; }' % t.i('nk33', L['failure_nk33']))
        a('\t\t\tnTest = CountTestStands();')
        a('\t\t\tif (nTest > 0) { fFail = fFail - %s; }' % t.i('test_stand', L['failure_test_stand']))
        fmin = t.i('fail_min', L['failure_min'])
        a('\t\t\tif (fFail < %s) { fFail = %s; }' % (fmin, fmin))
        a('\t\t\tRandom(r);')
        a('\t\t\tr = r % 100;')
        a('\t\t\tfr = r;')
        a('\t\t\tVehicle_SetCanSell(nVeh, 0);')
        a('\t\t\tif (fr < fFail)')
        a('\t\t\t{')
        a('\t\t\t\tScript_Sleep(3.0);')
        a('\t\t\t\tnVeh = FindLaunched(%d.0);' % m['power'])
        a('\t\t\t\tif (nVeh > -1) { Vehicle_Sell(nVeh, 0, 0); }')
        a('\t\t\t\tgs.GetCurrentGameSettigns();')
        a('\t\t\t\tif (gs.FiresEnabled)')
        a('\t\t\t\t{')
        a('\t\t\t\t\tBuilding_StartFire(nPad);')
        a('\t\t\t\t\tNotification_CreateNewStringPic("Launch failure", "The %s exploded. The pad is burning: send the fire brigade, then build another rocket and try again.", "research/%s.png", padPos);' % (m['rocket'], m['icon']))
        a('\t\t\t\t}')
        a('\t\t\t\telse()')
        a('\t\t\t\t{')
        repair = t.i('repair_days', L['pad_repair_days'])
        a('\t\t\t\t\tDate_GetCurrentDate_D365Y(day, year);')
        a('\t\t\t\t\tnBlockedPad = nPad;')
        a('\t\t\t\t\tnBlockUntil = year * 365 + day + %s;' % repair)
        a('\t\t\t\t\tNotification_CreateNewStringPic("Launch failure", "The %s exploded and wrecked the pad. Repairs take %s days; build another rocket meanwhile.", "research/%s.png", padPos);' % (m['rocket'], repair, m['icon']))
        a('\t\t\t\t}')
        a('\t\t\t}')
        a('\t\t\telse()')
        a('\t\t\t{')
        a('\t\t\t\t// the plugin clears the flag when the climb is over (at most a minute)')
        a('\t\t\t\tk = 0;')
        a('\t\t\t\tbContinue = 1;')
        a('\t\t\t\twhile (bContinue)')
        a('\t\t\t\t{')
        a('\t\t\t\t\tScript_Sleep(1.0);')
        a('\t\t\t\t\tk = k + 1;')
        a('\t\t\t\t\tnVeh = FindLaunched(%d.0);' % m['power'])
        a('\t\t\t\t\tif (nVeh < 0 | !lk | k > 60) { bContinue = 0; }')
        a('\t\t\t\t}')
        a('\t\t\t\tif (nVeh > -1) { Vehicle_Sell(nVeh, 0, 0); }')
        a('\t\t\t\tsrDone[%d] = 1;' % idx)
        a('\t\t\t\trocketOK[%d] = rocketOK[%d] + 1;' % (p, p))
        a('\t\t\t\tif (usDone[%d])' % idx)
        a('\t\t\t\t{')
        a('\t\t\t\t\tMoney_AddUSD(%s);' % t.i('second_money', max(0, R['second_money'])))
        a('\t\t\t\t\tfLoyal = %s;' % t.f('second_loyalty', R['second_loyalty'] / 100.0))
        a('\t\t\t\t\tBoostLoyalty(fLoyal);')
        a('\t\t\t\t\tScenario_WindowWithImageLeft("%s", "%s The Americans did it first, but we are catching up.", "%s.png", 3);' % (esc(m['title']), esc(m['win']), m['key']))
        a('\t\t\t\t}')
        a('\t\t\t\telse()')
        a('\t\t\t\t{')
        a('\t\t\t\t\tMoney_AddUSD(%s);' % t.i('first_money', max(0, R['first_money'])))
        a('\t\t\t\t\tfLoyal = %s;' % t.f('first_loyalty', R['first_loyalty'] / 100.0))
        a('\t\t\t\t\tBoostLoyalty(fLoyal);')
        a('\t\t\t\t\tScenario_WindowWithImageLeft("%s", "%s A Soviet first: the world is watching.", "%s.png", 3);' % (esc(m['title']), esc(m['win']), m['key']))
        a('\t\t\t\t}')
        a('\t\t\t\twinexist = 1;')
        a('\t\t\t\twhile (winexist) { Scenario_WindowExists(winexist); }')
        a('\t\t\t}')
        a('\t\t}')
        a('\t}')
        for o in ('sr_rocket', 'sr_prop', 'sr_craft'):
            a('\tObjective_Remove("%s");' % o)
        a('\tif (nNeedCrew > 0) { Objective_Remove("sr_crew"); }')
        a('\tif (nNeedTrack > 0) { Objective_Remove("sr_track"); }')
    a('')
    a('\tif (usDone[%d])' % last)
    a('\t{')
    a('\t\tScenario_WindowWithImageLeft("The race is over", "We reached the Moon, but the Americans were there first. History will remember Apollo 11 - and the N1 that came after it.", "moon.png", 3);')
    a('\t}')
    a('\telse()')
    a('\t{')
    a('\t\tScenario_WindowWithImageLeft("Victory in the Space Race", "A Soviet cosmonaut walked on the Moon before any American. From Sputnik to the N1, the republic won the race to space.", "moon.png", 3);')
    a('\t\tMoney_AddUSD(%s);' % t.i('victory_money', max(0, R['victory_money'])))
    a('\t\tfLoyal = %s;' % t.f('victory_loyalty', R['victory_loyalty'] / 100.0))
    a('\t\tBoostLoyalty(fLoyal);')
    a('\t}')
    a('\twinexist = 1;')
    a('\twhile (winexist) { Scenario_WindowExists(winexist); }')
    a('\tScenario_ObjectiveSetCompleted("sr_race", 0, 1);')
    a('\tScenario_UnlockNextScenarios();')
    a('}')
    return '\r\n'.join(L_) + '\r\n'


def vanilla_style(src):
    """Re-flow the script the way vanilla scripts are written: one statement per line,
    braces on their own lines. Strings and // comments are left intact."""
    out = []
    depth = 0
    for raw in src.split('\r\n'):
        line = raw.strip()
        if not line or line.startswith('//') or line.startswith('include(') or line.startswith('define'):
            if line.startswith('defineFunction') or not line.startswith('define'):
                out.append('\t' * depth + line if line else '')
            else:
                out.append('\t' * depth + line)
            continue
        buf = ''
        instr = False
        paren = 0
        for ch in line:
            if ch == '"':
                instr = not instr
                buf += ch
                continue
            if instr:
                buf += ch
                continue
            if ch == '(':
                paren += 1
            elif ch == ')':
                paren -= 1
            if ch == '{' and paren == 0:
                if buf.strip():
                    out.append('\t' * depth + buf.strip())
                out.append('\t' * depth + '{')
                depth += 1
                buf = ''
            elif ch == '}' and paren == 0:
                if buf.strip():
                    out.append('\t' * depth + buf.strip())
                depth -= 1
                out.append('\t' * depth + '}')
                buf = ''
            elif ch == ';' and paren == 0:
                out.append('\t' * depth + (buf + ';').strip())
                buf = ''
            else:
                buf += ch
        if buf.strip():
            out.append('\t' * depth + buf.strip())
    assert depth == 0, 'unbalanced braces while re-flowing'
    return '\r\n'.join(out) + '\r\n'


def lint(src):
    """No VM here, so catch what can be caught: brace balance and undeclared names."""
    import re
    assert src.count('{') == src.count('}'), 'unbalanced braces'
    assert src.count('(') == src.count(')'), 'unbalanced parentheses'
    code = re.sub(r'"[^"]*"', '""', src)
    code = re.sub(r'//[^\n]*', '', code)
    declared = set(re.findall(r'defineVariable\(\w+, (\w+)\)', code)) | set(re.findall(r'defineArray\(\w+\[\d+\], (\w+)\)', code))
    declared |= set(re.findall(r'defineFunction\((\w+),', code))
    declared |= set(re.findall(r'\w+:(\w+)', code))
    body = code.split('defineFunction(CountExperts', 1)[1]
    names = set(re.findall(r'(?<![\.\w])([a-z]\w*)(?=\s*(?:=[^=]|\[|\.|\)|,|;| [<>?&|+\-*/%]))', body))
    known = declared | {'if', 'else', 'while', 'for', 'return', 'include', 'defineFunction', 'void', 'int', 'float', 'vec3'}
    missing = sorted(n for n in names if n not in known)
    return missing


def images():
    """Window images from the kit renders (vanilla window art is about 400 x 400)."""
    src = {'programme': ('build/space_vehicles/showcase_lineup.png', None),
           'sputnik': ('build/space/bureau.png', None), 'laika': ('build/space/recovery.png', None),
           'luna': ('build/space/tracking.png', None), 'vostok': ('build/space_vehicles/showcase_sr_pad_r7.png', None),
           'voskhod': ('build/space/training.png', None), 'soyuz': ('build/space/spacecraft.png', None),
           'zond': ('build/space/propellant.png', None), 'moon': ('build/space_vehicles/showcase_sr_pad_n1.png', None)}
    for key, (p, _) in src.items():
        im = Image.open(os.path.join(ROOT, p)).convert('RGB')
        w, h = im.size
        s = min(w, h)
        im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2)).resize((400, 400), Image.LANCZOS).transpose(Image.FLIP_LEFT_RIGHT)
        im.save(os.path.join(PROG, key + '.png'))
    Image.open(os.path.join(PROG, 'programme.png')).save(os.path.join(OUT, 'previewimage.png'))
    Image.open(os.path.join(PROG, 'programme.png')).resize((128, 128), Image.LANCZOS).save(os.path.join(OUT, 'icon.png'))
    Image.open(os.path.join(PROG, 'moon.png')).save(os.path.join(OUT, 'end.png'))
    Image.open(os.path.join(PROG, 'programme.png')).resize((128, 128), Image.LANCZOS).save(os.path.join(PROG, 'icon.png'))


def render(template, values):
    """Fill @token@s the way the plugin does."""
    import re
    return re.sub(r'@([a-z0-9_]+)@', lambda m: values[m.group(1)], template)


def main():
    for d in (OUT, PROG):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)
    for d in sorted(os.listdir(LEGACY)):
        if os.path.isdir(os.path.join(LEGACY, d)):
            shutil.copytree(os.path.join(LEGACY, d), os.path.join(OUT, d))
    open(os.path.join(OUT, 'script.ini'), 'w', newline='').write('\r\n'.join([
        '$NAME_STR "The Space Race"',
        '$DESCRIPTION_STR "Beat the United States to orbit, to a man in space and to the Moon. Starts itself in any game; nothing happens until the Rocket Research Institute is researched."',
        '$END_TEXT_STR "The race to the Moon is over."',
        '$AVAILABLE_ON_ALL_MAPS', '$END', '']))
    open(os.path.join(PROG, 'script.ini'), 'w', newline='').write('\r\n'.join([
        '$RUNSCRIPT race.txt', '$NAME_STR "The Space Race"',
        '$DESCRIPTION_STR "From Sputnik to the N1: eight milestones against the American timeline."',
        '$TREEXPOS 0', '$STARTUNLOCKED', '$END', '']))
    tt = Tok(True)
    tmpl = vanilla_style(gen_script(tt))
    renders = []
    for new_goods in (False, True):
        td = Tok(False)
        src = vanilla_style(gen_script(td, new_goods))
        assert set(tt.values) == set(td.values) and render(tmpl, td.values) == src, 'template and rendered defaults differ'
        assert '>=' not in src and '<=' not in src and '!=' not in src and '==' not in src, 'operator the VM lacks'
        renders.append((DEFAULT_RENDER % int(new_goods), src))
    missing = lint(renders[0][1]) + lint(renders[1][1])
    meta = ['; generated by tools/space_scenario.py - for the spacerace plugin, which renders race.tmpl',
            '; goods <fuel> <lox> <hyper> <craft> <food>: the game goods behind the @fuel_N@ .. @food_N@ tokens',
            'goods ' + ' '.join(GOOD[k] for k, _ in LOAD_KEYS),
            '; milestone <key> <rocket>, in template order: tokens _0, _1, ... belong to these']
    meta += ['milestone %s %s' % (m['key'], ROCKET_OF[m['power']]) for m in MILESTONES]
    meta += ['; tokens: ' + ' '.join(sorted(tt.values))]
    open(os.path.join(PROG, 'milestones.txt'), 'w', newline='').write('\r\n'.join(meta) + '\r\n')
    open(os.path.join(PROG, 'race.tmpl'), 'w', newline='').write(tmpl)
    os.makedirs(os.path.dirname(DEFAULT_RENDER), exist_ok=True)
    for path, text in renders:
        open(path, 'w', newline='').write(text)
    lines = ['; generated by tools/space_scenario.py (goods from space_goods.py) - read by the spacerace plugin.',
             '; The pads, effects and script goods of the launches. The loads, bills, radius and climb here are the',
             '; defaults and the rules of the frozen legacy missions; spacerace.ini [rockets], [rocket_parts] and',
             '; [launches] set them for the current programme.',
             'radius %d' % L['radius'], 'climb_seconds %d' % L['climb_seconds']]
    lines += ['; effects from particleeffect/particleeffects.ini: under the rocket, its trail, round the pad at lift-off, a failure',
              'fx_flame airplane_jet', 'fx_smoke big_firesmoke', 'fx_pad factory_big_white', 'fx_boom buildingfall2',
              ]
    lines += ['; vm_goods: added goods scripts may read, answered with _Resources_reserved_16_.._19_ in this order']
    lines += ['vm_goods ' + ' '.join(G.VM_GOODS) if G.USE_NEW_GOODS else '; (stand-in goods: no vm_goods)']
    lines += ['; standin <new good> <vanilla good>: what plays each new good while spacerace.ini has new_goods = 0']
    lines += ['standin %s %s' % (g, G.STANDIN[g]) for g in G.NEW]
    lines += ['; rocket <object> <the only pad kind it may stand on> then <good> <tonnes> pairs taken at lift-off']
    for k, v in LOADS.items():
        pairs = ' '.join('%s %g' % (GOOD[key], v[key]) for key, _ in LOAD_KEYS if v[key])
        lines.append('rocket %s %s %s' % (k, PAD_OF.get(k, 'sr_pad_r7'), pairs))
    if G.USE_NEW_GOODS:
        lines += ['; bill <object> then <good> <tonnes> pairs: what the MIK builds it from (workdays stay the engine\'s)']
        lines += ['bill %s %s' % (k, ' '.join('%s %g' % gt for gt in v)) for k, v in G.BILL.items()]
    open(os.path.join(DATA, 'launches.ini'), 'w', newline='').write('\r\n'.join(lines) + '\r\n')
    images()
    print('programme: %d milestones, %d tokens, %d lines of VM script; undeclared names: %s'
          % (len(MILESTONES), len(tt.values), src.count('\r\n'), missing or 'none'))
    # the compiler's own rules (argument types, function endings, fields, ...): see tools/vmcheck.py
    for path, _text in renders:
        r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'vmcheck.py'), path])
        if r.returncode:
            sys.exit('vmcheck found problems in the generated script')


if __name__ == '__main__':
    main()
