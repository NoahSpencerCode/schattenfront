"""
Unit roster and the Unit class.

Distances are in world units on a globe of radius 30 (planet circumference
~188 units). Speeds are world units per second at normal game speed.

Units are drawn as flat map counters on the planet surface — a faction-
coloured card with the branch symbol, like a marker inked onto the map.
"""

from panda3d.core import Vec3

from panda3d.core import TextNode

from config import (AIR_VISION_MULT, COMM_RADIUS_FACTOR, COUNTRIES,
                    RAIL_LEG_MULT, RAIL_TRAIN_SPEED,
                    GLOBE_RADIUS, LIFT_AIR, LIFT_GROUND, LIFT_RING,
                    NIGHT_VISION_FACTOR, UNIT_SPEED_FACTOR,
                    UNIT_SPRITE_SCALE, VISION_SCALE)
from globe import make_surface_ring, orient_to_surface
from models import (make_flat_ring, make_flag_quad, make_icon_quad,
                    set_marker_layer, unit_layer_base)
from utils import (north_tangent, slerp, angle_between,
                   vec_to_latlon)

# domain: where the unit lives.  targets: what its guns can hurt.
UNIT_TYPES = {
    # ----- ARMY -----
    'infantry': {
        'label': 'Enlisted', 'domain': 'land', 'speed': 0.038,
        'road_mult': 1.5,   # 4 km/h cross-country, 6 in column
        'vision': 0.7, 'hp': 60, 'cost': 100, 'build_time': 4,
        'damage': 7, 'range': 0.5, 'targets': ('land',), 'icon': 'INF'},
    'tank': {
        'label': 'Medium Tank', 'domain': 'land', 'speed': 0.188,
        'road_mult': 2.0,   # 20 km/h cross-country, 40 on road
        'vision': 0.8, 'hp': 160, 'cost': 320, 'build_time': 8,
        'damage': 22, 'range': 0.65, 'targets': ('land', 'bridge'),
        'icon': 'TNK'},
    'supply_truck': {
        'label': 'Supply Truck', 'domain': 'land', 'speed': 0.141,
        'road_mult': 4.0,   # 15 km/h off, 60 on road
        'vision': 0.6, 'hp': 70, 'cost': 150, 'build_time': 5,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'SUP',
        'supply_cap': 1600.0, 'supply_carrier': True},
    'transport_truck': {
        'label': 'Personnel Truck', 'domain': 'land', 'speed': 0.141,
        'road_mult': 4.0, 'capacity': 4,   # a motorized infantry lift
        'vision': 0.6, 'hp': 90, 'cost': 180, 'build_time': 5,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'TRK'},
    'aa_artillery': {
        'label': 'AA Battery', 'domain': 'land', 'speed': 0.104,
        'road_mult': 3.5,
        'vision': 1.1, 'hp': 110, 'cost': 260, 'build_time': 7,
        'damage': 16, 'range': 1.2, 'targets': ('air',), 'icon': 'AAA'},
    'army_command': {
        'label': 'Army Command Post', 'domain': 'land', 'speed': 0.132,
        'road_mult': 3.5,
        'vision': 0.9, 'hp': 90, 'cost': 550, 'build_time': 12,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'CMD', 'comm': True},
    'engineer': {
        'label': 'Engineer Company', 'domain': 'land', 'speed': 0.113,
        'road_mult': 3.5,
        'vision': 0.7, 'hp': 50, 'cost': 200, 'build_time': 6,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'ENG',
        'engineer': True, 'supply_cap': 300.0},

    # ----- NAVY -----
    'naval_command': {
        'label': 'Fleet Command Ship', 'domain': 'sea', 'speed': 0.414,
        'vision': 1.0, 'hp': 140, 'cost': 800, 'build_time': 16,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'FLT', 'comm': True},
    'personnel_transport': {
        'label': 'Troop Transport', 'domain': 'sea', 'speed': 0.348,
        'vision': 0.8, 'hp': 120, 'cost': 550, 'build_time': 12,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'TPT',
        'capacity': 6},
    'destroyer_sea_sea': {
        'label': 'Destroyer (Surface)', 'domain': 'sea', 'speed': 0.527,
        'vision': 1.1, 'hp': 150, 'cost': 700, 'build_time': 14,
        'damage': 26, 'range': 1.1, 'targets': ('sea',), 'icon': 'DDS'},
    'destroyer_aa': {
        'label': 'Destroyer (AA Picket)', 'domain': 'sea', 'speed': 0.527,
        'vision': 1.1, 'hp': 140, 'cost': 720, 'build_time': 14,
        'damage': 20, 'range': 1.3, 'targets': ('air',), 'icon': 'DDA'},
    'destroyer_sea_land': {
        'label': 'Destroyer (Shore Gun)', 'domain': 'sea', 'speed': 0.490,
        'vision': 1.1, 'hp': 145, 'cost': 750, 'build_time': 14,
        'damage': 24, 'range': 1.25, 'targets': ('land', 'bridge'),
        'icon': 'DDL'},
    'supply_ship': {
        'label': 'Naval Supply Vessel', 'domain': 'sea', 'speed': 0.282,
        'vision': 0.8, 'hp': 130, 'cost': 650, 'build_time': 12,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'NSV',
        'supply_cap': 8000.0, 'supply_carrier': True},
    'aircraft_carrier': {
        'label': 'Fleet Carrier', 'domain': 'sea', 'speed': 0.527,
        'vision': 1.5, 'hp': 320, 'cost': 1500, 'build_time': 25,
        'damage': 10, 'range': 1.2, 'targets': ('air',), 'icon': 'CV'},

    # ----- AIR FORCE -----
    # 'fuel' is the total flight-plan distance (out + home) an aircraft
    # can be committed to. Aircraft always fly a full sortie: airfield ->
    # objective -> airfield.
    'fighter': {
        'label': 'Fighter Squadron', 'domain': 'air', 'speed': 2.64,
        'vision': 1.5, 'hp': 90, 'cost': 400, 'build_time': 8,
        'damage': 14, 'range': 0.8, 'targets': ('air', 'land'),
        'icon': 'FTR', 'fuel': 6.6},
    'bomber': {
        # 30% slower than a fighter; bombs only what lies under the flight
        # path, so its "range" is a tenth of a fighter's reach.
        'label': 'Bomber Wing', 'domain': 'air', 'speed': 2.18,
        'vision': 1.2, 'hp': 130, 'cost': 620, 'build_time': 12,
        'damage': 32, 'range': 0.06, 'targets': ('land', 'sea', 'bridge'),
        'icon': 'BMB', 'fuel': 11.8},
    'airforce_command': {
        # 60% slower than a fighter
        'label': 'Air Command Wing', 'domain': 'air', 'speed': 1.85,
        'vision': 1.2, 'hp': 110, 'cost': 900, 'build_time': 16,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'ACW', 'comm': True,
        'fuel': 14.1},
    'transport_air': {
        'label': 'Air Transport', 'domain': 'air', 'speed': 1.69,
        'vision': 1.0, 'hp': 120, 'cost': 500, 'build_time': 10,
        'damage': 0, 'range': 0, 'targets': (), 'icon': 'ATR',
        'capacity': 4, 'paradrop': True, 'fuel': 12.2},

    'blimp': {
        # a blimp STATION on wheels: drives like a lorry, and once the
        # envelope is raised it stands fast and out-sees any aircraft
        'label': 'Blimp Station', 'domain': 'land', 'speed': 0.141,
        'road_mult': 4.0, 'vision': 1.5, 'hp': 60, 'cost': 350,
        'build_time': 8, 'damage': 0, 'range': 0, 'targets': (),
        'icon': 'BLP', 'sprite_size': 0.62},

    # ----- RESEARCH ARSENAL (locked until the tech tree opens them) --
    'artillery': {
        'label': 'Field Artillery', 'domain': 'land', 'speed': 0.104,
        'road_mult': 3.5, 'vision': 0.9, 'hp': 90, 'cost': 380,
        'build_time': 9, 'damage': 26, 'range': 1.5,
        'targets': ('land', 'bridge'), 'icon': 'ART'},
    'heavy_tank': {
        'label': 'Heavy Tank', 'domain': 'land', 'speed': 0.160,
        'road_mult': 2.0, 'vision': 0.8, 'hp': 260, 'cost': 520,
        'build_time': 12, 'damage': 34, 'range': 0.7,
        'targets': ('land', 'bridge'), 'icon': 'HTK'},
    'heavy_bomber': {
        'label': 'Heavy Bomber Wing', 'domain': 'air', 'speed': 1.91,
        'vision': 1.2, 'hp': 180, 'cost': 950, 'build_time': 16,
        'damage': 48, 'range': 0.06,
        'targets': ('land', 'sea', 'bridge'), 'icon': 'HBM',
        'fuel': 17.0},
    'jet_fighter': {
        'label': 'Jet Fighter Squadron', 'domain': 'air', 'speed': 4.09,
        'vision': 1.5, 'hp': 100, 'cost': 1100, 'build_time': 14,
        'damage': 20, 'range': 0.9, 'targets': ('air', 'land'),
        'icon': 'JET', 'fuel': 4.9},
    'submarine': {
        'label': 'Submarine Flotilla', 'domain': 'sea', 'speed': 0.301,
        'vision': 0.9, 'hp': 110, 'cost': 900, 'build_time': 16,
        'damage': 30, 'range': 0.9, 'targets': ('sea',), 'icon': 'SUB'},
    'battleship': {
        'label': 'Battleship', 'domain': 'sea', 'speed': 0.480,
        'vision': 1.3, 'hp': 420, 'cost': 2000, 'build_time': 30,
        'damage': 40, 'range': 1.6,
        'targets': ('sea', 'land', 'bridge'), 'icon': 'BB'},
    # ---- the researched fleet: better hulls, not new roles
    'heavy_cruiser': {
        'label': 'Heavy Cruiser', 'domain': 'sea', 'speed': 0.510,
        'vision': 1.25, 'hp': 265, 'cost': 1250, 'build_time': 20,
        'damage': 33, 'range': 1.40,
        'targets': ('sea', 'land', 'bridge'), 'icon': 'CA'},
    'fast_battleship': {
        'label': 'Fast Battleship', 'domain': 'sea', 'speed': 0.560,
        'vision': 1.45, 'hp': 530, 'cost': 2650, 'build_time': 34,
        'damage': 53, 'range': 1.95,
        'targets': ('sea', 'land', 'bridge'), 'icon': 'BBF'},
}

BRANCH_OF = {'land': 'ARMY', 'sea': 'NAVY', 'air': 'AIR FORCE'}

# ---- the price of war ---------------------------------------------
# EVERY PIECE COSTS THREE TIMES what it did. Applied to the base
# chassis before the national modifiers scale it, so a nation that
# builds its armour dear still builds it dear.
COST_MULTIPLIER = 3
for _ut, _s in UNIT_TYPES.items():
    _s['cost'] = int(_s['cost'] * COST_MULTIPLIER)

# ---- supply defaults: logistics wins wars -------------------------------
# Everything but aircraft burns supply (lbs) to move and fight; aircraft
# operate in sorties instead (their airfield/carrier pays per takeoff).
# Naval units carry far more, making them more independent.
for _ut, _s in UNIT_TYPES.items():
    if _s['domain'] == 'air':
        _s.setdefault('supply_cap', 0.0)
        _s.setdefault('use_move', 0.0)
    elif _s['domain'] == 'sea':
        _s.setdefault('supply_cap', 1200.0)
        _s.setdefault('use_move', 5.0)      # lbs per second under way
    else:
        # tight: a column burns its stores crossing a small country,
        # so the supply chain is a critical mechanic, not a garnish.
        # (2.5 gave infantry a quarter-degree unsupported range --
        # every advance died at the border; 1.0 keeps the chain
        # essential over any real distance without strangling the
        # first march.)
        _s.setdefault('supply_cap', 80.0)
        _s.setdefault('use_move', 1.0)
FIRE_SUPPLY_FACTOR = 1.8                    # lbs per point of damage dealt

# ---- strategic material costs -----------------------------------------
# Production spends STEEL (hulls heaviest) and RUBBER (tyres and
# tracks) alongside money. Men cost neither. Derived from the dollar
# cost by domain, with flavour overrides where the history insists.
def material_cost(unit_type, country=None):
    """{'steel': n} for one piece of equipment. STEEL is the only
    material a factory spends -- machines do not eat, and men are
    not built. Tuned so a money-limited fortnight's slate bills
    roughly one fortnight's mines: it pinches, never strangles."""
    s = stats_for(unit_type, country) if country else UNIT_TYPES[unit_type]
    if unit_type == 'infantry':
        return {'steel': 0}
    dom = s['domain']
    # the divisors carry the money multiplier with them: it is the
    # PRICE that tripled, and a factory's steel bill per piece is
    # meant to stand where it stood
    div = (50 if dom == 'sea' else 80 if dom == 'air' else 100) \
        * COST_MULTIPLIER
    return {'steel': max(1, int(s['cost'] // div))}

# ---- sprite sizes: real-world proportions ------------------------------
# Relative to the fleet carrier (1.0, the largest thing afloat). The
# smallest unit (infantry) is a tenth of her, so the size spread reads as
# a real order-of-magnitude difference between a division and a fleet.
_SPRITE_SIZE = {
    'aircraft_carrier': 1.00,
    'naval_command': 0.73,
    'supply_ship': 0.73,
    'personnel_transport': 0.68,
    'destroyer_sea_sea': 0.60,
    'destroyer_aa': 0.60,
    'destroyer_sea_land': 0.60,
    'transport_air': 0.46,
    'bomber': 0.42,
    'airforce_command': 0.42,
    'army_command': 0.32,
    'aa_artillery': 0.28,
    'supply_truck': 0.28,
    'transport_truck': 0.28,
    'engineer': 0.28,
    'tank': 0.24,
    'fighter': 0.21,
    'infantry': 0.10,
    'battleship': 0.85,
    'submarine': 0.50,
    'heavy_bomber': 0.46,
    'jet_fighter': 0.22,
    'heavy_tank': 0.27,
    'artillery': 0.26,
}
for _ut, _s in UNIT_TYPES.items():
    _s['sprite_size'] = _SPRITE_SIZE.get(_ut, 0.6)

# ---- national rosters: same 18 chassis, five very different armies ----
# Each entry: (label, stat multipliers, briefing note). The multipliers
# exaggerate real WW2 national strengths -- German panzers and fighters,
# American industry, the Royal Navy and radar, Japanese carriers and
# range, Soviet mass -- while keeping overall faction power comparable.
NATION_UNITS = {
    'germany': {
        'infantry': ('Enlisted',
                     {'damage': 1.15, 'hp': 1.05, 'cost': 1.1},
                     "Doctrine-hardened Landser, dangerous in the attack."),
        'tank': ('Panzer IV',
                 {'damage': 1.4, 'hp': 1.3, 'cost': 1.35,
                  'build_time': 1.25, 'speed': 0.95},
                 "The long-75 workhorse of every panzer division."),
        'supply_truck': ('Opel Blitz Column', {},
                         "Standard lorry of the Wehrmacht trains."),
        'blimp': ('Zeppelin Aufklärer', {'vision': 1.1, 'cost': 1.15},
                  "The Graf's heirs: high, silent, all-seeing."),
        'transport_truck': ('Sd.Kfz. 251 Carrier',
                            {'hp': 1.15, 'cost': 1.1},
                            "Armoured halftracks shrug off small arms."),
        'aa_artillery': ('88mm Flak Battery',
                         {'damage': 1.3, 'range': 1.15, 'cost': 1.15},
                         "The dreaded Acht-Acht reaches high and hits hard."),
        'army_command': ('OKH Field HQ', {'vision': 1.1},
                         "Prussian staff work: crisp orders, wide awareness."),
        'engineer': ('Pionier Battalion', {'hp': 1.1},
                     "Assault pioneers, bridge-layers of the blitzkrieg."),
        'naval_command': ('Kriegsmarine Flagship', {},
                          "Flagship of a fleet built to raid, not to rule."),
        'personnel_transport': ('Marinefahrprahm', {'cost': 0.95},
                                "Sturdy landing barges of the Kriegsmarine."),
        'destroyer_sea_sea': ('Z-Class Destroyer', {'damage': 1.05},
                              "Big guns for a destroyer; too few hulls."),
        'destroyer_aa': ('Flakschiff Escort', {'damage': 1.05},
                         "Layered light flak screens the anchorage."),
        'destroyer_sea_land': ('Panzerschiff Raider',
                               {'damage': 1.15, 'hp': 1.1, 'cost': 1.15},
                               "Pocket-battleship guns turned on the shore."),
        'supply_ship': ('Dithmarschen Tender', {},
                        "Fleet tenders built for long raiding cruises."),
        'aircraft_carrier': ('Graf Zeppelin',
                             {'cost': 1.3, 'build_time': 1.3},
                             "The Reich's one great carrier, slow to finish."),
        'fighter': ('Bf 109 Messerschmitt',
                    {'damage': 1.3, 'speed': 1.1, 'cost': 1.15},
                    "Experten-flown; the deadliest gun platform aloft."),
        'bomber': ('Ju 88 Schnellbomber', {'speed': 1.1},
                   "Fast medium bomber; hard to intercept."),
        'airforce_command': ('Geschwader Stab', {},
                             "Veteran staff flights direct the air battle."),
        'transport_air': ('Ju 52 Tante Ju', {'hp': 1.05},
                          "Corrugated, dependable Tante Ju."),
        'artillery': ('10.5cm leFH Battalion', {'damage': 1.1},
                      "The divisional workhorse howitzer."),
        'heavy_tank': ('Tiger I', {'damage': 1.15, 'hp': 1.1,
                                   'cost': 1.15},
                       "88mm gun; nearly unanswerable when it arrives."),
        'heavy_bomber': ('He 177 Greif', {'cost': 0.95},
                         "The Reich's troubled strategic reach."),
        'jet_fighter': ('Me 262 Schwalbe', {'speed': 1.1, 'cost': 1.1},
                        "The first operational jet fighter."),
        'submarine': ('Type VII U-boat', {'cost': 0.8, 'damage': 1.15},
                      "The wolfpack tonnage war, perfected."),
        'heavy_cruiser': ('Admiral Hipper-class',
                          {'damage': 1.05},
                          "Heavy cruisers of the Kriegsmarine: a "
                          "long reach for commerce war."),
        'fast_battleship': ('Scharnhorst-class',
                            {'speed': 1.05},
                            "Fast capital ships built to outrun what "
                            "they cannot outgun."),
        'battleship': ('Bismarck-class', {'hp': 1.1},
                       "The Atlantic's most hunted ship."),
    },
    'usa': {
        'infantry': ('Enlisted',
                     {'damage': 1.25, 'hp': 1.3, 'cost': 0.85},
                     "The best-equipped rifleman of the war -- and plenty."),
        'tank': ('M4 Sherman', {'cost': 0.7, 'build_time': 0.8},
                 "Not the best tank; there are simply always more."),
        'supply_truck': ('GMC Deuce-and-a-Half',
                         {'supply_cap': 1.4, 'cost': 0.8, 'speed': 1.1},
                         "The deuce hauls more, faster, for less."),
        'blimp': ('K-Class Patrol Blimp',
                  {'vision': 1.15, 'cost': 1.1},
                  "The Navy's K-ships: no convoy under one was lost."),
        'transport_truck': ('M3 Half-track', {'cost': 0.8, 'hp': 1.1},
                            "Mass-built armoured taxi for the infantry."),
        'aa_artillery': ('M1 90mm AA Battery', {'cost': 0.85},
                         "Radar-directed 90mm guns off the assembly line."),
        'army_command': ('Corps Command Post', {'cost': 0.85},
                         "Radio nets and liaison jeeps everywhere."),
        'engineer': ('Seabee Battalion', {'cost': 0.85, 'hp': 1.15},
                     "Construction battalions: 'Can Do', anywhere."),
        'naval_command': ('Fleet Flagship', {'cost': 0.9},
                          "Command post of a two-ocean navy."),
        'personnel_transport': ('Attack Transport APA',
                                {'cost': 0.85, 'capacity': 1.34},
                                "Purpose-built assault shipping; more boots "
                                "per lift."),
        'destroyer_sea_sea': ('Fletcher-class',
                              {'cost': 0.85, 'hp': 1.05},
                              "The war's definitive destroyer, by the dozen."),
        'destroyer_aa': ('Atlanta-class AA',
                         {'cost': 0.85, 'damage': 1.1},
                         "A cruiser made entirely of 5-inch AA guns."),
        'destroyer_sea_land': ('Cleveland Gun Cruiser', {'cost': 0.85},
                               "Six-inch broadsides on call for the beach."),
        'supply_ship': ('Liberty Ship',
                        {'cost': 0.7, 'supply_cap': 1.3},
                        "Launched faster than they can be sunk."),
        'aircraft_carrier': ('Essex-class Carrier',
                             {'cost': 0.85, 'build_time': 0.85, 'hp': 1.1},
                             "The fleet carrier as an industrial product."),
        'fighter': ('P-51 Mustang',
                    {'fuel': 1.3, 'damage': 1.1, 'cost': 0.9},
                    "Long-legged escort; hunts to the target and back."),
        'bomber': ('B-17 Fortress', {'hp': 1.35, 'damage': 1.15},
                   "Flying Fortress: bristling guns, brings crews home."),
        'airforce_command': ('USAAF Air Command', {'cost': 0.9},
                             "Bomber streams marshalled by the hundred."),
        'transport_air': ('C-47 Skytrain',
                          {'cost': 0.85, 'capacity': 1.26},
                          "The immortal Gooney Bird lifts more for less."),
        'artillery': ('105mm M2A1 Battalion', {'cost': 0.9},
                      "Massed, fast-shifting fire support."),
        'heavy_tank': ('M26 Pershing', {'cost': 0.9},
                       "Arrives late, hits hard, keeps coming."),
        'heavy_bomber': ('B-29 Superfortress', {'hp': 1.2},
                         "Pressurised and long-legged; flies above the flak."),
        'jet_fighter': ('P-80 Shooting Star', {},
                        "America's jet age opens."),
        'submarine': ('Gato-class', {'hp': 1.1},
                      "The Pacific commerce war in steel."),
        'heavy_cruiser': ('Baltimore-class',
                          {'hp': 1.05},
                          "The war-built heavy cruiser: radar, "
                          "armour and eight-inch guns."),
        'fast_battleship': ('Iowa-class',
                            {'speed': 1.08, 'damage': 1.05},
                            "Thirty-three knots and sixteen inches -- "
                            "the fast battleship perfected."),
        'battleship': ('North Carolina-class', {'speed': 1.1},
                       "New battleships riding with the carriers."),
    },
    'britain': {
        'infantry': ('Enlisted', {'hp': 1.1},
                     "Steady regulars of Empire and Commonwealth."),
        'tank': ('Matilda II', {'hp': 1.25, 'speed': 0.85},
                 "The Queen of the Desert: shellproof, and in no hurry."),
        'supply_truck': ('Bedford QL Column', {},
                         "The Army's dependable workhorse lorry."),
        'blimp': ('Balloon Command Section', {'hp': 1.2},
                  "Winched veterans of the Blitz, eyes ever upward."),
        'transport_truck': ('Bren Carrier Section', {'speed': 1.1},
                            "Nippy tracked carriers rush the Bren forward."),
        'aa_artillery': ('QF 3.7-in AA Battery',
                         {'range': 1.1, 'vision': 1.15},
                         "Radar-laid heavy AA of the Home defences."),
        'army_command': ('GHQ Staff Column', {'vision': 1.2},
                         "Ultra intercepts brief the staff caravan."),
        'engineer': ('Royal Engineers', {'hp': 1.05},
                     "Sappers of the Corps: bridges built under fire."),
        'naval_command': ('Admiralty Flagship',
                          {'vision': 1.2, 'hp': 1.1},
                          "The Royal Navy's eyes reach past every horizon."),
        'personnel_transport': ('Landing Ship Infantry', {},
                                "Converted liners carrying assault craft."),
        'destroyer_sea_sea': ('Tribal-class',
                              {'damage': 1.25, 'hp': 1.15},
                              "The Royal Navy's finest gun destroyers."),
        'destroyer_aa': ('Dido-class AA Cruiser',
                         {'damage': 1.2, 'hp': 1.1},
                         "Quick-firing 5.25s screen the convoys."),
        'destroyer_sea_land': ('Monitor HMS Roberts',
                               {'damage': 1.25, 'range': 1.1},
                               "15-inch guns dedicated to the shore."),
        'supply_ship': ('RFA Auxiliary', {'hp': 1.1},
                        "The Fleet Train keeps the squadrons at sea."),
        'aircraft_carrier': ('Illustrious-class', {'hp': 1.25},
                             "Armoured flight decks bounce the bombs off."),
        'fighter': ('Supermarine Spitfire',
                    {'damage': 1.15, 'vision': 1.2, 'hp': 1.1},
                    "Vectored by radar; a legend in the turn."),
        'bomber': ('Handley Page Halifax', {'damage': 1.25},
                   "Four engines over the Ruhr, night after night."),
        'airforce_command': ('RAF Group HQ', {'vision': 1.25},
                             "The Dowding system: plotted, tracked, met."),
        'transport_air': ('Dakota Mk III', {},
                          "Lend-lease Dakotas on Commonwealth routes."),
        'artillery': ('25-Pounder Regiment', {'cost': 0.9},
                      "The Commonwealth's beloved gun-howitzer."),
        'heavy_tank': ('Churchill VII', {'hp': 1.2, 'speed': 0.85},
                       "Slow, but climbs what stops the rest."),
        'heavy_bomber': ('Avro Lancaster', {'damage': 1.1},
                         "The night offensive's heavy hand."),
        'jet_fighter': ('Gloster Meteor', {},
                        "Britain answers the jet question."),
        'submarine': ('T-class', {},
                      "Quiet boats for narrow seas."),
        'heavy_cruiser': ('County-class',
                          {'vision': 1.08},
                          "Long-legged cruisers built to police an "
                          "empire's sea lanes."),
        'fast_battleship': ('Renown-class',
                            {'hp': 1.06},
                            "Refitted battlecruisers: first to the "
                            "sound of the guns."),
        'battleship': ('King George V-class', {},
                       "The Royal Navy's modern line."),
    },
    'japan': {
        'infantry': ('Enlisted',
                     {'cost': 0.75, 'speed': 1.15, 'damage': 1.1,
                      'hp': 0.85},
                     "Fanatic light infantry, fast through any country."),
        'tank': ('Type 97 Chi-Ha',
                 {'cost': 0.7, 'hp': 0.75, 'speed': 1.05},
                 "Thin-skinned but quick and cheap."),
        'supply_truck': ('Type 94 Column', {'cost': 0.9},
                         "Light trucks on long, thin supply lines."),
        'blimp': ('Kansoku Balloon Corps', {'cost': 0.85, 'hp': 0.8},
                  "Paper-light observation balloons, cheap and brave."),
        'transport_truck': ('Type 1 Ho-Ha', {'cost': 0.9},
                            "Spartan halftracks of the mobile brigades."),
        'aa_artillery': ('Type 88 AA Battery', {'cost': 0.9},
                         "Standard heavy AA of the home islands."),
        'army_command': ('Area Army HQ', {},
                         "Rigid but relentless staff planning."),
        'engineer': ('Pioneer Regiment', {'speed': 1.1},
                     "Jungle roads cut at astonishing speed."),
        'naval_command': ('Yamato Flagship',
                          {'hp': 1.3, 'cost': 1.2},
                          "The greatest battleship afloat leads the fleet."),
        'personnel_transport': ('Daihatsu Convoy',
                                {'speed': 1.1, 'cost': 0.9},
                                "Fast barge convoys slip between islands."),
        'destroyer_sea_sea': ('Fubuki-class',
                              {'damage': 1.2, 'speed': 1.05},
                              "Long Lance torpedoes strike from the dark."),
        'destroyer_aa': ('Akizuki-class', {'damage': 1.1},
                         "Purpose-built AA destroyers of the screen."),
        'destroyer_sea_land': ('Mogami-class', {'damage': 1.1},
                               "Heavy cruiser gunnery against the beach."),
        'supply_ship': ('Maru Convoy', {'cost': 0.9},
                        "Requisitioned marus feed the perimeter."),
        'aircraft_carrier': ('Akagi Fleet Carrier',
                             {'hp': 1.15, 'cost': 0.85, 'build_time': 0.85},
                             "The world's finest carrier striking force."),
        'fighter': ('A6M Zero-sen',
                    {'fuel': 1.5, 'speed': 1.05, 'damage': 1.1, 'hp': 0.8},
                    "Unmatched range and agility; no armour at all."),
        'bomber': ('G4M Rikko',
                   {'fuel': 1.35, 'damage': 1.1, 'hp': 0.8},
                   "Very long-ranged; burns when caught."),
        'airforce_command': ('Koku Kantai HQ', {'fuel': 1.2},
                             "Naval air staffs range across the ocean."),
        'transport_air': ('Ki-57 Topsy', {'fuel': 1.2},
                          "Long-range transport of the southern drives."),
        'artillery': ('Type 91 Battalion', {'cost': 0.9},
                      "Light guns that travel anywhere."),
        'heavy_tank': ('Type 3 Chi-Nu', {'cost': 0.8,
                                         'damage': 0.85},
                       "The Empire's best armour, outmatched."),
        'heavy_bomber': ('Ki-67 Hiryu', {'speed': 1.05, 'hp': 0.8},
                         "The Empire's finest bomber, come too late."),
        'jet_fighter': ('Nakajima Kikka', {'cost': 1.1},
                        "A desperate leap for the jet age."),
        'submarine': ('I-class', {'vision': 1.1},
                      "Long-ranged fleet boats with seaplanes."),
        'heavy_cruiser': ('Takao-class',
                          {'damage': 1.1},
                          "Torpedo-heavy cruisers drilled for the "
                          "night action."),
        'fast_battleship': ('Kongo-class Refit',
                            {'speed': 1.1},
                            "Rebuilt battlecruisers: fast enough to "
                            "run with the carriers."),
        'battleship': ('Nagato-class', {'hp': 1.25, 'cost': 1.2},
                       "First with sixteen-inch guns; pride of the line."),
    },
    'soviet': {
        'infantry': ('Enlisted',
                     {'cost': 0.6, 'hp': 1.15, 'damage': 0.95,
                      'build_time': 0.8},
                     "Massed frontoviki: cheap, tough, and everywhere."),
        'tank': ('T-34 Medium Tank',
                 {'cost': 0.75, 'build_time': 0.75, 'damage': 1.15,
                  'hp': 1.1},
                 "Sloped armour and sheer numbers -- the war-winner."),
        'supply_truck': ('ZIS-5 Column', {'hp': 1.1},
                         "Rugged three-tonners through rasputitsa mud."),
        'blimp': ('Aerostat Observation Post', {'cost': 0.9},
                  "The aerostats that ringed Moscow, gone mobile."),
        'transport_truck': ('Studebaker US6', {'cost': 0.9},
                            "Lend-Lease Studebakers carry the Guards."),
        'aa_artillery': ('85mm 52-K Battery', {'damage': 1.15},
                         "The 85 doubles against tanks and bombers alike."),
        'army_command': ('Stavka Field HQ', {'hp': 1.1},
                         "Deep-echeloned command, dug in hard."),
        'engineer': ('Sapper Brigade', {'cost': 0.85, 'hp': 1.1},
                     "Sappers bridge rivers under fire, nightly."),
        'naval_command': ('Red Banner Flagship', {'cost': 1.1},
                          "Flagship of a coastal, riverine navy."),
        'personnel_transport': ('Naval Inf. Transport', {},
                                "Black-capped naval infantry storm ashore."),
        'destroyer_sea_sea': ('Gnevny-class', {'cost': 0.95},
                              "Quick Project 7 boats of the Red fleets."),
        'destroyer_aa': ('Tashkent AA Leader', {},
                         "The Blue Cruiser leads the flak screen."),
        'destroyer_sea_land': ('Marat Gun Line',
                               {'damage': 1.1, 'speed': 0.9},
                               "Old battleship turrets pound the coast."),
        'supply_ship': ('Arctic Convoy Ship', {'hp': 1.15},
                        "Ice-hardened hulls on the Murmansk run."),
        'aircraft_carrier': ('Project 71 Carrier',
                             {'cost': 1.4, 'build_time': 1.4},
                             "A paper design, pursued at great expense."),
        'fighter': ('Yak-3',
                    {'speed': 1.05, 'cost': 0.85, 'fuel': 0.85},
                    "Feather-light dogfighter, short on legs."),
        'bomber': ('Il-2 Sturmovik',
                   {'hp': 1.4, 'damage': 1.1, 'fuel': 0.85, 'cost': 0.9},
                   "The flying tank: armoured bath, rocket rails."),
        'airforce_command': ('VVS Air Army Staff', {'cost': 0.9},
                             "Air armies massed over the breakthrough."),
        'transport_air': ('Li-2 Transport', {'cost': 0.9},
                          "Licence-built Dakotas supply the partisans."),
        'artillery': ('ML-20 Gun-Howitzer Rgt', {'damage': 1.15},
                      "The god of war speaks in salvoes."),
        'heavy_tank': ('IS-2', {'damage': 1.1, 'cost': 0.95},
                       "Breakthrough armour for the drive west."),
        'heavy_bomber': ('Pe-8 Wing', {'cost': 0.95},
                         "The VVS's small strategic arm."),
        'jet_fighter': ('MiG-9', {},
                        "Captured science, Soviet steel."),
        'submarine': ('Shchuka-class', {'cost': 0.85},
                      "Coastal boats in every sea."),
        'heavy_cruiser': ('Kirov-class',
                          {'cost': 0.92},
                          "Cruisers of the coastal fleets, built "
                          "quickly and cheaply."),
        'fast_battleship': ('Sovetsky Soyuz-class',
                            {'hp': 1.08},
                            "The great programme laid down at last: "
                            "armour above all."),
        'battleship': ('Gangut-class (mod.)', {'hp': 0.9, 'cost': 0.8},
                       "The old guard, re-gunned."),
    },
}


def _scale_stats(base, mods):
    out = dict(base)
    for key, mult in mods.items():
        v = base[key] * mult
        if key == 'cost':
            out[key] = max(5, int(round(v / 5.0) * 5))
        elif key in ('hp', 'build_time', 'capacity'):
            out[key] = max(1, int(round(v)))
        else:
            out[key] = v
    return out


# country -> unit_type -> full stats dict (national label + note included)
NATION_UNIT_STATS = {}
for _c, _d in NATION_UNITS.items():
    NATION_UNIT_STATS[_c] = {}
    for _ut, _base in UNIT_TYPES.items():
        _lbl, _mods, _note = _d.get(_ut, (_base['label'], {}, ""))
        _s = _scale_stats(_base, _mods)
        _s['label'] = _lbl
        _s['note'] = _note
        NATION_UNIT_STATS[_c][_ut] = _s


def stats_for(unit_type, country):
    """The nation-specific stat block (falls back to the base chassis)."""
    return NATION_UNIT_STATS.get(country, {}).get(unit_type,
                                                  UNIT_TYPES[unit_type])


FIRE_INTERVAL = 1.4        # seconds between shots
AIR_LIFT = LIFT_AIR        # air counters layer above ground counters
GROUND_LIFT = LIFT_GROUND  # low lifts: tall ones parallax when panning


class Unit:
    next_id = 1

    def __init__(self, game, unit_type, country, pos_vec):
        self.id = Unit.next_id
        Unit.next_id += 1
        self.game = game
        self.unit_type = unit_type
        self.stats = stats_for(unit_type, country)
        self.country = country
        self.pos = Vec3(pos_vec)          # unit vector on the sphere
        self.pos.normalize()
        self.hp = self.stats['hp']
        self.max_hp = self.stats['hp']
        self.selected = False
        self.alive = True
        self.visible_to_player = False
        self.in_contact = True            # inside a friendly comm circle

        # aircraft: where the machine is parked / where the flight ends
        self.based_at = None              # Airfield or carrier Unit
        self.landing_at = None            # airfield the flight returns to
        self.drop_at = None               # paradrop point on this sortie

        # logistics
        self.supply = self.stats['supply_cap']
        self.sortie_plan = []     # parked aircraft: waypoints on the board
        self.sortie_targets = []  # aloft: remaining briefed targets
        # carriers hold aviation supply for their air wing's sorties
        self.av_stock = 6000.0 if unit_type == 'aircraft_carrier' else 0.0

        # Orders
        self.path = []            # list of (unit_vec, speed_mult) waypoints
        self.order_queue = []     # queued orders: dicts {kind, ...}
        self.current_order = None
        self.attack_target = None     # Unit or Bridge
        self.fire_cooldown = 0.0
        self.cargo = []           # for transports
        self.plan_pending = None  # background route job token
        self.carried_by = None

        self._build_visuals()

    # ------------------------------------------------------------- visuals
    def _build_visuals(self):
        g = self.game
        # root sits at the globe centre, oriented so +Z is the surface
        # normal under the unit; all children are flat map markers.
        self.root = g.render.attachNewNode('unit_%d' % self.id)

        # tiny per-unit lift offset prevents z-fighting of stacked counters
        lift = GLOBE_RADIUS * self.altitude() + (self.id % 37) * 0.0008
        self.holder = self.root.attachNewNode('holder')
        self.holder.setPos(0, 0, lift)

        base = unit_layer_base(self.id, self.stats['domain'] == 'air')
        self._layer_base = base
        # the unit IS its pictogram: every nation's counter wears the
        # SAME ink (no faction tinting) and turns to face its
        # direction of travel; ownership flies on the standard above
        self.counter = make_icon_quad(g.loader, self.unit_type, 'unit',
                                      half=1.0, nation=self.country)
        self.counter.setColorScale(0.93, 0.90, 0.83, 1.0)
        self.counter.reparentTo(self.holder)
        set_marker_layer(self.counter, base + 2)
        # a FOREIGN unit flies its nation's tiny standard; your own
        # men carry no flag (you know your own)
        self.flag = None
        if self.country != g.player_country:
            self.flag = make_flag_quad(g.loader, self.country,
                                       half=0.32)
            self.flag.setPos(0, 1.48, 0)
            self.flag.reparentTo(self.holder)
            set_marker_layer(self.flag, base + 8)

        friendly = (self.country == g.player_country)
        ring_col = ((0.4, 1.0, 0.4, 0.95) if friendly
                    else (1.0, 0.35, 0.28, 0.95))
        self.sel_ring = make_flat_ring('sel', 1.25, ring_col,
                                       thickness=2.0, segments=24)
        self.sel_ring.reparentTo(self.holder)
        set_marker_layer(self.sel_ring, base + 3)
        self.sel_ring.hide()
        # the guns' reach: built lazily on first selection
        self._layer_base = base
        self.range_ring = None

        # range decals (hidden for enemy units); the vision field and the
        # merged comm-net outline are both drawn by the globe shader
        self.decals = self.root.attachNewNode('decals')

        # count badge: carriers show their air wing, transports their
        # embarked passengers
        self.count_badge = None
        self.count_badge_tn = None
        if self.unit_type == 'aircraft_carrier' or self.stats.get('capacity'):
            badge_icon = ('fighter' if self.unit_type == 'aircraft_carrier'
                          else 'infantry')
            from models import make_flat_disc
            self.count_badge = self.holder.attachNewNode('count_badge')
            pill = make_flat_disc('pill', 0.46,
                                  (0.93, 0.90, 0.83, 0.96),
                                  segments=20)
            pill.setPos(0, -1.38, 0)
            pill.reparentTo(self.count_badge)
            rim = make_flat_ring('rim', 0.46, (0.13, 0.11, 0.09, 1.0),
                                 thickness=1.6, segments=20)
            rim.setPos(0, -1.38, 0)
            rim.reparentTo(self.count_badge)
            ic = make_icon_quad(g.loader, badge_icon, 'dark', half=0.30,
                                depth=8)
            ic.setPos(-0.14, -1.38, 0)
            ic.reparentTo(self.count_badge)
            tn = TextNode('badge_count')
            tn.setAlign(TextNode.ALeft)
            if g.hud_font:
                tn.setFont(g.hud_font)
            tn.setTextColor(0.13, 0.11, 0.09, 1)
            self.count_badge_tn = tn
            np_ = self.count_badge.attachNewNode(tn)
            np_.setP(-90)
            np_.setScale(0.5)
            np_.setPos(0.10, -1.55, 0)
            np_.setDepthOffset(8)
            set_marker_layer(self.count_badge, base + 4)
            self.count_badge.hide()

        # out-of-supply warning above the counter
        self.nosupply_icon = None
        if self.stats['supply_cap'] > 0:
            self.nosupply_icon = make_icon_quad(g.loader, 'nosupply',
                                                'red', half=0.34, depth=8)
            self.nosupply_icon.setPos(0, 1.30, 0)
            self.nosupply_icon.reparentTo(self.holder)
            set_marker_layer(self.nosupply_icon, base + 7)
            self.nosupply_icon.hide()

        self._oriented_at = None
        self._heading = 0.0
        # fixed world size, proportioned to the real machine
        self.holder.setScale(UNIT_SPRITE_SCALE *
                             self.stats['sprite_size'])
        self.update_visual()

    def set_wing_count(self, n):
        self.set_badge_count(n)

    def set_badge_count(self, n):
        if self.count_badge is None:
            return
        if n > 0:
            self.count_badge_tn.setText("x%d" % n)
            if self.count_badge.isHidden():
                self.count_badge.show()
        elif not self.count_badge.isHidden():
            self.count_badge.hide()

    def has_supply(self):
        return self.stats['supply_cap'] <= 0 or self.supply > 0

    def set_nosupply_flag(self, starving):
        if self.nosupply_icon is None:
            return
        if starving and self.nosupply_icon.isHidden():
            self.nosupply_icon.show()
        elif not starving and not self.nosupply_icon.isHidden():
            self.nosupply_icon.hide()

    def altitude(self):
        return AIR_LIFT if self.stats['domain'] == 'air' else GROUND_LIFT

    def update_visual(self):
        if self._oriented_at == self.pos:
            return
        self._oriented_at = Vec3(self.pos)
        orient_to_surface(self.root, self.pos)
        # turn the pictogram to face the direction of travel
        if self.path:
            target = self.path[0][0]
            d = Vec3(target) - self.pos * self.pos.dot(target)
            n = north_tangent(self.pos)
            e = n.cross(self.pos)
            if d.lengthSquared() > 1e-10:
                import math as _m
                self._heading = _m.degrees(_m.atan2(d.dot(e), d.dot(n)))
        self.holder.setH(-self._heading)

    def set_marker_scale(self, scale):
        pass    # sprites keep a fixed world size at every zoom

    def max_attack_range(self):
        """The farthest this unit's guns can EVER strike, in world
        units -- the best case of the gunnery law: most arms are
        capped by their own DAYTIME eyes; tanks, artillery and
        warships reach TWICE their eyes when a friend observes the
        target; aircraft use their airborne eyes (a bomber strikes
        far shorter than it sees)."""
        rng = self.stats['range']
        if self.stats['damage'] <= 0 or rng <= 0:
            return 0.0
        day = self.stats['vision'] * VISION_SCALE
        if self.is_air():
            day *= AIR_VISION_MULT
        if (self.stats['domain'] == 'sea'
                or self.unit_type in self.game.INDIRECT_FIRE):
            return min(rng, day * 2.0)
        return min(rng, day)

    def _show_range_ring(self):
        """A THIN RED CIRCLE at the guns' longest reach, drawn while
        the unit is selected. Parented to the unit's root (not the
        scaled holder), so its radius is true world size at every
        zoom -- and separate from the vision circle, because for the
        long arms the two are NOT the same ring."""
        r = self.max_attack_range()
        if r <= 0.0:
            return
        if self.range_ring is None:
            ring = make_flat_ring('atk_range', r,
                                  (0.85, 0.18, 0.12, 0.85),
                                  thickness=1.5, segments=48)
            ring.reparentTo(self.root)
            ring.setPos(0, 0, GLOBE_RADIUS * LIFT_RING)
            set_marker_layer(ring, self._layer_base + 2)
            self.range_ring = ring
        self.range_ring.show()

    def set_selected(self, sel):
        self.selected = sel
        if sel:
            self.sel_ring.show()
            self._show_range_ring()
        else:
            self.sel_ring.hide()
            if self.range_ring is not None:
                self.range_ring.hide()

    # -------------------------------------------------------------- orders
    def clear_orders(self):
        self.path = []
        self.order_queue = []
        self.current_order = None
        self.attack_target = None
        self.sortie_plan = []
        self.sortie_targets = []
        # a route still cooking in the planner belongs to the OLD
        # orders: forgetting this let a lorry boarded mid-planning
        # receive its stale continental path after a paradrop and
        # drive home straight across the ocean
        self.plan_pending = None

    def give_order(self, order, queue=False):
        if not queue:
            self.clear_orders()
            # a DIRECT order from the hand outranks every standing
            # arrangement -- including a transport's hold at the
            # ramp for boarders who never came
            order['direct'] = True
        self.order_queue.append(order)
        self.game.on_order_given(self, order, queue)

    def is_air(self):
        return self.stats['domain'] == 'air'

    def vision_range(self):
        """Fog-of-war radius: 1/5 of the base stat, aircraft see 3x
        further, and night halves everything."""
        r = self.stats['vision'] * VISION_SCALE
        if self.is_air():
            r *= AIR_VISION_MULT
        elif getattr(self, 'deployed', False):
            # a blimp on station out-sees any aircraft by half again
            r *= AIR_VISION_MULT * 1.5
        if not self.game.is_day(self.pos):
            r *= NIGHT_VISION_FACTOR
        return r

    def comm_range(self):
        # the wireless net is radio, not eyes: unaffected by vision rules
        if self.stats.get('comm'):
            return self.stats['vision'] * COMM_RADIUS_FACTOR
        return 0.0

    def dist_to(self, other_pos):
        return angle_between(self.pos, other_pos) * GLOBE_RADIUS

    def can_target(self, kind):
        return kind in self.stats['targets']

    # -------------------------------------------------------------- update
    def update(self, dt):
        if not self.alive or self.carried_by:
            return
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)

        if self.current_order is None and self.order_queue:
            nxt = self.order_queue[0]
            # a transport holds at the ramp until every unit ordered
            # aboard has embarked -- waypoints can be planned ahead.
            # BUT a DIRECT order sails at once: a boarder who never
            # arrives must never pin the ship to the quay forever --
            # the player's fresh move outranks the wait, and the
            # riders' board orders simply chase the new anchorage.
            hold = (self.stats.get('capacity')
                    and self.stats['domain'] != 'air'
                    and nxt.get('kind') in ('move', 'unload')
                    and not nxt.get('auto')
                    and not nxt.get('direct')
                    and self.game.inbound_boarders(self))
            if not hold:
                self.current_order = self.order_queue.pop(0)
                self.game.begin_order(self, self.current_order)

        # an attack order CHASES: the march corrects onto the
        # target's current position while it stays in sight
        if self.current_order is not None:
            self.game.tick_attack_pursuit(self)

        # a route is still being planned in the background. THE GUNS
        # DO NOT WAIT ON THE MAP ROOM: a unit standing with an enemy
        # in range fires while its next route is being worked out --
        # returning here outright was why troops so often sat and
        # watched a column go past.
        if getattr(self, 'plan_pending', None):
            self._combat(dt)
            return

        # no supplies: the column halts and the guns fall silent
        if not self.has_supply():
            if self.current_order and not self.path:
                if self.game.order_finished(self, self.current_order):
                    self.current_order = None
            return

        moved = self._follow_path(dt)
        if self.drop_at is not None:
            self.game.check_paradrop(self)
        # a briefed sortie works down its target list as each falls
        if self.sortie_targets and (
                self.attack_target is None
                or not getattr(self.attack_target, 'alive', False)):
            self.attack_target = self.sortie_targets.pop(0)
        self._combat(dt)

        # arrival-by-proximity orders complete the moment the unit is
        # close enough, even with path legs left (a section that runs
        # dry AT the gate still signs on); everything else completes
        # when its path is walked out
        near_kinds = ('garrison', 'board')
        if self.current_order and (
                not self.path
                or self.current_order.get('kind') in near_kinds):
            done = self.game.order_finished(self, self.current_order)
            # order_finished may destroy this unit (e.g. an aircraft with
            # nowhere left to land); stop touching it if so
            if not self.alive or self.root is None:
                return
            if done:
                self.current_order = None
                self.path = []
        if moved:
            self.update_visual()

    def _follow_path(self, dt):
        if not self.path:
            return False
        target, speed_mult = self.path[0]
        on_rail = abs(speed_mult - RAIL_LEG_MULT) < 1e-6
        if on_rail:
            # the TRAIN sets the pace: every unit aboard -- marching
            # Enlisted included -- rides at a lorry's road speed
            speed = (RAIL_TRAIN_SPEED * UNIT_SPEED_FACTOR *
                     self.game.game_speed)
        else:
            # on a road leg the ROUTING mult is only a flag: each
            # chassis brings its own paved-road factor (feet gain
            # little, wheels a lot), so column speeds stay true to life
            eff_mult = (self.stats.get('road_mult', 3.0)
                        if speed_mult > 1.001 else speed_mult)
            speed = (self.stats['speed'] * UNIT_SPEED_FACTOR *
                     eff_mult * self.game.game_speed)
        # the climb bites: off-road land movement pays the real grade
        # (roads are engineered and exempt; one sample per leg)
        if self.stats['domain'] == 'land' and speed_mult <= 1.001:
            if getattr(self, '_slope_tgt', None) is not target:
                self._slope_tgt = target
                la1, lo1 = vec_to_latlon(self.pos)
                la2, lo2 = vec_to_latlon(target)
                self._slope_fac = self.game.world.terrain.speed_factor(
                    la1, lo1, la2, lo2)
            speed *= self._slope_fac
        if getattr(self, 'submerged', False):
            speed *= 0.45               # on the batteries, creeping
        ang = angle_between(self.pos, target)
        step = speed * dt / GLOBE_RADIUS
        if ang <= step or ang < 1e-5:
            newpos = Vec3(target)
            arrived = True
        else:
            newpos = slerp(self.pos, target, step / ang)
            arrived = False
        # THE WALL: field works admit only men on foot. A vehicle
        # stepping into a bunker's perimeter is turned along the
        # rim and rolls around it; Enlisted walk straight through.
        if (self.stats['domain'] == 'land'
                and self.unit_type != 'infantry' and not on_rail):
            from structures import BUNKER_RADIUS
            wall_ang = BUNKER_RADIUS / GLOBE_RADIUS
            for b in self.game.bunkers:
                d_ang = angle_between(newpos, b.pos)
                if d_ang >= wall_ang:
                    continue
                # radial direction in the tangent plane at the works
                out = newpos - Vec3(b.pos) * newpos.dot(b.pos)
                if out.lengthSquared() < 1e-12:
                    # dead centre: pick the side nearer the goal
                    out = Vec3(target) - Vec3(b.pos) \
                        * Vec3(target).dot(b.pos)
                    if out.lengthSquared() < 1e-12:
                        out = north_tangent(Vec3(b.pos))
                out.normalize()
                # a touch of spin so a head-on approach still slides
                # around instead of butting the wall forever
                spin = Vec3(b.pos).cross(out)
                to_goal = Vec3(target) - Vec3(newpos)
                if spin.dot(to_goal) < 0:
                    spin = -spin
                out = out + spin * 0.35
                out.normalize()
                import math as _m
                newpos = (Vec3(b.pos) * _m.cos(wall_ang)
                          + out * _m.sin(wall_ang))
                newpos.normalize()
                # a goal INSIDE the wall can never be reached by a
                # vehicle: the rim IS arrival, or it stalls forever
                arrived = (angle_between(Vec3(target), Vec3(b.pos))
                           < wall_ang)
                break
        self.pos = newpos
        if arrived:
            self.path.pop(0)
        moved_wu = min(step, ang) * GLOBE_RADIUS
        if self.stats['domain'] == 'air':
            # the fuel odometer: what a retasking mid-air may still ask
            # of the tanks is endurance minus this
            self._flown = getattr(self, '_flown', 0.0) + moved_wu
        if self.stats['supply_cap'] > 0 and not on_rail:
            # the ORIGINAL harsh economy, by design: the column burns
            # stores every second it is under way, and no advance
            # outlives its train -- supply reliance is a core mechanic.
            # RAIL legs are the one exemption: the railway carries the
            # column's stores with it
            burn = self.stats['use_move'] * dt * self.game.game_speed
            if getattr(self, 'submerged', False):
                burn *= 2.0             # running submerged drinks amps
            self.supply = max(0.0, self.supply - burn)
            if self.supply <= 0.0 and getattr(self, 'submerged', False):
                self.game.set_submerged(self, False, forced=True)
        return True

    def _combat(self, dt):
        if self.stats['damage'] <= 0:
            return
        if self.based_at is not None:
            return          # parked aircraft don't fight; scramble them
        target = self.attack_target
        if target is not None and not getattr(target, 'alive', True):
            self.attack_target = None
            target = None
        # peace (declared mid-fight or by stale order) drops the target
        if (target is not None
                and getattr(target, 'country', None) is not None
                and isinstance(target, Unit)
                and not self.game.at_war(self.country, target.country)):
            self.attack_target = None
            target = None
        if target is None:
            if self.fire_cooldown > 0.0:
                return          # scan for targets only when guns are ready
            target = self.game.auto_acquire_target(self)
            if target is None:
                self.fire_cooldown = 0.35
                return
        # the gunnery law: range is capped by the unit's own eyes
        # (or a friendly observer's, for the indirect-fire arms)
        if self.dist_to(target.pos) <= \
                self.game.effective_fire_range(self, target):
            if self.fire_cooldown <= 0.0:
                self.game.resolve_shot(self, target)
                self.fire_cooldown = FIRE_INTERVAL

    def take_damage(self, amount, attacker=None):
        self.hp -= amount
        if self.hp <= 0 and self.alive:
            self.game.unit_destroyed(self, attacker)

    def destroy(self):
        self.alive = False
        for u in self.cargo:
            u.alive = False
            u.cleanup()
        self.cleanup()

    def cleanup(self):
        if self.root:
            self.root.removeNode()
            self.root = None
            self.decals = None
