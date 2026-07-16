"""
Game Configuration and Constants
"""

# Display Settings
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FULLSCREEN = False
WINDOW_TITLE = "Schattenfront"
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
UNIT_SPRITE_SCALE = 0.045     # fixed world-size of unit pictograms
                              # (tiny; vanishing when zoomed out is fine)
ROAD_SPEED_MULTIPLIER = 10.0  # land units move 10x faster on roads
BRIDGE_TOLERANCE_DEG = 0.45   # river crossing allowed this close to a bridge

# Vision & Communication
VISION_SCALE = 0.1            # fog-of-war ranges are 1/10 of the base stat
AIR_VISION_MULT = 3.0         # aircraft see 3x further than land/sea
NIGHT_VISION_FACTOR = 0.5     # night halves it again
CITY_VISION_RANGE = 0.2       # garrison observers around friendly cities
COMM_RADIUS_FACTOR = 5.0      # comm radius = 5x the raw vision stat
CITY_COMM_RADIUS = 1.25       # friendly cities carry the land-line network
SUPPLY_TRANSFER_RANGE = 0.3   # trucks/ships hand over within this floor
# outside friendly vision the map is darker and drained of colour
FOG_BRIGHTNESS = 0.8          # 20% darker
FOG_SATURATION = 0.5          # 50% less saturated
MAX_VISION_SOURCES = 96       # shader uniform budget

# Economy — the fortnight budget
STARTING_FUNDS = 40000
CITY_INCOME_PER_SEC = 30      # per city
CAPITAL_INCOME_PER_SEC = 70
BUDGET_PERIOD_DAYS = 14       # a transmitted budget is locked this long
PRODUCTION_TIME_FACTOR = 4.0  # works orders take this much longer

# Combat / capture
CITY_CAPTURE_RANGE = 0.5      # world units
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
    'britain': (0.75, 0.28, 0.24),   # imperial red
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

# File Paths
MEDIA_PATH = "media/"
MENU_VIDEO_PATH = "media/menu_background.mp4"

# Campaign clock: game starts at dawn, 1 Sep 1939. Minutes pass per second.
CAMPAIGN_START = (1939, 9, 1, 5, 0)
MINUTES_PER_SECOND = 12.0
