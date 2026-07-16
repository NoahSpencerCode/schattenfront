"""
Schattenfront — game application.

State machine: main menu -> nation selection -> campaign on the globe.
Controls follow Supreme Commander conventions: left-click / drag-box to
select, right-click for context orders (move / attack / board / repair),
shift to queue waypoints, ctrl+number for control groups.

Everything on the map is drawn flat on the planet surface — unit
counters, city rings, bridges, hit flashes — like symbols inked onto a
1940s situation map.  Units outside a friendly communication circle go
OUT OF CONTACT: invisible and beyond command until the net reaches them.
"""

import math
import random
import threading
import zlib

from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (AmbientLight, CardMaker, DirectionalLight,
                          KeyboardButton, LineSegs, Point2, Point3,
                          SamplerState, TextNode, TextProperties,
                          TextPropertiesManager, TransparencyAttrib,
                          Vec3, Vec4)

from config import (AI_STARTING_FUNDS, AI_THINK_INTERVAL, AI_WAVE_INTERVAL,
                    AIR_VISION_MULT, VISION_SCALE,
                    BRIDGE_HP, BRIDGE_REPAIR_RATE, BUDGET_PERIOD_DAYS,
                    CAM_MAX_DIST, CAM_MIN_DIST, CAM_START_DIST,
                    CAM_ZOOM_CITY_LABELS, CAM_ZOOM_LABELS, CAMPAIGN_START,
                    CAPITAL_GROSS_FORTNIGHT, CAPTURE_INFANTRY_PER_MILLION,
                    CITY_CAPTURE_RANGE, CITY_COMM_RADIUS,
                    CITY_GROSS_FORTNIGHT, CITY_VISION_RANGE, COUNTRIES,
                    DAY_CYCLE_LENGTH, FORMATION_SPACING, GLOBE_RADIUS,
                    INDUSTRY_DRIFT, LIFT_FX, LIFT_GROUND, LIFT_PATH,
                    MINUTES_PER_SECOND,
                    NIGHT_VISION_FACTOR, PRODUCTION_TIME_FACTOR,
                    STARTING_FUNDS, SUPPLY_TRANSFER_RANGE, TAX_DEFAULT,
                    TAX_EQUILIBRIUM, UNIT_SPRITE_SCALE)
from geodata import (WorldData, HARBOR_CITIES, CITY_POPULATION,
                     CAPITALS)
from globe import (Globe, NAT_ORDER, make_surface_ring,
                   orient_to_surface)
from menu import MenuScreen
from icons import get_icon_path
from models import (make_bridge_marker, make_flat_ring,
                    make_hit_flash_template, set_marker_layer,
                    LAYER_BRIDGE, LAYER_FLASH, LAYER_HOVER, LAYER_STRUCT)
from pathfinding import MovementPlanner
from structures import (Airfield, Bunker, Depot, Harbor,
                        AIRFIELD_STOCK_CAP,
                        BUNKER_RADIUS, DEPOT_STOCK_CAP, SORTIE_COST)
from ui import (TopBar, BottomBar, FaxPanel, BudgetFax, BriefingFax,
                ProductionFax, TaxFax, B)
from units import (Unit, UNIT_TYPES, BRANCH_OF, FIRE_SUPPLY_FACTOR,
                   NATION_UNIT_STATS, stats_for)
from utils import (angle_between, find_regular_font_path,
                   find_typewriter_font_path, latlon_dist_deg,
                   latlon_to_vec, north_tangent, vec_to_latlon)

MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
          'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

CLICK_RADIUS = 0.04          # screen-space pick tolerance
DRAG_THRESHOLD = 0.015
HIT_FLASH_TIME = 0.35        # seconds for a combat flash to expand and die
MAX_HIT_FLASHES = 48

STARTING_ARMY = ['army_command', 'infantry', 'infantry', 'tank', 'engineer',
                 'aa_artillery', 'supply_truck']
STARTING_AIR = ['fighter', 'bomber']
STARTING_NAVY = ['destroyer_sea_sea', 'personnel_transport']

CONTROLS_HINT = ("LMB SELECT/DRAG/DBL-CLICK TYPE   RMB ORDER   "
                 "SHIFT QUEUE WAYPOINTS   H HALT   B BUDGET   "
                 "CTRL+1-9 GROUP   WASD/MMB CAM   WHEEL ZOOM   "
                 "SPACE PAUSE")


class City:
    def __init__(self, game, index, name, country, lat, lon):
        self.game = game
        self.index = index
        self.name = name
        self.country = country          # current owner
        self.home_country = country
        self.capital = name in CAPITALS
        self.harbor = name in HARBOR_CITIES
        # WW2-era metropolitan population (persons)
        self.population = int(CITY_POPULATION.get(name, 120) * 1000)
        # the war economy: taxes are levied each fortnight; the rate can
        # be decreed at any time but binds from the NEXT fortnight, and
        # heavy taxation grinds the industrial base down
        self.tax_rate = TAX_DEFAULT
        self.pending_tax = None
        self.industry = 100.0           # industrial health, percent
        self.annexing = False           # captured, not yet taxable
        self.lat, self.lon = lat, lon
        self.pos = latlon_to_vec(lat, lon)
        self.capture_progress = 0.0
        self.capturing_country = None
        self.production = []            # [unit_type, seconds_left]
        self.alive = True

        self.root = game.render.attachNewNode('city_%s' % name)
        orient_to_surface(self.root, self.pos)
        self.holder = self.root.attachNewNode('holder')
        self.holder.setPos(0, 0, GLOBE_RADIUS * LIFT_GROUND)
        self.sel_ring = make_flat_ring('city_sel', 1.9,
                                       (1.0, 0.9, 0.3, 0.95),
                                       thickness=2.0, segments=32)
        self.sel_ring.reparentTo(self.holder)
        set_marker_layer(self.sel_ring, LAYER_STRUCT + 5)
        self.sel_ring.hide()

        # etched name label, shown only when the camera is close
        tn = TextNode('cityname_%s' % name)
        tn.setText(name.upper())
        tn.setAlign(TextNode.ACenter)
        if game.map_font:
            tn.setFont(game.map_font)
        self.label_tn = tn
        # the name sits directly over the town, half transparent, flat
        # on the map (never billboarded) at a fixed map size
        self.label_pos = latlon_to_vec(lat, lon)
        self.label = game.render.attachNewNode(tn)
        self.label.setPos(self.label_pos * (GLOBE_RADIUS * LIFT_GROUND))
        self.label.lookAt(Point3(0, 0, 0), Vec3(0, 0, 1))
        self.label.setScale(0.05)       # fixed map size at every zoom
        self.label.setLightOff()
        self.label.setTransparency(TransparencyAttrib.MAlpha)
        set_marker_layer(self.label, LAYER_STRUCT + 4)
        self.refresh_marker()

    def refresh_marker(self):
        # the city itself is sketched onto the map texture; ownership
        # shows in the colour of its name
        c = COUNTRIES[self.country]['color']
        self.label_tn.setTextColor(min(1.0, c[0] * 1.5 + 0.25),
                                   min(1.0, c[1] * 1.5 + 0.25),
                                   min(1.0, c[2] * 1.5 + 0.25), 0.5)
        self.label_tn.setShadow(0.05, 0.05)
        self.label_tn.setShadowColor(0.08, 0.07, 0.05, 0.5)

    def set_marker_scale(self, scale):
        self.holder.setScale(scale)

    def gross_product(self):
        base = (CAPITAL_GROSS_FORTNIGHT if self.capital
                else CITY_GROSS_FORTNIGHT)
        return base * self.industry / 100.0

    def fortnight_revenue(self, rate=None):
        """What the city pays into the treasury at the fortnight."""
        if self.annexing:
            return 0
        r = self.tax_rate if rate is None else rate
        return int(self.gross_product() * r / 100.0)

    def industry_drift(self, rate=None):
        """Industry %-points gained/lost per fortnight at a tax rate."""
        r = self.tax_rate if rate is None else rate
        return (TAX_EQUILIBRIUM - r) * INDUSTRY_DRIFT

    def required_infantry(self):
        """Garrison needed to annex: one division per million souls."""
        return max(1, int(math.ceil(
            self.population / 1e6 * CAPTURE_INFANTRY_PER_MILLION)))

    def cleanup(self):
        self.root.removeNode()
        self.label.removeNode()


class Bridge:
    def __init__(self, game, info, index):
        self.game = game
        self.index = index
        self.lat, self.lon = info['lat'], info['lon']
        self.road = info['road']
        self.pos = latlon_to_vec(self.lat, self.lon)
        self.hp = BRIDGE_HP
        self.max_hp = BRIDGE_HP
        self.alive = True
        self.country = None             # bridges are neutral
        self.root = game.render.attachNewNode('bridge_%d' % index)
        orient_to_surface(self.root, self.pos)
        holder = self.root.attachNewNode('holder')
        holder.setPos(0, 0, GLOBE_RADIUS * LIFT_GROUND)
        # lay the span along its road so it crosses the river the way
        # the traffic does (engineer-built spans have no road link)
        seg = info.get('seg')
        i, j = self.road
        if seg is not None:
            # tangent of the actual (snaking) road segment at the crossing
            va = latlon_to_vec(seg[0], seg[1])
            vb = latlon_to_vec(seg[2], seg[3])
        elif i < 0 or j < 0:
            self.marker = make_bridge_marker(game.loader)
            self.marker.reparentTo(holder)
            return
        else:
            ca, cb = game.world.cities[i], game.world.cities[j]
            va = latlon_to_vec(ca[2], ca[3])
            vb = latlon_to_vec(cb[2], cb[3])
        d = vb - va
        n = Vec3(self.pos)
        tang = d - n * d.dot(n)
        if tang.lengthSquared() > 1e-9:
            tang.normalize()
            north = north_tangent(n)
            east = north.cross(n)
            heading = math.degrees(math.atan2(tang.dot(east),
                                              tang.dot(north)))
            holder.setH(-heading)
        self.marker = make_bridge_marker(game.loader)
        self.marker.reparentTo(holder)

    def take_damage(self, amount, attacker=None):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.marker.setColorScale(0.35, 0.28, 0.25, 0.9)
            self.game.on_bridge_destroyed(self, attacker)

    def repair(self, amount):
        was_dead = not self.alive
        self.hp = min(self.max_hp, self.hp + amount)
        if self.hp >= self.max_hp * 0.5 and not self.alive:
            self.alive = True
        if self.alive and was_dead:
            self.marker.clearColorScale()
            self.game.on_bridge_repaired(self)


class WW2RTSGame(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()
        self.setBackgroundColor(0.04, 0.05, 0.08)
        self.camLens.setNearFar(0.05, 500.0)

        # open fully expanded; the OS pointer stays visible by default --
        # the software cursor sprite only appears for the special modes
        # (attack / embark / disembark)
        if self.win is not None:
            try:
                from panda3d.core import WindowProperties
                wp = WindowProperties()
                if hasattr(wp, 'setMaximized'):
                    wp.setMaximized(True)
                self.win.requestProperties(wp)
            except Exception:
                pass

        font_path = find_typewriter_font_path()
        self.hud_font = None
        self.map_font = None
        self.body_font = None
        if font_path:
            try:
                self.hud_font = self.loader.loadFont(font_path)
                self.hud_font.setPixelsPerUnit(120)   # crisp FAX print
                self.hud_font.setPageSize(1024, 1024)
                self.map_font = self.hud_font
            except Exception:
                pass
        reg_path = find_regular_font_path()
        if reg_path:
            try:
                self.body_font = self.loader.loadFont(reg_path)
                self.body_font.setPixelsPerUnit(120)
                self.body_font.setPageSize(1024, 1024)
            except Exception:
                pass
        if self.hud_font:
            # ui.B() switches spans to the bold face inside signal text
            # (registered in both cases: signal bodies get uppercased)
            tp = TextProperties()
            tp.setFont(self.hud_font)
            tp.setTextColor(0.52, 0.10, 0.06, 1.0)   # dispatch-red stamp
            mgr = TextPropertiesManager.getGlobalPtr()
            mgr.setProperties('b', tp)
            mgr.setProperties('B', tp)

        self.game_state = 'menu'
        self.menu = None
        self.world = None
        self.globe = None
        self.planner = None

        # campaign state
        self.player_country = None
        self.units = []
        self.cities = []
        self.bridges = []
        self.airfields = []
        self.harbors = []
        self.depots = []
        self.bunkers = []
        self.custom_roads = []          # engineer-built road nodepaths
        self.build_mode = None          # engineer works: kind awaiting site
        self.road_plan = []             # surveyed road waypoints
        self.road_preview = None        # yellow survey line
        self.selected = []
        self.selected_city = None
        self.selected_airfield = None
        self.selected_harbor = None
        self.roster_base = None          # airfield/carrier whose menu is up
        self.groups = {}
        self.funds = {}
        self.game_speed = 1.0
        self.is_paused = False
        self.clock_minutes = 0.0
        self.sun_angle = 0.0
        self.eliminated = set()
        self.game_over = False
        self.kills = 0
        self.losses = 0
        self.out_of_contact = 0
        self.budget_lock_until = None
        self.budget_counts = {}         # the standing fortnight budget
        self.fortnight_start = 0.0
        self.fortnight_order = {}       # this fortnight's ordered counts
        self.fortnight_delivered = {}   # ... and what has been delivered
        self.budget_fax = None
        self.briefing_fax = None
        self.tax_fax = None

        # input state
        self.drag_start = None
        self.drag_box = None
        self.mmb_down = False
        self.last_mouse = None
        kb = KeyboardButton
        self._key_up = (kb.asciiKey('w'), kb.up())
        self._key_down = (kb.asciiKey('s'), kb.down())
        self._key_left = (kb.asciiKey('a'), kb.left())
        self._key_right = (kb.asciiKey('d'), kb.right())
        self._key_shift = kb.shift()

        # camera orbit (targets are chased smoothly each frame)
        self.cam_lat = 45.0
        self.cam_lon = 0.0
        self.cam_lat_target = 45.0
        self.cam_lon_target = 0.0
        self.cam_dist = CAM_START_DIST
        self.cam_dist_target = CAM_START_DIST

        # UI / effects
        self.top_bar = None
        self.bottom_bar = None
        self.fax = None
        self.pause_frame = None
        self.tracers = []               # [nodepath, ttl]
        self.flashes = []               # [root, holder, age]
        self.flash_total = 0            # lifetime spawn count (debug/tests)
        self.hit_template = make_hit_flash_template()
        self.marker_scale = 1.0
        self._scale_ref_dist = 0.0
        self._hover_timer = 0.0
        self.cursor = None
        self.cursor_tex = {}
        self.cursor_mode = 'default'
        self._build_cursor()
        self.hover_glow = None          # built lazily (needs no loader)
        self._vision_units = []
        self._vision_cities = []
        self._last_click = (0.0, None)  # double-click bookkeeping
        self.unload_mode = False        # armed: next RMB sites the drop
        self._vision_timer = 0.0
        self._capture_timer = 0.0
        self._supply_timer = 0.0
        self._chase_timer = 0.0
        # background route planning: long plans never freeze a frame
        import queue as _queue
        self._plan_jobs = _queue.Queue()
        self._plan_results = []
        self._plan_seq = 0
        self._pending_plans = 0
        self._preplans = {}         # token -> queued order awaiting route
        self._ind_tokens = set()    # plans the player is waiting on
        self._plan_worker = threading.Thread(target=self._plan_loop,
                                             daemon=True)
        self._plan_worker.start()
        self.planning_text = None
        self._city_ui_timer = 0.0
        self._top_bar_timer = 0.0
        self._ai_timers = {}
        self._ai_overseas_cache = {}
        self._pending_ai_orders = []
        self._path_viz = None
        self._path_viz_timer = 0.0

        self._setup_lighting()
        self.show_menu()
        self.taskMgr.add(self.update, 'update')

    # ================================================== lighting & clock
    def _setup_lighting(self):
        amb = AmbientLight('ambient')
        amb.setColor(Vec4(0.55, 0.55, 0.52, 1))
        self.render.setLight(self.render.attachNewNode(amb))
        self.sun_light = DirectionalLight('sun')
        self.sun_light.setColor(Vec4(0.9, 0.87, 0.8, 1))
        self.sun_np = self.render.attachNewNode(self.sun_light)
        self.render.setLight(self.sun_np)

    def sun_direction(self):
        a = self.sun_angle
        return Vec3(math.cos(a), math.sin(a), 0.25).normalized()

    def is_day(self, pos):
        """Daylight at a surface point (matches the shader terminator)."""
        return pos.dot(self.sun_direction()) > 0.03

    def campaign_clock_text(self):
        y, mo, d, h, mi = CAMPAIGN_START
        total = mi + h * 60 + (d - 1) * 1440 + self.clock_minutes
        days, rem = divmod(int(total), 1440)
        hh, mm = divmod(rem, 60)
        month = mo - 1 + days // 30
        day = days % 30 + 1
        year = y + month // 12
        month %= 12
        return "%02d%02d HRS  %d %s %d" % (hh, mm, day, MONTHS[month], year)

    # ========================================================== states
    def show_menu(self):
        self.game_state = 'menu'
        self._teardown_campaign()
        if self.menu:
            self.menu.destroy()
        self.menu = MenuScreen(self, self.start_game)

    def _teardown_campaign(self):
        for u in self.units:
            u.cleanup()
        self.units = []
        for c in self.cities:
            c.cleanup()
        self.cities = []
        for group in (self.airfields, self.harbors, self.depots,
                      self.bunkers):
            for s in group:
                s.cleanup()
        self.airfields = []
        self.harbors = []
        self.depots = []
        self.bunkers = []
        for np_ in self.custom_roads:
            np_.removeNode()
        self.custom_roads = []
        self.build_mode = None
        self._clear_road_plan()
        self.selected_airfield = None
        self.roster_base = None
        for b in self.bridges:
            b.root.removeNode()
        self.bridges = []
        for np_, _ in self.tracers:
            np_.removeNode()
        self.tracers = []
        for entry in self.flashes:
            entry[0].removeNode()
        self.flashes = []
        if self._path_viz:
            self._path_viz.removeNode()
            self._path_viz = None
        for bar in (self.top_bar, self.bottom_bar, self.fax,
                    self.budget_fax, self.briefing_fax, self.tax_fax):
            if bar:
                bar.destroy()
        self.top_bar = self.bottom_bar = self.fax = None
        self.budget_fax = None
        self.briefing_fax = None
        self.tax_fax = None
        self.budget_lock_until = None
        self.budget_counts = {}
        self.fortnight_start = 0.0
        self.fortnight_order = {}
        self.fortnight_delivered = {}
        if self.pause_frame:
            self.pause_frame.destroy()
            self.pause_frame = None
        if self.planning_text:
            self.planning_text.removeNode()
            self.planning_text = None
        if self.globe:
            self.globe.destroy()
            self.globe = None
        self.selected = []
        self.selected_city = None
        self.groups = {}
        self.eliminated = set()
        self.game_over = False
        self.is_paused = False
        self.kills = self.losses = 0
        self.out_of_contact = 0
        self.clock_minutes = 0.0
        self._ai_overseas_cache = {}
        self._pending_ai_orders = []
        self.unload_mode = False
        self._vision_units = []
        self._vision_cities = []
        self._last_click = (0.0, None)
        self._preplans = {}
        self._ind_tokens = set()
        if self.hover_glow:
            self.hover_glow.hide()
            self.hover_glow.detachNode()
        self._set_cursor_mode('default')

    def _loading_screen(self):
        """Full-screen mobilization card shown while the world builds.
        Returns (root_node, set_status) -- set_status(text) updates the
        progress line and forces a frame so the player sees it."""
        from direct.gui.DirectGui import DirectFrame
        root = self.aspect2d.attachNewNode('loading_screen')
        card = DirectFrame(parent=root, frameColor=(0.05, 0.06, 0.08, 1.0),
                           frameSize=(-3.6, 3.6, -1.2, 1.2))
        card.setBin('gui-popup', 90)

        def text(t, z, scale, color):
            tn = TextNode('loading')
            tn.setText(t)
            tn.setAlign(TextNode.ACenter)
            if self.hud_font:
                tn.setFont(self.hud_font)
            tn.setTextColor(*color)
            np_ = root.attachNewNode(tn)
            np_.setScale(scale)
            np_.setPos(0, 0, z)
            np_.setBin('gui-popup', 91)
            return tn

        text("SCHATTENFRONT", 0.30, 0.14, (0.92, 0.87, 0.70, 1.0))
        text("++ MOBILIZATION IN PROGRESS ++", 0.14, 0.05,
             (0.70, 0.66, 0.55, 1.0))
        status_tn = text("DRAWING UP MAPS...", -0.10, 0.045,
                         (0.62, 0.58, 0.48, 1.0))
        text("THE GENERAL STAFF THANKS YOU FOR YOUR PATIENCE",
             -0.85, 0.032, (0.45, 0.42, 0.35, 1.0))

        def set_status(t):
            status_tn.setText(str(t).upper())
            for _ in range(2):
                self.graphicsEngine.renderFrame()

        set_status("DRAWING UP MAPS...")
        return root, set_status

    def start_game(self, country):
        loading, progress = self._loading_screen()
        if self.world is None:
            self.world = WorldData(log=progress)
        if self.menu:
            self.menu.destroy()
            self.menu = None
        self.game_state = 'playing'
        self.player_country = country

        progress("PAINTING THE OPERATIONS GLOBE...")
        self.globe = Globe(self, self.world)
        self.bridges = [Bridge(self, info, i)
                        for i, info in enumerate(self.world.bridges)]
        self.planner = MovementPlanner(self.world, self.bridges)
        # build the route graphs now, behind the loading screen, instead
        # of hitching on the first movement order
        progress("PLOTTING ROADS AND SEA LANES...")
        self.planner._build_land_graph()
        self.planner._build_sea_grid()
        progress("RAISING THE ARMIES...")
        self.cities = [City(self, i, n, c, la, lo)
                       for i, (n, c, la, lo) in enumerate(self.world.cities)]
        # an airfield beside every city and a harbor where the sea is
        # near; both sited deterministically by the world data (which
        # also draws their spur roads onto the map)
        self.airfields = []
        self.harbors = []
        for c in self.cities:
            site = self.world.airfield_sites[c.name]
            self.airfields.append(Airfield(self, site[0], site[1],
                                           c.country,
                                           "%s FIELD" % c.name.upper(),
                                           city=c))
            hs = self.world.harbor_sites.get(c.name)
            c.harbor = hs is not None
            if hs is not None:
                self.harbors.append(Harbor(self, hs[0], hs[1], c.country,
                                           "%s HARBOUR" % c.name.upper(),
                                           city=c))
        self.depots = []
        self.bunkers = []
        self._ai_overseas_cache = {}
        self._pending_ai_orders = []

        self.funds = {c: (STARTING_FUNDS if c == country else
                          AI_STARTING_FUNDS) for c in COUNTRIES}
        self._ai_timers = {c: {'think': random.uniform(2, 6),
                               'wave': AI_WAVE_INTERVAL * random.uniform(.6, 1)}
                           for c in COUNTRIES
                           if c != country and c != 'neutral'}

        for faction in COUNTRIES:
            if faction != 'neutral':
                self._spawn_starting_forces(faction)

        self._update_borders()
        cap = self.capital_of(country)
        self.cam_lat = self.cam_lat_target = cap.lat
        self.cam_lon = self.cam_lon_target = cap.lon
        self.cam_dist = self.cam_dist_target = 55.0
        self._scale_ref_dist = 0.0      # force a marker-scale pass

        self.top_bar = TopBar(self, self.open_budget,
                              self.open_factory_report)
        self.bottom_bar = BottomBar(self)
        self.bottom_bar.set_title("ALL QUIET")
        self.bottom_bar.set_hint(CONTROLS_HINT)
        self.fax = FaxPanel(self)
        self.fax.post(
            "ASSUMPTION OF COMMAND",
            "You command the %s forces. The first fortnight budget is "
            "already committed. Press %s to amend the next one. "
            "Good hunting." %
            (B(COUNTRIES[country]['adjective']), B("[B]")),
            sender="WAR OFFICE")

        # the first fortnight budget is in effect from the opening gun:
        # the treasury maxed out, split equally across the order of battle
        self.fortnight_start = 0.0
        self.budget_counts = self._default_budget_counts(
            country, self.funds[country])
        self._apply_fortnight_budget()

        loading.removeNode()
        self._bind_game_controls()
        self._tick_vision_comm()        # fog + contact valid on frame one

    def capital_of(self, country):
        for c in self.cities:
            if c.home_country == country and c.capital:
                return c
        return self.cities[0]

    def _spawn_starting_forces(self, faction):
        cities = [c for c in self.cities if c.home_country == faction]
        cap = cities[0]
        for i, ut in enumerate(STARTING_ARMY):
            self.spawn_unit(ut, faction, cap.lat, cap.lon, jitter=0.9, seed=i)
        for i, ut in enumerate(STARTING_AIR):
            self.spawn_unit(ut, faction, cap.lat, cap.lon, jitter=1.2,
                            seed=10 + i)
        second = cities[1]
        for i, ut in enumerate(['infantry', 'tank']):
            self.spawn_unit(ut, faction, second.lat, second.lon, jitter=0.8,
                            seed=20 + i)
        harbor = next((c for c in cities if c.harbor), None)
        if harbor:
            wl, wo = self.world.harbor_sites[harbor.name]
            for i, ut in enumerate(STARTING_NAVY):
                self.spawn_unit(ut, faction, wl, wo, jitter=0.25,
                                seed=30 + i, water=True)

    def spawn_unit(self, unit_type, faction, lat, lon, jitter=0.0, seed=0,
                   water=False, base=None):
        rng = random.Random(hash((faction, unit_type, seed)))
        la = lat + rng.uniform(-jitter, jitter)
        lo = lon + rng.uniform(-jitter, jitter)
        domain = UNIT_TYPES[unit_type]['domain']
        if domain == 'sea' or water:
            la, lo = self.world.nearest_water(la, lo)
        elif domain == 'land':
            la, lo = self.world.nearest_land(la, lo)
        unit = Unit(self, unit_type, faction, latlon_to_vec(la, lo))
        if domain == 'air':
            # aircraft start parked (hidden) at their airfield
            if base is None:
                fields = self.airfields_of(faction)
                base = min(fields, key=lambda f: unit.dist_to(f.pos)) \
                    if fields else None
            unit.based_at = base
            if base is not None:
                unit.pos = Vec3(base.pos)
                unit.update_visual()
                unit.root.hide()
                self._refresh_air_base(base)
        if faction != self.player_country:
            unit.decals.hide()
            if not unit.root.isHidden():
                unit.root.hide()
        self.units.append(unit)
        return unit

    def airfield_of_city(self, city):
        for a in self.airfields:
            if a.city is city:
                return a
        return None

    def _update_borders(self):
        """Refresh the Voronoi border shader after any change of
        ownership (capture or completed annexation)."""
        if not self.globe:
            return
        idx = {k: i for i, k in enumerate(NAT_ORDER)}
        self.globe.set_borders(
            [(c.pos, idx.get(c.country, 5)) for c in self.cities])

    def harbor_of_city(self, city):
        for h in self.harbors:
            if h.city is city:
                return h
        return None

    # ==================================================== input binding
    def _bind_game_controls(self):
        for key in ('n', 'h', 'q', 'b', '1', '2', '3', '4'):
            self.ignore(key)
        self.accept('escape', self.on_escape)
        self.accept('space', self.toggle_pause)
        # note: Panda prefixes button-down events with held modifiers
        # ("shift-mouse3"), so every binding needs its shifted twin or
        # shift-queued orders never arrive
        self.accept('mouse1', self.on_lmb_down)
        self.accept('shift-mouse1', self.on_lmb_down)
        self.accept('mouse1-up', self.on_lmb_up)
        self.accept('mouse3', self.on_rmb)
        self.accept('shift-mouse3', self.on_rmb)
        self.accept('mouse2', self.on_mmb, [True])
        self.accept('shift-mouse2', self.on_mmb, [True])
        self.accept('mouse2-up', self.on_mmb, [False])
        self.accept('wheel_up', self.on_zoom, [-1])
        self.accept('wheel_down', self.on_zoom, [1])
        self.accept('h', self.order_stop)
        self.accept('b', self.open_budget)
        self.accept('=', self.change_speed, [1])
        self.accept('-', self.change_speed, [-1])
        for i in range(1, 10):
            self.accept('control-%d' % i, self.assign_group, [i])
            self.accept('%d' % i, self.recall_group, [i])

    def on_escape(self):
        if self.game_state != 'playing':
            return
        if self.build_mode:
            self.build_mode = None
            self._clear_road_plan()
            self.fax_short("WORKS ORDER CANCELLED")
        elif self.unload_mode:
            self.unload_mode = False
            self.fax_short("DISEMBARKATION CANCELLED")
        elif self.briefing_fax:
            self._close_briefing()
        elif self.tax_fax:
            self._tax_discard()
        elif self.budget_fax:
            self._budget_discard()
        elif self.pause_frame:
            self._close_pause_menu()
        elif (self.selected or self.selected_city or self.selected_airfield
                or self.selected_harbor):
            self.clear_selection()
        else:
            self._open_pause_menu()

    def _open_pause_menu(self):
        self.is_paused = True
        self.pause_frame = DirectFrame(parent=self.aspect2d,
                                       frameColor=(0.05, 0.05, 0.04, 0.88),
                                       frameSize=(-0.6, 0.6, -0.4, 0.4),
                                       state=DGG.NORMAL)
        tn = TextNode('pause')
        tn.setText("FIELD ORDERS")
        tn.setAlign(TextNode.ACenter)
        if self.hud_font:
            tn.setFont(self.hud_font)
        tn.setTextColor(0.9, 0.85, 0.65, 1)
        np_ = self.pause_frame.attachNewNode(tn)
        np_.setScale(0.08)
        np_.setPos(0, 0, 0.25)
        for i, (label, cmd) in enumerate([
                ("RESUME OPERATIONS", self._close_pause_menu),
                ("ABANDON CAMPAIGN", self.show_menu),
                ("QUIT TO BARRACKS", self.userExit)]):
            DirectButton(parent=self.pause_frame, text=label,
                         text_scale=0.05, text_fg=(0.9, 0.85, 0.65, 1),
                         text_font=self.hud_font,
                         frameColor=((0.18, 0.16, 0.12, 0.9),
                                     (0.32, 0.28, 0.18, 1),
                                     (0.1, 0.1, 0.08, 0.9),
                                     (0.3, 0.3, 0.3, 0.4)),
                         frameSize=(-0.5, 0.5, -0.045, 0.07),
                         relief=DGG.FLAT, command=cmd,
                         pos=(0, 0, 0.08 - i * 0.16))

    def _close_pause_menu(self):
        if self.pause_frame:
            self.pause_frame.destroy()
            self.pause_frame = None
        self.is_paused = False

    def toggle_pause(self):
        if self.game_state == 'playing' and not self.pause_frame:
            self.is_paused = not self.is_paused

    def change_speed(self, direction):
        speeds = [0.5, 1.0, 2.0, 4.0]
        try:
            i = speeds.index(self.game_speed)
        except ValueError:
            i = 1
        self.game_speed = speeds[max(0, min(len(speeds) - 1, i + direction))]

    # ====================================================== the budget
    def fortnight_day(self):
        """Which day of the running fortnight we are on, 1..14."""
        d = int((self.clock_minutes - self.fortnight_start) / 1440.0) + 1
        return max(1, min(BUDGET_PERIOD_DAYS, d))

    def _default_budget_counts(self, country, funds):
        """The opening appropriation: the treasury maxed out, divided
        equally across every unit type on the books."""
        has_harbor = any(c.harbor and c.country == country
                         for c in self.cities)
        types = [ut for ut in NATION_UNIT_STATS[country]
                 if UNIT_TYPES[ut]['domain'] != 'sea' or has_harbor]
        counts = {ut: 0 for ut in types}
        share = funds / max(1, len(types))
        spent = 0
        for ut in types:
            cost = stats_for(ut, country)['cost']
            counts[ut] = int(share // cost)
            spent += counts[ut] * cost
        # spend the remainder on the cheapest lines: the budget maxes out
        rest = funds - spent
        for ut in sorted(types, key=lambda t: stats_for(t, country)['cost']):
            cost = stats_for(ut, country)['cost']
            n = int(rest // cost)
            if n > 0:
                counts[ut] += n
                rest -= n * cost
        return counts

    def _apply_fortnight_budget(self):
        """Fortnight opens: the standing budget (last transmitted, or the
        default) is executed against whatever the treasury holds."""
        country = self.player_country
        counts = dict(self.budget_counts)
        buy = {}
        spent = 0
        for ut, n in counts.items():
            cost = stats_for(ut, country)['cost']
            for _ in range(n):
                if self.funds[country] - spent < cost:
                    break
                buy[ut] = buy.get(ut, 0) + 1
                spent += cost
        if spent <= 0:
            return
        self.funds[country] -= spent
        # the production ledger the WAR INDUSTRIES page reports against
        self.fortnight_order = dict(buy)
        self.fortnight_delivered = {}
        self._distribute_production(country, buy)
        lines = ", ".join("%dx %s" % (n, UNIT_TYPES[ut]['icon'])
                          for ut, n in buy.items() if n > 0)
        self.fax.post(
            "FORTNIGHT APPROPRIATION",
            "The standing budget is executed: %s committed. %s. Amend "
            "the budget any time -- it takes effect next fortnight." %
            (B("$%d" % spent), lines),
            sender="EXCHEQUER")

    def _fortnight_rollover(self):
        """The fortnight turns: decreed tax rates bind, every treasury
        collects its cities' taxes, industry drifts under the new rates,
        annexations complete, and the standing budget is executed."""
        take = {c: 0 for c in COUNTRIES}
        for city in self.cities:
            if city.pending_tax is not None:
                city.tax_rate = city.pending_tax
                city.pending_tax = None
            take[city.country] += city.fortnight_revenue()
            if not city.annexing:
                city.industry = max(5.0, min(100.0, city.industry +
                                             city.industry_drift()))
            if city.annexing:
                city.annexing = False
                if city.country == self.player_country:
                    self.fax_short("%s ANNEXED -- NOW ON THE TAX ROLLS"
                                   % city.name.upper())
        for country, amount in take.items():
            if country not in self.eliminated:
                self.funds[country] += amount
        self._update_borders()      # annexations completed above
        if take.get(self.player_country):
            self.fax.post(
                "FORTNIGHT TAX RECEIPTS",
                "The provinces remit %s to the treasury." %
                B("$%d" % take[self.player_country]),
                sender="EXCHEQUER")
        self._apply_fortnight_budget()

    def projected_revenue(self, country):
        """What the cities will remit at the next fortnight under the
        DECREED tax rates (pending decrees included)."""
        total = 0
        for c in self.cities:
            if c.country != country or c.annexing:
                continue
            rate = (c.pending_tax if c.pending_tax is not None
                    else c.tax_rate)
            total += c.fortnight_revenue(rate)
        return total

    def open_budget(self):
        if self.game_state != 'playing' or self.budget_fax:
            return
        has_harbor = any(c.harbor and c.country == self.player_country
                         for c in self.cities)
        # the manifest is planned against the money that will exist when
        # it executes: the treasury plus the taxes the decreed rates will
        # bring in at the fortnight
        treasury = int(self.funds[self.player_country])
        revenue = self.projected_revenue(self.player_country)
        self.budget_fax = BudgetFax(
            self, self, treasury + revenue,
            NATION_UNIT_STATS[self.player_country],
            has_harbor, self._budget_transmit, self._budget_discard,
            initial=self.budget_counts,
            subtitle="PROJECTED TAX REVENUE $%d + TREASURY $%d = $%d "
                     "PLANNABLE NEXT FORTNIGHT" %
                     (revenue, treasury, revenue + treasury))

    def _budget_discard(self):
        if self.budget_fax:
            self.budget_fax.destroy()
            self.budget_fax = None
            self.fax_short("BUDGET MANIFEST DISCARDED")

    def _budget_transmit(self, counts):
        total = sum(stats_for(ut, self.player_country)['cost'] * n
                    for ut, n in counts.items())
        n_units = sum(counts.values())
        self.budget_fax.destroy()
        self.budget_fax = None
        if n_units == 0:
            self.fax_short("NOTHING ALLOCATED -- MANIFEST UNCHANGED")
            return
        self.budget_counts = dict(counts)
        self.fax.post(
            "BUDGET TRANSMITTED",
            "%s allocated. The new appropriation takes effect when the "
            "next fortnight begins; until then the current one stands." %
            B("$%d" % total),
            sender="EXCHEQUER")

    def _capture_clicked(self, city):
        if self.attempt_capture(city, self.player_country):
            self._select_city(city)     # reopen as our own municipality

    def open_tax_fax(self, city):
        if (self.game_state != 'playing' or self.tax_fax
                or city.country != self.player_country or city.annexing):
            return
        self.tax_fax = TaxFax(self, city, self._tax_transmit,
                              self._tax_discard)

    def _tax_transmit(self, city, rate):
        if self.tax_fax:
            self.tax_fax.destroy()
            self.tax_fax = None
        rate = max(0, min(100, int(rate)))
        city.pending_tax = rate
        self.fax.post(
            "TAX DECREE -- %s" % city.name.upper(),
            "The rate is set to %s, binding from the next fortnight. "
            "Projected remittance %s; industry drift %s%% per "
            "fortnight." %
            (B("%d%%" % rate), B("$%d" % city.fortnight_revenue(rate)),
             B("%+.1f" % city.industry_drift(rate))),
            sender="EXCHEQUER")
        if self.selected_city is city:
            self._refresh_selection_ui()

    def _tax_discard(self):
        if self.tax_fax:
            self.tax_fax.destroy()
            self.tax_fax = None

    def open_factory_report(self):
        """The war-industries FAX: per unit type, how many of this
        fortnight's order have been delivered, and how far along the
        next one on the line is."""
        if self.game_state != 'playing' or self.briefing_fax:
            return
        player = self.player_country
        rows = []
        for ut, total in self.fortnight_order.items():
            s = stats_for(ut, player)
            done = min(total, self.fortnight_delivered.get(ut, 0))
            # progress of the closest-to-delivery item of this type
            build = max(1.0, s['build_time'] * PRODUCTION_TIME_FACTOR)
            progress = None
            for c in self.cities:
                if c.country != player:
                    continue
                for (qut, secs) in c.production:
                    if qut == ut:
                        p = 1.0 - max(0.0, secs) / build
                        progress = p if progress is None \
                            else max(progress, p)
            if done >= total:
                progress = 1.0
            rows.append((s['label'].upper(),
                         get_icon_path(ut, 'dark'),
                         done, total,
                         0.0 if progress is None else progress))
        rows.sort(key=lambda r: r[0])
        self.briefing_fax = ProductionFax(self, rows,
                                          self._close_briefing)

    def _distribute_production(self, country, counts):
        cities = [c for c in self.cities if c.country == country]
        if not cities:
            return
        harbors = [c for c in cities if c.harbor]
        capital = next((c for c in cities if c.capital), cities[0])
        rr = {'land': 0, 'sea': 0}
        for ut, n in counts.items():
            stats = stats_for(ut, country)
            for _ in range(n):
                domain = stats['domain']
                if domain == 'sea':
                    if not harbors:
                        continue
                    city = harbors[rr['sea'] % len(harbors)]
                    rr['sea'] += 1
                elif domain == 'air':
                    city = capital
                else:
                    city = cities[rr['land'] % len(cities)]
                    rr['land'] += 1
                city.production.append(
                    [ut, stats['build_time'] * PRODUCTION_TIME_FACTOR])

    def queue_production(self, city, unit_type):
        city.production.append(
            [unit_type,
             stats_for(unit_type, city.country)['build_time'] *
             PRODUCTION_TIME_FACTOR])

    # ====================================================== picking
    def screen_pos(self, world_pos):
        p3 = self.cam.getRelativePoint(self.render, world_pos)
        p2 = Point2()
        if self.camLens.project(p3, p2):
            return p2
        return None

    def mouse_ground_point(self):
        if not self.mouseWatcherNode.hasMouse():
            return None
        mpos = self.mouseWatcherNode.getMouse()
        near, far = Point3(), Point3()
        self.camLens.extrude(mpos, near, far)
        o = self.render.getRelativePoint(self.cam, near)
        d = self.render.getRelativePoint(self.cam, far) - o
        d.normalize()
        b = 2.0 * o.dot(d)
        c = o.dot(o) - GLOBE_RADIUS * GLOBE_RADIUS
        disc = b * b - 4 * c
        if disc < 0:
            return None
        t = (-b - math.sqrt(disc)) / 2.0
        if t < 0:
            return None
        hit = o + d * t
        hit.normalize()
        return hit

    def _pick_object(self, mpos, candidates):
        best, best_d = None, CLICK_RADIUS
        for obj, world_pos in candidates:
            sp = self.screen_pos(world_pos)
            if sp is None:
                continue
            d = (sp - mpos).length()
            if d < best_d:
                best, best_d = obj, d
        return best

    def _unit_world_pos(self, u):
        return u.pos * (GLOBE_RADIUS * u.altitude())

    def _facing_camera(self, pos_vec):
        cam_dir = latlon_to_vec(self.cam_lat, self.cam_lon)
        return pos_vec.dot(cam_dir) > 0.05

    def _commandable(self, u):
        """Player units that can be seen and given orders on the map.
        Embarked aircraft are commanded through their carrier's menu."""
        return (u.alive and u.country == self.player_country
                and not u.carried_by and u.in_contact
                and not self.is_embarked(u))

    # ------------------------------------------------------- selection
    def on_lmb_down(self):
        if (self.game_state != 'playing' or self.pause_frame
                or self.briefing_fax or self.tax_fax):
            return
        if not self.mouseWatcherNode.hasMouse():
            return
        self.drag_start = Point2(self.mouseWatcherNode.getMouse())

    def on_lmb_up(self):
        if self.game_state != 'playing' or self.drag_start is None:
            return
        if not self.mouseWatcherNode.hasMouse():
            self.drag_start = None
            self._remove_drag_box()
            return
        mpos = Point2(self.mouseWatcherNode.getMouse())
        start = self.drag_start
        self.drag_start = None
        self._remove_drag_box()
        shift = self.mouseWatcherNode.isButtonDown(self._key_shift)
        if (mpos - start).length() > DRAG_THRESHOLD:
            self._box_select(start, mpos, shift)
        else:
            self._click_select(mpos, shift)

    def _click_select(self, mpos, shift):
        own = [(u, self._unit_world_pos(u)) for u in self.units
               if self._commandable(u) and self._facing_camera(u.pos)]
        unit = self._pick_object(mpos, own)
        if unit:
            self._select_city(None)
            self._select_airfield(None)
            now = globalClock.getFrameTime()
            last_t, last_u = self._last_click
            self._last_click = (now, unit)
            if (not shift and last_u is unit and now - last_t < 0.4):
                # double-click: every visible unit of this type on screen
                self.clear_selection()
                for u in self.units:
                    if (u.unit_type == unit.unit_type
                            and self._commandable(u)
                            and self._facing_camera(u.pos)):
                        sp = self.screen_pos(self._unit_world_pos(u))
                        if sp and -1 <= sp.x <= 1 and -1 <= sp.y <= 1:
                            self.selected.append(u)
                            u.set_selected(True)
                self._refresh_selection_ui()
                return
            if shift:
                if unit in self.selected:
                    self._deselect_unit(unit)
                else:
                    self.selected.append(unit)
                    unit.set_selected(True)
            else:
                self.clear_selection()
                self.selected = [unit]
                unit.set_selected(True)
            self._refresh_selection_ui()
            return
        self._last_click = (0.0, None)
        own_fields = [(a, a.pos * GLOBE_RADIUS) for a in self.airfields
                      if a.country == self.player_country
                      and self._facing_camera(a.pos)]
        field = self._pick_object(mpos, own_fields)
        if field:
            self.clear_selection()
            self._select_airfield(field)
            return
        own_harbors = [(h, h.pos * GLOBE_RADIUS) for h in self.harbors
                       if h.country == self.player_country
                       and self._facing_camera(h.pos)]
        harbor = self._pick_object(mpos, own_harbors)
        if harbor:
            self.clear_selection()
            self._select_harbor(harbor)
            return
        own_cities = [(c, c.label_pos * GLOBE_RADIUS)
                      for c in self.cities
                      if c.country == self.player_country
                      and self._facing_camera(c.pos)]
        city = self._pick_object(mpos, own_cities)
        if city:
            self.clear_selection()
            self._select_city(city)
            return
        # visible enemy: selectable for an intelligence view (no orders)
        foes = [(u, self._unit_world_pos(u)) for u in self.units
                if u.alive and u.country != self.player_country
                and u.visible_to_player and not u.carried_by
                and not self.is_parked(u)
                and self._facing_camera(u.pos)]
        foe = self._pick_object(mpos, foes)
        if foe:
            self.clear_selection()
            self.selected = [foe]
            foe.set_selected(True)
            self._refresh_selection_ui()
            return
        # any other city (enemy or neutral): selectable for an intel view
        other_cities = [(c, c.label_pos * GLOBE_RADIUS)
                        for c in self.cities
                        if c.country != self.player_country
                        and self._facing_camera(c.pos)]
        ocity = self._pick_object(mpos, other_cities)
        if ocity:
            self.clear_selection()
            self._select_city(ocity)
            return
        if not shift:
            self.clear_selection()
            self._refresh_selection_ui()

    def _box_select(self, a, b, shift):
        x0, x1 = min(a.x, b.x), max(a.x, b.x)
        y0, y1 = min(a.y, b.y), max(a.y, b.y)
        if not shift:
            self.clear_selection()
        self._select_city(None)
        for u in self.units:
            if not self._commandable(u) or not self._facing_camera(u.pos):
                continue
            sp = self.screen_pos(self._unit_world_pos(u))
            if sp and x0 <= sp.x <= x1 and y0 <= sp.y <= y1:
                if u not in self.selected:
                    self.selected.append(u)
                    u.set_selected(True)
        self._refresh_selection_ui()

    def _deselect_unit(self, unit):
        if unit in self.selected:
            self.selected.remove(unit)
            unit.set_selected(False)

    def clear_selection(self):
        for u in self.selected:
            u.set_selected(False)
        self.selected = []
        self.roster_base = None
        self._select_city(None)
        self._select_airfield(None)
        self._select_harbor(None)
        self._refresh_selection_ui()

    def _select_city(self, city):
        if self.selected_city:
            self.selected_city.sel_ring.hide()
        self.selected_city = city
        if city:
            city.sel_ring.show()
        self._refresh_selection_ui()

    def _select_airfield(self, field):
        if self.selected_airfield:
            self.selected_airfield.sel_ring.hide()
        self.selected_airfield = field
        if field:
            field.sel_ring.show()
        self._refresh_selection_ui()

    def _select_harbor(self, harbor):
        if self.selected_harbor:
            self.selected_harbor.sel_ring.hide()
        self.selected_harbor = harbor
        if harbor:
            harbor.sel_ring.show()
        self._refresh_selection_ui()

    def assign_group(self, n):
        own = [u for u in self.selected
               if u.country == self.player_country]
        if own:
            self.groups[n] = own
            self.fax_short("CONTROL GROUP %d ASSIGNED (%d UNITS)"
                           % (n, len(own)))

    def recall_group(self, n):
        units = [u for u in self.groups.get(n, []) if self._commandable(u)]
        if units:
            self.clear_selection()
            self.selected = units
            for u in units:
                u.set_selected(True)
            self._refresh_selection_ui()

    # ------------------------------------------------------- orders
    def on_rmb(self):
        if (self.game_state != 'playing' or self.pause_frame
                or self.briefing_fax or self.tax_fax):
            return
        if not self.selected or not self.mouseWatcherNode.hasMouse():
            return
        mpos = Point2(self.mouseWatcherNode.getMouse())
        ground = self.mouse_ground_point()
        if ground is None:
            return
        shift = self.mouseWatcherNode.isButtonDown(self._key_shift)

        # an engineering works order is armed: this click sites it
        if self.build_mode:
            self._order_build(ground, shift)
            return

        # selection may include enemies (intelligence view): orders only
        # ever apply to own troops
        own_selected = [u for u in self.selected
                        if u.country == self.player_country]
        if not own_selected:
            return

        # an unload/paradrop order is armed: this click sites the drop
        if self.unload_mode:
            self.unload_mode = False
            for u in own_selected:
                if not u.cargo:
                    continue
                if (u.stats['domain'] == 'air' and self.is_parked(u)
                        and angle_between(ground, u.based_at.pos) *
                        GLOBE_RADIUS < 0.6):
                    self._unload_cargo(u)      # unload on the apron
                else:
                    u.give_order({'kind': 'unload', 'goal': Vec3(ground)},
                                 queue=shift)
            self.fax_short("DISEMBARKATION ORDERED")
            self._refresh_selection_ui()
            return

        # aircraft already aloft are committed to their flight plan
        aloft = [u for u in own_selected
                 if u.stats['domain'] == 'air' and u.based_at is None]
        if aloft:
            self.fax_short("AIRCRAFT ALOFT -- COMMITTED TO FLIGHT PLAN")
            if len(aloft) == len(own_selected):
                return

        enemies = [(u, self._unit_world_pos(u)) for u in self.units
                   if u.alive and u.country != self.player_country
                   and u.visible_to_player and self._facing_camera(u.pos)]
        target = self._pick_object(mpos, enemies)
        if target is None:
            bridges = [(b, b.pos * GLOBE_RADIUS) for b in self.bridges
                       if self._facing_camera(b.pos)]
            target = self._pick_object(mpos, bridges)
        if target is None:
            own_transports = [
                (u, self._unit_world_pos(u)) for u in self.units
                if self._commandable(u) and u.stats.get('capacity')
                and self._facing_camera(u.pos)]
            transport = self._pick_object(mpos, own_transports)
            if transport and any(u.stats['domain'] == 'land'
                                 for u in own_selected):
                boarders = [u for u in own_selected
                            if u.stats['domain'] == 'land'
                            and u is not transport]
                self._order_board(transport, boarders, shift)
                return

        commandable = [u for u in own_selected if u not in aloft]

        # enemy airfields can be demolished like bridges
        if target is None:
            foe_fields = [(a, a.pos * GLOBE_RADIUS) for a in self.airfields
                          if a.country != self.player_country
                          and self._facing_camera(a.pos)]
            foe_field = self._pick_object(mpos, foe_fields)
            if foe_field is not None:
                attackers = [u for u in commandable
                             if u.can_target('bridge')]
                if attackers:
                    for u in attackers:
                        u.give_order({'kind': 'attack',
                                      'target': foe_field}, queue=shift)
                    self.fax_short("STRIKE ON %s ORDERED" % foe_field.name)
                    return

        # right-click an own airfield with land units: board a parked
        # air transport there if one has room, else march to the field
        if target is None:
            fields = [(a, a.pos * GLOBE_RADIUS) for a in self.airfields
                      if a.country == self.player_country
                      and self._facing_camera(a.pos)]
            field = self._pick_object(mpos, fields)
            if field is not None:
                lifters = [p for p in self.base_wing(field)
                           if p.stats.get('capacity')
                           and self._board_capacity_left(p) > 0]
                landers = [u for u in commandable
                           if u.stats['domain'] == 'land']
                if lifters and landers:
                    self._order_board(lifters[0], landers, shift)
                    return
                for u in commandable:
                    u.give_order({'kind': 'move',
                                  'goal': Vec3(field.pos)}, queue=shift)
                lifts = [u for u in commandable
                         if u.stats.get('capacity') and u.cargo
                         and u.stats['domain'] == 'air']
                if lifts:
                    self.fax_short("AIR LIFT TO %s ORDERED -- %d UNIT(S) "
                                   "ABOARD" % (field.name,
                                               sum(len(u.cargo)
                                                   for u in lifts)))
                return

        if isinstance(target, Bridge):
            self._order_on_bridge(target, shift, commandable)
            return
        if isinstance(target, Unit):
            for u in commandable:
                if u.can_target(target.stats['domain']):
                    u.give_order({'kind': 'attack', 'target': target},
                                 queue=shift)
                else:
                    u.give_order({'kind': 'move', 'goal': Vec3(target.pos)},
                                 queue=shift)
            return

        # plain ground order: move only — transports never disembark on
        # their own; arm UNLOAD from the selection panel instead
        goals = self._formation_goals(ground, commandable)
        for u, goal in zip(commandable, goals):
            if u.stats.get('supply_carrier'):
                u.station = Vec3(goal)          # supply loop anchor
            u.give_order({'kind': 'move', 'goal': goal}, queue=shift)

    def _formation_goals(self, ground, units):
        """Spread simultaneous movers around the target so they don't
        pile onto one point (ring packing, deterministic by order)."""
        n = len(units)
        if n <= 1:
            return [Vec3(ground)] * n
        north = north_tangent(ground)
        east = north.cross(ground)
        # fixed spacing: deterministic regardless of the viewer's zoom
        # (a server and every client must compute identical goals)
        spacing = FORMATION_SPACING
        goals = []
        idx = 0
        ring = 0
        while len(goals) < n:
            if ring == 0:
                goals.append(Vec3(ground))
                ring += 1
                continue
            cap = 6 * ring
            r = ring * spacing / GLOBE_RADIUS
            for k in range(cap):
                if len(goals) >= n:
                    break
                a = 2 * math.pi * k / cap
                p = Vec3(ground) + (north * math.cos(a) +
                                    east * math.sin(a)) * r
                p.normalize()
                goals.append(p)
            ring += 1
        return goals

    def _order_on_bridge(self, bridge, shift, units=None):
        units = self.selected if units is None else units
        attackers = [u for u in units if u.can_target('bridge')]
        engineers = [u for u in units if u.stats.get('engineer')]
        if not bridge.alive and engineers:
            for u in engineers:
                u.give_order({'kind': 'repair', 'target': bridge},
                             queue=shift)
            self.fax_short("ENGINEERS DISPATCHED TO REBUILD BRIDGE")
        elif bridge.alive and attackers:
            for u in attackers:
                u.give_order({'kind': 'attack', 'target': bridge},
                             queue=shift)
            self.fax_short("DEMOLITION OF BRIDGE ORDERED")
        else:
            for u in units:
                u.give_order({'kind': 'move', 'goal': Vec3(bridge.pos)},
                             queue=shift)

    def order_stop(self):
        for u in self.selected:
            if u.country != self.player_country:
                continue        # intelligence view: not ours to command
            if u.stats['domain'] == 'air' and u.based_at is None:
                continue        # a flight plan cannot be halted mid-air
            u.clear_orders()

    # ------------------------------------------------- aircraft sorties
    @staticmethod
    def is_parked(u):
        """Aircraft in a hangar or on a deck: hidden, sees nothing."""
        return u.stats['domain'] == 'air' and u.based_at is not None

    # legacy name; embarked-on-carrier and parked-at-field behave alike
    is_embarked = is_parked

    def base_wing(self, base):
        return [u for u in self.units if u.alive and u.based_at is base]

    def carrier_wing(self, carrier):
        return self.base_wing(carrier)

    def _refresh_air_base(self, base):
        if base is None or not getattr(base, 'alive', False):
            return
        n = len(self.base_wing(base))
        if isinstance(base, Unit):
            base.set_wing_count(n)
        else:
            base.set_count(n)

    def _base_stock(self, base):
        return base.av_stock if isinstance(base, Unit) else base.stock

    def _draw_base_stock(self, base, amount):
        if isinstance(base, Unit):
            base.av_stock = max(0.0, base.av_stock - amount)
        else:
            base.stock = max(0.0, base.stock - amount)

    def airfields_of(self, country):
        """The country's airfields plus its carriers at sea."""
        fields = [a for a in self.airfields if a.country == country]
        fields += [u for u in self.units
                   if u.alive and u.country == country
                   and u.unit_type == 'aircraft_carrier']
        return fields

    def _begin_air_order(self, unit, order):
        """Aircraft fly complete sorties: airfield -> objective -> an
        airfield within fuel. No hovering, no mid-air re-tasking."""
        if unit.based_at is None:
            unit.current_order = None
            return
        # the base pays the sortie's supply bill before wheels-up
        if self._base_stock(unit.based_at) < SORTIE_COST:
            if unit.country == self.player_country:
                name = getattr(unit.based_at, 'name', None) or \
                    unit.based_at.stats['label']
                self.fax.post(
                    "SORTIE REFUSED",
                    "%s at %s. Send supply columns forward." %
                    (B("AVIATION SUPPLY EXHAUSTED"), name),
                    sender="AIR MINISTRY")
            unit.current_order = None
            return
        # roll out of the hangar / off the deck at the base's position
        unit.pos = Vec3(unit.based_at.pos)
        unit.update_visual()
        kind = order['kind']
        if kind == 'attack':
            objective = Vec3(order['target'].pos)
        else:
            objective = Vec3(order.get('goal', unit.pos))
        fields = self.airfields_of(unit.country)
        if not fields:
            unit.current_order = None
            return
        home = min(fields,
                   key=lambda f: angle_between(objective, f.pos))
        d_out = unit.dist_to(objective)
        d_home = angle_between(objective, home.pos) * GLOBE_RADIUS
        if d_out + d_home > unit.stats['fuel']:
            if unit.country == self.player_country:
                self.fax.post(
                    "SORTIE REFUSED",
                    "Objective %s: flight plan %d mi, endurance "
                    "%d mi. Stage closer." %
                    (B("BEYOND FUEL RADIUS"), (d_out + d_home) * 60,
                     unit.stats['fuel'] * 60),
                    sender="AIR MINISTRY")
            unit.current_order = None
            return
        was_base = unit.based_at
        unit.path = [(objective, 1.0), (Vec3(home.pos), 1.0)]
        unit.landing_at = home
        unit.based_at = None            # wheels up
        self._draw_base_stock(was_base, SORTIE_COST)
        # own aircraft appear at once; enemy aircraft stay dark until a
        # friendly vision field actually spots them
        if unit.country == self.player_country:
            unit.root.show()
        else:
            unit.visible_to_player = False
            unit.root.hide()
        self._refresh_air_base(was_base)
        if kind == 'attack':
            unit.attack_target = order['target']
        elif kind == 'unload':
            unit.drop_at = objective

    def _finish_air_order(self, unit, order):
        """Path exhausted: land, or chase the carrier that moved."""
        field = unit.landing_at
        if field is None or not getattr(field, 'alive', True):
            fields = self.airfields_of(unit.country)
            if not fields:
                # every airfield and carrier is gone: the aircraft has
                # nowhere left to set down and is lost
                if unit.country == self.player_country:
                    self.fax.post(
                        "AIRCRAFT LOST",
                        "%s: %s. The crew are gone." %
                        (unit.stats['label'], B("NO AIRFIELD TO RECOVER")),
                        sender="CASUALTY BRANCH")
                self.unit_destroyed(unit, None)
                return True
            field = min(fields, key=lambda f: unit.dist_to(f.pos))
            unit.landing_at = field
        if unit.dist_to(field.pos) < 0.5:
            unit.based_at = field
            unit.landing_at = None
            unit.attack_target = None
            unit.drop_at = None
            unit.pos = Vec3(field.pos)
            unit.update_visual()
            # into the hangar / struck below: parked aircraft are out of
            # sight and see nothing
            unit.root.hide()
            unit.in_contact = True
            if unit in self.selected:
                self._deselect_unit(unit)
                self._refresh_selection_ui()
            self._refresh_air_base(field)
            if unit.country == self.player_country:
                name = getattr(field, 'name', None) or field.stats['label']
                self.fax_short("%s RECOVERED AT %s" %
                               (unit.stats['label'].upper(), name.upper()))
            return True
        unit.path = [(Vec3(field.pos), 1.0)]
        return False

    def check_paradrop(self, unit):
        if unit.drop_at is None or not unit.cargo:
            unit.drop_at = None
            return
        if unit.dist_to(unit.drop_at) < 0.4:
            self._unload_cargo(unit)
            unit.drop_at = None

    # order execution callbacks (called by Unit.update) ------------------
    def begin_order(self, unit, order):
        kind = order['kind']
        domain = unit.stats['domain']
        if domain == 'air':
            self._begin_air_order(unit, order)
            return
        if kind in ('move', 'unload'):
            pre = order.pop('pre_path', None)
            if pre:
                unit.path = pre         # leg was routed when it was queued
                return
            goal = self._legal_goal(unit, order['goal'])
            self._enqueue_plan(unit, goal, silent=order.get('auto', False),
                               indicate=order.pop('indicate', False))
        elif kind == 'attack':
            unit.attack_target = order['target']
            self._approach_target(unit, order['target'],
                                  indicate=order.pop('indicate', False))
        elif kind in ('board', 'repair'):
            self._approach_target(unit, order['target'])

    def _legal_goal(self, unit, goal):
        lat, lon = vec_to_latlon(goal)
        domain = unit.stats['domain']
        if domain == 'sea' and self.world.is_land(lat, lon):
            return latlon_to_vec(*self.world.nearest_water(lat, lon))
        if domain == 'land' and not self.world.is_land(lat, lon):
            return latlon_to_vec(*self.world.nearest_land(lat, lon))
        return goal

    def _approach_target(self, unit, target, indicate=False):
        goal = self._legal_goal(unit, Vec3(target.pos))
        self._enqueue_plan(unit, goal, indicate=indicate)

    def on_order_given(self, unit, order, queue):
        """Called for every order entering a unit's queue. Marks orders
        from the player's hand for the [PLANNING ROUTE] indicator, and
        pre-plans queued waypoint legs so every leg gets real routing
        (not just the first)."""
        if unit.country == self.player_country and not order.get('auto'):
            order['indicate'] = True
        if (queue and order['kind'] in ('move', 'unload')
                and order.get('goal') is not None
                and unit.stats['domain'] != 'air'):
            start = self._queue_leg_start(unit, order)
            goal = self._legal_goal(unit, order['goal'])
            self._enqueue_preplan(unit, start, goal, order)

    def _queue_leg_start(self, unit, order):
        """Where the unit will be when this queued order begins: the end
        of everything queued before it."""
        start = None
        for o in unit.order_queue:
            if o is order:
                break
            g = o.get('goal')
            if g is None:
                tgt = o.get('target')
                g = getattr(tgt, 'pos', None)
            if g is not None:
                start = Vec3(g)
        if start is not None:
            return start
        if unit.path:
            return Vec3(unit.path[-1][0])
        return Vec3(unit.pos)

    def _enqueue_preplan(self, unit, start, goal, order):
        self._plan_seq += 1
        token = self._plan_seq
        self._preplans[token] = order
        if order.get('indicate'):
            self._ind_tokens.add(token)
        self._pending_plans += 1
        self._plan_jobs.put((unit, unit.stats['domain'], Vec3(start),
                             Vec3(goal), token))

    # ---------------------------------------------- background planning
    def _plan_loop(self):
        """Worker thread: route planning off the main thread so a
        trans-planet order never freezes the game."""
        while True:
            unit, domain, start, goal, token = self._plan_jobs.get()
            try:
                path = self.planner.plan(domain, start, goal)
            except Exception:
                path = None
            self._plan_results.append((unit, token, path))

    def _enqueue_plan(self, unit, goal, silent=False, indicate=False):
        self._plan_seq += 1
        unit.plan_pending = self._plan_seq
        unit._plan_silent = silent
        if indicate:
            self._ind_tokens.add(self._plan_seq)
        self._pending_plans += 1
        self._plan_jobs.put((unit, unit.stats['domain'], Vec3(unit.pos),
                             Vec3(goal), self._plan_seq))

    def _drain_plans(self):
        while self._plan_results:
            unit, token, path = self._plan_results.pop(0)
            self._pending_plans = max(0, self._pending_plans - 1)
            self._ind_tokens.discard(token)
            # a pre-planned queued leg: file the route into its order
            order = self._preplans.pop(token, None)
            if order is not None:
                if path:
                    order['pre_path'] = path
                continue
            if not unit.alive or getattr(unit, 'plan_pending', None) \
                    != token:
                continue
            unit.plan_pending = None
            if path is None:
                # back off so a stranded unit can't churn the planner
                # (and spam FAXes) every tick
                unit._route_fail_until = globalClock.getFrameTime() + 20.0
                if not getattr(unit, '_plan_silent', False):
                    self._no_route_fax(unit)
                unit.current_order = None
            else:
                unit.path = path
        # [PLANNING ROUTE] indicator: plain centred text, no backdrop
        if self.planning_text is None and self.game_state == 'playing':
            tn = TextNode('planning')
            tn.setText("[ PLANNING ROUTE ]")
            tn.setAlign(TextNode.ACenter)
            if self.hud_font:
                tn.setFont(self.hud_font)
            tn.setTextColor(0.92, 0.88, 0.72, 0.85)
            tn.setShadow(0.05, 0.05)
            tn.setShadowColor(0.05, 0.05, 0.05, 0.8)
            self.planning_text = self.aspect2d.attachNewNode(tn)
            self.planning_text.setScale(0.05)
            self.planning_text.setPos(0, 0, 0.1)
            self.planning_text.hide()
        if self.planning_text is not None:
            # only the player's own latest waypoint clicks show the
            # indicator -- background/AI/auto planning stays silent
            busy = bool(self._ind_tokens)
            if busy and self.planning_text.isHidden():
                self.planning_text.show()
            elif not busy and not self.planning_text.isHidden():
                self.planning_text.hide()

    def _replan_ready(self, unit, cooldown=0.8):
        """Rate-limits pursuit re-planning so chases don't spike frames."""
        now = globalClock.getFrameTime()
        if now - getattr(unit, '_last_replan', -99.0) < cooldown:
            return False
        unit._last_replan = now
        return True

    def _no_route_fax(self, unit):
        if unit.country == self.player_country:
            self.fax.post(
                "ORDER REFUSED",
                "%s: %s. Rivers need bridges; open water needs "
                "transports." % (unit.stats['label'],
                                 B("NO PRACTICABLE ROUTE")),
                sender="MOVEMENT CONTROL")

    def order_finished(self, unit, order):
        kind = order['kind']
        if unit.stats['domain'] == 'air':
            return self._finish_air_order(unit, order)
        if kind == 'move':
            return True
        if kind == 'attack':
            target = order['target']
            if not getattr(target, 'alive', False):
                unit.attack_target = None
                return True
            if unit.dist_to(target.pos) > unit.stats['range']:
                if not self._replan_ready(unit):
                    return False
                self._approach_target(unit, target)
                return not unit.path
            return False
        if kind == 'board':
            transport = order['target']
            if not transport.alive:
                return True
            if unit.dist_to(transport.pos) < 0.6:
                if len(transport.cargo) < transport.stats['capacity']:
                    self._load_unit(transport, unit)
                return True
            if not self._replan_ready(unit):
                return False
            self._approach_target(unit, transport)
            return not unit.path
        if kind == 'build':
            # the engineers must actually be standing on the site before
            # the first shovel goes in
            near = 0.4 if order.get('what') == 'harbor' else 0.18
            if unit.dist_to(order['site']) < near:
                order['t'] -= globalClock.getDt() * self.game_speed
                if order['t'] <= 0:
                    self._complete_build(unit, order)
                    return True
                return False
            if not self._replan_ready(unit):
                return False
            goal = self._legal_goal(unit, order['site'])
            self._enqueue_plan(unit, goal)
            return False
        if kind == 'repair':
            bridge = order['target']
            if bridge.hp >= bridge.max_hp:
                return True
            if unit.dist_to(bridge.pos) < 0.6:
                bridge.repair(BRIDGE_REPAIR_RATE * self.game_speed *
                              globalClock.getDt())
                return False
            self._approach_target(unit, bridge)
            return not unit.path
        if kind == 'unload':
            self._unload_cargo(unit)
            return True
        return True

    def _board_capacity_left(self, transport):
        """Free berths = capacity minus those aboard and those already
        ordered to board (so repeated commands can't overfill)."""
        inbound = 0
        for u in self.units:
            if not u.alive or u.carried_by:
                continue
            orders = list(u.order_queue)
            if u.current_order:
                orders.append(u.current_order)
            if any(o.get('kind') == 'board' and o.get('target') is transport
                   for o in orders):
                inbound += 1
        return transport.stats['capacity'] - len(transport.cargo) - inbound

    def _order_board(self, transport, boarders, shift):
        """Order up to the free berths onto the transport; the rest are
        refused so a full transport can't be over-committed."""
        slots = max(0, self._board_capacity_left(transport))
        accepted = boarders[:slots]
        for u in accepted:
            u.give_order({'kind': 'board', 'target': transport},
                         queue=shift)
        rejected = len(boarders) - len(accepted)
        if accepted and rejected:
            self.fax_short("%d EMBARKING -- %d HELD BACK (NO ROOM)" %
                           (len(accepted), rejected))
        elif rejected:
            self.fax_short("TRANSPORT FULL -- ORDER REFUSED")
        elif accepted:
            self.fax_short("EMBARKATION ORDER DISPATCHED (%d)" %
                           len(accepted))

    def _load_unit(self, transport, unit):
        unit.carried_by = transport
        unit.clear_orders()
        unit.set_selected(False)
        if unit in self.selected:
            self.selected.remove(unit)
        unit.root.hide()
        transport.cargo.append(unit)
        if transport.country == self.player_country:
            self.fax_short("%s EMBARKED ABOARD %s" %
                           (unit.stats['label'].upper(),
                            transport.stats['label'].upper()))

    def _unload_cargo(self, transport):
        if not transport.cargo:
            return
        lat, lon = vec_to_latlon(transport.pos)
        para = transport.stats.get('paradrop')
        n_out = 0
        for unit in list(transport.cargo):
            la, lo = self.world.nearest_land(lat + random.uniform(-.4, .4),
                                             lon + random.uniform(-.4, .4))
            d = latlon_to_vec(la, lo)
            if not para and angle_between(d, transport.pos) * GLOBE_RADIUS > 2.2:
                continue
            transport.cargo.remove(unit)
            unit.carried_by = None
            unit.pos = d
            if unit.country == self.player_country:
                unit.root.show()
            else:
                unit.visible_to_player = False
                unit.root.hide()        # revealed only when spotted
            unit.update_visual()
            n_out += 1
        if transport.country == self.player_country:
            if n_out:
                verb = ("PARACHUTE ASSAULT" if para else "LANDING")
                self.fax_short("%s: %d UNIT(S) PUT ASHORE" % (verb, n_out))
            else:
                self.fax_short("NO SUITABLE GROUND TO DISEMBARK -- "
                               "CLOSE WITH THE SHORE")

    # ====================================================== combat
    def auto_acquire_target(self, unit):
        best, best_d = None, min(unit.vision_range(),
                                 unit.stats['range'] * 1.6)
        night_blind = not self.is_day(unit.pos)   # vs the other domain
        unit_air = unit.is_air()
        for other in self.units:
            if not other.alive or other.country == unit.country \
                    or other.carried_by or self.is_embarked(other):
                continue
            if not unit.can_target(other.stats['domain']):
                continue
            if night_blind and other.is_air() != unit_air:
                continue        # night: air and surface can't spot
                                # each other
            d = unit.dist_to(other.pos)
            if d < best_d:
                best, best_d = other, d
        return best

    def resolve_shot(self, attacker, target):
        dmg = attacker.stats['damage'] * random.uniform(0.75, 1.25)
        # bunkered infantry shrug off bombs and naval shellfire
        if (isinstance(target, Unit) and target.unit_type == 'infantry'
                and attacker.stats['domain'] in ('air', 'sea')):
            for b in self.bunkers:
                if (b.country == target.country
                        and target.dist_to(b.pos) < BUNKER_RADIUS):
                    dmg *= 0.33
                    break
        # ammunition is supply too
        if attacker.stats['supply_cap'] > 0:
            attacker.supply = max(
                0.0, attacker.supply -
                attacker.stats['damage'] * FIRE_SUPPLY_FACTOR)
        target.take_damage(dmg, attacker)
        self._spawn_tracer(attacker, target)
        self.spawn_hit_flash(target.pos)
        if random.random() < 0.4:
            self.spawn_hit_flash(target.pos)

    TRACER_SPEED = 0.9          # world units/sec (slow enough to read)
    TRACER_LEN = 0.03           # a short round in flight

    def _spawn_tracer(self, attacker, target):
        """A short round that travels from the shooter to its target, so
        you can read who is firing at whom."""
        dist = attacker.dist_to(target.pos)
        if dist < 1e-4:
            return
        root = self.render.attachNewNode('tracer')
        orient_to_surface(root, attacker.pos)
        holder = root.attachNewNode('h')
        holder.setPos(0, 0, GLOBE_RADIUS * LIFT_FX)
        # heading toward the target
        d = Vec3(target.pos) - attacker.pos * attacker.pos.dot(target.pos)
        n = north_tangent(attacker.pos)
        e = n.cross(attacker.pos)
        if d.lengthSquared() > 1e-12:
            heading = math.degrees(math.atan2(d.dot(e), d.dot(n)))
            holder.setH(-heading)
        segs = LineSegs()
        segs.setThickness(2.0)
        segs.setColor(1.0, 0.85, 0.4, 0.95)
        segs.moveTo(0, 0, 0)
        segs.drawTo(0, self.TRACER_LEN, 0)
        line = holder.attachNewNode(segs.create())
        line.setLightOff()
        set_marker_layer(line, LAYER_FLASH - 1)
        flight_t = dist / self.TRACER_SPEED
        self.tracers.append([root, 0.0, flight_t,
                             Vec3(attacker.pos), Vec3(target.pos)])

    def _tick_tracers(self, dt):
        from utils import slerp
        keep = []
        for entry in self.tracers:
            entry[1] += dt * self.game_speed
            t = entry[1] / entry[2]
            if t >= 1.0:
                entry[0].removeNode()
                continue
            p = slerp(entry[3], entry[4], t)
            orient_to_surface(entry[0], p)
            keep.append(entry)
        self.tracers = keep

    def spawn_hit_flash(self, pos_vec):
        """Red ring that expands and dies — the crack of enemy fire."""
        if len(self.flashes) >= MAX_HIT_FLASHES:
            return
        self.flash_total += 1
        # tight on the victim: the strike must read unambiguously
        jitter = Vec3(random.uniform(-1, 1), random.uniform(-1, 1),
                      random.uniform(-1, 1)) * \
            (UNIT_SPRITE_SCALE * 0.4 / GLOBE_RADIUS)
        p = Vec3(pos_vec) + jitter
        p.normalize()
        root = self.render.attachNewNode('flash')
        orient_to_surface(root, p)
        holder = root.attachNewNode('holder')
        holder.setPos(0, 0, GLOBE_RADIUS * LIFT_FX)
        self.hit_template.copyTo(holder)
        holder.setScale(UNIT_SPRITE_SCALE * 0.4)
        self.flashes.append([root, holder, 0.0])

    def _tick_flashes(self, dt):
        if not self.flashes:
            return
        keep = []
        base = UNIT_SPRITE_SCALE
        for entry in self.flashes:
            entry[2] += dt
            t = entry[2] / HIT_FLASH_TIME
            if t >= 1.0:
                entry[0].removeNode()
                continue
            # grows to about unit-sprite size, no bigger
            entry[1].setScale(base * (0.4 + t * 0.7))
            entry[1].setAlphaScale(1.0 - t)
            keep.append(entry)
        self.flashes = keep

    def unit_destroyed(self, unit, attacker):
        was_embarked_on = unit.based_at if self.is_parked(unit) else None
        unit.destroy()
        if unit in self.selected:
            self.selected.remove(unit)
            self._refresh_selection_ui()
        if was_embarked_on is not None:
            self._refresh_air_base(was_embarked_on)
        if unit.unit_type == 'aircraft_carrier':
            # aircraft on her deck go down with the ship
            for u in list(self.units):
                if u.alive and u.based_at is unit:
                    self.unit_destroyed(u, attacker)
        if unit.country == self.player_country:
            self.losses += 1
            if unit.stats.get('comm') or unit.unit_type == 'aircraft_carrier':
                self.fax.post(
                    "GRAVE LOSS",
                    "%s destroyed. The %s net is degraded in that "
                    "sector." % (B(unit.stats['label']), B("W/T")),
                    sender="CASUALTY BRANCH")
        elif attacker is not None and getattr(attacker, 'country', None) \
                == self.player_country:
            self.kills += 1

    @staticmethod
    def _grid_ref(lat, lon):
        return "%.1f%s %.1f%s" % (abs(lat), 'N' if lat >= 0 else 'S',
                                  abs(lon), 'E' if lon >= 0 else 'W')

    def on_airfield_destroyed(self, field, attacker):
        """The field is cratered: everything on the ground goes with it."""
        for u in list(self.units):
            if u.alive and u.based_at is field:
                self.unit_destroyed(u, attacker)
        if self.selected_airfield is field:
            self._select_airfield(None)
        if field in self.airfields:
            self.airfields.remove(field)
        field.cleanup()
        self.fax.post(
            "AIRFIELD DESTROYED",
            "%s has been %s. Aircraft on the ground are lost." %
            (B(field.name), B("CRATERED AND BURNT")),
            sender="FIELD COMMAND")
        self._cancel_air_production(field.country)

    def _cancel_air_production(self, country):
        """No airfields, no aircraft: if a nation can no longer base
        aircraft anywhere, scrap and refund any still on the works
        lists rather than delivering them onto open ground."""
        if self.airfields_of(country):
            return
        refunded = 0
        n = 0
        for city in self.cities:
            if city.country != country:
                continue
            kept = []
            for entry in city.production:
                if UNIT_TYPES[entry[0]]['domain'] == 'air':
                    refunded += stats_for(entry[0], country)['cost']
                    n += 1
                else:
                    kept.append(entry)
            city.production = kept
        if n:
            self.funds[country] += refunded
            if country == self.player_country:
                self.fax.post(
                    "AIR PROGRAMME SUSPENDED",
                    "%s remain. %d aircraft struck from the works "
                    "lists; $%d refunded to the treasury." %
                    (B("NO AIRFIELDS"), n, refunded),
                    sender="AIR MINISTRY")

    def on_bridge_destroyed(self, bridge, attacker):
        if self.planner:
            self.planner.notify_bridge_change()
        self.fax.post(
            "BRIDGE DOWN",
            "Span demolished at %s. Land traffic must detour." %
            B(self._grid_ref(bridge.lat, bridge.lon)),
            sender="MOVEMENT CONTROL")

    def on_bridge_repaired(self, bridge):
        if self.planner:
            self.planner.notify_bridge_change()
        self.fax.post(
            "SPAN RESTORED",
            "Bridge at %s fit for traffic again." %
            B(self._grid_ref(bridge.lat, bridge.lon)),
            sender="ENGINEER CORPS")

    # =============================================== engineering works
    # works are paid for in SUPPLY from the engineer's own stores --
    # the treasury never sees an engineering bill
    BUILD_WORKS = {
        'bridge':   ('BRIDGE', 250, 30.0),
        'road':     ('ROAD', 300, 40.0),
        'depot':    ('SUPPLY DEPOT', 300, 25.0),
        'bunker':   ('BUNKER', 250, 18.0),
        'airfield': ('AIRFIELD', 500, 45.0),
        'harbor':   ('HARBOUR', 500, 45.0),
    }

    def _build_engineer(self):
        return next((u for u in self.selected
                     if u.stats.get('engineer')), None)

    def begin_build_mode(self, kind):
        label, cost, _t = self.BUILD_WORKS[kind]
        eng = self._build_engineer()
        if eng is None:
            return
        if eng.supply < cost:
            self.fax.post("WORKS REFUSED",
                          "The company's stores cannot cover the %s "
                          "(%s). Bring a supply column forward." %
                          (label, B("%d LBS" % cost)),
                          sender="ENGINEER CORPS")
            return
        self.build_mode = kind
        self.fax_short("SITE THE %s: RIGHT-CLICK THE MAP -- ESC CANCELS"
                       % label)

    def _order_build(self, ground, shift=False):
        """RMB while a works order is armed: site it.  Roads collect
        shift-clicked waypoints first (yellow survey line), the plain
        click commits the whole route."""
        kind = self.build_mode
        engineers = [u for u in self.selected if u.stats.get('engineer')]
        if not engineers:
            self.build_mode = None
            self._clear_road_plan()
            return
        eng = engineers[0]
        lat, lon = vec_to_latlon(ground)
        label, cost, build_time = self.BUILD_WORKS[kind]
        if kind == 'harbor':
            # the quay goes ON the water, just off the shore
            if self.world.is_land(lat, lon):
                lat, lon = self.world.nearest_water(lat, lon, max_deg=1.0)
            ground = latlon_to_vec(lat, lon)
            if self.world.is_land(lat, lon):
                self.fax.post("WORKS REFUSED",
                              "%s -- a harbour wants open water." %
                              B("NO ANCHORAGE AT THAT SITE"),
                              sender="ENGINEER CORPS")
                self.build_mode = None
                return
        elif kind != 'bridge' and self.world.is_water(lat, lon):
            lat, lon = self.world.nearest_land(lat, lon)
            ground = latlon_to_vec(lat, lon)

        if kind == 'road':
            self.road_plan.append(Vec3(ground))
            self._draw_road_plan(eng)
            if shift:
                self.fax_short("SURVEY POINT %d SET -- CLICK TO ADD, "
                               "PLAIN CLICK COMMITS" % len(self.road_plan))
                return                  # stay in build mode, keep adding
            points = list(self.road_plan)
            self.build_mode = None
            self._clear_road_plan()
            n_legs = len(points)
            total_cost = cost + 100 * (n_legs - 1)
            if eng.supply < total_cost:
                self.fax.post("WORKS REFUSED",
                              "Stores cannot cover the survey (%s)." %
                              B("%d LBS" % total_cost),
                              sender="ENGINEER CORPS")
                return
            eng.supply -= total_cost
            eng.give_order({'kind': 'build', 'what': 'road',
                            'site': Vec3(points[0]),
                            'points': points, 'from': Vec3(eng.pos),
                            't': build_time + 20.0 * (n_legs - 1),
                            'cost': total_cost})
            self.fax_short("ROAD UNDER CONSTRUCTION -- %d LEG(S)"
                           % n_legs)
            return

        self.build_mode = None
        if kind == 'bridge':
            near_river = any(
                min(latlon_dist_deg((lon, lat), seg[0]),
                    latlon_dist_deg((lon, lat), seg[1])) < 1.2
                for seg in self.world.river_segments_near(lon, lat))
            if not near_river:
                self.fax.post("WORKS REFUSED",
                              "%s -- a bridge wants a river." %
                              B("NO CROSSING AT THAT SITE"),
                              sender="ENGINEER CORPS")
                return
        if eng.supply < cost:
            return
        eng.supply -= cost
        eng.give_order({'kind': 'build', 'what': kind,
                        'site': Vec3(ground), 'from': Vec3(eng.pos),
                        't': build_time, 'cost': cost})
        self.fax_short("%s UNDER CONSTRUCTION -- ENGINEERS EN ROUTE"
                       % label)

    def _draw_road_plan(self, eng):
        """Yellow survey line: engineer through the planned waypoints."""
        from utils import slerp
        if self.road_preview:
            self.road_preview.removeNode()
            self.road_preview = None
        pts = [Vec3(eng.pos)] + self.road_plan
        segs = LineSegs()
        segs.setThickness(2.2)
        segs.setColor(1.0, 0.85, 0.2, 0.9)      # surveyor's yellow
        lift = GLOBE_RADIUS * LIFT_PATH
        segs.moveTo(pts[0] * lift)
        for a, b in zip(pts[:-1], pts[1:]):
            n = max(1, int(angle_between(a, b) * GLOBE_RADIUS / 0.3))
            for k in range(1, n + 1):
                segs.drawTo(slerp(a, b, k / n) * lift)
        self.road_preview = self.render.attachNewNode(segs.create())
        self.road_preview.setLightOff()
        self.road_preview.setDepthOffset(4)

    def _clear_road_plan(self):
        self.road_plan = []
        if self.road_preview:
            self.road_preview.removeNode()
            self.road_preview = None

    def _complete_build(self, eng, order):
        kind = order['what']
        site = order['site']
        lat, lon = vec_to_latlon(site)
        label = self.BUILD_WORKS[kind][0]
        country = eng.country
        if kind == 'depot':
            self.depots.append(Depot(self, lat, lon, country,
                                     "DEPOT %d" % (len(self.depots) + 1)))
        elif kind == 'bunker':
            self.bunkers.append(Bunker(self, lat, lon, country,
                                       "BUNKER %d" % (len(self.bunkers) + 1)))
        elif kind == 'airfield':
            field = Airfield(self, lat, lon, country,
                             "FIELD %d" % (len(self.airfields) + 1))
            field.stock = 0.0           # bring supplies by truck
            self.airfields.append(field)
        elif kind == 'harbor':
            self.harbors.append(
                Harbor(self, lat, lon, country,
                       "HARBOUR %d" % (len(self.harbors) + 1)))
        elif kind == 'bridge':
            self.bridges.append(Bridge(self, {'lat': lat, 'lon': lon,
                                              'road': (-1, -1)},
                                       len(self.bridges)))
            self.planner.notify_bridge_change()
        elif kind == 'road':
            pts = order.get('points') or [site]
            chain = [order['from']] + list(pts)
            for a, b in zip(chain[:-1], chain[1:]):
                self.planner.add_custom_road(a, b)
                self._draw_custom_road(a, b)
        self._apply_marker_scale()
        if country == self.player_country:
            self.fax.post("WORKS COMPLETE",
                          "%s ready at %s." %
                          (B(label), self._grid_ref(lat, lon)),
                          sender="ENGINEER CORPS")

    def _draw_custom_road(self, a, b):
        segs = LineSegs()
        segs.setThickness(2.5)
        segs.setColor(0.48, 0.38, 0.24, 1.0)
        from utils import slerp
        n = max(2, int(angle_between(a, b) * GLOBE_RADIUS / 0.2))
        for i in range(n + 1):
            p = slerp(a, b, i / n) * (GLOBE_RADIUS * LIFT_GROUND)
            if i == 0:
                segs.moveTo(p)
            else:
                segs.drawTo(p)
        np_ = self.render.attachNewNode(segs.create())
        np_.setLightOff()
        self.custom_roads.append(np_)

    # ====================================================== logistics
    def _tick_supply(self):
        """Once per second: sources fill, carriers distribute, the
        starving get flagged.  Logistics wins wars."""
        units = self.units

        # 1) cities are bottomless sources for anything nearby
        for u in units:
            if (not u.alive or u.carried_by
                    or u.stats['supply_cap'] <= 0
                    or u.supply >= u.stats['supply_cap']):
                continue
            for c in self.cities:
                if c.country == u.country and u.dist_to(c.pos) < 0.6:
                    u.supply = u.stats['supply_cap']
                    break

        # city-side airfields refill from their city; carriers at a
        # friendly harbor take on aviation stock
        for a in self.airfields:
            if a.city is not None and a.city.country == a.country:
                a.stock = AIRFIELD_STOCK_CAP
        for u in units:
            if u.alive and u.unit_type == 'aircraft_carrier':
                for c in self.cities:
                    if (c.country == u.country and c.harbor
                            and u.dist_to(c.pos) < 1.0):
                        u.av_stock = AIRFIELD_STOCK_CAP
                        break

        # 2) depots: trucks exchange with them, nearby units draw
        for d in self.depots:
            for u in units:
                if not u.alive or u.carried_by or u.country != d.country:
                    continue
                if u.dist_to(d.pos) > 0.5:
                    continue
                cap = u.stats['supply_cap']
                if cap <= 0:
                    continue
                if (u.stats.get('supply_carrier')
                        and u.stats['domain'] == 'land'):
                    if u.supply > cap * 0.6 and d.stock < DEPOT_STOCK_CAP:
                        move = min(u.supply - cap * 0.5,
                                   DEPOT_STOCK_CAP - d.stock)
                        u.supply -= move
                        d.stock += move
                    elif u.supply < cap * 0.3 and d.stock > 0:
                        move = min(cap - u.supply, d.stock)
                        u.supply += move
                        d.stock -= move
                elif d.stock > 0 and u.supply < cap:
                    move = min(cap - u.supply, d.stock)
                    u.supply += move
                    d.stock -= move

        # 3) supply carriers push to everything inside their vision
        for src in units:
            if (not src.alive or src.carried_by
                    or not src.stats.get('supply_carrier')
                    or src.supply <= 0):
                continue
            rng = max(src.vision_range(), SUPPLY_TRANSFER_RANGE)
            src_sea = src.stats['domain'] == 'sea'
            for u in units:
                if (u is src or not u.alive or u.carried_by
                        or u.country != src.country
                        or u.stats['supply_cap'] <= 0):
                    continue
                if u.stats.get('supply_carrier') and not src_sea:
                    continue        # trucks don't top up other trucks
                if not src_sea and u.stats['domain'] == 'sea':
                    continue        # ships resupply at sea, not from shore
                if src.supply <= 0:
                    break
                if u.dist_to(src.pos) > rng:
                    continue
                need = u.stats['supply_cap'] - u.supply
                if need <= 0:
                    continue
                move = min(need, src.supply)
                u.supply += move
                src.supply -= move
            # aviation stock: trucks feed airfields, ships feed carriers
            if src.supply > 0:
                if src_sea:
                    for u in units:
                        if (u.alive and u.country == src.country
                                and u.unit_type == 'aircraft_carrier'
                                and u.dist_to(src.pos) <= rng
                                and u.av_stock < AIRFIELD_STOCK_CAP):
                            move = min(AIRFIELD_STOCK_CAP - u.av_stock,
                                       src.supply)
                            u.av_stock += move
                            src.supply -= move
                else:
                    for a in self.airfields:
                        if (a.country == src.country
                                and a.stock < AIRFIELD_STOCK_CAP
                                and angle_between(a.pos, src.pos) *
                                GLOBE_RADIUS <= rng):
                            move = min(AIRFIELD_STOCK_CAP - a.stock,
                                       src.supply)
                            a.stock += move
                            src.supply -= move

        # 4) starving units get the red jerrycan
        for u in units:
            if u.alive:
                u.set_nosupply_flag(u.stats['supply_cap'] > 0
                                    and u.supply <= 0)

        # 5) idle supply carriers run their loops automatically
        for u in units:
            if (u.alive and not u.carried_by
                    and u.stats.get('supply_carrier')):
                self._auto_shuttle(u)

    def _auto_shuttle(self, truck):
        """Empty: fetch more.  Full: return to station or find the
        neediest friend.  Player orders always override."""
        if truck.current_order or truck.order_queue or truck.plan_pending:
            return
        # if a recent auto-route failed, wait out the backoff before we
        # try again — otherwise a stranded truck loops forever
        if globalClock.getFrameTime() < getattr(truck,
                                                '_route_fail_until', 0.0):
            return
        cap = truck.stats['supply_cap']
        frac = truck.supply / cap
        if frac < 0.15:
            sources = [c for c in self.cities
                       if c.country == truck.country]
            sources += [d for d in self.depots
                        if d.country == truck.country and d.stock > 2000]
            if truck.stats['domain'] == 'sea':
                sources = [c for c in self.cities
                           if c.country == truck.country and c.harbor]
            if sources:
                src = min(sources, key=lambda s: truck.dist_to(s.pos))
                truck.give_order({'kind': 'move', 'goal': Vec3(src.pos),
                                  'auto': True})
        elif frac > 0.6:
            if truck.station is not None:
                if truck.dist_to(truck.station) > 0.8:
                    truck.give_order({'kind': 'move',
                                      'goal': Vec3(truck.station),
                                      'auto': True})
            else:
                same_sea = truck.stats['domain'] == 'sea'
                needy = [u for u in self.units
                         if u.alive and u.country == truck.country
                         and not u.carried_by
                         and u.stats['supply_cap'] > 0
                         and not u.stats.get('supply_carrier')
                         and u.supply < u.stats['supply_cap'] * 0.5
                         and (u.stats['domain'] == 'sea') == same_sea]
                if needy:
                    tgt = min(needy, key=lambda u: truck.dist_to(u.pos))
                    if truck.dist_to(tgt.pos) > truck.vision_range():
                        truck.give_order({'kind': 'move',
                                          'goal': Vec3(tgt.pos),
                                          'auto': True})

    # ====================================================== economy
    def _tick_production(self, dt):
        for city in self.cities:
            if not city.production:
                continue
            city.production[0][1] -= dt * self.game_speed
            if city.production[0][1] <= 0:
                unit_type, _ = city.production.pop(0)
                # no airfield to receive a finished aircraft: refund it
                # rather than delivering it onto open ground
                if (UNIT_TYPES[unit_type]['domain'] == 'air'
                        and not self.airfields_of(city.country)):
                    self.funds[city.country] += \
                        stats_for(unit_type, city.country)['cost']
                    continue
                # new hulls go to the fleet yard and wait for LAUNCH
                # (the player's one-way launching ceremony; AI powers
                # put theirs straight into the water)
                if UNIT_TYPES[unit_type]['domain'] == 'sea':
                    h = self.harbor_of_city(city)
                    if h is not None:
                        if city.country == self.player_country:
                            h.ready.append(unit_type)
                            h.set_count(len(h.ready))
                            self.fortnight_delivered[unit_type] = \
                                self.fortnight_delivered.get(unit_type,
                                                             0) + 1
                            lbl = stats_for(unit_type,
                                            city.country)['label']
                            self.fax_short("%s READY FOR LAUNCH AT %s" %
                                           (lbl.upper(), h.name))
                            if self.selected_harbor is h:
                                self._refresh_harbor_ui(h)
                        else:
                            self.spawn_unit(unit_type, city.country,
                                            h.lat, h.lon, jitter=0.2,
                                            seed=random.randrange(9999),
                                            water=True)
                        continue
                u = self.spawn_unit(unit_type, city.country, city.lat,
                                    city.lon, jitter=0.7,
                                    seed=random.randrange(9999),
                                    base=self.airfield_of_city(city))
                if city.country == self.player_country:
                    self.fortnight_delivered[unit_type] = \
                        self.fortnight_delivered.get(unit_type, 0) + 1
                    self.fax_short("%s REPORTING FOR DUTY AT %s" %
                                   (u.stats['label'].upper(),
                                    city.name.upper()))

    # ====================================================== capture
    def _capture_garrison(self, city, country):
        """The infantry a power has standing on the city."""
        return [u for u in self.units
                if u.alive and u.country == country
                and u.unit_type == 'infantry' and not u.carried_by
                and u.dist_to(city.pos) < CITY_CAPTURE_RANGE]

    def attempt_capture(self, city, country):
        """Annex a city: costs one infantry division per million souls
        (the cost of control -- they garrison it and leave the order of
        battle). The city cannot be taxed until the next fortnight."""
        if city.country == country or not self.units:
            return False
        garrison = self._capture_garrison(city, country)
        need = city.required_infantry()
        if len(garrison) < need:
            return False
        for u in garrison[:need]:
            u.alive = False
            if u in self.selected:
                self._deselect_unit(u)
            u.cleanup()
            if u in self.units:
                self.units.remove(u)
        self._capture_city(city, country)
        return True

    def _tick_capture(self, dt):
        # AI powers annex automatically under the same infantry rule;
        # the player uses the CAPTURE button on the city's menu
        for city in self.cities:
            for country in COUNTRIES:
                if (country == city.country or country in self.eliminated
                        or country == self.player_country
                        or country == 'neutral'):
                    continue
                if len(self._capture_garrison(city, country)) \
                        >= city.required_infantry():
                    self.attempt_capture(city, country)
                    break

        # standalone (engineer-built) airfields fall to whoever holds
        # the ground
        for a in self.airfields:
            if a.city is not None:
                continue
            occupier = None
            defended = False
            for u in self.units:
                if not u.alive or u.stats['domain'] != 'land' \
                        or u.carried_by:
                    continue
                if u.dist_to(a.pos) < CITY_CAPTURE_RANGE:
                    if u.country == a.country:
                        defended = True
                        break
                    occupier = u.country
            if occupier and not defended:
                old = a.country
                for p in list(self.units):
                    if p.alive and p.based_at is a and p.country == old:
                        self.unit_destroyed(p, None)
                a.country = occupier
                a.refresh_marker()
                if self.player_country in (old, occupier):
                    self.fax.post("AIRFIELD TAKEN",
                                  "%s now flies %s colours." %
                                  (B(a.name),
                                   B(COUNTRIES[occupier]['adjective'])),
                                  sender="FIELD COMMAND")

    def _capture_city(self, city, new_owner):
        old = city.country
        city.country = new_owner
        city.capture_progress = 0.0
        city.capturing_country = None
        city.annexing = True        # taxable from the NEXT fortnight
        city.pending_tax = None
        city.tax_rate = TAX_DEFAULT
        city.production = []
        city.refresh_marker()
        self._update_borders()
        self._ai_overseas_cache.clear()
        # the city's airfield changes hands; aircraft caught on the
        # ground are lost
        hb = self.harbor_of_city(city)
        if hb is not None:
            hb.country = new_owner
            hb.ready = []
            hb.set_count(0)
            hb.refresh_marker()
        field = self.airfield_of_city(city)
        if field is not None:
            for u in list(self.units):
                if u.alive and u.based_at is field and u.country == old:
                    self.unit_destroyed(u, None)
            field.country = new_owner
            field.refresh_marker()
            self._refresh_air_base(field)
            self._cancel_air_production(old)   # old owner may be fieldless
        if new_owner == self.player_country:
            self.fax.post("CITY TAKEN",
                          "Colours raised over %s. Annexation is in "
                          "progress -- its taxes flow from the next "
                          "fortnight." % B(city.name),
                          sender="FIELD COMMAND")
        elif old == self.player_country:
            self.fax.post("CITY LOST",
                          "%s has fallen to %s forces." %
                          (B(city.name),
                           B(COUNTRIES[new_owner]['adjective'])),
                          sender="FIELD COMMAND")
        self._check_victory()

    def _check_victory(self):
        if self.game_over:
            return
        for country in COUNTRIES:
            if country in self.eliminated or country == 'neutral':
                continue
            if not any(c.country == country for c in self.cities):
                self.eliminated.add(country)
                self.fax.post(
                    "INSTRUMENT OF SURRENDER",
                    "%s has capitulated. Its forces lay down their "
                    "arms." % B(COUNTRIES[country]['name']),
                    sender="SUPREME HQ")
                for u in self.units:
                    if u.alive and u.country == country:
                        self.unit_destroyed(u, None)
        if self.player_country in self.eliminated:
            self.game_over = True
            self.fax.post("DEFEAT",
                          "The government has %s. The war is over -- "
                          "press %s for headquarters." %
                          (B("SURRENDERED"), B("ESC")),
                          sender="SUPREME HQ")
        elif all(c in self.eliminated or c == self.player_country
                 or c == 'neutral' for c in COUNTRIES):
            self.game_over = True
            self.fax.post("TOTAL VICTORY",
                          "%s. Church bells ring at home -- press %s "
                          "for headquarters." %
                          (B("ALL ENEMY POWERS HAVE CAPITULATED"),
                           B("ESC")),
                          sender="SUPREME HQ")

    # =========================================== vision & communications
    def _tick_vision_comm(self):
        """One pass: who is on the wireless net, and who can see whom."""
        player = self.player_country

        # communication sources: command units' circles + city land lines
        comm_sources = [(c.pos, CITY_COMM_RADIUS) for c in self.cities
                        if c.country == player]
        for u in self.units:
            if (u.alive and u.country == player and not u.carried_by
                    and u.stats.get('comm')):
                comm_sources.append((u.pos, u.comm_range()))
        # the map draws one merged outline around the whole wireless net
        if self.globe:
            self.globe.set_comm(comm_sources)

        # contact status for player units
        out = 0
        changed_selection = False
        for u in self.units:
            if not u.alive or u.country != player or u.carried_by:
                continue
            if self.is_embarked(u):
                u.in_contact = True     # the ship's W/T room reports
                continue
            if u.stats.get('comm'):
                in_c = True         # a command unit carries its own set
            else:
                in_c = False
                for (pos, rng) in comm_sources:
                    if angle_between(u.pos, pos) * GLOBE_RADIUS <= rng:
                        in_c = True
                        break
            if not in_c:
                out += 1
            if in_c != u.in_contact:
                u.in_contact = in_c
                if in_c:
                    u.root.show()
                else:
                    u.root.hide()
                    if u in self.selected:
                        self.selected.remove(u)
                        u.set_selected(False)
                        changed_selection = True
        self.out_of_contact = out
        if changed_selection:
            self._refresh_selection_ui()

        # enemy visibility: only in-contact eyes can report sightings
        # (embarked aircraft see nothing from below deck).  Each source
        # carries (pos, range, is_air, is_day): at night, air and
        # surface cannot spot each other.
        friendly = [(u.pos, u.vision_range(), u.is_air(),
                     self.is_day(u.pos))
                    for u in self.units
                    if u.alive and u.country == player and not u.carried_by
                    and u.in_contact and not self.is_embarked(u)]
        for c in self.cities:
            if c.country == player:
                day = self.is_day(c.pos)
                rng = CITY_VISION_RANGE * (1.0 if day
                                           else NIGHT_VISION_FACTOR)
                friendly.append((c.pos, rng, False, day))
        # remember the live sources: the fog shader is refreshed every
        # frame from them so circles glide with their units (the slow
        # membership pass stays on this tick)
        self._vision_units = [u for u in self.units
                              if u.alive and u.country == player
                              and not u.carried_by and u.in_contact
                              and not self.is_parked(u)]
        self._vision_cities = [c for c in self.cities
                               if c.country == player]
        self._update_vision_shader()
        for u in self.units:
            if not u.alive or u.carried_by or u.country == player \
                    or self.is_embarked(u):
                if u.alive and u.country == player:
                    u.visible_to_player = u.in_contact
                continue
            target_air = u.is_air()
            visible = False
            for (pos, rng, src_air, src_day) in friendly:
                if not src_day and src_air != target_air:
                    continue        # night: air and surface see nothing
                                    # of each other
                if angle_between(u.pos, pos) * GLOBE_RADIUS <= rng:
                    visible = True
                    break
            if visible != u.visible_to_player:
                u.visible_to_player = visible
                if visible:
                    u.root.show()
                else:
                    u.root.hide()
                    if u in self.selected:      # intel view went dark
                        self._deselect_unit(u)
                        self._refresh_selection_ui()

    def _update_vision_shader(self):
        """Per-frame fog-circle refresh so vision moves with the units."""
        if not self.globe:
            return
        entries = [(u.pos, u.vision_range()) for u in self._vision_units
                   if u.alive]
        for c in self._vision_cities:
            day = self.is_day(c.pos)
            entries.append((c.pos, CITY_VISION_RANGE *
                            (1.0 if day else NIGHT_VISION_FACTOR)))
        self.globe.set_vision(entries)

    # ====================================================== AI
    AI_ARMY_MIX = ['infantry', 'infantry', 'tank', 'tank', 'aa_artillery',
                   'engineer', 'supply_truck', 'supply_truck']
    AI_AIR_MIX = ['fighter', 'bomber', 'bomber']

    def _tick_ai(self, dt):
        for country, timers in self._ai_timers.items():
            if country in self.eliminated:
                continue
            timers['think'] -= dt * self.game_speed
            timers['wave'] -= dt * self.game_speed
            if timers['think'] <= 0:
                timers['think'] = AI_THINK_INTERVAL * random.uniform(.7, 1.3)
                self._ai_buy(country)
            if timers['wave'] <= 0:
                timers['wave'] = AI_WAVE_INTERVAL * random.uniform(.7, 1.3)
                self._ai_launch_wave(country)

    def _ai_buy(self, country):
        cities = [c for c in self.cities if c.country == country]
        if not cities:
            return
        overseas = self._ai_overseas(country)
        pool = self.AI_AIR_MIX if (overseas and random.random() < 0.6) \
            else self.AI_ARMY_MIX + self.AI_AIR_MIX
        unit_type = random.choice(pool)
        city = random.choice(cities)
        if unit_type in self.AI_AIR_MIX and not city.capital:
            city = next((c for c in cities if c.capital), city)
            if not city.capital:
                unit_type = random.choice(self.AI_ARMY_MIX)
        cost = stats_for(unit_type, country)['cost']
        if self.funds[country] >= cost:
            self.funds[country] -= cost
            self.queue_production(city, unit_type)

    def _ai_overseas(self, country):
        """Cached — geography only changes when cities change hands."""
        if country in self._ai_overseas_cache:
            return self._ai_overseas_cache[country]
        my_cap = self.capital_of(country)
        overseas = True
        for other in COUNTRIES:
            if other == country or other in self.eliminated:
                continue
            their = [c for c in self.cities if c.country == other]
            if not their:
                continue
            path = self.planner.plan_land(my_cap.pos, their[0].pos)
            if path is not None:
                overseas = False
                break
        self._ai_overseas_cache[country] = overseas
        return overseas

    def _ai_launch_wave(self, country):
        idle = [u for u in self.units
                if u.alive and u.country == country and not u.order_queue
                and not u.current_order and u.stats['damage'] > 0
                and (u.stats['domain'] != 'air' or u.based_at is not None)]
        if len(idle) < 3:
            return
        targets = [c for c in self.cities if c.country != country
                   and c.country not in self.eliminated]
        if not targets:
            return
        my_cap = self.capital_of(country)
        targets.sort(key=lambda c: angle_between(my_cap.pos, c.pos))
        target = targets[0]
        for u in idle:
            if u.stats['domain'] == 'land':
                if random.random() < 0.5:
                    continue
            # queue instead of ordering now: route planning is spread
            # over the next frames so a wave never stalls a frame
            self._pending_ai_orders.append(
                (u, {'kind': 'move', 'goal': Vec3(target.pos)}))

    # ====================================================== camera
    def _tick_camera(self, dt):
        mw = self.mouseWatcherNode
        if mw is None:
            self._update_camera_transform(dt)
            return
        alt = self.cam_dist - GLOBE_RADIUS
        rot_speed = max(1.0, min(55.0, alt * 3.3))

        def down(pair):
            return mw.isButtonDown(pair[0]) or mw.isButtonDown(pair[1])

        dlat = dlon = 0.0
        if down(self._key_up):
            dlat += rot_speed * dt
        if down(self._key_down):
            dlat -= rot_speed * dt
        if down(self._key_left):
            dlon -= rot_speed * dt
        if down(self._key_right):
            dlon += rot_speed * dt

        if self.mmb_down and mw.hasMouse():
            mpos = Point2(mw.getMouse())
            if self.last_mouse is not None:
                delta = mpos - self.last_mouse
                drag = max(1.0, alt * 1.5)
                dlon -= delta.x * drag
                dlat -= delta.y * drag
            self.last_mouse = mpos
        else:
            self.last_mouse = None

        if dlat or dlon:
            # direct steering moves camera and target together (no lag)
            self.cam_lat += dlat
            self.cam_lon += dlon
            self.cam_lat_target += dlat
            self.cam_lon_target += dlon

        self._update_camera_transform(dt)

    def _update_camera_transform(self, dt):
        # chase the targets smoothly (zoom pans glide, never jump)
        k = min(1.0, dt * 8.0)
        self.cam_lat_target = max(-85.0, min(85.0, self.cam_lat_target))
        dlon = (self.cam_lon_target - self.cam_lon + 180.0) % 360.0 - 180.0
        self.cam_lat += (self.cam_lat_target - self.cam_lat) * k
        self.cam_lon += dlon * k
        self.cam_lat = max(-85.0, min(85.0, self.cam_lat))
        self.cam_lon = (self.cam_lon + 180.0) % 360.0 - 180.0
        self.cam_dist += (self.cam_dist_target - self.cam_dist) * \
            min(1.0, dt * 8.0)
        pos = latlon_to_vec(self.cam_lat, self.cam_lon) * self.cam_dist
        self.camera.setPos(pos)
        self.camera.lookAt(Point3(0, 0, 0), Vec3(0, 0, 1))

        if self.globe:
            self.globe.set_labels_visible(self.cam_dist > CAM_ZOOM_LABELS)
            self.globe.detail.update(self.cam_lat, self.cam_lon,
                                     self.cam_dist, self.sun_direction())


        # rescale flat markers only when the zoom has actually changed
        if (self._scale_ref_dist == 0.0 or
                abs(self.cam_dist - self._scale_ref_dist) >
                self._scale_ref_dist * 0.03):
            self._scale_ref_dist = self.cam_dist
            self._apply_marker_scale()

    def _apply_marker_scale(self):
        alt = self.cam_dist - GLOBE_RADIUS
        self.marker_scale = max(0.008, min(0.72, alt * 0.0115))
        city_scale = self.marker_scale * 0.32
        # units, structures and city names all keep fixed map sizes;
        # only the city selection rings scale to stay clickable
        for c in self.cities:
            c.set_marker_scale(city_scale)
        # LOD: at strategic altitudes the fixed-size structure markers
        # are sub-pixel -- hide them (and their billboard math) outright
        show = alt < 26.0
        if show != getattr(self, '_structs_shown', True):
            self._structs_shown = show
            for group in (self.airfields, self.harbors, self.depots,
                          self.bunkers):
                for s in group:
                    if show:
                        s.root.show()
                    else:
                        s.root.hide()

    def on_zoom(self, direction):
        old_alt = self.cam_dist_target - GLOBE_RADIUS
        alt = max(CAM_MIN_DIST - GLOBE_RADIUS,
                  min(CAM_MAX_DIST - GLOBE_RADIUS,
                      old_alt * 1.18 ** direction))
        self.cam_dist_target = GLOBE_RADIUS + alt
        # zoom IN toward the cursor (Google-maps style); zooming OUT is a
        # plain zoom.  The pan adjusts the smoothed target so it glides.
        if (direction >= 0 or self.game_state != 'playing'
                or old_alt <= 0):
            return
        ground = self.mouse_ground_point()
        if ground is None:
            return
        t_lat, t_lon = vec_to_latlon(ground)
        ratio = alt / old_alt
        dlon = (self.cam_lon_target - t_lon + 180.0) % 360.0 - 180.0
        self.cam_lat_target = t_lat + (self.cam_lat_target - t_lat) * ratio
        self.cam_lon_target = t_lon + dlon * ratio

    def on_mmb(self, down):
        self.mmb_down = down
        self.last_mouse = None

    # ====================================================== HUD
    def _build_cursor(self):
        """The software pointer: a textured sprite that follows the mouse
        and swaps between wing-compass / attack / embark / disembark."""
        from panda3d.core import CardMaker, TransparencyAttrib
        from icons import get_icon_path
        for mode in ('default', 'attack', 'embark', 'disembark'):
            tex = self.loader.loadTexture(
                get_icon_path('cursor_' + mode, 'dark'))
            tex.setMinfilter(SamplerState.FTLinear)
            tex.setMagfilter(SamplerState.FTLinear)
            self.cursor_tex[mode] = tex
        cm = CardMaker('cursor')
        half = 0.025      # 50% smaller pointer
        cm.setFrame(-half, half, -half, half)
        cur = self.aspect2d.attachNewNode(cm.generate())
        cur.setTexture(self.cursor_tex['default'])
        cur.setTransparency(TransparencyAttrib.MAlpha)
        cur.setBin('gui-popup', 100)     # above every panel
        cur.setDepthTest(False)
        cur.setDepthWrite(False)
        cur.setLightOff()
        cur.hide()
        self.cursor = cur

    def _position_cursor(self):
        """Every frame: sit the cursor sprite on the real mouse. In
        default mode the OS pointer is used and the sprite stays hidden."""
        if self.cursor is None:
            return
        mw = self.mouseWatcherNode
        if (self.cursor_mode != 'default' and mw is not None
                and mw.hasMouse()):
            mp = mw.getMouse()
            self.cursor.setPos(mp.getX() * self.getAspectRatio(), 0,
                               mp.getY())
            if self.cursor.isHidden():
                self.cursor.show()
        elif not self.cursor.isHidden():
            self.cursor.hide()

    def _show_os_cursor(self, visible):
        try:
            from panda3d.core import WindowProperties
            wp = WindowProperties()
            wp.setCursorHidden(not visible)
            self.win.requestProperties(wp)
        except Exception:
            pass

    def _set_cursor_mode(self, mode):
        if self.cursor is not None and mode != self.cursor_mode:
            self.cursor_mode = mode
            if mode == 'default':
                self._show_os_cursor(True)
                self.cursor.hide()
            else:
                self._show_os_cursor(False)
                self.cursor.setTexture(self.cursor_tex[mode], 1)

    def _tick_cursor_mode(self):
        """Choose the cursor symbol from what is under the pointer."""
        mode = 'default'
        mw = self.mouseWatcherNode
        if (self.game_state == 'playing' and mw and mw.hasMouse()
                and not self.pause_frame and not self.budget_fax
                and not self.briefing_fax and not self.tax_fax):
            if self.unload_mode:
                mode = 'disembark'
            elif self.build_mode:
                mode = 'default'
            elif self.selected:
                mode = self._cursor_context(Point2(mw.getMouse()))
        self._set_cursor_mode(mode)

    def _cursor_context(self, mpos):
        # attack: a shooter is selected and a valid target is hovered
        shooters = [u for u in self.selected if u.stats['damage'] > 0
                    and not (u.stats['domain'] == 'air'
                             and u.based_at is None)]
        if shooters:
            cands = [(u, self._unit_world_pos(u)) for u in self.units
                     if u.alive and u.country != self.player_country
                     and u.visible_to_player and self._facing_camera(u.pos)]
            target = self._pick_object(mpos, cands)
            kind = target.stats['domain'] if target else None
            if target is None:
                bl = [(b, b.pos * GLOBE_RADIUS) for b in self.bridges
                      if b.alive and self._facing_camera(b.pos)]
                bl += [(a, a.pos * GLOBE_RADIUS) for a in self.airfields
                       if a.country != self.player_country
                       and self._facing_camera(a.pos)]
                target = self._pick_object(mpos, bl)
                kind = 'bridge'
            if target is not None and any(u.can_target(kind)
                                          for u in shooters):
                return 'attack'
        # embark: land units selected, hovering a transport (ship or a
        # parked air transport at an airfield)
        landers = [u for u in self.selected
                   if u.stats['domain'] == 'land'
                   and u.country == self.player_country
                   and not self.is_parked(u)]
        if landers:
            transports = [(u, self._unit_world_pos(u)) for u in self.units
                          if self._commandable(u) and u.stats.get('capacity')
                          and self._facing_camera(u.pos)]
            if self._pick_object(mpos, transports) is not None:
                return 'embark'
            fields = [(a, a.pos * GLOBE_RADIUS) for a in self.airfields
                      if a.country == self.player_country
                      and self._facing_camera(a.pos)]
            f = self._pick_object(mpos, fields)
            if f is not None and any(
                    p.stats.get('capacity') and
                    len(p.cargo) < p.stats['capacity']
                    for p in self.base_wing(f)):
                return 'embark'
        return 'default'

    def _tick_hover_glow(self):
        """Subtle ring on whatever unit the pointer rests over."""
        if self.hover_glow is None:
            self.hover_glow = make_flat_ring(
                'hover', 1.35, (1.0, 0.97, 0.75, 0.55),
                thickness=3.0, segments=28)
            set_marker_layer(self.hover_glow, LAYER_HOVER)
            self.hover_glow.detachNode()
        target = None
        mw = self.mouseWatcherNode
        if (self.game_state == 'playing' and mw and mw.hasMouse()
                and not self.pause_frame and not self.budget_fax):
            mpos = Point2(mw.getMouse())
            cands = [(u, self._unit_world_pos(u)) for u in self.units
                     if u.alive and not u.carried_by
                     and not self.is_parked(u)
                     and self._facing_camera(u.pos)
                     and (u.country == self.player_country
                          or u.visible_to_player)]
            target = self._pick_object(mpos, cands)
        if target is not None:
            self.hover_glow.reparentTo(target.holder)
            if self.hover_glow.isHidden():
                self.hover_glow.show()
        elif not self.hover_glow.isHidden():
            self.hover_glow.hide()
            self.hover_glow.detachNode()

    def _tick_drag_box(self):
        if self.mouseWatcherNode is None:
            return
        if self.drag_start is None or not self.mouseWatcherNode.hasMouse():
            self._remove_drag_box()
            return
        mpos = self.mouseWatcherNode.getMouse()
        if (Point2(mpos) - self.drag_start).length() < DRAG_THRESHOLD:
            return
        self._remove_drag_box()
        cm = CardMaker('dragbox')
        x0, x1 = sorted((self.drag_start.x, mpos.x))
        y0, y1 = sorted((self.drag_start.y, mpos.y))
        cm.setFrame(x0, x1, y0, y1)
        self.drag_box = self.render2d.attachNewNode(cm.generate())
        self.drag_box.setColor(0.4, 1.0, 0.4, 0.15)
        self.drag_box.setTransparency(True)

    def _remove_drag_box(self):
        if self.drag_box:
            self.drag_box.removeNode()
            self.drag_box = None

    def _tick_path_viz(self, dt):
        self._path_viz_timer -= dt
        if self._path_viz_timer > 0:
            return
        self._path_viz_timer = 0.4
        if self._path_viz:
            self._path_viz.removeNode()
            self._path_viz = None
        from utils import slerp
        segs = LineSegs()
        segs.setThickness(2.0)
        segs.setColor(0.25, 0.80, 1.0, 0.85)    # neon sky-blue
        lift = GLOBE_RADIUS * LIFT_PATH  # above the map, never under it
        joins = []                       # order waypoints (not path turns)
        drew = False
        for u in self.selected:
            if not u.alive or u.country != self.player_country:
                continue
            if not u.path and not u.order_queue:
                continue
            drew = True
            # follow the great circle of each leg so long paths hug the
            # planet instead of chording through it
            prev = Vec3(u.pos)
            segs.moveTo(prev * lift)

            def draw_leg(a, b):
                n = max(1, int(angle_between(a, b) * GLOBE_RADIUS / 0.4))
                for k in range(1, n + 1):
                    segs.drawTo(slerp(a, b, k / n) * lift)

            for (wp, _) in u.path:
                draw_leg(prev, wp)
                prev = Vec3(wp)
            if u.path:
                joins.append(Vec3(prev))     # current order's destination
            # queued (shift-linked) orders: follow each leg's own planned
            # route when it is ready, with a join ring at each waypoint
            for order in u.order_queue:
                goal = order.get('goal')
                if goal is None:
                    tgt = order.get('target')
                    goal = getattr(tgt, 'pos', None)
                if goal is None:
                    continue
                pre = order.get('pre_path')
                if pre:
                    for (wp, _) in pre:
                        draw_leg(prev, wp)
                        prev = Vec3(wp)
                else:
                    draw_leg(prev, goal)
                    prev = Vec3(goal)
                joins.append(Vec3(prev))
        # join rings: small fixed size (1/5 of the old ring)
        r = UNIT_SPRITE_SCALE * 0.16
        for jp in joins:
            for i in range(17):
                a = 2 * math.pi * i / 16
                east = north_tangent(jp).cross(jp)
                p = jp + (north_tangent(jp) * math.cos(a) +
                          east * math.sin(a)) * (r / GLOBE_RADIUS)
                p.normalize()
                if i == 0:
                    segs.moveTo(p * lift)
                else:
                    segs.drawTo(p * lift)
        if drew:
            self._path_viz = self.render.attachNewNode(segs.create())
            self._path_viz.setLightOff()
            self._path_viz.setDepthOffset(4)

    def fax_short(self, line):
        if self.bottom_bar:
            self.bottom_bar.set_info(line)

    def _refresh_selection_ui(self):
        if not self.bottom_bar:
            return
        bar = self.bottom_bar
        bar.clear_buttons()
        # briefing button: shown for any selection holding a friendly
        # unit, keyed to that unit's type
        bar.hide_info()
        bar.hide_capture()
        primary = next((u for u in self.selected
                        if u.country == self.player_country), None)
        if primary is not None:
            bar.show_info(self.open_unit_briefing, [primary.unit_type])
        if self.selected_airfield:
            self._refresh_airfield_ui(self.selected_airfield)
            return
        if self.selected_harbor:
            self._refresh_harbor_ui(self.selected_harbor)
            return
        if self.selected_city:
            city = self.selected_city
            tag = " (CAPITAL)" if city.capital else ""
            if city.annexing:
                tag += " [ANNEXING]"
            if city.country == self.player_country:
                bar.set_title("%s%s -- GARRISON COMMAND" %
                              (city.name.upper(), tag))
                self._set_city_info(city)
                if not city.annexing:
                    bar.add_buttons([
                        ("TAX DECREE", self.open_tax_fax, [city],
                         get_icon_path('tax_button', 'dark'))])
                    bar.set_hint("SET THE CITY'S TAX RATE -- IT BINDS "
                                 "FROM THE NEXT FORTNIGHT")
                else:
                    bar.set_hint("ANNEXATION IN PROGRESS -- ON THE TAX "
                                 "ROLLS NEXT FORTNIGHT")
            else:
                need = city.required_infantry()
                have = len(self._capture_garrison(city,
                                                  self.player_country))
                bar.set_title("%s%s -- %s CITY" %
                              (city.name.upper(), tag,
                               COUNTRIES[city.country]['adjective'].upper()))
                bar.set_info(
                    "POPULATION %s   %sCONTROLLED BY %s   "
                    "CAPTURE: %d/%d INFANTRY ON THE CITY" %
                    ("{:,}".format(city.population),
                     "PORT   " if city.harbor else "",
                     COUNTRIES[city.country]['name'].upper(),
                     have, need))
                if have >= need:
                    bar.show_capture(self._capture_clicked, [city])
                    bar.set_hint("THE GARRISON STANDS READY -- CAPTURING "
                                 "COSTS %d INFANTRY" % need)
                else:
                    bar.set_hint("MARCH %d INFANTRY ONTO THE CITY TO "
                                 "TAKE IT (1 PER MILLION SOULS)" % need)
            return
        if not self.selected:
            bar.set_title("ALL QUIET")
            bar.set_info("")
            bar.set_hint(CONTROLS_HINT)
            return
        # keep the airfield/carrier roster open while managing its
        # parked squadrons, so you can shift-click to add or remove
        if (self.roster_base is not None
                and getattr(self.roster_base, 'alive', False)
                and self.selected
                and all(self.is_parked(u) and u.based_at is self.roster_base
                        for u in self.selected)):
            self._refresh_air_roster(self.roster_base)
            return
        if len(self.selected) == 1:
            u = self.selected[0]
            if u.country != self.player_country:
                bar.set_title("%s -- ENEMY %s" %
                              (u.stats['label'].upper(),
                               BRANCH_OF[u.stats['domain']]))
                bar.set_info(
                    "INTELLIGENCE VIEW   STRENGTH %d/%d   SPEED %.0f MPH"
                    "   %s" %
                    (int(u.hp), u.max_hp, u.stats['speed'] * 60,
                     COUNTRIES[u.country]['name'].upper()))
                bar.set_hint("OBSERVATION ONLY -- THE ENEMY DOES NOT "
                             "TAKE OUR ORDERS")
                return
            if u.unit_type == 'aircraft_carrier':
                self._refresh_carrier_ui(u)
                return
            if u.stats.get('engineer'):
                self._refresh_engineer_ui(u)
                return
            if self.is_parked(u):
                base = u.based_at
                base_name = (getattr(base, 'name', None) or
                             base.stats['label']).upper()
                if u.stats.get('capacity'):
                    # a parked air transport: full lift-management menu
                    bar.set_title("%s -- LOADED %d/%d AT %s" %
                                  (u.stats['label'].upper(),
                                   len(u.cargo), u.stats['capacity'],
                                   base_name))
                    bar.set_info(
                        "STRENGTH %d/%d   ENDURANCE %.0f MI   "
                        "BASE STOCK %d LBS" %
                        (int(u.hp), u.max_hp, u.stats['fuel'] * 60,
                         int(self._base_stock(base))))
                    entries = []
                    if u.cargo:
                        entries.append(("++ UNLOAD HERE ++",
                                        self._unload_parked, [u]))
                    entries += [("%d/%d" % (int(p.hp), p.max_hp),
                                 self._noop, [],
                                 get_icon_path(p.unit_type, 'dark'))
                                for p in u.cargo]
                    bar.add_buttons(entries)
                    bar.set_hint(
                        "RMB LAND UNITS ONTO THE FIELD TO BOARD -- RMB "
                        "ANOTHER AIRFIELD TO FLY THE LIFT -- RMB OPEN "
                        "GROUND TO PARADROP")
                    return
                bar.set_title("%s -- READY AT %s" %
                              (u.stats['label'].upper(), base_name))
                bar.set_info("STRENGTH %d/%d   ENDURANCE %.0f MI   "
                             "BASE STOCK %d LBS" %
                             (int(u.hp), u.max_hp, u.stats['fuel'] * 60,
                              int(self._base_stock(base))))
                bar.set_hint("RIGHT-CLICK AN OBJECTIVE TO LAUNCH THE "
                             "SORTIE -- ESC TO STAND DOWN")
                return
            bar.set_title("%s -- %s" % (u.stats['label'].upper(),
                                        BRANCH_OF[u.stats['domain']]))
            extra = ""
            if u.stats.get('capacity'):
                extra = "  CARGO %d/%d" % (len(u.cargo),
                                           u.stats['capacity'])
            if u.stats.get('comm'):
                extra += "  COMM NET RADIUS %.0f MI" % (u.comm_range() * 60)
            if u.stats['domain'] == 'air':
                if u.based_at is not None:
                    name = getattr(u.based_at, 'name', None) or \
                        u.based_at.stats['label']
                    extra += "  BASED AT %s" % name.upper()
                else:
                    extra += "  ALOFT -- SORTIE IN PROGRESS"
                extra += "  ENDURANCE %.0f MI" % (u.stats['fuel'] * 60)
            if u.stats['supply_cap'] > 0:
                extra += "  SUPPLY %d LBS" % int(u.supply)
            bar.set_info("STRENGTH %d/%d%s" % (int(u.hp), u.max_hp, extra))
            if u.cargo:
                entries = [("%d/%d" % (int(p.hp), p.max_hp),
                            self._noop, [],
                            get_icon_path(p.unit_type, 'dark'))
                           for p in u.cargo]
                verb = ("PARADROP" if u.stats.get('paradrop')
                        else "UNLOAD")
                entries.insert(0, ("++ %s: RMB SITE ++" % verb,
                                   self._arm_unload, []))
                bar.add_buttons(entries)
        else:
            counts = {}
            for u in self.selected:
                counts[u.stats['label']] = counts.get(u.stats['label'], 0) + 1
            summary = "  ".join("%dx %s" % (n, lbl)
                                for lbl, n in sorted(counts.items()))
            bar.set_title("TASK FORCE -- %d UNITS" % len(self.selected))
            bar.set_info(summary)
        bar.set_hint(CONTROLS_HINT)

    def _refresh_carrier_ui(self, carrier):
        self._refresh_air_roster(carrier)

    def _refresh_airfield_ui(self, field):
        self._refresh_air_roster(field)

    def _refresh_harbor_ui(self, harbor):
        bar = self.bottom_bar
        bar.set_title("%s -- FLEET YARD" % harbor.name)
        bar.set_info("READY HULLS %d   LAUNCHING IS ONE-WAY: A SHIP "
                     "NEVER RETURNS TO THE YARD" % len(harbor.ready))
        entries = []
        for i, ut in enumerate(harbor.ready[:17]):
            s = stats_for(ut, harbor.country)
            entries.append(("LAUNCH %s" % s['label'][:14].upper(),
                            self.launch_ship, [harbor, i],
                            get_icon_path(ut, 'dark')))
        bar.add_buttons(entries)
        bar.set_hint("NEW HULLS ARRIVE HERE FROM THE FORTNIGHT BUDGET"
                     if not harbor.ready else
                     "CLICK A HULL TO PUT HER IN THE WATER")

    def launch_ship(self, harbor, index):
        """Slide a ready hull down the ways: a one-time event."""
        if (harbor.country != self.player_country
                or index >= len(harbor.ready)):
            return
        ut = harbor.ready.pop(index)
        harbor.set_count(len(harbor.ready))
        u = self.spawn_unit(ut, harbor.country, harbor.lat, harbor.lon,
                            jitter=0.15, seed=random.randrange(9999),
                            water=True)
        self.fax_short("%s SLIDES DOWN THE WAYS AT %s" %
                       (u.stats['label'].upper(), harbor.name))
        if self.selected_harbor is harbor:
            self._refresh_harbor_ui(harbor)

    def _unload_parked(self, transport):
        """Disembark a parked transport's load onto the apron."""
        self._unload_cargo(transport)
        self._refresh_selection_ui()

    def _refresh_air_roster(self, base):
        """Shared airfield/carrier menu: lists parked squadrons as
        buttons; selected ones are white-bordered.  Stays up while you
        shift-click to build a strike package."""
        self.roster_base = base
        bar = self.bottom_bar
        wing = self.base_wing(base)
        is_carrier = isinstance(base, Unit)
        if is_carrier:
            bar.set_title("FLEET CARRIER -- NAVY")
            bar.set_info("STRENGTH %d/%d   AIR WING %d   AV STOCK %d LBS   "
                         "SUPPLY %d LBS" %
                         (int(base.hp), base.max_hp, len(wing),
                          int(base.av_stock), int(base.supply)))
            empty_hint = ("NO AIRCRAFT ABOARD -- ORDER SQUADRONS TO LAND "
                          "ON THE CARRIER TO EMBARK THEM")
        else:
            bar.set_title("%s -- AIR STATION" % base.name)
            bar.set_info("AVIATION STOCK %d LBS   AIRCRAFT %d%s" %
                         (int(base.stock), len(wing),
                          "   (SUPPLIED BY CITY)" if base.city is not None
                          else "   (TRUCK SUPPLY REQUIRED)"))
            empty_hint = "NO AIRCRAFT ON THE FIELD"
        if wing:
            entries = [("%d/%d" % (int(p.hp), p.max_hp),
                        self._select_embarked, [p],
                        get_icon_path(p.unit_type, 'dark'),
                        p in self.selected)
                       for p in wing]
            bar.add_buttons(entries)
            n = sum(1 for p in wing if p in self.selected)
            if n:
                bar.set_hint("%d SELECTED -- SHIFT-CLICK TO ADD/REMOVE   "
                             "RIGHT-CLICK AN OBJECTIVE TO LAUNCH" % n)
            else:
                bar.set_hint("CLICK A SQUADRON; SHIFT-CLICK TO ADD MORE "
                             "FOR A STRIKE PACKAGE")
        else:
            bar.set_hint(empty_hint)

    def _refresh_engineer_ui(self, eng):
        bar = self.bottom_bar
        bar.set_title("ENGINEER COMPANY -- WORKS DETAIL")
        bar.set_info("STRENGTH %d/%d   SUPPLY %d LBS" %
                     (int(eng.hp), eng.max_hp, int(eng.supply)))
        entries = [("%s %dLB" % (label, cost), self.begin_build_mode,
                    [kind])
                   for kind, (label, cost, _t) in self.BUILD_WORKS.items()]
        entries.append(("REPAIR: RMB BRIDGE", self._noop, []))
        bar.add_buttons(entries)
        bar.set_hint("")

    def _noop(self):
        pass

    # how-to-employ notes, one per unit type; stats are generated
    UNIT_USAGE = {
        'infantry': [
            "The backbone of any advance and the only arm that",
            "takes and holds ground -- move a section onto a town",
            "to capture it. Cheap and expendable; commit them in",
            "numbers. Shelter them in bunkers against bombs and",
            "naval gunfire."],
        'tank': [
            "Your armoured fist: heavy hitting power against ground",
            "troops, and able to demolish bridges. Very fast on",
            "roads. Spearhead breakthroughs and exploit gaps -- but",
            "keep supply lorries close, for armour drinks stores."],
        'supply_truck': [
            "Carries stores to the front. Right-click a position",
            "near your troops to set its RAILHEAD; it then hauls",
            "from the nearest city or depot and issues stores to any",
            "friendly unit within sight -- unaided. Keep one behind",
            "every advance. Depots let you stage stores forward."],
        'transport_truck': [
            "Motor transport for infantry over friendly ground.",
            "Foot troops that must cross water or drop from the sky",
            "require sea or air transport instead."],
        'aa_artillery': [
            "Air defence. Engages enemy aircraft at long range and",
            "is useless against ground troops. Post batteries over",
            "your cities, columns and airfields to deny the enemy",
            "the skies. Site it well -- it is slow to reposition."],
        'army_command': [
            "The wireless heart of your army. Units beyond every",
            "command post's white W/T circle go OUT OF CONTACT --",
            "invisible and beyond orders. Keep a command post well",
            "forward with any detached force."],
        'engineer': [
            "Field engineers. Select for the works menu: build",
            "bridges, roads, supply depots, bunkers and airfields.",
            "They march to the site, then build; they also rebuild",
            "demolished bridges. Unarmed -- give them an escort."],
        'naval_command': [
            "The fleet's wireless flagship, extending the W/T net",
            "out to sea so detached squadrons stay in contact.",
            "Unarmed; screen it with destroyers."],
        'personnel_transport': [
            "Sea lift for land units. Right-click your troops onto",
            "the ship to embark them, sail to a hostile shore, then",
            "use the UNLOAD control to put them ashore. It will not",
            "disembark on its own."],
        'destroyer_sea_sea': [
            "Surface warfare -- hunts and sinks enemy shipping.",
            "Fast and cheap; work them in packs to screen the fleet",
            "and hold the sea lanes. No answer to aircraft."],
        'destroyer_aa': [
            "Anti-aircraft picket. Throws up a flak umbrella over",
            "the fleet against enemy air. Station it alongside your",
            "carriers and troop transports."],
        'destroyer_sea_land': [
            "Shore bombardment. Its heavy guns range inland to pound",
            "coastal troops and demolish bridges. Bring it close in",
            "to support a landing."],
        'supply_ship': [
            "The fleet train. Carries vast stores and replenishes",
            "warships at sea, tops up carrier aviation stocks, and",
            "even fills lorries on the shoreline -- keeping a fleet",
            "fighting far from port."],
        'aircraft_carrier': [
            "A mobile airfield at sea. Aircraft land aboard and sail",
            "with her. Select the carrier to launch her air wing on",
            "sorties. Keep her aviation stores topped up and screen",
            "her well -- she is a prize target."],
        'fighter': [
            "Air superiority and ground attack. Flies a complete",
            "sortie from an airfield or carrier and returns. Engages",
            "enemy aircraft and strafes ground troops. An order",
            "beyond her fuel radius will be refused."],
        'bomber': [
            "The heavy punch from above -- devastating against",
            "ground troops, shipping and bridges. Send several at a",
            "hard target. Vulnerable to fighters and flak; time your",
            "raids for weak air defence."],
        'airforce_command': [
            "Airborne wireless relay, extending the W/T net across",
            "the map on patrol. Flies sorties like any aircraft but",
            "carries no arms."],
        'transport_air': [
            "Air lift and airborne assault. Ferry land units airfield",
            "to airfield, or PARADROP them anywhere within fuel range",
            "-- select, then site the drop. Unarmed."],
    }

    def open_unit_briefing(self, unit_type):
        if self.game_state != 'playing' or self.briefing_fax:
            return
        s = stats_for(unit_type, self.player_country)
        title = "*** UNIT BRIEFING -- %s ***" % s['label'].upper()
        self.briefing_fax = BriefingFax(
            self, title, self._unit_briefing_lines(unit_type),
            self._close_briefing)

    def _unit_briefing_lines(self, unit_type):
        from config import COMM_RADIUS_FACTOR
        s = stats_for(unit_type, self.player_country)

        def row(label, val):
            return "%s %s" % ((label + ' ').ljust(15, '.'), val)

        lines = []
        if s.get('note'):
            lines += ["#NATIONAL DESIGNATION", s['note'], ""]
        lines += ["#SERVICE RECORD",
                 row("BRANCH", BRANCH_OF[s['domain']]),
                 row("STRENGTH", "%d" % s['hp']),
                 row("SPEED", "%.0f MPH" % (s['speed'] * 60)),
                 row("VISION", "%.0f MI OBSERVATION%s" %
                     (s['vision'] * VISION_SCALE *
                      (AIR_VISION_MULT if s['domain'] == 'air' else 1.0)
                      * 60,
                      " (AIRBORNE)" if s['domain'] == 'air' else ""))]
        if s['damage'] > 0:
            lines.append(row("ARMAMENT", "%d PER SALVO, RANGE %.0f MI" %
                             (s['damage'], s['range'] * 60)))
            lines.append(row("ENGAGES",
                             ", ".join(t.upper() for t in s['targets'])))
        else:
            lines.append(row("ARMAMENT", "NONE -- NON-COMBATANT"))
        if s.get('capacity'):
            lines.append(row("CAPACITY", "%d UNITS EMBARKED" %
                             s['capacity']))
        if s.get('fuel'):
            lines.append(row("COMBAT RADIUS", "%.0f MI (THERE AND BACK)" %
                             (s['fuel'] / 2.0 * 60)))
        if s.get('comm'):
            lines.append(row("WIRELESS NET", "COMMAND RADIUS %.0f MI" %
                             (s['vision'] * COMM_RADIUS_FACTOR * 60)))
        if s['domain'] != 'air' and s.get('supply_cap', 0) > 0:
            lines.append(row("STORES", "%d LBS CARRIED" % s['supply_cap']))
        lines.append(row("COST", "$%d" % s['cost']))
        lines.append("")
        lines.append("#EMPLOYMENT")
        lines.extend(self.UNIT_USAGE.get(unit_type,
                                         ["(No briefing on file.)"]))
        return lines

    def _close_briefing(self):
        if self.briefing_fax:
            self.briefing_fax.destroy()
            self.briefing_fax = None

    def _arm_unload(self):
        if any(u.cargo for u in self.selected
               if u.country == self.player_country):
            self.unload_mode = True
            self.fax_short("SITE THE DISEMBARKATION: RIGHT-CLICK THE "
                           "MAP -- ESC CANCELS")

    def _select_embarked(self, plane):
        """Squadron button in an airfield/carrier menu; shift-click
        toggles a squadron in/out of the strike package (white border
        shows which are chosen).  The roster stays open throughout."""
        if not plane.alive or not self.is_parked(plane):
            return
        base = plane.based_at
        mw = self.mouseWatcherNode
        shift = mw and mw.isButtonDown(self._key_shift)
        if (shift and self.selected
                and all(self.is_parked(u) and u.based_at is base
                        for u in self.selected)):
            if plane in self.selected:
                self.selected.remove(plane)
                plane.set_selected(False)
            else:
                self.selected.append(plane)
                plane.set_selected(True)
            self.roster_base = base
            self._refresh_selection_ui()
            return
        self.clear_selection()
        self.selected = [plane]
        plane.set_selected(True)
        self.roster_base = base
        self._refresh_selection_ui()

    def _set_city_info(self, city):
        queue = ", ".join("%s %ds" % (UNIT_TYPES[t]['icon'], s)
                          for t, s in city.production[:4])
        tax = "%d%%" % city.tax_rate
        if city.pending_tax is not None:
            tax += " (%d%% NEXT)" % city.pending_tax
        self.bottom_bar.set_info(
            "POP %s%s   INDUSTRY %.0f%%   TAX %s   WORKS: %s" %
            ("{:,}".format(city.population),
             "   PORT" if city.harbor else "",
             city.industry, tax,
             queue if queue else "NONE"))

    def _tick_top_bar(self):
        if not self.top_bar:
            return
        n_units = sum(1 for u in self.units
                      if u.alive and u.country == self.player_country)
        n_cities = sum(1 for c in self.cities
                       if c.country == self.player_country)
        self.top_bar.set_stats({
            'NATION': COUNTRIES[self.player_country]['adjective'].upper(),
            'TREASURY': "$%d" % int(self.funds[self.player_country]),
            'FORCES': n_units,
            'CITIES': n_cities,
            'TIME': self.campaign_clock_text(),
            '[OUT OF CONTACT]': (self.out_of_contact
                                 if self.out_of_contact else "-"),
            'KILLS': self.kills,
            'LOSSES': self.losses,
            'SPEED': ("PAUSED" if self.is_paused
                      else "x%g" % self.game_speed),
        })
        self.top_bar.set_fortnight_day(self.fortnight_day())

    # ====================================================== main loop
    def update(self, task):
        dt = globalClock.getDt()
        self._position_cursor()         # follows the mouse in menu too
        if self.game_state != 'playing':
            return Task.cont

        self._tick_camera(dt)
        self._tick_drag_box()
        self._drain_plans()
        self._update_vision_shader()    # fog circles glide with units
        self.globe.set_comm_width(self.cam_dist - GLOBE_RADIUS)
        self.globe.tick_border_bake()   # swap in a finished border bake
        self._hover_timer -= dt
        if self._hover_timer <= 0:
            self._hover_timer = 0.09
            self._tick_cursor_mode()
            self._tick_hover_glow()
        if self.fax:
            self.fax.update(dt)

        if not self.is_paused and not self.game_over:
            gdt = dt * self.game_speed
            self.clock_minutes += gdt * MINUTES_PER_SECOND
            # a new fortnight begins: taxes bind, revenue comes in, the
            # standing budget goes into effect
            if (self.clock_minutes - self.fortnight_start
                    >= BUDGET_PERIOD_DAYS * 1440.0):
                self.fortnight_start += BUDGET_PERIOD_DAYS * 1440.0
                self._fortnight_rollover()
            # the sun tracks westward so it rises in the east and sets
            # in the west
            self.sun_angle = (self.sun_angle -
                              2 * math.pi * gdt / DAY_CYCLE_LENGTH)
            sun = self.sun_direction()
            self.globe.set_sun_direction(sun)
            self.sun_np.setPos(sun * 200)
            self.sun_np.lookAt(0, 0, 0)

            for u in self.units:
                u.update(dt)
            self.units = [u for u in self.units if u.alive]

            self._tick_production(dt)
            self._tick_ai(dt)
            self._tick_flashes(dt)

            # spread queued AI movement orders over frames (route
            # planning is the expensive part)
            for _ in range(2):
                if not self._pending_ai_orders:
                    break
                u, order = self._pending_ai_orders.pop(0)
                if u.alive and not u.carried_by:
                    u.give_order(order)

            # aircraft bound for a carrier keep tracking her movement
            self._chase_timer -= dt
            if self._chase_timer <= 0:
                self._chase_timer = 0.7
                for u in self.units:
                    if (u.alive and u.stats['domain'] == 'air'
                            and u.based_at is None and u.path
                            and isinstance(u.landing_at, Unit)):
                        carrier = u.landing_at
                        if not carrier.alive:
                            continue
                        last = u.path[-1][0]
                        if angle_between(last, carrier.pos) * \
                                GLOBE_RADIUS > 0.12:
                            u.path[-1] = (Vec3(carrier.pos),
                                          u.path[-1][1])


            self._capture_timer -= dt
            if self._capture_timer <= 0:
                self._capture_timer = 0.5
                self._tick_capture(0.5)

            self._supply_timer -= dt
            if self._supply_timer <= 0:
                self._supply_timer = 1.0
                self._tick_supply()

            self._vision_timer -= dt
            if self._vision_timer <= 0:
                self._vision_timer = 0.3
                self._tick_vision_comm()
                self._check_victory()

            self._tick_tracers(dt)

        self._tick_path_viz(dt)
        self._top_bar_timer -= dt
        if self._top_bar_timer <= 0:
            self._top_bar_timer = 0.25
            self._tick_top_bar()

        self._city_ui_timer -= dt
        if self._city_ui_timer <= 0:
            self._city_ui_timer = 1.0
            if self.selected_city and self.bottom_bar:
                self._set_city_info(self.selected_city)
        return Task.cont
