"""
THE FIELD MANUAL -- the game's wiki, on one tabbed folder.

Twelve tabs cover every mechanic in play: the world and its map,
the economy, the cities, the supply net, combat, the three service
arms' full stat tables, the five powers, the research chart, the
diplomatic instruments, and the controls.

THE FIGURES ARE NEVER COPIED IN BY HAND. Every number on these
pages is read from the same tables the game itself plays by --
config.py, units.UNIT_TYPES, tech.NODES, deals.STANDING -- at the
moment the page is printed, so the manual cannot drift from the
game. It is the source of record for players and for development
alike: when a mechanic changes in code, this page says so at the
next opening.
"""

from direct.gui.DirectGui import DirectButton, DirectFrame, DGG
from panda3d.core import TextNode

import config as C
from icons import get_icon_path, unit_ui_icon
from ui import (FormSheet, pill_button, crisp_image, INK, INK_FAINT,
                RED_INK, GREEN_INK, KEY_LIGHT)
from units import UNIT_TYPES, BRANCH_OF, FIRE_SUPPLY_FACTOR

SEL_FILL = (0.22, 0.19, 0.14, 1.0)
SEL_TEXT = (0.93, 0.90, 0.80, 1.0)

TABS = (
    ('world', 'WORLD'),
    ('economy', 'ECONOMY'),
    ('cities', 'CITIES'),
    ('supply', 'SUPPLY'),
    ('combat', 'COMBAT'),
    ('army', 'ARMY'),
    ('air', 'AIR FORCE'),
    ('navy', 'NAVY'),
    ('nations', 'NATIONS'),
    ('research', 'RESEARCH'),
    ('diplomacy', 'DIPLOMACY'),
    ('controls', 'CONTROLS'),
)


def _mi(wu):
    """World units to statute miles, as the briefings convert."""
    return wu * C.MILES_PER_WU


class WikiFax:
    """One wide War Office folder with physical tabs across the
    top. Clicking a tab re-prints the open page."""

    W, H = 1.42, 0.92
    TAB_Y = 0.615               # centre line of the tab rank
    BODY_TOP = 0.520

    def __init__(self, base, on_close):
        self.base = base
        self.on_close = on_close
        self.tab = 'world'
        self.sheet = FormSheet(base, "THE FIELD MANUAL",
                               half_w=self.W, half_h=self.H,
                               stamp=None,
                               sheet_tag="THE WHOLE WAR ON FILE")
        self.frame = self.sheet.frame
        self.sheet.keys([
            ("CLOSE  [ESC]", self._close, (), 0.0, 'red',
             KEY_LIGHT, 0.22),
        ])
        self._tab_widgets = []
        self._content = None
        self._build_tabs()
        self._build_page()

    # ------------------------------------------------------- chrome
    def _build_tabs(self):
        for w in self._tab_widgets:
            w.destroy() if hasattr(w, 'destroy') else w.removeNode()
        self._tab_widgets = []
        n = len(TABS)
        span = 2.0 * self.W - 0.16
        step = span / n
        x0 = -self.W + 0.08 + step / 2.0
        for i, (key, label) in enumerate(TABS):
            sel = (key == self.tab)
            fill = SEL_FILL if sel else (0.86, 0.82, 0.68, 0.0)
            b = DirectButton(
                parent=self.frame, text=label,
                text_scale=0.0205,
                text_fg=(SEL_TEXT if sel else INK),
                text_font=self.base.hud_font,
                text_pos=(0, -0.008),
                frameColor=(fill,
                            fill if sel else (0.80, 0.74, 0.55, 0.55),
                            fill if sel else (0.70, 0.66, 0.54, 0.65),
                            (0.5, 0.5, 0.5, 0.3)),
                frameSize=(-step / 2 + 0.006, step / 2 - 0.006,
                           -0.030, 0.030),
                relief=DGG.FLAT, command=self._open,
                extraArgs=[key],
                pos=(x0 + i * step, 0, self.TAB_Y))
            self._tab_widgets.append(b)
        # the folder's edge: the open tab sits ON the line
        r = DirectFrame(parent=self.frame, frameColor=INK,
                        frameSize=(-self.W + 0.08, self.W - 0.08,
                                   self.TAB_Y - 0.0335,
                                   self.TAB_Y - 0.0315))
        self._tab_widgets.append(r)

    def _open(self, key):
        if key == self.tab:
            return
        self.tab = key
        self._build_tabs()
        self._build_page()

    def _close(self):
        cb = self.on_close
        self.on_close = None
        if cb:
            cb()

    # ------------------------------------------------ page plumbing
    def _build_page(self):
        if self._content is not None:
            self._content.destroy()
        self._content = DirectFrame(parent=self.frame,
                                    frameColor=(0, 0, 0, 0),
                                    frameSize=(-0.01, 0.01,
                                               -0.01, 0.01))
        getattr(self, '_page_' + self.tab)()

    def text(self, t, pos, scale=0.026, color=INK,
             align=TextNode.ALeft, wrap=None):
        tn = TextNode('wiki_text')
        tn.setAlign(align)
        if wrap:
            tn.setWordwrap(wrap)
        if self.base.hud_font:
            tn.setFont(self.base.hud_font)
        tn.setTextColor(*color)
        tn.setText(t)
        np_ = self._content.attachNewNode(tn)
        np_.setPos(pos[0], 0, pos[1])
        np_.setScale(scale)
        return tn, np_

    def header(self, t, pos, scale=0.030):
        return self.text(t, pos, scale, RED_INK)

    def rule(self, x0, x1, z, thick=0.002, color=INK_FAINT):
        return DirectFrame(parent=self._content, frameColor=color,
                           frameSize=(x0, x1, z - thick / 2.0,
                                      z + thick / 2.0))

    def vrule(self, x, z0, z1, thick=0.002, color=INK_FAINT):
        return DirectFrame(parent=self._content, frameColor=color,
                           frameSize=(x - thick / 2.0,
                                      x + thick / 2.0, z0, z1))

    def icon(self, name, pos, scale=0.028, unit=False):
        ic = DirectFrame(parent=self._content, relief=None,
                         frameColor=(0, 0, 0, 0),
                         image=(unit_ui_icon(name) if unit
                                else get_icon_path(name, 'dark')),
                         image_scale=scale,
                         frameSize=(-scale, scale, -scale, scale),
                         pos=(pos[0], 0, pos[1]))
        ic.setTransparency(True)
        crisp_image(ic)
        return ic

    def flag(self, country, pos, hw=0.060):
        from ui import flag_tex
        f = DirectFrame(parent=self._content,
                        frameColor=(1, 1, 1, 1),
                        frameTexture=flag_tex(country),
                        frameSize=(-hw, hw, -hw * 2 / 3.0,
                                   hw * 2 / 3.0),
                        pos=(pos[0], 0, pos[1]))
        return f

    def bullets(self, lines, x, y, step=0.0455, scale=0.0255,
                color=INK):
        for ln in lines:
            self.text(ln, (x, y), scale, color)
            y -= step
        return y

    # =================================================== THE PAGES
    def _page_world(self):
        t = self.BODY_TOP
        L, M = -1.32, 0.06
        self.header("THE GLOBE AND THE CLOCK", (L, t))
        self.bullets([
            "The war is fought on the real Earth. One world unit "
            "is %d statute miles." % C.MILES_PER_WU,
            "The clock opens at dawn, 1 September 1939, and runs "
            "%d minutes to the real second." % int(C.MINUTES_PER_SECOND),
            "The sun tracks west; a full planet day passes in %d "
            "seconds." % int(C.DAY_CYCLE_LENGTH),
            "Game speed is changed with = and - and paused with "
            "SPACE.",
        ], L, t - 0.055)

        self.header("FOG OF WAR -- WHAT YOU SEE", (L, t - 0.290))
        self.bullets([
            "A unit sees its VISION stat / 10 in world units; "
            "aircraft see %dx further." % int(C.AIR_VISION_MULT),
            "NIGHT HALVES ALL VISION -- and at night aircraft "
            "and surface units",
            "  cannot spot each other at all.",
            "Friendly towns keep their own watch (%.0f mi about "
            "the walls)." % _mi(C.CITY_VISION_RANGE),
            "Ground you cannot see is darker and drained of "
            "colour; enemies",
            "  there are invisible.",
        ], L, t - 0.345)

        self.header("THE WIRELESS NET -- COMMAND", (L, t - 0.640))
        self.bullets([
            "Command posts, flagships and command wings carry "
            "the net: radius",
            "  %.1fx their raw vision stat." % C.COMM_RADIUS_FACTOR,
            "Friendly cities carry the land-line network "
            "(%.0f mi about each town)." % _mi(C.CITY_COMM_RADIUS),
            "A unit OUTSIDE the net goes W/T SILENT: invisible, "
            "unselectable,",
            "  deaf to orders. The top bar counts them under "
            "[OUT OF CONTACT].",
        ], L, t - 0.695)

        self.vrule(-0.04, -0.66, t + 0.02)
        self.header("ROADS, RAILS AND RIVERS", (M, t))
        self.bullets([
            "Roads multiply a chassis's cross-country speed by its "
            "own road factor:",
            "  men x1.5, tanks x2.0, guns and staff cars x3.5, "
            "lorries x4.0.",
            "RAILWAYS carry EVERY unit at one train speed (%.0f "
            "mph) and burn no stores" % (C.RAIL_TRAIN_SPEED * 60),
            "  under way. The router prefers rail over road when "
            "both serve.",
            "THE FRONTIER BINDS THE ROUTE: no course is plotted "
            "through a country",
            "  that has not granted passage -- war or a treaty "
            "opens it.",
            "Rivers stop land columns dead, except at BRIDGES "
            "(%d hp; engineers repair" % C.BRIDGE_HP,
            "  %d hp a second, and can survey new roads, rails "
            "and bridges)." % C.BRIDGE_REPAIR_RATE,
            "The sea lanes of the world are open: Suez, Panama, "
            "Kiel, the Belts, the",
            "  Bosporus and the narrow straits are all navigable.",
            "Engineers build depots, bunkers, bridges, radar, "
            "ports and airfields",
            "  ON SITE -- and lay roads and rails STRETCH BY "
            "STRETCH, the party",
            "  advancing along its own survey as each length of "
            "way opens.",
        ], M, t - 0.055)
        self.header("THE MAP IS THE TRUTH", (M, t - 0.665))
        self.bullets([
            "Cities, deposits, bases and bridges are printed on "
            "the map itself.",
            "Contour lines are drawn from the same ground the "
            "columns march over.",
        ], M, t - 0.720)

    def _page_economy(self):
        t = self.BODY_TOP
        L, M = -1.32, 0.06
        self.header("THE FORTNIGHT", (L, t))
        self.bullets([
            "Everything fiscal runs on the fortnight: %d campaign "
            "days." % C.BUDGET_PERIOD_DAYS,
            "The top bar's dots count the running fortnight's "
            "days.",
        ], L, t - 0.055)
        self.header("TAXES AND INDUSTRY", (L, t - 0.175))
        self.bullets([
            "A town's gross product is $%d a fortnight ($%d for "
            "the capital)." % (C.CITY_GROSS_FORTNIGHT,
                               C.CAPITAL_GROSS_FORTNIGHT),
            "Remittance = gross x tax rate x industry health.",
            "At %d%% tax the industry HOLDS. Every point above "
            "decays it %.1f%%/ftn;" % (C.TAX_EQUILIBRIUM,
                                       C.INDUSTRY_DRIFT),
            "  every point below heals it the same. Set rates by "
            "TAX DECREE per town.",
        ], L, t - 0.230)
        self.header("THE BUDGET MANIFEST  [B]", (L, t - 0.435))
        self.bullets([
            "The treasury is allocated across unit types on one "
            "sheet; TRANSMIT",
            "  commits it for the fortnight (the remainder "
            "carries forward).",
            "Land units muster at ARMY BASES, ships at NAVAL "
            "BASES, aircraft at",
            "  AIRFORCE BASES. No base, no delivery.",
            "Works orders run %.0fx their nominal build time."
            % C.PRODUCTION_TIME_FACTOR,
        ], L, t - 0.490)
        self.header("TREATY TRADE", (L, t - 0.740))
        self.bullets([
            "Base prices $/ton: oil %d, steel %d, food %d -- "
            "warmer standing, better" % (C.TRADE_PRICES['oil'],
                                         C.TRADE_PRICES['steel'],
                                         C.TRADE_PRICES['food']),
            "  prices. One-time shipments land on signing.",
        ], L, t - 0.795)

        self.vrule(-0.04, -0.66, t + 0.02)
        self.header("THE THREE RESOURCES", (M, t))
        rows = [
            ('derrick', "OIL -- OPERATIONS",
             "Drawn at the pumps: 1 ton moves 1,250 lbs of stores "
             "into a machine. Each sortie burns %.1f t of spirit."
             % C.OIL_PER_SORTIE),
            ('foundry', "STEEL -- PRODUCTION",
             "Spent building every hull and plate. A piece's bill "
             "rises with its price; infantry cost none."),
            ('granary', "FOOD -- MANPOWER",
             "GROWN BY EVERY TOWN: %d t/ftn base plus its "
             "agriculture level. %d t raises a section; civilians "
             "eat %.2f t per million souls a day (occupied mouths "
             "%.1f t)." % (C.CITY_FOOD_BASE, C.FOOD_PER_ENLISTED,
                           C.CIVIL_RATION, C.OCCUPIED_RATION)),
        ]
        y = t - 0.070
        for icon_name, head, body in rows:
            self.icon(icon_name, (M + 0.045, y - 0.020), 0.040)
            self.text(head, (M + 0.105, y), 0.0265, RED_INK)
            self.text(body, (M + 0.105, y - 0.042), 0.0235,
                      INK, wrap=48)
            y -= 0.175
        n_dep = {}
        for name, (res, out) in C.DEPOSITS.items():
            n_dep[res] = n_dep.get(res, 0) + 1
        self.header("DEPOSITS -- THE WORLD'S ONLY TAPS",
                    (M, y - 0.010))
        self.bullets([
            "%d oil fields and %d steel districts lie by their "
            "real towns, and they" % (n_dep.get('oil', 0),
                                      n_dep.get('steel', 0)),
            "  are the ONLY source of oil and steel on Earth: no "
            "free imports.",
            "OWN THE TOWN AND ITS DEPOSIT PAYS YOU, steadily, "
            "every fortnight",
            "  (stockpile cap %d). No deposit? BUY at the treaty "
            "table -- or take one." % C.RESOURCE_CAP,
            "The heaviest: Houston %d oil, Pittsburgh %d steel. "
            "Food has no deposits"
            % (C.DEPOSITS['Houston'][1],
               C.DEPOSITS['Pittsburgh'][1]),
            "  at all -- the historic farm belts open with "
            "agriculture pre-levelled.",
        ], M, y - 0.065)

    def _page_cities(self):
        t = self.BODY_TOP
        L, M = -1.32, 0.06
        self.header("THE MUNICIPAL LEDGER", (L, t))
        self.bullets([
            "Every town keeps THREE PERMANENT TRACKS of %d levels "
            "-- agriculture," % C.TRACK_MAX_LEVEL,
            "  the works, the laboratories. One fortnight focus "
            "buys ONE level,",
            "  MONEY ALONE (L1-L%d: %s), and the returns are"
            % (C.TRACK_MAX_LEVEL,
               ", ".join("$%d" % c for c in C.TRACK_COSTS)),
            "  EXPONENTIAL -- the deep town beats two shallow "
            "ones. Levels survive",
            "  capture: a developed city is worth taking.",
        ], L, t - 0.055)
        track_rows = [
            ("AGRICULTURE", "food t/ftn by level: %s (+%d base "
             "every town)" % ("/".join(
                 str(v) for v in C.AGRI_FOOD_CUM[1:]),
                 C.CITY_FOOD_BASE)),
            ("THE WORKS", "its bases build faster: %s"
             % "/".join("x%.2f" % v
                        for v in C.WORKS_SPEED_MULT[1:])),
            ("THE LABORATORIES", "research focus yields: %s"
             % "/".join("x%.1f" % v
                        for v in C.LAB_YIELD_MULT[1:])),
        ]
        y = t - 0.300
        for head, body in track_rows:
            self.text(head, (L + 0.02, y), 0.0245, INK)
            self.text(body, (L + 0.36, y), 0.022, INK_FAINT)
            self.rule(L + 0.02, -0.10, y - 0.017, 0.0014)
            y -= 0.052
        focus_rows = [
            ("INVEST IN FINANCE", "+%.0f industry health"
             % C.FOCUS_FINANCE_HEAL),
            ("RUN THE LABORATORIES", "%.0f RP per million souls "
             "(min %.0f) x the labs level"
             % (C.FOCUS_RESEARCH_RP_PER_M, C.FOCUS_RESEARCH_RP_MIN)),
            ("RAISE A BASE", "army $%d+%ds, air $%d+%ds, naval "
             "$%d+%ds; once each"
             % (C.BASE_COSTS['army'] + C.BASE_COSTS['air']
                + C.BASE_COSTS['naval'])),
        ]
        for head, body in focus_rows:
            self.text(head, (L + 0.02, y), 0.0245, INK)
            self.text(body, (L + 0.36, y), 0.022, INK_FAINT)
            self.rule(L + 0.02, -0.10, y - 0.017, 0.0014)
            y -= 0.052
        self.header("BASES AND FIELDS", (L, y - 0.030))
        self.bullets([
            "BASES are city-built and produce: army bases land "
            "units, naval bases",
            "  ships, airforce bases aircraft. The town supplies "
            "them itself.",
            "PORTS and AIRFIELDS are engineer-built works: they "
            "base and supply",
            "  but produce nothing, and lorries must feed them.",
            "A town's own bases carry STRIKE keys on its garrison "
            "command --",
            "  two clicks decommission one; a focus raises it "
            "again.",
        ], L, y - 0.085)

        self.vrule(-0.04, -0.66, t + 0.02)
        self.header("THE CIVILIAN DRAFT", (M, t))
        self.bullets([
            "The rolls grow one section per 400,000 souls a "
            "fortnight, banked to three.",
            "Sections from the rolls muster FREE and AT ONCE.",
            "Beyond the rolls is CONSCRIPTION: -%.1f%% industry a "
            "section, down to" % C.DRAFT_INDUSTRY_GRIND,
            "  nought. Every section still eats %d t of food."
            % C.FOOD_PER_ENLISTED,
        ], M, t - 0.055)
        self.header("TAKING A TOWN", (M, t - 0.290))
        self.bullets([
            "Stand infantry ON the town (within %.0f mi) for %.0f "
            "seconds." % (_mi(C.CITY_CAPTURE_RANGE),
                          C.CITY_CAPTURE_TIME),
            "The garrison bill: %.0f section(s) per million "
            "souls." % C.CAPTURE_INFANTRY_PER_MILLION,
            "NO ANNEXATION while an enemy stands within %.0f mi "
            "of the town --" % _mi(C.CAPTURE_CLEAR_RANGE),
            "  if the garrison on the square cannot see him, he "
            "does not contest it.",
            "A captured town brings its deposit, its base and its "
            "airfield -- and",
            "  its mouths: the occupied eat %.1f t per million a "
            "day." % C.OCCUPIED_RATION,
            "A town ready to fall flies a flashing >CAPTURE< "
            "banner over its name,",
            "  with the garrison bill. CLICK THE BANNER to run "
            "the flag up.",
        ], M, t - 0.345)
        self.header("SELECTING A TOWN", (M, t - 0.755))
        self.bullets([
            "Click the CIVIC ICON standing left of the town's "
            "name -- it glows",
            "  under the cursor. The letters and the ground belong "
            "to the counters.",
        ], M, t - 0.810)

    def _page_supply(self):
        t = self.BODY_TOP
        L, M = -1.32, 0.06
        land_cap = UNIT_TYPES['infantry']['supply_cap']
        eng_cap = UNIT_TYPES['engineer']['supply_cap']
        trk_cap = UNIT_TYPES['supply_truck']['supply_cap']
        sea_cap = UNIT_TYPES['destroyer_sea_sea']['supply_cap']
        ship_cap = UNIT_TYPES['supply_ship']['supply_cap']
        self.header("STORES -- THE POUND IS THE UNIT", (L, t))
        self.bullets([
            "Land units carry %d lbs (engineers %d). Sea hulls "
            "carry %d lbs;" % (land_cap, eng_cap, sea_cap),
            "  the supply ship holds %d and the lorry %d."
            % (ship_cap, trk_cap),
            "MOVEMENT burns stores: %.0f lb/s on land, %.0f lb/s "
            "at sea." % (UNIT_TYPES['infantry']['use_move'],
                         UNIT_TYPES['destroyer_sea_sea']['use_move']),
            "FIRING burns %.1f lbs per point of damage dealt."
            % FIRE_SUPPLY_FACTOR,
            "RAIL RUNNING BURNS NOTHING -- the train feeds the "
            "men.",
            "At zero stores a unit can neither move nor fight, "
            "and wears the red",
            "  jerrican badge until fed.",
        ], L, t - 0.055)
        self.header("WHERE STORES COME FROM", (L, t - 0.430))
        self.bullets([
            "Friendly towns refill anything standing near them, "
            "free.",
            "DEPOTS (engineer-built) bank stores and exchange "
            "with lorries.",
            "SUPPLY LORRIES run their own shuttle: empty to the "
            "nearest source,",
            "  full to their station (RMB sets it) or the "
            "neediest friend in sight.",
            "  The frontier binds the lorries too: no errand "
            "runs through a closed country.",
            "SUPPLY SHIPS feed warships, carriers' air stock and "
            "columns ashore --",
            "  or ANCHOR as a floating supply station: a port that "
            "floats, stored",
            "  into and drawn from by the chain. At anchor she "
            "cannot make way.",
            "Hand-over happens within %.0f mi." %
            _mi(C.SUPPLY_TRANSFER_RANGE),
        ], L, t - 0.485)

        self.vrule(-0.04, -0.66, t + 0.02)
        self.header("AIRCRAFT FLY SORTIES", (M, t))
        self.bullets([
            "Aircraft burn no stores under way; their FIELD pays "
            "PER TAKEOFF:",
            "  600 lbs of the field's stock and %.1f t of "
            "aviation spirit." % C.OIL_PER_SORTIE,
            "Every sortie is flown whole: field, objective, "
            "field. FUEL is the",
            "  total flight plan a squadron can be committed to.",
            "A field that falls takes its parked wings with it.",
        ], M, t - 0.055)
        self.header("THE PUMPS -- OIL UNDER EVERYTHING",
                    (M, t - 0.330))
        self.bullets([
            "Every pound of stores issued to a MACHINE draws oil: "
            "one ton moves",
            "  1,250 lbs. Men and the railways draw none.",
            "No oil, no issue: the machine keeps its stores but "
            "the pumps stop.",
            "The STRATEGIC RESOURCES ledger (top bar) shows "
            "stocks, the take,",
            "  the fortnight's spend and the whole supply net "
            "live.",
        ], M, t - 0.385)
        self.header("FOOD IS MANPOWER", (M, t - 0.660))
        self.bullets([
            "Rations are drawn when towns muster men and daily "
            "for every soul",
            "  the flag covers. A blockaded island starves before "
            "it surrenders.",
        ], M, t - 0.715)

    def _page_combat(self):
        t = self.BODY_TOP
        L, M = -1.32, 0.06
        self.header("THE SALVO", (L, t))
        self.bullets([
            "Units fire on enemies in range OF THEIR OWN ACCORD "
            "-- no order needed.",
            "AN ATTACK ORDER CHASES: while the prey is in sight "
            "the march corrects",
            "  onto its CURRENT position; sight lost, the column "
            "makes for the last",
            "  known place -- and locks on again when sight "
            "returns.",
            "Damage is the salvo's weight; strength (HP) is what "
            "a unit absorbs.",
            "Each arm engages only what its guns can hurt: AA "
            "fires at aircraft,",
            "  destroyers at what their class names, bombers at "
            "what lies under",
            "  the flight path. See the service tables.",
            "A SELECTED unit wears a thin red ring at its guns' "
            "longest reach:",
            "  most arms are capped by their own daytime eyes, "
            "but tanks, artillery",
            "  and warships strike TWICE their eyes with a "
            "friendly observer on",
            "  the target -- and aircraft strike shorter than "
            "they see.",
            "A unit under fire flashes a red ring on the map.",
        ], L, t - 0.055)
        self.header("THE NIGHT", (L, t - 0.660))
        self.bullets([
            "Night halves every eye, and aircraft and surface "
            "units cannot spot",
            "  each other at all -- night convoys slip beneath "
            "the bombers.",
        ], L, t - 0.715)
        self.header("BUNKERS", (L, t - 0.855))
        self.bullets([
            "Engineer-built. INFANTRY ONLY may stand on the "
            "works; vehicles",
            "  deflect around the rim. Enemy fire on infantry "
            "inside is QUARTERED.",
        ], L, t - 0.910)

        self.vrule(-0.04, -0.66, t + 0.02)
        self.header("EMBARKATION AND THE CHAIN", (M, t))
        self.bullets([
            "Infantry ride lorries (%d sections) and any unit "
            "rides ships;"
            % UNIT_TYPES['transport_truck']['capacity'],
            "  air transports lift %d and can PARADROP them."
            % UNIT_TYPES['transport_air']['capacity'],
            "ORDERS CHAIN: select troops, RMB the transport "
            "(embark), then RMB",
            "  the far shore (disembark), then onward -- the "
            "column executes the",
            "  whole plan by itself. Works with BUILD and ATTACK "
            "orders too.",
            "Transports never unload on their own: the UNLOAD "
            "key sites the",
            "  put-ashore, PARADROP the drop.",
            "A transport HOLDS AT THE RAMP for ordered boarders "
            "-- but a direct",
            "  MOVE order sails at once; no straggler ever pins "
            "the ship.",
            "A fleet UNLOADS TOGETHER, berthing abreast down the "
            "coast -- but",
            "  NO PUT-ASHORE in a country without passage or war.",
        ], M, t - 0.055)
        self.header("BRIDGES AND WORKS UNDER FIRE",
                    (M, t - 0.575))
        self.bullets([
            "Bridges (%d hp) can be dropped by gunfire or bombs "
            "and repaired by" % C.BRIDGE_HP,
            "  engineers at %d hp a second."
            % C.BRIDGE_REPAIR_RATE,
            "Airfields are targetable works: destroyed, their "
            "parked wings die.",
        ], M, t - 0.630)
        self.header("AIRCRAFT IN ACTION", (M, t - 0.805))
        self.bullets([
            "Squadrons launch from a field or deck (SCRAMBLE, or "
            "ENTER), strike",
            "  and come home; carriers are moving airfields.",
        ], M, t - 0.860)

    # -------------------------------------------- the stat tables
    def _stat_table(self, domain):
        """One service arm's full table, straight from the tables
        the game plays by."""
        import tech
        rows = [(ut, s) for ut, s in UNIT_TYPES.items()
                if s['domain'] == domain]
        rows.sort(key=lambda kv: kv[1]['cost'])
        t = self.BODY_TOP
        L, R = -1.32, 1.32
        cols = [
            ("UNIT", L + 0.10, TextNode.ALeft),
            ("COST", -0.42, TextNode.ARight),
            ("STR", -0.27, TextNode.ARight),
            ("SALVO", -0.11, TextNode.ARight),
            ("RANGE", 0.07, TextNode.ARight),
            ("SPEED", 0.26, TextNode.ARight),
            ("SEES", 0.44, TextNode.ARight),
            ("NOTES", 0.52, TextNode.ALeft),
        ]
        for name, x, align in cols:
            self.header(name, (x, t), 0.024) if align == TextNode.ALeft \
                else self.text(name, (x, t), 0.024, RED_INK, align)
        self.rule(L, R, t - 0.020, 0.0022, INK)
        y = t - 0.070
        row_h = (y + 0.66) / max(1, len(rows))
        row_h = min(0.105, row_h)
        for ut, s in rows:
            self.icon(ut, (L + 0.045, y + 0.006), 0.030,
                      unit=True)
            self.text(s['label'], (L + 0.10, y), 0.0245)
            if ut == 'infantry':
                # never bought: the budget sells no Enlisted -- they
                # muster from the city draft (rolls free, conscripts
                # paid in industry)
                self.text("DRAFT", (-0.42, y), 0.0245,
                          INK, TextNode.ARight)
            else:
                self.text("$%d" % s['cost'], (-0.42, y), 0.0245,
                          INK, TextNode.ARight)
            self.text("%d" % s['hp'], (-0.27, y), 0.0245, INK,
                      TextNode.ARight)
            if s['damage'] > 0:
                self.text("%d" % s['damage'], (-0.11, y), 0.0245,
                          INK, TextNode.ARight)
                self.text("%.0f MI" % (s['range'] * 60), (0.07, y),
                          0.0245, INK, TextNode.ARight)
            else:
                self.text("--", (-0.11, y), 0.0245, INK_FAINT,
                          TextNode.ARight)
                self.text("--", (0.07, y), 0.0245, INK_FAINT,
                          TextNode.ARight)
            self.text("%.0f MPH" % (s['speed'] * 60), (0.26, y),
                      0.0245, INK, TextNode.ARight)
            vis = (s['vision'] * C.VISION_SCALE
                   * (C.AIR_VISION_MULT if domain == 'air' else 1.0))
            self.text("%.0f MI" % _mi(vis), (0.44, y), 0.0245,
                      INK, TextNode.ARight)
            notes = []
            if s.get('comm'):
                notes.append("COMMAND NET")
            if s.get('capacity'):
                notes.append("CARRIES %d" % s['capacity'])
            if s.get('supply_carrier'):
                notes.append("HAULS %d LBS" % s['supply_cap'])
            if s.get('engineer'):
                notes.append("BUILDS THE WORKS")
            if s.get('paradrop'):
                notes.append("PARADROPS")
            if domain == 'air' and s.get('fuel'):
                notes.append("RADIUS %.0f MI"
                             % (s['fuel'] / 2.0 * C.MILES_PER_WU))
            if ut == 'aircraft_carrier':
                notes.append("A MOVING AIRFIELD")
            if ut == 'submarine':
                notes.append("SUBMERGES")
            if ut == 'blimp':
                notes.append("ENVELOPE UP: SEES %.0f MI, STANDS "
                             "FAST" % _mi(s['vision']
                                          * C.VISION_SCALE
                                          * C.AIR_VISION_MULT))
            if ut not in tech.BASE_UNITS:
                notes.append("RESEARCH (USA AND JAPAN SAIL THEIRS "
                             "FROM DAY ONE)"
                             if ut == 'aircraft_carrier'
                             else "RESEARCH")
            self.text("; ".join(notes) if notes else "--",
                      (0.52, y), 0.0215, INK_FAINT)
            self.rule(L, R, y - row_h / 2.0 + 0.012, 0.0012)
            y -= row_h
        self.text("Salvo weights, ranges and speeds are the BASE "
                  "chassis; each power's own marks differ -- see "
                  "NATIONS.", (0, -0.655), 0.022, INK_FAINT,
                  TextNode.ACenter)

    def _page_army(self):
        self._stat_table('land')

    def _page_air(self):
        self._stat_table('air')

    def _page_navy(self):
        self._stat_table('sea')

    def _page_nations(self):
        from menu import COUNTRY_DOSSIERS
        t = self.BODY_TOP
        L, R = -1.32, 1.32
        y = t - 0.030
        for nat in C.PLAYABLE:
            d = COUNTRY_DOSSIERS[nat]
            self.flag(nat, (L + 0.085, y - 0.030), 0.075)
            self.text(C.COUNTRIES[nat]['name'].upper(),
                      (L + 0.20, y), 0.034)
            self.text(d['epithet'], (L + 0.20, y - 0.048), 0.022,
                      INK_FAINT)
            self.text("+ " + "  + ".join(s.title()
                                         for s in d['strengths'][:2]),
                      (-0.36, y), 0.0225, GREEN_INK)
            self.text("- " + "  - ".join(w.title()
                                         for w in d['weaknesses'][:2]),
                      (-0.36, y - 0.044), 0.0225,
                      (0.62, 0.14, 0.10, 1.0))
            x = -0.36
            for label, score in d['ratings']:
                self.text(label, (x, y - 0.098), 0.019, INK_FAINT)
                for k in range(5):
                    sq = DirectFrame(
                        parent=self._content,
                        frameColor=(INK if k < score else
                                    (INK[0], INK[1], INK[2], 0.15)),
                        frameSize=(-0.009, 0.009, -0.009, 0.009),
                        pos=(x + 0.20 + k * 0.028, 0, y - 0.092))
                x += 0.42
            self.rule(L, R, y - 0.140, 0.0014)
            y -= 0.205
        self.text("Every power fields the same chassis under its "
                  "own name and modifiers; the QUICK MATCH sheet "
                  "carries each staff appreciation in full.",
                  (0, -0.655), 0.022, INK_FAINT, TextNode.ACenter)

    def _page_research(self):
        import tech
        t = self.BODY_TOP
        L, R = -1.32, 1.32
        self.bullets([
            "Research points come FROM THE TOWNS ALONE: RUN THE "
            "LABORATORIES earns %.0f RP per million souls (min "
            "%.0f), TIMES the labs level (x%s at the top)."
            % (C.FOCUS_RESEARCH_RP_PER_M, C.FOCUS_RESEARCH_RP_MIN,
               C.LAB_YIELD_MULT[-1]),
            "A programme opens when every programme wired above "
            "it is delivered. Spending is instant on the RESEARCH "
            "CHART [R].",
        ], L, t, step=0.075, scale=0.024)
        cols = [("PROGRAMME", L, TextNode.ALeft),
                ("BRANCH", -0.52, TextNode.ALeft),
                ("COST", -0.16, TextNode.ARight),
                ("AFTER", -0.06, TextNode.ALeft),
                ("DELIVERS", 0.52, TextNode.ALeft)]
        ty = t - 0.170
        for name, x, align in cols:
            self.text(name, (x, ty), 0.024, RED_INK, align)
        self.rule(L, R, ty - 0.020, 0.0022, INK)
        y = ty - 0.062
        nodes = sorted(tech.NODES.items(),
                       key=lambda kv: (kv[1]['branch'],
                                       kv[1]['row'], kv[1]['cost']))
        def prog_name(nid):
            return nid.replace('_', ' ').upper()

        for nid, node in nodes:
            self.text(prog_name(nid), (L, y), 0.023)
            self.text({'land': 'ARMY', 'air': 'AIR',
                       'sea': 'NAVY'}[node['branch']],
                      (-0.52, y), 0.023, INK_FAINT)
            self.text("%d RP" % node['cost'], (-0.16, y), 0.023,
                      INK, TextNode.ARight)
            req = ", ".join(prog_name(r)
                            for r in node['req']) or "--"
            self.text(req[:26], (-0.06, y), 0.021, INK_FAINT)
            unlocks = ", ".join(
                ('Radar Station' if u == 'radar_station'
                 else UNIT_TYPES[u]['label'])
                for u in node['unlocks'])
            self.text(unlocks[:40], (0.52, y), 0.021, INK_FAINT)
            self.rule(L, R, y - 0.018, 0.0012)
            y -= 0.052
        self.text("The 1939 fleet -- destroyers, transports, "
                  "supply ships, the battleship of the day -- "
                  "needs no research at all.",
                  (0, -0.655), 0.022, INK_FAINT, TextNode.ACenter)

    def _page_diplomacy(self):
        import deals
        t = self.BODY_TOP
        L, M = -1.32, 0.06
        self.header("STANDING -- HOW THEY PRICE YOU", (L, t))
        y = t - 0.060
        for floor, word, mult in deals.STANDING:
            band = (">= %d" % floor if floor > -900 else "BELOW")
            self.text(band, (L + 0.02, y), 0.024, INK_FAINT)
            self.text(word, (L + 0.24, y), 0.026, INK)
            self.text("asks priced at %d%% of worth"
                      % int(mult * 100), (L + 0.52, y), 0.023,
                      INK_FAINT)
            y -= 0.048
        self.header("THE ENVOYS", (L, y - 0.030))
        self.bullets([
            "Your sheets go out from the NEGOTIATING TABLE and "
            "are answered at",
            "  once. Foreign envoys call ONE AT A TIME with terms "
            "of their own --",
            "  NOTHING BINDS UNTIL YOU SIGN. Accept or send him "
            "away.",
            "An alliance is never sold cold: it wants standing of "
            "45 or better.",
        ], L, y - 0.085)
        self.header("ACTS NEEDING NO SIGNATURE", (L, y - 0.330))
        self.bullets([
            "DECLARE WAR, at any hour. BREAK YOUR OWN PACT. "
            "REQUEST VOLUNTEERS",
            "  of an ally: 10 Enlisted at $40 a man, a quarter "
            "off per shared war.",
        ], L, y - 0.385)

        self.vrule(-0.04, -0.66, t + 0.02)
        self.header("THE INSTRUMENTS", (M, t))
        from ui import DiplomacyLedger
        inst = [
            ('RIGHT OF PASSAGE', 'passage'),
            ('USE OF THE SUPPLY NET', 'supply'),
            ('USE OF THE WIRELESS NET', 'comms'),
            ('PACT OF NON-AGGRESSION', 'nonaggression'),
            ('PACT OF ALLIANCE', 'alliance'),
            ('AN END TO THE WAR', 'peace'),
            ('FUNDS, ONCE OR STANDING', 'funds_once'),
            ('CARGO, ONCE OR STANDING', 'res_once'),
        ]
        y = t - 0.060
        for label, kind in inst:
            tip = DiplomacyLedger.TOKEN_TIP.get(kind, '')
            self.text(label, (M + 0.02, y), 0.024, INK)
            self.text(tip.capitalize(), (M + 0.02, y - 0.036),
                      0.021, INK_FAINT, wrap=58)
            self.rule(M + 0.02, 1.30, y - 0.064, 0.0012)
            y -= 0.096
        self.text("THE FRONTIER IS REAL: without passage or war, "
                  "your columns and your engineers stop at the "
                  "border -- and the router plots no course "
                  "through a closed country.",
                  (M, y - 0.020), 0.023, INK, wrap=56)
        self.text("WAR TEARS UP THE PAPERS: every right and "
                  "standing arrangement with a belligerent dies "
                  "with the declaration -- however the war "
                  "arrived.",
                  (M, y - 0.155), 0.023, INK, wrap=56)

    def _page_controls(self):
        t = self.BODY_TOP
        L, M = -1.32, 0.06
        left = [
            ("LMB", "Select. Drag a box for many; double-click "
             "for every unit of a type on screen."),
            ("RMB", "Order: move, attack, board, build. Orders "
             "CHAIN through transports and works."),
            ("SHIFT + RMB", "Queue waypoints; with an engineer, "
             "survey multi-leg roads and rails."),
            ("CTRL + 1-9", "Assign a command group; 1-9 recalls "
             "it."),
            ("H", "Halt the selection."),
            ("SPACE", "Pause the war."),
            ("= / -", "Game speed up / down."),
            ("ESC", "Field orders menu; closes any open sheet."),
            ("MENU KEY", "The three-bar key, top left of the bar: "
             "FIELD ORDERS, same as ESC."),
        ]
        right = [
            ("B", "The BUDGET MANIFEST."),
            ("R", "The RESEARCH CHART."),
            ("ENTER", "Launch the readied sorties."),
            ("W A S D / MMB", "Pan the camera."),
            ("WHEEL", "Zoom, gliding toward the cursor."),
            ("TOP BAR KEYS", "Factory, resources, research and "
             "diplomacy reports."),
            ("CITY CLICK", "The CIVIC ICON beside the town's name "
             "selects it (it glows on hover); its keys open tax, "
             "draft and focus sheets."),
            ("[i] KEY", "The selected unit's service briefing."),
            ("WORKS CLICK", "A selected bunker, depot or engineer "
             "airfield carries a STRIKE key: two clicks "
             "decommission it."),
        ]
        self.header("IN THE FIELD", (L, t))
        y = t - 0.060
        for key, what in left:
            self.text(key, (L + 0.02, y), 0.026, INK)
            self.text(what, (L + 0.40, y), 0.0225, INK_FAINT,
                      wrap=42)
            self.rule(L + 0.02, -0.10, y - 0.055, 0.0012)
            y -= 0.088
        self.vrule(-0.04, -0.66, t + 0.02)
        self.header("AT HEADQUARTERS", (M, t))
        y = t - 0.060
        for key, what in right:
            self.text(key, (M + 0.02, y), 0.026, INK)
            self.text(what, (M + 0.40, y), 0.0225, INK_FAINT,
                      wrap=42)
            self.rule(M + 0.02, 1.30, y - 0.055, 0.0012)
            y -= 0.088

    def destroy(self):
        self.sheet.destroy()
