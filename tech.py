"""
The tech tree: each power's wartime research programme, as a
BRANCHING GRAPH -- prerequisites, forks, and paths a nation commits
to, in the manner of the Civilization tech charts.

Research points (RP) are bought two ways: a share of the tax
fortnight tithed to the laboratories ($300 the point), and the
FUND THE LABORATORIES city focus. A node is bought instantly when
its prerequisites stand and the points are on hand.

The GRAPH is symmetric across powers -- the flavour, the programme
names and the stat mods (units.NATION_UNITS) are each nation's own.
Units and works locked behind a node do not appear anywhere in the
game -- budget, menus, engineer works -- until it is researched.
"""

RESEARCH_DOLLARS_PER_POINT = 300
RESEARCH_PCT_CHOICES = (0, 10, 20, 30)

TECH_BRANCHES = ('land', 'air', 'sea')

# the skeleton every power researches: id -> node. 'row' is depth on
# the chart (0 = a root the nation may start at once).
NODES = {
    # ---- LAND
    'artillery': {
        'branch': 'land', 'row': 0, 'cost': 20, 'req': (),
        'unlocks': ('artillery',)},
    'heavy_armour': {
        'branch': 'land', 'row': 1, 'cost': 45,
        'req': ('artillery',), 'unlocks': ('heavy_tank',)},
    'detection': {
        'branch': 'land', 'row': 1, 'cost': 35,
        'req': ('artillery',), 'unlocks': ('radar_station',)},
    # ---- AIR
    'medium_bombers': {
        'branch': 'air', 'row': 0, 'cost': 25, 'req': (),
        'unlocks': ('bomber',)},
    'air_logistics': {
        'branch': 'air', 'row': 1, 'cost': 30,
        'req': ('medium_bombers',),
        'unlocks': ('transport_air', 'blimp')},
    'strategic_bombing': {
        'branch': 'air', 'row': 1, 'cost': 50,
        'req': ('medium_bombers',), 'unlocks': ('heavy_bomber',)},
    'jet_propulsion': {
        'branch': 'air', 'row': 2, 'cost': 75,
        'req': ('strategic_bombing',), 'unlocks': ('jet_fighter',)},
    # ---- SEA. The 1939 fleet -- escorts, AA ships, the fleet
    # train and the battle line -- sails from the first day. What
    # the laboratories buy is BETTER HULLS: thicker armour, heavier
    # guns and a longer reach than anything already afloat.
    'naval_gunnery': {
        'branch': 'sea', 'row': 0, 'cost': 25, 'req': (),
        'unlocks': ('heavy_cruiser',)},
    'submarines': {
        'branch': 'sea', 'row': 1, 'cost': 30,
        'req': ('naval_gunnery',), 'unlocks': ('submarine',)},
    'capital_gunnery': {
        'branch': 'sea', 'row': 1, 'cost': 60,
        'req': ('naval_gunnery',), 'unlocks': ('fast_battleship',)},
    'naval_aviation': {
        'branch': 'sea', 'row': 2, 'cost': 70,
        'req': ('capital_gunnery',),
        'unlocks': ('aircraft_carrier',)},
}

# each power's name for every programme
NAMES = {
    'germany': {
        'artillery': "ARTILLERIE-PROGRAMM",
        'heavy_armour': "PANZERWAFFE VI",
        'detection': "FUNKMESS-GERAT",
        'medium_bombers': "KAMPFGESCHWADER",
        'air_logistics': "TRANSPORTFLIEGER",
        'strategic_bombing': "FERNKAMPF-PROJEKT",
        'jet_propulsion': "PROJEKT SCHWALBE",
        'naval_gunnery': "KREUZER-PROGRAMM",
        'submarines': "RUDELTAKTIK",
        'capital_gunnery': "PLAN Z",
        'naval_aviation': "TRAGER-PROJEKT",
    },
    'usa': {
        'artillery': "FIELD ARTILLERY BOARD",
        'heavy_armour': "PERSHING PROGRAM",
        'detection': "SCR-270 RADAR",
        'medium_bombers': "MEDIUM BOMBARDMENT GROUPS",
        'air_logistics': "AIR TRANSPORT COMMAND",
        'strategic_bombing': "STRATEGIC BOMBING DOCTRINE",
        'jet_propulsion': "PROJECT SHOOTING STAR",
        'naval_gunnery': "CRUISER CONSTRUCTION ACT",
        'submarines': "SILENT SERVICE",
        'capital_gunnery': "FAST BATTLESHIP PROGRAM",
        'naval_aviation': "CARRIER TASK FORCE DOCTRINE",
    },
    'britain': {
        'artillery': "ROYAL ARTILLERY EXPANSION",
        'heavy_armour': "INFANTRY TANK MK IV",
        'detection': "CHAIN HOME",
        'medium_bombers': "BOMBER COMMAND",
        'air_logistics': "RAF TRANSPORT COMMAND",
        'strategic_bombing': "AREA BOMBING DIRECTIVE",
        'jet_propulsion': "WHITTLE JET PROGRAMME",
        'naval_gunnery': "CRUISER SQUADRONS",
        'submarines': "SUBMARINE SERVICE",
        'capital_gunnery': "KGV FAST BATTLESHIPS",
        'naval_aviation': "FLEET AIR ARM",
    },
    'japan': {
        'artillery': "TYPE 91 MOBILISATION",
        'heavy_armour': "CHI-HA KAI CONVERSION",
        'detection': "TYPE 11 RADAR",
        'medium_bombers': "RIKKO WINGS",
        'air_logistics': "ARMY AIR TRANSPORT",
        'strategic_bombing': "RENZAN PROJECT",
        'jet_propulsion': "KIKKA PROJECT",
        'naval_gunnery': "JUNYOKAN PROGRAMME",
        'submarines': "SENSUIKAN FLEET BOATS",
        'capital_gunnery': "YAMATO PROGRAMME",
        'naval_aviation': "KIDO BUTAI",
    },
    'soviet': {
        'artillery': "GUN-HOWITZER REGIMENTS",
        'heavy_armour': "IOSIF STALIN PROGRAMME",
        'detection': "RUS-2 RADAR",
        'medium_bombers': "FRONTAL AVIATION",
        'air_logistics': "AEROFLOT MOBILISATION",
        'strategic_bombing': "LONG-RANGE AVIATION",
        'jet_propulsion': "CAPTURED SCIENCE BUREAU",
        'naval_gunnery': "KIROV PROGRAMME",
        'submarines': "SHCHUKA FLOTILLAS",
        'capital_gunnery': "BALTIC REFIT PROGRAMME",
        'naval_aviation': "NAVAL AIR ARM VMF",
    },
}

# what every power fields WITHOUT research: the 1939 standing kit
BASE_UNITS = ('infantry', 'tank', 'supply_truck', 'transport_truck',
              'aa_artillery', 'army_command', 'engineer',
              # THE 1939 FLEET sails from the first day: escorts of
              # every kind, the fleet train and the battle line
              'naval_command', 'personnel_transport',
              'destroyer_sea_sea', 'destroyer_aa',
              'destroyer_sea_land', 'supply_ship', 'battleship',
              'fighter', 'airforce_command')

# pre-1.3.1 saves recorded research as (branch, tier-index) pairs
_LEGACY = {
    ('land', 0): ('artillery',),
    ('land', 1): ('artillery', 'heavy_armour'),
    ('land', 2): ('artillery', 'detection'),
    ('air', 0): ('medium_bombers', 'strategic_bombing'),
    ('air', 1): ('medium_bombers', 'strategic_bombing',
                 'jet_propulsion'),
    ('sea', 0): ('naval_gunnery', 'submarines'),
    ('sea', 1): ('naval_gunnery', 'capital_gunnery'),
}


def normalize(researched):
    """A clean set of node ids from any vintage of record."""
    out = set()
    for r in researched:
        if isinstance(r, str):
            if r in NODES:
                out.add(r)
        else:
            out.update(_LEGACY.get((r[0], r[1]), ()))
    return out


def node_name(country, node_id):
    return NAMES.get(country, {}).get(node_id, node_id.upper())


def unlocked_units(country, researched):
    """The buyable roster: the 1939 kit plus every researched unlock
    (radar_station is a works, not a unit -- filtered by callers)."""
    out = set(BASE_UNITS)
    for nid in normalize(researched):
        out.update(u for u in NODES[nid]['unlocks']
                   if u != 'radar_station')
    return out


def radar_unlocked(country, researched):
    return any('radar_station' in NODES[nid]['unlocks']
               for nid in normalize(researched))


def available_nodes(researched):
    """Nodes whose prerequisites all stand and which are not yet
    bought -- the frontier of the chart."""
    have = normalize(researched)
    return [nid for nid, n in NODES.items()
            if nid not in have and all(r in have for r in n['req'])]
