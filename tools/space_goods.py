"""The Space Race goods, shared by space_scene.py (building recipes, run inside Blender),
space_scenario.py (the programme and launches.ini) and anything else. Import-free.

USE_NEW_GOODS = True: six real goods from the resources plugin (mod/plugins/resources,
resources.ini [list]); False: every one is played by a vanilla stand-in (Track A).
Flipping it changes the save format - see resources.ini.
"""

USE_NEW_GOODS = True

# the six real goods; the others the design names stay stand-ins either way
NEW = ('rocket_stage', 'rocket_engine', 'avionics', 'lox', 'hypergolic', 'spacecraft')
STANDIN = {'lox': 'chemicals', 'hypergolic': 'chemicals', 'rocket_engine': 'mcomponents',
           'rocket_stage': 'mcomponents', 'avionics': 'eletronics', 'spacecraft': 'eletronics',
           'heat_shield': 'plastics', 'space_food': 'food'}

# storage class of every good the kit names (vanilla food travels COVERED)
CLASS = {'lox': 'OIL', 'hypergolic': 'OIL', 'fuel': 'OIL', 'chemicals': 'COVERED', 'rocket_engine': 'COVERED',
         'rocket_stage': 'OPEN', 'avionics': 'COVERED', 'spacecraft': 'COVERED', 'heat_shield': 'COVERED',
         'space_food': 'COVERED', 'steel': 'OPEN', 'aluminium': 'OPEN', 'mcomponents': 'COVERED', 'ecomponents': 'COVERED',
         'eletronics': 'COVERED', 'plastics': 'COVERED', 'fabric': 'COVERED', 'food': 'COVERED', 'water': 'WATER',
         'explosives': 'COVERED'}

# the four goods scripts may read. The game's name -> Resources-field chain (SOVIET64 0x59B3F0)
# knows no added good, so the spacerace plugin answers these with the spare fields, in order.
VM_GOODS = ('lox', 'hypergolic', 'spacecraft', 'avionics')
RESERVED = ('_Resources_reserved_16_', '_Resources_reserved_17_', '_Resources_reserved_18_', '_Resources_reserved_19_')

# what each rocket is built from at the MIK (tonnes; the engine's own bill, computed from the
# empty weight, is replaced by the spacerace plugin; workdays stay the engine's)
BILL = {'sr_sputnik': (('rocket_stage', 16), ('rocket_engine', 6), ('avionics', 1)),
        'sr_vostok': (('rocket_stage', 20), ('rocket_engine', 7), ('avionics', 2)),
        'sr_soyuz': (('rocket_stage', 26), ('rocket_engine', 9), ('avionics', 3)),
        'sr_proton': (('rocket_stage', 45), ('rocket_engine', 14), ('avionics', 4)),
        'sr_n1': (('rocket_stage', 120), ('rocket_engine', 40), ('avionics', 8))}


def good(name):
    """The resource name the game uses for a design good."""
    return name if (USE_NEW_GOODS and name in NEW) else STANDIN.get(name, name)


def field(name):
    """The Resources struct field a script reads a design good from."""
    g = good(name)
    if g in VM_GOODS and USE_NEW_GOODS:
        return RESERVED[VM_GOODS.index(g)]
    return g
