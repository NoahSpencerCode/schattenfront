"""
Game Configuration and Constants
"""

# Display Settings
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FULLSCREEN = False
WINDOW_TITLE = "Global Operations - 1939 Edition"
SHOW_FPS_METER = False        # set True to display the frame-rate meter

# Globe Settings
GLOBE_RADIUS = 30.0
GLOBE_SEGMENTS = 240          # 240 x 120 x 2 = ~57,600 triangles
GLOBE_RINGS = 120

# Day/Night Cycle
DAY_CYCLE_LENGTH = 240.0      # seconds for one full planet day
NIGHT_DARKNESS = 0.55         # how dark the night side is (0-1)

# Camera (distances from globe centre; surface is at 30)
CAM_MIN_DIST = 30.5           # 0.5 above the surface — 10x closer than v1
CAM_MAX_DIST = 160.0
CAM_START_DIST = 90.0
CAM_ZOOM_LABELS = 95.0        # country names shown when farther than this
CAM_ZOOM_CITY_LABELS = 55.0   # city names appear when closer than this

# Zoom detail overlay (Google-maps style realtime map rendering).
# The zoom range is split into THREE fixed render tiers: within a tier
# the rendered window and fidelity never change, so zooming produces no
# re-render wiggle. Each tier is delivered as a mosaic of small tiles,
# at most ONE uploaded per frame, so a tier switch never stalls a frame
# (the per-frame cost is identical to the old always-rerendering path).
DETAIL_ACTIVATE_ALT = 40.0    # altitude below which the overlay activates
# tier hand-over altitudes: an ultra-close street-level tier keeps max
# zoom razor sharp, then two broad tiers cover the rest
# (ranges: 0.5-3.2 / 3.2-10 / 10-40)
DETAIL_TIER_ALTS = (3.2, 10.0)
DETAIL_TEX_SIZE = 2048        # per-TILE render resolution

# Movement
UNIT_SPEED_FACTOR = 0.10      # global pace: down another 60%
FORMATION_SPACING = 0.02      # just enough that counters don't overlap
                              # at full zoom
# path legs carrying THIS mult are RAILROAD running: every unit --
# Enlisted included -- rides at the same TRAIN speed (a transport
# truck's road pace) and burns no stores under way
RAIL_LEG_MULT = 8.25
RAIL_TRAIN_SPEED = 0.564      # 0.141 lorry x 4.0 road mult
UNIT_SPRITE_SCALE = 0.045     # fixed world-size of unit pictograms
                              # (tiny; vanishing when zoomed out is fine)
ROAD_SPEED_MULTIPLIER = 4.0   # ROUTING preference for roads; actual
                              # column speed uses each unit's road_mult
BRIDGE_TOLERANCE_DEG = 0.45   # river crossing allowed this close to a bridge

# Vision & Communication
VISION_SCALE = 0.1            # fog-of-war ranges are 1/10 of the base stat
AIR_VISION_MULT = 3.0         # aircraft see 3x further than land/sea
NIGHT_VISION_FACTOR = 0.5     # night halves it again
CITY_VISION_RANGE = 0.2       # garrison observers around friendly cities
COMM_RADIUS_FACTOR = 2.5      # comm radius = 2.5x the raw vision stat
CITY_COMM_RADIUS = 1.25       # friendly cities carry the land-line network
SUPPLY_TRANSFER_RANGE = 0.3   # trucks/ships hand over within this floor
# outside friendly vision the map is darker and drained of colour
FOG_BRIGHTNESS = 0.8          # 20% darker
FOG_SATURATION = 0.5          # 50% less saturated
TERRAIN_LOS = False           # relief-warped vision fields (heavy);
                              # False = clean circles, flag kept for later
GAME_VERSION = '1.3.3'        # shown on the menu as ALPHA <version>

# ------------------------------------------------ strategic resources
# Exactly three, and each governs a different half of the war:
# OIL is OPERATIONS (drawn at the pumps when the supply net feeds a
# machine), STEEL is PRODUCTION (spent building every hull and
# hull-plate), FOOD is MANPOWER (rations for the men a city musters
# and the mouths its flag covers). Per-unit supply burn is untouched.
RESOURCES = ('oil', 'steel', 'food')
RESOURCE_CAP = 999            # national stockpile ceiling per resource
# sized so the OPENING slate builds clean (~530 tons of steel);
# a money-limited fortnight thereafter bills roughly one
# fortnight's deposit income -- materials pinch, never strangle
STARTING_RESOURCES = {'oil': 400, 'steel': 800, 'food': 260}
# THERE ARE NO FREE IMPORTS. Deposits are the WORLD'S ONLY taps of
# oil and steel: a nation without a deposit buys at the treaty
# table or goes without. Food is grown by the towns (below).
OIL_PER_LB = 1.0 / 1250.0     # tons of oil per lb of stores pumped
                              # into MACHINES (men and rail burn none)
OIL_PER_SORTIE = 0.6          # aviation spirit per takeoff

# FOOD is the manpower resource. Machines never eat: rations are
# drawn when a city musters its Enlisted, and every population the
# flag covers must be fed each day -- so conquest brings mouths as
# well as factories, and a blockaded island starves.
FOOD_PER_ENLISTED = 4         # tons to raise and feed one section
CIVIL_RATION = 0.55           # tons per MILLION souls per day
OCCUPIED_RATION = 1.6         # a hostile population eats dearer

# THE CIVILIAN DRAFT, immediate: the rolls (one per 400,000 souls
# a fortnight, banked to three) muster free; every section beyond
# them is CONSCRIPTION and mines the town's industry down to 0%.
DRAFT_INDUSTRY_GRIND = 0.8    # industry %-points per CONSCRIPTED
                              # section (beyond the rolls), immediate

# THE MUNICIPAL LEDGER: every city keeps three PERMANENT tracks --
# AGRICULTURE, THE WORKS, THE LABORATORIES -- of five levels each.
# One fortnight focus buys one level, MONEY ONLY, and the returns
# are EXPONENTIAL: the deep town always beats two shallow ones, so
# empires specialize their cities instead of spreading evenly.
TRACK_MAX_LEVEL = 5
TRACK_COSTS = (300, 450, 675, 1000, 1500)   # $ to reach L1..L5
# food a city grows, tons per fortnight, by agriculture level
# (cumulative: the table IS the output, not an increment)
CITY_FOOD_BASE = 10           # every town farms this unaided
AGRI_FOOD_CUM = (0, 4, 12, 28, 60, 124)
# production speed at THIS town's bases, by works level
WORKS_SPEED_MULT = (1.0, 1.15, 1.32, 1.52, 1.75, 2.0)
# the research focus's yield multiplier, by laboratories level
LAB_YIELD_MULT = (1.0, 1.3, 1.7, 2.2, 2.9, 3.7)
# THE BREADBASKETS: the historic farm belts open the war with
# agriculture already levelled -- the black earth is a head start,
# not a magic dot on the map (these replace the old food deposits)
BREADBASKETS = {
    'Kiev': 3, 'Voronezh': 2, 'Odessa': 2, 'Rostov': 2,
    'St. Louis': 3, 'Kansas City': 3, 'Omaha': 2, 'Minneapolis': 2,
    'Paris': 1, 'Lyon': 1, 'Bordeaux': 1, 'Bologna': 1,
    'Budapest': 1, 'Bucharest': 1, 'Konigsberg': 1, 'Munich': 1,
    'Delhi': 2, 'Calcutta': 2, 'Bangkok': 2, 'Mandalay': 2,
    'Saigon': 2, 'Nanking': 2, 'Wuhan': 1, 'Sydney': 2,
    'Nagoya': 1, 'Surabaya': 1,
}

# THE FORTNIGHT FOCUS: every city works at ONE directive a
# fortnight -- heal the industry, buy a track level, run the
# laboratories, or raise a base.
FOCUS_FINANCE_HEAL = 5.0      # industry points healed (revenue rises)
FOCUS_RESEARCH_RP_PER_M = 4.0 # research points per million souls
FOCUS_RESEARCH_RP_MIN = 2.0   # (multiplied by the town's LAB level)
BASE_COSTS = {'army': (400, 10),   # ($, steel) -- one fortnight
              'air': (500, 12),
              'naval': (600, 16)}

# the open market: base $/ton for treaty trade, discounted between
# allies the same way volunteers are
TRADE_PRICES = {'oil': 8, 'steel': 6, 'food': 7}
TRADE_STEPS = (20, 40)        # tonnages a treaty line may carry

# Deposits sit beside their historical cities; own the city, work
# the deposit. Output is tons per fortnight into the owner's
# stockpile (playable powers only -- NPC nations run no economy;
# their deposits matter when captured, courted or embargoed).
DEPOSITS = {
    # ---- OIL
    'Ploiesti': ('oil', 90), 'Baghdad': ('oil', 60),
    'Tehran': ('oil', 60), 'Houston': ('oil', 120),
    'Oklahoma City': ('oil', 60), 'Palembang': ('oil', 80),
    'Novorossiysk': ('oil', 100), 'Kuybyshev': ('oil', 40),
    'Rangoon': ('oil', 30),
    # ---- STEEL
    'Essen': ('steel', 110), 'Birmingham': ('steel', 80),
    'Glasgow': ('steel', 40), 'Pittsburgh': ('steel', 120),
    'Chicago': ('steel', 60), 'Stalingrad': ('steel', 60),
    'Kharkov': ('steel', 60), 'Gorky': ('steel', 40),
    'Osaka': ('steel', 60), 'Mukden': ('steel', 60),
    'Liege': ('steel', 40), 'Prague': ('steel', 40),
    'Milan': ('steel', 40),
    # (FOOD has no deposits: it is grown by the towns themselves --
    # see BREADBASKETS above for the pre-levelled farm belts)
}
MILES_PER_WU = 132            # one world unit is ~212 km = 132 statute mi
BORDER_WASH_BAND = 0.022      # frontier ribbon width, radians (~140 km)
BORDER_WASH_FLOOR = 0.06      # interior tint floor (near-transparent)
MAX_VISION_SOURCES = 320      # shader uniform budget (a big fleet
                              # must never lose its vision circles)

# Economy — the fortnight budget. Cities pay their taxes once per
# fortnight; the take depends on each city's tax rate and the health of
# its industry (heavy taxation erodes the industrial base).
STARTING_FUNDS = 40000
CITY_GROSS_FORTNIGHT = 2500      # a city's gross product per fortnight
CAPITAL_GROSS_FORTNIGHT = 5500   # the capital's gross product
TAX_DEFAULT = 30              # opening tax rate, percent
TAX_EQUILIBRIUM = 30          # at this rate industry health holds steady
INDUSTRY_DRIFT = 0.5          # industry %-points per tax point per
                              # fortnight (above/below equilibrium)
BUDGET_PERIOD_DAYS = 14       # the fortnight
PRODUCTION_TIME_FACTOR = 4.0  # works orders take this much longer
CAPTURE_INFANTRY_PER_MILLION = 1.0   # garrison cost to annex a city

# Combat / capture
CITY_CAPTURE_RANGE = 0.15     # world units: standing ON the town
CAPTURE_CLEAR_RANGE = 0.07    # no annexation while enemy units
                              # stand THIS close to the town -- an
                              # INFANTRY SECTION'S EYES (vision 0.7
                              # x VISION_SCALE): if the garrison
                              # standing on the town cannot see him,
                              # he does not contest it
CITY_CAPTURE_TIME = 8.0       # seconds
BRIDGE_HP = 120
BRIDGE_REPAIR_RATE = 12       # hp/sec by engineers

# AI
AI_THINK_INTERVAL = 6.0
AI_WAVE_INTERVAL = 90.0
AI_STARTING_FUNDS = 40000

# Marker lifts above the sphere (kept tiny: tall lifts parallax badly
# against the map when the camera pans at full zoom)
LIFT_PATCH = 1.0006           # detail overlay
LIFT_GROUND = 1.0012          # land/sea markers, cities, bridges, roads
LIFT_AIR = 1.0018             # aircraft markers
LIFT_RING = 1.0015            # comm rings and other surface rings
LIFT_FX = 1.0021              # hit flashes, tracers
LIFT_PATH = 1.0025            # movement path lines

# Country colors (RGB 0-1)
COUNTRY_COLORS = {
    'britain': (0.22, 0.35, 0.62),   # royal navy blue
    'germany': (0.35, 0.37, 0.40),   # feldgrau
    'usa':     (0.30, 0.45, 0.28),   # olive drab
    'japan':   (0.85, 0.62, 0.20),   # rising-sun gold
    'soviet':  (0.80, 0.13, 0.10),   # revolutionary scarlet
}

COUNTRIES = {
    'britain': {'color': COUNTRY_COLORS['britain'], 'name': 'British Empire',
                'adjective': 'British'},
    'germany': {'color': COUNTRY_COLORS['germany'], 'name': 'German Reich',
                'adjective': 'German'},
    'usa':     {'color': COUNTRY_COLORS['usa'], 'name': 'United States',
                'adjective': 'American'},
    'japan':   {'color': COUNTRY_COLORS['japan'], 'name': 'Empire of Japan',
                'adjective': 'Japanese'},
    'soviet':  {'color': COUNTRY_COLORS['soviet'], 'name': 'Soviet Union',
                'adjective': 'Soviet'},
}
PLAYABLE = ('britain', 'germany', 'usa', 'japan', 'soviet')

# The NPC nations of 1939: every town outside the five empires belongs
# to one of these, by historic ownership. They field a standing
# home-defense garrison and answer diplomatic fax traffic, but run no
# economy and never expand -- their leverage is the alliance table.
NPC_NATIONS = {
    'france':      {'color': (0.28, 0.42, 0.75), 'name': 'French Republic',
                    'adjective': 'French'},
    'italy':       {'color': (0.45, 0.62, 0.42), 'name': 'Kingdom of Italy',
                    'adjective': 'Italian'},
    'china':       {'color': (0.55, 0.42, 0.65), 'name': 'Republic of China',
                    'adjective': 'Chinese'},
    'poland':      {'color': (0.78, 0.42, 0.48), 'name': 'Republic of Poland',
                    'adjective': 'Polish'},
    'netherlands': {'color': (0.85, 0.50, 0.20), 'name': 'The Netherlands',
                    'adjective': 'Dutch'},
    'belgium':     {'color': (0.62, 0.55, 0.25), 'name': 'Kingdom of Belgium',
                    'adjective': 'Belgian'},
    'norway':      {'color': (0.35, 0.55, 0.68), 'name': 'Kingdom of Norway',
                    'adjective': 'Norwegian'},
    'denmark':     {'color': (0.72, 0.35, 0.35), 'name': 'Kingdom of Denmark',
                    'adjective': 'Danish'},
    'finland':     {'color': (0.55, 0.65, 0.75), 'name': 'Republic of Finland',
                    'adjective': 'Finnish'},
    'greece':      {'color': (0.40, 0.58, 0.62), 'name': 'Kingdom of Greece',
                    'adjective': 'Greek'},
    'yugoslavia':  {'color': (0.48, 0.48, 0.62), 'name': 'Kingdom of Yugoslavia',
                    'adjective': 'Yugoslav'},
    'romania':     {'color': (0.68, 0.58, 0.35), 'name': 'Kingdom of Romania',
                    'adjective': 'Romanian'},
    'hungary':     {'color': (0.58, 0.45, 0.40), 'name': 'Kingdom of Hungary',
                    'adjective': 'Hungarian'},
    'bulgaria':    {'color': (0.45, 0.55, 0.45), 'name': 'Kingdom of Bulgaria',
                    'adjective': 'Bulgarian'},
    'iraq':        {'color': (0.62, 0.52, 0.42), 'name': 'Kingdom of Iraq',
                    'adjective': 'Iraqi'},
    'iran':        {'color': (0.52, 0.58, 0.38), 'name': 'Imperial Iran',
                    'adjective': 'Iranian'},
    'siam':        {'color': (0.65, 0.45, 0.55), 'name': 'Kingdom of Siam',
                    'adjective': 'Siamese'},
    # dominions and colonial commands of the playable empires stand as
    # their own nations, so the majors begin with their HOME cities
    # only and the wider empires enter the war by diplomacy. They wear
    # PLAIN names on every ledger and paper -- "Egypt", not "British
    # Mediterranean" -- so players read them as countries, not
    # command abbreviations (internal keys unchanged for saves).
    'brit_med':    {'color': (0.35, 0.48, 0.70), 'name': 'Egypt',
                    'adjective': 'Egyptian'},
    'raj':         {'color': (0.30, 0.52, 0.58), 'name': 'India',
                    'adjective': 'Indian'},
    'fareast':     {'color': (0.42, 0.55, 0.52), 'name': 'Malaya',
                    'adjective': 'Malayan'},
    'australia':   {'color': (0.38, 0.58, 0.45), 'name': 'Australia',
                    'adjective': 'Australian'},
}
COUNTRIES.update(NPC_NATIONS)
# short names for tight layouts (ledger cards, wire traffic):
# no 'Kingdom of', no 'Republic of' -- just the country
SHORT_NAMES = {
    'britain': 'Britain',
    'germany': 'Germany',
    'usa': 'United States',
    'japan': 'Japan',
    'soviet': 'Soviet Union',
    'france': 'France',
    'italy': 'Italy',
    'china': 'China',
    'poland': 'Poland',
    'netherlands': 'Netherlands',
    'belgium': 'Belgium',
    'norway': 'Norway',
    'denmark': 'Denmark',
    'finland': 'Finland',
    'greece': 'Greece',
    'yugoslavia': 'Yugoslavia',
    'romania': 'Romania',
    'hungary': 'Hungary',
    'bulgaria': 'Bulgaria',
    'iraq': 'Iraq',
    'iran': 'Iran',
    'siam': 'Siam',
    'brit_med': 'Egypt',
    'raj': 'India',
    'fareast': 'Malaya',
    'australia': 'Australia',
    'neutral': 'Neutral',
}


def short_name(key):
    return SHORT_NAMES.get(
        key, COUNTRIES.get(key, {}).get('name', key))


# not a nation: the fallback class for unowned ground
COUNTRIES['neutral'] = {'color': (0.58, 0.56, 0.50), 'name': 'Neutral',
                        'adjective': 'Neutral'}

# File Paths
MEDIA_PATH = "media/"
MENU_VIDEO_PATH = "media/menu_background.mp4"

# Campaign clock: game starts at dawn, 1 Sep 1939. Minutes pass per second.
CAMPAIGN_START = (1939, 9, 1, 5, 0)
MINUTES_PER_SECOND = 12.0
