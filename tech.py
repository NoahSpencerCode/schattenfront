"""
The tech trees: each power's wartime research programme.

Research points (RP) are bought with the tax fortnight: a nation
allocates a share of its revenue to the laboratories, and every $300
so tithed becomes one RP. Each branch (LAND / AIR / SEA) is a chain
of tiers; researching a tier (instantly, if the RP are on hand)
unlocks its units for the budget manifest and, for the third land
tier, the RADAR STATION works for the engineers. Tiers must be taken
in order within a branch.

The unlock MECHANICS are symmetric across powers -- the flavour, the
names and the stat mods (see units.NATION_UNITS) are each nation's
own: German wolfpacks, American fortress wings, Soviet gun-howitzer
regiments.
"""

RESEARCH_DOLLARS_PER_POINT = 300
RESEARCH_PCT_CHOICES = (0, 10, 20, 30)

# branch -> ordered tiers; every power researches the same skeleton,
# under its own programme names
TECH_BRANCHES = ('land', 'air', 'sea')

TECH_TREES = {
    'germany': {
        'land': [("ARTILLERIE-PROGRAMM", 20, ('artillery',)),
                 ("PANZERWAFFE VI", 45, ('heavy_tank',)),
                 ("FUNKMESS-GERAT", 70, ('radar_station',))],
        'air':  [("KAMPFGESCHWADER SCHWER", 30, ('heavy_bomber',)),
                 ("PROJEKT SCHWALBE", 75, ('jet_fighter',))],
        'sea':  [("RUDELTAKTIK", 25, ('submarine',)),
                 ("PLAN Z", 60, ('battleship',))],
    },
    'usa': {
        'land': [("FIELD ARTILLERY BOARD", 20, ('artillery',)),
                 ("PERSHING PROGRAM", 45, ('heavy_tank',)),
                 ("SCR-270 RADAR", 70, ('radar_station',))],
        'air':  [("STRATEGIC BOMBING DOCTRINE", 30, ('heavy_bomber',)),
                 ("PROJECT SHOOTING STAR", 75, ('jet_fighter',))],
        'sea':  [("SILENT SERVICE", 25, ('submarine',)),
                 ("FAST BATTLESHIP PROGRAM", 60, ('battleship',))],
    },
    'britain': {
        'land': [("ROYAL ARTILLERY EXPANSION", 20, ('artillery',)),
                 ("INFANTRY TANK MK IV", 45, ('heavy_tank',)),
                 ("CHAIN HOME", 60, ('radar_station',))],
        'air':  [("BOMBER COMMAND", 30, ('heavy_bomber',)),
                 ("WHITTLE JET PROGRAMME", 75, ('jet_fighter',))],
        'sea':  [("SUBMARINE SERVICE", 25, ('submarine',)),
                 ("KGV FAST BATTLESHIPS", 60, ('battleship',))],
    },
    'japan': {
        'land': [("TYPE 91 MOBILISATION", 20, ('artillery',)),
                 ("CHI-HA KAI CONVERSION", 40, ('heavy_tank',)),
                 ("TYPE 11 RADAR", 75, ('radar_station',))],
        'air':  [("RIKKO LONG-RANGE WINGS", 30, ('heavy_bomber',)),
                 ("KIKKA PROJECT", 80, ('jet_fighter',))],
        'sea':  [("SENSUIKAN FLEET BOATS", 25, ('submarine',)),
                 ("YAMATO PROGRAMME", 65, ('battleship',))],
    },
    'soviet': {
        'land': [("GUN-HOWITZER REGIMENTS", 20, ('artillery',)),
                 ("IOSIF STALIN PROGRAMME", 40, ('heavy_tank',)),
                 ("RUS-2 RADAR", 70, ('radar_station',))],
        'air':  [("LONG-RANGE AVIATION", 35, ('heavy_bomber',)),
                 ("CAPTURED SCIENCE BUREAU", 75, ('jet_fighter',))],
        'sea':  [("SHCHUKA FLOTILLAS", 25, ('submarine',)),
                 ("BALTIC REFIT PROGRAMME", 55, ('battleship',))],
    },
}

# what every power fields WITHOUT research
BASE_UNITS = ('infantry', 'tank', 'supply_truck', 'transport_truck',
              'aa_artillery', 'army_command', 'engineer',
              'naval_command', 'personnel_transport',
              'destroyer_sea_sea', 'destroyer_aa', 'destroyer_sea_land',
              'supply_ship', 'aircraft_carrier',
              'fighter', 'bomber', 'airforce_command', 'transport_air',
              'blimp')


def unlocked_units(country, researched):
    """The buyable roster: base chassis plus every researched unlock
    (radar_station is a works, not a unit -- filtered by the caller)."""
    out = set(BASE_UNITS)
    tree = TECH_TREES.get(country, {})
    for (branch, idx) in researched:
        tiers = tree.get(branch, ())
        if idx < len(tiers):
            out.update(u for u in tiers[idx][2]
                       if u != 'radar_station')
    return out


def radar_unlocked(country, researched):
    tree = TECH_TREES.get(country, {})
    for (branch, idx) in researched:
        tiers = tree.get(branch, ())
        if idx < len(tiers) and 'radar_station' in tiers[idx][2]:
            return True
    return False


def next_tier(country, branch, researched):
    """Index of the next unresearched tier in a branch, or None."""
    tiers = TECH_TREES.get(country, {}).get(branch, ())
    for i in range(len(tiers)):
        if (branch, i) not in researched:
            return i
    return None
